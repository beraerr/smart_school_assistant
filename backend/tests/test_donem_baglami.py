"""Tarih bloğu, türetilmiş sayılar, geçmiş sayıları, düzeltme turu ve geri dönüş.

Gerçek model API'si ve gerçek veritabanı yok: sahte istemci ve sahte oturum.
"""

import json
import logging
import sys
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.core.logging_config import query_logger
from backend.app.core.sql_safety import validate_select_only
from backend.app.services import assistant_service
from backend.app.services.assistant_service import (
    GROUNDING_GERI_DONUS,
    YEDEK_CEVAP,
    _arac_siniri,
    _gecmis_sayilari,
    dayanaksiz_sayilar,
    format_date_block,
    load_date_block,
    run_assistant,
)
from backend.app.services.takvim import ozet_en, ozet_tr
from backend.tests.sahte_model import SahteIstemci
from config.settings import settings

_DAYANAKSIZ_TR = "Bu cevaptaki sayıları doğrulayamadım; daha belirli bir soru sorabilir misiniz?"
_ARAC_HATA = "Çalıştırma hatası, şemadaki sütunlarla basitleştir."

_SEMA = "Şema özeti:\n- grades.subject değerleri: Matematik, Fizik"


@pytest.fixture(autouse=True)
def _sema_sahte(monkeypatch: pytest.MonkeyPatch) -> None:
    """Şema özeti veritabanından okunmaz."""
    monkeypatch.setattr(assistant_service, "build_schema_context", lambda: _SEMA)


# --- Sahte oturum: set_config ve MIN/MAX sorguları ---


class _Sonuc:
    def __init__(self, satir: object) -> None:
        self._satir = satir

    def one(self) -> object:
        return self._satir


class _SahteOturum:
    def __init__(self, notlar: tuple, devam: tuple) -> None:
        self.notlar = SimpleNamespace(ilk=notlar[0], son=notlar[1])
        self.devam = SimpleNamespace(ilk=devam[0], son=devam[1])
        self.cagrilar: list[tuple[str, dict | None]] = []
        self.kapandi = False

    def connection(self) -> None:
        return None

    def execute(self, stmt: object, params: dict | None = None) -> _Sonuc:
        sql = str(stmt)
        self.cagrilar.append((sql, params))
        if "FROM grades" in sql:
            return _Sonuc(self.notlar)
        if "FROM attendance" in sql:
            return _Sonuc(self.devam)
        return _Sonuc(None)

    def close(self) -> None:
        self.kapandi = True


_KULLANICI = SimpleNamespace(
    role="principal", username="principal", related_class=None, related_id=None
)
_NOT_ARALIGI = (date(2026, 9, 14), date(2026, 11, 3))
_DEVAM_ARALIGI = (date(2026, 9, 14), date(2026, 11, 4))


def _oturum_ac(
    monkeypatch: pytest.MonkeyPatch,
    notlar: tuple = _NOT_ARALIGI,
    devam: tuple = _DEVAM_ARALIGI,
) -> list[_SahteOturum]:
    acilan: list[_SahteOturum] = []

    def _fabrika() -> _SahteOturum:
        oturum = _SahteOturum(notlar, devam)
        acilan.append(oturum)
        return oturum

    monkeypatch.setattr(assistant_service, "AppSessionLocal", _fabrika)
    return acilan


def _bugun(monkeypatch: pytest.MonkeyPatch, gun: date) -> None:
    monkeypatch.setattr(settings, "DEMO_TODAY", gun)


# --- Görev 1: Tarih bloğu ---


