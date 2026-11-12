"""2026-2027 öğretim yılının tamamını kapsayan deterministik mock veri üreticisi.

Çıktı database/mock_data.json dosyasıdır (teachers, students, users, grades,
attendance). Kimlikler ve hesaplar database/archive/mock_data_hafta07-11.json
dosyasından alınır; o dosya değiştirilmez. Veritabanına yazmaz.

Üretim random.Random(20260914) ile yapılır; "şimdi" okunmaz. Aynı çalıştırma
her seferinde bayt bayt aynı dosyayı verir.

Proje kökünden:
    python scripts/mock_uret.py
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from datetime import date
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.services import takvim
from backend.app.services.risk import assess_risk

TOHUM = 20260914
MEVCUT_VERI = _PROJECT_ROOT / "database" / "archive" / "mock_data_hafta07-11.json"
CIKTI = _PROJECT_ROOT / "database" / "mock_data.json"

# Arşiv dosyasındaki kimlikler: bunların üstündekiler yeni kayıttır.
MEVCUT_OGRENCI_SAYISI = 12
MEVCUT_OGRETMEN_SAYISI = 2

DERSLER = ("Matematik", "Fizik", "Kimya", "Türkçe", "Tarih")

NOT_PENCERELERI = (
    (date(2026, 9, 28), date(2026, 10, 2)),
    (date(2026, 10, 19), date(2026, 10, 23)),
    (date(2026, 12, 7), date(2026, 12, 11)),
    (date(2027, 1, 4), date(2027, 1, 8)),
    (date(2027, 2, 22), date(2027, 2, 26)),
    (date(2027, 3, 22), date(2027, 3, 26)),
    (date(2027, 4, 26), date(2027, 4, 30)),
    (date(2027, 5, 31), date(2027, 6, 4)),
)

KONTROL_GUNLERI = (date(2026, 11, 3), date(2027, 1, 22), date(2027, 6, 25))

# Sıra önemlidir: kimlikler mevcut 12 öğrenciden sonra bu sırayla 13'ten başlar.
YENI_OGRENCILER: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("9-A", ("Emre Aydın", "Selin Koç")),
    ("10-B", ("Burak Şahin", "Defne Arslan")),
    ("5-A", ("Yusuf Kara", "Elif Çelik")),
    ("6-C", ("Mert Yıldız", "Ayşe Doğan", "Kerem Özkan", "Nehir Aksoy", "Can Erdem", "İrem Kurt")),
    ("11-A", ("Barış Güneş", "Zehra Tunç", "Onur Keskin", "Melis Uçar", "Efe Bulut", "Duru Avcı")),
    ("12-B", ("Arda Korkmaz", "Naz Eren", "Kaan Sezer", "Ela Yavuz", "Tuna Karaca", "Ceren Altın")),
)

# Arşivde olmayan, yeni eklenen sınıflar (50 altı yıl ortalaması kontrolü için).
YENI_SINIFLAR = ("6-C", "11-A", "12-B")

# Yeni sınıf öğretmenleri (giriş hesabı yok); kimlikler arşivdeki 2'den sonra gelir.
# Mevcut kimlikler değişmez; her yeni kayıt sıradaki kimliği alır.
YENI_OGRETMENLER = (
    ("Hülya Er", "6-C"),
    ("Serkan Tan", "11-A"),
    ("Gül Oral", "12-B"),
    ("Nihan Akın", "5-A"),
)

# Hikâye öğrencileri: kontrol ve kapı koşulları bu sabitlerle anılır; adlar
# yalnızca bu tanım bloğunda ve PROFILLER içinde geçer.
ANA_OGRENCI = "Ali Yılmaz"
RISKLI_OGRENCI = "Zeynep Demir"
BAYRAKLI_OGRENCILER = ("Lina Öztürk", "Ece Polat")

# Öğrenci profilleri. temel: ortalama başarı (0-100); ders_ozel: derse özgü ek
# sapma; egilim: ilk pencereden sonuncuya toplam değişim (puan); pencere_sd:
# pencere gürültüsü.
# Devamsızlık: mazeretsiz_hedef: yıl sonu (2027-06-25) mazeretsiz gün sayısı;
# mazeretli_kume: yıl içindeki mazeretli küme sayısı (0-3, her küme 1-4 gün);
# faz: mazeretsiz günlerin yıl içindeki başlangıç kayması (0-1).
# devamsizlik / mazeret: günlük oran; mazeretsiz_hedef ya da mazeretli_kume
# verilmediyse ondan türetilir.
# Burada olmayan alanlar rastgele (sabit tohumla) üretilir.
PROFILLER: dict[str, dict[str, Any]] = {
    # 9-A
    "Ali Yılmaz": {"temel": 84.0, "mazeretsiz_hedef": 9, "mazeretli_kume": 2, "faz": 0.0, "pencere_sd": 4.0, "egilim": 1.0, "ders_ozel": {"Fizik": -10.0}},
    "Zeynep Demir": {"temel": 64.0, "mazeretsiz_hedef": 8, "faz": 0.9, "pencere_sd": 5.5, "egilim": 0.0, "ders_ozel": {"Fizik": -17.0}},
    "Mehmet Kaya": {"temel": 79.0, "devamsizlik": 0.020},
    "Kerem Güneş": {"temel": 74.0, "devamsizlik": 0.030},
    "Emre Aydın": {"temel": 76.0, "devamsizlik": 0.022},
    "Selin Koç": {"temel": 68.0, "mazeretsiz_hedef": 7, "faz": 0.8},
    # 10-B
    "Elif Şahin": {"temel": 77.0, "devamsizlik": 0.035},
    "Can Arslan": {"temel": 77.0, "devamsizlik": 0.018},
    "Selin Yıldız": {"temel": 74.0, "devamsizlik": 0.020},
    "Lina Öztürk": {"temel": 61.0, "mazeretsiz_hedef": 10, "egilim": 0.0},
    "Burak Şahin": {"temel": 72.0, "devamsizlik": 0.025},
    "Defne Arslan": {"temel": 70.0, "devamsizlik": 0.030},
    # 5-A
    "Deniz Aktaş": {"temel": 79.0, "devamsizlik": 0.030},
    "Ece Polat": {"temel": 60.0, "devamsizlik": 0.070, "egilim": 0.0},
    "Burak Çelik": {"temel": 77.0, "devamsizlik": 0.020},
    "Mira Koç": {"temel": 78.0, "devamsizlik": 0.025},
    "Yusuf Kara": {"temel": 74.0, "devamsizlik": 0.030},
    "Elif Çelik": {"temel": 72.0, "devamsizlik": 0.028},
    # 6-C
    "Mert Yıldız": {"temel": 75.0},
    "Ayşe Doğan": {"temel": 80.0},
    "Kerem Özkan": {"temel": 56.0, "devamsizlik": 0.050},
    "Nehir Aksoy": {"temel": 72.0},
    "Can Erdem": {"temel": 68.0},
    "İrem Kurt": {"temel": 77.0},
    # 11-A
    "Barış Güneş": {"temel": 70.0},
    "Zehra Tunç": {"temel": 82.0},
    "Onur Keskin": {"temel": 64.0},
    "Melis Uçar": {"temel": 74.0},
    "Efe Bulut": {"temel": 62.0},
    "Duru Avcı": {"temel": 78.0},
    # 12-B
    "Arda Korkmaz": {"temel": 71.0},
    "Naz Eren": {"temel": 83.0},
    "Kaan Sezer": {"temel": 64.0},
    "Ela Yavuz": {"temel": 76.0},
    "Tuna Karaca": {"temel": 57.0},
    "Ceren Altın": {"temel": 45.0, "mazeretsiz_hedef": 10, "egilim": -1.0},
}

# Mazeretli devamsızlık küme uzunlukları (1-4 gün) ve ağırlıkları.
_MAZERET_UZUNLUK = (1, 2, 3, 4)
_MAZERET_AGIRLIK = (3, 4, 2, 1)
MAZERETLI_KUME_UST_SINIR = 3
_KUME_DENEME = 200

# Ortaöğretim sınıflarında yıl sonu mazeretsiz gün sayısı bu sınırı geçemez.
ORTAOGRETIM_SINIFLARI = ("9-A", "10-B", "11-A", "12-B")
YIL_SONU_MAZERETSIZ_UST_SINIR = 10


# ---------------------------------------------------------------- üretim


def _mevcut_kayitlar() -> dict[str, Any]:
    """Mevcut dosyadan yalnız ilk 12 öğrenci, 2 öğretmen ve hesaplar alınır."""
    with MEVCUT_VERI.open(encoding="utf-8") as handle:
        veri = json.load(handle)
    return {
        "teachers": [r for r in veri["teachers"] if r["id"] <= MEVCUT_OGRETMEN_SAYISI],
        "students": [r for r in veri["students"] if r["id"] <= MEVCUT_OGRENCI_SAYISI],
        "users": veri["users"],
    }


def _ogrenciler_ve_ogretmenler(
    mevcut: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ogretmenler = [dict(r) for r in mevcut["teachers"]]
    ogrenciler = [dict(r) for r in mevcut["students"]]
    adlar = {r["name"] for r in ogrenciler}
    for sinif, adlari in YENI_OGRENCILER:
        for ad in adlari:
            if ad in adlar:
                raise SystemExit(f"Yeni öğrenci adı mevcut bir öğrenciyle çakışıyor: {ad}")
            adlar.add(ad)
            ogrenciler.append(
                {"id": len(ogrenciler) + 1, "name": ad, "class_name": sinif, "parent_id": None}
            )
    for ad, sinif in YENI_OGRETMENLER:
        ogretmenler.append({"id": len(ogretmenler) + 1, "name": ad, "class_name": sinif})
    eksik = [r["name"] for r in ogrenciler if r["name"] not in PROFILLER]
    if eksik:
        raise SystemExit(f"Profili olmayan öğrenci: {eksik}")
    return ogrenciler, ogretmenler


def _rastgele_profiller(
    rng: random.Random, ogrenciler: list[dict[str, Any]]
) -> dict[int, dict[str, Any]]:
    """Her öğrenci için sabit sırayla rastgele değerler çeker, sonra profille ezer."""
    sonuc: dict[int, dict[str, Any]] = {}
    for ogr in ogrenciler:
        profil = {
            "temel": rng.gauss(72.0, 7.0),
            "pencere_sd": rng.uniform(4.0, 7.0),
            "egilim": rng.uniform(-3.0, 3.0),
            "ders_sapma": {ders: rng.gauss(0.0, 3.0) for ders in DERSLER},
            "devamsizlik": rng.uniform(0.015, 0.040),
            "faz": rng.random(),
            "mazeret": rng.uniform(0.008, 0.020),
        }
        ozel = PROFILLER[ogr["name"]]
        for anahtar in ("temel", "pencere_sd", "egilim", "devamsizlik", "faz", "mazeret"):
            if anahtar in ozel:
                profil[anahtar] = ozel[anahtar]
        for ders, fark in ozel.get("ders_ozel", {}).items():
            profil["ders_sapma"][ders] += fark
        sonuc[ogr["id"]] = profil
    return sonuc


def _sinavlar(rng: random.Random, siniflar: list[str]) -> dict[tuple[str, str, int], date]:
    """Sınıf-ders-pencere başına tek okul günü seçer."""
    gunler = [
        takvim.okul_gunleri(baslangic, bitis) for baslangic, bitis in NOT_PENCERELERI
    ]
    for pencere, liste in enumerate(gunler):
        if not liste:
            raise SystemExit(f"Not penceresinde okul günü yok: {NOT_PENCERELERI[pencere]}")
    sonuc: dict[tuple[str, str, int], date] = {}
    for sinif in siniflar:
        for ders in DERSLER:
            for pencere, liste in enumerate(gunler):
                sonuc[(sinif, ders, pencere)] = liste[rng.randrange(len(liste))]
    return sonuc


def _notlar(
    rng: random.Random,
    ogrenciler: list[dict[str, Any]],
    profiller: dict[int, dict[str, Any]],
    sinavlar: dict[tuple[str, str, int], date],
) -> list[dict[str, Any]]:
    satirlar: list[dict[str, Any]] = []
    son = len(NOT_PENCERELERI) - 1
    for ogr in ogrenciler:
        profil = profiller[ogr["id"]]
        for ders in DERSLER:
            for pencere in range(len(NOT_PENCERELERI)):
                egilim = profil["egilim"] * (pencere / son - 0.5)
                ham = (
                    profil["temel"]
                    + profil["ders_sapma"][ders]
                    + egilim
                    + rng.gauss(0.0, profil["pencere_sd"])
                )
                deger = round(min(100.0, max(0.0, ham)), 2)
                tarih = sinavlar[(ogr["class_name"], ders, pencere)]
                satirlar.append(
                    {
                        "id": len(satirlar) + 1,
                        "student_id": ogr["id"],
                        "subject": ders,
                        "grade": deger,
                        "date": tarih.isoformat(),
                    }
                )
    return satirlar


def _devamsizlik_parametreleri(
    ogrenciler: list[dict[str, Any]],
    profiller: dict[int, dict[str, Any]],
    gun_sayisi: int,
) -> None:
    """Her profile mazeretsiz_hedef ve mazeretli_kume yazar; rastgele sayı çekmez.

    Profilde verilmişse o değer, verilmemişse günlük orandan türetilen değer
    kullanılır. Ortaöğretim sınıflarında türetilen hedef üst sınırla kısılır;
    verilen hedef sınırı aşarsa hata verilir.
    """
    for ogr in ogrenciler:
        profil = profiller[ogr["id"]]
        ozel = PROFILLER[ogr["name"]]
        ortaogretim = ogr["class_name"] in ORTAOGRETIM_SINIFLARI
        if "mazeretsiz_hedef" in ozel:
            hedef = int(ozel["mazeretsiz_hedef"])
        else:
            hedef = round(profil["devamsizlik"] * gun_sayisi)
            if ortaogretim:
                hedef = min(hedef, YIL_SONU_MAZERETSIZ_UST_SINIR)
        if "mazeretli_kume" in ozel:
            kume = int(ozel["mazeretli_kume"])
        else:
            kume = min(MAZERETLI_KUME_UST_SINIR, round(profil["mazeret"] * gun_sayisi))
        if not 0 <= hedef <= gun_sayisi:
            raise SystemExit(f"mazeretsiz_hedef aralık dışı: {ogr['name']} {hedef}")
        if ortaogretim and hedef > YIL_SONU_MAZERETSIZ_UST_SINIR:
            raise SystemExit(f"mazeretsiz_hedef ortaöğretim sınırını aşıyor: {ogr['name']} {hedef}")
        if not 0 <= kume <= MAZERETLI_KUME_UST_SINIR:
            raise SystemExit(f"mazeretli_kume aralık dışı: {ogr['name']} {kume}")
        profil["mazeretsiz_hedef"] = hedef
        profil["mazeretli_kume"] = kume


def _en_yakin_bos_sira(dolu: set[int], sira: int, n: int) -> int:
    """sira doluysa ona en yakın boş sırayı (önce ileri, sonra geri) verir."""
    for uzaklik in range(n):
        for aday in (sira + uzaklik, sira - uzaklik):
            if 0 <= aday < n and aday not in dolu:
                return aday
    raise SystemExit("Boş okul günü kalmadı")


def _mazeretsiz_gunler(rng: random.Random, n: int, hedef: int, faz: float) -> set[int]:
    """Yıla düzenli aralıkla dağılmış, ±2 gün kaydırılmış tam hedef sayıda gün sırası."""
    if hedef > n:
        raise SystemExit(f"mazeretsiz_hedef gün sayısından büyük: {hedef} > {n}")
    secilen: set[int] = set()
    for k in range(hedef):
        taban = int((k + faz) * n / hedef)
        sira = min(max(taban + rng.randint(-2, 2), 0), n - 1)
        secilen.add(_en_yakin_bos_sira(secilen, sira, n))
    return secilen


def _mazeretli_kumeler(rng: random.Random, liste: list[str], kume: int) -> None:
    """liste üzerine kume adet mazeretli küme yazar (yerinde).

    Küme yalnızca "present" günlere ve komşusu da "present" olan günlere konur;
    böylece mazeretsiz günlerle çakışmaz ve kümeler birleşmez.
    """
    n = len(liste)
    for _ in range(kume):
        uzunluk = rng.choices(_MAZERET_UZUNLUK, weights=_MAZERET_AGIRLIK)[0]
        for _deneme in range(_KUME_DENEME):
            bas = rng.randrange(0, n - uzunluk + 1)
            alan = range(max(bas - 1, 0), min(bas + uzunluk + 1, n))
            if all(liste[sira] == "present" for sira in alan):
                for sira in range(bas, bas + uzunluk):
                    liste[sira] = "excused"
                break
        else:
            raise SystemExit("Mazeretli küme için uygun yer bulunamadı")


def _ogrenci_devamsizligi(
    rng: random.Random, n: int, profil: dict[str, Any]
) -> list[str]:
    """Bir öğrencinin okul günü başına durum listesi; tüm öğrenciler için aynı kod."""
    liste = ["present"] * n
    for sira in _mazeretsiz_gunler(rng, n, profil["mazeretsiz_hedef"], profil["faz"]):
        liste[sira] = "absent"
    _mazeretli_kumeler(rng, liste, profil["mazeretli_kume"])
    return liste


def _devam(
    rng: random.Random,
    ogrenciler: list[dict[str, Any]],
    profiller: dict[int, dict[str, Any]],
    gunler: list[date],
) -> list[dict[str, Any]]:
    n = len(gunler)
    durumlar = {
        ogr["id"]: _ogrenci_devamsizligi(rng, n, profiller[ogr["id"]])
        for ogr in ogrenciler
    }
    satirlar: list[dict[str, Any]] = []
    for sira, gun in enumerate(gunler):
        for ogr in ogrenciler:
            satirlar.append(
                {
                    "id": len(satirlar) + 1,
                    "student_id": ogr["id"],
                    "date": gun.isoformat(),
                    "status": durumlar[ogr["id"]][sira],
                }
            )
    return satirlar


def uret() -> dict[str, Any]:
    """Tüm mock veriyi bellekte üretir; dosyaya yazmaz."""
    rng = random.Random(TOHUM)
    mevcut = _mevcut_kayitlar()
    ogrenciler, ogretmenler = _ogrenciler_ve_ogretmenler(mevcut)
    profiller = _rastgele_profiller(rng, ogrenciler)
    siniflar = list(dict.fromkeys(r["class_name"] for r in ogrenciler))
    sinavlar = _sinavlar(rng, siniflar)
    notlar = _notlar(rng, ogrenciler, profiller, sinavlar)
    gunler = takvim.okul_gunleri(takvim.DONEM_1_BASLANGIC, takvim.DONEM_2_BITIS)
    _devamsizlik_parametreleri(ogrenciler, profiller, len(gunler))
    devam = _devam(rng, ogrenciler, profiller, gunler)
    return {
        "teachers": ogretmenler,
        "students": ogrenciler,
        "users": [dict(r) for r in mevcut["users"]],
        "grades": notlar,
        "attendance": devam,
    }


def serilestir(veri: dict[str, Any]) -> bytes:
    """export_mock_data.py ile aynı biçim: UTF-8, 2 boşluk girinti, son satır sonu."""
    metin = json.dumps(veri, ensure_ascii=False, indent=2) + "\n"
    return metin.encode("utf-8")


def md5(icerik: bytes) -> str:
    return hashlib.md5(icerik).hexdigest()


# ---------------------------------------------------------------- kontrol


def gun_verisi(veri: dict[str, Any], gun: date) -> dict[str, list[dict[str, Any]]]:
    """Kontrol gününe (dahil) kadarki not ve devamsızlık satırları."""
    sinir = gun.isoformat()
    return {
        "grades": [r for r in veri["grades"] if r["date"] <= sinir],
        "attendance": [r for r in veri["attendance"] if r["date"] <= sinir],
    }


def _ortalama(degerler: list[float]) -> float:
    return sum(degerler) / len(degerler)


def kontrol_raporu(veri: dict[str, Any], gun: date) -> dict[str, Any]:
    """Bir kontrol gününün sayıları ve hikâye koşulları (risk.py ile)."""
    parca = gun_verisi(veri, gun)
    ogrenciler = veri["students"]
    ad_id = {r["name"]: r["id"] for r in ogrenciler}
    sinif_of = {r["id"]: r["class_name"] for r in ogrenciler}

    not_listesi: dict[int, list[float]] = {}
    ders_listesi: dict[tuple[int, str], list[float]] = {}
    for r in parca["grades"]:
        not_listesi.setdefault(r["student_id"], []).append(r["grade"])
        ders_listesi.setdefault((r["student_id"], r["subject"]), []).append(r["grade"])
    ortalamalar = {sid: _ortalama(v) for sid, v in not_listesi.items()}

    mazeretsiz: dict[int, int] = {r["id"]: 0 for r in ogrenciler}
    mazeretli: dict[int, int] = {r["id"]: 0 for r in ogrenciler}
    for r in parca["attendance"]:
        if r["status"] == "absent":
            mazeretsiz[r["student_id"]] += 1
        elif r["status"] == "excused":
            mazeretli[r["student_id"]] += 1

    siniflar = list(dict.fromkeys(r["class_name"] for r in ogrenciler))
    sinif_ortalama = {
        s: _ortalama([ortalamalar[r["id"]] for r in ogrenciler if r["class_name"] == s])
        for s in siniflar
    }

    satirlar = assess_risk(ogrenciler, parca["grades"], parca["attendance"])
    bayrakli = sorted(r["name"] for r in satirlar if r["flagged"])
    bayrak = {r["name"]: r["flagged"] for r in satirlar}

    ali, zeynep = ad_id[ANA_OGRENCI], ad_id[RISKLI_OGRENCI]
    lina_ad, ece_ad = BAYRAKLI_OGRENCILER
    sinif_9a = [r["id"] for r in ogrenciler if r["class_name"] == "9-A"]
    sirali = sorted(sinif_9a, key=lambda sid: ortalamalar[sid], reverse=True)
    ali_sira = sirali.index(ali) + 1
    ali_dersler = {d: _ortalama(ders_listesi[(ali, d)]) for d in DERSLER}
    zeynep_dersler = {d: _ortalama(ders_listesi[(zeynep, d)]) for d in DERSLER}
    digerleri = [sid for sid in sinif_9a if sid != ali]

    kosullar = {
        "ali_ust_yari": ali_sira <= len(sinif_9a) / 2,
        "ali_en_dusuk_ders_fizik": min(ali_dersler, key=ali_dersler.get) == "Fizik",
        "ali_en_cok_mazeretsiz": all(mazeretsiz[ali] > mazeretsiz[s] for s in digerleri),
        "ali_bayraksiz": not bayrak[ANA_OGRENCI],
        "zeynep_bayrakli": bayrak[RISKLI_OGRENCI],
        "lina_bayrakli": bayrak[lina_ad],
        "ece_bayrakli": bayrak[ece_ad],
        "zeynep_fizik_en_dusuk": min(zeynep_dersler, key=zeynep_dersler.get) == "Fizik"
        and sorted(zeynep_dersler.values())[0] < sorted(zeynep_dersler.values())[1],
        "zeynep_fizik_60_alti": zeynep_dersler["Fizik"] < 60,
    }
    return {
        "gun": gun,
        "sinif_ortalama": sinif_ortalama,
        "bayrakli": bayrakli,
        "ali_ortalama": ortalamalar[ali],
        "ali_mazeretsiz": mazeretsiz[ali],
        "ali_mazeretli": mazeretli[ali],
        "ali_sira": ali_sira,
        "zeynep_fizik": zeynep_dersler["Fizik"],
        "kosullar": kosullar,
        "sinif_of": sinif_of,
    }


def elli_alti(veri: dict[str, Any]) -> dict[str, Any]:
    """50 altı not sayısı, oranı, dağıldığı öğrenciler ve yeni sınıf yıl ortalamaları."""
    dusuk = [r for r in veri["grades"] if r["grade"] < 50]
    ogrenciler = sorted({r["student_id"] for r in dusuk})
    sinif_of = {r["id"]: r["class_name"] for r in veri["students"]}
    yillik: dict[int, list[float]] = {}
    for r in veri["grades"]:
        yillik.setdefault(r["student_id"], []).append(r["grade"])
    yeni_siniflar = set(YENI_SINIFLAR)
    yeni_altinda = sorted(
        sid
        for sid, v in yillik.items()
        if sinif_of[sid] in yeni_siniflar and _ortalama(v) < 50
    )
    return {
        "sayi": len(dusuk),
        "oran": len(dusuk) / len(veri["grades"]),
        "ogrenciler": ogrenciler,
        "yeni_sinif_ortalama_50_alti": yeni_altinda,
    }


def mazeretsiz_sayilari(veri: dict[str, Any], gun: date | None = None) -> dict[int, int]:
    """Öğrenci başına mazeretsiz devamsızlık günü; gun verilirse o güne kadar (dahil)."""
    sinir = None if gun is None else gun.isoformat()
    sayilar = {r["id"]: 0 for r in veri["students"]}
    for r in veri["attendance"]:
        if r["status"] == "absent" and (sinir is None or r["date"] <= sinir):
            sayilar[r["student_id"]] += 1
    return sayilar


def mazeretli_kume_uzunluklari(veri: dict[str, Any], student_id: int) -> list[int]:
    """Öğrencinin ardışık okul günlerindeki mazeretli kümelerinin uzunlukları."""
    uzunluklar: list[int] = []
    sayac = 0
    for r in veri["attendance"]:
        if r["student_id"] != student_id:
            continue
        if r["status"] == "excused":
            sayac += 1
        elif sayac:
            uzunluklar.append(sayac)
            sayac = 0
    if sayac:
        uzunluklar.append(sayac)
    return uzunluklar


def devamsizlik_hatalari(veri: dict[str, Any]) -> list[str]:
    """Ana öğrencinin devamsızlık profili ve ortaöğretim yıl sonu üst sınırı."""
    hatalar: list[str] = []
    ali = next(r["id"] for r in veri["students"] if r["name"] == ANA_OGRENCI)
    yil_sonu = mazeretsiz_sayilari(veri, KONTROL_GUNLERI[-1])
    if not 8 <= yil_sonu[ali] <= 9:
        hatalar.append(f"Ana öğrencinin yıl sonu mazeretsiz günü 8-9 değil: {yil_sonu[ali]}")
    for r in veri["students"]:
        kumeler = mazeretli_kume_uzunluklari(veri, r["id"])
        verilen = PROFILLER[r["name"]].get("mazeretli_kume")
        if verilen is not None and len(kumeler) != verilen:
            hatalar.append(
                f"Öğrenci {r['id']} mazeretli küme sayısı profildeki {verilen} değil: {len(kumeler)}"
            )
        if len(kumeler) > MAZERETLI_KUME_UST_SINIR or any(
            not 1 <= uzunluk <= 4 for uzunluk in kumeler
        ):
            hatalar.append(f"Öğrenci {r['id']} mazeretli kümeleri kurala uymuyor: {kumeler}")
    sinif_of = {r["id"]: r["class_name"] for r in veri["students"]}
    for sid, sayi in yil_sonu.items():
        if sinif_of[sid] in ORTAOGRETIM_SINIFLARI and sayi > YIL_SONU_MAZERETSIZ_UST_SINIR:
            hatalar.append(f"Öğrenci {sid} yıl sonu mazeretsiz {sayi} > {YIL_SONU_MAZERETSIZ_UST_SINIR}")
    return hatalar


def hikaye_hatalari(veri: dict[str, Any]) -> list[str]:
    """Sağlanmayan hikâye koşullarının listesi; boşsa hepsi sağlanıyor."""
    hatalar: list[str] = devamsizlik_hatalari(veri)
    for gun in KONTROL_GUNLERI:
        for ad, tamam in kontrol_raporu(veri, gun)["kosullar"].items():
            if not tamam:
                hatalar.append(f"{gun.isoformat()} {ad}")
    dusuk = elli_alti(veri)
    ad_id = {r["name"]: r["id"] for r in veri["students"]}
    if not 0.03 <= dusuk["oran"] <= 0.06:
        hatalar.append(f"50 altı oranı aralık dışı: {dusuk['oran']:.4f}")
    if len(dusuk["ogrenciler"]) < 4:
        hatalar.append("50 altı notlar 4'ten az öğrenciye dağılıyor")
    if ad_id[RISKLI_OGRENCI] not in dusuk["ogrenciler"]:
        hatalar.append("Riskli öğrencide 50 altı not yok")
    if not dusuk["yeni_sinif_ortalama_50_alti"]:
        hatalar.append("Yeni sınıflarda yıl ortalaması 50 altı öğrenci yok")
    return hatalar


# ---------------------------------------------------------------- çıktı


def _ekrana_yaz(veri: dict[str, Any], icerik: bytes, yol: Path) -> None:
    siniflar = list(dict.fromkeys(r["class_name"] for r in veri["students"]))
    okul_gunu = len({r["date"] for r in veri["attendance"]})
    print(f"Çıktı: {yol}")
    print(f"Öğrenci: {len(veri['students'])}")
    print(f"Sınıf: {len(siniflar)} ({', '.join(siniflar)})")
    print(f"Öğretmen: {len(veri['teachers'])}")
    print(f"Not: {len(veri['grades'])}")
    print(f"Devamsızlık kaydı: {len(veri['attendance'])} ({okul_gunu} okul günü)")
    for gun in KONTROL_GUNLERI:
        rapor = kontrol_raporu(veri, gun)
        print(f"\nKontrol günü {gun.isoformat()}")
        ortalamalar = ", ".join(f"{s} {v:.2f}" for s, v in rapor["sinif_ortalama"].items())
        print(f"  Sınıf ortalamaları: {ortalamalar}")
        print(f"  Bayraklı öğrenciler: {', '.join(rapor['bayrakli'])}")
        print(
            f"  Ana öğrenci: ortalama {rapor['ali_ortalama']:.2f}, 9-A sırası {rapor['ali_sira']}/6, "
            f"mazeretsiz {rapor['ali_mazeretsiz']}, mazeretli {rapor['ali_mazeretli']}"
        )
    print("\nYıl sonu devamsızlık (öğrenci, sınıf, mazeretsiz gün, mazeretli küme sayısı)")
    yil_sonu = mazeretsiz_sayilari(veri, KONTROL_GUNLERI[-1])
    for r in veri["students"]:
        kumeler = mazeretli_kume_uzunluklari(veri, r["id"])
        print(f"  {r['name']:<16} {r['class_name']:<5} {yil_sonu[r['id']]:>3} {len(kumeler):>2} {kumeler}")
    dusuk = elli_alti(veri)
    print(
        f"\n50 altı not: {dusuk['sayi']} (oran {dusuk['oran'] * 100:.2f}%), "
        f"{len(dusuk['ogrenciler'])} öğrenci"
    )
    print(f"md5: {md5(icerik)}")


def yaz(yol: Path = CIKTI) -> tuple[dict[str, Any], bytes]:
    veri = uret()
    icerik = serilestir(veri)
    yol.write_bytes(icerik)
    return veri, icerik


def main() -> int:
    veri = uret()
    hatalar = hikaye_hatalari(veri)
    if hatalar:
        print("Hikâye koşulları sağlanmadı; dosya yazılmadı:")
        for hata in hatalar:
            print(f"  - {hata}")
        return 1
    icerik = serilestir(veri)
    CIKTI.write_bytes(icerik)
    _ekrana_yaz(veri, icerik, CIKTI)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
