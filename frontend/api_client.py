"""Login, /query ve /risk için HTTP istemcisi.

Başarılı yanıtlar ayrıştırılmış JSON olarak `data` içindedir.
`/query` gövdesi: answer, row_count, results, explanation, grounding_retry,
grounding_fallback. SHOW_SQL açıksa
çalışan sorgular `sql` listesinde gelir; istemci alanları ayıklamaz.
`/risk` gövdesi öğrenci satırlarının listesidir.
Hata durumları exception fırlatmaz; status_code ve message döner.
"""

import os

import requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

_TIMEOUT = 60


def _mesaj(body: object, response_text: str) -> str:
    if isinstance(body, dict):
        detail = body.get("detail")
        if isinstance(detail, str) and detail:
            return detail
        if detail:
            return str(detail)
    if isinstance(body, str) and body:
        return body
    return response_text or ""


def _hata(
    status_code: int | None,
    message: str,
    retry_after: str | None = None,
    kind: str | None = None,
) -> dict:
    return {
        "ok": False,
        "status_code": status_code,
        "data": None,
        "message": message,
        "retry_after": retry_after,
        "kind": kind,
    }


def _basari(data: dict | list) -> dict:
    return {
        "ok": True,
        "status_code": 200,
        "data": data,
        "message": "",
        "retry_after": None,
    }


def _post(path: str, json_body: dict, headers: dict | None = None) -> dict:
    try:
        response = requests.post(
            f"{API_BASE_URL}{path}",
            json=json_body,
            headers=headers,
            timeout=_TIMEOUT,
        )
    except requests.ConnectionError as exc:
        return _hata(None, str(exc), kind="connection")
    except requests.RequestException as exc:
        return _hata(None, str(exc), kind="server")

    try:
        body = response.json()
    except (ValueError, requests.RequestException):
        body = None

    if response.status_code == 200 and isinstance(body, dict):
        return _basari(body)

    retry_after = None
    if response.status_code == 429:
        header = response.headers.get("Retry-After")
        if header is not None:
            retry_after = str(header)
    text = response.text if isinstance(response.text, str) else ""
    kind = "server" if response.status_code >= 500 else None
    return _hata(response.status_code, _mesaj(body, text), retry_after, kind)


def _get(path: str, headers: dict | None = None, params: dict | None = None) -> dict:
    try:
        response = requests.get(
            f"{API_BASE_URL}{path}",
            headers=headers,
            params=params,
            timeout=_TIMEOUT,
        )
    except requests.ConnectionError as exc:
        return _hata(None, str(exc), kind="connection")
    except requests.RequestException as exc:
        return _hata(None, str(exc), kind="server")

    try:
        body = response.json()
    except (ValueError, requests.RequestException):
        body = None

    if response.status_code == 200 and isinstance(body, (dict, list)):
        return _basari(body)

    retry_after = None
    if response.status_code == 429:
        header = response.headers.get("Retry-After")
        if header is not None:
            retry_after = str(header)
    text = response.text if isinstance(response.text, str) else ""
    kind = "server" if response.status_code >= 500 else None
    return _hata(response.status_code, _mesaj(body, text), retry_after, kind)


def login(username: str, password: str) -> dict:
    """POST /auth/login. 200 gövdesi access_token, token_type ve user içerir."""
    return _post(
        "/auth/login",
        {"username": username, "password": password},
    )


def risk(token: str, class_name: str | None = None) -> dict:
    """GET /risk. İstenirse sınıf süzgeci `class_name` parametresine gider."""
    params = {"class_name": class_name} if class_name else None
    return _get(
        "/risk",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
    )


def examples(token: str, lang: str) -> dict:
    """GET /assistant/examples. Gövde [{"question": str}] listesidir."""
    return _get(
        "/assistant/examples",
        headers={"Authorization": f"Bearer {token}"},
        params={"lang": lang},
    )


def query(
    token: str,
    question: str,
    lang: str,
    history: list | None = None,
) -> dict:
    """POST /query. Seçilen dil `lang` alanında gider. Geçmiş sunucuda kırpılır."""
    return _post(
        "/query",
        {"question": question, "lang": lang, "history": history or []},
        headers={"Authorization": f"Bearer {token}"},
    )
