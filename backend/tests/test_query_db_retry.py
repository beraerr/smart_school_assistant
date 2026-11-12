"""Veritabanı hatası aynı deneme hakkını kullanır; kullanıcıya ham hata gitmez."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.main import app

client = TestClient(app)

_BOZUK = (
    "SELECT id, name FROM students "
    "WHERE parent_id = current_setting('app.user_id')::integer"
)
_DUZ = "SELECT id, name FROM students"
_GENEL = "Soru işlenemedi, lütfen farklı ifade edin"


def _token() -> str:
    login = client.post(
        "/auth/login",
        json={"username": "parent1", "password": "parent123"},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


def _uret(sirali: list[str]):
    cagrilar: list[str | None] = []

    def _fn(question, role, client=None, validation_error=None):
        cagrilar.append(validation_error)
        return sirali[len(cagrilar) - 1]

    return _fn, cagrilar


def test_bozuk_sql_sonra_dogru_sql_200(monkeypatch: pytest.MonkeyPatch) -> None:
    fn, cagrilar = _uret([_BOZUK, _DUZ])
    monkeypatch.setattr(
        "backend.app.api.query.detect_intent",
        lambda question, client=None: "sql",
    )
    monkeypatch.setattr("backend.app.api.query.translate_question_to_sql", fn)
    token = _token()
    response = client.post(
        "/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "ben kimin velisiyim?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sql"] == _DUZ
    assert body["row_count"] == 1
    assert len(cagrilar) == 2
    assert cagrilar[0] is None
    assert cagrilar[1]
    assert "app.user_id" in cagrilar[1]
    assert "app.user_id" not in response.text


def test_iki_bozuk_sql_genel_400(monkeypatch: pytest.MonkeyPatch) -> None:
    fn, cagrilar = _uret([_BOZUK, _BOZUK])
    monkeypatch.setattr(
        "backend.app.api.query.detect_intent",
        lambda question, client=None: "sql",
    )
    monkeypatch.setattr("backend.app.api.query.translate_question_to_sql", fn)
    token = _token()
    response = client.post(
        "/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "ben kimin velisiyim?"},
    )
    assert response.status_code == 400
    assert response.status_code != 500
    body = response.json()
    assert body["detail"] == _GENEL
    assert "sql" not in body
    assert len(cagrilar) == 2
    assert "app.user_id" not in response.text
    assert "UndefinedObject" not in response.text
    assert "current_setting" not in response.text
    assert "psycopg" not in response.text.lower()
