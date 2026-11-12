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
    sql = translate_question_to_sql("öğrenciler kim?", "teacher", client=istemci)
    assert sql == "SELECT id FROM students"


def test_prompt_sema_ve_kurallar() -> None:
    istemci = _SahteIstemci("SELECT 1")
    translate_question_to_sql("sınıfımdaki öğrenciler kim?", "teacher", client=istemci)
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
    assert "ILIKE '%...%'" in sistem
    assert "SELECT listesinde" in sistem
    assert "name" in sistem and "id" in sistem
    assert "class_name" in sistem and "student_id" in sistem
    assert "ben kimin velisiyim" in sistem
    assert "SELECT id, name, class_name FROM students" in sistem
    assert "current_setting" in sistem
    assert "set_config" in sistem
    assert "Kullanıcı kimliği diye bir ayar yok" in sistem


def test_karsilastirma_kurali_yalnizca_veli_ve_ogrenci() -> None:
    for role in ("parent", "student"):
        istemci = _SahteIstemci("SELECT 1")
        translate_question_to_sql("sınıfta kaçıncı", role, client=istemci)
        sistem = istemci.messages.calls[0]["system"]
        assert "NOT_SUPPORTED_COMPARISON" in sistem
        assert "karşılaştırma" in sistem
        assert "ILIKE '%...%'" in sistem
        assert "SELECT listesinde" in sistem
        assert "ben kimin velisiyim" in sistem
        assert "current_setting" in sistem
        assert "set_config" in sistem
        assert "SELECT * FROM student_rank('class', NULL)" in sistem
        assert "SELECT * FROM student_rank('school', NULL)" in sistem
        assert "SELECT * FROM student_rank('class', 'Matematik')" in sistem
        assert "Matematik, Fizik, Kimya, Tarih, Türkçe" in sistem
        assert "group_avg" in sistem and "student_avg" in sistem

    for role in ("teacher", "principal"):
        istemci = _SahteIstemci("SELECT 1")
        translate_question_to_sql("sınıfta en yüksek not", role, client=istemci)
        sistem = istemci.messages.calls[0]["system"]
        assert "NOT_SUPPORTED_COMPARISON" not in sistem
        assert "karşılaştırma" not in sistem
        assert "sıralama" not in sistem
        assert "student_rank" not in sistem
        assert "ILIKE '%...%'" in sistem
        assert "SELECT listesinde" in sistem
        assert "class_name" in sistem and "student_id" in sistem
        assert "ben kimin velisiyim" in sistem
        assert "current_setting" in sistem
        assert "set_config" in sistem


def test_dogrulama_hatasi_kullanici_mesajina_yazilir() -> None:
    istemci = _SahteIstemci("SELECT id FROM students")
    translate_question_to_sql(
        "öğrenciler",
        "teacher",
        client=istemci,
        validation_error="İzin verilmeyen tablo: users",
    )
    icerik = istemci.messages.calls[0]["messages"][0]["content"]
    assert "öğrenciler" in icerik
    assert "İzin verilmeyen tablo: users" in icerik
