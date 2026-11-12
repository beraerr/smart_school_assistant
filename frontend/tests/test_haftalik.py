"""Haftalık sunum sayfası ve ad ayrıştırıcı."""

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest
from PIL import Image
from streamlit.testing.v1 import AppTest

_FRONTEND = Path(__file__).resolve().parents[1]
_ROOT = _FRONTEND.parent
for yol in (_ROOT, _FRONTEND):
    if str(yol) not in sys.path:
        sys.path.insert(0, str(yol))

import haftalik  # noqa: E402
from i18n import get_text  # noqa: E402

_APP = _FRONTEND / "app.py"
_GERCEK_KOK = _FRONTEND / "assets" / "haftalik"

_BETIK_YOLU = _ROOT / "scripts" / "haftalik_slaytlar.py"
_OZEL = importlib.util.spec_from_file_location("haftalik_slaytlar", _BETIK_YOLU)
assert _OZEL is not None and _OZEL.loader is not None
betik = importlib.util.module_from_spec(_OZEL)
sys.modules["haftalik_slaytlar"] = betik
_OZEL.loader.exec_module(betik)


# --- Ad ayrıştırıcı -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("ad", "beklenen"),
    [("hafta11_tr.pptx", (11, "tr")), ("hafta06_en.pptx", (6, "en"))],
)
def test_ad_ayristirici_gecerli_adlar(ad: str, beklenen: tuple[int, str]) -> None:
    assert betik.sunum_adi_ayristir(ad) == beklenen


@pytest.mark.parametrize(
    "ad",
    ["Hafta11_Entegrasyon.pptx", "hafta1_tr.pptx", "hafta11_de.pptx"],
)
def test_ad_ayristirici_gecersiz_adlar_hata_verir(ad: str) -> None:
    with pytest.raises(ValueError):
        betik.sunum_adi_ayristir(ad)


def test_kurala_uymayan_dosya_betigi_durdurur_ve_cikti_silinmez(tmp_path: Path) -> None:
    sunumlar = tmp_path / "sunumlar"
    sunumlar.mkdir()
    (sunumlar / "hafta01_tr.pptx").write_bytes(b"x")
    (sunumlar / "Hafta02_Ozel.pptx").write_bytes(b"x")
    cikti = tmp_path / "cikti"
    cikti.mkdir()
    (cikti / "eski.txt").write_text("durur", encoding="utf-8")
    with pytest.raises(ValueError):
        betik.kur(sunumlar, cikti)
    assert (cikti / "eski.txt").is_file()


# --- Sayfa ----------------------------------------------------------------------------


def _png(yol: Path, renk: tuple[int, int, int]) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 6), renk).save(yol)


def _sunum(kok: Path, hafta: int, dil: str, adet: int, renk: tuple[int, int, int]) -> dict:
    klasor = f"hafta{hafta:02d}/{dil}"
    slaytlar = []
    for sira in range(1, adet + 1):
        yol = f"{klasor}/slayt_{sira:02d}.png"
        _png(kok / yol, renk)
        slaytlar.append(yol)
    pdf = f"{klasor}/sunum.pdf"
    (kok / pdf).write_bytes(b"%PDF-1.4 deneme")
    return {"pdf": pdf, "slaytlar": slaytlar}


