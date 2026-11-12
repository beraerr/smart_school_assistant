"""Metin yaması (docs/metin_yamasi.json) testleri.

Beklenen değerler açık kaynaklardan gelir (yama dosyası, ek_metrics.json, docs/*.md, WEEK_10 kayıtları,
notebook hücreleri); uygulamanın kendi çıktısından türetilmez.
"""

import html
import json
import re
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

_FRONTEND = Path(__file__).resolve().parents[1]
_ROOT = _FRONTEND.parent
for yol in (_ROOT, _FRONTEND):
    if str(yol) not in sys.path:
        sys.path.insert(0, str(yol))

import arastirma  # noqa: E402
from arastirma_metin import ARAYUZ, EKSIK_EN, METIN, SEKME_SIRA, YER_TUTUCU  # noqa: E402
from data_science.oulad.rule import FLAG_RATE  # noqa: E402

_APP = _FRONTEND / "app.py"
_DOCS = _ROOT / "docs"
_YAMA = json.loads((_DOCS / "metin_yamasi.json").read_text(encoding="utf-8"))
_EK_METRICS = json.loads(
    (_ROOT / "data_science" / "oulad" / "reports" / "ek_metrics.json").read_text(encoding="utf-8")
)
# WEEK_09/WEEK_10 kayıtları haftaların kendi klasörlerinde durur (week-11/docs altında değil).
_HAFTALAR = _ROOT / "docs" / "haftalar"

# Yamadaki {?ad} yer tutucularının gerçek paket yolları (yamanın soru_isaretli_yer_tutucular bölümü).
_ESLEME = {
    "?kapasite": "rule.flag_rate",
    "?beklenti_toplam": "ek.summary.total",
    "?n_modul": "turev.oulad.n_modul",
    "?e3_30_test": "turev.ek.e3_30_test",
}
_SAYILAR = re.compile(r"\d+(?:[.,]\d+)*")
_YEDI_YER_TUTUCU = re.compile(r"\{(\?[a-z0-9_]+):")


# --- Yardımcılar ---------------------------------------------------------------------


def _sayfa(lang: str, bolum: str) -> AppTest:
    at = AppTest.from_file(str(_APP), default_timeout=30)
    at.session_state["token"] = None
    at.session_state["user"] = None
    at.session_state["lang"] = lang
    at.query_params["sayfa"] = "arastirma"
    at.query_params["bolum"] = bolum
    at.run()
    assert len(at.exception) == 0, [e.value for e in at.exception]
    return at


def _sayfa_metni(at: AppTest) -> str:
    parcalar = [str(oge.value) for oge in at.markdown if not str(oge.value).lstrip().startswith("<style>")]
    parcalar += [str(oge.value) for oge in at.code]
    parcalar += [str(oge.value) for oge in at.caption]
    return "\n".join(parcalar)


def _tum_sekmeler(lang: str) -> str:
    return "\n".join(_sayfa_metni(_sayfa(lang, bolum)) for bolum in SEKME_SIRA)


def _metinler(deger: object):
    if isinstance(deger, str):
        yield deger
    elif isinstance(deger, dict):
        for oge in deger.values():
            yield from _metinler(oge)
    elif isinstance(deger, (tuple, list)):
        for oge in deger:
            yield from _metinler(oge)


def _duz(deger: object) -> object:
    """Tuple/list farkını yok sayarak karşılaştırma için JSON biçimine getirir."""
    return json.loads(json.dumps(deger, ensure_ascii=False))


def _yamadaki_yol(metin: str) -> str:
    return _YEDI_YER_TUTUCU.sub(lambda e: "{" + _ESLEME[e.group(1)] + ":", metin)


def _yama_degeri(deger: object) -> object:
    """Yama değerinde {?ad} yer tutucularını gerçek yollarına çevirir (başka hiçbir şey değişmez)."""
    if isinstance(deger, str):
        sonuc = _yamadaki_yol(deger)
        assert "{?" not in sonuc, f"eşlemesi olmayan yer tutucu: {deger}"
        return sonuc
    if isinstance(deger, dict):
        return {anahtar: _yama_degeri(oge) for anahtar, oge in deger.items()}
    if isinstance(deger, list):
        return [_yama_degeri(oge) for oge in deger]
    return deger