def test_tarih_blogu_tr(monkeypatch: pytest.MonkeyPatch) -> None:
    _bugun(monkeypatch, date(2026, 11, 4))
    acilan = _oturum_ac(monkeypatch)
    blok = load_date_block(_KULLANICI, "tr")
    assert blok == "\n".join(
        [
            "[Tarih]",
            "bugün: 2026-11-04 (Çarşamba)",
            "dönem: 1. dönem (2026-09-14 .. 2027-01-22)",
            "görünür veri aralığı, notlar: 2026-09-14 .. 2026-11-03",
            "görünür veri aralığı, devamsızlık: 2026-09-14 .. 2026-11-04",
            f"takvim: {ozet_tr()}",
            "[/Tarih]",
        ]
    )
    # Veri aralığı RLS'li oturumda okunur: önce bağlam (app.today dahil), sonra iki ayrı sorgu.
    (oturum,) = acilan
    sqller = [sql for sql, _ in oturum.cagrilar]
    assert "app.today" in " ".join(sqller[:4])
    assert [p for sql, p in oturum.cagrilar if "app.today" in sql] == [
        {"value": "2026-11-04"}
    ]
    sorgular = [sql for sql in sqller if "MIN(date)" in sql]
    assert len(sorgular) == 2
    assert "FROM grades" in sorgular[0] and "FROM attendance" not in sorgular[0]
    assert "FROM attendance" in sorgular[1] and "FROM grades" not in sorgular[1]
    assert sqller.index(sorgular[0]) > max(
        i for i, sql in enumerate(sqller) if "set_config" in sql
    )
    assert oturum.kapandi is True


def test_tarih_blogu_en(monkeypatch: pytest.MonkeyPatch) -> None:
    _bugun(monkeypatch, date(2026, 11, 4))
    _oturum_ac(monkeypatch)
    blok = load_date_block(_KULLANICI, "en")
    assert blok == "\n".join(
        [
            "[Tarih]",
            "today: 2026-11-04 (Wednesday)",
            "term: First term (2026-09-14 .. 2027-01-22)",
            "visible data range, grades: 2026-09-14 .. 2026-11-03",
            "visible data range, attendance: 2026-09-14 .. 2026-11-04",
            f"calendar: {ozet_en()}",
            "[/Tarih]",
        ]
    )


def test_tarih_blogu_her_istekte_kurulur_ve_bugunle_degisir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    acilan = _oturum_ac(monkeypatch)
    _bugun(monkeypatch, date(2026, 11, 4))
    birinci = load_date_block(_KULLANICI, "tr")
    _bugun(monkeypatch, date(2026, 11, 18))
    ikinci = load_date_block(_KULLANICI, "tr")
    assert len(acilan) == 2  # önbellek yok: her çağrıda yeni oturum, yeni okuma
    assert birinci != ikinci
    assert "bugün: 2026-11-04 (Çarşamba)" in birinci
    assert "dönem: 1. dönem (" in birinci
    assert "bugün: 2026-11-18 (Çarşamba)" in ikinci
    # Dönem durumu adı ve tarihleri bloğa girer (ara tatil, dönemden önceliklidir).
    assert "dönem: 1. dönem ara tatili (2026-11-16 .. 2026-11-20)" in ikinci
    assert [p for sql, p in acilan[1].cagrilar if "app.today" in sql] == [
        {"value": "2026-11-18"}
    ]


def test_tarih_blogu_kayit_yoksa_ve_donem_disinda(monkeypatch: pytest.MonkeyPatch) -> None:
    blok = format_date_block(date(2026, 8, 1), (None, None), (None, None), "tr")
    assert "dönem: Okul öncesi (- .. 2026-09-13)" in blok
    assert "görünür veri aralığı, notlar: kayıt yok" in blok
    assert "görünür veri aralığı, devamsızlık: kayıt yok" in blok
    en = format_date_block(date(2027, 7, 1), (None, None), (None, None), "en")
    assert "term: Summer break (2027-06-26 .. -)" in en
    assert "visible data range, grades: no records" in en


