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


def test_student_rank_kabul() -> None:
    validate_select_only("SELECT * FROM student_rank('class', NULL)")


def test_class_teacher_kabul() -> None:
    validate_select_only("SELECT name FROM class_teacher()")


def test_pg_ls_dir_reddedilir() -> None:
    with pytest.raises(ValueError):
        validate_select_only("SELECT * FROM pg_ls_dir('.')")


def test_toplama_ve_pencere_kabul() -> None:
    validate_select_only(
        """
        SELECT COUNT(*) AS total, ROUND(AVG(g.grade), 2), MIN(g.grade), MAX(g.grade),
               SUM(g.grade), LOWER(s.name), UPPER(s.name), COALESCE(s.name, ''),
               EXTRACT(YEAR FROM g.date), DATE_TRUNC('month', g.date),
               NOW(), CURRENT_DATE,
               RANK() OVER (ORDER BY g.grade),
               DENSE_RANK() OVER (ORDER BY g.grade),
               ROW_NUMBER() OVER (ORDER BY g.grade)
        FROM students AS s
        JOIN grades g ON g.student_id = s.id
        """
    )


def test_tur_donusumu_kabul() -> None:
    validate_select_only("SELECT id::text, CAST(id AS integer) FROM students")


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT set_config('app.role', 'principal', true)",
        "WITH x AS (SELECT set_config('app.role', 'principal', true)) "
        "SELECT s.* FROM students s, x",
        "SELECT s.* FROM students s WHERE (SELECT set_config('app.role', 'principal', true)) IS NOT NULL",
        "SELECT current_setting('app.role', true)",
        "SELECT pg_sleep(1)",
        "SELECT lo_import('/etc/passwd')",
        "SELECT dblink('host=localhost', 'SELECT 1')",
        "SELECT student_rank('class', NULL)",
        "SELECT class_teacher()",
    ],
)
def test_izin_listesi_disi_fonksiyon_reddedilir(sql: str) -> None:
    with pytest.raises(ValueError):
        validate_select_only(sql)


def test_join_ve_takma_ad_kabul() -> None:
    validate_select_only(
        """
        SELECT s.name, g.grade
        FROM students AS s
        JOIN grades g ON g.student_id = s.id
        """
    )
