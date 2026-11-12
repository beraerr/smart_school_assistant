"""Herkese açık araştırma sayfası (docs/arastirma_raporu_spec_v2.md ve eki).

Sayfa giriş gerektirmez, api_client'ı ve backend'i çağırmaz. Bütün sayılar paketlenmiş
JSON'dan gelir; metindeki `{yol:bicim}` alanları burada çözülür. Sayfa 11 sekmedir
(`arastirma_metin.SEKME_SIRA`); seçili sekme adres çubuğunda `&bolum=<kimlik>` olarak durur.
Grafik fonksiyonları (Z1, D1–D4, ...): paketteki `figures.charts` satırında karşılığı (PNG) olan
kimlikler o görseli seçili dile göre çizer; karşılığı olmayanlar (S2–S5'te çizilecek) boştur.
Görseller yalnızca açık sekmede okunur (kapalı sekmenin işlevleri çağrılmaz).
"""

import base64
import csv
import functools
import html
import io
import json
from collections.abc import Callable
from dataclasses import dataclass
from itertools import zip_longest
from pathlib import Path

import streamlit as st

from arastirma_metin import (
    ARAYUZ,
    BICIMLER,
    HATA_BAGLANTI,
    KOD_BLOGU,
    METIN,
    SEKME_SIRA,
    YER_TUTUCU,
)
from i18n import get_text

_KOK = Path(__file__).resolve().parent
_PAKET = _KOK / "assets" / "arastirma" / "arastirma.json"
_LOGO = _KOK / "assets" / "logo.svg"
_ASSET_KOKU = _KOK / "assets" / "arastirma"
# O4 sinyal seçicisi: seçenek sırası `METIN[dil]["oulad_o4_secenekler"]` sırasıdır (spec v2, 6).
_O4_SINYALLER = ("n_unsubmitted", "vle_clicks", "score_mean", "score_vs_hist")


# --- Paket ve biçimleyici -------------------------------------------------------------


@st.cache_data(show_spinner=False)
def paketi_oku() -> dict:
    """Paketi bir kez okur. Dosya yoksa ya da bozuksa hata olduğu gibi yükselir."""
    return json.loads(_PAKET.read_text(encoding="utf-8"))


def yol_degeri(paket: dict, yol: str) -> object:
    """`a.b.c` yolunu paketten okur. Yol yoksa KeyError (tam yolla)."""
    deger: object = paket
    for parca in yol.split("."):
        if not isinstance(deger, dict) or parca not in deger:
            raise KeyError(yol)
        deger = deger[parca]
    return deger


def turev(paket: dict) -> dict:
    """Paketteki satırlardan sayfa katmanında türetilen değerler (`turev.*` yolları).

    Hiçbir sayı elle yazılmaz; hepsi paketin kendi satırlarından okunur. Paketleyici ileride bu
    alanları kendisi üretirse bu işlev kalkar ve yollar paket anahtarına bağlanır (spec v2, 6:
    "üretici `risk_pivot`'tan min/max ... alanlarını türetir").
    """
    oulad = paket["oulad"]
    risk = oulad["risk_pivot"]
    en_dusuk = min(risk, key=lambda satir: satir["rate"])
    en_yuksek = max(risk, key=lambda satir: satir["rate"])

    def etiket(satir: dict) -> str:
        return f"{satir['module']} {satir['presentation']}"

    sinyaller = oulad["signals"]

    def dilim(sinyal: str, ad: str) -> float:
        for satir in sinyaller[sinyal]:
            if satir["bin"] == ad:
                return satir["rate"]
        raise KeyError(f"oulad.signals.{sinyal}: '{ad}' dilimi yok")

    egitim = [parca for parca in oulad["split"] if parca["part"] == "train"]
    if len(egitim) != 1:
        raise KeyError("oulad.split: tek bir 'train' parçası bekleniyordu")

    # E3 sabit kohort, GENERAL hgb, referans hedef, test dönemi, 30. gün (ek_metrics.json'dan
    # paketlenen `ek.e3.rows`). Tam bir satır bulunmazsa sessizce geçilmez, hata verilir.
    e3_satirlari = [
        satir
        for satir in paket["ek"]["e3"]["rows"]
        if satir["cutoff"] == 30
        and satir["view"] == "b_sabit_kohort"
        and satir["target"] == "referans"
        and satir["set"] == "GENERAL"
        and satir["model"] == "hgb"
        and satir["period"] == "test"
    ]
    if len(e3_satirlari) != 1:
        raise KeyError(f"ek.e3.rows: 30. gün sabit kohort GENERAL hgb test: {len(e3_satirlari)} satır (1 olmalı)")

    return {
        "uci": {"n_early": len(paket["uci"]["feature_sets"]["early"])},
        # Modül sayısı: risk_pivot'taki farklı `module` değerleri (elle yazılmaz).
        "oulad": {"n_modul": len({satir["module"] for satir in risk})},
        "ek": {"e3_30_test": e3_satirlari[0]["roc_auc"]["estimate"]},
        "risk": {
            "en_dusuk": etiket(en_dusuk),
            "en_dusuk_oran": en_dusuk["rate"],
            "en_yuksek": etiket(en_yuksek),
            "en_yuksek_oran": en_yuksek["rate"],
        },
        "sinyal": {
            "teslim_0": dilim("n_unsubmitted", "0"),
            "teslim_1": dilim("n_unsubmitted", "1"),
            "tik_ilk": sinyaller["vle_clicks"][0]["rate"],
            "tik_son": sinyaller["vle_clicks"][-1]["rate"],
            "not_eksik": dilim("score_mean", "eksik"),
        },
        "model": {"egitim_satir": egitim[0]["rows"]},
    }


def tam_paket() -> dict:
    """Paket + `turev` alanları. Sayfa ve yer tutucu çözümü bunu kullanır."""
    paket = paketi_oku()
    return {**paket, "turev": turev(paket)}


def _sayi_mi(deger: object) -> bool:
    return isinstance(deger, (int, float)) and not isinstance(deger, bool)


def _ondalik(deger: float, basamak: int, lang: str) -> str:
    metin = f"{deger:.{basamak}f}"
    return metin.replace(".", ",") if lang == "tr" else metin


