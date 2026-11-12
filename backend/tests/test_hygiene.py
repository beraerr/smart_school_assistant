"""Giriş ve sorgu yanıtlarında parola, jeton ve veritabanı hatası sızmaz."""

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
from backend.tests.sahte_model import bagla
from config.settings import settings

client = TestClient(app)


def _log_metni(caplog: pytest.LogCaptureFixture) -> str:
    return "\n".join(kayit.getMessage() for kayit in caplog.records)


def test_giris_yaniti_ve_logu_sir_tasimaz(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    query_logger.addHandler(caplog.handler)
    parola = "parent123"
    try:
        response = client.post(
            "/auth/login",
            json={"username": "parent1", "password": parola},
        )
        assert response.status_code == 200
        govde = response.text
        loglar = _log_metni(caplog)
        token = response.json()["access_token"]
        assert parola not in govde
        assert parola not in loglar
        assert token not in loglar
        assert settings.SECRET_KEY not in govde
        assert settings.SECRET_KEY not in loglar
        if settings.ANTHROPIC_API_KEY:
            assert settings.ANTHROPIC_API_KEY not in govde
            assert settings.ANTHROPIC_API_KEY not in loglar
    finally:
        query_logger.removeHandler(caplog.handler)


def test_veritabani_hata_metni_kullaniciya_gitmez(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bagla(monkeypatch, [["SELECT no_such_column FROM students"]] * 3)
    login = client.post(
        "/auth/login",
        json={"username": "parent1", "password": "parent123"},
    )
    response = client.post(
        "/query",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        json={"question": "kayıt"},
    )
    assert response.status_code == 200
    assert "no_such_column" not in response.text
    assert "UndefinedColumn" not in response.text
    assert "psycopg" not in response.text.lower()
    assert "İstek geçersiz" not in response.text


def test_cors_yildiz_degil() -> None:
    katmanlar = [
        katman
        for katman in app.user_middleware
        if katman.cls.__name__ == "CORSMiddleware"
    ]
    assert len(katmanlar) == 1
    kokenler = katmanlar[0].kwargs["allow_origins"]
    assert kokenler == settings.cors_origin_list()
    assert "*" not in kokenler
    assert "http://localhost:8501" in kokenler