def _hata_kaydi(yol: Path, baslik: str, etiketler: tuple[str, str, str, str]) -> dict[str, str]:
    """Hafta dosyasındaki hata kaydının dört alanı (belirti, kok, duzeltme, sonra), olduğu gibi.

    WEEK_10.md'de kayıtla ilgisi olmayan bir satırda bozuk bayt var; bu yüzden dosya satır satır baytla
    okunur ve yalnızca kaydın satırları UTF-8 olarak SIKI çözülür (hata yutulmaz).
    """
    ham = yol.read_bytes().splitlines()
    sira = ham.index(baslik.encode("utf-8"))
    kayit = [satir.decode("utf-8") for satir in ham[sira + 1 : sira + 6]]
    sonuc = {}
    for alan, etiket in zip(("belirti", "kok", "duzeltme", "sonra"), etiketler, strict=True):
        onek = f"- {etiket}: "
        bulunan = [satir for satir in kayit if satir.startswith(onek)]
        assert len(bulunan) == 1, f"{yol.name}: '{etiket}' satırı {len(bulunan)} kez"
        sonuc[alan] = bulunan[0][len(onek) :]
    return sonuc


# --- Yama metinleri aynen -----------------------------------------------------------------


@pytest.mark.parametrize("dil", ["tr", "en"])
def test_yamadaki_her_metin_aynen_yazilmis(dil: str) -> None:
    for anahtar, deger in _YAMA[dil].items():
        beklenen = _yama_degeri(deger)
        gercek = _duz(METIN[dil][anahtar])
        if anahtar == "hata_govde":
            # 6. kart yamada yok; kaynaktan alınır (aşağıdaki testte sınanır).
            gercek = {sira: kart for sira, kart in gercek.items() if sira != "6"}
        assert gercek == beklenen, f"{dil}/{anahtar}: yamadan farklı"


# --- (a) EN karşılığı ve yer tutucu kümesi -------------------------------------------------


def _yer_tutucu_kumesi(deger: object) -> list[tuple[str, str]]:
    return sorted(
        (yol, bicim) for metin in _metinler(deger) for yol, bicim in YER_TUTUCU.findall(metin)
    )


def test_eksik_en_bos() -> None:
    assert EKSIK_EN == ()


def test_her_tr_anahtarinin_en_karsiligi_var_ve_yer_tutucu_kumesi_ayni() -> None:
    assert set(METIN["tr"]) == set(METIN["en"]), sorted(set(METIN["tr"]) ^ set(METIN["en"]))
    for anahtar, deger in METIN["tr"].items():
        assert _yer_tutucu_kumesi(deger) == _yer_tutucu_kumesi(METIN["en"][anahtar]), anahtar


# --- (b) Her yer tutucu paketle çözülür ------------------------------------------------------


@pytest.mark.parametrize("dil", ["tr", "en"])
def test_her_yer_tutucu_paketle_cozulur(dil: str) -> None:
    paket = arastirma.tam_paket()
    for anahtar, deger in METIN[dil].items():
        for metin in _metinler(deger):
            assert "{?" not in metin, f"{dil}/{anahtar}: çözülmemiş soru işaretli yer tutucu"
            cozulmus = arastirma.coz(metin, paket, dil)
            assert "{" not in cozulmus and "}" not in cozulmus, f"{dil}/{anahtar}: {cozulmus[:80]}"


