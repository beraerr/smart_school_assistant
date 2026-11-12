"""Dayanak kontrolü ve (A)/(B) cevapları: sahte model, gerçek API ve veritabanı yok."""

import json
import logging
import sys
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.core.logging_config import query_logger
from backend.app.services.assistant_service import (
    GROUNDING_GERI_DONUS,
    YEDEK_CEVAP,
    _metin_sayilari,
    _sonuc_sayilari,
    dayanaksiz_sayilar,
    run_assistant,
)
from backend.tests.sahte_model import SahteIstemci
from config.settings import settings

_DURUST = "Bu cevaptaki sayıları doğrulayamadım; daha belirli bir soru sorabilir misiniz?"


def _izinli(*satirlar: dict, row_count: int | None = None) -> set[float]:
    hedef: set[float] = set()
    _sonuc_sayilari(
        {
            "ok": True,
            "rows": list(satirlar),
            "row_count": len(satirlar) if row_count is None else row_count,
        },
        hedef,
    )
    return hedef


def _soru(metin: str) -> list[dict]:
    return [{"role": "user", "content": metin}]


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
        mesaj = kayit.getMessage()
        assert "\n" not in mesaj
        veri = json.loads(mesaj)
        if veri.get("event") == olay:
            sonuc.append(veri)
    return sonuc


# --- 1b: sayı normalleştirme, cevap ve sonuç tarafı aynı kuralla ---


@pytest.mark.parametrize("deger", [Decimal("65.32"), 65.32, "65.32", "65,32"])
@pytest.mark.parametrize("cevap", ["65,32", "65.32"])
def test_virgullu_ve_noktali_ayni_sayi_eslesir(deger: object, cevap: str) -> None:
    izinli = _izinli({"ortalama": deger})
    assert dayanaksiz_sayilar(f"Ortalama {cevap}.", izinli) == []


@pytest.mark.parametrize("deger", [Decimal("65.32"), 65.32, "65.32"])
@pytest.mark.parametrize("cevap", ["65,33", "65,3", "65", "6,53", "65,32 ve 66,00"])
def test_farkli_sayi_eslesmez(deger: object, cevap: str) -> None:
    izinli = _izinli({"ortalama": deger})
    assert dayanaksiz_sayilar(f"Ortalama {cevap}.", izinli) != []


def test_int_deger_ve_satir_sayisi_izinli() -> None:
    izinli = _izinli({"sayi": 6}, row_count=1)
    assert dayanaksiz_sayilar("6 kayıt.", izinli) == []
    assert dayanaksiz_sayilar("7 kayıt.", izinli) == ["7"]


def test_bool_ve_none_sayi_sayilmaz() -> None:
    izinli = _izinli({"gecti": True, "x": None}, row_count=0)
    assert dayanaksiz_sayilar("1 kayıt.", izinli) == ["1"]


def test_yeni_sinif_adlari_desenle_maskelenir() -> None:
    cevap = "9-A, 10-B, 5-A, 6-C, 11-A ve 12-B sınıflarına baktım."
    assert dayanaksiz_sayilar(cevap, set()) == []
    # Sonuç tarafı aynı maskeyi kullanır: sınıf adındaki rakamlar izinli kümeye girmez.
    izinli = _izinli({"class_name": "12-B", "ortalama": 65.32})
    assert 12.0 not in izinli
    assert 65.32 in izinli
    assert dayanaksiz_sayilar("12-B sınıfı 65,32.", izinli) == []


def test_sinif_adi_kuralinda_sabit_liste_yok() -> None:
    # Listede olmayan yeni bir ad da desenle maskelenir; boşluklu yazım da.
    assert dayanaksiz_sayilar("7-D ve 8 - E sınıfları", set()) == []


def test_sira_yuzde_ondalik_tarih_bicimleri() -> None:
    assert dayanaksiz_sayilar("Sıra 2/6.", set()) == []
    assert dayanaksiz_sayilar("%3,26 oranında.", {3.26}) == []
    assert dayanaksiz_sayilar("%3,26 oranında.", set()) == ["3,26"]
    assert dayanaksiz_sayilar("4 Kasım 2026 tarihinde.", set()) == []
    assert dayanaksiz_sayilar("2026-11-04 tarihinde.", set()) == []
    assert dayanaksiz_sayilar("4.11.2026 tarihinde.", set()) == []