def bicimle(deger: object, bicim: str, lang: str) -> str:
    """Değeri dile göre biçimler.

    tam: tamsayı, binlik ayraçlı (TR 32.593 / EN 32,593).
    yuzde: 0–1 oran, tek ondalık (TR %92,1 / EN 92.1%).
    yuzdetam: 0–1 oran, tam sayı yüzde (TR %20 / EN 20%); oran tam yüzdeye denk değilse hata verir.
    roc: üç ondalık (TR 0,792 / EN 0.792).
    kor: korelasyon, iki ondalık, eksi işareti "−" (TR 0,81 / −0,38; EN 0.81 / −0.38).
    puan: tek ondalık (TR 6,6 / EN 6.6).
    metin: olduğu gibi.
    """
    if bicim not in BICIMLER:
        raise ValueError(f"bilinmeyen biçim: {bicim}")
    if bicim == "metin":
        if not isinstance(deger, str):
            raise TypeError(f"metin biçimi metin ister: {deger!r}")
        return deger
    if bicim == "tam":
        if isinstance(deger, bool) or not isinstance(deger, int):
            raise TypeError(f"tam biçimi tamsayı ister: {deger!r}")
        metin = f"{deger:,}"
        return metin.replace(",", ".") if lang == "tr" else metin
    if not _sayi_mi(deger):
        raise TypeError(f"{bicim} biçimi sayı ister: {deger!r}")
    if bicim == "yuzde":
        sayi = _ondalik(float(deger) * 100, 1, lang)
        return f"%{sayi}" if lang == "tr" else f"{sayi}%"
    if bicim == "yuzdetam":
        yuzde = float(deger) * 100
        if abs(yuzde - round(yuzde)) > 1e-9:
            raise ValueError(f"yuzdetam biçimi tam yüzde ister: {deger!r}")
        return f"%{round(yuzde)}" if lang == "tr" else f"{round(yuzde)}%"
    if bicim == "roc":
        return _ondalik(float(deger), 3, lang)
    if bicim == "kor":
        return _ondalik(float(deger), 2, lang).replace("-", "\u2212")
    return _ondalik(float(deger), 1, lang)  # puan


def coz(metin: str, paket: dict, lang: str) -> str:
    """Metindeki `{yol:bicim}` alanlarını paketten doldurur; çözülmeyen alan hata verir."""

    def degistir(eslesme) -> str:
        yol, bicim = eslesme.group(1), eslesme.group(2)
        return bicimle(yol_degeri(paket, yol), bicim, lang)

    return YER_TUTUCU.sub(degistir, metin)


# --- Ham tablolar ---------------------------------------------------------------------


def _skaler_mi(deger: object) -> bool:
    return deger is None or isinstance(deger, (str, int, float, bool))


def satirla(deger: object) -> list[dict]:
    """Paket değerini düz satırlara açar (`st.dataframe` ve CSV için).

    İç içe sözlük ve liste anahtarları `anahtar_1`, `anahtar_2`, ... sütunları olur; üst düzey
    skaler alanlar altlarındaki satırlara bağlam olarak yazılır; skaler listeler virgülle
    birleşir. Desteklenmeyen biçim (liste içinde liste) sessizce geçilmez, hata verir.
    """
    satirlar: list[dict] = []

    def gez(dugum: object, baglam: dict, derinlik: int) -> None:
        if isinstance(dugum, dict):
            skaler: dict = {}
            cocuklar: list[tuple[str, object]] = []
            for anahtar, oge in dugum.items():
                if _skaler_mi(oge):
                    skaler[anahtar] = oge
                elif isinstance(oge, list) and all(_skaler_mi(x) for x in oge):
                    skaler[anahtar] = ", ".join(str(x) for x in oge)
                else:
                    cocuklar.append((anahtar, oge))
            if not cocuklar:
                satirlar.append({**baglam, **skaler})
                return
            for anahtar, oge in cocuklar:
                gez(oge, {**baglam, **skaler, f"anahtar_{derinlik + 1}": anahtar}, derinlik + 1)
        elif isinstance(dugum, list):
            for oge in dugum:
                if isinstance(oge, dict):
                    gez(oge, baglam, derinlik)
                elif _skaler_mi(oge):
                    satirlar.append({**baglam, "deger": oge})
                else:
                    raise TypeError(f"satırlanamayan iç içe liste: {type(oge).__name__}")
        else:
            satirlar.append({**baglam, "deger": dugum})

    gez(deger, {}, 0)
    if not satirlar:
        raise ValueError("ham tablo boş: paket değeri satır üretmedi")
    return satirlar


def _sutunlar(satirlar: list[dict]) -> list[str]:
    sutunlar: list[str] = []
    for satir in satirlar:
        for anahtar in satir:
            if anahtar not in sutunlar:
                sutunlar.append(anahtar)
    return sutunlar


def csv_metni(satirlar: list[dict]) -> str:
    """Satırları CSV metnine çevirir (UTF-8, `\\n` satır sonu, eksik hücre boş)."""
    cikti = io.StringIO()
    yazici = csv.DictWriter(
        cikti, fieldnames=_sutunlar(satirlar), restval="", lineterminator="\n"
    )
    yazici.writeheader()
    yazici.writerows(satirlar)
    return cikti.getvalue()


def _yol(yol: str) -> Callable[[dict], list[dict]]:
    return lambda paket: satirla(yol_degeri(paket, yol))


def _korelasyon_matrisi(paket: dict) -> list[dict]:
    matris = yol_degeri(paket, "uci.corr_matrix")
    kolonlar = matris["columns"]
    return [
        {"degisken": ad, **dict(zip(kolonlar, satir, strict=True))}
        for ad, satir in zip(kolonlar, matris["values"], strict=True)
    ]


def _devamsizlik_skalerleri(paket: dict) -> list[dict]:
    sozluk = yol_degeri(paket, "uci.absence")
    return [{"anahtar": ad, "deger": oge} for ad, oge in sozluk.items() if _skaler_mi(oge)]


def _g3_sifir(paket: dict) -> list[dict]:
    satirlar = [{"anahtar": "uci.g3_zero", "deger": yol_degeri(paket, "uci.g3_zero")}]
    for ders, sayi in yol_degeri(paket, "uci.g3_zero_by_subject").items():
        satirlar.append({"anahtar": f"uci.g3_zero_by_subject.{ders}", "deger": sayi})
    return satirlar


def _beklentiler(paket: dict) -> list[dict]:
    return [
        {alan: oge[alan] for alan in ("id", "expectation", "criterion", "result")}
        for oge in yol_degeri(paket, "ek.expectations")
    ]


