"""SHOW_SQL: çalışan sorguda sql alanı, diğer yanıtlarda yok."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.main import app

client = TestClient(app)

_CALISAN = "SELECT id, name FROM students"
_RED = "SELECT * FROM users"


def _token() -> str:
    login = client.post(
        "/auth/login",
        json={"username": "teacher1", "password": "teacher123"},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


def _sor(token: str, question: str = "öğrenciler kim?"):
    return client.post(
        "/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": question},
    )


def _bayrak(monkeypatch: pytest.MonkeyPatch, acik: bool) -> None:
    monkeypatch.setattr("backend.app.api.query.settings.SHOW_SQL", acik)


def test_show_sql_acikken_calisan_sorgu_tam_metni_doner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bayrak(monkeypatch, True)
    monkeypatch.setattr(
        "backend.app.api.query.detect_intent",
        lambda question, client=None: "sql",
    )
    cagrilar: list[str | None] = []

    def _uret(question, role, client=None, validation_error=None):
        cagrilar.append(validation_error)
        if len(cagrilar) == 1:
            return _RED
        return _CALISAN

    monkeypatch.setattr("backend.app.api.query.translate_question_to_sql", _uret)
    response = _sor(_token())
    assert response.status_code == 200
    body = response.json()
    assert body["sql"] == _CALISAN
    assert "users" not in body["sql"]
    assert len(cagrilar) == 2


def test_show_sql_acikken_sohbet_ret_ve_400_sql_icermez(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bayrak(monkeypatch, True)
    token = _token()

    monkeypatch.setattr(
        "backend.app.api.query.detect_intent",
        lambda question, client=None: "chat",
    )
    sohbet = _sor(token, "Merhaba")
    assert sohbet.status_code == 200
    assert "sql" not in sohbet.json()
    assert "SELECT" not in sohbet.text

    monkeypatch.setattr(
        "backend.app.api.query.detect_intent",
        lambda question, client=None: "sql",
    )
    monkeypatch.setattr(
        "backend.app.api.query.translate_question_to_sql",
        lambda question, role, client=None, validation_error=None: "NOT_SUPPORTED_COMPARISON",
    )
    ret = _sor(token, "kim daha başarılı?")
    assert ret.status_code == 200
    assert "sql" not in ret.json()
    assert "NOT_SUPPORTED_COMPARISON" not in ret.text
    assert "SELECT" not in ret.text

    monkeypatch.setattr(
        "backend.app.api.query.translate_question_to_sql",
        lambda question, role, client=None, validation_error=None: _RED,
    )
    red = _sor(token, "kullanıcılar")
    assert red.status_code == 400
    assert "sql" not in red.json()
    assert "SELECT" not in red.text
    assert "users" not in red.text


def test_show_sql_kapaliyken_hicbir_yanitta_yok(monkeypatch: pytest.MonkeyPatch) -> None:
    _bayrak(monkeypatch, False)
    token = _token()
    monkeypatch.setattr(
        "backend.app.api.query.detect_intent",
        lambda question, client=None: "sql",
    )
    monkeypatch.setattr(
        "backend.app.api.query.translate_question_to_sql",
        lambda question, role, client=None, validation_error=None: _CALISAN,
    )
    tamam = _sor(token)
    assert tamam.status_code == 200
    assert "sql" not in tamam.json()
    assert _CALISAN not in tamam.text

    monkeypatch.setattr(
        "backend.app.api.query.detect_intent",
        lambda question, client=None: "chat",
    )
    sohbet = _sor(token, "Merhaba")
    assert sohbet.status_code == 200
    assert "sql" not in sohbet.json()

    monkeypatch.setattr(
        "backend.app.api.query.detect_intent",
        lambda question, client=None: "sql",
    )
    monkeypatch.setattr(
        "backend.app.api.query.translate_question_to_sql",
        lambda question, role, client=None, validation_error=None: "NOT_SUPPORTED_COMPARISON",
    )
    ret = _sor(token, "kim daha başarılı?")
    assert ret.status_code == 200
    assert "sql" not in ret.json()

    monkeypatch.setattr(
        "backend.app.api.query.translate_question_to_sql",
        lambda question, role, client=None, validation_error=None: _RED,
    )
    red = _sor(token, "kullanıcılar")
    assert red.status_code == 400
    assert "sql" not in red.json()
    assert "SELECT" not in red.text
