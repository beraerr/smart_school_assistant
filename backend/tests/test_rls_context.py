"""Hafta 1 RLS sayılarının POST /query üzerinden de geldiğini kanıtlar.

Beklenen görünür öğrenci sayıları mock_data.json'dan hesaplanır:
teacher → kendi sınıfı, principal → tüm okul, parent → 1, student → 1.
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
from backend.tests import mock_veri
from backend.tests.sahte_model import bagla

client = TestClient(app)

# kullanıcı, parola, beklenen satır sayısı (mock_data.json'dan hesaplanır)
_CASES = [
    ("teacher1", "teacher123", mock_veri.ogrenci_sayisi("9-A")),
    ("principal", "admin123", mock_veri.ogrenci_sayisi()),
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
    bagla(monkeypatch, [["SELECT * FROM students"], "Liste hazır."])
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