# --- (c) Rakam testi ---------------------------------------------------------------------
#
# Yer tutucular çıkarıldıktan sonra her anahtarda kalan rakamlar, aşağıdaki açık izin listesine
# eşit olmalıdır. Liste, yamanın rakam_kararlari bölümündeki meşru sınıflardan anahtar bazında
# çıkarılmıştır:
#   yıl (2008, 2013, 2014, 2017, 2026) · lisans (CC BY 4.0) · gün sayısı (14/30/60/90/120. gün)
#   notebook adı (01/02/03) · ölçek (0–20, 20 üzerinden, 100'lük) · değer etiketi (G3=0, devamsızlık 0)
#   hafta adı (H8–H11, Hafta 8) · kimlik (B1–B10, E1–E4, kart no) · okuma süresi (~20 dk)
# Sütun kimlikleri (G1, G2, G3) ve "md5" adı kimlik sınıfındandır; sayı değildir.
# Yeni elle yazılmış bir rakam bu testi kırar.
_IZIN: dict[str, list[str]] = {
    "veri1": ["0", "20", "1", "2", "3", "2008", "4.0"],  # ölçek, G1/G2/G3, yıl, lisans
    "veri2": ["2013", "2014", "2017", "4.0"],  # yıl, lisans
    "uci_bulgu": ["1", "3"],  # G1, G3
    "u1_dahil": ["3", "0"],  # G3=0
    "u1_haric": ["3", "0"],  # G3=0
    "oulad_duzen": ["60"],  # gün
    "b47": ["60"],  # gün
    "r1_not": ["60"],  # gün
    "tablo_11": ["60"],  # gün
    "yeniden_uretim": ["01", "02", "03", "2008", "2017"],  # notebook adı, yıl
    "ozet_gosterebildik": ["60"],  # gün
    "z1_duraklar": ["8", "9", "60", "10", "11", "11", "5"],  # H8–H11, H11+, 60. gün, md5
    "veri_d0": ["2013", "2014", "20", "4.0", "4.0"],  # yıl, 20 üzerinden, lisans
    "veri_d2_not": ["60"],  # gün
    "uci_u1_not": ["20", "100"],  # ölçek
    "uci_u2_bulgu": ["0"],  # değer etiketi (final notu 0)
    "uci_u4_alt": ["1", "2", "3"],  # G1, G2, G3
    "uci_u5_bulgu": ["2", "3", "1"],  # G1, G2, G3
    "hata_basliklar": ["02", "03"],  # notebook adı
    "kaynak_kaynakca": ["2008", "2017"],  # yıl
    "kaynak_yazar": ["2026"],  # yıl
    "ek_basliklar": ["2", "1", "3", "4"],  # E1–E4
    "ek_harita": ["8", "3", "0", "9", "10", "60", "11"],  # H8–H11, G3=0, 60. gün
    "ek_sorular": ["1", "2", "3", "4"],  # E1–E4
    "ek_onkayit": ["5"],  # md5
    "ek_muhur": ["5"],  # md5
    "ek_e2_metin": ["4"],  # B4
    "ek_e1_metin": ["1", "3", "2"],  # B1, B3, B2
    "ek_e3_metin": ["14", "30", "60", "90", "120", "8", "60", "9", "14", "10"],  # gün, B8–B10
    "ek_e3_karar": ["14", "3"],  # 14. gün, E3
    "ek_x5_not": ["120"],  # gün
    "ek_e3_bulgu": ["60", "14", "60", "60"],  # gün
    "ek_kapanis": ["60"],  # gün
    "ham_uci": ["3", "0"],  # G3=0
    # LİTERATÜR İSTİSNASI (spec eki 2.6): dış kaynak sayısı, "%90'ın üzerinde"; 2026 yıl.
    "ek_e4_metin": ["90", "2026"],
}
# uci_hata: değer etiketleri (final notu 0, devamsızlık 0); EN cümle yapısı farklı olduğundan dil başına.
_IZIN_DIL: dict[tuple[str, str], list[str]] = {
    ("tr", "uci_hata"): ["0", "0"],
    ("en", "uci_hata"): ["0"],
}
# hata_govde kart başına: 1 (final notu 0, G3=0), 6 (60. gün), 8 (Hafta 8), 9 (Notebook 02 ve 03),
# 10 (Notebook 03), 11 (md5), 12 (B4, B5, B7).
_IZIN_HATA_KART: dict[str, list[str]] = {
    "1": ["0", "0", "3", "0"],
    "6": ["60"],
    "8": ["8"],
    "9": ["02", "03"],
    "10": ["03"],
    "11": ["5"],
    "12": ["4", "5", "7"],
}
# ek_l1: Wu/Adnan/Scientific Reports satırları, gözlemler ve kaynakça literatürdür; rakamları
# dış kaynaktandır (spec eki 2.6, tek istisna). Başka hiçbir anahtar bu listeye eklenmez.
_LITERATUR_ISTISNASI = frozenset({"ek_l1"})


