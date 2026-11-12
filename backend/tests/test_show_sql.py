"""SHOW_SQL: çalışan sorguda sql alanı, diğer yanıtlarda yok."""

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
    bagla(monkeypatch, [[_RED], [_CALISAN], "Liste hazır."])
    response = _sor(_token())
    assert response.status_code == 200
    body = response.json()
    assert body["sql"] == [_CALISAN]
    assert "users" not in "".join(body["sql"])


def test_show_sql_acikken_metin_ve_basarisiz_arac_sql_icermez(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bayrak(monkeypatch, True)
    token = _token()

    bagla(monkeypatch, ["Merhaba, buyurun."])
    sohbet = _sor(token, "Merhaba")
    assert sohbet.status_code == 200
    assert "sql" not in sohbet.json()
    assert "SELECT" not in sohbet.text

    bagla(monkeypatch, ["Kendi kaydına bakabilirim."])
    ret = _sor(token, "kim daha başarılı?")
    assert ret.status_code == 200
    assert "sql" not in ret.json()
    assert "SELECT" not in ret.text

    bagla(monkeypatch, [[_RED]] * 3)
    red = _sor(token, "kullanıcılar")
    assert red.status_code == 200
    assert "sql" not in red.json()
    assert "users" not in red.text


def test_show_sql_kapaliyken_hicbir_yanitta_yok(monkeypatch: pytest.MonkeyPatch) -> None:
    _bayrak(monkeypatch, False)
    token = _token()
    bagla(monkeypatch, [[_CALISAN], "Liste hazır."])
    tamam = _sor(token)
    assert tamam.status_code == 200
    assert "sql" not in tamam.json()
    assert _CALISAN not in tamam.text

    bagla(monkeypatch, ["Merhaba, buyurun."])
    sohbet = _sor(token, "Merhaba")
    assert sohbet.status_code == 200
    assert "sql" not in sohbet.json()

    bagla(monkeypatch, ["Kendi kaydına bakabilirim."])
    ret = _sor(token, "kim daha başarılı?")
    assert ret.status_code == 200
    assert "sql" not in ret.json()

    bagla(monkeypatch, [[_RED]] * 3)
    red = _sor(token, "kullanıcılar")
    assert red.status_code == 200
    assert "sql" not in red.json()
    assert "users" not in red.text
