"""Giriş ve sohbet ekranı."""

import pandas as pd
import streamlit as st

import api_client
from i18n import get_text
from view import has_duplicate_grades, pivot_grades

st.set_page_config(page_title="Akıllı Okul Bilgi Sistemi", layout="centered")

_GECMIS = 6

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


def _oturumu_temizle() -> None:
    st.session_state.token = None
    st.session_state.user = None
    st.session_state.messages = []
    st.session_state.query_error = None
    st.session_state.form_error = None


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

    results = data.get("results")
    if isinstance(results, list) and results:
        with st.expander(get_text(lang, "table"), expanded=False):
            tablo = pd.DataFrame(results)
            if {"name", "subject", "grade"}.issubset(tablo.columns):
                if st.checkbox(
                    get_text(lang, "columns_by_subject"),
                    key=f"pivot_{sira}",
                ):
                    if has_duplicate_grades(tablo):
                        st.warning(get_text(lang, "duplicate_grades"))
                    tablo = pivot_grades(tablo)
            st.dataframe(tablo)

    sorgular = _sql_listesi(data)
    if sorgular:
        with st.expander(get_text(lang, "generated_sql"), expanded=False):
            for sorgu in sorgular:
                st.code(sorgu, language="sql")

    aciklama = data.get("explanation")
    if isinstance(aciklama, str) and aciklama.strip():
        st.caption(aciklama)


def _mesaji_ciz(lang: str, mesaj: dict, sira: int) -> None:
    with st.chat_message(mesaj["role"]):
        if mesaj["role"] == "assistant" and isinstance(mesaj.get("data"), dict):
            _asistan_icerigi(lang, mesaj["data"], sira)
        else:
            st.markdown(mesaj.get("content") or "")


def _gecmis() -> list[dict]:
    return [
        {"role": mesaj["role"], "content": mesaj.get("content") or ""}
        for mesaj in st.session_state.messages[-_GECMIS:]
    ]


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
    sonuc = api_client.login(username, password)
    if sonuc["ok"] and isinstance(sonuc.get("data"), dict):
        govde = sonuc["data"]
        token = govde.get("access_token")
        if token:
            st.session_state.token = token
            st.session_state.user = govde.get("user")
            st.session_state.messages = []
            st.session_state.query_error = None
            st.rerun()
            return
    if sonuc.get("status_code") == 401:
        st.session_state.form_error = sonuc
        st.error(get_text(lang, "login_error"))
        return
    st.session_state.form_error = sonuc
    _hata_goster(lang, sonuc)


def _sohbet(lang: str) -> None:
    kullanici = st.session_state.user if isinstance(st.session_state.user, dict) else {}
    sol, orta, sag = st.columns([4, 2, 1])
    with sol:
        st.write(get_text(lang, "welcome").format(username=kullanici.get("username", "")))
    with orta:
        if st.button(get_text(lang, "new_chat"), key="yeni_konusma"):
            st.session_state.messages = []
            st.session_state.query_error = None
            st.rerun()
    with sag:
        if st.button(get_text(lang, "logout"), key="cikis"):
            _oturumu_temizle()
            st.session_state.notice = None
            st.rerun()

    for sira, mesaj in enumerate(st.session_state.messages):
        _mesaji_ciz(lang, mesaj, sira)

    soru = st.chat_input(get_text(lang, "question_box"))
    if soru and soru.strip():
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


def main() -> None:
    lang = _baslik_ve_dil(st.session_state.lang)
    if st.session_state.token:
        _sohbet(lang)
    else:
        _giris(lang)


main()
