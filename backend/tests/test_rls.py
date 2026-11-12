"""
Prove PostgreSQL row-level security without FastAPI or a rule engine.

Prerequisites, from the week-01 root:
    python database/init_db.py
    python database/enable_rls.py
    python database/seed_mock.py

The postgres superuser bypasses RLS, so these tests connect as school_app
(created by enable_rls.py). SET LOCAL lasts for the current transaction only.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pytest
from sqlalchemy import create_engine, text

from config.settings import DATABASE_URL
from database.base import with_psycopg2_driver
from database.enable_rls import APP_PASSWORD, APP_ROLE


@pytest.fixture
def rls_conn():
    url = with_psycopg2_driver(DATABASE_URL).set(
        username=APP_ROLE, password=APP_PASSWORD
    )
    app_engine = create_engine(url)
    with app_engine.connect() as conn:
        yield conn
    app_engine.dispose()


def _student_count(conn, *statements: str) -> int:
    with conn.begin():
        for statement in statements:
            conn.execute(text(statement))
        return conn.execute(text("SELECT COUNT(*) FROM students")).scalar_one()


def test_teacher_sees_only_own_class(rls_conn):
    count = _student_count(
        rls_conn,
        "SET LOCAL app.role = 'teacher'",
        "SET LOCAL app.class = '9-A'",
    )
    assert count == 4


def test_principal_sees_all_students(rls_conn):
    count = _student_count(rls_conn, "SET LOCAL app.role = 'principal'")
    assert count == 12


def test_parent_sees_only_linked_student(rls_conn):
    count = _student_count(
        rls_conn,
        "SET LOCAL app.role = 'parent'",
        "SET LOCAL app.student_id = '1'",
    )
    assert count == 1