def test_tarih_blogu_talimata_girer_ve_istege_gore_degisir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _oturum_ac(monkeypatch)
    _bugun(monkeypatch, date(2026, 11, 4))
    blok_a = load_date_block(_KULLANICI, "tr")
    _bugun(monkeypatch, date(2026, 11, 18))
    blok_b = load_date_block(_KULLANICI, "tr")

    sistemler = []
    for blok in (blok_a, blok_b):
        istemci = SahteIstemci(["Merhaba."])
        run_assistant(
            [{"role": "user", "content": "merhaba"}],
            "principal",
            "tr",
            client=istemci,
            run_sql=lambda sql: {"ok": False},
            identity="[Kimlik]\nkullanıcı: principal\n[/Kimlik]",
            date_block=blok,
        )
        sistemler.append(istemci.cagrilar[0]["system"])
    assert blok_a in sistemler[0] and blok_b not in sistemler[0]
    assert blok_b in sistemler[1] and blok_a not in sistemler[1]
    assert "bugün: 2026-11-04" in sistemler[0]
    assert "bugün: 2026-11-18" in sistemler[1]
    assert "1. dönem ara tatili" in sistemler[1]
    # Kimlik bloğunun yanında durur.
    assert sistemler[0].index("[Kimlik]") < sistemler[0].index("[Tarih]")


def test_talimatta_tarih_kurallari_tr() -> None:
    istemci = SahteIstemci(["Tamam."])
    run_assistant(
        [{"role": "user", "content": "merhaba"}],
        "teacher",
        "tr",
        client=istemci,
        run_sql=lambda sql: {"ok": False},
        date_block="[Tarih]\nbugün: 2026-11-04 (Çarşamba)\n[/Tarih]",
    )
    sistem = istemci.cagrilar[0]["system"]
    for parca in (
        'Göreli tarihler ("bugün", "dün", "bu hafta", "bu ay", "geçen ay", "bu dönem") '
        "yalnızca yukarıdaki Tarih bloğuna göre yorumlanır.",
        "Soru tatile veya hafta sonuna denk geliyorsa bunu söyle ve en yakın okul gününü "
        "ya da dönemi öner.",
        "Sorulan tarih görünür veri aralığının dışındaysa aralığı bildir ve o aralıkta "
        "cevaplamayı öner.",
        "SQL'de CURRENT_DATE veya NOW() yazma; Tarih bloğundaki tarihi sabit değer olarak "
        "yaz (örnek: DATE 'YYYY-MM-DD').",
    ):
        assert parca in sistem
    assert "Bugünün tarihi" not in sistem


def test_talimatta_tarih_kurallari_en() -> None:
    istemci = SahteIstemci(["Okay."])
    run_assistant(
        [{"role": "user", "content": "hello"}],
        "teacher",
        "en",
        client=istemci,
        run_sql=lambda sql: {"ok": False},
        date_block="[Tarih]\ntoday: 2026-11-04 (Wednesday)\n[/Tarih]",
    )
    sistem = istemci.cagrilar[0]["system"]
    for parca in (
        'Relative dates ("today", "yesterday", "this week", "this month", "last month", '
        '"this term") are interpreted only against the Date block above.',
        "If the question falls on a holiday or a weekend, say so and suggest the nearest "
        "school day or term.",
        "If the date asked about is outside the visible data range, state the range and "
        "suggest answering within it.",
        "In SQL, do not write CURRENT_DATE or NOW(); write the date from the Date block "
        "as a fixed value (example: DATE 'YYYY-MM-DD').",
    ):
        assert parca in sistem


# --- Görev 2: türetilmiş sayılar SQL'de ---


@pytest.mark.parametrize("dil", ["tr", "en"])
def test_talimatta_turetilmis_sayi_kurali_ve_lag_ornegi(dil: str) -> None:
    istemci = SahteIstemci(["Tamam."])
    run_assistant(
        [{"role": "user", "content": "merhaba"}],
        "principal",
        dil,
        client=istemci,
        run_sql=lambda sql: {"ok": False},
    )
    sistem = istemci.cagrilar[0]["system"]
    assert "LAG(AVG(grade)) OVER (ORDER BY DATE_TRUNC('month', date))" in sistem
    if dil == "tr":
        assert "her türetilmiş sayı (fark, değişim, yüzde, oran, sıra, sayım," in sistem
    else:
        assert "Every derived number you write in the answer (difference, change," in sistem
    # Örnek sorgu, SQL izin listesinden geçer.
    sql = next(
        satir.split(": ", 1)[1]
        for satir in sistem.splitlines()
        if satir.startswith(("Örnek, aylık ortalama", "Example, monthly average"))
    )
    validate_select_only(sql)


