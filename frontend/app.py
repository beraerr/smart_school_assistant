"""Giriş ve sorgu ekranı."""

import pandas as pd
import streamlit as st

from api_client import login, query
from i18n import get_text
from view import has_duplicate_grades, pivot_grades

st.set_page_config(page_title="Akıllı Okul Bilgi Sistemi", layout="centered")

st.session_state.setdefault("token", None)
st.session_state.setdefault("user", None)
st.session_state.setdefault("lang", "tr")
st.session_state.setdefault("query_data", None)
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


def _baslik_ve_dil(lang: str) -> str:
    sol, sag = st.columns([6, 1])
    with sag:
        st.selectbox(
            get_text(lang, "language"),
            options=["tr", "en"],
            format_func=lambda kod: "TR" if kod == "tr" else "EN",
            key="lang",
            label_visibility="collapsed",
        )
    lang = st.session_state.lang
    with sol:
        st.title(get_text(lang, "title"))
    return lang


def _sonuclari_goster(lang: str, data: dict) -> None:
    results = data.get("results") or []
    explanation = data.get("explanation") or ""
    if results:
        tablo = pd.DataFrame(results)
        if {"name", "subject", "grade"}.issubset(tablo.columns):
            if st.checkbox(get_text(lang, "columns_by_subject"), key="pivot_secimi"):
                if has_duplicate_grades(tablo):
                    st.warning(get_text(lang, "duplicate_grades"))
                tablo = pivot_grades(tablo)
        st.dataframe(tablo)
    else:
        st.info(get_text(lang, "no_results"))
    if explanation:
        st.info(explanation)
    sql_metin = data.get("sql")
    if isinstance(sql_metin, str) and sql_metin:
        with st.expander(get_text(lang, "generated_sql")):
            st.code(sql_metin, language="sql")


def _giris(lang: str) -> None:
    if st.session_state.notice == "error_401":
        st.error(get_text(lang, "error_401"))
    elif isinstance(st.session_state.form_error, dict):
        hata = st.session_state.form_error
        if hata.get("status_code") == 401:
            st.error(get_text(lang, "login_error"))
        else:
            _hata_goster(lang, hata)

    with st.form("giris"):
        username = st.text_input(get_text(lang, "username"), key="kullanici_adi")
        password = st.text_input(
            get_text(lang, "password"),
            type="password",
            key="sifre",
        )
        gonder = st.form_submit_button(get_text(lang, "login_button"))

    if not gonder:
        return

    st.session_state.notice = None
    st.session_state.form_error = None
    sonuc = login(username, password)
    if sonuc["ok"] and isinstance(sonuc.get("data"), dict):
        govde = sonuc["data"]
        token = govde.get("access_token")
        if token:
            st.session_state.token = token
            st.session_state.user = govde.get("user")
            st.session_state.query_data = None
            st.session_state.query_error = None
            st.rerun()
            return
    if sonuc.get("status_code") == 401:
        st.session_state.form_error = sonuc
        st.error(get_text(lang, "login_error"))
        return
    st.session_state.form_error = sonuc
    _hata_goster(lang, sonuc)


def _sorgu(lang: str) -> None:
    kullanici = st.session_state.user if isinstance(st.session_state.user, dict) else {}
    st.write(get_text(lang, "welcome").format(username=kullanici.get("username", "")))
    if st.button(get_text(lang, "logout"), key="cikis"):
        st.session_state.token = None
        st.session_state.user = None
        st.session_state.query_data = None
        st.session_state.query_error = None
        st.session_state.notice = None
        st.session_state.form_error = None
        st.rerun()

    with st.form("soru_formu", clear_on_submit=False):
        soru = st.text_area(get_text(lang, "question_box"), key="soru")
        gonder = st.form_submit_button(get_text(lang, "ask_button"))
    if gonder:
        with st.spinner(get_text(lang, "loading")):
            sonuc = query(st.session_state.token, soru, lang)
        if sonuc["ok"]:
            st.session_state.query_data = sonuc["data"]
            st.session_state.query_error = None
        elif sonuc.get("status_code") == 401:
            st.session_state.token = None
            st.session_state.user = None
            st.session_state.query_data = None
            st.session_state.query_error = None
            st.session_state.form_error = None
            st.session_state.notice = "error_401"
            st.rerun()
        else:
            st.session_state.query_data = None
            st.session_state.query_error = sonuc

    if isinstance(st.session_state.query_error, dict):
        _hata_goster(lang, st.session_state.query_error)
    if isinstance(st.session_state.query_data, dict):
        _sonuclari_goster(lang, st.session_state.query_data)


def main() -> None:
    lang = _baslik_ve_dil(st.session_state.lang)
    if st.session_state.token:
        _sorgu(lang)
    else:
        _giris(lang)


main()
