"""translate_question_to_sql: sahte client, kod bloğu ve prompt."""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.services.llm_service import translate_question_to_sql
from config.settings import settings


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


def test_kod_blogu_temizlenir() -> None:
    istemci = _SahteIstemci("```sql\nSELECT id FROM students\n```")
    sql = translate_question_to_sql("öğrenciler kim?", client=istemci)
    assert sql == "SELECT id FROM students"


def test_prompt_sema_ve_kurallar() -> None:
    istemci = _SahteIstemci("SELECT 1")
    translate_question_to_sql("sınıfımdaki öğrenciler kim?", client=istemci)
    cagri = istemci.messages.calls[0]
    sistem = cagri["system"]

    assert cagri["temperature"] == 0
    assert cagri["model"] == settings.LLM_MODEL
    assert "students(id, name, class_name, total_absences, parent_id)" in sistem
    assert "grades(id, student_id, subject, grade, date)" in sistem
    assert "attendance(id, student_id, date, status)" in sistem
    assert "Yalnızca tek bir SELECT" in sistem
    assert "students, grades ve attendance" in sistem
    assert "Erişim filtresi ekleme" in sistem