# --- Görev 3: önceki cevaplardaki sayılar ---


def _gecmis(*mesajlar: tuple[str, str]) -> list[dict]:
    return [{"role": rol, "content": icerik} for rol, icerik in mesajlar]


def test_gecmisteki_asistan_sayisi_izinli_diger_roller_degil() -> None:
    izinli: set[float] = set()
    _gecmis_sayilari(
        _gecmis(
            ("user", "5 öğrenci"),
            ("assistant", "9-A ortalaması 74,01."),
            ("system", "ortalama 63,50"),
            ("tool", "ortalama 58,25"),
        ),
        izinli,
    )
    assert 74.01 in izinli
    assert 5.0 in izinli
    assert 63.5 not in izinli
    assert 58.25 not in izinli


def test_74_01_gecmisteki_asistan_mesajindan_izinli() -> None:
    istemci = SahteIstemci(["9-A ortalaması 74,01 idi; bu turda yeniden sorgulamadım."])
    sonuc = run_assistant(
        _gecmis(
            ("user", "Sınıfların ortalaması?"),
            ("assistant", "9-A ortalaması 74,01; 9-B ortalaması 78,40."),
            ("user", "9-A neden diğer sınıflardan düşük?"),
        ),
        "principal",
        "tr",
        client=istemci,
        run_sql=lambda sql: (_ for _ in ()).throw(AssertionError("run_sql yok")),
    )
    assert sonuc.grounding_retry is False
    assert sonuc.grounding_fallback is False
    assert sonuc.tool_calls == 0
    assert sonuc.answer.startswith("9-A ortalaması 74,01 idi")


@pytest.mark.parametrize(
    "gecmis",
    [
        # Hiç geçmeyen sayı.
        _gecmis(("user", "9-A neden düşük?")),
        # Asistan ve kullanıcı dışındaki rolde geçen sayı.
        _gecmis(("system", "9-A ortalaması 74,01"), ("user", "9-A neden düşük?")),
        _gecmis(("tool", "9-A ortalaması 74,01"), ("user", "9-A neden düşük?")),
    ],
)
def test_74_01_baska_rolde_ya_da_hic_gecmeyen_sayi_izinli_degil(gecmis: list[dict]) -> None:
    istemci = SahteIstemci(["9-A ortalaması 74,01.", "9-A ortalaması 74,01."])
    sonuc = run_assistant(
        gecmis,
        "principal",
        "tr",
        client=istemci,
        run_sql=lambda sql: (_ for _ in ()).throw(AssertionError("run_sql yok")),
    )
    assert sonuc.grounding_retry is True
    assert sonuc.answer == _DAYANAKSIZ_TR
    assert "74,01" in istemci.cagrilar[1]["system"]


def test_iki_izinli_sayinin_farki_izinli_degil() -> None:
    gecmis = _gecmis(
        ("assistant", "Eylül ortalaması 74,01."),
        ("assistant", "Ekim ortalaması 71,18."),
        ("user", "Aradaki fark ne kadar?"),
    )
    izinli: set[float] = set()
    _gecmis_sayilari(gecmis, izinli)
    assert dayanaksiz_sayilar("Eylül 74,01, Ekim 71,18.", izinli) == []
    assert dayanaksiz_sayilar("Fark 2,83.", izinli) == ["2,83"]  # 74,01 - 71,18
    assert dayanaksiz_sayilar("Oran 1,04.", izinli) == ["1,04"]  # 74,01 / 71,18
    istemci = SahteIstemci(["Fark 2,83.", "Fark 2,83."])
    sonuc = run_assistant(
        gecmis,
        "principal",
        "tr",
        client=istemci,
        run_sql=lambda sql: (_ for _ in ()).throw(AssertionError("run_sql yok")),
    )
    assert sonuc.grounding_retry is True
    assert sonuc.answer == _DAYANAKSIZ_TR
    assert "2,83" in istemci.cagrilar[1]["system"]


