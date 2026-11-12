"""Dört rol için login: doğru parolada 200 + JWT, yanlış parolada 401."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.core.security import decode_access_token
from backend.app.main import app

client = TestClient(app)

_ACCOUNTS = [
    ("principal", "admin123", "principal", None, None),
    ("teacher1", "teacher123", "teacher", 1, "9-A"),
    ("parent1", "parent123", "parent", 1, None),
    ("student1", "student123", "student", 1, None),
]


@pytest.mark.parametrize(
    ("username", "password", "role", "related_id", "related_class"),
    _ACCOUNTS,
)
def test_login_dogru_parola_token_doner(
    username: str,
    password: str,
    role: str,
    related_id: int | None,
    related_class: str | None,
) -> None:
    response = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]

    payload = decode_access_token(body["access_token"])
    assert payload["sub"] == username
    assert payload["role"] == role
    assert payload["related_id"] == related_id
    assert payload["related_class"] == related_class
    assert "exp" in payload


@pytest.mark.parametrize(
    ("username", "password", "role", "related_id", "related_class"),
    _ACCOUNTS,
)
def test_login_yanlis_parola_401(
    username: str,
    password: str,
    role: str,
    related_id: int | None,
    related_class: str | None,
) -> None:
    del password, role, related_id, related_class
    response = client.post(
        "/auth/login",
        json={"username": username, "password": "yanlis-parola"},
    )
    assert response.status_code == 401
    assert "access_token" not in response.json()
