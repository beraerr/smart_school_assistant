"""login ve query: requests.post mock'lanır, gerçek HTTP isteği yok."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from frontend.api_client import API_BASE_URL, examples, login, query, risk

_LOGIN_200 = {
    "access_token": "token-1",
    "token_type": "bearer",
    "user": {
        "id": 1,
        "username": "teacher1",
        "role": "teacher",
        "related_id": 1,
        "related_class": "9-A",
    },
}

_QUERY_200 = {
    "answer": "Ali Yılmaz matematikten 90 almış.",
    "row_count": 1,
    "results": [{"name": "Ali Yılmaz", "subject": "Matematik", "grade": 90}],
    "explanation": "Bu sonuçlar, öğretmen hesabınıza atanmış sınıfın kayıtlarından gelir.",
}

_CHAT_200 = {
    "answer": "Merhaba, hangi kayda bakmamı istersiniz?",
    "row_count": 0,
    "results": [],
    "explanation": "Bu sonuçlar, veli hesabınıza bağlı öğrencinin kayıtlarından gelir.",
}


def _yanit(status_code: int, body: dict | None = None, headers: dict | None = None) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.headers = headers or {}
    response.json.return_value = {} if body is None else body
    response.text = ""
    return response


def _cagir(ad: str) -> dict:
    if ad == "login":
        return login("teacher1", "teacher123")
    return query("token-1", "not ortalaması", "en")


@patch("frontend.api_client.requests.post")
def test_login_basari(mock_post: MagicMock) -> None:
    mock_post.return_value = _yanit(200, _LOGIN_200)
    sonuc = login("teacher1", "teacher123")
    assert sonuc["ok"] is True
    assert sonuc["status_code"] == 200
    assert sonuc["data"] == _LOGIN_200
    assert sonuc["data"]["access_token"] == "token-1"
    assert sonuc["data"]["user"]["username"] == "teacher1"
    mock_post.assert_called_once_with(
        f"{API_BASE_URL}/auth/login",
        json={"username": "teacher1", "password": "teacher123"},
        headers=None,
        timeout=60,
    )


@patch("frontend.api_client.requests.post")
def test_query_basari(mock_post: MagicMock) -> None:
    mock_post.return_value = _yanit(200, _QUERY_200)
    sonuc = query("token-1", "not ortalaması", "en")
    assert sonuc["ok"] is True
    assert sonuc["status_code"] == 200
    assert sonuc["data"]["results"] == _QUERY_200["results"]
    assert sonuc["data"]["explanation"] == _QUERY_200["explanation"]
    assert sonuc["data"]["row_count"] == 1
    assert set(sonuc["data"]) == {"answer", "row_count", "results", "explanation"}
    mock_post.assert_called_once_with(
        f"{API_BASE_URL}/query",
        json={"question": "not ortalaması", "lang": "en", "history": []},
        headers={"Authorization": "Bearer token-1"},
        timeout=60,
    )


@patch("frontend.api_client.requests.post")
def test_query_sql_alanini_oldugu_gibi_gecirir(mock_post: MagicMock) -> None:
    govde = {**_QUERY_200, "sql": ["SELECT id, name FROM students"]}
    mock_post.return_value = _yanit(200, govde)
    sonuc = query("token-1", "öğrenciler kim?", "tr")
    assert sonuc["ok"] is True
    assert sonuc["data"]["sql"] == ["SELECT id, name FROM students"]
    assert sonuc["data"]["results"] == _QUERY_200["results"]


@patch("frontend.api_client.requests.post")
def test_query_sohbet_yaniti_answer_alaninda(mock_post: MagicMock) -> None:
    mock_post.return_value = _yanit(200, _CHAT_200)
    sonuc = query("token-1", "Merhaba", "tr")
    assert sonuc["ok"] is True
    assert sonuc["data"]["results"] == []
    assert sonuc["data"]["row_count"] == 0
    assert sonuc["data"]["answer"].startswith("Merhaba")


@patch("frontend.api_client.requests.post")
def test_query_gecmisi_gonderir(mock_post: MagicMock) -> None:
    mock_post.return_value = _yanit(200, _CHAT_200)
    gecmis = [
        {"role": "user", "content": "Notlar?"},
        {"role": "assistant", "content": "Matematikten 90."},
    ]
    query("token-1", "peki fizikte?", "tr", history=gecmis)
    assert mock_post.call_args.kwargs["json"] == {
        "question": "peki fizikte?",
        "lang": "tr",
        "history": gecmis,
    }


@pytest.mark.parametrize("cagri", ["login", "query"])
@pytest.mark.parametrize(
    ("status_code", "detail", "headers", "retry_after"),
    [
        (401, "Kimlik doğrulama başarısız", None, None),
        (400, "Soru metni boş olamaz", None, None),
        (429, "Çok fazla istek", {"Retry-After": "12"}, "12"),
        (503, "Şu anda yoğunluk var, lütfen tekrar deneyin", None, None),
    ],
)
@patch("frontend.api_client.requests.post")
def test_http_hatalari(
    mock_post: MagicMock,
    cagri: str,
    status_code: int,
    detail: str,
    headers: dict | None,
    retry_after: str | None,
) -> None:
    mock_post.return_value = _yanit(status_code, {"detail": detail}, headers)
    sonuc = _cagir(cagri)
    assert sonuc["ok"] is False
    assert sonuc["status_code"] == status_code
    assert sonuc["message"] == detail
    assert sonuc["retry_after"] == retry_after
    assert sonuc["data"] is None


@pytest.mark.parametrize("cagri", ["login", "query"])
@patch("frontend.api_client.requests.post")
def test_baglanti_hatasi(mock_post: MagicMock, cagri: str) -> None:
    mock_post.side_effect = requests.ConnectionError("baglanti reddedildi")
    sonuc = _cagir(cagri)
    assert sonuc["ok"] is False
    assert sonuc["status_code"] is None
    assert "baglanti reddedildi" in sonuc["message"]
    assert sonuc["kind"] == "connection"
    assert sonuc["retry_after"] is None
    assert sonuc["data"] is None


@patch("frontend.api_client.requests.post")
def test_500_baglanti_hatasi_degil(mock_post: MagicMock) -> None:
    mock_post.return_value = _yanit(500, {"detail": "Internal Server Error"})
    sonuc = query("token-1", "not ortalaması", "tr")
    assert sonuc["ok"] is False
    assert sonuc["status_code"] == 500
    assert sonuc["kind"] == "server"
    assert sonuc["kind"] != "connection"


_RISK_200 = [
    {
        "student_id": 1,
        "name": "Ali Yılmaz",
        "class_name": "9-A",
        "flagged": True,
        "grade_average": 10.5,
        "unexcused_absences": 2,
        "grade_rank": "1/2",
        "absence_rank": "1–2/2 (eşit)",
        "reason": "Dikkat bayrağı var.",
    }
]


@patch("frontend.api_client.requests.get")
def test_examples_basari(mock_get: MagicMock) -> None:
    govde = [
        {"question": "Not ortalamam kaç?"},
        {"question": "Sınıfta kaçıncıyım?"},
    ]
    mock_get.return_value = _yanit(200, govde)
    sonuc = examples("token-1", "tr")
    assert sonuc["ok"] is True
    assert sonuc["data"] == govde
    mock_get.assert_called_once_with(
        f"{API_BASE_URL}/assistant/examples",
        headers={"Authorization": "Bearer token-1"},
        params={"lang": "tr"},
        timeout=60,
    )


@patch("frontend.api_client.requests.get")
def test_risk_basari(mock_get: MagicMock) -> None:
    mock_get.return_value = _yanit(200, _RISK_200)
    sonuc = risk("token-1", "tr")
    assert sonuc["ok"] is True
    assert sonuc["status_code"] == 200
    assert sonuc["data"] == _RISK_200
    mock_get.assert_called_once_with(
        f"{API_BASE_URL}/risk",
        headers={"Authorization": "Bearer token-1"},
        params={"lang": "tr"},
        timeout=60,
    )


@patch("frontend.api_client.requests.get")
def test_risk_sinif_parametresi(mock_get: MagicMock) -> None:
    mock_get.return_value = _yanit(200, _RISK_200)
    sonuc = risk("token-1", "en", "9-A")
    assert sonuc["ok"] is True
    assert sonuc["data"] == _RISK_200
    mock_get.assert_called_once_with(
        f"{API_BASE_URL}/risk",
        headers={"Authorization": "Bearer token-1"},
        params={"lang": "en", "class_name": "9-A"},
        timeout=60,
    )


@patch("frontend.api_client.requests.get")
def test_risk_403(mock_get: MagicMock) -> None:
    detail = "Bu işlem yalnızca müdür ve öğretmen hesaplarına açıktır"
    mock_get.return_value = _yanit(403, {"detail": detail})
    sonuc = risk("token-1", "tr")
    assert sonuc["ok"] is False
    assert sonuc["status_code"] == 403
    assert sonuc["message"] == detail
    assert sonuc["data"] is None
    assert sonuc["kind"] != "connection"


@patch("frontend.api_client.requests.get")
def test_risk_baglanti_hatasi(mock_get: MagicMock) -> None:
    mock_get.side_effect = requests.ConnectionError("baglanti reddedildi")
    sonuc = risk("token-1", "tr")
    assert sonuc["ok"] is False
    assert sonuc["status_code"] is None
    assert sonuc["kind"] == "connection"
    assert "baglanti reddedildi" in sonuc["message"]


def test_frontend_kaynaklari_veritabanina_baglanmaz() -> None:
    kok = Path(__file__).resolve().parents[1]
    yasak = ("sqlalchemy", "backend", "database")
    kaynaklar = [yol for yol in kok.rglob("*.py") if "tests" not in yol.parts]
    assert kaynaklar
    for yol in kaynaklar:
        for satir in yol.read_text(encoding="utf-8").splitlines():
            temiz = satir.strip()
            if temiz.startswith(("import ", "from ")):
                assert not any(parca in temiz for parca in yasak), yol.name