# --- Görev 4: "0.48" senaryosu ve düzeltme notu ---

_AYLIK = {
    "ok": True,
    "rows": [
        {"ay": "2026-09-01", "ortalama": 71.66},
        {"ay": "2026-10-01", "ortalama": 71.18},
    ],
    "row_count": 2,
    "truncated": False,
}
_FARKLI = {
    "ok": True,
    "rows": [
        {"ay": "2026-09-01", "ortalama": 71.66, "onceki_aya_fark": None},
        {"ay": "2026-10-01", "ortalama": 71.18, "onceki_aya_fark": -0.48},
    ],
    "row_count": 2,
    "truncated": False,
}
_SQL_AYLIK = (
    "SELECT DATE_TRUNC('month', date) AS ay, ROUND(AVG(grade)::numeric, 2) AS ortalama "
    "FROM grades GROUP BY DATE_TRUNC('month', date) ORDER BY ay"
)
_SQL_FARKLI = (
    "SELECT DATE_TRUNC('month', date) AS ay, ROUND(AVG(grade)::numeric, 2) AS ortalama, "
    "ROUND((AVG(grade) - LAG(AVG(grade)) OVER (ORDER BY DATE_TRUNC('month', date)))"
    "::numeric, 2) AS onceki_aya_fark FROM grades GROUP BY DATE_TRUNC('month', date) "
    "ORDER BY ay"
)


def test_sql_ornekleri_izin_listesinden_gecer() -> None:
    validate_select_only(_SQL_AYLIK)
    validate_select_only(_SQL_FARKLI)


def test_0_48_fark_reddedilir_duzeltme_yeni_sorguyla_kabul() -> None:
    sorgular: list[str] = []

    def run_sql(sql: str) -> dict:
        sorgular.append(sql)
        return _FARKLI if "LAG" in sql else _AYLIK

    istemci = SahteIstemci(
        [
            [_SQL_AYLIK],
            "Eylül 71,66, Ekim 71,18; aradaki fark 0.48 puan.",
            [_SQL_FARKLI],
            "Ekim ortalaması 71,18; Eylül'e göre 0,48 puan düştü.",
        ]
    )
    sonuc = run_assistant(
        [{"role": "user", "content": "Geçen aya göre okul ortalaması nasıl değişti?"}],
        "principal",
        "tr",
        client=istemci,
        run_sql=run_sql,
    )
    # İlk cevap: fark SQL sonucunda yoktu, reddedildi.
    assert sonuc.grounding_retry is True
    # Düzeltme notu reddedilen sayıyı açıkça listeler ve yönlendirir.
    not_metni = istemci.cagrilar[2]["system"]
    assert "Cevabındaki şu sayılar sorgu sonuçlarında yok: 0.48." in not_metni
    assert (
        "Bu sayıları ya yeni bir run_sql sorgusunda hesaplayıp sonuçtan yaz ya da "
        "cümleden çıkar; özür dileme, düzeltme yaptığını söyleme."
    ) in not_metni
    assert "tools" in istemci.cagrilar[2]
    # Düzeltme turunda fark sütunlu yeni sorgu: cevap kabul edilir.
    assert sorgular == [_SQL_AYLIK, _SQL_FARKLI]
    assert sonuc.grounding_fallback is False
    assert sonuc.answer == "Ekim ortalaması 71,18; Eylül'e göre 0,48 puan düştü."
    assert sonuc.tool_calls == 2
    assert sonuc.results == _FARKLI["rows"]


def test_duzeltme_notu_en() -> None:
    istemci = SahteIstemci(
        [
            ["SELECT 1"],
            "The difference is 0.48.",
            "The difference is 0.48.",
        ]
    )
    run_assistant(
        [{"role": "user", "content": "How did the average change?"}],
        "principal",
        "en",
        client=istemci,
        run_sql=lambda sql: _AYLIK,
    )
    not_metni = istemci.cagrilar[2]["system"]
    assert "These numbers in your answer are not in the query results: 0.48." in not_metni
    assert (
        "Either compute these numbers in a new run_sql query and write them from the "
        "result, or remove them from the sentence; do not apologize, do not say you "
        "made a correction."
    ) in not_metni


