"""Sohbet ekranı: geçmiş, yeni konuşma, tablo ve SQL bölümleri, hata durumları."""

import html
import json
import logging
import re
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

_FRONTEND = Path(__file__).resolve().parents[1]
_ROOT = _FRONTEND.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_FRONTEND) not in sys.path:
    sys.path.insert(0, str(_FRONTEND))

import api_client  # noqa: E402
from backend.app.services.assistant_examples import example_questions as _sunucu_sorulari  # noqa: E402

_APP = _FRONTEND / "app.py"
_SQL = "SELECT name, subject, grade, date FROM grades"
_ACIKLAMA = "Bu sonuçlar, veli hesabınıza bağlı öğrencinin kayıtlarından gelir."
_SATIRLAR = [
    {"name": "Ali Yılmaz", "subject": "Matematik", "grade": 90, "date": "2026-09-15"},
    {"name": "Ali Yılmaz", "subject": "Matematik", "grade": 70, "date": "2026-10-15"},
    {"name": "Ali Yılmaz", "subject": "Fizik", "grade": 80, "date": "2026-09-15"},
]


def _veri(
    answer: str,
    results: list | None = None,
    sql: list | None = None,
    grounding_fallback: bool | None = None,
) -> dict:
    govde = {
        "answer": answer,
        "row_count": len(results or []),
        "results": results or [],
        "explanation": _ACIKLAMA,
    }
    if sql is not None:
        govde["sql"] = sql
    if grounding_fallback is not None:
        govde["grounding_fallback"] = grounding_fallback
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


def _gorunen_metin(at: AppTest) -> str:
    """Kullanıcıya görünen metin: tema <style> bloğu (CSS ve yorumları) hariç."""
    parcalar = [
        eleman.value
        for eleman in at.markdown
        if not str(eleman.value).lstrip().startswith("<style>")
    ]
    parcalar += [eleman.value for eleman in at.caption]
    parcalar += [eleman.value for eleman in at.info]
    parcalar += [eleman.value for eleman in at.error]
    return "\n".join(str(parca) for parca in parcalar)


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
    assert [bolum.label for bolum in at.expander] == ["Sorguyu göster", "Neler sorabilirim?"]
    sql_bolum = next(bolum for bolum in at.expander if bolum.label == "Sorguyu göster")
    assert [kod.value for kod in sql_bolum.code] == [_SQL, "SELECT 1 FROM grades"]
    assert sql_bolum.code[0].language == "sql"
    assert sql_bolum.proto.expanded is False  # olağan cevapta bölüm kapalı gelir
    assert len(at.dataframe) == 1
    ayar = json.loads(at.dataframe[0].proto.columns)
    assert ayar["_index"]["hidden"] is True
    assert at.caption[0].value == _ACIKLAMA
    asistan = at.chat_message[1]
    assert asistan.markdown[0].value == "Ali'nin notları burada."


_GERI_DONUS = (
    "Sorgu sonuçlarını aşağıda gösteriyorum; bazı hesaplamaları doğrulayamadığım "
    "için yorum eklemedim."
)


@pytest.mark.parametrize("sql", [[_SQL], None])
def test_grounding_fallback_bolum_acik_ve_tablo_gorunur(sql: list | None) -> None:
    sahte = _Sahte([_veri(_GERI_DONUS, _SATIRLAR, sql, grounding_fallback=True)])
    with patch.object(api_client, "query", sahte):
        at = _ekran()
        _sor(at, "notlar")
    assert len(at.exception) == 0
    sql_bolum = next(bolum for bolum in at.expander if bolum.label == "Sorguyu göster")
    assert sql_bolum.proto.expanded is True
    assert [kod.value for kod in sql_bolum.code] == (sql or [])
    assert len(at.dataframe) == 1
    assert _GERI_DONUS in _metinler(at)


def test_grounding_fallback_false_iken_bolum_kapali() -> None:
    sahte = _Sahte([_veri("Notlar burada.", _SATIRLAR, [_SQL], grounding_fallback=False)])
    with patch.object(api_client, "query", sahte):
        at = _ekran()
        _sor(at, "notlar")
    sql_bolum = next(bolum for bolum in at.expander if bolum.label == "Sorguyu göster")
    assert sql_bolum.proto.expanded is False


