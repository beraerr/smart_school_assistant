"""Herkese açık haftalık sunum sayfası (`?sayfa=haftalik`).

Girişsizdir; okul verisine ve backend'e dokunmaz. Girdi yalnızca
`assets/haftalik/haftalik.json` (scripts/haftalik_slaytlar.py üretir) ve onun gösterdiği dosyalardır.
Seçili dilde sürüm yoksa açık bir mesaj gösterilir; diğer dile geri dönülmez.
"""

import json
import os
from collections.abc import Callable
from pathlib import Path

import streamlit as st

from i18n import get_text

_KOK = Path(__file__).resolve().parent
_VARSAYILAN_DIZIN = _KOK / "assets" / "haftalik"
_DIZIN_ORTAM = "HAFTALIK_DIZIN"
_DILLER = ("tr", "en")


def _kok() -> Path:
    """Sunum kök dizini; her çağrıda okunur. HAFTALIK_DIZIN tanımlıysa o, yoksa assets/haftalik.

    Kök yalnızca burada belirlenir; böylece betiğin yeniden çalışması kökü değiştirmez.
    """
    ayar = os.environ.get(_DIZIN_ORTAM)
    if ayar is None:
        return _VARSAYILAN_DIZIN
    if not ayar:
        raise ValueError(f"{_DIZIN_ORTAM} boş olamaz")
    return Path(ayar)


def manifesti_oku() -> list[dict]:
    """Haftaları döndürür. Dosya yoksa boş liste (henüz sunum yok); bozuk dosyada hata yükselir."""
    yol = _kok() / "haftalik.json"
    if not yol.is_file():
        return []
    govde = json.loads(yol.read_text(encoding="utf-8"))
    haftalar = govde["haftalar"]
    if not isinstance(haftalar, list):
        raise ValueError("haftalik.json: 'haftalar' liste olmalı")
    for hafta in haftalar:
        if not isinstance(hafta["hafta"], int) or not isinstance(hafta["diller"], dict):
            raise ValueError(f"haftalik.json: geçersiz hafta kaydı: {hafta!r}")
        if not set(hafta["diller"]) <= set(_DILLER):
            raise ValueError(f"haftalik.json: bilinmeyen dil: {sorted(hafta['diller'])}")
    return haftalar


def _geri_don() -> None:
    if "sayfa" in st.query_params:
        del st.query_params["sayfa"]
    st.rerun()


def _ust_serit(lang: str, dil_sec: Callable[..., None]) -> None:
    with st.container(horizontal=True, vertical_alignment="center", gap="small", key="hf_ust"):
        st.markdown(f"### {get_text(lang, 'weekly_title')}")
        with st.container(horizontal=True, vertical_alignment="center", gap="small", key="hf_ust_sag"):
            dil_sec(lang)
            if st.button(get_text(lang, "back_to_signin"), key="hf_geri"):
                _geri_don()


def _sunumu_ciz(lang: str, hafta: dict) -> None:
    sunum = hafta["diller"].get(lang)
    if sunum is None:
        st.info(get_text(lang, "weekly_missing"))
        return
    kok = _kok()
    pdf = kok / sunum["pdf"]
    st.download_button(
        get_text(lang, "weekly_pdf"),
        data=pdf.read_bytes(),
        file_name=f"hafta{hafta['hafta']:02d}_{lang}.pdf",
        mime="application/pdf",
        key="hf_pdf",
        icon=":material/download:",
    )
    slaytlar = sunum["slaytlar"]
    for sira, slayt in enumerate(slaytlar, start=1):
        st.image(
            str(kok / slayt),
            caption=get_text(lang, "weekly_slide").format(n=sira, total=len(slaytlar)),
            width="stretch",
        )


def haftalik_sayfa(lang: str, dil_sec: Callable[..., None]) -> None:
    """Haftalık sunum sayfasını çizer. api_client'a dokunmaz."""
    dil = lang if lang in _DILLER else "tr"
    # Küçükten büyüğe; varsayılan hafta listenin ilki, yani en küçük haftadır.
    haftalar = sorted(manifesti_oku(), key=lambda hafta: hafta["hafta"])
    with st.container(key="haftalik"):
        _ust_serit(dil, dil_sec)
        if not haftalar:
            st.info(get_text(dil, "weekly_empty"))
            return
        numaralar = [hafta["hafta"] for hafta in haftalar]
        secilen = st.pills(
            get_text(dil, "weekly_select"),
            options=numaralar,
            selection_mode="single",
            default=numaralar[0],
            required=True,
            format_func=lambda n: get_text(dil, "weekly_week").format(n=n),
            key="hf_hafta",
        )
        hafta = next(hafta for hafta in haftalar if hafta["hafta"] == secilen)
        _sunumu_ciz(dil, hafta)