def _kalan_sayilar(deger: object) -> list[str]:
    return [
        sayi
        for metin in _metinler(deger)
        for sayi in _SAYILAR.findall(YER_TUTUCU.sub("", metin))
    ]


@pytest.mark.parametrize("dil", ["tr", "en"])
def test_yer_tutucu_disinda_kalan_rakamlar_izin_listesine_esit(dil: str) -> None:
    for anahtar, deger in METIN[dil].items():
        if anahtar in _LITERATUR_ISTISNASI:
            continue
        if anahtar == "hata_govde":
            assert set(deger) == {str(i) for i in range(1, 13)}
            for sira, kart in deger.items():
                beklenen = _IZIN_HATA_KART.get(sira, [])
                assert sorted(_kalan_sayilar(kart)) == sorted(beklenen), f"{dil}/hata_govde.{sira}"
            continue
        beklenen = _IZIN_DIL.get((dil, anahtar), _IZIN.get(anahtar, []))
        assert sorted(_kalan_sayilar(deger)) == sorted(beklenen), f"{dil}/{anahtar}: izin dışı rakam"


def test_izin_listesinde_olmayan_anahtar_yok() -> None:
    bilinen = set(METIN["tr"])
    assert set(_IZIN) <= bilinen
    assert {anahtar for _, anahtar in _IZIN_DIL} <= bilinen
    assert _LITERATUR_ISTISNASI <= bilinen


def test_yeni_elle_yazilmis_rakam_testi_kirar() -> None:
    """Bekçinin kendisi: yazılmış bir rakam izin listesinde değilse sayılır."""
    assert _kalan_sayilar("Bayrak oranı %20, {uci.total:tam} kayıt") == ["20"]
    assert _kalan_sayilar("Bayrak oranı {rule.flag_rate:yuzde}, {uci.total:tam} kayıt") == []


# --- (d) Spec numaraları sayfada geçmez ----------------------------------------------------


@pytest.mark.parametrize("dil", ["tr", "en"])
def test_sayfada_spec_numarasi_gecmez(dil: str) -> None:
    metin = _tum_sekmeler(dil)
    for yasak in ("2.1 ", "10.1 ", "(bölüm ", "Bölüm 9"):
        assert yasak not in metin, f"{dil}: sayfada '{yasak}' geçiyor"


# --- (e) turev değerleri açık kaynaktaki değerlere eşit ------------------------------------


def _belge_beklenti_sayisi() -> int:
    """docs/ek_analizler_sonuc.md beklenti tablolarındaki B<n> satırları."""
    kimlikler = re.findall(
        r"^\| (B\d+) \|", (_DOCS / "ek_analizler_sonuc.md").read_text(encoding="utf-8"), re.M
    )
    assert len(kimlikler) == len(set(kimlikler))
    return len(kimlikler)


def test_beklenti_sayisi_kaynaktaki_10a_esit() -> None:
    kaynak = len(_EK_METRICS["expectations"]) + len(_EK_METRICS["e3"]["expectations"])
    assert kaynak == _belge_beklenti_sayisi() == 10
    assert arastirma.tam_paket()["ek"]["summary"]["total"] == kaynak


def test_modul_sayisi_belgedeki_7ye_esit() -> None:
    belge = re.search(
        r"(\d+) modül", (_DOCS / "arastirma_raporu_spec_v2.md").read_text(encoding="utf-8")
    )
    assert belge is not None
    assert int(belge.group(1)) == 7
    assert arastirma.tam_paket()["turev"]["oulad"]["n_modul"] == 7


