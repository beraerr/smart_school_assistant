"""Araştırma sayfası: çizim, yer tutucular, biçimleyici, api_client'sız çalışma, giriş bağlantısı."""

import ast
import csv
import hashlib
import html
import inspect
import io
import sys
import textwrap
from pathlib import Path
from unittest.mock import DEFAULT, MagicMock, patch

import pytest
from streamlit.testing.v1 import AppTest
from streamlit.testing.v1.element_tree import Block

_FRONTEND = Path(__file__).resolve().parents[1]
_ROOT = _FRONTEND.parent
for yol in (_ROOT, _FRONTEND):
    if str(yol) not in sys.path:
        sys.path.insert(0, str(yol))

import api_client  # noqa: E402
import arastirma  # noqa: E402
from arastirma_metin import (  # noqa: E402
    ARAYUZ,
    BICIMLER,
    EKSIK_EN,
    KOD_BLOGU,
    METIN,
    SEKME_SIRA,
    YER_TUTUCU,
)
from i18n import get_text  # noqa: E402

_APP = _FRONTEND / "app.py"


def _sayfa(lang: str, oturumlu: bool, bolum: str | None = None) -> AppTest:
    at = AppTest.from_file(str(_APP), default_timeout=30)
    if oturumlu:
        at.session_state["token"] = "token-1"
        at.session_state["user"] = {"username": "teacher1", "role": "teacher"}
    else:
        at.session_state["token"] = None
        at.session_state["user"] = None
    at.session_state["lang"] = lang
    at.query_params["sayfa"] = "arastirma"
    if bolum is not None:
        at.query_params["bolum"] = bolum
    at.run()
    return at


def _giris(lang: str) -> AppTest:
    at = AppTest.from_file(str(_APP), default_timeout=15)
    at.session_state["token"] = None
    at.session_state["user"] = None
    at.session_state["lang"] = lang
    at.run()
    return at


def _sayfa_metni(at: AppTest) -> str:
    """Çizilen metinler; tema <style> bloğu (CSS süslü parantez içerir) hariç."""
    parcalar = [str(oge.value) for oge in at.markdown if not str(oge.value).lstrip().startswith("<style>")]
    parcalar += [str(oge.value) for oge in at.code]
    parcalar += [str(oge.value) for oge in at.caption]
    return "\n".join(parcalar)


def _tum_sekmeler_metni(lang: str, oturumlu: bool = False) -> str:
    """Bütün sekmeler sırayla açılıp çizilen metinler birleştirilir (her sekme istisnasız çizilmeli)."""
    parcalar = []
    for bolum in SEKME_SIRA:
        at = _sayfa(lang, oturumlu, bolum)
        assert len(at.exception) == 0, f"{lang}/{bolum}: {[e.value for e in at.exception]}"
        parcalar.append(_sayfa_metni(at))
    return "\n".join(parcalar)


def _gorunur(metin: str, sayfa_metni: str) -> bool:
    """Metin ya doğrudan (markdown) ya da HTML kaçışlı (div/p içinde) çizilmiş olmalı."""
    return metin in sayfa_metni or html.escape(metin) in sayfa_metni


def _metinler(metin: object):
    """Sözlük içindeki bütün metinleri (anahtar, değer) olarak gezer."""
    if isinstance(metin, str):
        yield metin
    elif isinstance(metin, dict):
        for oge in metin.values():
            yield from _metinler(oge)
    elif isinstance(metin, (tuple, list)):
        for oge in metin:
            yield from _metinler(oge)


def _yer_tutucular() -> list[tuple[str, str, str, str]]:
    """(dil, anahtar, yol, bicim) üçlüleri."""
    sonuc = []
    for dil, sozluk in METIN.items():
        for anahtar, deger in sozluk.items():
            for metin in _metinler(deger):
                for yol, bicim in YER_TUTUCU.findall(metin):
                    sonuc.append((dil, anahtar, yol, bicim))
    return sonuc


# --- Çizim -----------------------------------------------------------------------------


@pytest.mark.parametrize("lang", ["tr", "en"])
@pytest.mark.parametrize("oturumlu", [False, True])
def test_sayfa_istisnasiz_cizilir(lang: str, oturumlu: bool) -> None:
    at = _sayfa(lang, oturumlu)
    assert len(at.exception) == 0
    metin = _sayfa_metni(at)
    assert METIN[lang]["hero_baslik"] in metin
    # Başka hiçbir şey çizilmez: giriş formu, sohbet, kenar menü yok.
    assert len(at.text_input) == 0
    assert len(at.chat_input) == 0
    assert len(at.sidebar.button) == 0
    assert [kutu.key for kutu in at.selectbox] == ["lang"]


@pytest.mark.parametrize("lang", ["tr", "en"])
def test_sayfa_ust_serit_dugmeleri(lang: str) -> None:
    at = _sayfa(lang, False)
    assert at.button(key="ar_marka").label == get_text(lang, "brand_short")
    assert at.button(key="ar_geri").label == get_text(lang, "back_to_signin")
    assert get_text("tr", "back_to_signin") == "Girişe dön"
    assert get_text("en", "back_to_signin") == "Back to sign in"
    # Yeniden yükleme yaptıran <a href> bağlantısı yok.
    assert "href=" not in _sayfa_metni(at)


@pytest.mark.parametrize("lang", ["tr", "en"])
def test_tum_bloklar_her_iki_dilde_cizilir(lang: str) -> None:
    for bolum, anahtar in (("model", "tablo_46"), ("sistem", "tablo_11")):
        metin = _sayfa_metni(_sayfa(lang, False, bolum))
        for baslik in METIN[lang][anahtar]["ust"]:
            assert f"<th>{baslik}</th>" in metin
    metin = _sayfa_metni(_sayfa(lang, False, "kaynak"))
    assert html.escape(METIN[lang]["sinirlar"]) in metin
    assert METIN[lang]["yeniden_uretim"] in metin


def test_dugmeyle_giris_ekranindan_arastirmaya_ve_geri_oturumsuz() -> None:
    at = _giris("en")
    assert at.session_state["lang"] == "en"
    at.button(key="arastirma_ac").click().run()
    assert len(at.exception) == 0
    assert METIN["en"]["hero_baslik"] in _sayfa_metni(at)
    assert len(at.text_input) == 0
    assert at.query_params.get("sayfa") == "arastirma"  # adres çubuğunda paylaşılabilir
    assert at.session_state["lang"] == "en"
    assert at.session_state["token"] is None
    at.button(key="ar_geri").click().run()
    assert len(at.exception) == 0
    assert len(at.text_input) == 2  # giriş formu geri geldi
    assert "sayfa" not in at.query_params
    assert "bolum" not in at.query_params
    assert at.session_state["lang"] == "en"


