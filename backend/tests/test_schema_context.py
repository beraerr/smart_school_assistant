"""Şema özeti açılışta okunur, önbelleğe alınır, öğrenci kimliği taşımaz."""

import sys
from datetime import date
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.services.schema_context import (
    build_schema_context,
    reset_schema_context,
    veri_araligi,
)
from backend.tests import mock_veri

_YOK = (
    "Ders programı, veli toplantısı, servis, "
    "iletişim bilgisi veritabanında YOKTUR."
)


@pytest.fixture(autouse=True)
def _temiz_onbellek():
    reset_schema_context()
    yield
    reset_schema_context()


def test_sema_ozeti_kimlik_tasimaz() -> None:
    metin = build_schema_context()
    assert _YOK in metin
    assert "Matematik" in metin
    assert "9-A" in metin
    assert "present" in metin
    assert (
        "devamsızlık = attendance tablosu; status='absent' mazeretsiz, "
        "status='excused' mazeretli (ayrı say)"
    ) in metin
    assert "total_absences" not in metin
    assert "Yılmaz" not in metin
    assert "Ali" not in metin


def test_sema_ozeti_bir_kez_okunur(monkeypatch: pytest.MonkeyPatch) -> None:
    ilk = build_schema_context()

    def _yasak():
        raise AssertionError("ikinci okuma")

    monkeypatch.setattr(
        "backend.app.services.schema_context.SessionLocal",
        _yasak,
    )
    assert build_schema_context() == ilk


def test_gecme_notu_yonetmelikte(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("backend.app.services.schema_context.settings.PASS_GRADE", 50)
    monkeypatch.setattr("backend.app.services.schema_context.settings.GRADE_LABELS", "")
    metin = build_schema_context()
    assert "Okul yönetmeliği: 100'lük sistemde ders geçme notu 50'dir." in metin
    assert "Sınıf geçme için ek kurallar vardır" in metin
    assert "sınıf öğretmeni veya okul idaresiyle görüşmeyi öner" in metin
    assert "5'lik veya harf dönüşümü yapma" in metin
    assert "Geçme notu" not in metin


def test_gecme_notu_ayardan_gelir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("backend.app.services.schema_context.settings.PASS_GRADE", 60)
    monkeypatch.setattr(
        "backend.app.services.schema_context.settings.GRADE_LABELS",
        "85-100=5, 70-84=4",
    )
    metin = build_schema_context()
    assert "ders geçme notu 60" in metin
    assert "85-100=5, 70-84=4" in metin
    assert "5'lik veya harf dönüşümü yapma" not in metin


def test_varsayilan_ayarlar() -> None:
    from config.settings import Settings

    ayar = Settings(
        SECRET_KEY="x",
        DATABASE_URL="postgresql://a",
        APP_DATABASE_URL="postgresql://b",
        LLM_MODEL="m",
        _env_file=None,
    )
    assert ayar.PASS_GRADE == 50
    assert ayar.GRADE_LABELS == ""
    assert ayar.DEMO_TODAY is None


def test_ozet_bugunun_tarihini_tasimaz(monkeypatch: pytest.MonkeyPatch) -> None:
    """Önbellekteki özet tarih taşımaz; tarih her istekte Tarih bloğundan gelir."""
    monkeypatch.setattr(
        "backend.app.services.schema_context.settings.DEMO_TODAY", date(2026, 11, 3)
    )
    metin = build_schema_context()
    assert "Bugünün tarihi" not in metin
    assert "2026-11-03" not in metin
    assert "gibi ifadeler bu tarihe göre yorumlanır" not in metin


def test_ozet_veri_tarih_araligi_tasimaz(monkeypatch: pytest.MonkeyPatch) -> None:
    """Min/max tarih özetten çıkar; ayrı bir değer olarak önbellekte tutulur."""
    monkeypatch.setattr(
        "backend.app.services.schema_context.settings.DEMO_TODAY", date(2030, 1, 1)
    )
    metin = build_schema_context()
    assert "Veri aralığı:" not in metin
    assert "grades.date aralığı" not in metin
    veri = mock_veri.yukle()
    for tarih in (
        min(r["date"] for r in veri["grades"] + veri["attendance"]),
        max(r["date"] for r in veri["grades"] + veri["attendance"]),
    ):
        assert tarih not in metin


def test_veri_araligi_mock_ile_ayni() -> None:
    veri = mock_veri.yukle()
    tarihler = [r["date"] for r in veri["grades"] + veri["attendance"]]
    assert veri_araligi() == (date.fromisoformat(min(tarihler)), date.fromisoformat(max(tarihler)))


def test_veri_araligi_bir_kez_okunur(monkeypatch: pytest.MonkeyPatch) -> None:
    ilk = veri_araligi()

    def _yasak():
        raise AssertionError("ikinci okuma")

    monkeypatch.setattr("backend.app.services.schema_context.SessionLocal", _yasak)
    assert veri_araligi() == ilk
    assert veri_araligi() is veri_araligi()


def test_bugun_demo_yokken_istanbul_gunu(monkeypatch: pytest.MonkeyPatch) -> None:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from backend.app.core.bugun import bugun

    class _Sabit(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2024, 3, 4, 10, 0, tzinfo=ZoneInfo("UTC")).astimezone(tz)

    monkeypatch.setattr("backend.app.services.schema_context.settings.DEMO_TODAY", None)
    monkeypatch.setattr("backend.app.core.bugun.datetime", _Sabit)
    assert bugun() == date(2024, 3, 4)
    assert "2024-03-04" not in build_schema_context()