def test_grounding_fallback_sonuc_yoksa_bos_bolum_acilmaz() -> None:
    sahte = _Sahte([_veri(_GERI_DONUS, [], None, grounding_fallback=True)])
    with patch.object(api_client, "query", sahte):
        at = _ekran()
        _sor(at, "notlar")
    assert all(bolum.label != "Sorguyu göster" for bolum in at.expander)
    assert len(at.dataframe) == 0


def test_bos_sonucta_bolum_ve_kalip_metin_yok() -> None:
    sahte = _Sahte([_veri("Bu ay için devamsızlık kaydı çıkmadı.")])
    with patch.object(api_client, "query", sahte):
        at = _ekran()
        _sor(at, "devamsızlık")
    assert len(at.exception) == 0
    assert [bolum.label for bolum in at.expander] == ["Neler sorabilirim?"]
    assert len(at.dataframe) == 0
    assert len(at.info) == 0
    metin = _metinler(at)
    assert "Bu ay için devamsızlık kaydı çıkmadı." in metin
    assert "Sonuç bulunamadı" not in metin
    assert at.caption[0].value == _ACIKLAMA


def test_sorguyu_goster_sql_yokken_yok() -> None:
    sahte = _Sahte([_veri("Ali'nin notları burada.", _SATIRLAR)])
    with patch.object(api_client, "query", sahte):
        at = _ekran()
        _sor(at, "notlar")
    assert len(at.exception) == 0
    assert [bolum.label for bolum in at.expander] == ["Neler sorabilirim?"]
    assert all(bolum.label != "Sorguyu göster" for bolum in at.expander)
    assert "Sorguyu göster" not in _metinler(at)
    assert len(at.dataframe) == 0
    assert "Ali'nin notları burada." in _metinler(at)
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


def test_demo_dugmesi_alanlari_doldurur() -> None:
    at = AppTest.from_file(str(_APP), default_timeout=15)
    at.session_state["token"] = None
    at.session_state["user"] = None
    at.session_state["lang"] = "tr"
    at.run()
    assert len(at.exception) == 0
    beklenen = (
        ("demo_principal", "Müdür", "principal", "admin123"),
        ("demo_teacher", "Sınıf öğretmeni", "teacher1", "teacher123"),
        ("demo_parent", "Veli", "parent1", "parent123"),
        ("demo_student", "Öğrenci", "student1", "student123"),
    )
    for anahtar, rol, kullanici, sifre in beklenen:
        etiket = at.button(key=anahtar).label
        assert rol in etiket
        assert f":material/person: {kullanici}" in etiket
        assert f":material/key: {sifre}" in etiket
        assert "`" not in etiket
        at.button(key=anahtar).click().run()
        assert len(at.exception) == 0
        assert at.text_input(key="kullanici_adi").value == kullanici
        assert at.text_input(key="sifre").value == sifre


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
    assert [bolum.label for bolum in at.expander] == ["Show query", "What can I ask?"]
    assert at.button(key="yeni_konusma").label == "New conversation"
    assert sahte.cagrilar[0]["lang"] == "en"


_RISK_BILDIRIMI = (
    "Dikkat bayrağı, içinde bulunulan dönemin verisiyle her sınıfta göreli olarak "
    "hesaplanır: not ortalaması ve mazeretsiz devamsızlık sıralamalarına göre "
    "sınıfın yaklaşık beşte biri işaretlenir; eşit sıralamalar bu sayıyı "
    "artırabilir. Henüz not girilmemiş sınıfta bayrak yoktur. Bu bir olasılık ya "
    "da tanı değil, öğretmenin dikkatine sunulan bir işarettir."
)
_RISK_SATIRLARI = [
    {
        "student_id": 1,
        "name": "Ayşe Demir",
        "class_name": "9-A",
        "flagged": False,
        "grade_average": 80.0,
        "unexcused_absences": 0,
        "grade_rank": "2/2",
        "absence_rank": "2/2",
        "reason": "Dikkat bayrağı yok.",
    },
    {
        "student_id": 2,
        "name": "Ali Yılmaz",
        "class_name": "10-B",
        "flagged": True,
        "grade_average": 10.5,
        "unexcused_absences": 4,
        "grade_rank": "1/2",
        "absence_rank": "1–2/2 (eşit)",
        "reason": "Dikkat bayrağı var.",
    },
    {
        "student_id": 3,
        "name": "Can Kaya",
        "class_name": "9-A",
        "flagged": True,
        "grade_average": 40.0,
        "unexcused_absences": 3,
        "grade_rank": "1/2",
        "absence_rank": "1/2",
        "reason": "Dikkat bayrağı var.",
    },
]