def test_negatif_sutun_degeri_isaretsiz_cevabi_dayandirir_ama_baska_sayiyi_degil() -> None:
    izinli: set[float] = set()
    assistant_service._sonuc_sayilari(_FARKLI, izinli)
    assert dayanaksiz_sayilar("0,48 puan düştü.", izinli) == []
    assert dayanaksiz_sayilar("0,49 puan düştü.", izinli) == ["0,49"]
    assert dayanaksiz_sayilar("Fark 0,48; yüzde 0,67.", izinli) == ["0,67"]


# --- Görev 4: bütçe kuralı ---


def test_arac_butcesi_tek_yerde() -> None:
    assert assistant_service._AZAMI_ARAC == 3
    assert assistant_service._DUZELTME_EK_ARAC == 1
    assert _arac_siniri(False, 0) == 3
    assert _arac_siniri(False, 3) == 3
    assert _arac_siniri(True, 0) == 3
    assert _arac_siniri(True, 2) == 3
    assert _arac_siniri(True, 3) == 4
    assert _arac_siniri(True, 4) == 4


def test_butce_bitmediyse_duzeltmede_ek_hak_yok() -> None:
    gorulen: list[str] = []

    def run_sql(sql: str) -> dict:
        gorulen.append(sql)
        return _AYLIK

    istemci = SahteIstemci(
        [
            ["SELECT 1"],
            "Fark 0.48.",
            ["SELECT 2", "SELECT 3", "SELECT 4"],
            "Ekim 71,18.",
        ]
    )
    sonuc = run_assistant(
        [{"role": "user", "content": "fark?"}],
        "principal",
        "tr",
        client=istemci,
        run_sql=run_sql,
    )
    # 1 kullanıldı: düzeltmede toplam sınır 3; ek hak yalnızca bütçe bitmişse tanınır.
    assert gorulen == ["SELECT 1", "SELECT 2", "SELECT 3"]
    assert sonuc.tool_calls == 3


def test_butce_bittiyse_duzeltmede_tam_bir_ek_cagri_besinci_yok() -> None:
    gorulen: list[str] = []

    def run_sql(sql: str) -> dict:
        gorulen.append(sql)
        return _FARKLI if sql == "SELECT 4" else _AYLIK

    istemci = SahteIstemci(
        [
            ["SELECT 1"],
            ["SELECT 2"],
            ["SELECT 3"],
            "Fark 0.48.",
            ["SELECT 4", "SELECT 5"],
            "Eylül'e göre 0,48 puan düştü.",
        ]
    )
    sonuc = run_assistant(
        [{"role": "user", "content": "fark?"}],
        "principal",
        "tr",
        client=istemci,
        run_sql=run_sql,
    )
    assert gorulen == ["SELECT 1", "SELECT 2", "SELECT 3", "SELECT 4"]
    assert "SELECT 5" not in gorulen
    assert sonuc.tool_calls == 4
    assert sonuc.answer == "Eylül'e göre 0,48 puan düştü."
    assert sonuc.grounding_fallback is False


# --- Görev 5: zarif geri dönüş ---


def test_duzeltme_de_basarisizsa_geri_donus_sonuclar_kalir() -> None:
    istemci = SahteIstemci([[_SQL_AYLIK], "Fark 0.48.", "Yine fark 0.48."])
    sonuc = run_assistant(
        [{"role": "user", "content": "Geçen aya göre okul ortalaması nasıl değişti?"}],
        "principal",
        "tr",
        client=istemci,
        run_sql=lambda sql: _AYLIK,
    )
    assert sonuc.grounding_retry is True
    assert sonuc.grounding_fallback is True
    assert sonuc.answer == (
        "Sorgu sonuçlarını aşağıda gösteriyorum; bazı hesaplamaları doğrulayamadığım "
        "için yorum eklemedim."
    )
    assert sonuc.answer == GROUNDING_GERI_DONUS["tr"]
    assert "doğrulayamadım;" not in sonuc.answer
    assert sonuc.results == _AYLIK["rows"]
    assert sonuc.row_count == 2
    assert sonuc.sql == [_SQL_AYLIK]