def test_e3_30_gun_sabit_kohort_test_degeri_belgedeki_0711e_esit() -> None:
    belge = re.search(
        r"sabit kohortta 30\. gün \.(\d{3})\b",
        (_DOCS / "ek_analizler_sonuc.md").read_text(encoding="utf-8"),
    )
    assert belge is not None
    beklenen = int(belge.group(1)) / 1000
    assert beklenen == 0.711
    kaynak = _EK_METRICS["e3"]["cutoff_results"]["30"]["targets"]["referans"]["results"]["GENERAL"][
        "hgb"
    ]["b_sabit_kohort"]["test"]["roc_auc"]["estimate"]
    assert round(kaynak, 3) == beklenen
    deger = arastirma.tam_paket()["turev"]["ek"]["e3_30_test"]
    assert deger == kaynak
    assert arastirma.bicimle(deger, "roc", "tr") == "0,711"
    assert arastirma.bicimle(deger, "roc", "en") == "0.711"


def test_bayrak_orani_kuralin_sabiti_ve_spec_v2deki_yuzde_20ye_esit() -> None:
    belge = re.search(
        r"sınıf içi %(\d+)", (_DOCS / "arastirma_raporu_spec_v2.md").read_text(encoding="utf-8")
    )
    assert belge is not None
    assert int(belge.group(1)) / 100 == FLAG_RATE == 0.2
    assert arastirma.tam_paket()["rule"]["flag_rate"] == FLAG_RATE


@pytest.mark.parametrize("dil", ["tr", "en"])
def test_bayrak_orani_metinlerde_tam_yuzde_olarak_gorunur(dil: str) -> None:
    """Beklenen değer spec'ten (sınıf içi %20); `yuzde` biçimi (%20,0 / 20.0%) bu alanda kullanılmaz."""
    belge = re.search(
        r"sınıf içi %(\d+)", (_DOCS / "arastirma_raporu_spec_v2.md").read_text(encoding="utf-8")
    )
    assert belge is not None
    beklenen = f"%{belge.group(1)}" if dil == "tr" else f"{belge.group(1)}%"
    assert beklenen == ("%20" if dil == "tr" else "20%")
    paket = arastirma.tam_paket()
    alanlar = [
        (anahtar, metin)
        for anahtar, deger in METIN[dil].items()
        for metin in _metinler(deger)
        if "{rule.flag_rate:" in metin
    ]
    assert len(alanlar) == 3, [a for a, _ in alanlar]
    for anahtar, metin in alanlar:
        assert "{rule.flag_rate:yuzdetam}" in metin, anahtar
        cozulen = arastirma.coz(metin, paket, dil)
        assert beklenen in cozulen, f"{dil}/{anahtar}: {beklenen} yok"
        for yasak in ("%20,0", "20.0%"):
            assert yasak not in cozulen, f"{dil}/{anahtar}: {yasak} görünüyor"
    assert beklenen in _tum_sekmeler(dil)


def test_soru_isaretli_yer_tutucularin_hepsi_eslenmis() -> None:
    assert set(_ESLEME) == set(_YAMA["soru_isaretli_yer_tutucular"])
    paket = arastirma.tam_paket()
    for yol in _ESLEME.values():
        arastirma.yol_degeri(paket, yol)


# --- Hata kartları -------------------------------------------------------------------------


@pytest.mark.parametrize("dil", ["tr", "en"])
def test_on_iki_hata_karti_dort_alanla_ve_cizim_kodundaki_alan_adlariyla(dil: str) -> None:
    govde = METIN[dil]["hata_govde"]
    assert sorted(govde, key=int) == [str(i) for i in range(1, 13)]
    for sira, kart in govde.items():
        assert set(kart) == {"belirti", "kok", "duzeltme", "sonra"}, f"{dil}/{sira}"
        assert all(kart[alan].strip() for alan in kart)
    # Kartın okuduğu alan adları çizim kodundakilerle aynı: etiketler ARAYUZ'de var.
    assert {"belirti", "kok", "duzeltme", "sonra"} <= set(ARAYUZ[dil])


@pytest.mark.parametrize("dil", ["tr", "en"])
def test_on_iki_hata_karti_butun_alanlariyla_cizilir(dil: str) -> None:
    paket = arastirma.tam_paket()
    metin = _sayfa_metni(_sayfa(dil, "hatalar"))
    for sira, kart in METIN[dil]["hata_govde"].items():
        for alan in ("belirti", "kok", "duzeltme", "sonra"):
            satir = f"**{ARAYUZ[dil][alan]}:** {arastirma.coz(kart[alan], paket, dil)}"
            assert satir in metin, f"{dil}: kart {sira} '{alan}' çizilmedi"