class _RiskCagri:
    def __init__(self, sonuc: dict) -> None:
        self.sonuc = sonuc
        self.cagrilar: list[dict] = []

    def __call__(self, token, class_name=None):
        self.cagrilar.append({"token": token, "class_name": class_name})
        return self.sonuc


def _ekran_rol(role: str, lang: str = "tr", sayfa: str | None = None) -> AppTest:
    at = AppTest.from_file(str(_APP), default_timeout=15)
    at.session_state["token"] = "token-1"
    at.session_state["user"] = {"username": role, "role": role}
    at.session_state["lang"] = lang
    if sayfa == "risk" and role in {"principal", "teacher"}:
        at.session_state["menu"] = "risk"
    if sayfa:
        at.query_params["sayfa"] = sayfa
    at.run()
    return at


def _hucreler(tablo: pd.DataFrame, kolon: str) -> list[str]:
    return ["" if pd.isna(deger) else str(deger) for deger in tablo[kolon]]


def test_veli_ve_ogrenci_menude_risk_yok() -> None:
    for role in ("parent", "student"):
        at = _ekran_rol(role)
        assert len(at.exception) == 0
        assert at.button(key="nav_chat").label == "Asistan"
        assert all(btn.key != "nav_risk" for btn in at.button)
        assert at.session_state["menu"] == "chat"
        assert len(at.chat_input) == 1
        assert len(at.dataframe) == 0


@pytest.mark.parametrize("role", ["parent", "student"])
def test_risk_adresi_403(role: str) -> None:
    sahte = _RiskCagri({"ok": True, "status_code": 200, "data": _RISK_SATIRLARI})
    with patch.object(api_client, "risk", sahte):
        at = _ekran_rol(role, sayfa="risk")
    assert len(at.exception) == 0
    assert sahte.cagrilar == []
    assert [hata.value for hata in at.error] == [
        "Bu işlem yalnızca müdür ve öğretmen hesaplarına açıktır."
    ]
    assert len(at.dataframe) == 0
    assert len(at.info) == 0
    assert len(at.chat_input) == 0
    assert len(at.radio) == 0
    at.button(key="sohbete_don").click().run()
    assert len(at.exception) == 0
    assert at.button(key="nav_chat").label == "Asistan"
    assert all(btn.key != "nav_risk" for btn in at.button)
    assert len(at.chat_input) == 1
    assert [hata.value for hata in at.error] == []


def test_ogretmen_risk_sekmesi_sinif_filtresi_yok() -> None:
    sahte = _RiskCagri(
        {"ok": True, "status_code": 200, "data": _RISK_SATIRLARI, "message": ""}
    )
    with patch.object(api_client, "risk", sahte):
        at = _ekran_rol("teacher")
        assert sahte.cagrilar == []
        assert at.button(key="nav_chat").label == "Asistan"
        assert at.button(key="nav_risk").label == "Risk"
        at.button(key="nav_risk").click().run()
    assert len(at.exception) == 0
    assert sahte.cagrilar == [{"token": "token-1", "class_name": None}]
    assert at.info[0].value == _RISK_BILDIRIMI
    assert len(at.selectbox) == 1
    tablo = at.dataframe[0].value
    assert list(tablo.columns) == [
        "Öğrenci",
        "Sınıf",
        "Not ortalaması",
        "Mazeretsiz devamsızlık",
        "Not sırası",
        "Devamsızlık sırası",
        "Bayrak",
    ]
    assert _hucreler(tablo, "Öğrenci") == ["Ali Yılmaz", "Can Kaya", "Ayşe Demir"]
    assert _hucreler(tablo, "Bayrak") == ["Dikkat", "Dikkat", ""]
    assert tablo["Not ortalaması"].tolist() == [10.5, 40.0, 80.0]
    assert "Gerekçe" not in tablo.columns
    assert "score" not in tablo.columns
    assert "probability" not in tablo.columns
    ayar = json.loads(at.dataframe[0].proto.columns)
    assert ayar["Not ortalaması"]["alignment"] == "right"
    assert ayar["Not ortalaması"]["type_config"]["format"] == "%.2f"
    kartlar = [oge.value for oge in at.markdown if 'class="risk-card"' in oge.value]
    assert len(kartlar) == 2
    assert "Ali Yılmaz" in kartlar[0] and "10-B" in kartlar[0]
    assert "Dikkat bayrağı var." in kartlar[0]
    assert "Can Kaya" in kartlar[1] and "9-A" in kartlar[1]
    assert all("#FFF3E0" in kart and "#8A5200" in kart for kart in kartlar)
    assert all("red" not in kart.casefold() for kart in kartlar)
    assert all("Dikkat bayrağı yok." not in kart for kart in kartlar)
    metin = _gorunen_metin(at)
    assert "alarm" not in metin.casefold()
    assert "tehlike" not in metin.casefold()
    assert "kırmızı" not in metin.casefold()


