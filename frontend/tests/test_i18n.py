"""İki dil aynı anahtarları taşır."""

from frontend.i18n import STRINGS, get_text

_ANAHTARLAR = {
    "title",
    "username",
    "password",
    "login_button",
    "login_error",
    "welcome",
    "logout",
    "question_box",
    "new_chat",
    "table",
    "columns_by_subject",
    "error_401",
    "error_429",
    "error_503",
    "error_400",
    "error_connection",
    "error_server",
    "generated_sql",
}


def test_diller_ayni_anahtarlari_tasir() -> None:
    assert set(STRINGS) == {"tr", "en"}
    assert set(STRINGS["tr"]) == set(STRINGS["en"])
    assert _ANAHTARLAR <= set(STRINGS["tr"])


def test_get_text_secilen_dili_okur() -> None:
    assert get_text("tr", "login_button") == "Giriş"
    assert get_text("en", "new_chat") == "New conversation"
    assert get_text("tr", "table") == "Tablo"
    assert "Sonuç bulunamadı" not in " ".join(STRINGS["tr"].values())
    assert get_text("en", "columns_by_subject") == "Columns by subject"
    assert get_text("tr", "generated_sql") == "Üretilen SQL"
    assert get_text("en", "generated_sql") == "Generated SQL"
    assert get_text("tr", "error_server") == "Sunucuda bir hata oluştu, lütfen tekrar deneyin."
    assert get_text("en", "error_server") == "A server error occurred, please try again."
    assert "{seconds}" in get_text("tr", "error_429")
    assert get_text("fr", "title") == get_text("tr", "title")
    assert get_text("tr", "olmayan") == "olmayan"