def test_dugmeyle_gecis_oturumu_ve_dili_korur() -> None:
    sahte = patch.object(api_client, "examples", return_value={"ok": False, "status_code": 500})
    with sahte:
        at = AppTest.from_file(str(_APP), default_timeout=30)
        at.session_state["token"] = "token-1"
        at.session_state["user"] = {"username": "teacher1", "role": "teacher"}
        at.session_state["lang"] = "en"
        at.query_params["sayfa"] = "arastirma"
        at.run()
        assert METIN["en"]["hero_baslik"] in _sayfa_metni(at)
        at.button(key="ar_marka").click().run()
        assert len(at.exception) == 0
        assert "sayfa" not in at.query_params
        assert len(at.chat_input) == 1  # oturum açık: sohbet ekranı
        assert METIN["en"]["hero_baslik"] not in _sayfa_metni(at)
        assert at.session_state["token"] == "token-1"
        assert at.session_state["user"] == {"username": "teacher1", "role": "teacher"}
        assert at.session_state["lang"] == "en"


def test_dil_secimi_sayfada_degisince_metin_degisir() -> None:
    at = _sayfa("tr", False)
    assert METIN["tr"]["hero_baslik"] in _sayfa_metni(at)
    at.selectbox(key="lang").select("en").run()
    assert len(at.exception) == 0
    assert METIN["en"]["hero_baslik"] in _sayfa_metni(at)
    assert at.session_state["lang"] == "en"


def test_sayfa_gorunen_yer_tutucu_metin_yok() -> None:
    for lang in ("tr", "en"):
        metin = _tum_sekmeler_metni(lang)
        assert "TODO" not in metin
        assert "TBD" not in metin


@pytest.mark.parametrize("lang", ["tr", "en"])
def test_sayfada_cozulmemis_yer_tutucu_kalmaz(lang: str) -> None:
    metin = _tum_sekmeler_metni(lang)
    assert "{" not in metin
    assert "}" not in metin


def test_sayfa_sayilari_dile_gore_cizer() -> None:
    paket = arastirma.paketi_oku()
    tr = _sayfa_metni(_sayfa("tr", False))
    en = _sayfa_metni(_sayfa("en", False))
    assert arastirma.bicimle(paket["oulad"]["n_rows_raw"], "tam", "tr") in tr
    assert arastirma.bicimle(paket["oulad"]["n_rows_raw"], "tam", "en") in en
    assert arastirma.bicimle(paket["rule"]["capture_rule2"]["2014J"], "yuzde", "tr") in tr
    assert arastirma.bicimle(paket["rule"]["capture_rule2"]["2014J"], "yuzde", "en") in en


def test_ingilizce_eksik_bloklar_yalniz_listedekiler() -> None:
    """Belirtimin İngilizce karşılığını vermediği her anahtar EKSIK_EN'de açıkça listelenir."""
    assert len(EKSIK_EN) == len(set(EKSIK_EN)), "EKSIK_EN'de yinelenen anahtar var"
    tr, en = METIN["tr"], METIN["en"]
    eksik = {anahtar for anahtar in tr if anahtar not in en}
    assert eksik == set(EKSIK_EN), f"EKSIK_EN ile gerçek eksikler ayrışıyor: {sorted(eksik ^ set(EKSIK_EN))}"
    assert set(en) <= set(tr)


def test_metin_kodu_ve_kod_blogu_cizilir() -> None:
    at = _sayfa("tr", False, "kaynak")
    assert [kod.value for kod in at.code] == [KOD_BLOGU]
    assert "python scripts/arastirma_paketi.py" in KOD_BLOGU


# --- Yer tutucular -----------------------------------------------------------------------


def test_her_yer_tutucu_paketten_cozulur() -> None:
    paket = arastirma.tam_paket()
    cozulmeyen = []
    for dil, anahtar, yol, bicim in _yer_tutucular():
        try:
            deger = arastirma.yol_degeri(paket, yol)
            arastirma.bicimle(deger, bicim, dil)
        except (KeyError, TypeError, ValueError) as hata:
            cozulmeyen.append(f"{dil}/{anahtar}: {yol}:{bicim} ({type(hata).__name__}: {hata})")
    assert not cozulmeyen, "çözülmeyen yer tutucular:\n" + "\n".join(cozulmeyen)


def test_yer_tutucu_bicimleri_bilinen_ve_metin_baska_suslu_parantez_icermez() -> None:
    assert _yer_tutucular(), "metinlerde hiç yer tutucu yok"
    for _, anahtar, yol, bicim in _yer_tutucular():
        assert bicim in BICIMLER, f"{anahtar}: bilinmeyen biçim {bicim} ({yol})"
    for dil, sozluk in METIN.items():
        for anahtar, deger in sozluk.items():
            for metin in _metinler(deger):
                artik = YER_TUTUCU.sub("", metin)
                assert "{" not in artik and "}" not in artik, f"{dil}/{anahtar}: biçimsiz alan"


def test_tr_ve_en_ayni_yollari_kullanir() -> None:
    yollar = {"tr": {}, "en": {}}
    for dil, sozluk in METIN.items():
        for anahtar, deger in sozluk.items():
            yollar[dil][anahtar] = sorted(
                (yol, bicim) for metin in _metinler(deger) for yol, bicim in YER_TUTUCU.findall(metin)
            )
    for anahtar, en_yollari in yollar["en"].items():
        assert yollar["tr"][anahtar] == en_yollari, f"{anahtar}: TR ve EN alanları farklı"


def test_coz_bilinmeyen_yol_ve_bicimde_hata_verir() -> None:
    paket = arastirma.paketi_oku()
    with pytest.raises(KeyError):
        arastirma.coz("{yok.boyle.bir.yol:tam}", paket, "tr")
    with pytest.raises(ValueError):
        arastirma.coz("{uci.total:bilinmeyen}", paket, "tr")
    with pytest.raises(TypeError):
        arastirma.coz("{uci.total:metin}", paket, "tr")


