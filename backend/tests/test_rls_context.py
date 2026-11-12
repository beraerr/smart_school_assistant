"""Hafta 1 RLS sayılarının POST /query üzerinden de geldiğini kanıtlar.

Beklenen görünür öğrenci sayıları (Hafta 1 test_rls.py ile aynı):
teacher → 4, principal → 12, parent → 1, student → 1.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.core.database import AppSessionLocal
from backend.app.main import app

client = TestClient(app)

# kullanıcı, parola, beklenen satır sayısı
_CASES = [
    ("teacher1", "teacher123", 4),
    ("principal", "admin123", 12),
    ("parent1", "parent123", 1),
    ("student1", "student123", 1),
]


def test_school_app_superuser_degil() -> None:
    """RLS'in gerçekten devrede olması için API rolü süper kullanıcı olmamalı."""
    db = AppSessionLocal()
    try:
        row = db.execute(
            text(
                """
                SELECT rolname, rolsuper, rolbypassrls
                FROM pg_roles
                WHERE rolname = current_user
                """
            )
        ).one()
    finally:
        db.close()
    assert row.rolname == "school_app"
    assert row.rolsuper is False
    assert row.rolbypassrls is False


@pytest.mark.parametrize(("username", "password", "expected"), _CASES)
def test_query_students_hafta1_sayilari(
    monkeypatch: pytest.MonkeyPatch, username: str, password: str, expected: int
) -> None:
    monkeypatch.setattr(
        "backend.app.api.query.detect_intent",
        lambda question, client=None: "sql",
    )
    monkeypatch.setattr(
        "backend.app.api.query.translate_question_to_sql",
        lambda question, role, client=None, validation_error=None: "SELECT * FROM students",
    )
    login = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    response = client.post(
        "/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "öğrenciler kim?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["row_count"] == expected
    rows = body["results"]
    assert len(rows) == expected

    if username == "teacher1":
        assert {row["class_name"] for row in rows} == {"9-A"}
    if username in {"parent1", "student1"}:
        assert rows[0]["id"] == 1
        assert rows[0]["name"] == "Ali Yılmaz"
