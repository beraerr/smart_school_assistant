"""validate_select_only: tek SELECT, izinli tablolar, takma ad."""

import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.core.sql_safety import validate_select_only


def test_gecerli_select_kabul() -> None:
    validate_select_only("SELECT id, name FROM students")


def test_drop_reddedilir() -> None:
    with pytest.raises(ValueError):
        validate_select_only("DROP TABLE students")


def test_coklu_ifade_reddedilir() -> None:
    with pytest.raises(ValueError):
        validate_select_only("SELECT * FROM students; DROP TABLE students")


def test_users_referansi_reddedilir() -> None:
    with pytest.raises(ValueError):
        validate_select_only("SELECT * FROM users")


def test_teachers_referansi_reddedilir() -> None:
    with pytest.raises(ValueError):
        validate_select_only("SELECT id FROM teachers")


def test_join_ve_takma_ad_kabul() -> None:
    validate_select_only(
        """
        SELECT s.name, g.grade
        FROM students AS s
        JOIN grades g ON g.student_id = s.id
        """
    )