def test_geri_donus_en() -> None:
    istemci = SahteIstemci([["SELECT 1"], "Change 0.48.", "Change 0.48."])
    sonuc = run_assistant(
        [{"role": "user", "content": "How did the average change?"}],
        "principal",
        "en",
        client=istemci,
        run_sql=lambda sql: _AYLIK,
    )
    assert sonuc.grounding_fallback is True
    assert sonuc.answer == GROUNDING_GERI_DONUS["en"]
    assert sonuc.results == _AYLIK["rows"]


def test_basarili_cevapta_geri_donus_bayragi_yok() -> None:
    istemci = SahteIstemci([["SELECT 1"], "Eylül 71,66, Ekim 71,18."])
    sonuc = run_assistant(
        [{"role": "user", "content": "aylık ortalama"}],
        "principal",
        "tr",
        client=istemci,
        run_sql=lambda sql: _AYLIK,
    )
    assert sonuc.grounding_fallback is False
    assert sonuc.grounding_retry is False


@contextmanager
def _kayitlar(caplog: pytest.LogCaptureFixture):
    query_logger.addHandler(caplog.handler)
    try:
        with caplog.at_level(logging.INFO, logger=query_logger.name):
            yield caplog
    finally:
        query_logger.removeHandler(caplog.handler)


def _olaylar(caplog: pytest.LogCaptureFixture, olay: str) -> list[dict]:
    sonuc = []
    for kayit in caplog.records:
        if kayit.name != query_logger.name:
            continue
        veri = json.loads(kayit.getMessage())
        if veri.get("event") == olay:
            sonuc.append(veri)
    return sonuc


def test_hic_basarili_sorgu_yoksa_yedek_cevap_ve_basarisiz_sql_loglanir(
    caplog: pytest.LogCaptureFixture,
) -> None:
    cagrilar = {"n": 0}

    def run_sql(sql: str) -> dict:
        cagrilar["n"] += 1
        if cagrilar["n"] == 1:
            return {"ok": False, "reason": "validation: İzin verilmeyen fonksiyon: lead"}
        raise RuntimeError("boom")

    istemci = SahteIstemci(
        [
            ["SELECT LEAD(grade) OVER (ORDER BY date) FROM grades"],
            ["SELECT broken FROM grades"],
            "Fark 12,34.",
            "Fark 12,34.",
        ]
    )
    with _kayitlar(caplog):
        sonuc = run_assistant(
            [{"role": "user", "content": "fark nedir?"}],
            "principal",
            "tr",
            client=istemci,
            run_sql=run_sql,
        )
    assert sonuc.answer == YEDEK_CEVAP["tr"]
    assert sonuc.grounding_fallback is False
    assert sonuc.results == []
    beklenen = [
        {
            "sql": "SELECT LEAD(grade) OVER (ORDER BY date) FROM grades",
            "reason": "validation: İzin verilmeyen fonksiyon: lead",
        },
        {"sql": "SELECT broken FROM grades", "reason": "RuntimeError: boom"},
    ]
    kayit = _olaylar(caplog, "assistant_fallback")[-1]
    assert kayit["reason"] == "no_successful_query"
    assert kayit["failed_tool_calls"] == 2
    assert kayit["failed_calls"] == beklenen
    assert _olaylar(caplog, "ungrounded_number")[-1]["failed_calls"] == beklenen
    # Neden modele ve kullanıcıya gitmez.
    for cagri in istemci.cagrilar[1:]:
        gonderilen = json.dumps(cagri["messages"], ensure_ascii=False)
        assert "İzin verilmeyen fonksiyon" not in gonderilen
        assert "RuntimeError" not in gonderilen
        assert _ARAC_HATA in gonderilen
    assert "lead" not in sonuc.answer.lower()


