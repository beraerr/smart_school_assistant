"""Veritabanı hatası modele ve kullanıcıya ham metin olarak gitmez."""

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.main import app
from backend.tests.sahte_model import bagla

client = TestClient(app)

_BOZUK = "SELECT no_such_column FROM students"
_DUZ = "SELECT id, name FROM students"


def _token() -> str:
    login = client.post(
        "/auth/login",
        json={"username": "parent1", "password": "parent123"},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


def test_bozuk_sql_sonra_dogru_sql_200(monkeypatch: pytest.MonkeyPatch) -> None:
    istemci = bagla(monkeypatch, [[_BOZUK], [_DUZ], "Ali Yılmaz kayıtta."])
    response = client.post(
        "/query",
        headers={"Authorization": f"Bearer {_token()}"},
        json={"question": "ben kimin velisiyim?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sql"] == [_DUZ]
    assert body["row_count"] == 1
    assert body["answer"] == "Ali Yılmaz kayıtta."
    ikinci = json.dumps(istemci.cagrilar[1]["messages"], ensure_ascii=False)
    assert "Çalıştırma hatası" in ikinci
    assert "UndefinedColumn" not in ikinci
    assert "psycopg" not in ikinci.lower()
    assert "no_such_column" not in response.text


def test_uc_bozuk_sql_yedek_cevap(monkeypatch: pytest.MonkeyPatch) -> None:
    istemci = bagla(monkeypatch, [[_BOZUK]] * 3)
    response = client.post(
        "/query",
        headers={"Authorization": f"Bearer {_token()}"},
        json={"question": "ben kimin velisiyim?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "sql" not in body
    assert "İstek geçersiz" not in body["answer"]
    assert "Sonuç bulunamadı" not in body["answer"]
    birlesik = json.dumps(istemci.cagrilar, ensure_ascii=False)
    assert "UndefinedColumn" not in birlesik
    assert "psycopg" not in birlesik.lower()
    assert "no_such_column" not in response.text
    assert "UndefinedColumn" not in response.text
    assert "psycopg" not in response.text.lower()
