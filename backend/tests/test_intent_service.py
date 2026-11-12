"""detect_intent: sahte client ile chat, sql ve belirsiz yanıt."""

import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.services.intent_service import detect_intent
from config.settings import Settings, settings


class _Messages:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        blok = type("Blok", (), {"type": "text", "text": self.text})()
        return type("Mesaj", (), {"content": [blok]})()


class _SahteIstemci:
    def __init__(self, text: str) -> None:
        self.messages = _Messages(text)


def test_chat_doner() -> None:
    istemci = _SahteIstemci("chat")
    assert detect_intent("merhaba", client=istemci) == "chat"


def test_sql_doner() -> None:
    istemci = _SahteIstemci("SQL")
    assert detect_intent("Ali'nin notu kaç?", client=istemci) == "sql"


@pytest.mark.parametrize("yanit", ["emin değilim", "belki chat belki sql", "", "chat lütfen"])
def test_belirsiz_yanit_sql(yanit: str) -> None:
    istemci = _SahteIstemci(yanit)
    assert detect_intent("bir şey", client=istemci) == "sql"


def test_model_ve_kucuk_max_tokens() -> None:
    istemci = _SahteIstemci("sql")
    detect_intent("merhaba", client=istemci)
    cagri = istemci.messages.calls[0]
    assert cagri["model"] == settings.INTENT_MODEL
    assert cagri["max_tokens"] <= 32
    assert cagri["temperature"] == 0


def test_intent_model_varsayilan_llm_model() -> None:
    varsayilan = Settings(
        SECRET_KEY="test",
        DATABASE_URL="postgresql://localhost/school",
        APP_DATABASE_URL="postgresql://localhost/school",
        LLM_MODEL="model-a",
        INTENT_MODEL="",
    )
    ozel = Settings(
        SECRET_KEY="test",
        DATABASE_URL="postgresql://localhost/school",
        APP_DATABASE_URL="postgresql://localhost/school",
        LLM_MODEL="model-a",
        INTENT_MODEL="model-b",
    )
    assert varsayilan.INTENT_MODEL == "model-a"
    assert ozel.INTENT_MODEL == "model-b"
