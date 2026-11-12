"""Zaman kapısı: "bugün"den sonraki not ve devamsızlık kayıtları hiçbir rolde görünmez.

RLS politikaları school_app oturumunda app.today ayarına bakar. Ayar yoksa
satır gelmez. Beklenen sayılar mock_data.json'dan hesaplanır.
"""

import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.core import bugun as bugun_modulu
from backend.app.core.access_context import set_access_context
from backend.app.core.bugun import bugun
from backend.app.core.database import AppSessionLocal
from backend.tests import mock_veri
from config.settings import settings
from database.enable_rls import enable_rls

_GUN = date(2026, 11, 3)
_ROLLER = [
    ("principal", None, None),
    ("teacher", "9-A", 1),
    ("parent", None, 1),
    ("student", None, 1),
]


@pytest.fixture(scope="module", autouse=True)
def _politikalar_kurulu() -> None:
    enable_rls()


def _sayilar(ayarlar: dict[str, str], tablo: str) -> tuple[int, int, date | None]:
    """Ham ayarlarla school_app oturumunda (satır, bugünden sonraki satır, son tarih)."""
    db = AppSessionLocal()
    try:
        db.connection()
        tum = {"app.class": "", "app.student_id": "", **ayarlar}
        for ad, deger in tum.items():
            db.execute(text("SELECT set_config(:ad, :deger, true)"), {"ad": ad, "deger": deger})
        toplam, son = db.execute(text(f"SELECT COUNT(*), MAX(date) FROM {tablo}")).one()
        sonrasi = db.execute(
            text(f"SELECT COUNT(*) FROM {tablo} WHERE date > CAST(:gun AS date)"),
            {"gun": _GUN.isoformat()},
        ).scalar_one()
        return toplam, sonrasi, son
    finally:
        db.close()


@pytest.mark.parametrize("tablo", ["grades", "attendance"])
def test_bugun_ayarsizken_satir_gorunmez(tablo: str) -> None:
    toplam, _, son = _sayilar({"app.role": "principal"}, tablo)
    assert toplam == 0
    assert son is None


@pytest.mark.parametrize("tablo", ["grades", "attendance"])
def test_bugun_bosken_satir_gorunmez(tablo: str) -> None:
    toplam, _, _ = _sayilar({"app.role": "principal", "app.today": ""}, tablo)
    assert toplam == 0


@pytest.mark.parametrize("tablo", ["grades", "attendance"])
def test_bugunden_sonraki_kayit_gorunmez(tablo: str) -> None:
    toplam, sonrasi, son = _sayilar(
        {"app.role": "principal", "app.today": _GUN.isoformat()}, tablo
    )
    notlar, devam = mock_veri.gune_kadar(_GUN)
    beklenen = len(notlar if tablo == "grades" else devam)
    gelecek_not, gelecek_devam = mock_veri.gelecek_kayitlar(_GUN)
    assert (gelecek_not if tablo == "grades" else gelecek_devam)  # mock gelecek kayıt taşır
    assert sonrasi == 0
    assert son is not None and son <= _GUN
    assert toplam == beklenen


@pytest.mark.parametrize("tablo", ["grades", "attendance"])
def test_bugun_gunu_dahildir(tablo: str) -> None:
    """Tam bugünün tarihli kaydı görünür (<=)."""
    tarihler = [
        r["date"]
        for r in mock_veri.yukle()[tablo]
        if r["date"] <= _GUN.isoformat()
    ]
    son_gun = date.fromisoformat(max(tarihler))
    _, _, son = _sayilar({"app.role": "principal", "app.today": son_gun.isoformat()}, tablo)
    assert son == son_gun


@pytest.mark.parametrize(("rol", "sinif", "ogrenci"), _ROLLER)
def test_her_rolde_bugunden_sonrasi_gorunmez(
    monkeypatch: pytest.MonkeyPatch, rol: str, sinif: str | None, ogrenci: int | None
) -> None:
    monkeypatch.setattr(settings, "DEMO_TODAY", _GUN)
    gorunen = {
        r["id"]
        for r in mock_veri.yukle()["students"]
        if (rol == "principal")
        or (rol == "teacher" and r["class_name"] == sinif)
        or (rol in ("parent", "student") and r["id"] == ogrenci)
    }
    notlar, devam = mock_veri.gune_kadar(_GUN)
    beklenen = {
        "grades": sum(1 for r in notlar if r["student_id"] in gorunen),
        "attendance": sum(1 for r in devam if r["student_id"] in gorunen),
    }
    db = AppSessionLocal()
    try:
        db.connection()
        set_access_context(db, rol, sinif, ogrenci)
        for tablo in ("grades", "attendance"):
            toplam, son = db.execute(
                text(f"SELECT COUNT(*), MAX(date) FROM {tablo}")
            ).one()
            assert toplam == beklenen[tablo], tablo
            assert son is not None and son <= _GUN, tablo
    finally:
        db.close()


def test_set_access_context_app_today_yazar(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "DEMO_TODAY", _GUN)
    db = AppSessionLocal()
    try:
        db.connection()
        set_access_context(db, "principal", None, None)
        deger = db.execute(text("SELECT current_setting('app.today', true)")).scalar_one()
        assert deger == _GUN.isoformat()
    finally:
        db.close()


def test_bugun_demo_tarihini_kullanir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "DEMO_TODAY", date(2027, 1, 27))
    assert bugun() == date(2027, 1, 27)


def test_bugun_demo_yokken_istanbul_gunu(monkeypatch: pytest.MonkeyPatch) -> None:
    """UTC 23:30 İstanbul'da ertesi gündür (UTC+3)."""

    class _Sabit(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2030, 1, 2, 23, 30, tzinfo=ZoneInfo("UTC")).astimezone(tz)

    monkeypatch.setattr(settings, "DEMO_TODAY", None)
    monkeypatch.setattr(bugun_modulu, "datetime", _Sabit)
    assert bugun() == date(2030, 1, 3)


def test_demo_today_bos_deger_none_olur() -> None:
    from config.settings import Settings

    ortak = dict(
        SECRET_KEY="x",
        DATABASE_URL="postgresql://a",
        APP_DATABASE_URL="postgresql://b",
        LLM_MODEL="m",
        _env_file=None,
    )
    assert Settings(**ortak).DEMO_TODAY is None
    assert Settings(DEMO_TODAY="", **ortak).DEMO_TODAY is None
    assert Settings(DEMO_TODAY="2026-11-03", **ortak).DEMO_TODAY == date(2026, 11, 3)