def test_hata_karti_6_kaynak_kayittan_aynen() -> None:
    tr = _hata_kaydi(
        _HAFTALAR / "WEEK_10.md",
        "**Hata 1 — grafik alt metni**",
        ("Belirti", "Kök neden", "Düzeltme", "Durum"),
    )
    en = _hata_kaydi(
        _HAFTALAR / "WEEK_10_eng.md",
        "**Bug 1 — figure alternative text**",
        ("Symptom", "Root cause", "Fix", "Status"),
    )
    assert METIN["tr"]["hata_govde"]["6"] == tr
    assert METIN["en"]["hata_govde"]["6"] == en
    # Kartın başlığı yamadaki 6. başlıkla aynı kayıt: görülmemiş ders grafiğinin alt metni.
    assert "Görülmemiş ders" in METIN["tr"]["hata_basliklar"][5]


# --- Yeni metinler -------------------------------------------------------------------------

_BU_BOLUMDE = {
    "ozet_bu_bolumde": "ozet",
    "kural_bu_bolumde": "kural",
    "sistem_bu_bolumde": "sistem",
    "kaynak_bu_bolumde": "kaynak",
}


@pytest.mark.parametrize("dil", ["tr", "en"])
@pytest.mark.parametrize("anahtar,sekme", list(_BU_BOLUMDE.items()))
def test_bu_bolumde_kutulari_yamadaki_metinle_dogru_sekmede_cizilir(
    dil: str, anahtar: str, sekme: str
) -> None:
    assert METIN[dil][anahtar] == _YAMA["yeni_metinler"][anahtar][dil]
    metin = _sayfa_metni(_sayfa(dil, sekme))
    assert f"**{ARAYUZ[dil]['bu_bolumde']}.** {METIN[dil][anahtar]}" in metin
    for diger in set(SEKME_SIRA) - {sekme}:
        assert METIN[dil][anahtar] not in _sayfa_metni(_sayfa(dil, diger))


# --- Kaynaktan alınan O3 alt metni ------------------------------------------------------------


@pytest.mark.parametrize(
    "dil,defter",
    [("tr", "02_oulad_eda.ipynb"), ("en", "02_oulad_eda_eng.ipynb")],
)
def test_o3_alt_metni_notebook_hucre_17den_aynen(dil: str, defter: str) -> None:
    hucre = json.loads((_ROOT / "notebooks" / defter).read_text(encoding="utf-8"))["cells"][17]
    assert hucre["cell_type"] == "markdown"
    beklenen = "".join(hucre["source"]).strip()
    satir = arastirma.gorsel_satiri(arastirma.paketi_oku(), "O3", dil)
    assert satir["alt"] == beklenen
    assert not _SAYILAR.search(beklenen)


# --- L1 tablosu: yer tutuculu hücreler ve gözlemler çözülerek çizilir -------------------------


@pytest.mark.parametrize("dil", ["tr", "en"])
def test_l1_tablosu_ve_gozlemleri_yer_tutuculari_cozulmus_cizilir(dil: str) -> None:
    paket = arastirma.tam_paket()
    metin = _sayfa_metni(_sayfa(dil, "ek"))
    assert "{" not in metin and "}" not in metin
    l1 = METIN[dil]["ek_l1"]
    for satir in l1["satirlar"]:
        for hucre in satir:
            cozulmus = arastirma.coz(hucre, paket, dil)
            assert cozulmus in metin or html.escape(cozulmus) in metin, f"{dil}: L1 hücresi çizilmedi"
    for gozlem in l1["gozlemler"]:
        assert arastirma.coz(gozlem, paket, dil) in metin
    # Bu çalışmanın satırı ve Gözlem 2 paketin 0,711 / 0.711 değerini taşır.
    beklenen = {"tr": "0,711", "en": "0.711"}[dil]
    assert metin.count(beklenen) >= 2