def _manifest_kur(kok: Path) -> dict:
    """Hafta 11: TR 3 + EN 2 slayt. Hafta 6: yalnızca TR 1 slayt."""
    manifest = {
        "haftalar": [
            {"hafta": 6, "diller": {"tr": _sunum(kok, 6, "tr", 1, (200, 0, 0))}},
            {
                "hafta": 11,
                "diller": {
                    "tr": _sunum(kok, 11, "tr", 3, (0, 200, 0)),
                    "en": _sunum(kok, 11, "en", 2, (0, 0, 200)),
                },
            },
        ]
    }
    (kok / "haftalik.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


@pytest.fixture(autouse=True)
def _gecici_kok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Her testte sunum kökü geçici dizindir; ortam değişkeni betik yeniden çalışınca da kalır."""
    assert tmp_path.resolve() != _GERCEK_KOK.resolve()
    monkeypatch.setenv("HAFTALIK_DIZIN", str(tmp_path))


def _sayfa(kok: Path, lang: str, hafta: int | None = None) -> AppTest:
    # Sayfa manifesti ve görselleri yalnızca haftalik._kok() kökünden çözer; kök ortam
    # değişkeniyle geçici dizine yönlenir ve gerçek frontend/assets/haftalik/ okunmaz.
    assert kok.resolve() != _GERCEK_KOK.resolve()
    assert os.environ["HAFTALIK_DIZIN"] == str(kok)
    assert haftalik._kok() == kok
    at = AppTest.from_file(str(_APP), default_timeout=30)
    at.session_state["token"] = None
    at.session_state["user"] = None
    at.session_state["lang"] = lang
    at.query_params["sayfa"] = "haftalik"
    at.run()
    if hafta is not None:
        at.pills(key="hf_hafta").select(hafta).run()
    return at


def _slayt_sayisi(at: AppTest) -> int:
    # AppTest'te st.image düğümlerinin türü "image"dir ("imgs" proto alanı adıdır, düğüm türü değil).
    return sum(len(oge.proto.imgs) for oge in at.get("image"))


def _bilgiler(at: AppTest) -> list[str]:
    return [str(oge.value) for oge in at.info]


def _beklenen(manifest: dict, hafta: int, dil: str) -> int:
    for kayit in manifest["haftalar"]:
        if kayit["hafta"] == hafta:
            return len(kayit["diller"][dil]["slaytlar"])
    raise AssertionError(hafta)


@pytest.mark.parametrize("lang", ["tr", "en"])
def test_slayt_sayisi_manifestle_esit(tmp_path: Path, lang: str) -> None:
    manifest = _manifest_kur(tmp_path)
    at = _sayfa(tmp_path, lang)
    assert len(at.exception) == 0
    # Varsayılan seçim en küçük haftadır (hafta 6); hafta 11 seçilince kendi sayısı gelir.
    en_kucuk = min(kayit["hafta"] for kayit in manifest["haftalar"])
    assert at.pills(key="hf_hafta").value == en_kucuk == 6
    if lang == "en":
        # Hafta 6'nın İngilizce sürümü yoktur: slayt yok, açık mesaj var.
        assert _slayt_sayisi(at) == 0
        assert len(at.download_button) == 0
        at = _sayfa(tmp_path, lang, hafta=11)
        assert _slayt_sayisi(at) == _beklenen(manifest, 11, lang)
    else:
        assert _slayt_sayisi(at) == _beklenen(manifest, en_kucuk, lang)
    assert len(at.download_button) == 1
    assert at.download_button(key="hf_pdf").label == get_text(lang, "weekly_pdf")


def test_haftalar_kucukten_buyuge_ve_varsayilan_en_kucuk(tmp_path: Path) -> None:
    manifest = _manifest_kur(tmp_path)
    en_kucuk = min(kayit["hafta"] for kayit in manifest["haftalar"])
    assert en_kucuk == 6
    at = _sayfa(tmp_path, "tr")
    assert list(at.pills(key="hf_hafta").options) == ["Hafta 6", "Hafta 11"]
    assert at.pills(key="hf_hafta").value == en_kucuk
    assert list(at.pills(key="hf_hafta").indices) == [0]
    assert _slayt_sayisi(at) == _beklenen(manifest, en_kucuk, "tr")
    at_en = _sayfa(tmp_path, "en")
    assert list(at_en.pills(key="hf_hafta").options) == ["Week 6", "Week 11"]
    assert at_en.pills(key="hf_hafta").value == en_kucuk
    assert list(at_en.pills(key="hf_hafta").indices) == [0]


def test_secili_hafta_degisince_slaytlar_degisir(tmp_path: Path) -> None:
    manifest = _manifest_kur(tmp_path)
    at = _sayfa(tmp_path, "tr", hafta=6)
    assert len(at.exception) == 0
    assert _slayt_sayisi(at) == _beklenen(manifest, 6, "tr")
    at.pills(key="hf_hafta").select(11).run()
    assert len(at.exception) == 0
    assert _slayt_sayisi(at) == _beklenen(manifest, 11, "tr")


def test_kok_secici_degisince_de_gecici_kalir(tmp_path: Path) -> None:
    """Isırma testi: seçici hafta 11'e değişip betik yeniden çalışınca kök hâlâ geçici dizindir."""
    manifest = _manifest_kur(tmp_path)
    at = _sayfa(tmp_path, "tr")
    assert haftalik._kok() == tmp_path
    at.pills(key="hf_hafta").select(11).run()
    assert len(at.exception) == 0
    assert haftalik._kok() == tmp_path
    assert haftalik._kok().resolve() != _GERCEK_KOK.resolve()
    assert _slayt_sayisi(at) == _beklenen(manifest, 11, "tr")


def test_dil_eksikse_acik_mesaj_ve_diger_dilin_gorseli_yok(tmp_path: Path) -> None:
    manifest = _manifest_kur(tmp_path)
    assert _beklenen(manifest, 6, "tr") == 1
    at = _sayfa(tmp_path, "en", hafta=6)
    assert len(at.exception) == 0
    assert "The English version of this week is not available yet." in _bilgiler(at)
    assert _slayt_sayisi(at) == 0
    assert len(at.download_button) == 0


def test_sunum_dosyasi_olmayan_tr_icin_turkce_mesaj(tmp_path: Path) -> None:
    manifest = _manifest_kur(tmp_path)
    manifest["haftalar"][1]["diller"].pop("tr")
    (tmp_path / "haftalik.json").write_text(json.dumps(manifest), encoding="utf-8")
    at = _sayfa(tmp_path, "tr", hafta=11)  # varsayılan artık hafta 6; TR'si silinen hafta 11 seçilir
    assert "Bu haftanın Türkçe sürümü henüz yok." in _bilgiler(at)
    assert _slayt_sayisi(at) == 0
    assert len(at.download_button) == 0


@pytest.mark.parametrize(
    ("lang", "mesaj"),
    [("tr", "Henüz yüklenmiş sunum yok."), ("en", "No presentations have been uploaded yet.")],
)
def test_manifest_yoksa_bos_mesaji(tmp_path: Path, lang: str, mesaj: str) -> None:
    at = _sayfa(tmp_path, lang)
    assert len(at.exception) == 0
    assert len(at.error) == 0
    assert mesaj in _bilgiler(at)
    assert _slayt_sayisi(at) == 0


def test_kok_gecici_dizine_yonlenir_gercek_klasor_etkilemez(tmp_path: Path) -> None:
    """Gerçek klasör var da olsa yok da olsa sonuç yalnızca geçici kökten gelir."""
    assert haftalik._kok() == tmp_path
    assert haftalik.manifesti_oku() == []  # geçici kökte manifest yok
    at = _sayfa(tmp_path, "tr")
    assert "Henüz yüklenmiş sunum yok." in _bilgiler(at)
    assert _slayt_sayisi(at) == 0
    manifest = _manifest_kur(tmp_path)
    at = _sayfa(tmp_path, "en", hafta=11)  # varsayılan artık hafta 6 (EN sürümü yok)
    assert _slayt_sayisi(at) == _beklenen(manifest, 11, "en")


def test_manifest_bossa_bos_mesaji(tmp_path: Path) -> None:
    (tmp_path / "haftalik.json").write_text(json.dumps({"haftalar": []}), encoding="utf-8")
    at = _sayfa(tmp_path, "tr")
    assert len(at.exception) == 0
    assert "Henüz yüklenmiş sunum yok." in _bilgiler(at)


# --- Araştırma sayfasındaki bağlantı --------------------------------------------------


def _arastirma(lang: str) -> AppTest:
    at = AppTest.from_file(str(_APP), default_timeout=30)
    at.session_state["token"] = None
    at.session_state["user"] = None
    at.session_state["lang"] = lang
    at.query_params["sayfa"] = "arastirma"
    at.run()
    return at


@pytest.mark.parametrize(
    ("lang", "etiket"),
    [("tr", "Haftalık raporlar →"), ("en", "Weekly reports →")],
)
def test_arastirma_sayfasinda_haftalik_baglantisi(lang: str, etiket: str) -> None:
    at = _arastirma(lang)
    assert len(at.exception) == 0
    assert at.button(key="ar_haftalik").label == etiket


def test_baglanti_haftalik_sayfaya_goturur() -> None:
    at = _arastirma("tr")
    at.button(key="ar_haftalik").click().run()
    assert len(at.exception) == 0
    assert at.query_params.get("sayfa") == "haftalik"
    assert "bolum" not in at.query_params


def test_haftalik_sayfada_klavye_acan_kontrol_yok(tmp_path: Path) -> None:
    _manifest_kur(tmp_path)
    at = _sayfa(tmp_path, "tr")
    assert len(at.exception) == 0
    assert len(at.selectbox) == 0
    assert len(at.text_input) == 0
    assert [kutu.key for kutu in at.segmented_control] == ["lang_secim"]
    assert [kutu.key for kutu in at.pills] == ["hf_hafta"]
    assert at.segmented_control(key="lang_secim").options == ["TR", "EN"]


def test_haftalik_dil_kontrolu_secimle_dil_degisir(tmp_path: Path) -> None:
    _manifest_kur(tmp_path)
    at = _sayfa(tmp_path, "tr")
    at.segmented_control(key="lang_secim").select("EN").run()
    assert len(at.exception) == 0
    assert at.session_state["lang"] == "en"
    assert list(at.pills(key="hf_hafta").options) == ["Week 6", "Week 11"]


def test_haftalik_dil_secimi_kaldirilinca_onceki_dil_korunur(tmp_path: Path) -> None:
    _manifest_kur(tmp_path)
    at = _sayfa(tmp_path, "en")
    at.segmented_control(key="lang_secim").unselect("EN").run()
    assert len(at.exception) == 0
    assert at.session_state["lang"] == "en"
    assert at.segmented_control(key="lang_secim").value == "EN"
