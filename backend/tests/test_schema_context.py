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
)

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
        "toplam devamsızlık = students.total_absences; ayrıntı = attendance (status)"
        in metin
    )
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
    assert ayar.REFERENCE_DATE == ""


def test_referans_tarihi_ve_veri_araligi(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "backend.app.services.schema_context.settings.REFERENCE_DATE",
        "2026-10-01",
    )
    metin = build_schema_context()
    assert "Bugünün tarihi: 2026-10-01." in metin
    assert "Veri aralığı: 2026-08-26–2026-10-25." in metin
    assert (
        "'dün', 'bu hafta', 'bu ay', 'geçen ay' gibi ifadeler bu tarihe göre yorumlanır; "
        "tarih aralıklarını SQL'e yaz."
    ) in metin
    assert 'Veri aralığı dışında kalan dönemde "o dönemde kayıt yok" de.' in metin


def test_referans_tarihi_bosken_bugun(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Sabit(date):
        @classmethod
        def today(cls):
            return cls(2024, 3, 4)

    monkeypatch.setattr("backend.app.services.schema_context.date", _Sabit)
    monkeypatch.setattr("backend.app.services.schema_context.settings.REFERENCE_DATE", "  ")
    metin = build_schema_context()
    assert "Bugünün tarihi: 2024-03-04." in metin
