"""
Enable PostgreSQL row-level security on student-scoped tables.

Run from the week-01 project root, after init_db.py. Order relative to
seed_mock.py does not matter: seeding uses the superuser in DATABASE_URL,
and superusers bypass row-level security.

    python database/enable_rls.py

Policies read session settings set by the caller (SET LOCAL app.role, and
app.class or app.student_id). They apply only to roles that do not bypass
RLS. This script creates school_app for that purpose. The postgres superuser
still sees every row, which is what init_db.py and seed_mock.py rely on.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy import text

from database.base import engine

APP_ROLE = "school_app"
APP_PASSWORD = "devpassword"

_STUDENTS_POLICY = "students_role_access"
_GRADES_POLICY = "grades_via_students"
_ATTENDANCE_POLICY = "attendance_via_students"


def _autocommit(sql: str) -> None:
    """Run a statement outside a transaction (required for CREATE/ALTER ROLE)."""
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text(sql))


def _ensure_app_role() -> None:
    """Non-superuser role the API and RLS tests connect as."""
    password = APP_PASSWORD.replace("'", "''")
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_roles WHERE rolname = :name"),
            {"name": APP_ROLE},
        ).scalar()
    if exists:
        _autocommit(
            f"ALTER ROLE {APP_ROLE} WITH LOGIN PASSWORD '{password}' "
            "NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE"
        )
        return
    _autocommit(
        f"CREATE ROLE {APP_ROLE} LOGIN PASSWORD '{password}' "
        "NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE"
    )


def enable_rls() -> None:
    """Turn on RLS and (re)create the role policies. Idempotent."""
    if engine.dialect.name != "postgresql":
        raise SystemExit("enable_rls.py requires PostgreSQL (see DATABASE_URL).")

    _ensure_app_role()

    students_using = """
        current_setting('app.role', true) = 'principal'
        OR (
            current_setting('app.role', true) = 'teacher'
            AND class_name = current_setting('app.class', true)
        )
        OR (
            current_setting('app.role', true) IN ('parent', 'student')
            AND id = current_setting('app.student_id', true)::int
        )
    """
    via_students = "student_id IN (SELECT id FROM students)"

    statements = [
        "ALTER TABLE students ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE grades ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE attendance ENABLE ROW LEVEL SECURITY",
        f"DROP POLICY IF EXISTS {_STUDENTS_POLICY} ON students",
        f"DROP POLICY IF EXISTS {_GRADES_POLICY} ON grades",
        f"DROP POLICY IF EXISTS {_ATTENDANCE_POLICY} ON attendance",
        f"""
        CREATE POLICY {_STUDENTS_POLICY} ON students
        FOR SELECT
        USING ({students_using})
        """,
        f"""
        CREATE POLICY {_GRADES_POLICY} ON grades
        FOR SELECT
        USING ({via_students})
        """,
        f"""
        CREATE POLICY {_ATTENDANCE_POLICY} ON attendance
        FOR SELECT
        USING ({via_students})
        """,
        f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}",
        (
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "
            f"users, teachers, students, grades, attendance TO {APP_ROLE}"
        ),
        f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {APP_ROLE}",
    ]

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
        rows = conn.execute(
            text(
                """
                SELECT tablename, policyname
                FROM pg_policies
                WHERE schemaname = 'public'
                ORDER BY tablename, policyname
                """
            )
        ).all()

    print(f"Row-level security enabled. Application role: {APP_ROLE}")
    for table_name, policy_name in rows:
        print(f"  {table_name}: {policy_name}")


if __name__ == "__main__":
    enable_rls()
