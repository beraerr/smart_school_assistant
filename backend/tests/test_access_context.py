"""Kötü niyetli related_class değerinin SQL olarak çalışmadığını kanıtlar."""

import sys
from pathlib import Path

from sqlalchemy import text

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.core.access_context import set_access_context
from backend.app.core.database import AppSessionLocal, SessionLocal
from backend.tests import mock_veri

# Tırnak ve yorum işareti içeren değer. Parametre olarak giderse komut değildir.
_KOTU_SINIF = "9-A'; DROP TABLE students; --"


def test_kotu_niyetli_sinif_sorguyu_ve_tabloyu_bozmaz() -> None:
    """set_access_context sonrası öğrenci sayımı hata vermez; seed durur."""
    db = AppSessionLocal()
    try:
        db.connection()
        set_access_context(db, "teacher", _KOTU_SINIF, None)
        db.execute(text("SELECT COUNT(*) FROM students")).scalar_one()
    finally:
        db.close()

    admin = SessionLocal()
    try:
        tablo = admin.execute(text("SELECT to_regclass('public.students')")).scalar_one()
        assert tablo is not None
        toplam = admin.execute(text("SELECT COUNT(*) FROM students")).scalar_one()
        assert toplam == mock_veri.ogrenci_sayisi()
    finally:
        admin.close()


def test_kotu_niyetli_sinif_literal_eslesmez() -> None:
    """Aynı değer sınıf filtresi olarak hiçbir öğrenci satırına denk gelmez."""
    db = AppSessionLocal()
    try:
        db.connection()
        set_access_context(db, "teacher", _KOTU_SINIF, None)
        sayi = db.execute(text("SELECT COUNT(*) FROM students")).scalar_one()
        assert sayi == 0
    finally:
        db.close()