# --- Tarih maskesi yalnız gerçek tarih biçimlerini siler; ay adından sonraki değer sayıdır ---

_AY_DEGERLERI = {71.66, 71.18, 74.01}


@pytest.mark.parametrize(
    "metin",
    [
        "Eylül 71,66",
        "Ekim 71.18",
        "Eylül'de 71,66",
        "**Eylül**: 71.66",
        "Eylül 74,01, Ekim 71,18.",
    ],
)
def test_ay_adindan_sonraki_deger_izinliyse_kabul(metin: str) -> None:
    assert dayanaksiz_sayilar(metin, set(_AY_DEGERLERI)) == []


@pytest.mark.parametrize(
    ("metin", "beklenen"),
    [
        ("Eylül 71,66", ["71,66"]),
        ("Ekim 71.18", ["71.18"]),
        ("Eylül'de 71,66", ["71,66"]),
        ("**Eylül**: 71.66", ["71.66"]),
        ("Eylül 74,01, Ekim 71,18.", ["74,01", "71,18"]),
    ],
)
def test_ay_adindan_sonraki_deger_izinsizse_tam_sayi_reddedilir(
    metin: str, beklenen: list[str]
) -> None:
    # Parça ("71", "66", "01") değil, sayının tamamı.
    assert dayanaksiz_sayilar(metin, set()) == beklenen


def test_ay_adindan_sonraki_deger_metin_sayisi_olarak_butun() -> None:
    hedef: set[float] = set()
    _metin_sayilari("Eylül 71,66, Ekim 71.18", hedef)
    assert hedef == {71.66, 71.18}


@pytest.mark.parametrize(
    "metin",
    [
        "4 Kasım 2026 tarihinde.",
        "4 Kasım",
        "Kasım 2026",
        "2026-11-04",
        "November 4, 2026",
        "November 4",
        "4 November 2026",
        "November 2026",
    ],
)
def test_gercek_tarih_bicimleri_maskelenir(metin: str) -> None:
    assert dayanaksiz_sayilar(metin, set()) == []


def test_kasim_3_belirsiz_oldugu_icin_sayi_olarak_dogrulanir() -> None:
    assert dayanaksiz_sayilar("Kasım 3", set()) == ["3"]
    assert dayanaksiz_sayilar("Kasım 3", {3.0}) == []


def test_sayi_ondalik_ayiriciden_parcalanmaz() -> None:
    # 4 haneli yıl biçiminde başlayan ondalık, yıl diye bölünmez.
    assert dayanaksiz_sayilar("1999,5 puan.", set()) == ["1999,5"]
    assert dayanaksiz_sayilar("2026.5 puan.", set()) == ["2026.5"]
    # Ondalığın kuyruğu gün gibi okunup ay adına bağlanmaz.
    assert dayanaksiz_sayilar("71,18 Ekim ortalaması.", set()) == ["71,18"]
    # Virgülle bitişik sınıf adları yine maskelenir.
    assert dayanaksiz_sayilar("9-A,10-B sınıfları.", set()) == []


def test_binlik_nokta_ondalik_okunur_mevcut_davranis() -> None:
    # Bugünkü kural: "1.234" ondalık sayılır (1,23). Binlik ayracı çözülmüyor;
    # bu bilinçli olarak gevşetilmedi (bkz. rapor, hipotez).
    assert dayanaksiz_sayilar("1.234 kayıt.", {1234.0}) == ["1.234"]
    assert dayanaksiz_sayilar("1.234 kayıt.", {1.23}) == []


def test_sonucta_olmayan_sayim_ve_fark_yakalanir() -> None:
    izinli = _izinli({"ortalama": 65.32}, {"ortalama": 62.06})
    assert dayanaksiz_sayilar("3 öğrenci var.", izinli) == ["3"]
    assert dayanaksiz_sayilar("Aradaki fark 3,26.", izinli) == ["3,26"]
    assert dayanaksiz_sayilar("2 sınıf var.", izinli) == []


def test_markdown_tablo_hucreleri() -> None:
    izinli = _izinli(
        {"class_name": "12-B", "ortalama": Decimal("65.32"), "n": 24},
        {"class_name": "9-A", "ortalama": Decimal("70.10"), "n": 20},
    )
    tablo = (
        "| Sınıf | Ortalama | Not sayısı |\n"
        "|---|---|---|\n"
        "| 12-B | 65,32 | 24 |\n"
        "| 9-A | 70,10 | 20 |"
    )
    assert dayanaksiz_sayilar(tablo, izinli) == []
    uydurma = tablo.replace("70,10", "71,00")
    assert dayanaksiz_sayilar(uydurma, izinli) == ["71,00"]