# --- Biçimleyici -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("deger", "bicim", "tr", "en"),
    [
        (0.9208579881656804, "yuzde", "%92,1", "92.1%"),
        (0.2, "yuzdetam", "%20", "20%"),
        (0.05, "yuzdetam", "%5", "5%"),
        (0.2, "yuzde", "%20,0", "20.0%"),  # genel biçim değişmedi
        (32593, "tam", "32.593", "32,593"),
        (0.7922494, "roc", "0,792", "0.792"),
        (6.564417, "puan", "6,6", "6.6"),
        (0.8091417205401191, "kor", "0,81", "0.81"),
        (-0.3831452797182739, "kor", "\u22120,38", "\u22120.38"),
        ("AAA", "metin", "AAA", "AAA"),
    ],
)
def test_bicimleyici_tr_ve_en(deger: object, bicim: str, tr: str, en: str) -> None:
    assert arastirma.bicimle(deger, bicim, "tr") == tr
    assert arastirma.bicimle(deger, bicim, "en") == en


@pytest.mark.parametrize("lang", ["tr", "en"])
def test_yuzdetam_tam_olmayan_yuzdeyi_yuvarlamaz(lang: str) -> None:
    with pytest.raises(ValueError):
        arastirma.bicimle(0.205, "yuzdetam", lang)


def test_bicimleyici_yer_tutucu_icinde_ve_yuzde_isareti_tekil() -> None:
    paket = {"a": {"oran": 0.9208579881656804, "n": 10655280}}
    assert arastirma.coz("{a.oran:yuzde} · {a.n:tam}", paket, "tr") == "%92,1 · 10.655.280"
    assert arastirma.coz("{a.oran:yuzde} · {a.n:tam}", paket, "en") == "92.1% · 10,655,280"


@pytest.mark.parametrize(
    ("deger", "bicim"),
    [(1.5, "tam"), (True, "tam"), ("0,5", "yuzde"), (None, "roc"), (3, "metin")],
)
def test_bicimleyici_yanlis_tipte_hata_verir(deger: object, bicim: str) -> None:
    with pytest.raises(TypeError):
        arastirma.bicimle(deger, bicim, "tr")


# --- api_client ------------------------------------------------------------------------


@pytest.mark.parametrize("oturumlu", [False, True])
def test_sayfa_api_client_cagirmaz(oturumlu: bool) -> None:
    islevler = [ad for ad in dir(api_client) if callable(getattr(api_client, ad)) and not ad.startswith("__")]
    assert {"login", "risk", "examples", "query"} <= set(islevler)
    with patch.multiple(api_client, **{ad: DEFAULT for ad in islevler}) as sahteler:
        for dil in ("tr", "en"):
            _tum_sekmeler_metni(dil, oturumlu)  # her sekme açılır; istisna olursa düşer
    for ad, sahte in sahteler.items():
        assert sahte.call_count == 0, f"api_client.{ad} çağrıldı"


# --- Giriş ekranı ---------------------------------------------------------------------


@pytest.mark.parametrize("lang", ["tr", "en"])
def test_giris_ekraninda_arastirma_baglantisi_ve_ucuncu_ozellik(lang: str) -> None:
    at = _giris(lang)
    assert len(at.exception) == 0
    metin = html.unescape("\n".join(str(oge.value) for oge in at.markdown))
    assert at.button(key="arastirma_ac").label == get_text(lang, "research_link")
    assert "href=\"?sayfa=arastirma\"" not in metin
    if lang == "tr":
        assert at.button(key="arastirma_ac").label == "Araştırmayı incele →"
        assert "Açık veriyle sınanmış kural" in metin
        assert (
            "OULAD'da modellerle karşılaştırılan iki sinyalli kuralın okul verisindeki karşılığı."
            in metin
        )
    else:
        assert at.button(key="arastirma_ac").label == "Explore the research →"
        assert "A rule tested on open data" in metin
        assert (
            "The school-data counterpart of a two-signal rule compared against models on OULAD."
            in metin
        )
    assert "Veri bilimiyle sınanmış risk" not in metin
    assert "Risk checked with data science" not in metin


# --- S1: 11 sekme, &bolum=, bölüm içeriği ------------------------------------------------

# docs/arastirma_raporu_spec_v2_eki.md bölüm 1 tablosu (kimlik, TR, EN), sırasıyla.
# Beklenen değerler uygulama kodundan okunmaz; burada açıkça yazılıdır.
_SEKMELER = [
    ("ozet", "Özet", "Summary"),
    ("veri", "Veri setleri", "Datasets"),
    ("uci", "UCI keşif", "UCI exploration"),
    ("oulad", "OULAD keşif", "OULAD exploration"),
    ("model", "Modelleme", "Modelling"),
    ("kural", "Karar kuralı", "Decision rule"),
    ("ek", "Ek analizler", "Further analyses"),
    ("hoca", "Hoca etkisi", "Teacher effect"),
    ("sistem", "Sisteme köprü", "Bridge to the system"),
    ("hatalar", "Hatalar ve düzeltmeler", "Errors and fixes"),
    ("kaynak", "Sınırlar ve kaynaklar", "Limits and sources"),
]
_ETIKET = {"tr": {k: tr for k, tr, _ in _SEKMELER}, "en": {k: en for k, _, en in _SEKMELER}}


def _acik_sekmeler(at: AppTest) -> list[str]:
    """İçeriği çizilmiş (çocuğu olan) sekmelerin etiketleri."""
    return [sekme.label for sekme in at.tabs if len(sekme.children) > 0]


def test_sekme_sirasi_belirtimdeki_gibi() -> None:
    assert list(SEKME_SIRA) == [kimlik for kimlik, _, _ in _SEKMELER]
    for dil in ("tr", "en"):
        assert dict(METIN[dil]["sekmeler"]) == _ETIKET[dil]


@pytest.mark.parametrize("lang", ["tr", "en"])
@pytest.mark.parametrize("oturumlu", [False, True])
def test_on_bir_sekme_ekteki_sirada(lang: str, oturumlu: bool) -> None:
    at = _sayfa(lang, oturumlu)
    assert len(at.exception) == 0
    assert [sekme.label for sekme in at.tabs] == [_ETIKET[lang][k] for k in SEKME_SIRA]
    assert len(at.tabs) == 11


@pytest.mark.parametrize("lang", ["tr", "en"])
@pytest.mark.parametrize("bolum", [k for k, _, _ in _SEKMELER])
def test_bolum_parametresi_sekmeyi_dogrudan_acar(lang: str, bolum: str) -> None:
    at = _sayfa(lang, False, bolum)
    assert len(at.exception) == 0
    assert at.session_state[f"ar_sekme_{lang}"] == _ETIKET[lang][bolum]
    assert _acik_sekmeler(at) == [_ETIKET[lang][bolum]]
    assert at.query_params.get("bolum") == bolum