def test_mudur_sinif_filtresi() -> None:
    sahte = _RiskCagri(
        {"ok": True, "status_code": 200, "data": _RISK_SATIRLARI, "message": ""}
    )
    with patch.object(api_client, "risk", sahte):
        at = _ekran_rol("principal", sayfa="risk")
        assert at.info[0].value == _RISK_BILDIRIMI
        kutu = at.selectbox(key="risk_sinif")
        assert kutu.options[0] == "Tümü"
        assert "9-A" in kutu.options
        assert "10-B" in kutu.options
        kutu.set_value("9-A").run()
    assert len(at.exception) == 0
    assert all(cagri["class_name"] is None for cagri in sahte.cagrilar)
    tablo = at.dataframe[0].value
    assert _hucreler(tablo, "Öğrenci") == ["Can Kaya", "Ayşe Demir"]
    assert _hucreler(tablo, "Sınıf") == ["9-A", "9-A"]
    assert "Gerekçe" not in tablo.columns
    kartlar = [oge.value for oge in at.markdown if 'class="risk-card"' in oge.value]
    assert len(kartlar) == 1
    assert "Can Kaya" in kartlar[0]
    assert "9-A" in kartlar[0]
    assert "Dikkat bayrağı var." in kartlar[0]
    assert "Ali Yılmaz" not in kartlar[0]
    assert "Dikkat bayrağı yok." not in kartlar[0]
    assert "#FFF3E0" in kartlar[0] and "#8A5200" in kartlar[0]
    assert at.info[0].value == _RISK_BILDIRIMI


def test_risk_api_403_mesaji() -> None:
    sahte = _RiskCagri(
        {
            "ok": False,
            "status_code": 403,
            "data": None,
            "message": "Bu işlem yalnızca müdür ve öğretmen hesaplarına açıktır",
        }
    )
    with patch.object(api_client, "risk", sahte):
        at = _ekran_rol("teacher", sayfa="risk")
    assert len(at.exception) == 0
    assert len(sahte.cagrilar) == 1
    assert [hata.value for hata in at.error] == [
        "Bu işlem yalnızca müdür ve öğretmen hesaplarına açıktır."
    ]
    assert at.info[0].value == _RISK_BILDIRIMI
    assert len(at.dataframe) == 0


def test_ingilizce_risk_sekmesi() -> None:
    sahte = _RiskCagri(
        {"ok": True, "status_code": 200, "data": _RISK_SATIRLARI, "message": ""}
    )
    with patch.object(api_client, "risk", sahte):
        at = _ekran_rol("teacher", lang="en", sayfa="risk")
    assert len(at.exception) == 0
    assert at.button(key="nav_chat").label == "Assistant"
    assert at.button(key="nav_risk").label == "Risk"
    assert at.info[0].value.startswith("Attention flags are computed relative to each class")
    assert _hucreler(at.dataframe[0].value, "Flag")[0] == "Attention"
    assert "Grade average" in at.dataframe[0].value.columns
    assert "Reason" not in at.dataframe[0].value.columns
    ayar = json.loads(at.dataframe[0].proto.columns)
    assert ayar["Grade average"]["alignment"] == "right"
    assert ayar["Grade average"]["type_config"]["format"] == "%.2f"


_CHIP = re.compile(r'<span class="tb-chip">(.*?)</span>')


def _ust_cubuk_chipleri(at: AppTest) -> list[str]:
    """Üst çubuktaki .tb-chip metinleri, ekrandaki sırayla."""
    chipler: list[str] = []
    for oge in at.markdown:
        chipler += _CHIP.findall(str(oge.value))
    return chipler


def _oturum(username: str, role: str, lang: str, related_class: str | None = None) -> AppTest:
    at = AppTest.from_file(str(_APP), default_timeout=15)
    at.session_state["token"] = "token-1"
    kullanici = {"username": username, "role": role}
    if related_class:
        kullanici["related_class"] = related_class
    at.session_state["user"] = kullanici
    at.session_state["lang"] = lang
    at.run()
    return at


