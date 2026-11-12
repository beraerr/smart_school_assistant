"""Üretilen SQL expander'ı yalnızca yanıtta sql varsa görünür."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

_APP = Path(__file__).resolve().parents[1] / "app.py"
_SQL = "SELECT id, name FROM students"


def _ekran(data: dict, lang: str = "tr") -> AppTest:
    at = AppTest.from_file(str(_APP), default_timeout=15)
    at.session_state["token"] = "token-1"
    at.session_state["user"] = {"username": "teacher1"}
    at.session_state["lang"] = lang
    at.session_state["query_data"] = data
    at.run()
    return at


def test_sql_varsa_expander_gorunur() -> None:
    at = _ekran(
        {
            "question": "öğrenciler kim?",
            "row_count": 1,
            "results": [{"name": "Ali Yılmaz"}],
            "explanation": "Bu sonuçlar, öğretmen hesabınıza atanmış sınıfın kayıtlarından gelir.",
            "sql": _SQL,
        }
    )
    assert len(at.exception) == 0
    assert len(at.expander) == 1
    assert at.expander[0].label == "Üretilen SQL"
    assert at.expander[0].code[0].value == _SQL


def test_sql_yoksa_expander_yok() -> None:
    at = _ekran(
        {
            "question": "Merhaba",
            "row_count": 0,
            "results": [],
            "explanation": "Merhaba. Okul kayıtları hakkında bir sorunuz olursa yardımcı olabilirim.",
        }
    )
    assert len(at.exception) == 0
    assert len(at.expander) == 0
    assert len(at.info) == 2


def test_500_baglanti_mesaji_gostermez() -> None:
    at = AppTest.from_file(str(_APP), default_timeout=15)
    at.session_state["token"] = "token-1"
    at.session_state["user"] = {"username": "teacher1"}
    at.session_state["lang"] = "tr"
    at.session_state["query_error"] = {
        "ok": False,
        "status_code": 500,
        "message": "Internal Server Error",
        "kind": "server",
    }
    at.run()
    assert len(at.exception) == 0
    metinler = [hata.value for hata in at.error]
    assert metinler == ["Sunucuda bir hata oluştu, lütfen tekrar deneyin."]
    assert all("bağlanılamadı" not in metin for metin in metinler)


def test_sql_expander_ingilizce() -> None:
    at = _ekran(
        {
            "question": "who are the students?",
            "row_count": 1,
            "results": [{"name": "Ali Yılmaz"}],
            "explanation": "These results come from records of the class assigned to your teacher account.",
            "sql": _SQL,
        },
        lang="en",
    )
    assert len(at.exception) == 0
    assert at.expander[0].label == "Generated SQL"
    assert at.expander[0].code[0].value == _SQL