@pytest.mark.parametrize("gecersiz", ["yok", "OZET", "ozet2", "Özet", "kaynakça"])
def test_gecersiz_bolum_ozete_duser(gecersiz: str) -> None:
    at = _sayfa("tr", False, gecersiz)
    assert len(at.exception) == 0
    assert _acik_sekmeler(at) == ["Özet"]
    assert at.query_params.get("bolum") == "ozet"


@pytest.mark.parametrize("lang", ["tr", "en"])
def test_bolum_yoksa_ozet_acilir_ve_adrese_yazilir(lang: str) -> None:
    at = _sayfa(lang, False)
    assert _acik_sekmeler(at) == [_ETIKET[lang]["ozet"]]
    assert at.query_params.get("bolum") == "ozet"
    assert at.query_params.get("sayfa") == "arastirma"


def test_dil_degisince_sekme_ve_adres_korunur() -> None:
    at = _sayfa("tr", False, "hoca")
    at.selectbox(key="lang").select("en").run()
    assert len(at.exception) == 0
    assert _acik_sekmeler(at) == ["Teacher effect"]
    assert at.query_params.get("bolum") == "hoca"


def test_sekmeye_gecis_dugmesi_sekmeyi_ve_adresi_degistirir() -> None:
    at = _sayfa("tr", False, "uci")
    at.button(key="ar_git_uci_hata").click().run()
    assert len(at.exception) == 0
    assert _acik_sekmeler(at) == ["Hatalar ve düzeltmeler"]
    assert at.query_params.get("bolum") == "hatalar"
    assert at.query_params.get("sayfa") == "arastirma"


@pytest.mark.parametrize("lang", ["tr", "en"])
@pytest.mark.parametrize("oturumlu", [False, True])
@pytest.mark.parametrize("bolum", [k for k, _, _ in _SEKMELER])
def test_her_sekme_istisnasiz_cizilir(lang: str, oturumlu: bool, bolum: str) -> None:
    at = _sayfa(lang, oturumlu, bolum)
    assert len(at.exception) == 0
    assert len(at.markdown) > 1  # tema <style> + sekme içeriği


@pytest.mark.parametrize("lang", ["tr", "en"])
@pytest.mark.parametrize("bolum", [k for k, _, _ in _SEKMELER])
def test_her_bolumde_ham_tablo_acilir_dataframe_ve_csv_dugmesi(lang: str, bolum: str) -> None:
    at = _sayfa(lang, False, bolum)
    adet = len(arastirma.HAM[bolum])
    assert adet >= 1
    assert ARAYUZ[lang]["ham_tablolar"] in [oge.label for oge in at.expander]
    assert len(at.dataframe) == adet
    assert len(at.download_button) == adet
    assert {dugme.label for dugme in at.download_button} == {ARAYUZ[lang]["csv_indir"]}


def test_ham_tablolar_her_sekme_icin_tanimli() -> None:
    assert set(arastirma.HAM) == set(SEKME_SIRA)


def test_ham_tablo_satirlari_ve_csv_paketle_birebir() -> None:
    paket = arastirma.tam_paket()
    for bolum, tablolar in arastirma.HAM.items():
        for _, yol, yukle in tablolar:
            satirlar = yukle(paket)
            assert satirlar, f"{bolum}/{yol}: boş ham tablo"
            okunan = list(csv.DictReader(io.StringIO(arastirma.csv_metni(satirlar))))
            assert len(okunan) == len(satirlar), f"{bolum}/{yol}"
            for ham, geri in zip(satirlar, okunan, strict=True):
                for anahtar, deger in ham.items():
                    beklenen = "" if deger is None else str(deger)
                    assert geri[anahtar] == beklenen, f"{bolum}/{yol}/{anahtar}"


def test_satirla_ic_ice_yapilari_acar_ve_desteklenmeyeni_reddeder() -> None:
    assert arastirma.satirla([{"a": 1, "b": [1, 2]}]) == [{"a": 1, "b": "1, 2"}]
    assert arastirma.satirla({"x": {"p": 1}, "y": {"p": 2}}) == [
        {"anahtar_1": "x", "p": 1},
        {"anahtar_1": "y", "p": 2},
    ]
    assert arastirma.satirla({"s": [{"bin": "0", "rate": 0.5}]}) == [
        {"anahtar_1": "s", "bin": "0", "rate": 0.5}
    ]
    with pytest.raises(TypeError):
        arastirma.satirla([[{"a": 1}]])
    with pytest.raises(ValueError):
        arastirma.satirla([])


def test_turev_degerleri_paketin_satirlarindan_gelir() -> None:
    paket = arastirma.paketi_oku()
    tam = arastirma.tam_paket()
    assert "turev" not in paket
    oranlar = [satir["rate"] for satir in paket["oulad"]["risk_pivot"]]
    assert tam["turev"]["risk"]["en_dusuk_oran"] == min(oranlar)
    assert tam["turev"]["risk"]["en_yuksek_oran"] == max(oranlar)
    assert tam["turev"]["uci"]["n_early"] == len(paket["uci"]["feature_sets"]["early"])
    assert all(0 <= deger <= 1 for deger in tam["turev"]["sinyal"].values())
    assert isinstance(tam["turev"]["model"]["egitim_satir"], int)


# Grafik yerleri (spec v2 + ek): hepsi çağrılır, hiçbiri bir şey çizmez.
_GRAFIK_KIMLIKLERI = (
    ["Z1"]
    + [f"D{i}" for i in range(1, 5)]
    + [f"U{i}" for i in range(1, 7)]
    + [f"O{i}" for i in range(1, 5)]
    + [f"M{i}" for i in range(1, 10)]
    + ["K1", "R1", "R2", "P1"]
    + [f"X{i}" for i in range(1, 6)]
    + ["H1"]
)