def _soru_metinleri(role: str, lang: str) -> list[str]:
    return [oge["question"] for oge in _sunucu_sorulari(role, lang)]


def _kenar_sorulari(at: AppTest, role: str, lang: str) -> None:
    sorular = _soru_metinleri(role, lang)
    assert [at.button(key=f"side_q_{sira}").label for sira in range(len(sorular))] == sorular
    assert all(not str(btn.key).startswith("suggest_") for btn in at.button)


def _ornek_yaniti(role: str, lang: str) -> dict:
    return {
        "ok": True,
        "status_code": 200,
        "data": _sunucu_sorulari(role, lang),
        "message": "",
        "retry_after": None,
    }


def test_bos_sohbet_oneri_dugmesi_yok() -> None:
    with patch.object(
        api_client,
        "examples",
        side_effect=[
            _ornek_yaniti("parent", "tr"),
            _ornek_yaniti("student", "en"),
            _ornek_yaniti("principal", "tr"),
        ],
    ):
        at = _ekran_rol("parent")
        assert len(at.exception) == 0
        assert len(at.chat_message) == 0
        assert "Merhaba, ne sormak istersiniz?" in _metinler(at)
        assert "Veri soruları" not in _metinler(at)
        assert "Zor sorular" not in _metinler(at)
        _kenar_sorulari(at, "parent", "tr")
        ogrenci = _ekran_rol("student", lang="en")
        assert "Hello, what would you like to ask?" in _metinler(ogrenci)
        _kenar_sorulari(ogrenci, "student", "en")
        mudur = _ekran_rol("principal")
        _kenar_sorulari(mudur, "principal", "tr")
        assert _soru_metinleri("principal", "tr") != _soru_metinleri("parent", "tr")


def test_kenar_ornekleri_tam_listeyi_sohbete_gonderir() -> None:
    sahte = _Sahte([_veri("Sınıf ortalaması burada.")])
    with (
        patch.object(api_client, "examples", return_value=_ornek_yaniti("teacher", "tr")),
        patch.object(api_client, "query", sahte),
    ):
        at = _ekran_rol("teacher")
        sorular = _soru_metinleri("teacher", "tr")
        assert at.expander[0].label == "Neler sorabilirim?"
        metin = _metinler(at)
        assert "Veri soruları" not in metin
        assert "Zor sorular" not in metin
        assert [at.button(key=f"side_q_{sira}").label for sira in range(len(sorular))] == sorular
        at.button(key="side_q_1").click().run()
    assert len(at.exception) == 0
    assert sahte.cagrilar[-1]["question"] == sorular[1]
    assert sahte.cagrilar[-1]["lang"] == "tr"
    assert at.session_state["menu"] == "chat"


def test_beklenmeyen_ornek_bicimi_gizlenir(caplog: pytest.LogCaptureFixture) -> None:
    yanit = {
        "ok": True,
        "status_code": 200,
        "data": {"questions": ["düz metin"]},
        "message": "",
        "retry_after": None,
    }
    with caplog.at_level(logging.WARNING, logger="frontend.examples"):
        with patch.object(api_client, "examples", return_value=yanit):
            at = _ekran_rol("teacher")
    assert len(at.exception) == 0
    assert "Merhaba, ne sormak istersiniz?" in _metinler(at)
    assert "Veri soruları" not in _metinler(at)
    assert "Zor sorular" not in _metinler(at)
    assert all(bolum.label != "Neler sorabilirim?" for bolum in at.expander)
    assert all(not str(btn.key).startswith("suggest_") for btn in at.button)
    assert all(not str(btn.key).startswith("side_q_") for btn in at.button)
    assert any("beklenen biçimde değil" in kayit.message for kayit in caplog.records)


def test_ingilizce_ornek_basliklari_ve_kapsam_yazisi_yok() -> None:
    with patch.object(api_client, "examples", return_value=_ornek_yaniti("parent", "en")):
        at = _ekran_rol("parent", lang="en")
    assert len(at.exception) == 0
    metin = _metinler(at)
    assert at.expander[0].label == "What can I ask?"
    assert "Data questions" not in metin
    assert "Hard questions" not in metin
    assert [at.button(key=f"side_q_{sira}").label for sira in range(len(_soru_metinleri("parent", "en")))] == _soru_metinleri("parent", "en")
    assert "Answers are based only on the school data within your access" not in metin
    assert "cause-and-effect" not in metin