def muhur_satirlari(paket: dict) -> list[dict]:
    """`ek.pre_registration`: her dosyanın her kaydı, sırayla (dosya, md5, zaman)."""
    satirlar = []
    for dosya, kayit in yol_degeri(paket, "ek.pre_registration").items():
        for adim in kayit["history"]:
            satirlar.append({"dosya": dosya, "md5": adim["md5"], "zaman": adim["time"]})
    return satirlar


# Her bölümün "Ham tablolar" açılırı: (başlık anahtarı | None, paket yolu, yükleyici).
# Başlık anahtarı METIN[dil]["ham_<bölüm>"] içinde aranır; yoksa paket yolu başlık olur.
HAM: dict[str, tuple[tuple[str | None, str, Callable[[dict], list[dict]]], ...]] = {
    "ozet": (
        (None, "sets.within_module_mean", _yol("sets.within_module_mean")),
        (None, "rule.capture_rule2", _yol("rule.capture_rule2")),
        (None, "rule.gap_rule2", _yol("rule.gap_rule2")),
    ),
    "veri": (
        (None, "oulad.tables", _yol("oulad.tables")),
        (None, "oulad.sample", _yol("oulad.sample")),
        (None, "oulad.final_result", _yol("oulad.final_result")),
        (None, "oulad.split", _yol("oulad.split")),
        (None, "model.presentations", _yol("model.presentations")),
    ),
    "uci": (
        ("korelasyon", "uci.top_corr", _yol("uci.top_corr")),
        ("korelasyon", "uci.corr_matrix", _korelasyon_matrisi),
        ("devamsizlik", "uci.absence.buckets", _yol("uci.absence.buckets")),
        ("devamsizlik", "uci.absence", _devamsizlik_skalerleri),
        ("g3_sifir", "uci.g3_zero", _g3_sifir),
    ),
    "oulad": (
        ("tablolar", "oulad.tables", _yol("oulad.tables")),
        ("final", "oulad.final_result", _yol("oulad.final_result")),
        ("risk", "oulad.risk_pivot", _yol("oulad.risk_pivot")),
        ("gecmis", "oulad.hist_vs_current", _yol("oulad.hist_vs_current")),
        ("yuva", "oulad.slot_means", _yol("oulad.slot_means")),
        ("sinyaller", "oulad.signals", _yol("oulad.signals")),
        ("ggg", "oulad.data_notes.ggg", _yol("oulad.data_notes.ggg")),
    ),
    "model": (
        ("test", "model.test_metrics", _yol("model.test_metrics")),
        ("esli", "model.paired", _yol("model.paired")),
        ("dogrulama", "model.validation_rows", _yol("model.validation_rows")),
        ("modul_roc", "model.module_roc", _yol("model.module_roc")),
        ("taban", "model.base_rate", _yol("model.base_rate")),
        ("lomo", "model.lomo.rows", _yol("model.lomo.rows")),
        ("shap", "shap.features", _yol("shap.features")),
    ),
    "kural": (
        (None, "rule.periods", _yol("rule.periods")),
        (None, "rule.capture_rule2", _yol("rule.capture_rule2")),
        (None, "rule.gap_rule2", _yol("rule.gap_rule2")),
        (None, "rule.excluded", _yol("rule.excluded")),
        (None, "rule.roc_auc", _yol("rule.roc_auc")),
        (None, "capacity", _yol("capacity")),
    ),
    "ek": (
        (None, "ek.e1.rows", _yol("ek.e1.rows")),
        (None, "ek.e2.rows", _yol("ek.e2.rows")),
        (None, "ek.e3.rows", _yol("ek.e3.rows")),
        (None, "ek.expectations", _beklentiler),
        (None, "ek.recall_by_outcome", _yol("ek.recall_by_outcome")),
        (None, "ek.summary", _yol("ek.summary")),
        (None, "ek.pre_registration", muhur_satirlari),
    ),
    "hoca": (
        (None, "oulad.risk_pivot", _yol("oulad.risk_pivot")),
        (None, "oulad.hist_vs_current", _yol("oulad.hist_vs_current")),
        (None, "model.base_rate", _yol("model.base_rate")),
        (None, "test.module_rates", _yol("test.module_rates")),
    ),
    "sistem": ((None, "oulad.feature_map", _yol("oulad.feature_map")),),
    "hatalar": (
        (None, "uci.absence.buckets", _yol("uci.absence.buckets")),
        (None, "model.validation_rows", _yol("model.validation_rows")),
        (None, "ek.expectations", _beklentiler),
    ),
    "kaynak": (
        (None, "kaynaklar", _yol("kaynaklar")),
        (None, "ek.protocol", _yol("ek.protocol")),
        (None, "oulad.zip_sha256", _yol("oulad.zip_sha256")),
    ),
}


# --- Grafik yerleri: PNG karşılığı olanlar görseli çizer, diğerleri boştur ------------------


def gorsel_satirlari(paket: dict, kimlik: str, lang: str) -> list[dict]:
    """`figures.charts` içinde bu kimliğin bu dildeki satırları (yoksa boş liste)."""
    return [
        satir
        for satir in yol_degeri(paket, "figures.charts")
        if satir["id"] == kimlik and satir["lang"] == lang
    ]


def gorsel_satiri(paket: dict, kimlik: str, lang: str, varyant: str | None = None) -> dict:
    bulunan = [s for s in gorsel_satirlari(paket, kimlik, lang) if s["variant"] == varyant]
    if len(bulunan) != 1:
        raise KeyError(f"figures.charts: {kimlik}/{varyant}/{lang}: {len(bulunan)} satır (1 olmalı)")
    return bulunan[0]


def gorsel_ciz(paket: dict, lang: str, kimlik: str, varyant: str | None = None) -> None:
    """Paketteki görseli çizer: tam genişlik, altında görünür alt yazı (başlık + alt metin).

    Dosya yoksa FileNotFoundError (sessizce bozuk görsel çizilmez). Alt metin yoksa uydurulmaz;
    yerine "alt metin eksik" yazılır.
    """
    satir = gorsel_satiri(paket, kimlik, lang, varyant)
    yol = _ASSET_KOKU / satir["path"]
    if not yol.is_file():
        raise FileNotFoundError(yol)
    alt = satir["alt"] or ARAYUZ[lang]["alt_eksik"]
    st.image(
        str(yol),
        caption=f"**{satir['title']}.** {alt}",
        width="stretch",
        alt=satir["title"],
    )


def grafik_z1(paket: dict, lang: str) -> None:
    """Z1: araştırma yolculuğu (statik zaman çizelgesi)."""