# S1b: PNG karşılığı olan grafik yerleri (görsel çizer). Diğerleri S1'deki gibi boş kalır.
# Beklenen küme uygulama kodundan okunmaz; burada açıkça yazılıdır.
_GORSELLI = (
    [f"U{i}" for i in range(1, 7)]
    + [f"O{i}" for i in range(1, 5)]
    + ["M4", "M6", "M8", "M9", "K1", "R1", "P1"]
    + [f"X{i}" for i in range(1, 6)]
)
_GORSELSIZ = ["Z1", "D1", "D2", "D3", "D4", "M1", "M2", "M3", "M5", "M7", "R2", "H1"]
# Sekme -> o sekmede, sayfadaki sırayla çizilmesi gereken görseller ("kimlik" ya da "kimlik:varyant").
_SEKME_GORSELLERI = {
    "ozet": [],
    "veri": [],
    "uci": ["U1", "U2", "U3", "U4", "U5", "U6"],
    "oulad": ["O1", "O2", "O3", "O4:n_unsubmitted"],
    "model": ["M4", "M6", "M8", "M9"],
    "kural": ["K1", "R1"],
    "ek": ["P1:once", "P1:sonuc", "X1", "X2", "X3", "X4", "X5"],
    "hoca": [],
    "sistem": [],
    "hatalar": [],
    "kaynak": [],
}


def _govde(islev) -> list[ast.stmt]:
    return ast.parse(textwrap.dedent(inspect.getsource(islev))).body[0].body


def _docstring_mi(govde: list[ast.stmt]) -> bool:
    return (
        len(govde) == 1
        and isinstance(govde[0], ast.Expr)
        and isinstance(govde[0].value, ast.Constant)
        and isinstance(govde[0].value.value, str)
    )


def _gorsel_ciz_cagirir_mi(islev) -> bool:
    return any(
        isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "gorsel_ciz"
        for govde in _govde(islev)
        for d in ast.walk(govde)
    )


def test_grafik_yerleri_tam_liste_gorselliler_gorsel_cizer_digerleri_bos() -> None:
    assert sorted(arastirma.GRAFIKLER) == sorted(_GRAFIK_KIMLIKLERI)
    assert len(_GRAFIK_KIMLIKLERI) == 34
    assert sorted([*_GORSELLI, *_GORSELSIZ]) == sorted(_GRAFIK_KIMLIKLERI)
    for kimlik, islev in arastirma.GRAFIKLER.items():
        assert islev.__name__ == f"grafik_{kimlik.lower()}"
        if kimlik in _GORSELLI:
            assert _gorsel_ciz_cagirir_mi(islev), f"{kimlik}: gorsel_ciz çağırmalı"
        else:
            assert _docstring_mi(_govde(islev)), f"{kimlik}: görseli yok, yalnız docstring olmalı"


@pytest.mark.parametrize("lang", ["tr", "en"])
def test_her_grafik_yeri_tam_bir_kez_cagrilir(lang: str) -> None:
    sahteler = {kimlik: MagicMock(name=kimlik) for kimlik in _GRAFIK_KIMLIKLERI}
    with patch.dict(arastirma.GRAFIKLER, sahteler):
        for bolum in SEKME_SIRA:
            at = _sayfa(lang, False, bolum)
            assert len(at.exception) == 0
    for kimlik, sahte in sahteler.items():
        assert sahte.call_count == 1, f"{kimlik}: {sahte.call_count} kez çağrıldı"
        paket, dil = sahte.call_args.args
        assert dil == lang
        assert "turev" in paket and "oulad" in paket


def _beklenen_satir(paket: dict, anahtar: str, lang: str) -> dict:
    kimlik, _, varyant = anahtar.partition(":")
    return arastirma.gorsel_satiri(paket, kimlik, lang, varyant or None)


_UCI_KIMLIKLERI = ("U1", "U2", "U3", "U4", "U5", "U6")


@pytest.mark.parametrize("kimlik", _UCI_KIMLIKLERI)
@pytest.mark.parametrize("eksik,var", [("tr", "en"), ("en", "tr")])
def test_dilde_gorsel_yoksa_baska_dile_dusulmez_hata_verir(kimlik: str, eksik: str, var: str) -> None:
    """Paketten bir dilin satırı çıkarılırsa o dil EN/TR görselle doldurulmaz: hata verir."""
    paket = arastirma.paketi_oku()
    kisitli = {
        **paket,
        "figures": {
            **paket["figures"],
            "charts": [
                s for s in paket["figures"]["charts"] if not (s["id"] == kimlik and s["lang"] == eksik)
            ],
        },
    }
    assert arastirma.gorsel_satirlari(kisitli, kimlik, eksik) == []
    assert len(arastirma.gorsel_satirlari(kisitli, kimlik, var)) == 1
    with pytest.raises(KeyError):
        arastirma.gorsel_satiri(kisitli, kimlik, eksik)
    with patch("streamlit.image") as sahte, pytest.raises(KeyError):
        arastirma.gorsel_ciz(kisitli, eksik, kimlik)
    sahte.assert_not_called()
    # Kalan dil etkilenmez.
    assert arastirma.gorsel_satiri(kisitli, kimlik, var)["lang"] == var


def test_her_gorsel_kimligi_her_dilde_tam_bir_satira_ve_dosyaya_sahip() -> None:
    paket = arastirma.paketi_oku()
    for kimlik in _GORSELLI:
        for lang in ("tr", "en"):
            satirlar = arastirma.gorsel_satirlari(paket, kimlik, lang)
            assert satirlar, f"{kimlik}/{lang}: görsel satırı yok"
            for satir in satirlar:
                assert satir["lang"] == lang
                assert f"_{lang}" in Path(satir["path"]).name
                assert (arastirma._ASSET_KOKU / satir["path"]).is_file()


def _yapraklar(at: AppTest) -> list:
    """Sayfanın çizim sırasındaki yaprak öğeleri (kapsayıcılar atlanır)."""
    return [d for d in at.main if not isinstance(d, Block)]


@pytest.mark.parametrize("lang", ["tr", "en"])
@pytest.mark.parametrize("bolum", list(SEKME_SIRA))
def test_sekme_yalniz_kendi_gorsellerini_ister_ve_dosyalar_paketle_ayni(lang: str, bolum: str) -> None:
    """Tembel yükleme: yalnız açık sekmenin görselleri istenir; dosya md5'i paketteki satırla aynıdır."""
    assert list(_SEKME_GORSELLERI) == list(SEKME_SIRA)
    paket = arastirma.paketi_oku()
    with patch("streamlit.image") as sahte:
        at = _sayfa(lang, False, bolum)
    assert len(at.exception) == 0, [e.value for e in at.exception]
    beklenen = [_beklenen_satir(paket, a, lang) for a in _SEKME_GORSELLERI[bolum]]
    cagrilar = sahte.call_args_list
    assert [Path(c.args[0]) for c in cagrilar] == [arastirma._ASSET_KOKU / s["path"] for s in beklenen]
    for cagri, satir in zip(cagrilar, beklenen):
        assert hashlib.md5(Path(cagri.args[0]).read_bytes()).hexdigest() == satir["md5"]
        assert cagri.kwargs["width"] == "stretch"
        assert cagri.kwargs["alt"] == satir["title"]
        assert cagri.kwargs["caption"].strip()


