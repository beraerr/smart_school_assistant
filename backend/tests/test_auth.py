"""Dört rol için login: doğru parolada 200 + JWT, yanlış parolada 401."""

import sys
import time
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


def test_bilinmeyen_kullanici_ayni_401_ve_hash_dogrular(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.app.core import security

    cagrilar: list[str] = []
    gercek = security.verify_password

    def sarmal(plain: str, hashed: str) -> bool:
        cagrilar.append(hashed)
        return gercek(plain, hashed)

    monkeypatch.setattr("backend.app.api.auth.verify_password", sarmal)
    parola = "ayni-yanlis-parola"
    yok = client.post(
        "/auth/login",
        json={"username": "olmayan-kullanici", "password": parola},
    )
    yanlis = client.post(
        "/auth/login",
        json={"username": "parent1", "password": parola},
    )
    assert yok.status_code == 401
    assert yanlis.status_code == 401
    assert yok.json() == yanlis.json()
    assert yok.json()["detail"] == "Kullanıcı adı veya parola hatalı"
    assert len(cagrilar) == 2
    assert cagrilar[0] != cagrilar[1]


def test_bilinmeyen_ve_yanlis_parola_sureleri_yakin() -> None:
    def _olc(username: str) -> float:
        basla = time.perf_counter()
        response = client.post(
            "/auth/login",
            json={"username": username, "password": "sure-olcumu"},
        )
        gecen = time.perf_counter() - basla
        assert response.status_code == 401
        return gecen

    yok = _olc("olmayan-kullanici-sure")
    yanlis = _olc("parent1")
    assert yok > 0.02
    assert yanlis > 0.02
    assert max(yok, yanlis) < min(yok, yanlis) * 4


def test_bes_yanlis_denemeden_sonra_429(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.core.rate_limiter import RateLimiter

    simdi = {"t": 1_000.0}
    monkeypatch.setattr(
        "backend.app.api.auth.login_failure_limiter",
        RateLimiter(limit=5, clock=lambda: simdi["t"]),
    )
    govde = {"username": "parent1", "password": "yanlis-parola"}
    for _ in range(5):
        response = client.post("/auth/login", json=govde)
        assert response.status_code == 401
    altinci = client.post("/auth/login", json=govde)
    assert altinci.status_code == 429
    assert altinci.json()["detail"] == "Çok fazla deneme"
    assert altinci.headers["retry-after"]
    simdi["t"] = 1_060.0
    tekrar = client.post("/auth/login", json=govde)
    assert tekrar.status_code == 401