def grafik_d1(paket: dict, lang: str) -> None:
    """D1: OULAD tabloları (yatay çubuk, log ölçek)."""


def grafik_d2(paket: dict, lang: str) -> None:
    """D2: örneklem hunisi."""


def grafik_d3(paket: dict, lang: str) -> None:
    """D3: final sonuçları (yığılmış çubuk)."""


def grafik_d4(paket: dict, lang: str) -> None:
    """D4: bölme zaman çizelgesi."""


def grafik_u1(paket: dict, lang: str) -> None:
    """U1: derse göre geçme oranı (notebook 01 görseli)."""
    gorsel_ciz(paket, lang, "U1")


def grafik_u2(paket: dict, lang: str) -> None:
    """U2: final notu dağılımı (notebook 01 görseli)."""
    gorsel_ciz(paket, lang, "U2")


def grafik_u3(paket: dict, lang: str) -> None:
    """U3: en güçlü on ilişki (notebook 01 görseli)."""
    gorsel_ciz(paket, lang, "U3")


def grafik_u4(paket: dict, lang: str) -> None:
    """U4: korelasyon ısı haritası (notebook 01 görseli)."""
    gorsel_ciz(paket, lang, "U4")


def grafik_u5(paket: dict, lang: str) -> None:
    """U5: sızıntı saçılımı G1 → G3 ve G2 → G3 (notebook 01 görseli)."""
    gorsel_ciz(paket, lang, "U5")


def grafik_u6(paket: dict, lang: str) -> None:
    """U6: devamsızlık, dahil ve hariç (notebook 01 görseli)."""
    gorsel_ciz(paket, lang, "U6")


def grafik_o1(paket: dict, lang: str) -> None:
    """O1: modül × dönem risk ısı haritası (notebook 02 görseli)."""
    gorsel_ciz(paket, lang, "O1")


def grafik_o2(paket: dict, lang: str) -> None:
    """O2: geçmiş oran ve bu dönemin oranı (notebook 02 görseli)."""
    gorsel_ciz(paket, lang, "O2")


def grafik_o3(paket: dict, lang: str) -> None:
    """O3: aynı ödevin dönemler arası ortalaması (notebook 02 görseli)."""
    gorsel_ciz(paket, lang, "O3")


def grafik_o4(paket: dict, lang: str) -> None:
    """O4: erken sinyaller; sinyal seçicisi dört notebook 02 görselinden birini seçer."""
    secenekler = METIN[lang]["oulad_o4_secenekler"]
    if len(secenekler) != len(_O4_SINYALLER):
        raise ValueError("oulad_o4_secenekler sayısı sinyal sayısıyla ayrışıyor")
    secilen = st.radio(
        ARAYUZ[lang]["sinyal"], secenekler, horizontal=True, key=f"ar_o4_sinyal_{lang}"
    )
    gorsel_ciz(paket, lang, "O4", _O4_SINYALLER[secenekler.index(secilen)])


def grafik_m1(paket: dict, lang: str) -> None:
    """M1: protokol şeması."""


def grafik_m2(paket: dict, lang: str) -> None:
    """M2: metrik matrisi."""


def grafik_m3(paket: dict, lang: str) -> None:
    """M3: eşli farklar (forest grafiği)."""


def grafik_m4(paket: dict, lang: str) -> None:
    """M4: doğrulama → test eğim grafiği (week10 fig01)."""
    gorsel_ciz(paket, lang, "M4")


def grafik_m5(paket: dict, lang: str) -> None:
    """M5: modül bazında sıralama."""


def grafik_m6(paket: dict, lang: str) -> None:
    """M6: taban oran ve kayma (week10 fig02)."""
    gorsel_ciz(paket, lang, "M6")


def grafik_m7(paket: dict, lang: str) -> None:
    """M7: geçmiş oran neden yanılttı?"""


def grafik_m8(paket: dict, lang: str) -> None:
    """M8: görülmemiş ders (week10 fig03)."""
    gorsel_ciz(paket, lang, "M8")


def grafik_m9(paket: dict, lang: str) -> None:
    """M9: SHAP (week10 fig05)."""
    gorsel_ciz(paket, lang, "M9")


def grafik_k1(paket: dict, lang: str) -> None:
    """K1: bayrak oranına göre kesinlik (week10 fig04; kaydırıcı sonraki aşamada)."""
    gorsel_ciz(paket, lang, "K1")


def grafik_r1(paket: dict, lang: str) -> None:
    """R1: sinyal kesinliği, kural ve model (week11 fig01)."""
    gorsel_ciz(paket, lang, "R1")


def grafik_r2(paket: dict, lang: str) -> None:
    """R2: kural ile modelin modül bazında sıralaması."""


def grafik_p1(paket: dict, lang: str) -> None:
    """P1: koşmadan önce yazılan beklentiler (week11 fig07a); altında açılır "Sonuçlar" bölümünde
    sonuçlar (week11 fig07). "Sonuçları göster" düğmeli açılış S5'te gelecek."""
    gorsel_ciz(paket, lang, "P1", "once")
    with st.expander(ARAYUZ[lang]["sonuclar"]):
        gorsel_ciz(paket, lang, "P1", "sonuc")


def grafik_x1(paket: dict, lang: str) -> None:
    """X1: hedef panoları (week11 fig03)."""
    gorsel_ciz(paket, lang, "X1")


def grafik_x2(paket: dict, lang: str) -> None:
    """X2: kuralın yakaladığı başarısız ve bırakan oranı (week11 fig04)."""
    gorsel_ciz(paket, lang, "X2")


def grafik_x3(paket: dict, lang: str) -> None:
    """X3: sinyal grupları × ROC AUC (week11 fig02)."""
    gorsel_ciz(paket, lang, "X3")


def grafik_x4(paket: dict, lang: str) -> None:
    """X4: kesim gününe göre ROC AUC (week11 fig05)."""
    gorsel_ciz(paket, lang, "X4")


def grafik_x5(paket: dict, lang: str) -> None:
    """X5: kesim gününe göre KALDI ve BIRAKTI (week11 fig06)."""
    gorsel_ciz(paket, lang, "X5")


def grafik_h1(paket: dict, lang: str) -> None:
    """H1: neyi ayırabildik? (katmanlı şema)."""