def _kenar_etiketleri(at: AppTest) -> list[str]:
    """Kenar menüdeki örnek soru düğmelerinin etiketleri, sırayla. Fazladan düğme de görünür."""
    dugmeler = [btn for btn in at.button if str(btn.key).startswith("side_q_")]
    dugmeler.sort(key=lambda btn: int(str(btn.key).removeprefix("side_q_")))
    return [btn.label for btn in dugmeler]


_ROLLER = ("principal", "teacher", "parent", "student")


@pytest.mark.parametrize("lang", ["tr", "en"])
@pytest.mark.parametrize("role", _ROLLER)
def test_kenar_menude_rolun_kendi_listesi_gorunur(role: str, lang: str) -> None:
    with patch.object(api_client, "examples", return_value=_ornek_yaniti(role, lang)):
        at = _ekran_rol(role, lang=lang)
    assert len(at.exception) == 0
    kendi = _soru_metinleri(role, lang)
    assert _kenar_etiketleri(at) == kendi
    # Başka rolün yalnız ona özgü soruları görünmez.
    for diger in _ROLLER:
        if diger == role:
            continue
        ozgu = set(_soru_metinleri(diger, lang)) - set(kendi)
        assert not ozgu & set(_kenar_etiketleri(at)), (role, diger)


def _giris_sahtesi(roller: dict[str, str]):
    def giris(username: str, password: str) -> dict:
        rol = roller[username]
        return {
            "ok": True,
            "status_code": 200,
            "data": {
                "access_token": f"tok-{rol}",
                "token_type": "bearer",
                "user": {"username": username, "role": rol},
            },
            "message": "",
            "retry_after": None,
        }

    return giris


def _sunucu_gibi_ornekler(token: str, lang: str) -> dict:
    """Backend gibi: liste jetondaki (oturumdaki) role göre döner."""
    return _ornek_yaniti(token.removeprefix("tok-"), lang)


def _forma_gir(at: AppTest, kullanici: str, sifre: str) -> None:
    at.text_input(key="kullanici_adi").set_value(kullanici)
    at.text_input(key="sifre").set_value(sifre)
    gonder = next(btn for btn in at.button if btn.label == "Giriş yap")
    gonder.click().run()


def test_cikis_ve_baska_rolle_giris_ornek_listesini_yeniler() -> None:
    roller = {"mudur": "principal", "veli": "parent"}
    with (
        patch.object(api_client, "login", side_effect=_giris_sahtesi(roller)),
        patch.object(
            api_client, "examples", side_effect=_sunucu_gibi_ornekler
        ) as ornekler,
    ):
        at = AppTest.from_file(str(_APP), default_timeout=15)
        at.session_state["lang"] = "tr"
        at.run()
        _forma_gir(at, "mudur", "x")
        assert len(at.exception) == 0
        liste_a = _kenar_etiketleri(at)
        assert ornekler.call_count == 1

        at.button(key="cikis").click().run()
        assert len(at.exception) == 0
        assert at.session_state["token"] is None
        for anahtar in ("ornek_sorular", "bekleyen_soru", "menu", "menu_ac"):
            assert anahtar not in at.session_state

        _forma_gir(at, "veli", "x")
        assert len(at.exception) == 0
        liste_b = _kenar_etiketleri(at)
        assert ornekler.call_count == 2
        assert [cagri.args[0] for cagri in ornekler.call_args_list] == [
            "tok-principal",
            "tok-parent",
        ]
    assert liste_a == _soru_metinleri("principal", "tr")
    assert liste_b == _soru_metinleri("parent", "tr")
    assert liste_b != liste_a


def _ekran_jetonlu(role: str) -> AppTest:
    """Jeton rolü taşır (tok-<rol>); örnek sorular sahtesi rolü jetondan okur."""
    at = AppTest.from_file(str(_APP), default_timeout=15)
    at.session_state["token"] = f"tok-{role}"
    at.session_state["user"] = {"username": role, "role": role}
    at.session_state["lang"] = "tr"
    at.run()
    return at


def test_ornek_onbellegi_rol_ve_dil_anahtarlidir() -> None:
    """Çıkış yapılmasa bile rol değişince eski rolün listesi kullanılmaz."""
    with patch.object(api_client, "examples", side_effect=_sunucu_gibi_ornekler) as ornekler:
        at = _ekran_jetonlu("principal")
        assert _kenar_etiketleri(at) == _soru_metinleri("principal", "tr")
        at.session_state["token"] = "tok-parent"
        at.session_state["user"] = {"username": "veli", "role": "parent"}
        at.run()
        assert _kenar_etiketleri(at) == _soru_metinleri("parent", "tr")
        assert ornekler.call_count == 2
        # Aynı rol ve dil için ikinci çizimde yeniden istek yok.
        at.run()
        assert ornekler.call_count == 2
        assert set(at.session_state["ornek_sorular"]) == {
            ("principal", "tr"),
            ("parent", "tr"),
        }


