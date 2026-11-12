"""Giriş ve sohbet ekranı."""

import base64
import functools
import html
import logging
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import api_client
import arastirma
from i18n import get_text
from view import (
    has_duplicate_grades,
    pivot_grades,
    risk_filtre,
    risk_kart_html,
    risk_kartlari,
    risk_siniflari,
    risk_stili,
    risk_tablosu,
)

_KOK = Path(__file__).resolve().parent
_ASSETS = _KOK / "assets"
_LOGO_YAZI = _ASSETS / "logo_wordmark.svg"
_LOGO_BEYAZ = _ASSETS / "logo_white.svg"
_AVATAR = _ASSETS / "avatar.svg"
_TURKSAT = _ASSETS / "turksat_logo.png"
_FAVICON = _ASSETS / "favicon.png"
_THEME = _KOK / "theme.css"

_RISK_ROLLERI = frozenset({"principal", "teacher"})
_ROL_ANAHTAR = {
    "principal": "role_principal",
    "teacher": "role_teacher",
    "parent": "role_parent",
    "student": "role_student",
}
_DEMO = (
    ("demo_principal", "role_principal", "principal", "admin123"),
    ("demo_teacher", "role_teacher", "teacher1", "teacher123"),
    ("demo_parent", "role_parent", "parent1", "parent123"),
    ("demo_student", "role_student", "student1", "student123"),
)
_OZELLIKLER = (
    ("smart_toy", "feature_agent_title", "feature_agent_body"),
    ("shield", "feature_security_title", "feature_security_body"),
    ("monitoring", "feature_tested_title", "feature_tested_body"),
)
_GECMIS = 6
_ORNEK_ALAN = frozenset({"question"})
_ornek_kayit = logging.getLogger("frontend.examples")
# Kullanıcıya bağlı, widget olmayan session_state anahtarları (messages ve query_error ayrıca).
_KULLANICI_ANAHTARLARI = ("ornek_sorular", "bekleyen_soru", "menu", "menu_ac")