@pytest.mark.parametrize("lang", ["tr", "en"])
def test_haritalanan_her_grafik_kimligi_gorsel_cizer(lang: str) -> None:
    """Haritalı her kimlik her dilde sayfada bir <img> (Image) öğesi çizer; altyazısı başlığı içerir."""
    paket = arastirma.paketi_oku()
    cizilen: dict[str, str] = {}
    for bolum, anahtarlar in _SEKME_GORSELLERI.items():
        at = _sayfa(lang, False, bolum)
        assert len(at.exception) == 0, [e.value for e in at.exception]
        resimler = [d for d in _yapraklar(at) if d.type == "image"]
        assert len(resimler) == len(anahtarlar), f"{bolum}: {len(resimler)} görsel"
        for resim, anahtar in zip(resimler, anahtarlar):
            satir = _beklenen_satir(paket, anahtar, lang)
            (altyazi,) = resim.captions
            assert satir["title"] in altyazi
            if satir["alt"]:
                assert satir["alt"] in altyazi
            cizilen[anahtar] = altyazi
    assert {a.partition(":")[0] for a in cizilen} == set(_GORSELLI)


@pytest.mark.parametrize("lang", ["tr", "en"])
def test_altyazilar_dolu_ve_cozulmemis_isaret_icermez(lang: str) -> None:
    eksik = []
    for bolum, anahtarlar in _SEKME_GORSELLERI.items():
        if not anahtarlar:
            continue
        at = _sayfa(lang, False, bolum)
        for resim in (d for d in _yapraklar(at) if d.type == "image"):
            (altyazi,) = resim.captions
            if not altyazi.strip() or ARAYUZ[lang]["alt_eksik"] in altyazi:
                eksik.append((bolum, altyazi))
            assert "{" not in altyazi and "}" not in altyazi and "TODO" not in altyazi
    assert eksik == [], f"alt metni eksik grafikler: {eksik}"


@pytest.mark.parametrize("lang", ["tr", "en"])
def test_o4_secici_her_secenek_kendi_gorselini_cizer(lang: str) -> None:
    paket = arastirma.paketi_oku()
    secenekler = list(METIN[lang]["oulad_o4_secenekler"])
    assert len(secenekler) == 4
    at = _sayfa(lang, False, "oulad")
    radyo = at.radio(key=f"ar_o4_sinyal_{lang}")
    for secenek, varyant in zip(secenekler, ("n_unsubmitted", "vle_clicks", "score_mean", "score_vs_hist")):
        radyo.set_value(secenek).run()
        assert len(at.exception) == 0
        resimler = [d for d in _yapraklar(at) if d.type == "image"]
        assert len(resimler) == 4  # O1, O2, O3 + seçili O4
        satir = arastirma.gorsel_satiri(paket, "O4", lang, varyant)
        assert satir["title"] in resimler[-1].captions[0]
        radyo = at.radio(key=f"ar_o4_sinyal_{lang}")


@pytest.mark.parametrize("lang", ["tr", "en"])
def test_p1_once_gorseli_ve_sonuclar_acilirinda_sonuc_gorseli(lang: str) -> None:
    paket = arastirma.paketi_oku()
    at = _sayfa(lang, False, "ek")
    sonuclar = [e for e in at.expander if e.label == ARAYUZ[lang]["sonuclar"]]
    assert len(sonuclar) == 1
    icindekiler = [d for d in sonuclar[0] if not isinstance(d, Block) and d.type == "image"]
    assert len(icindekiler) == 1
    assert arastirma.gorsel_satiri(paket, "P1", lang, "sonuc")["title"] in icindekiler[0].captions[0]
    # Sekmedeki ilk görsel (açılırın dışındaki) P1'in "önce" görselidir.
    ilk = next(d for d in _yapraklar(at) if d.type == "image")
    assert ilk is not icindekiler[0]
    assert arastirma.gorsel_satiri(paket, "P1", lang, "once")["title"] in ilk.captions[0]


# Kutu -> (sekme, grafik kimliği, kapsayıcı anahtarı, metin anahtarı). Görseli olan grafiğe dayanan kutular.
_KANITLI_KUTULAR = [
    ("uci", "U2", "ar_kutu_bulgu_uci_u2_bulgu", "uci_u2_bulgu"),
    ("uci", "U5", "ar_kutu_bulgu_uci_u5_bulgu", "uci_u5_bulgu"),
    ("uci", "U6", "ar_kutu_hata_uci_hata", "uci_hata"),
    ("oulad", "O1", "ar_kutu_bulgu_oulad_o1_bulgu", "oulad_o1_bulgu"),
    ("oulad", "O4", "ar_kutu_bulgu_oulad_o4_bulgu", "oulad_o4_bulgu"),
    ("ek", "X3", "ar_kutu_bulgu_ek_e1_bulgu", "ek_e1_bulgu"),
]


@pytest.mark.parametrize("lang", ["tr", "en"])
@pytest.mark.parametrize("sekme,grafik,kutu_anahtari,metin_anahtari", _KANITLI_KUTULAR)
def test_bulgu_kutusu_grafigin_hemen_altinda_ve_atifli(
    lang: str, sekme: str, grafik: str, kutu_anahtari: str, metin_anahtari: str
) -> None:
    if metin_anahtari in EKSIK_EN and lang == "en":
        pytest.skip("kutunun İngilizcesi yok (EKSIK_EN)")
    paket = arastirma.paketi_oku()
    at = _sayfa(lang, False, sekme)
    assert len(at.exception) == 0
    yapraklar = _yapraklar(at)
    kutu = next(d for d in at.main if isinstance(d, Block) and d.key == kutu_anahtari)
    ilk = next(d for d in kutu if not isinstance(d, Block))
    sira = next(i for i, d in enumerate(yapraklar) if d is ilk)
    onceki = yapraklar[sira - 1]
    assert onceki.type == "image", f"{kutu_anahtari}: kutunun üstünde görsel yok ({onceki.type})"
    satirlar = arastirma.gorsel_satirlari(paket, grafik, lang)
    baslik = {s["cite_title"] for s in satirlar}
    assert len(baslik) == 1
    (baslik,) = baslik
    atif = f"*{ARAYUZ[lang]['atif_grafik']}: {baslik}*"
    # Atıf, kutunun en başında (Bulgu etiketinden hemen sonra; Hata kutusunda etiketsiz) durur.
    onek = f"**{ARAYUZ[lang]['bulgu']}.** " if "_bulgu_" in kutu_anahtari else ""
    assert ilk.value.startswith(f"{onek}{atif}\n\n"), ilk.value[:120]
    # Görsel, atıf yapılan grafiğin kendisidir (varyantlı O4'te açık olan seçenek).
    assert any(s["title"] in onceki.captions[0] for s in satirlar)