def test_401_ornek_onbellegini_de_temizler() -> None:
    sahte = _Sahte([{"ok": False, "status_code": 401, "kind": "http"}])
    with (
        patch.object(api_client, "query", sahte),
        patch.object(api_client, "examples", side_effect=_sunucu_gibi_ornekler),
    ):
        at = _ekran_jetonlu("principal")
        assert "ornek_sorular" in at.session_state
        _sor(at, "notlar")
    assert at.session_state["token"] is None
    assert "ornek_sorular" not in at.session_state


def test_ust_cubuk_kullanici_ve_rol() -> None:
    """Üst çubukta yalnız "Demo verisi" ve rol adı .tb-chip olarak görünür."""
    durumlar = [
        # (kullanıcı adı, rol, sınıf, dil, demo chip, rol chip)
        ("mudur.demo", "principal", None, "tr", "Demo verisi", "Müdür"),
        ("ogretmen.demo", "teacher", "9-A", "tr", "Demo verisi", "Sınıf öğretmeni"),
        ("ogretmen.demo", "teacher", "9-A", "en", "Demo data", "Class teacher"),
        ("mudur.demo", "principal", None, "en", "Demo data", "Principal"),
        ("veli.demo", "parent", None, "tr", "Demo verisi", "Veli"),
        ("ogrenci.demo", "student", None, "en", "Demo data", "Student"),
        # Kullanıcı adı rol adıyla aynı olsa da rol tek chip olarak kalır.
        ("Müdür", "principal", None, "tr", "Demo verisi", "Müdür"),
    ]
    for kullanici_adi, rol, sinif, lang, demo, rol_adi in durumlar:
        at = _oturum(kullanici_adi, rol, lang, related_class=sinif)
        assert len(at.exception) == 0, (rol, lang)
        chipler = _ust_cubuk_chipleri(at)
        assert chipler == [demo, rol_adi], (rol, lang, chipler)
        assert chipler.count(rol_adi) == 1
        if kullanici_adi != rol_adi:
            assert all(kullanici_adi not in chip for chip in chipler)
            assert kullanici_adi not in _metinler(at), (rol, lang)
        if sinif:
            assert all(sinif not in chip for chip in chipler)
        metin = _metinler(at)
        for eski in ("user-block", "user-name", "user-role"):
            assert eski not in metin
        assert len(at.title) == 0
        assert len(at.header) == 0


def _giris_ekrani(lang: str) -> AppTest:
    at = AppTest.from_file(str(_APP), default_timeout=15)
    at.session_state["token"] = None
    at.session_state["user"] = None
    at.session_state["lang"] = lang
    at.run()
    return at


def test_giris_metinleri_ve_logolar() -> None:
    at = _giris_ekrani("tr")
    assert len(at.exception) == 0
    assert len(at.image) == 0
    metin = _metinler(at)
    assert "Sorunuzu kendi cümlelerinizle yazın. Asistan ne sorduğunuzu anlar" in metin
    assert "Soruyu anlar, anlamsal SQL üretir, sonucu konuşur gibi açıklar." in metin
    assert "Her sorgu kurallardan geçer; satır düzeyi güvenlik herkesi kendi verisiyle sınırlar." in metin
    assert (
        "OULAD'da modellerle karşılaştırılan iki sinyalli kuralın okul verisindeki karşılığı."
        in html.unescape(metin)
    )
    assert "Türksat A.Ş. yaz stajı çalışması · Demo sürümü, örnek okul verisiyle çalışır" in metin
    assert "Sınıfımda dikkat bayrağı olan öğrenci var mı?" not in metin
    assert "Zeynep Demir" not in metin
    assert "Türksat Yaz Stajı 2026" not in metin
    assert "Yaz stajı projesi · 2026" not in metin
    assert "Türksat yaz stajı kapsamında geliştirilmiştir" not in metin
    assert 'class="logo-img' in metin
    assert 'alt="Türksat"' in metin
    assert "data:image/png;base64," in metin
    assert "data:image/svg+xml;base64," in metin

    ingilizce = _giris_ekrani("en")
    assert len(ingilizce.exception) == 0
    ingilizce_metin = _metinler(ingilizce)
    assert "Write your question in your own words." in ingilizce_metin
    assert "produces semantic SQL" in ingilizce_metin
    assert "row-level security limits each person to their own data." in ingilizce_metin
    assert "compared against models on OULAD" in ingilizce_metin
    assert "Türksat Inc. summer internship project · Demo version, runs on sample school data" in ingilizce_metin
    assert "Is there a student in my class with an attention flag?" not in ingilizce_metin
    assert "Zeynep Demir" not in ingilizce_metin
    assert "Türksat Summer Internship 2026" not in ingilizce_metin
    assert "Summer internship project · 2026" not in ingilizce_metin
    assert "Developed as part of the Türksat summer internship" not in ingilizce_metin


