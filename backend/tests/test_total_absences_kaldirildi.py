"""students.total_absences sütunu kaldırıldı; devamsızlık yalnızca attendance'tan gelir."""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.models import Student
from backend.app.services.schema_context import (
    build_schema_context,
    reset_schema_context,
)
from backend.tests import mock_veri


def test_modelde_total_absences_yok() -> None:
    assert not hasattr(Student, "total_absences")
    assert "total_absences" not in Student.__table__.columns.keys()


def test_sema_ozetinde_total_absences_yok() -> None:
    reset_schema_context()
    try:
        assert "total_absences" not in build_schema_context()
    finally:
        reset_schema_context()


def test_mock_ogrenci_kayitlarinda_total_absences_yok() -> None:
    ogrenciler = mock_veri.yukle()["students"]
    assert ogrenciler
    for kayit in ogrenciler:
        assert "total_absences" not in kayit, kayit["id"]
