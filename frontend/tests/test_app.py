"""Sohbet ekranı: geçmiş, yeni konuşma, tablo ve SQL bölümleri, hata durumları."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

_FRONTEND = Path(__file__).resolve().parents[1]
if str(_FRONTEND) not in sys.path:
    sys.path.insert(0, str(_FRONTEND))

import api_client  # noqa: E402

_APP = _FRONTEND / "app.py"
_SQL = "SELECT name, subject, grade, date FROM grades"
_ACIKLAMA = "Bu sonuçlar, veli hesabınıza bağlı öğrencinin kayıtlarından gelir."
_SATIRLAR = [
    {"name": "Ali Yılmaz", "subject": "Matematik", "grade": 90, "date": "2026-09-15"},
    {"name": "Ali Yılmaz", "subject": "Matematik", "grade": 70, "date": "2026-10-15"},
    {"name": "Ali Yılmaz", "subject": "Fizik", "grade": 80, "date": "2026-09-15"},
]


def _veri(answer: str, results: list | None = None, sql: list | None = None) -> dict:
    govde = {
        "answer": answer,
        "row_count": len(results or []),
        "results": results or [],
        "explanation": _ACIKLAMA,
    }
    if sql is not None:
        govde["sql"] = sql
    return {"ok": True, "status_code": 200, "data": govde}


class _Sahte:
    """Her çağrıyı kaydeder, sıradaki yanıtı döner."""

    def __init__(self, yanitlar: list[dict]) -> None:
        self.yanitlar = list(yanitlar)
        self.cagrilar: list[dict] = []

    def __call__(self, token, question, lang, history=None):
        self.cagrilar.append(
            {
                "token": token,
                "question": question,
                "lang": lang,
                "history": [dict(oge) for oge in history or []],
            }
        )
        if len(self.yanitlar) > 1:
            return self.yanitlar.pop(0)
        return self.yanitlar[0]


def _ekran(lang: str = "tr") -> AppTest:
    at = AppTest.from_file(str(_APP), default_timeout=15)
    at.session_state["token"] = "token-1"
    at.session_state["user"] = {"username": "parent1"}
    at.session_state["lang"] = lang
    at.run()
    return at


def _sor(at: AppTest, soru: str) -> AppTest:
    at.chat_input[0].set_value(soru).run()
    return at


def _metinler(at: AppTest) -> str:
    parcalar = [eleman.value for eleman in at.markdown]
    parcalar += [eleman.value for eleman in at.caption]
    parcalar += [eleman.value for eleman in at.info]
    parcalar += [eleman.value for eleman in at.error]
    return "\n".join(str(parca) for parca in parcalar)


def test_gecmis_birikir_ve_son_alti_gonderilir() -> None:
    sahte = _Sahte([_veri(f"cevap {n}") for n in range(5)])
    with patch.object(api_client, "query", sahte):
        at = _ekran()
        for n in range(5):
            _sor(at, f"soru {n}")
    assert len(at.exception) == 0
    mesajlar = at.session_state["messages"]
    assert len(mesajlar) == 10
    assert [mesaj["role"] for mesaj in mesajlar[:2]] == ["user", "assistant"]
    assert sahte.cagrilar[0]["history"] == []
    assert sahte.cagrilar[1]["history"] == [
        {"role": "user", "content": "soru 0"},
        {"role": "assistant", "content": "cevap 0"},
    ]
    son = sahte.cagrilar[4]["history"]
    assert len(son) == 6
    assert son[0] == {"role": "user", "content": "soru 1"}
    assert son[-1] == {"role": "assistant", "content": "cevap 3"}
    assert all(set(oge) == {"role", "content"} for oge in son)
    assert sahte.cagrilar[4]["question"] == "soru 4"
    assert len(at.chat_message) == 10


def test_yeni_konusma_gecmisi_temizler() -> None:
    sahte = _Sahte([_veri("cevap")])
    with patch.object(api_client, "query", sahte):
        at = _ekran()
        _sor(at, "soru")
        assert len(at.session_state["messages"]) == 2
        at.button(key="yeni_konusma").click().run()
        assert at.session_state["messages"] == []
        assert len(at.chat_message) == 0
        _sor(at, "yeni soru")
    assert len(at.exception) == 0
    assert sahte.cagrilar[-1]["history"] == []


def test_tablo_ve_sql_yalniz_veri_varsa() -> None:
    sahte = _Sahte([_veri("Ali'nin notları burada.", _SATIRLAR, [_SQL, "SELECT 1 FROM grades"])])
    with patch.object(api_client, "query", sahte):
        at = _ekran()
        _sor(at, "notlar")
    assert len(at.exception) == 0
    assert [bolum.label for bolum in at.expander] == ["Tablo", "Üretilen SQL"]
    assert [kod.value for kod in at.expander[1].code] == [_SQL, "SELECT 1 FROM grades"]
    assert at.expander[1].code[0].language == "sql"
    assert len(at.dataframe) == 1
    assert at.caption[0].value == _ACIKLAMA
    asistan = at.chat_message[1]
    assert asistan.markdown[0].value == "Ali'nin notları burada."


def test_bos_sonucta_bolum_ve_kalip_metin_yok() -> None:
    sahte = _Sahte([_veri("Bu ay için devamsızlık kaydı çıkmadı.")])
    with patch.object(api_client, "query", sahte):
        at = _ekran()
        _sor(at, "devamsızlık")
    assert len(at.exception) == 0
    assert len(at.expander) == 0
    assert len(at.dataframe) == 0
    assert len(at.info) == 0
    metin = _metinler(at)
    assert "Bu ay için devamsızlık kaydı çıkmadı." in metin
    assert "Sonuç bulunamadı" not in metin
    assert at.caption[0].value == _ACIKLAMA


def test_pivot_tarih_basina_ayri_satir() -> None:
    sahte = _Sahte([_veri("Notlar.", _SATIRLAR, [_SQL])])
    with patch.object(api_client, "query", sahte):
        at = _ekran()
        _sor(at, "notlar")
        assert len(at.dataframe[0].value) == 3
        at.checkbox(key="pivot_1").check().run()
    assert len(at.exception) == 0
    tablo = at.dataframe[0].value
    assert len(tablo) == 2
    assert set(tablo.columns) >= {"Matematik", "Fizik"}


@pytest.mark.parametrize(
    ("sonuc", "beklenen"),
    [
        (
            {"ok": False, "status_code": 429, "retry_after": "12", "kind": "http"},
            "Çok fazla istek. 12 saniye sonra tekrar deneyin.",
        ),
        (
            {"ok": False, "status_code": 503, "kind": "http"},
            "Servis şu anda kullanılamıyor. Lütfen tekrar deneyin.",
        ),
        (
            {"ok": False, "status_code": 500, "kind": "server"},
            "Sunucuda bir hata oluştu, lütfen tekrar deneyin.",
        ),
        (
            {"ok": False, "status_code": None, "kind": "connection"},
            "Sunucuya bağlanılamadı.",
        ),
    ],
)
def test_hata_durumlari_cokmez(sonuc: dict, beklenen: str) -> None:
    sahte = _Sahte([sonuc])
    with patch.object(api_client, "query", sahte):
        at = _ekran()
        _sor(at, "notlar")
    assert len(at.exception) == 0
    assert [hata.value for hata in at.error] == [beklenen]
    assert at.session_state["messages"] == []
    assert at.session_state["token"] == "token-1"


def test_401_oturumu_kapatir() -> None:
    sahte = _Sahte([{"ok": False, "status_code": 401, "kind": "http"}])
    with patch.object(api_client, "query", sahte):
        at = _ekran()
        _sor(at, "notlar")
    assert len(at.exception) == 0
    assert at.session_state["token"] is None
    assert at.session_state["messages"] == []
    assert [hata.value for hata in at.error] == [
        "Oturumunuz sona erdi. Lütfen yeniden giriş yapın."
    ]


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


def test_ingilizce_bolum_adlari() -> None:
    sahte = _Sahte([_veri("Here are the grades.", _SATIRLAR, [_SQL])])
    with patch.object(api_client, "query", sahte):
        at = _ekran(lang="en")
        _sor(at, "grades")
    assert len(at.exception) == 0
    assert [bolum.label for bolum in at.expander] == ["Table", "Generated SQL"]
    assert at.button(key="yeni_konusma").label == "New conversation"
    assert sahte.cagrilar[0]["lang"] == "en"