@functools.lru_cache(maxsize=8)
def _veri_url(yol: str) -> str:
    dosya = Path(yol)
    mime = "image/svg+xml" if dosya.suffix.lower() == ".svg" else "image/png"
    kod = base64.b64encode(dosya.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{kod}"


def _logo_html(yol: Path, alt: str, genislik: int, sinif: str) -> str:
    return (
        f'<img class="logo-img {sinif}" alt="{html.escape(alt)}" '
        f'width="{genislik}" draggable="false" src="{_veri_url(str(yol))}">'
    )

st.set_page_config(
    page_title="Akıllı Okul Bilgi Sistemi",
    page_icon=str(_FAVICON),
    layout="wide",
    initial_sidebar_state="expanded",
)


def _temayi_yukle() -> None:
    css = _THEME.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


_temayi_yukle()

st.session_state.setdefault("token", None)
st.session_state.setdefault("user", None)
st.session_state.setdefault("lang", "tr")
st.session_state.setdefault("messages", [])
st.session_state.setdefault("query_error", None)
st.session_state.setdefault("notice", None)
st.session_state.setdefault("form_error", None)


def _hata_goster(lang: str, sonuc: dict) -> None:
    kod = sonuc.get("status_code")
    if kod == 429:
        sure = sonuc.get("retry_after") or "?"
        st.error(get_text(lang, "error_429").format(seconds=sure))
    elif kod == 503:
        st.error(get_text(lang, "error_503"))
    elif kod == 400:
        st.error(get_text(lang, "error_400"))
    elif isinstance(kod, int) and kod >= 500:
        st.error(get_text(lang, "error_server"))
    elif sonuc.get("kind") == "connection":
        st.error(get_text(lang, "error_connection"))
    else:
        st.error(get_text(lang, "error_server"))


def _dil_sec(lang: str, genis: int = 96) -> None:
    st.selectbox(
        get_text(lang, "language"),
        options=["tr", "en"],
        format_func=lambda kod: "TR" if kod == "tr" else "EN",
        key="lang",
        label_visibility="collapsed",
        width=genis,
    )


def _kullanici_durumunu_sifirla() -> None:
    """Kullanıcıya göre değişen session_state değerlerini siler.

    Çıkışta, 401'de ve başarılı girişte çağrılır; bir sonraki kullanıcı öncekinin
    sohbetini, hatasını, sayfa seçimini ve örnek sorularını görmez.
    Widget anahtarları (pivot_*, risk_sinif) Streamlit tarafından, widget bir
    çalıştırmada çizilmeyince kendiliğinden düşürülür; burada elle silinmez.
    """
    st.session_state.messages = []
    st.session_state.query_error = None
    for anahtar in _KULLANICI_ANAHTARLARI:
        st.session_state.pop(anahtar, None)


def _oturumu_temizle() -> None:
    st.session_state.token = None
    st.session_state.user = None
    st.session_state.form_error = None
    _kullanici_durumunu_sifirla()


def _sql_listesi(data: dict) -> list[str]:
    sql = data.get("sql")
    if isinstance(sql, str):
        sql = [sql]
    if not isinstance(sql, list):
        return []
    return [str(parca) for parca in sql if isinstance(parca, str) and parca.strip()]


def _asistan_icerigi(lang: str, data: dict, sira: int) -> None:
    cevap = data.get("answer")
    if isinstance(cevap, str) and cevap.strip():
        st.markdown(cevap)

    sorgular = _sql_listesi(data)
    results = data.get("results")
    sonuc_var = isinstance(results, list) and bool(results)
    # Dayanak kontrolü cevabı geri çektiyse sonuç tablosu cevabın yerine geçer: bölüm açık gelir.
    # SQL gizliyken (SHOW_SQL kapalı) bölüm yine de tabloyu göstermek için açılır.
    geri_donus = data.get("grounding_fallback") is True
    if sorgular or (geri_donus and sonuc_var):
        with st.expander(get_text(lang, "show_query"), expanded=geri_donus):
            for sorgu in sorgular:
                st.code(sorgu, language="sql")
            if sonuc_var:
                tablo = pd.DataFrame(results)
                if {"name", "subject", "grade"}.issubset(tablo.columns):
                    if st.checkbox(
                        get_text(lang, "columns_by_subject"),
                        key=f"pivot_{sira}",
                    ):
                        if has_duplicate_grades(tablo):
                            st.warning(get_text(lang, "duplicate_grades"))
                        tablo = pivot_grades(tablo)
                st.dataframe(tablo, hide_index=True)

    aciklama = data.get("explanation")
    if isinstance(aciklama, str) and aciklama.strip():
        st.caption(aciklama)


def _mesaji_ciz(lang: str, mesaj: dict, sira: int) -> None:
    avatar = str(_AVATAR) if mesaj["role"] == "assistant" else None
    with st.chat_message(mesaj["role"], avatar=avatar):
        if mesaj["role"] == "assistant" and isinstance(mesaj.get("data"), dict):
            _asistan_icerigi(lang, mesaj["data"], sira)
        else:
            st.markdown(mesaj.get("content") or "")


def _gecmis() -> list[dict]:
    return [
        {"role": mesaj["role"], "content": mesaj.get("content") or ""}
        for mesaj in st.session_state.messages[-_GECMIS:]
    ]


def _demo_doldur(kullanici: str, sifre: str) -> None:
    st.session_state["kullanici_adi"] = kullanici
    st.session_state["sifre"] = sifre


def _demo_dugmeleri(lang: str) -> None:
    for satir in (_DEMO[:2], _DEMO[2:]):
        kolonlar = st.columns(2, gap="small")
        for kolon, (anahtar, rol_anahtar, kullanici, sifre) in zip(kolonlar, satir, strict=True):
            with kolon:
                rol = get_text(lang, rol_anahtar)
                st.button(
                    f"**{rol}**  \n:material/person: {kullanici}  \n:material/key: {sifre}",
                    key=anahtar,
                    width="stretch",
                    on_click=_demo_doldur,
                    args=(kullanici, sifre),
                )


def _marka_paneli(lang: str) -> None:
    with st.container(key="brand_panel"):
        with st.container(key="brand_top"):
            with st.container(horizontal=True, vertical_alignment="center", gap="small"):
                st.markdown(
                    _logo_html(_LOGO_BEYAZ, get_text(lang, "brand_short"), 52, "logo-brand"),
                    unsafe_allow_html=True,
                )
                ad = get_text(lang, "brand_full")
                satirlar = "<br>".join(html.escape(parca) for parca in ad.split(" / "))
                st.markdown(f'<p class="brand-name">{satirlar}</p>', unsafe_allow_html=True)
        with st.container(key="brand_mid"):
            st.markdown(
                f'<h1 class="hero-title">{html.escape(get_text(lang, "login_hero"))}</h1>'
                f'<p class="hero-sub">{html.escape(get_text(lang, "login_sub"))}</p>',
                unsafe_allow_html=True,
            )
            parcalar = []
            for ikon, baslik_anahtar, govde_anahtar in _OZELLIKLER:
                parcalar.append(
                    "<div class='feature'>"
                    f"<span class='feature-icon' translate='no' aria-hidden='true'>{ikon}</span>"
                    "<div class='feature-copy'>"
                    f"<p class='feature-title'>{html.escape(get_text(lang, baslik_anahtar))}</p>"
                    f"<p class='feature-body'>{html.escape(get_text(lang, govde_anahtar))}</p>"
                    "</div></div>"
                )
            st.markdown("".join(parcalar), unsafe_allow_html=True)
            if st.button(get_text(lang, "research_link"), key="arastirma_ac"):
                st.query_params["sayfa"] = "arastirma"
                st.rerun()
        with st.container(key="brand_foot"):
            st.markdown(
                f'<p class="brand-foot">{html.escape(get_text(lang, "login_footer"))}</p>',
                unsafe_allow_html=True,
            )


def _giris_hata(lang: str) -> None:
    if st.session_state.notice == "error_401":
        st.error(get_text(lang, "error_401"))
    elif isinstance(st.session_state.form_error, dict):
        hata = st.session_state.form_error
        if hata.get("status_code") == 401:
            st.error(get_text(lang, "login_error"))
        else:
            _hata_goster(lang, hata)


def _giris_karti(lang: str) -> None:
    with st.container(key="login_card", border=True):
        with st.form("giris", border=False):
            username = st.text_input(get_text(lang, "username"), key="kullanici_adi")
            password = st.text_input(
                get_text(lang, "password"),
                type="password",
                key="sifre",
            )
            gonder = st.form_submit_button(
                get_text(lang, "login_submit"),
                type="primary",
                width="stretch",
            )
        _demo_dugmeleri(lang)
    with st.container(key="login_mark", border=False):
        st.markdown(
            _logo_html(_TURKSAT, "Türksat", 132, "logo-login-mark"),
            unsafe_allow_html=True,
        )

    if not gonder:
        return

    st.session_state.notice = None
    st.session_state.form_error = None
    sonuc = api_client.login(username, password)
    if sonuc["ok"] and isinstance(sonuc.get("data"), dict):
        govde = sonuc["data"]
        token = govde.get("access_token")
        if token:
            _kullanici_durumunu_sifirla()
            st.session_state.token = token
            st.session_state["menu_ac"] = True
            st.session_state.user = govde.get("user")
            st.rerun()
            return
    if sonuc.get("status_code") == 401:
        st.session_state.form_error = sonuc
        st.error(get_text(lang, "login_error"))
        return
    st.session_state.form_error = sonuc
    _hata_goster(lang, sonuc)


def _giris(lang: str) -> None:
    st.markdown('<div class="login-mode"></div>', unsafe_allow_html=True)
    sol, sag = st.columns([1, 1], gap="small", vertical_alignment="top")
    with sol:
        _marka_paneli(lang)
    with sag:
        with st.container(key="login_pane"):
            with st.container(key="login_lang"):
                _dil_sec(lang, genis=84)
            _giris_hata(lang)
            _giris_karti(lang)


def _rol(kullanici: dict) -> str:
    return str(kullanici.get("role") or "").lower()


def _rol_metni(lang: str, kullanici: dict) -> str:
    anahtar = _ROL_ANAHTAR.get(_rol(kullanici))
    if not anahtar:
        return ""
    return get_text(lang, anahtar)


def _cikis(lang: str) -> None:
    if st.button(get_text(lang, "logout"), key="cikis"):
        _oturumu_temizle()
        st.session_state.notice = None
        st.rerun()


def _nav_dugmesi(etiket: str, anahtar: str, hedef: str, aktif: bool, ikon: str) -> None:
    if st.button(
        etiket,
        key=anahtar,
        type="primary" if aktif else "secondary",
        icon=ikon,
        width="stretch",
    ):
        st.session_state["menu"] = hedef
        if hedef == "risk":
            st.query_params["sayfa"] = "risk"
        elif "sayfa" in st.query_params:
            del st.query_params["sayfa"]
        st.rerun()


def _kenar(lang: str, rol: str) -> None:
    with st.sidebar:
        if st.button(
            get_text(lang, "new_chat"),
            key="yeni_konusma",
            icon=":material/add:",
            width="stretch",
        ):
            st.session_state.messages = []
            st.session_state.query_error = None
            st.session_state["menu"] = "chat"
            if "sayfa" in st.query_params:
                del st.query_params["sayfa"]
            st.rerun()
        aktif = st.session_state.get("menu")
        _nav_dugmesi(
            get_text(lang, "nav_assistant"),
            "nav_chat",
            "chat",
            aktif == "chat",
            ":material/chat:",
        )
        if rol in _RISK_ROLLERI:
            _nav_dugmesi(
                get_text(lang, "tab_risk"),
                "nav_risk",
                "risk",
                aktif == "risk",
                ":material/flag:",
            )
        sorular = _ornek_sorulari(lang, rol)
        if sorular is not None:
            with st.container(key="sidebar_examples"):
                with st.expander(get_text(lang, "ask_examples"), expanded=False):
                    for sira, soru in enumerate(sorular):
                        st.button(
                            soru,
                            key=f"side_q_{sira}",
                            width="stretch",
                            on_click=_ornek_gonder,
                            args=(soru,),
                        )
        with st.container(key="sidebar_footer", border=False):
            st.markdown(
                _logo_html(_TURKSAT, "Türksat", 120, "logo-side-mark"),
                unsafe_allow_html=True,
            )


def _ust_cubuk(lang: str, kullanici: dict) -> None:
    with st.container(key="topbar"):
        with st.container(
            horizontal=True,
            vertical_alignment="center",
            gap="small",
            key="top_meta",
        ):
            st.markdown(
                f'<span class="tb-chip">{html.escape(get_text(lang, "demo_data"))}</span>',
                unsafe_allow_html=True,
            )
            rol_metni = _rol_metni(lang, kullanici).strip()
            if rol_metni:
                st.markdown(
                    f'<span class="tb-chip">{html.escape(rol_metni)}</span>',
                    unsafe_allow_html=True,
                )
            _dil_sec(lang, genis=76)
            _cikis(lang)


def _menuyu_ac() -> None:
    """Girişten sonra bir kez: kenar menü kapalıysa açma okuna tıklar."""
    if not st.session_state.pop("menu_ac", False):
        return
    with st.container(key="menu_ac"):
        components.html(
            "<script>setTimeout(function(){"
            "var b=window.parent.document.querySelector('[data-testid=\"stExpandSidebarButton\"]');"
            "if(b){b.click();}"
            "},300);</script>",
            height=0,
        )


def _sayfa_hazirla(rol: str) -> str:
    """Sohbet her rolde vardır. Risk yalnızca müdür ve öğretmendedir.

    Doğrudan adres `?sayfa=risk`. İzni olmayan rolde sayfa yoktur.
    """
    izin = rol in _RISK_ROLLERI
    istenen = st.query_params.get("sayfa")
    if istenen == "risk" and not izin:
        return "forbidden"
    secenekler = ["chat"]
    if izin:
        secenekler.append("risk")
    if st.session_state.get("menu") not in secenekler:
        st.session_state["menu"] = istenen if istenen in secenekler else "chat"
    secim = st.session_state["menu"]
    if secim == "risk":
        if istenen != "risk":
            st.query_params["sayfa"] = "risk"
    elif istenen == "risk":
        del st.query_params["sayfa"]
    return secim


def _risk_baslik(lang: str) -> dict[str, str]:
    return {
        "student": get_text(lang, "risk_student"),
        "class_name": get_text(lang, "risk_class"),
        "grade_average": get_text(lang, "risk_grade_average"),
        "absences": get_text(lang, "risk_absences"),
        "grade_rank": get_text(lang, "risk_grade_rank"),
        "absence_rank": get_text(lang, "risk_absence_rank"),
        "flag": get_text(lang, "risk_flag"),
    }


def _risk(lang: str, rol: str) -> None:
    st.info(get_text(lang, "risk_notice"))
    with st.spinner(get_text(lang, "loading")):
        sonuc = api_client.risk(st.session_state.token)
    if not sonuc.get("ok"):
        if sonuc.get("status_code") == 401:
            _oturumu_temizle()
            st.session_state.notice = "error_401"
            st.rerun()
        if sonuc.get("status_code") == 403:
            st.error(get_text(lang, "error_403"))
            return
        _hata_goster(lang, sonuc)
        return
    rows = sonuc.get("data")
    if not isinstance(rows, list):
        _hata_goster(lang, {"status_code": 500, "kind": "server"})
        return
    goster = rows
    if rol == "principal":
        secilen = st.selectbox(
            get_text(lang, "risk_class"),
            options=["", *risk_siniflari(rows)],
            format_func=lambda kod: get_text(lang, "risk_all_classes") if kod == "" else kod,
            key="risk_sinif",
        )
        goster = risk_filtre(rows, secilen or "")
    baslik = _risk_baslik(lang)
    evet = get_text(lang, "risk_flag_yes")
    for kart in risk_kartlari(goster):
        st.markdown(risk_kart_html(kart), unsafe_allow_html=True)
    tablo = risk_tablosu(goster, baslik, evet)
    with st.container(key="risk_table_card", border=True):
        st.dataframe(
            risk_stili(tablo, baslik["flag"], evet),
            hide_index=True,
            column_config={
                baslik["grade_average"]: st.column_config.NumberColumn(
                    alignment="right",
                    format="%.2f",
                ),
            },
        )


def _ornek_gonder(soru: str) -> None:
    """Kenar menüdeki örnek soruyu sohbete taşır."""
    st.session_state["bekleyen_soru"] = soru
    st.session_state["menu"] = "chat"
    if "sayfa" in st.query_params:
        del st.query_params["sayfa"]


def _ornek_logla(neden: str) -> None:
    _ornek_kayit.warning("Örnek soru yanıtı beklenen biçimde değil: %s", neden)


def _ornek_ayikla(gelen: object) -> list[str] | None:
    """Yalnızca [{"question": str}] kabul edilir."""
    if not isinstance(gelen, list):
        _ornek_logla(type(gelen).__name__)
        return None
    sorular: list[str] = []
    for oge in gelen:
        if not isinstance(oge, dict) or set(oge) != _ORNEK_ALAN:
            _ornek_logla("kayıt alanları")
            return None
        soru = oge.get("question")
        if not isinstance(soru, str) or not soru.strip():
            _ornek_logla("kayıt değeri")
            return None
        sorular.append(soru.strip())
    return sorular


def _ornek_sorulari(lang: str, rol: str) -> list[str] | None:
    """GET /assistant/examples. Beklenmeyen biçim öneri alanını gizler.

    Önbellek anahtarı (rol, dil): liste rola göre değişir, yalnız dile göre tutulamaz.
    """
    onbellek = st.session_state.get("ornek_sorular")
    if not isinstance(onbellek, dict):
        onbellek = {}
        st.session_state["ornek_sorular"] = onbellek
    anahtar = (rol, lang)
    kayit = onbellek.get(anahtar)
    if kayit == "gizli":
        return None
    if isinstance(kayit, list):
        return kayit
    sorular: list[str] | None = []
    token = st.session_state.get("token")
    if isinstance(token, str) and token:
        sonuc = api_client.examples(token, "en" if lang == "en" else "tr")
        if sonuc.get("ok"):
            sorular = _ornek_ayikla(sonuc.get("data"))
        else:
            sorular = []
    if sorular is None:
        onbellek[anahtar] = "gizli"
        return None
    onbellek[anahtar] = sorular
    return sorular


def _bos_sohbet(lang: str) -> None:
    with st.container(key="empty_chat"):
        st.markdown(
            _logo_html(_AVATAR, get_text(lang, "nav_assistant"), 72, "logo-avatar"),
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<p class="empty-hello">{html.escape(get_text(lang, "empty_hello"))}</p>',
            unsafe_allow_html=True,
        )


def _sohbet(lang: str) -> None:
    for sira, mesaj in enumerate(st.session_state.messages):
        _mesaji_ciz(lang, mesaj, sira)

    bekleyen = st.session_state.pop("bekleyen_soru", None)
    if not isinstance(bekleyen, str):
        bekleyen = None
    yazilan = st.bottom.chat_input(get_text(lang, "question_box"))
    soru = bekleyen if bekleyen and bekleyen.strip() else yazilan
    if not st.session_state.messages and not (isinstance(soru, str) and soru.strip()):
        _bos_sohbet(lang)
    if soru and str(soru).strip():
        soru = str(soru).strip()
        gecmis = _gecmis()
        with st.chat_message("user"):
            st.markdown(soru)
        with st.spinner(get_text(lang, "loading")):
            sonuc = api_client.query(
                st.session_state.token,
                soru,
                lang,
                history=gecmis,
            )
        if sonuc.get("ok") and isinstance(sonuc.get("data"), dict):
            data = sonuc["data"]
            st.session_state.query_error = None
            st.session_state.messages.append({"role": "user", "content": soru})
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": str(data.get("answer") or ""),
                    "data": data,
                }
            )
            sira = len(st.session_state.messages) - 1
            _mesaji_ciz(lang, st.session_state.messages[sira], sira)
        elif sonuc.get("status_code") == 401:
            _oturumu_temizle()
            st.session_state.notice = "error_401"
            st.rerun()
        else:
            st.session_state.query_error = sonuc

    if isinstance(st.session_state.query_error, dict):
        _hata_goster(lang, st.session_state.query_error)
    st.markdown('<div class="chat-end-pad" aria-hidden="true"></div>', unsafe_allow_html=True)


def main() -> None:
    lang = st.session_state.lang if st.session_state.lang in {"tr", "en"} else "tr"
    if st.query_params.get("sayfa") == "arastirma":
        # Herkese açık sayfa: oturum açık olsun olmasın yalnızca bu çizilir; backend'e gidilmez.
        arastirma.sayfa(lang, _dil_sec)
        return
    if not st.session_state.token:
        _giris(lang)
        return
    st.logo(str(_LOGO_YAZI), size="large")
    kullanici = st.session_state.user if isinstance(st.session_state.user, dict) else {}
    rol = _rol(kullanici)
    sayfa = _sayfa_hazirla(rol)
    _kenar(lang, rol)
    _ust_cubuk(lang, kullanici)
    _menuyu_ac()
    with st.container(key="page_body"):
        if sayfa == "forbidden":
            st.error(get_text(lang, "error_403"))
            if st.button(get_text(lang, "nav_assistant"), key="sohbete_don"):
                st.session_state["menu"] = "chat"
                if "sayfa" in st.query_params:
                    del st.query_params["sayfa"]
                st.rerun()
            return
        if sayfa == "risk":
            _risk(lang, rol)
            return
        _sohbet(lang)


main()