@pytest.mark.parametrize("lang", ["tr", "en"])
def test_atif_prefiksi_dil_ve_bicim(lang: str) -> None:
    assert ARAYUZ["tr"]["atif_grafik"] == "Grafik"
    assert ARAYUZ["en"]["atif_grafik"] == "Chart"
    at = _sayfa(lang, False, "uci")
    metin = _sayfa_metni(at)
    onek = f"*{ARAYUZ[lang]['atif_grafik']}: "
    assert onek in metin


def test_gorseli_olmayan_grafige_dayanan_ya_da_belirsiz_kutular_atifsiz() -> None:
    """M3/M5/M7/R2 görselsizdir; E2/E3/hoca kutuları hangi grafiğe dayandığı belirsiz olduğundan dokunulmadı."""
    kutular = [
        ("model", "ar_kutu_bulgu_model_m3_bulgu"),
        ("model", "ar_kutu_bulgu_model_m5_bulgu"),
        ("model", "ar_kutu_bulgu_model_m7_bulgu"),
        ("kural", "ar_kutu_bulgu_kural_r2_bulgu"),
        ("ek", "ar_kutu_bulgu_ek_e2_bulgu"),
        ("ek", "ar_kutu_bulgu_ek_e3_bulgu"),
        ("ek", "ar_kutu_hata_ek_e3_karar"),
        ("hoca", "ar_kutu_bulgu_hoca_bulgu"),
    ]
    bulunan = 0
    for sekme, anahtar in kutular:
        at = _sayfa("tr", False, sekme)
        for kutu in (d for d in at.main if isinstance(d, Block) and d.key == anahtar):
            bulunan += 1
            assert all("*Grafik: " not in d.value for d in kutu if not isinstance(d, Block)), anahtar
    assert bulunan > 0


def test_grafik_yeri_yer_tutucu_metin_cizmez() -> None:
    """Grafiğe ait metinler (alt yazı, not) S1'de görünmez; grafik gelince çizilir."""
    z1 = METIN["tr"]["z1_duraklar"]
    metin = _sayfa_metni(_sayfa("tr", False, "ozet"))
    for parca in _metinler(z1):
        assert parca not in metin
    assert "TODO" not in metin


# Yeni v2 metinleri: hangi sekmede, hangi anahtarlar düz metin olarak çizilir.
_DUZ_METINLER = {
    "ozet": ["okuma_suresi", "ozet_gosterebildik_baslik", "ozet_gosteremedik_baslik"],
    "veri": ["veri_bu_bolumde", "veri_d0_baslik", "veri_sosyokultur"],
    "uci": [
        "uci_bu_bolumde", "uci_u2_bulgu", "uci_u5_bulgu", "uci_hata_baglanti",
        "uci_u7_baslik", "uci_bolum_sonu",
    ],
    "oulad": ["oulad_bu_bolumde", "oulad_o1_bulgu", "oulad_o4_bulgu"],
    "model": [
        "model_bu_bolumde", "model_m0_baslik", "model_m3_bulgu", "model_m5_bulgu", "model_m7_bulgu",
    ],
    "kural": ["kural_r2_bulgu"],
    "ek": [
        "ek_bu_bolumde", "ek_suphe", "ek_onkayit", "ek_e2_metin", "ek_e2_bulgu", "ek_e1_metin",
        "ek_e1_bulgu", "ek_e3_metin", "ek_e3_karar", "ek_e3_bulgu", "ek_e4_metin",
    ],
    "hoca": ["hoca_bu_bolumde", "hoca_10_1", "hoca_10_2", "hoca_10_3", "hoca_bulgu"],
    "sistem": ["sistem_kopru"],
    "hatalar": ["hatalar_bu_bolumde"],
    "kaynak": ["kaynak_yazar"],
}
# v1 içeriği (Özet'te kalanlar ve spec'in adını verdiği sekmeye taşınanlar).
_V1_YERLERI = {
    "ozet": [
        "hero_baslik", "hero_alt", "ozet1_deger", "ozet1_aciklama", "ozet2_deger", "ozet2_aciklama",
        "ozet3_deger", "ozet3_aciklama", "uyari", "soru", "veri1_baslik", "veri1", "veri2_baslik",
        "veri2", "veri_alt",
    ],
    "veri": ["oulad_duzen"],
    "uci": ["uci_bulgu", "uci_hata", "uci_kapanis"],
    "model": [
        "b45_giris", "kart_ders", "kart_zaman", "kart_sira", "kart_hoca", "b46_metin",
        "tablo_46_baslik", "b46_kapanis", "b47", "b48",
    ],
    "kural": ["b49_giris", "b49_secim", "b410"],
    "sistem": ["b411"],
    "kaynak": ["sinirlar", "yeniden_uretim"],
}
# Grafik yerinin sahip olduğu metinler: S1'de çizilmez.
_GRAFIK_METINLERI = {
    "z1_duraklar", "veri_d1_alt", "veri_d2_not", "uci_u1_not", "uci_u4_alt", "oulad_o2_alt",
    "oulad_o4_secenekler", "oulad_o4_cumleler", "oulad_o4_nedensellik", "hoca_h1_katman",
    "hoca_h1_aciklama", "ek_onkayit_ozet", "ek_x2_alt", "ek_x5_not", "u1_dahil", "u1_haric", "r1_not",
}
# Yapılı bloklar (tablo, kart, liste); ayrı testlerde sınanır.
_YAPILI = {
    "sekmeler", "ozet_gosterebildik", "ozet_gosteremedik", "veri_d0", "oulad_o5", "model_m0",
    "hoca_basliklar", "hoca_h2", "hata_basliklar", "hata_tur", "hata_bag_not", "hata_govde",
    "kaynak_kaynakca", "ek_basliklar", "ek_harita", "ek_sorular", "ek_muhur", "ek_l1", "ek_kapanis",
    "ham_uci", "ham_oulad", "ham_model", "tablo_46", "tablo_11", "sayfa_sonu",
}


