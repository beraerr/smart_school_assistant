"""/query akışı: metin yanıtı, aracın kendini düzeltmesi, 429 ve JSON log."""

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
from backend.tests import mock_veri
from backend.tests.sahte_model import bagla
from config.settings import settings

client = TestClient(app)

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


def _veritabani_yasak(*_args, **_kwargs):
    raise AssertionError("veritabanı çağrılmamalı")


def test_chat_veritabanina_gitmez(monkeypatch: pytest.MonkeyPatch) -> None:
    bagla(monkeypatch, ["Merhaba, bir kayda bakmamı ister misin?"])
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
    assert "Merhaba" in body["answer"]
    assert "SELECT" not in response.text


def test_metin_yaniti_sql_calistirmaz(monkeypatch: pytest.MonkeyPatch) -> None:
    bagla(monkeypatch, ["Kendi kaydına bakabilirim."])
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
    assert body["answer"] == "Kendi kaydına bakabilirim."
    assert "NOT_SUPPORTED_COMPARISON" not in response.text
    assert "SELECT" not in response.text
    assert "İstek geçersiz" not in body["answer"]


def test_tek_yeniden_deneme(monkeypatch: pytest.MonkeyPatch) -> None:
    istemci = bagla(
        monkeypatch,
        [
            ["SELECT * FROM users"],
            ["SELECT id, name FROM students"],
            "Liste hazır.",
        ],
    )
    token = _token("teacher1", "teacher123")
    response = client.post(
        "/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "öğrenciler kim?"},
    )
    assert response.status_code == 200
    assert response.json()["row_count"] == mock_veri.ogrenci_sayisi("9-A")
    assert response.json()["sql"] == ["SELECT id, name FROM students"]
    ikinci = json.dumps(istemci.cagrilar[1]["messages"], ensure_ascii=False)
    assert "Çalıştırma hatası" in ikinci
    assert "İzin verilmeyen" not in ikinci


def test_uc_deneme_de_basarisizsa_yedek_cevap(monkeypatch: pytest.MonkeyPatch) -> None:
    bagla(monkeypatch, [["SELECT * FROM users"]] * 3)
    token = _token("teacher1", "teacher123")
    response = client.post(
        "/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "kullanıcılar"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["row_count"] == 0
    assert "sql" not in body
    assert "users" not in response.text
    assert "İzin verilmeyen" not in response.text
    assert "İstek geçersiz" not in body["answer"]


def test_onbirinci_istek_429(monkeypatch: pytest.MonkeyPatch) -> None:
    istemci = bagla(monkeypatch, ["Merhaba"] * 12)
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
    assert len(istemci.cagrilar) == 10


def test_log_json_ve_jeton_yok(
    monkeypatch: pytest.MonkeyPatch,
    sorgu_loglari: list[str],
) -> None:
    cevap = "Bugün hangi kayda bakayım?"
    bagla(monkeypatch, [cevap])
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
    assert cevap not in satir
    assert "Bearer" not in satir
    if settings.ANTHROPIC_API_KEY:
        assert settings.ANTHROPIC_API_KEY not in satir
    kayit = json.loads(satir)
    assert kayit["event"] == "query"
    assert kayit["user"] == "parent1"
    assert kayit["role"] == "parent"
    assert kayit["llm_calls"] == 1
    assert kayit["tool_calls"] == 0
    assert "intent" not in kayit
    assert "answer" not in kayit
    assert kayit["row_count"] == 0
    assert kayit["db_ms"] == 0
    assert kayit["rate_limited"] is False
    assert "sql" not in kayit


def test_calisan_sql_yanitta_ve_logda(
    monkeypatch: pytest.MonkeyPatch,
    sorgu_loglari: list[str],
) -> None:
    sql = "SELECT id, name FROM students"
    bagla(monkeypatch, [[sql], "Liste hazır."])
    token = _token("principal", "admin123")
    response = client.post(
        "/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "öğrenciler kim?"},
    )
    assert response.status_code == 200
    assert response.json()["row_count"] == mock_veri.ogrenci_sayisi()
    assert response.json()["sql"] == [sql]
    assert token not in sorgu_loglari[0]
    assert "Liste hazır." not in sorgu_loglari[0]
    kayit = json.loads(sorgu_loglari[0])
    assert kayit["sql"] == [sql]
    assert kayit["llm_calls"] == 2
    assert kayit["tool_calls"] == 1
    assert kayit["row_count"] == mock_veri.ogrenci_sayisi()
    assert kayit["role"] == "principal"
