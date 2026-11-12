"""Hafta 5 /query akışı: sohbet, karşılaştırma reddi, tek yeniden deneme, 429, JSON log."""

import json
import logging
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.core.logging_config import query_logger
from backend.app.main import app
from config.settings import settings

client = TestClient(app)

_GIZLILIK_TR = (
    "Bu soru başka öğrencilerle karşılaştırma gerektiriyor. "
    "Veli/öğrenci hesabınız yalnızca kendi kaydınıza erişebildiği için "
    "bu karşılaştırma yapılamıyor."
)


@pytest.fixture
def sorgu_loglari():
    satirlar: list[str] = []

    class _Yakalayici(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            satirlar.append(record.getMessage())

    handler = _Yakalayici()
    query_logger.addHandler(handler)
    try:
        yield satirlar
    finally:
        query_logger.removeHandler(handler)


def _token(username: str, password: str) -> str:
    login = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


def _sql_niyeti(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "backend.app.api.query.detect_intent",
        lambda question, client=None: "sql",
    )


def _veritabani_yasak(*_args, **_kwargs):
    raise AssertionError("veritabanı çağrılmamalı")


def test_chat_veritabanina_gitmez(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "backend.app.api.query.detect_intent",
        lambda question, client=None: "chat",
    )
    monkeypatch.setattr(
        "backend.app.api.query.translate_question_to_sql",
        _veritabani_yasak,
    )
    monkeypatch.setattr("backend.app.api.query.get_db_with_context", _veritabani_yasak)
    token = _token("teacher1", "teacher123")
    response = client.post(
        "/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Merhaba"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["results"] == []
    assert body["row_count"] == 0
    assert "Merhaba" in body["explanation"]
    assert "SELECT" not in response.text


def test_karsilastirma_sql_calistirmaz(monkeypatch: pytest.MonkeyPatch) -> None:
    _sql_niyeti(monkeypatch)
    monkeypatch.setattr(
        "backend.app.api.query.translate_question_to_sql",
        lambda question, role, client=None, validation_error=None: "NOT_SUPPORTED_COMPARISON",
    )
    monkeypatch.setattr("backend.app.api.query.get_db_with_context", _veritabani_yasak)
    token = _token("parent1", "parent123")
    response = client.post(
        "/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Çocuğum sınıfında kaçıncı sırada?", "lang": "tr"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["results"] == []
    assert body["row_count"] == 0
    assert body["explanation"] == _GIZLILIK_TR
    assert "NOT_SUPPORTED_COMPARISON" not in response.text
    assert "SELECT" not in response.text


def test_tek_yeniden_deneme(monkeypatch: pytest.MonkeyPatch) -> None:
    _sql_niyeti(monkeypatch)
    cagrilar: list[str | None] = []

    def _uret(question, role, client=None, validation_error=None):
        cagrilar.append(validation_error)
        if len(cagrilar) == 1:
            return "SELECT * FROM users"
        return "SELECT id, name FROM students"

    monkeypatch.setattr("backend.app.api.query.translate_question_to_sql", _uret)
    token = _token("teacher1", "teacher123")
    response = client.post(
        "/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "öğrenciler kim?"},
    )
    assert response.status_code == 200
    assert len(cagrilar) == 2
    assert cagrilar[0] is None
    assert cagrilar[1]
    assert "users" in cagrilar[1]
    assert response.json()["row_count"] == 4
    assert "SELECT" not in response.text


def test_ikinci_deneme_de_basarisizsa_genel_400(monkeypatch: pytest.MonkeyPatch) -> None:
    _sql_niyeti(monkeypatch)
    cagrilar: list[str | None] = []

    def _uret(question, role, client=None, validation_error=None):
        cagrilar.append(validation_error)
        return "SELECT * FROM users"

    monkeypatch.setattr("backend.app.api.query.translate_question_to_sql", _uret)
    token = _token("teacher1", "teacher123")
    response = client.post(
        "/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "kullanıcılar"},
    )
    assert response.status_code == 400
    assert len(cagrilar) == 2
    assert response.json()["detail"] == "Sorgu oluşturulamadı"
    assert "users" not in response.json()["detail"]
    assert "İzin verilmeyen" not in response.text


def test_onbirinci_istek_429(monkeypatch: pytest.MonkeyPatch) -> None:
    niyet = {"n": 0}

    def _niyet(question, client=None):
        niyet["n"] += 1
        return "chat"

    monkeypatch.setattr("backend.app.api.query.detect_intent", _niyet)
    token = _token("student1", "student123")
    for _ in range(10):
        response = client.post(
            "/query",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "Merhaba"},
        )
        assert response.status_code == 200
    response = client.post(
        "/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Merhaba"},
    )
    assert response.status_code == 429
    assert response.headers["retry-after"].isdigit()
    assert int(response.headers["retry-after"]) >= 1
    assert niyet["n"] == 10


def test_log_json_ve_jeton_yok(
    monkeypatch: pytest.MonkeyPatch,
    sorgu_loglari: list[str],
) -> None:
    monkeypatch.setattr(
        "backend.app.api.query.detect_intent",
        lambda question, client=None: "chat",
    )
    token = _token("parent1", "parent123")
    response = client.post(
        "/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Merhaba", "lang": "en"},
    )
    assert response.status_code == 200
    assert len(sorgu_loglari) == 1
    satir = sorgu_loglari[0]
    assert "\n" not in satir
    assert token not in satir
    assert "Bearer" not in satir
    if settings.ANTHROPIC_API_KEY:
        assert settings.ANTHROPIC_API_KEY not in satir
    kayit = json.loads(satir)
    assert kayit["event"] == "query"
    assert kayit["user"] == "parent1"
    assert kayit["role"] == "parent"
    assert kayit["intent"] == "chat"
    assert kayit["row_count"] == 0
    assert kayit["db_ms"] == 0
    assert kayit["rate_limited"] is False
    assert "sql" not in kayit


def test_sql_yalnizca_logda(
    monkeypatch: pytest.MonkeyPatch,
    sorgu_loglari: list[str],
) -> None:
    sql = "SELECT id, name FROM students"
    _sql_niyeti(monkeypatch)
    monkeypatch.setattr(
        "backend.app.api.query.translate_question_to_sql",
        lambda question, role, client=None, validation_error=None: sql,
    )
    token = _token("principal", "admin123")
    response = client.post(
        "/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "öğrenciler kim?"},
    )
    assert response.status_code == 200
    assert response.json()["row_count"] == 12
    assert sql not in response.text
    assert token not in sorgu_loglari[0]
    kayit = json.loads(sorgu_loglari[0])
    assert kayit["sql"] == sql
    assert kayit["intent"] == "sql"
    assert kayit["row_count"] == 12
    assert kayit["role"] == "principal"
