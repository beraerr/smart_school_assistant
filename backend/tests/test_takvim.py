"""2026-2027 okul takvimi: okul günü ve dönem durumu."""

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.services import takvim


@pytest.mark.parametrize(
    "gun",
    [
        date(2026, 10, 29),  # Cumhuriyet Bayramı
        date(2026, 11, 17),  # 1. dönem ara tatili
        date(2027, 1, 1),  # Yılbaşı
        date(2027, 1, 27),  # yarıyıl tatili
        date(2027, 3, 10),  # ara tatil + Ramazan Bayramı
        date(2027, 4, 23),  # Ulusal Egemenlik ve Çocuk Bayramı
        date(2027, 5, 18),  # Kurban Bayramı
        date(2027, 5, 19),  # Kurban Bayramı + Gençlik ve Spor Bayramı
        date(2026, 9, 19),  # cumartesi
        date(2026, 9, 13),  # dönem öncesi pazar
        date(2027, 6, 28),  # dönem sonrası pazartesi
    ],
)
def test_okul_gunu_degil(gun: date) -> None:
    assert takvim.okul_gunu_mu(gun) is False


@pytest.mark.parametrize(
    "gun",
    [
        date(2026, 9, 14),
        date(2026, 11, 3),
        date(2027, 2, 8),
        date(2027, 6, 25),
        date(2026, 10, 28),  # arife yarım günü okul günüdür
    ],
)
def test_okul_gunu(gun: date) -> None:
    assert takvim.okul_gunu_mu(gun) is True


@pytest.mark.parametrize(
    ("gun", "kod"),
    [
        (date(2026, 9, 11), "okul_oncesi"),
        (date(2026, 11, 3), "donem_1"),
        (date(2026, 11, 18), "ara_tatil_1"),
        (date(2027, 2, 1), "yariyil"),
        (date(2027, 3, 10), "ara_tatil_2"),
        (date(2027, 4, 15), "donem_2"),
        (date(2027, 7, 10), "yaz"),
    ],
)
def test_donem_durumu_kodu(gun: date, kod: str) -> None:
    durum = takvim.donem_durumu(gun)
    assert durum["durum"] == kod
    assert set(durum) == {"durum", "ad_tr", "ad_en", "baslangic", "bitis"}
    assert durum["ad_tr"] and durum["ad_en"]


def test_hafta_sonu_ve_resmi_tatil_donem_kodunu_degistirmez() -> None:
    assert takvim.donem_durumu(date(2026, 11, 7))["durum"] == "donem_1"  # cumartesi
    assert takvim.donem_durumu(date(2026, 10, 29))["durum"] == "donem_1"
    assert takvim.donem_durumu(date(2027, 4, 23))["durum"] == "donem_2"
    assert takvim.donem_durumu(date(2027, 5, 19))["durum"] == "donem_2"
    assert takvim.donem_durumu(date(2027, 1, 23))["durum"] == "yariyil"
    assert takvim.donem_durumu(date(2027, 6, 26))["durum"] == "yaz"


def test_donem_sinirlari() -> None:
    assert takvim.donem_durumu(date(2026, 9, 14))["durum"] == "donem_1"
    assert takvim.donem_durumu(date(2027, 1, 22))["durum"] == "donem_1"
    assert takvim.donem_durumu(date(2027, 1, 25))["durum"] == "yariyil"
    assert takvim.donem_durumu(date(2027, 2, 5))["durum"] == "yariyil"
    assert takvim.donem_durumu(date(2027, 2, 8))["durum"] == "donem_2"
    assert takvim.donem_durumu(date(2027, 6, 25))["durum"] == "donem_2"
    assert takvim.donem_durumu(date(2026, 11, 20))["durum"] == "ara_tatil_1"
    assert takvim.donem_durumu(date(2026, 11, 23))["durum"] == "donem_1"


def test_donem_durumu_tarihleri() -> None:
    durum = takvim.donem_durumu(date(2026, 11, 3))
    assert durum["baslangic"] == date(2026, 9, 14)
    assert durum["bitis"] == date(2027, 1, 22)
    durum = takvim.donem_durumu(date(2026, 11, 18))
    assert (durum["baslangic"], durum["bitis"]) == (date(2026, 11, 16), date(2026, 11, 20))


def test_okul_gunleri_aralik() -> None:
    gunler = takvim.okul_gunleri(date(2026, 10, 26), date(2026, 11, 2))
    assert gunler == [
        date(2026, 10, 26),
        date(2026, 10, 27),
        date(2026, 10, 28),
        date(2026, 10, 30),
        date(2026, 11, 2),
    ]
    assert takvim.okul_gunleri(date(2026, 11, 3), date(2026, 11, 2)) == []
    assert takvim.okul_gunleri(date(2027, 1, 25), date(2027, 2, 5)) == []


def test_okul_gunleri_okul_gunu_mu_ile_tutarli() -> None:
    gunler = takvim.okul_gunleri(date(2026, 9, 1), date(2027, 7, 31))
    beklenen = [
        date(2026, 9, 1) + timedelta(days=i)
        for i in range((date(2027, 7, 31) - date(2026, 9, 1)).days + 1)
        if takvim.okul_gunu_mu(date(2026, 9, 1) + timedelta(days=i))
    ]
    assert gunler == beklenen
    assert gunler == sorted(gunler)
    assert gunler[0] == date(2026, 9, 14)
    assert gunler[-1] == date(2027, 6, 25)


def test_ozet_tr_kisa_ve_dolu() -> None:
    metin = takvim.ozet_tr()
    assert isinstance(metin, str)
    assert "14 Eylül 2026" in metin
    assert "25 Haziran 2027" in metin
    assert "Kurban Bayramı" in metin
    assert len(metin) < 1500


def test_ozet_en_ozet_tr_ile_ayni_icerik() -> None:
    metin = takvim.ozet_en()
    assert "September 14, 2026" in metin
    assert "June 25, 2027" in metin
    assert "November 16, 2026 – November 20, 2026" in metin
    assert "Feast of Sacrifice Holiday" in metin
    assert len(metin) < 1500
    # Türkçe ay ve tatil adı sızmamalı.
    for ad in ("Eylül", "Bayramı", "Haziran", "Yılbaşı"):
        assert ad not in metin


def test_her_resmi_tatilin_ingilizce_adi_var() -> None:
    for _, _, ad in takvim.RESMI_TATILLER:
        assert ad in takvim._RESMI_TATIL_EN
    assert len(takvim._RESMI_TATIL_EN) == len({ad for _, _, ad in takvim.RESMI_TATILLER})
