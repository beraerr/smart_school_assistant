"""Dönemlik risk: pencere takvimdeki döneme göre seçilir, kural değişmez.

Beklenen satırlar mock_data.json'dan ve sabit günlerden hesaplanır; yanıt
bununla birebir karşılaştırılır.
"""

import sys
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.main import app
from backend.app.services import takvim
from backend.tests import mock_veri
from config.settings import settings

client = TestClient(app)

# gün, takvim durumu, beklenen pencere (başlangıç, bitiş) ya da None.
_GUNLER = [
    (date(2026, 11, 3), "donem_1", (date(2026, 9, 14), date(2026, 11, 3))),
    (date(2027, 1, 27), "yariyil", (date(2026, 9, 14), date(2027, 1, 22))),
    (date(2027, 4, 15), "donem_2", (date(2027, 2, 8), date(2027, 4, 15))),
    (date(2027, 7, 10), "yaz", (date(2027, 2, 8), date(2027, 6, 25))),
    (date(2026, 9, 10), "okul_oncesi", None),
    # Ara tatiller içinde bulunulan dönemin penceresini bugüne kadar uzatır.
    (date(2026, 11, 18), "ara_tatil_1", (date(2026, 9, 14), date(2026, 11, 18))),
    (date(2027, 3, 10), "ara_tatil_2", (date(2027, 2, 8), date(2027, 3, 10))),
]


@pytest.mark.parametrize(("gun", "durum", "pencere"), _GUNLER)
def test_risk_penceresi_donem_durumuna_gore(
    gun: date, durum: str, pencere: tuple[date, date] | None
) -> None:
    assert takvim.donem_durumu(gun)["durum"] == durum
    assert takvim.risk_penceresi(gun) == pencere


def _giris(username: str, parola: str) -> str:
    response = client.post("/auth/login", json={"username": username, "password": parola})
    assert response.status_code == 200
    return response.json()["access_token"]


def _risk(token: str, sinif: str | None = None):
    return client.get(
        "/risk",
        headers={"Authorization": f"Bearer {token}"},
        params={} if sinif is None else {"class_name": sinif},
    )


def _sirali(satirlar: list[dict]) -> list[dict]:
    return sorted(satirlar, key=lambda satir: satir["student_id"])


@pytest.mark.parametrize(("gun", "durum", "pencere"), _GUNLER)
def test_risk_yaniti_mock_pencere_hesabiyla_ayni(
    monkeypatch: pytest.MonkeyPatch,
    gun: date,
    durum: str,
    pencere: tuple[date, date] | None,
) -> None:
    del durum
    monkeypatch.setattr(settings, "DEMO_TODAY", gun)
    yanit = _risk(_giris("principal", "admin123"))
    assert yanit.status_code == 200
    beklenen = mock_veri.risk_beklenen(gun)
    if pencere is None:
        assert yanit.json() == []
        assert beklenen == []
        return
    assert _sirali(yanit.json()) == _sirali(beklenen)


@pytest.mark.parametrize(("gun", "durum", "pencere"), _GUNLER)
def test_ogretmen_kendi_sinifini_pencereyle_gorur(
    monkeypatch: pytest.MonkeyPatch,
    gun: date,
    durum: str,
    pencere: tuple[date, date] | None,
) -> None:
    del durum
    monkeypatch.setattr(settings, "DEMO_TODAY", gun)
    yanit = _risk(_giris("teacher1", "teacher123"))
    assert yanit.status_code == 200
    if pencere is None:
        assert yanit.json() == []
        return
    assert _sirali(yanit.json()) == _sirali(mock_veri.risk_beklenen(gun, "9-A"))


def test_pencere_disi_not_ve_devamsizlik_hesaba_girmez(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """2027-04-15'te yalnız 2. dönem satırları sayılır; 1. dönem girmez."""
    gun = date(2027, 4, 15)
    monkeypatch.setattr(settings, "DEMO_TODAY", gun)
    satirlar = _risk(_giris("principal", "admin123")).json()
    veri = mock_veri.yukle()
    for satir in satirlar:
        sid = satir["student_id"]
        mazeretsiz = [
            r
            for r in veri["attendance"]
            if r["student_id"] == sid
            and r["status"] == "absent"
            and "2027-02-08" <= r["date"] <= gun.isoformat()
        ]
        assert satir["unexcused_absences"] == len(mazeretsiz)
        notlar = [
            r["grade"]
            for r in veri["grades"]
            if r["student_id"] == sid and "2027-02-08" <= r["date"] <= gun.isoformat()
        ]
        if notlar:
            assert satir["grade_average"] == pytest.approx(
                sum(notlar) / len(notlar), abs=0.005
            )
        else:
            assert satir["grade_average"] is None
