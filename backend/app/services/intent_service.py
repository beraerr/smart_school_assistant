"""Sorunun sohbet mi yoksa veri sorgusu mu olduğunu ayırır."""

from typing import Literal

from config.settings import settings

_SISTEM = """Bir okul bilgi sistemi mesajının niyetini belirle.
Yanıtın yalnızca şu iki kelimeden biri olsun: chat veya sql.
chat: selamlama, teşekkür, vedalaşma veya kayıt istemeyen mesaj.
sql: öğrenci, not, devamsızlık, sınıf veya kayıt sorusu.
Emin değilsen sql yaz. Başka karakter ekleme.
"""


def _yanit_metni(mesaj: object) -> str:
    parcalar: list[str] = []
    for blok in getattr(mesaj, "content", []):
        if getattr(blok, "type", None) == "text":
            parcalar.append(blok.text)
    return "".join(parcalar)


def detect_intent(question: str, client=None) -> Literal["chat", "sql"]:
    """Mesajı chat veya sql olarak sınıflandırır.

    client verilmezse ayarlardaki anahtarla gerçek istemci oluşturulur.
    Model yanıtı tam olarak chat değilse sql döner.
    """
    if client is None:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    mesaj = client.messages.create(
        model=settings.INTENT_MODEL,
        max_tokens=16,
        temperature=0,
        system=_SISTEM,
        messages=[{"role": "user", "content": question}],
    )
    etiket = _yanit_metni(mesaj).strip().lower().strip(".,!?:;\"'`")
    if etiket == "chat":
        return "chat"
    return "sql"