def test_sorgusuz_dayanaksiz_cevap_eski_mesajda_kalir() -> None:
    istemci = SahteIstemci(["Fark 12,34.", "Fark 12,34."])
    sonuc = run_assistant(
        [{"role": "user", "content": "fark nedir?"}],
        "principal",
        "tr",
        client=istemci,
        run_sql=lambda sql: (_ for _ in ()).throw(AssertionError("run_sql yok")),
    )
    assert sonuc.grounding_fallback is False
    assert sonuc.answer == _DAYANAKSIZ_TR


# --- /query bağlantısı: tarih bloğu ve grounding_fallback alanı (gerçek veritabanı yok) ---


class _SahteDb:
    def execute(self, stmt: object, params: dict | None = None) -> "_SahteDb":
        return self

    def mappings(self) -> "_SahteDb":
        return self

    def fetchmany(self, _n: int) -> list[dict]:
        return list(_AYLIK["rows"])

    def rollback(self) -> None:
        return None


def _sorgu_govdesi(question: str) -> object:
    from backend.app.api.query import QueryRequest

    return QueryRequest(question=question, lang="tr")


def _query_baglanti(monkeypatch: pytest.MonkeyPatch, istemci: SahteIstemci) -> list[str]:
    from backend.app.api import query as query_api

    istekler: list[str] = []

    def _tarih(user: object, lang: str) -> str:
        istekler.append(lang)
        return f"[Tarih]\nbugün: istek-{len(istekler)}\n[/Tarih]"

    def _db(user: object):
        yield _SahteDb()

    monkeypatch.setattr(query_api, "_model_istemcisi", lambda: istemci)
    monkeypatch.setattr(query_api, "load_date_block", _tarih)
    monkeypatch.setattr(query_api, "load_identity_block", lambda u, d: "[Kimlik]\n[/Kimlik]")
    monkeypatch.setattr(query_api, "get_db_with_context", _db)
    return istekler


def test_query_her_istekte_tarih_blogu_kurar(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.api.query import run_query

    istemci = SahteIstemci(["Merhaba.", "Merhaba."])
    istekler = _query_baglanti(monkeypatch, istemci)
    yonetici = SimpleNamespace(
        role="principal", username="u", related_class=None, related_id=None
    )
    run_query(_sorgu_govdesi("merhaba"), current_user=yonetici)
    run_query(_sorgu_govdesi("merhaba"), current_user=yonetici)
    assert istekler == ["tr", "tr"]
    assert "bugün: istek-1" in istemci.cagrilar[0]["system"]
    assert "bugün: istek-2" in istemci.cagrilar[1]["system"]


def test_query_grounding_fallback_alani_ve_basarisiz_sql_nedeni(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from backend.app.api.query import run_query

    istemci = SahteIstemci(
        [
            ["SELECT * FROM users"],
            ["SELECT AVG(grade) AS ortalama FROM grades"],
            "Fark 0.48.",
            "Yine fark 0.48.",
        ]
    )
    _query_baglanti(monkeypatch, istemci)
    yonetici = SimpleNamespace(
        role="principal", username="u", related_class=None, related_id=None
    )
    with _kayitlar(caplog):
        yanit = run_query(_sorgu_govdesi("fark nedir?"), current_user=yonetici)
    assert yanit.grounding_fallback is True
    assert yanit.grounding_retry is True
    assert yanit.answer == GROUNDING_GERI_DONUS["tr"]
    assert yanit.results == _AYLIK["rows"]
    assert yanit.model_dump()["grounding_fallback"] is True
    son = _olaylar(caplog, "ungrounded_number")[-1]
    assert son["failed_calls"][0]["sql"] == "SELECT * FROM users"
    assert son["failed_calls"][0]["reason"].startswith("validation: ")
    assert "users" in son["failed_calls"][0]["reason"]
    # Neden modele gitmez.
    assert "validation:" not in json.dumps(istemci.cagrilar[1]["messages"], ensure_ascii=False)