def _kodda_basvurulan_anahtarlar() -> set[str]:
    """arastirma.py kaynağında metin anahtarı olarak geçen her dize sabiti.

    `b.m("x")`, `b.yaz("x")`, `t["x"]`, `b.t["x"]` gibi bütün erişim biçimlerini kapsar;
    belirli anahtarlara özel değildir. Çizim doğruluğu ayrıca sayfa metni testleriyle sınanır.
    """
    kaynak = Path(arastirma.__file__).read_text(encoding="utf-8")
    sabitler = {
        dugum.value
        for dugum in ast.walk(ast.parse(kaynak))
        if isinstance(dugum, ast.Constant) and isinstance(dugum.value, str)
    }
    return sabitler & set(METIN["tr"])


def test_her_metin_anahtari_bir_yerde_hesaplanmis() -> None:
    """Hiçbir metin sessizce düşmez: ya çizilir, ya yapılı bloktur, ya grafik yerine aittir."""
    sayilan = set(_GRAFIK_METINLERI) | _YAPILI | _kodda_basvurulan_anahtarlar()
    for liste in (*_DUZ_METINLER.values(), *_V1_YERLERI.values()):
        sayilan |= set(liste)
    assert set(METIN["tr"]) - sayilan == set(), "hesapta olmayan metin anahtarları"
    assert sayilan - set(METIN["tr"]) == set(), "metinde olmayan anahtar adları"


@pytest.mark.parametrize("lang", ["tr", "en"])
@pytest.mark.parametrize("bolum", [k for k, _, _ in _SEKMELER])
def test_bolum_metinleri_ve_v1_icerigi_dogru_sekmede(lang: str, bolum: str) -> None:
    paket = arastirma.tam_paket()
    metin = _sayfa_metni(_sayfa(lang, False, bolum))
    beklenen = _DUZ_METINLER.get(bolum, []) + _V1_YERLERI.get(bolum, [])
    for anahtar in beklenen:
        if anahtar not in METIN[lang]:
            assert anahtar in EKSIK_EN
            continue
        cozulmus = arastirma.coz(METIN[lang][anahtar], paket, lang)
        assert _gorunur(cozulmus, metin), f"{lang}/{bolum}: '{anahtar}' çizilmedi"
    for anahtar in _GRAFIK_METINLERI & set(METIN[lang]):
        parca = arastirma.coz(METIN[lang][anahtar], paket, lang) if isinstance(METIN[lang][anahtar], str) else None
        if parca and len(parca) > 25:
            assert not _gorunur(parca, metin), f"{lang}/{bolum}: grafik metni '{anahtar}' çizilmemeliydi"


@pytest.mark.parametrize("lang", ["tr", "en"])
def test_v1_icerigi_baska_sekmelere_dagilmadan_bir_kez_cizilir(lang: str) -> None:
    """v1 metinleri yalnız kendi sekmesinde; başka sekmede tekrar çizilmez."""
    paket = arastirma.tam_paket()
    for bolum in SEKME_SIRA:
        metin = _sayfa_metni(_sayfa(lang, False, bolum))
        for yer, anahtarlar in _V1_YERLERI.items():
            if yer == bolum:
                continue
            for anahtar in anahtarlar:
                parca = arastirma.coz(METIN[lang][anahtar], paket, lang)
                if len(parca) > 40:
                    assert not _gorunur(parca, metin), f"{lang}: v1 '{anahtar}' {bolum} sekmesinde de var"


def test_eksik_en_bloklari_ingilizce_sayfada_cizilmez() -> None:
    paket = arastirma.tam_paket()
    en = _tum_sekmeler_metni("en")
    for anahtar in EKSIK_EN:
        assert anahtar not in METIN["en"]
        for parca in _metinler(METIN["tr"][anahtar]):
            cozulmus = arastirma.coz(parca, paket, "tr")
            if len(cozulmus) >= 25:  # kısa sözcükler İngilizce metinde tesadüfen geçebilir
                assert not _gorunur(cozulmus, en), f"EN sayfada Türkçe blok: {anahtar}"


def test_ek_sekmesi_yapili_bloklari_tr() -> None:
    paket = arastirma.tam_paket()
    metin = _sayfa_metni(_sayfa("tr", False, "ek"))
    harita = METIN["tr"]["ek_harita"]
    for durak, bulduk, eksik in harita["duraklar"]:
        assert durak in metin and bulduk in metin and eksik in metin
    for kisa, soru in METIN["tr"]["ek_sorular"]:
        assert kisa in metin and soru in metin
    for satir in arastirma.muhur_satirlari(paket):
        assert satir["md5"] in metin
    l1 = METIN["tr"]["ek_l1"]
    assert metin.count('class="ar-gri"') == sum(
        hucre == l1["gri"] for satir in l1["satirlar"] for hucre in satir
    )
    for gozlem in l1["gozlemler"]:
        assert arastirma.coz(gozlem, paket, "tr") in metin
    for kaynak in l1["kaynakca"]:
        assert arastirma.coz(kaynak, paket, "tr") in metin
    assert METIN["tr"]["ek_kapanis"]["degisti"] in metin
    assert METIN["tr"]["ek_kapanis"]["degismedi"] in metin


@pytest.mark.parametrize("lang", ["tr", "en"])
def test_hata_kartlari_on_iki_baslikla_cizilir(lang: str) -> None:
    metin = _sayfa_metni(_sayfa(lang, False, "hatalar"))
    basliklar = METIN[lang]["hata_basliklar"]
    assert len(basliklar) == 12
    for sira, baslik in enumerate(basliklar, start=1):
        assert f"**{sira}. {baslik}**" in metin


@pytest.mark.parametrize("lang", ["tr", "en"])
def test_veri_ve_model_tablolari_hucreleri_cozulmus(lang: str) -> None:
    paket = arastirma.tam_paket()
    veri = _sayfa_metni(_sayfa(lang, False, "veri"))
    if "veri_d0" in METIN[lang]:
        for satir in METIN[lang]["veri_d0"]["satirlar"]:
            for hucre in satir:
                assert _gorunur(arastirma.coz(hucre, paket, lang), veri)
    model = _sayfa_metni(_sayfa(lang, False, "model"))
    for satir in METIN[lang]["model_m0"]["satirlar"]:
        for hucre in satir:
            assert _gorunur(arastirma.coz(hucre, paket, lang), model)
    for not_metni in METIN[lang]["model_m0"]["notlar"]:
        assert not_metni in model