# Sayfa grafiklere bu sözlükten ulaşır (testte yerine konabilir).
GRAFIKLER: dict[str, Callable[[dict, str], None]] = {
    "Z1": grafik_z1,
    "D1": grafik_d1,
    "D2": grafik_d2,
    "D3": grafik_d3,
    "D4": grafik_d4,
    "U1": grafik_u1,
    "U2": grafik_u2,
    "U3": grafik_u3,
    "U4": grafik_u4,
    "U5": grafik_u5,
    "U6": grafik_u6,
    "O1": grafik_o1,
    "O2": grafik_o2,
    "O3": grafik_o3,
    "O4": grafik_o4,
    "M1": grafik_m1,
    "M2": grafik_m2,
    "M3": grafik_m3,
    "M4": grafik_m4,
    "M5": grafik_m5,
    "M6": grafik_m6,
    "M7": grafik_m7,
    "M8": grafik_m8,
    "M9": grafik_m9,
    "K1": grafik_k1,
    "R1": grafik_r1,
    "R2": grafik_r2,
    "P1": grafik_p1,
    "X1": grafik_x1,
    "X2": grafik_x2,
    "X3": grafik_x3,
    "X4": grafik_x4,
    "X5": grafik_x5,
    "H1": grafik_h1,
}


# --- Çizim yardımcıları ---------------------------------------------------------------