def test_oturumda_logolar_st_image_degil() -> None:
    """Logolar st.image ile değil: marka st.logo, Türksat ve avatar base64 img."""
    with patch("streamlit.logo") as logo:
        at = _ekran_rol("parent")
    assert len(at.exception) == 0
    assert len(at.image) == 0

    # Marka: st.logo, logo_wordmark.svg dosyasıyla ve büyük boyutta.
    assert logo.call_count == 1
    args, kwargs = logo.call_args
    assert len(args) == 1
    assert Path(args[0]).name == "logo_wordmark.svg"
    assert Path(args[0]).is_file()
    assert kwargs == {"size": "large"}

    # Türksat (kenar menü altı) ve avatar: base64 img.
    metin = _metinler(at)
    imgler = re.findall(r'<img class="logo-img ([^"]*)"[^>]*>', metin)
    assert imgler.count("logo-side-mark") == 1
    assert imgler.count("logo-avatar") == 1
    yan = re.search(r'<img class="logo-img logo-side-mark"[^>]*>', metin)
    assert yan is not None
    assert 'alt="Türksat"' in yan.group(0)
    assert 'src="data:image/png;base64,' in yan.group(0)
    avatar = re.search(r'<img class="logo-img logo-avatar"[^>]*>', metin)
    assert avatar is not None
    assert 'src="data:image/' in avatar.group(0)

    # Eski kenar menü marka bloğu yok; marka st.markdown img olarak da verilmez.
    assert 'class="logo-img logo-side"' not in metin
    assert "logo_wordmark" not in metin
    assert "data:image/" in metin


def test_sayfa_ikonu_favicon_ile_ayarlanir() -> None:
    with patch("streamlit.set_page_config") as ayar:
        at = _ekran_rol("parent")
    assert len(at.exception) == 0
    assert ayar.call_count == 1
    kwargs = ayar.call_args.kwargs
    assert "page_icon" in kwargs
    assert Path(kwargs["page_icon"]) == _FRONTEND / "assets" / "favicon.png"
    assert Path(kwargs["page_icon"]).is_file()
    assert kwargs["page_title"] == "Akıllı Okul Bilgi Sistemi"


def test_calisma_gostergesi_genel_kuralla_gizlenir() -> None:
    css = (_FRONTEND / "theme.css").read_text(encoding="utf-8")
    assert css.count('[data-testid="stStatusWidget"]') == 1
    assert '.stApp:has(.login-mode) [data-testid="stStatusWidget"]' not in css


def test_tema_ikinci_tur_secicileri() -> None:
    css = (_FRONTEND / "theme.css").read_text(encoding="utf-8")
    assert ".st-key-topbar" in css
    assert 'div[data-testid="stVerticalBlock"] > div:has(> .st-key-topbar)' in css
    assert "position: sticky" in css
    assert "top: 0" in css
    assert "min-height: 0" in css
    assert "max-height: 100%" in css
    assert ".st-key-sidebar_footer" in css
    assert "max-width: 75%" in css
    assert "18px 18px 4px 18px" in css
    assert ".st-key-brand_mid" in css
    assert "max-width: 560px" in css
    assert "justify-content: center" in css
    assert "bottom: 0" in css
    assert "div:has(> .st-key-sidebar_footer)" in css
    assert '[data-testid="stSidebarContent"]' in css
    assert '[data-testid="stSidebarUserContent"]' in css
    assert "min-height: 100%" in css
    assert "width: 44px" in css
    assert "#8C0B1E" in css
    assert ".chat-end-pad" in css
    assert "summary:focus-visible" in css
    assert "pointer-events: none" in css
    assert '[data-testid="stHeader"]' in css
    assert '[data-testid="stDecoration"]' in css
