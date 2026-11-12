"""POST /query: RLS sayıları, users reddi, yetki hatası ve 529 eşlemesi."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.core.database import AppSessionLocal
from backend.app.main import app

client = TestClient(app)

_ROL_SAYILARI = [
    ("teacher1", "teacher123", 4),
    ("principal", "admin123", 12),
    ("parent1", "parent123", 1),
    ("student1", "student123", 1),
]


def _token(username: str, password: str) -> str:
    login = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


def _sabit_sql(monkeypatch: pytest.MonkeyPatch, sql: str) -> None:
    monkeypatch.setattr(
        "backend.app.api.query.detect_intent",
        lambda question, client=None: "sql",
    )
    monkeypatch.setattr(
        "backend.app.api.query.translate_question_to_sql",
        lambda question, role, client=None, validation_error=None: sql,
    )


@pytest.mark.parametrize(("username", "password", "expected"), _ROL_SAYILARI)
def test_query_select_students_rls_sayilari(
    monkeypatch: pytest.MonkeyPatch,
    username: str,
    password: str,
    expected: int,
) -> None:
    _sabit_sql(monkeypatch, "SELECT * FROM students")
    token = _token(username, password)
    response = client.post(
        "/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "öğrenciler kim?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"question", "row_count", "results", "explanation"}
    assert body["row_count"] == expected
    assert len(body["results"]) == expected
    assert body["explanation"]
    assert not any(karakter.isdigit() for karakter in body["explanation"])
    assert "SELECT" not in response.text

    if username == "teacher1":
        assert {row["class_name"] for row in body["results"]} == {"9-A"}
    if username in {"parent1", "student1"}:
        assert body["results"][0]["id"] == 1
        assert body["results"][0]["name"] == "Ali Yılmaz"


def test_users_sql_400(monkeypatch: pytest.MonkeyPatch) -> None:
    _sabit_sql(monkeypatch, "SELECT * FROM users")
    token = _token("teacher1", "teacher123")
    response = client.post(
        "/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "kullanıcılar"},
    )
    assert response.status_code == 400


def test_school_app_users_tablosuna_erisemez() -> None:
    """Doğrulama katmanı olmasa da school_app users üzerinde SELECT yapamaz."""
    db = AppSessionLocal()
    try:
        with pytest.raises(ProgrammingError):
            db.execute(text("SELECT * FROM users")).all()
        db.rollback()
    finally:
        db.close()


def test_529_hatasi_503_doner(monkeypatch: pytest.MonkeyPatch) -> None:
    def _yogunluk(question: str, role: str, client=None, validation_error=None) -> str:
        hata = Exception("overloaded")
        hata.status_code = 529
        raise hata

    monkeypatch.setattr(
        "backend.app.api.query.detect_intent",
        lambda question, client=None: "sql",
    )
    monkeypatch.setattr("backend.app.api.query.translate_question_to_sql", _yogunluk)
    token = _token("teacher1", "teacher123")
    response = client.post(
        "/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "öğrenciler kim?"},
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "Şu anda yoğunluk var, lütfen tekrar deneyin"
