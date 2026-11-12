"""scripts/mock_uret.py: belirlilik, takvim uyumu, kimlik koruma ve hikâye koşulları.

Gerçek veritabanı veya model API kullanılmaz. Çıktı yalnız tmp_path içine yazılır.
"""

import ast
import importlib.util
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.services import takvim
from backend.app.services.risk import assess_risk


def _modul():
    yol = _PROJECT_ROOT / "scripts" / "mock_uret.py"
    spec = importlib.util.spec_from_file_location("mock_uret_test", yol)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


mock_uret = _modul()

_K1, _K2, _K3 = mock_uret.KONTROL_GUNLERI
# Kimlik karşılaştırma kaynağı: arşivlenmiş önceki mock.
_ARSIV = _PROJECT_ROOT / "database" / "archive" / "mock_data_hafta07-11.json"
_MEVCUT = json.loads(_ARSIV.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def veri() -> dict:
    return mock_uret.uret()


def _gun(metin: str) -> date:
    return date.fromisoformat(metin)


def test_kaynak_ve_cikti_yollari() -> None:
    assert mock_uret.MEVCUT_VERI == _ARSIV
    assert mock_uret.CIKTI == _PROJECT_ROOT / "database" / "mock_data.json"
    assert _ARSIV.is_file()
    assert not (_PROJECT_ROOT / "database" / "mock_data_v2.json").exists()


def test_depodaki_mock_uretimle_ayni() -> None:
    """database/mock_data.json, üreticinin çıktısıyla bayt bayt aynıdır."""
    assert mock_uret.CIKTI.read_bytes() == mock_uret.serilestir(mock_uret.uret())


def test_iki_calistirma_ayni_md5(tmp_path: Path) -> None:
    ilk = mock_uret.serilestir(mock_uret.uret())
    ikinci = mock_uret.serilestir(mock_uret.uret())
    assert mock_uret.md5(ilk) == mock_uret.md5(ikinci)
    assert ilk == ikinci
    dosya_a = tmp_path / "a.json"
    dosya_b = tmp_path / "b.json"
    _, icerik_a = mock_uret.yaz(dosya_a)
    _, icerik_b = mock_uret.yaz(dosya_b)
    assert dosya_a.read_bytes() == dosya_b.read_bytes() == icerik_a == icerik_b
    assert json.loads(icerik_a.decode("utf-8")) == mock_uret.uret()


def test_cikti_dosyasi_mevcut_dosyayla_ayni_anahtarlar(veri: dict) -> None:
    assert list(veri) == list(_MEVCUT)
    for tablo in _MEVCUT:
        assert list(veri[tablo][0]) == list(_MEVCUT[tablo][0]), tablo
        for satir in veri[tablo]:
            assert list(satir) == list(_MEVCUT[tablo][0]), tablo
    metin = mock_uret.serilestir(veri).decode("utf-8")
    assert metin.endswith("}\n")
    assert metin == json.dumps(veri, ensure_ascii=False, indent=2) + "\n"


def test_kimlikler_ardisik(veri: dict) -> None:
    for tablo in ("teachers", "students", "grades", "attendance"):
        assert [r["id"] for r in veri[tablo]] == list(range(1, len(veri[tablo]) + 1))


def test_mevcut_12_ogrenci_ve_hesap_baglari_ayni(veri: dict) -> None:
    assert veri["students"][:12] == _MEVCUT["students"]
    assert veri["users"] == _MEVCUT["users"]
    assert veri["teachers"][:2] == _MEVCUT["teachers"]
    kullanici = {r["username"]: r for r in veri["users"]}
    ogrenci = {r["id"]: r for r in veri["students"]}
    assert kullanici["teacher1"]["related_class"] == "9-A"
    assert kullanici["parent1"]["related_id"] == 1
    assert ogrenci[1]["name"] == "Ali Yılmaz" and ogrenci[1]["parent_id"] == 4
    assert kullanici["student1"]["related_id"] == 1


def test_yeni_ogrenci_ve_ogretmenler(veri: dict) -> None:
    ogrenciler = veri["students"]
    assert len(ogrenciler) == 36
    adlar = [r["name"] for r in ogrenciler]
    assert len(set(adlar)) == len(adlar)
    sayim = Counter(r["class_name"] for r in ogrenciler)
    assert sayim == {"9-A": 6, "10-B": 6, "5-A": 6, "6-C": 6, "11-A": 6, "12-B": 6}
    for r in ogrenciler[12:]:
        assert r["parent_id"] is None
    assert len(veri["users"]) == 7
    assert [(r["name"], r["class_name"]) for r in veri["teachers"][2:]] == [
        ("Hülya Er", "6-C"),
        ("Serkan Tan", "11-A"),
        ("Gül Oral", "12-B"),
        ("Nihan Akın", "5-A"),
    ]


def test_5a_ogretmeni_hesapsiz_ve_siradaki_kimlikte(veri: dict) -> None:
    nihan = [r for r in veri["teachers"] if r["name"] == "Nihan Akın"]
    assert nihan == [{"id": len(veri["teachers"]), "name": "Nihan Akın", "class_name": "5-A"}]
    assert nihan[0]["id"] == max(r["id"] for r in veri["teachers"])
    # Mevcut öğretmen kimlikleri değişmedi; yeni kayıtların hesabı yok.
    assert veri["teachers"][: len(_MEVCUT["teachers"])] == _MEVCUT["teachers"]
    assert veri["users"] == _MEVCUT["users"]
    assert all(r["related_class"] != "5-A" for r in veri["users"] if r["role"] == "teacher")


def test_hicbir_kayit_okul_gunu_olmayan_tarihte_degil(veri: dict) -> None:
    for r in veri["attendance"] + veri["grades"]:
        assert takvim.okul_gunu_mu(_gun(r["date"])), r
    beklenen = [g.isoformat() for g in takvim.okul_gunleri(date(2026, 9, 14), date(2027, 6, 25))]
    assert sorted({r["date"] for r in veri["attendance"]}) == beklenen


def test_devamsizlik_her_okul_gunu_her_ogrenci(veri: dict) -> None:
    sayim = Counter((r["student_id"], r["date"]) for r in veri["attendance"])
    assert set(sayim.values()) == {1}
    gunler = {r["date"] for r in veri["attendance"]}
    assert len(veri["attendance"]) == len(gunler) * len(veri["students"])
    assert {r["status"] for r in veri["attendance"]} == {"present", "absent", "excused"}


def test_her_ogrenci_ders_icin_8_not_ilgili_pencerede(veri: dict) -> None:
    gruplar: dict[tuple[int, str], list[dict]] = {}
    for r in veri["grades"]:
        gruplar.setdefault((r["student_id"], r["subject"]), []).append(r)
    assert len(gruplar) == 36 * 5
    assert {ders for _, ders in gruplar} == set(mock_uret.DERSLER)
    for liste in gruplar.values():
        assert len(liste) == 8
        tarihler = sorted(_gun(r["date"]) for r in liste)
        for tarih, (bas, bit) in zip(tarihler, mock_uret.NOT_PENCERELERI, strict=True):
            assert bas <= tarih <= bit
    assert len(veri["grades"]) == 36 * 5 * 8


def test_ayni_sinif_ders_ayni_gunu_kullanir(veri: dict) -> None:
    sinif_of = {r["id"]: r["class_name"] for r in veri["students"]}
    gunler: dict[tuple[str, str, int], set[str]] = {}
    for r in veri["grades"]:
        tarih = _gun(r["date"])
        pencere = next(
            i for i, (bas, bit) in enumerate(mock_uret.NOT_PENCERELERI) if bas <= tarih <= bit
        )
        anahtar = (sinif_of[r["student_id"]], r["subject"], pencere)
        gunler.setdefault(anahtar, set()).add(r["date"])
    assert all(len(v) == 1 for v in gunler.values())


def test_notlar_0_100_ve_iki_ondalik(veri: dict) -> None:
    for r in veri["grades"]:
        assert isinstance(r["grade"], float)
        assert 0.0 <= r["grade"] <= 100.0
        assert round(r["grade"], 2) == r["grade"]


def _risk(veri: dict, gun: date) -> dict[str, dict]:
    sinir = gun.isoformat()
    notlar = [r for r in veri["grades"] if r["date"] <= sinir]
    devam = [r for r in veri["attendance"] if r["date"] <= sinir]
    return {r["name"]: r for r in assess_risk(veri["students"], notlar, devam)}


@pytest.mark.parametrize("gun", [_K1, _K2, _K3])
def test_hikaye_bayraklari(veri: dict, gun: date) -> None:
    satirlar = _risk(veri, gun)
    assert not satirlar["Ali Yılmaz"]["flagged"]
    for ad in ("Zeynep Demir", "Lina Öztürk", "Ece Polat"):
        assert satirlar[ad]["flagged"], ad


@pytest.mark.parametrize("gun", [_K1, _K2, _K3])
def test_hikaye_ali_ve_zeynep(veri: dict, gun: date) -> None:
    rapor = mock_uret.kontrol_raporu(veri, gun)
    assert rapor["kosullar"], gun
    assert all(rapor["kosullar"].values()), rapor["kosullar"]


def test_hikaye_hatasi_yok(veri: dict) -> None:
    assert mock_uret.hikaye_hatalari(veri) == []


def test_elli_alti_notlar(veri: dict) -> None:
    dusuk = mock_uret.elli_alti(veri)
    assert 0.03 <= dusuk["oran"] <= 0.06
    assert len(dusuk["ogrenciler"]) >= 4
    zeynep = next(r["id"] for r in veri["students"] if r["name"] == "Zeynep Demir")
    assert zeynep in dusuk["ogrenciler"]
    assert dusuk["yeni_sinif_ortalama_50_alti"]


def test_mazeretli_devamsizlik_kumeleri(veri: dict) -> None:
    uzunluklar: Counter = Counter()
    for sid in range(1, 37):
        sayac = 0
        for r in [x for x in veri["attendance"] if x["student_id"] == sid] + [{"status": ""}]:
            if r["status"] == "excused":
                sayac += 1
            elif sayac:
                uzunluklar[sayac] += 1
                sayac = 0
    assert any(uzunluk in uzunluklar for uzunluk in (2, 3, 4))
    assert max(uzunluklar) <= 4


# ------------------------------------------------ Ali'nin devamsızlık profili


def _kimlik(veri: dict, ad: str) -> int:
    return next(r["id"] for r in veri["students"] if r["name"] == ad)


def _mazeretsiz(veri: dict, gun: date) -> dict[int, int]:
    """Öğrenci başına gun (dahil) tarihine kadar mazeretsiz gün; testte bağımsız sayım."""
    sayilar: dict[int, int] = {r["id"]: 0 for r in veri["students"]}
    for r in veri["attendance"]:
        if r["status"] == "absent" and r["date"] <= gun.isoformat():
            sayilar[r["student_id"]] += 1
    return sayilar


def test_ali_yil_sonu_mazeretsiz_8_ile_9(veri: dict) -> None:
    ali = _kimlik(veri, "Ali Yılmaz")
    assert 8 <= _mazeretsiz(veri, _K3)[ali] <= 9


@pytest.mark.parametrize("gun", [_K1, _K2, _K3])
def test_ali_9a_da_en_cok_mazeretsiz(veri: dict, gun: date) -> None:
    sayilar = _mazeretsiz(veri, gun)
    ali = _kimlik(veri, "Ali Yılmaz")
    digerleri = [
        r["id"] for r in veri["students"] if r["class_name"] == "9-A" and r["id"] != ali
    ]
    assert digerleri
    for sid in digerleri:
        assert sayilar[ali] > sayilar[sid], (gun, sid)


def test_ali_profildeki_sayida_mazeretli_kume_1_ile_4_gun(veri: dict) -> None:
    ali = _kimlik(veri, "Ali Yılmaz")
    uzunluklar: list[int] = []
    sayac = 0
    for r in [x for x in veri["attendance"] if x["student_id"] == ali] + [{"status": ""}]:
        if r["status"] == "excused":
            sayac += 1
        elif sayac:
            uzunluklar.append(sayac)
            sayac = 0
    assert len(uzunluklar) == mock_uret.PROFILLER["Ali Yılmaz"]["mazeretli_kume"]
    assert all(1 <= uzunluk <= 4 for uzunluk in uzunluklar)


@pytest.mark.parametrize("gun", [_K1, _K2, _K3])
def test_zeynep_bayrakli_ali_degil_her_kontrol_gununde(veri: dict, gun: date) -> None:
    satirlar = _risk(veri, gun)
    assert satirlar["Zeynep Demir"]["flagged"]
    assert not satirlar["Ali Yılmaz"]["flagged"]


def test_ortaogretim_yil_sonu_mazeretsiz_10u_gecmez(veri: dict) -> None:
    sayilar = _mazeretsiz(veri, _K3)
    siniflar = {"9-A", "10-B", "11-A", "12-B"}
    kontrol = [r for r in veri["students"] if r["class_name"] in siniflar]
    assert len(kontrol) == 24
    for r in kontrol:
        assert sayilar[r["id"]] <= 10, (r["name"], sayilar[r["id"]])


# ------------------------------------------- profil parametreli, isimsiz üretim


def test_isme_ozel_devamsizlik_kodu_yok() -> None:
    for ad in (
        "_ali_devamsizligi",
        "_devam_duzelt",
        "_devamsiz_indeksler",
        "ALI_MAZERETSIZ",
        "ALI_MAZERETLI_KUMELER",
        "MAZERETSIZ_CIKAR",
    ):
        assert not hasattr(mock_uret, ad), ad


def test_ogrenci_adlari_yalniz_tanim_blogunda() -> None:
    """Hiçbir fonksiyon gövdesinde (docstring dahil) öğrenci adı string sabiti yoktur."""
    kaynak = (_PROJECT_ROOT / "scripts" / "mock_uret.py").read_text(encoding="utf-8")
    agac = ast.parse(kaynak)
    adlar = set(mock_uret.PROFILLER)
    assert len(adlar) == 36

    def _adli(dugum: ast.AST) -> list[str]:
        return [
            alt.value
            for alt in ast.walk(dugum)
            if isinstance(alt, ast.Constant)
            and isinstance(alt.value, str)
            and any(ad in alt.value for ad in adlar)
        ]

    fonksiyonlar = [
        d for d in ast.walk(agac) if isinstance(d, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert fonksiyonlar
    ihlaller = [(f.name, deger) for f in fonksiyonlar for deger in _adli(f)]
    assert ihlaller == []
    # Adlar gerçekten modül düzeyindeki tanım bloklarında duruyor.
    modul_duzeyi = [d for d in agac.body if not isinstance(d, ast.FunctionDef)]
    assert sum(len(_adli(d)) for d in modul_duzeyi) >= len(adlar)


def test_her_profilde_iki_devamsizlik_parametresi_ve_yil_sonu_esitligi(veri: dict) -> None:
    """Profilde verilen mazeretsiz_hedef / mazeretli_kume yıl sonunda aynen gerçekleşir."""
    sayilar = _mazeretsiz(veri, _K3)
    verilen = 0
    for r in veri["students"]:
        ozel = mock_uret.PROFILLER[r["name"]]
        if "mazeretsiz_hedef" in ozel:
            verilen += 1
            assert sayilar[r["id"]] == ozel["mazeretsiz_hedef"], r["name"]
        kumeler = mock_uret.mazeretli_kume_uzunluklari(veri, r["id"])
        assert len(kumeler) <= mock_uret.MAZERETLI_KUME_UST_SINIR, r["name"]
        assert all(1 <= uzunluk <= 4 for uzunluk in kumeler), r["name"]
        if "mazeretli_kume" in ozel:
            assert len(kumeler) == ozel["mazeretli_kume"], r["name"]
    assert verilen >= 5


def test_verilen_hedefler() -> None:
    beklenen = {
        "Ali Yılmaz": 9,
        "Zeynep Demir": 8,
        "Selin Koç": 7,
        "Lina Öztürk": 10,
        "Ceren Altın": 10,
    }
    for ad, hedef in beklenen.items():
        assert mock_uret.PROFILLER[ad]["mazeretsiz_hedef"] == hedef, ad
    assert mock_uret.PROFILLER["Ali Yılmaz"]["mazeretli_kume"] == 2


def test_mazeretli_kume_mazeretsiz_gunle_cakismaz(veri: dict) -> None:
    """Kümelerin iki yanı (varsa) "present"tir: mazeretsiz güne değmez, kümeler birleşmez."""
    for r in veri["students"]:
        durumlar = [x["status"] for x in veri["attendance"] if x["student_id"] == r["id"]]
        for sira, durum in enumerate(durumlar):
            if durum != "excused":
                continue
            for komsu in (sira - 1, sira + 1):
                if 0 <= komsu < len(durumlar) and durumlar[komsu] != "excused":
                    assert durumlar[komsu] == "present", (r["name"], sira)
        kumeler = mock_uret.mazeretli_kume_uzunluklari(veri, r["id"])
        assert sum(kumeler) == durumlar.count("excused"), r["name"]
