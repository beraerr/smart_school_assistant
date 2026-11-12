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
    "tab_chat",
    "tab_risk",
    "error_403",
    "risk_notice",
    "risk_student",
    "risk_class",
    "risk_grade_average",
    "risk_absences",
    "risk_grade_rank",
    "risk_absence_rank",
    "risk_flag",
    "risk_reason",
    "risk_flag_yes",
    "risk_all_classes",
}

_RISK_BILDIRIMI = (
    "Dikkat bayrağı, içinde bulunulan dönemin verisiyle her sınıfta göreli olarak "
    "hesaplanır: not ortalaması ve mazeretsiz devamsızlık sıralamalarına göre "
    "sınıfın yaklaşık beşte biri işaretlenir; eşit sıralamalar bu sayıyı "
    "artırabilir. Henüz not girilmemiş sınıfta bayrak yoktur. Bu bir olasılık ya "
    "da tanı değil, öğretmenin dikkatine sunulan bir işarettir."
)

_RISK_BILDIRIMI_EN = (
    "Attention flags are computed relative to each class using the current term's "
    "data: about one fifth of the class is flagged based on grade average and "
    "unexcused absence rankings; ties can raise this number. Classes with no "
    "grades yet have no flags. This is not a probability or a diagnosis, but a "
    "signal for the teacher's attention."
)


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


def test_risk_bildirimi_ve_alarm_dili_yok() -> None:
    assert get_text("tr", "risk_notice") == _RISK_BILDIRIMI
    assert get_text("en", "risk_notice") == _RISK_BILDIRIMI_EN
    assert "en az bir öğrenci" not in get_text("tr", "risk_notice")
    assert "at least one student" not in get_text("en", "risk_notice")
    assert get_text("tr", "error_403") == (
        "Bu işlem yalnızca müdür ve öğretmen hesaplarına açıktır."
    )
    assert get_text("tr", "risk_flag_yes") == "Dikkat"
    assert get_text("en", "risk_flag_yes") == "Attention"
    yasak = ("alarm", "tehlike", "kırmızı", "kirmizi", "danger")
    anahtarlar = [anahtar for anahtar in STRINGS["tr"] if anahtar.startswith("risk_") or anahtar.startswith("tab_")]
    anahtarlar.append("error_403")
    for dil in ("tr", "en"):
        for anahtar in anahtarlar:
            metin = get_text(dil, anahtar).casefold()
            assert all(kelime not in metin for kelime in yasak)