def test_metin_sayilari_virgul_ve_nokta_ayni_deger() -> None:
    a: set[float] = set()
    b: set[float] = set()
    _metin_sayilari("10,67", a)
    _metin_sayilari("10.67", b)
    assert a == b == {10.67}


# --- Kanıtlanmış neden: distinct_counts izinli kümeye giriyordu ---


def test_distinct_counts_degeri_dayanak_sayilir() -> None:
    # 10 satır, 8 farklı öğrenci: model distinct_counts'tan "8" der.
    satirlar = [
        {"name": f"Öğrenci{chr(65 + i % 8)}", "subject": "Fizik", "grade": 50 + i}
        for i in range(10)
    ]
    izinli = _izinli(*satirlar)
    assert dayanaksiz_sayilar("8 öğrenci var.", izinli) == []
    assert dayanaksiz_sayilar("7 öğrenci var.", izinli) == ["7"]
    assert dayanaksiz_sayilar("9 öğrenci var.", izinli) == ["9"]


def test_distinct_counts_run_assistant_icinde_ek_tur_acmaz() -> None:
    satirlar = [{"name": f"Ö{chr(65 + i % 8)}", "grade": 50 + i} for i in range(10)]
    istemci = SahteIstemci(
        [["SELECT DISTINCT name, grade FROM grades"], "Notu düşük 8 öğrenci var."]
    )
    sonuc = run_assistant(
        _soru("notu düşük kimler"),
        "principal",
        "tr",
        client=istemci,
        run_sql=lambda sql: {"ok": True, "rows": satirlar, "row_count": 10, "truncated": False},
    )
    assert sonuc.grounding_retry is False
    assert sonuc.answer == "Notu düşük 8 öğrenci var."


# --- (A): date ve Decimal içeren run_sql çıktısı modele gönderilebilir ---


def test_date_ve_decimal_iceren_sonuc_modele_gider() -> None:
    satirlar = [
        {
            "student_id": 3,
            "date": date(2026, 11, 4),
            "created": datetime(2026, 11, 4, 8, 30),
            "ortalama": Decimal("65.32"),
            "status": "Devamsız",
        }
    ]
    istemci = SahteIstemci(
        [
            ["SELECT student_id, date, status FROM attendance WHERE date = '2026-11-04'"],
            "Bugün 1 öğrenci gelmedi; ortalaması 65,32.",
        ]
    )
    sonuc = run_assistant(
        _soru("bugün devamsızlık yapanlar kimler"),
        "principal",
        "tr",
        client=istemci,
        run_sql=lambda sql: {
            "ok": True,
            "rows": satirlar,
            "row_count": 1,
            "truncated": False,
        },
    )
    assert sonuc.answer == "Bugün 1 öğrenci gelmedi; ortalaması 65,32."
    assert sonuc.answer != YEDEK_CEVAP["tr"]
    assert sonuc.grounding_retry is False
    mesajlar = istemci.cagrilar[1]["messages"]
    icerik = next(
        parca["content"]
        for mesaj in mesajlar
        if isinstance(mesaj["content"], list)
        for parca in mesaj["content"]
        if parca.get("type") == "tool_result"
    )
    govde = json.loads(icerik)
    assert govde["rows"][0]["date"] == "2026-11-04"
    assert govde["rows"][0]["created"] == "2026-11-04T08:30:00"
    assert govde["rows"][0]["ortalama"] == 65.32


def test_desteklenmeyen_tur_sessizce_yutulmaz() -> None:
    istemci = SahteIstemci([["SELECT 1"], "x"])
    with pytest.raises(TypeError):
        run_assistant(
            _soru("deneme"),
            "principal",
            "tr",
            client=istemci,
            run_sql=lambda sql: {
                "ok": True,
                "rows": [{"v": object()}],
                "row_count": 1,
                "truncated": False,
            },
        )


# --- Görev 2: yapılandırılmış kayıt ---