@functools.lru_cache(maxsize=1)
def _logo_url() -> str:
    kod = base64.b64encode(_LOGO.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{kod}"


def _girise_don() -> None:
    """Adres çubuğundan `sayfa` ve `bolum` parametrelerini kaldırır; oturum ve dil kalır."""
    for ad in ("sayfa", "bolum"):
        if ad in st.query_params:
            del st.query_params[ad]
    st.rerun()


def _ust_serit(lang: str, dil_sec: Callable[..., None]) -> None:
    with st.container(
        horizontal=True, vertical_alignment="center", gap="small", key="ar_ust"
    ):
        with st.container(
            horizontal=True, vertical_alignment="center", gap="small", key="ar_ust_sol"
        ):
            st.markdown(
                f'<img class="logo-img" alt="" width="32" draggable="false" src="{_logo_url()}">',
                unsafe_allow_html=True,
            )
            if st.button(get_text(lang, "brand_short"), key="ar_marka"):
                _girise_don()
        with st.container(
            horizontal=True, vertical_alignment="center", gap="small", key="ar_ust_sag"
        ):
            dil_sec(lang, genis=84)
            if st.button(get_text(lang, "back_to_signin"), key="ar_geri"):
                _girise_don()


def _tablo(ust: tuple, satirlar: tuple, gri: frozenset = frozenset()) -> None:
    """Statik tablo; hücre metni `gri` kümesindeyse gri çizilir (yazısı yine görünür)."""
    baslik = "".join(f"<th>{html.escape(hucre)}</th>" for hucre in ust)

    def hucre_html(hucre: str) -> str:
        sinif = ' class="ar-gri"' if hucre in gri else ""
        return f"<td{sinif}>{html.escape(hucre)}</td>"

    govde = "".join(
        "<tr>" + "".join(hucre_html(hucre) for hucre in satir) + "</tr>" for satir in satirlar
    )
    st.markdown(
        '<div class="ar-tablo"><table>'
        f"<thead><tr>{baslik}</tr></thead><tbody>{govde}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def _ozet_karti(sira: int, deger: str, aciklama: str) -> None:
    with st.container(key=f"ar_ozet_{sira}"):
        st.markdown(
            f'<p class="ar-ozet-deger">{html.escape(deger)}</p>'
            f'<p class="ar-ozet-metin">{html.escape(aciklama)}</p>',
            unsafe_allow_html=True,
        )


def _veri_karti(sira: int, baslik: str, govde: str) -> None:
    with st.container(key=f"ar_veri_{sira}"):
        st.markdown(f"**{baslik}** · {govde}")


# --- Sekme durumu ---------------------------------------------------------------------


def _sekme_anahtari(dil: str) -> str:
    """Sekme bileşeninin anahtarı dile bağlıdır: etiketler dile göre değişir."""
    return f"ar_sekme_{dil}"


def _kimlik(dil: str, etiket: str) -> str:
    for kimlik, ad in METIN[dil]["sekmeler"].items():
        if ad == etiket:
            return kimlik
    raise KeyError(etiket)


def _sekme_degisti(dil: str) -> None:
    """Kullanıcı sekme değiştirince seçili kimliği adres çubuğuna yazar."""
    st.query_params["bolum"] = _kimlik(dil, st.session_state[_sekme_anahtari(dil)])


def _sekmeye_git(dil: str, kimlik: str) -> None:
    st.session_state[_sekme_anahtari(dil)] = METIN[dil]["sekmeler"][kimlik]
    st.query_params["bolum"] = kimlik


@dataclass(frozen=True)
class _B:
    """Bir bölümün çizim bağlamı: dil, paket (turev dahil), metinler, arayüz etiketleri."""

    dil: str
    paket: dict
    t: dict
    a: dict

    def var(self, anahtar: str) -> bool:
        """Blok bu dilde var mı? (EKSIK_EN bloklar İngilizce sözlükte yoktur.)"""
        return anahtar in self.t

    def coz(self, metin: str) -> str:
        return coz(metin, self.paket, self.dil)

    def m(self, anahtar: str) -> str:
        return self.coz(self.t[anahtar])

    def yaz(self, anahtar: str) -> None:
        if self.var(anahtar):
            st.markdown(self.m(anahtar))

    def baslik(self, grup: str, anahtar: str) -> None:
        if self.var(grup):
            st.markdown(f"#### {self.t[grup][anahtar]}")

    def atif_basligi(self, grafik: str) -> str | None:
        """Grafiğin atıf başlığı (figures.json ya da notebook başlığı); görseli yoksa None."""
        satirlar = gorsel_satirlari(self.paket, grafik, self.dil)
        basliklar = {satir["cite_title"] for satir in satirlar}
        if len(basliklar) > 1:
            raise ValueError(f"{grafik}: birden çok atıf başlığı {sorted(basliklar)}")
        return basliklar.pop() if basliklar else None

    def atif(self, grafik: str | None) -> str | None:
        """Kutunun başına eklenen kısa atıf (TR "Grafik: <başlık>", EN "Chart: <title>").

        Grafiğin görseli yoksa başlık da yoktur; atıf uydurulmaz, None döner.
        """
        if grafik is None:
            return None
        baslik = self.atif_basligi(grafik)
        return None if baslik is None else f"*{self.a['atif_grafik']}: {baslik}*"

    def kutu(
        self, tur: str, anahtar: str, etiket: str | None = None, grafik: str | None = None
    ) -> None:
        """Kutu: `bolum` (nötr), `bulgu` (kırmızı sol kenar), `hata` (sarı sol kenar).

        `grafik`: kutunun dayandığı grafik kimliği; görseli varsa metnin başına atıf konur.
        """
        if not self.var(anahtar):
            return
        govde = self.m(anahtar)
        atif = self.atif(grafik)
        if atif is not None:
            govde = f"{atif}\n\n{govde}"
        if etiket is not None:
            govde = f"**{self.a[etiket]}.** {govde}"
        with st.container(key=f"ar_kutu_{tur}_{anahtar}"):
            st.markdown(govde)

    def grafik(self, kimlik: str) -> None:
        GRAFIKLER[kimlik](self.paket, self.dil)

    def tablo(self, anahtar: str, ust: tuple | None = None) -> None:
        """Statik tablo bloğu ({"ust", "satirlar"}); hücrelerdeki alanlar çözülür."""
        if not self.var(anahtar):
            return
        blok = self.t[anahtar]
        satirlar = tuple(tuple(self.coz(hucre) for hucre in satir) for satir in blok["satirlar"])
        _tablo(ust if ust is not None else blok["ust"], satirlar)

    def git_dugmesi(self, hedef: str, anahtar: str) -> None:
        """Başka sekmeye geçiren düğme; etiketi hedef sekmenin adıdır."""
        st.button(
            self.t["sekmeler"][hedef],
            key=f"ar_git_{anahtar}",
            on_click=_sekmeye_git,
            args=(self.dil, hedef),
        )


def _ham(b: _B, bolum: str) -> None:
    """Bölüm sonu "Ham tablolar": paket verisinden `st.dataframe` ve CSV indir düğmesi."""
    basliklar = b.t.get(f"ham_{bolum}", {})
    with st.expander(b.a["ham_tablolar"]):
        for sira, (kisa, yol, yukle) in enumerate(HAM[bolum]):
            satirlar = yukle(b.paket)
            baslik = basliklar.get(kisa) if kisa else None
            if baslik:
                st.markdown(f"**{baslik}**")
                st.caption(yol)
            else:
                st.markdown(f"`{yol}`")
            st.dataframe(satirlar, hide_index=True, width="stretch")
            st.download_button(
                b.a["csv_indir"],
                data=csv_metni(satirlar),
                file_name=f"{yol}.csv",
                mime="text/csv",
                key=f"ar_csv_{bolum}_{sira}",
                on_click="ignore",
            )


# --- Bölümler -------------------------------------------------------------------------


def _bolum_ozet(b: _B) -> None:
    t = b.t
    # v1 4.0 Hero
    st.markdown(
        f'<h1 class="ar-baslik">{html.escape(b.m("hero_baslik"))}</h1>'
        f'<p class="ar-alt">{html.escape(b.m("hero_alt"))}</p>',
        unsafe_allow_html=True,
    )
    if b.var("okuma_suresi"):
        st.markdown(
            f'<p class="ar-etiket">{html.escape(b.m("okuma_suresi"))}</p>',
            unsafe_allow_html=True,
        )
    b.kutu("bolum", "ozet_bu_bolumde", "bu_bolumde")
    for sira, kolon in enumerate(st.columns(3, gap="small"), start=1):
        with kolon:
            _ozet_karti(sira, b.m(f"ozet{sira}_deger"), b.m(f"ozet{sira}_aciklama"))
    st.markdown(
        f'<div class="ar-uyari" role="note">{html.escape(b.m("uyari"))}</div>',
        unsafe_allow_html=True,
    )

    # v1 4.1 Soru
    st.divider()
    st.markdown(b.m("soru"))

    # v1 4.2 İki veri seti
    st.divider()
    sol, sag = st.columns(2, gap="small")
    with sol:
        _veri_karti(1, t["veri1_baslik"], b.m("veri1"))
    with sag:
        _veri_karti(2, t["veri2_baslik"], b.m("veri2"))
    st.markdown(b.m("veri_alt"))

    # Spec v2, 3: cevapladıklarımız / cevaplayamadıklarımız
    st.divider()
    sol, sag = st.columns(2, gap="small")
    for kolon, kisa, kap in (
        (sol, "ozet_gosterebildik", "ar_liste_gosterilen"),
        (sag, "ozet_gosteremedik", "ar_liste_gosterilemeyen"),
    ):
        with kolon, st.container(key=kap):
            st.markdown(f"**{t[kisa + '_baslik']}**")
            st.markdown("\n".join(f"- {b.coz(madde)}" for madde in t[kisa]))
    b.grafik("Z1")
    _ham(b, "ozet")


def _bolum_veri(b: _B) -> None:
    b.kutu("bolum", "veri_bu_bolumde", "bu_bolumde")
    if b.var("veri_d0"):
        st.markdown(f"**{b.t['veri_d0_baslik']}**")
        b.tablo("veri_d0")
    b.yaz("veri_sosyokultur")
    b.grafik("D1")
    b.grafik("D2")
    b.grafik("D3")
    b.yaz("oulad_duzen")  # v1 4.4
    b.grafik("D4")
    _ham(b, "veri")


def _bolum_uci(b: _B) -> None:
    b.kutu("bolum", "uci_bu_bolumde", "bu_bolumde")
    b.yaz("uci_bulgu")  # v1 4.3
    b.grafik("U1")
    b.grafik("U2")
    b.kutu("bulgu", "uci_u2_bulgu", "bulgu", grafik="U2")
    b.grafik("U3")
    b.grafik("U4")
    b.grafik("U5")
    b.kutu("bulgu", "uci_u5_bulgu", "bulgu", grafik="U5")
    b.grafik("U6")
    with st.container(key="ar_kutu_hata_uci_hata"):
        atif = b.atif("U6")
        st.markdown(b.m("uci_hata") if atif is None else f"{atif}\n\n{b.m('uci_hata')}")
        if b.var("uci_hata_baglanti"):
            st.markdown(b.m("uci_hata_baglanti"))
        b.git_dugmesi("hatalar", "uci_hata")
    # U7: özellik setleri (paket: uci.feature_sets)
    if b.var("uci_u7_baslik"):
        st.markdown(f"**{b.t['uci_u7_baslik']}**")
    kumeler = yol_degeri(b.paket, "uci.feature_sets")
    _tablo(
        ("EARLY", "MIDTERM"),
        tuple(
            (erken or "", ortak or "")
            for erken, ortak in zip_longest(kumeler["early"], kumeler["midterm"])
        ),
    )
    b.yaz("uci_kapanis")  # v1 4.3
    b.yaz("uci_bolum_sonu")
    _ham(b, "uci")


def _bolum_oulad(b: _B) -> None:
    b.kutu("bolum", "oulad_bu_bolumde", "bu_bolumde")
    b.grafik("O1")
    b.kutu("bulgu", "oulad_o1_bulgu", "bulgu", grafik="O1")
    b.grafik("O2")
    b.grafik("O3")
    b.grafik("O4")
    b.kutu("bulgu", "oulad_o4_bulgu", "bulgu", grafik="O4")
    if b.var("oulad_o5"):
        st.markdown(f"**{b.t['oulad_o5']['baslik']}**")
        eslesme = yol_degeri(b.paket, "oulad.feature_map")
        alan = f"school_{b.dil}"
        _tablo(
            b.t["oulad_o5"]["ust"],
            tuple((s[alan], s["feature"]) for s in eslesme),
        )
    _ham(b, "oulad")


def _bolum_model(b: _B) -> None:
    t = b.t
    b.kutu("bolum", "model_bu_bolumde", "bu_bolumde")
    b.yaz("b45_giris")  # v1 4.5
    ust_sol, ust_sag = st.columns(2, gap="small")
    alt_sol, alt_sag = st.columns(2, gap="small")
    for kolon, anahtar in (
        (ust_sol, "kart_ders"),
        (ust_sag, "kart_zaman"),
        (alt_sol, "kart_sira"),
        (alt_sag, "kart_hoca"),
    ):
        with kolon, st.container(key=f"ar_{anahtar}"):
            st.markdown(b.m(anahtar))
    # M0
    if b.var("model_m0_baslik"):
        st.markdown(f"**{t['model_m0_baslik']}**")
    b.tablo("model_m0", ust=b.a["m0_ust"])
    for not_metni in t["model_m0"]["notlar"]:
        st.markdown(not_metni)
    b.grafik("M1")
    b.grafik("M2")
    b.grafik("M3")
    b.kutu("bulgu", "model_m3_bulgu", "bulgu", grafik="M3")
    b.grafik("M4")
    b.grafik("M5")
    b.kutu("bulgu", "model_m5_bulgu", "bulgu", grafik="M5")
    b.grafik("M6")
    b.grafik("M7")
    b.kutu("bulgu", "model_m7_bulgu", "bulgu", grafik="M7")
    b.yaz("b47")  # v1 4.7
    b.grafik("M8")
    b.yaz("b48")  # v1 4.8
    b.grafik("M9")
    # Dürüstlük kutusu: v1 4.6 metni ve tablosu
    with st.container(key="ar_kutu_hata_durustluk"):
        st.markdown(b.m("b46_metin"))
        if "tablo_46" in t:
            st.markdown(f"**{t['tablo_46_baslik']}**")
            _tablo(t["tablo_46"]["ust"], t["tablo_46"]["satirlar"])
        st.markdown(b.m("b46_kapanis"))
        b.git_dugmesi("hatalar", "durustluk")
    _ham(b, "model")


def _bolum_kural(b: _B) -> None:
    b.kutu("bolum", "kural_bu_bolumde", "bu_bolumde")
    b.yaz("b49_giris")  # v1 4.9
    b.grafik("K1")
    b.yaz("b49_secim")
    b.yaz("b410")  # v1 4.10
    b.grafik("R1")
    b.grafik("R2")
    b.kutu("bulgu", "kural_r2_bulgu", "bulgu", grafik="R2")
    _ham(b, "kural")


def _bolum_ek(b: _B) -> None:
    b.kutu("bolum", "ek_bu_bolumde", "bu_bolumde")
    # 2.1 Düşünce haritası
    b.baslik("ek_basliklar", "harita")
    if b.var("ek_harita"):
        harita = b.t["ek_harita"]
        sol, sag = st.columns([3, 2], gap="small")
        with sol:
            for sira, (durak, bulduk, eksik) in enumerate(harita["duraklar"], start=1):
                if sira > 1:
                    st.markdown('<p class="ar-ok" aria-hidden="true">↓</p>', unsafe_allow_html=True)
                with st.container(key=f"ar_harita_{sira}"):
                    st.markdown(
                        f"**{durak}**\n\n**{harita['bulduk']}:** {bulduk}\n\n"
                        f"**{harita['eksik']}:** {eksik}"
                    )
        with sag:
            for sira, (kisa, soru) in enumerate(b.t["ek_sorular"], start=1):
                with st.container(key=f"ar_soru_{sira}"):
                    st.markdown(f"**{kisa}**\n\n{soru}")
    if b.var("ek_suphe"):
        with st.container(key="ar_vurgu_suphe"):
            st.markdown(b.m("ek_suphe"))
    # 2.2 Ön kayıt
    b.baslik("ek_basliklar", "onkayit")
    b.yaz("ek_onkayit")
    b.grafik("P1")
    if b.var("ek_muhur"):
        muhur = b.t["ek_muhur"]
        with st.expander(muhur["baslik"]):
            _tablo(
                muhur["ust"],
                tuple(
                    (s["dosya"], s["md5"], s["zaman"]) for s in muhur_satirlari(b.paket)
                ),
            )
            st.markdown(muhur["not"])
    # 2.3 Şüphe çürüyor (E2)
    b.baslik("ek_basliklar", "e2")
    b.yaz("ek_e2_metin")
    b.grafik("X1")
    b.grafik("X2")
    b.kutu("bulgu", "ek_e2_bulgu", "bulgu")
    # 2.4 Bilgi nerede? (E1)
    b.baslik("ek_basliklar", "e1")
    b.yaz("ek_e1_metin")
    b.grafik("X3")
    b.kutu("bulgu", "ek_e1_bulgu", "bulgu", grafik="X3")
    # 2.5 Ne kadar erken? (E3)
    b.baslik("ek_basliklar", "e3")
    b.yaz("ek_e3_metin")
    b.kutu("hata", "ek_e3_karar")
    b.grafik("X4")
    b.grafik("X5")
    b.kutu("bulgu", "ek_e3_bulgu", "bulgu")
    # 2.6 Başkaları ne buldu? (E4)
    b.baslik("ek_basliklar", "e4")
    b.yaz("ek_e4_metin")
    if b.var("ek_l1"):
        l1 = b.t["ek_l1"]
        st.markdown(f"**{l1['baslik']}**")
        # Bu çalışmanın satırındaki ve Gözlem 2'deki değerler yer tutucudur; hücreler çözülür.
        _tablo(
            l1["ust"],
            tuple(tuple(b.coz(hucre) for hucre in satir) for satir in l1["satirlar"]),
            gri=frozenset({l1["gri"]}),
        )
        for gozlem in l1["gozlemler"]:
            st.markdown(b.coz(gozlem))
        st.markdown("\n".join(f"- {b.coz(kaynak)}" for kaynak in l1["kaynakca"]))
    # 2.7 Kapanış
    b.baslik("ek_basliklar", "kapanis")
    if b.var("ek_kapanis"):
        sol, sag = st.columns(2, gap="small")
        with sol, st.container(key="ar_liste_degisti"):
            st.markdown(b.t["ek_kapanis"]["degisti"])
        with sag, st.container(key="ar_liste_degismedi"):
            st.markdown(b.t["ek_kapanis"]["degismedi"])
    _ham(b, "ek")


def _bolum_hoca(b: _B) -> None:
    b.kutu("bolum", "hoca_bu_bolumde", "bu_bolumde")
    b.baslik("hoca_basliklar", "h10_1")
    b.yaz("hoca_10_1")
    b.grafik("H1")
    b.baslik("hoca_basliklar", "h10_2")
    b.yaz("hoca_10_2")
    if b.var("hoca_h2"):
        st.markdown(f"**{b.t['hoca_h2']['baslik']}**")
        b.tablo("hoca_h2")
    b.baslik("hoca_basliklar", "h10_3")
    b.yaz("hoca_10_3")
    b.kutu("bulgu", "hoca_bulgu", "bulgu")
    _ham(b, "hoca")


def _bolum_sistem(b: _B) -> None:
    b.kutu("bolum", "sistem_bu_bolumde", "bu_bolumde")
    if b.var("tablo_11"):
        b.tablo("tablo_11")
    b.yaz("b411")  # v1 4.11
    b.yaz("sistem_kopru")
    _ham(b, "sistem")


def _bolum_hatalar(b: _B) -> None:
    b.kutu("bolum", "hatalar_bu_bolumde", "bu_bolumde")
    turler = b.t.get("hata_tur")
    notlar = b.t.get("hata_bag_not", {})
    govde = b.t["hata_govde"]
    for sira, baslik in enumerate(b.t["hata_basliklar"], start=1):
        with st.container(key=f"ar_hata_{sira}"):
            st.markdown(f"**{sira}. {baslik}**")
            if turler:
                st.markdown(
                    f'<span class="ar-etiket">{html.escape(turler[sira - 1])}</span>',
                    unsafe_allow_html=True,
                )
            # 12 kartın her biri dört alanıyla çizilir; eksik kart ya da alan KeyError verir.
            alanlar = govde[str(sira)]
            for alan in ("belirti", "kok", "duzeltme", "sonra"):
                st.markdown(f"**{b.a[alan]}:** {b.coz(alanlar[alan])}")
            baglanti = HATA_BAGLANTI.get(sira, ())
            if baglanti:
                satir = f"**{b.a['gorsel']}:** {', '.join(baglanti)}"
                if str(sira) in notlar:
                    satir += f" ({notlar[str(sira)]})"
                st.markdown(satir)
    _ham(b, "hatalar")


def _bolum_kaynak(b: _B) -> None:
    t = b.t
    b.kutu("bolum", "kaynak_bu_bolumde", "bu_bolumde")
    if "sinirlar" in t:  # v1 4.12
        st.markdown(
            f'<div class="ar-sutun">{html.escape(b.m("sinirlar"))}</div>',
            unsafe_allow_html=True,
        )
    st.divider()
    if "yeniden_uretim" in t:  # v1 4.13
        st.markdown(b.m("yeniden_uretim"))
    st.code(KOD_BLOGU, language="bash")
    if b.var("kaynak_kaynakca"):
        st.markdown("\n".join(f"- {kaynak}" for kaynak in t["kaynak_kaynakca"]))
    if b.var("kaynak_yazar"):
        st.markdown(b.m("kaynak_yazar"))
    _ham(b, "kaynak")


_BOLUMLER: dict[str, Callable[[_B], None]] = {
    "ozet": _bolum_ozet,
    "veri": _bolum_veri,
    "uci": _bolum_uci,
    "oulad": _bolum_oulad,
    "model": _bolum_model,
    "kural": _bolum_kural,
    "ek": _bolum_ek,
    "hoca": _bolum_hoca,
    "sistem": _bolum_sistem,
    "hatalar": _bolum_hatalar,
    "kaynak": _bolum_kaynak,
}


# --- Sayfa ---------------------------------------------------------------------------


def sayfa(lang: str, dil_sec: Callable[..., None]) -> None:
    """Araştırma sayfasını çizer: üst şerit + 11 sekme. api_client'a dokunmaz.

    Seçili sekme `&bolum=<kimlik>` olarak adres çubuğuna yazılır. Geçersiz ya da eksik kimlik
    Özet'e düşer. Yalnızca açık sekmenin içeriği çizilir.
    """
    dil = lang if lang in METIN else "tr"
    paket = tam_paket()
    t = METIN[dil]
    b = _B(dil=dil, paket=paket, t=t, a=ARAYUZ[dil])
    sekmeler = t["sekmeler"]
    etiketler = [sekmeler[kimlik] for kimlik in SEKME_SIRA]
    anahtar = _sekme_anahtari(dil)

    with st.container(key="arastirma"):
        _ust_serit(dil, dil_sec)

        if st.session_state.get(anahtar) not in etiketler:
            istenen = st.query_params.get("bolum")
            st.session_state[anahtar] = sekmeler[istenen if istenen in sekmeler else "ozet"]
        secili = _kimlik(dil, st.session_state[anahtar])
        if st.query_params.get("bolum") != secili:
            st.query_params["bolum"] = secili

        kaplar = st.tabs(etiketler, key=anahtar, on_change=_sekme_degisti, args=(dil,))
        for kimlik, kap in zip(SEKME_SIRA, kaplar, strict=True):
            if kap.open is False:
                continue
            with kap:
                _BOLUMLER[kimlik](b)

        # Sayfa sonu: yeniden üretim satırı ve Sınırlar ve kaynaklar'a bağlantı
        if b.var("sayfa_sonu"):
            st.divider()
            st.markdown(b.m("sayfa_sonu"))
            b.git_dugmesi("kaynak", "sayfa_sonu")