def test_ret_kaydi_alanlari(caplog: pytest.LogCaptureFixture) -> None:
    istemci = SahteIstemci(
        [
            ["SELECT class_name, AVG(grade) FROM grades GROUP BY class_name"],
            "Aradaki fark 3,26 puan.",
            "Yine fark 3,26 puan.",
        ]
    )
    with _kayitlar(caplog):
        sonuc = run_assistant(
            _soru("sınıfların ortalaması"),
            "principal",
            "tr",
            client=istemci,
            run_sql=lambda sql: {
                "ok": True,
                "rows": [{"class_name": "9-A", "ortalama": 65.32}],
                "row_count": 1,
                "truncated": False,
            },
        )
    assert sonuc.answer == GROUNDING_GERI_DONUS["tr"]
    assert sonuc.grounding_fallback is True
    assert sonuc.results == [{"class_name": "9-A", "ortalama": 65.32}]
    kayitlar = _olaylar(caplog, "ungrounded_number")
    assert [k["stage"] for k in kayitlar] == ["retry", "final"]
    son = kayitlar[-1]
    assert son["role"] == "principal"
    assert son["question"] == "sınıfların ortalaması"
    assert son["sql"] == ["SELECT class_name, AVG(grade) FROM grades GROUP BY class_name"]
    assert son["row_counts"] == [1]
    assert son["numbers"] == ["3,26"]
    beklenen = _izinli({"class_name": "9-A", "ortalama": 65.32}) | {round(float(settings.PASS_GRADE), 2)}
    assert son["allowed_set_size"] == len(beklenen)
    assert son["draft"] == "Yine fark 3,26 puan."
    assert len(son["draft"]) <= 500


def test_taslak_ilk_500_karakterle_sinirli(caplog: pytest.LogCaptureFixture) -> None:
    uzun = "Kayıt 77 " + "x" * 900
    istemci = SahteIstemci([uzun, uzun])
    with _kayitlar(caplog):
        run_assistant(
            _soru("soru"),
            "teacher",
            "tr",
            client=istemci,
            run_sql=lambda sql: {"ok": False},
        )
    kayit = _olaylar(caplog, "ungrounded_number")[-1]
    assert kayit["draft"] == uzun[:500]


def test_yedek_kaydi_bos_metin(caplog: pytest.LogCaptureFixture) -> None:
    istemci = SahteIstemci([["SELECT student_id FROM attendance"], ""])
    with _kayitlar(caplog):
        sonuc = run_assistant(
            _soru("bugün gelmeyenler kimler"),
            "principal",
            "tr",
            client=istemci,
            run_sql=lambda sql: {
                "ok": True,
                "rows": [{"student_id": 3}],
                "row_count": 1,
                "truncated": False,
            },
        )
    assert sonuc.answer == YEDEK_CEVAP["tr"]
    kayit = _olaylar(caplog, "assistant_fallback")[0]
    assert kayit["reason"] == "empty_model_text"
    assert kayit["sql"] == ["SELECT student_id FROM attendance"]
    assert kayit["row_counts"] == [1]
    assert kayit["tool_exception"] == ""
    assert kayit["question"] == "bugün gelmeyenler kimler"


def test_yedek_kaydi_yakalanan_istisna(caplog: pytest.LogCaptureFixture) -> None:
    def run_sql(sql: str) -> dict:
        raise RuntimeError("boom")

    istemci = SahteIstemci([["SELECT 1"], ["SELECT 2"], ["SELECT 3"], ""])
    with _kayitlar(caplog):
        sonuc = run_assistant(
            _soru("kayıt"), "parent", "tr", client=istemci, run_sql=run_sql
        )
    assert sonuc.answer == YEDEK_CEVAP["tr"]
    kayit = _olaylar(caplog, "assistant_fallback")[0]
    assert kayit["tool_exception"] == "RuntimeError: boom"
    assert kayit["failed_tool_calls"] == 3
    assert kayit["sql"] == []
    assert len(_olaylar(caplog, "run_sql_exception")) == 3


def test_kayitta_sir_yok(caplog: pytest.LogCaptureFixture) -> None:
    istemci = SahteIstemci(["Fark 3,26.", "Fark 3,26."])
    with _kayitlar(caplog):
        run_assistant(
            _soru("ortalama"), "principal", "tr", client=istemci, run_sql=lambda s: {"ok": False}
        )
    metin = "\n".join(k.getMessage() for k in caplog.records)
    assert settings.SECRET_KEY not in metin
    if settings.ANTHROPIC_API_KEY:
        assert settings.ANTHROPIC_API_KEY not in metin
    assert "Authorization" not in metin
