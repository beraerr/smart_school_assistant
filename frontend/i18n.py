"""Arayüz metinleri. Bütün görünen yazılar bu sözlükten okunur."""

STRINGS = {
    "tr": {
        "title": "Akıllı Okul Bilgi Sistemi",
        "username": "Kullanıcı adı",
        "password": "Şifre",
        "login_button": "Giriş",
        "login_error": "Kullanıcı adı veya şifre hatalı.",
        "welcome": "Hoş geldiniz, {username}",
        "logout": "Çıkış",
        "question_box": "Sorunuz",
        "ask_button": "Sor",
        "no_results": "Sonuç bulunamadı.",
        "columns_by_subject": "Derslere göre sütunlar",
        "error_401": "Oturumunuz sona erdi. Lütfen yeniden giriş yapın.",
        "error_429": "Çok fazla istek. {seconds} saniye sonra tekrar deneyin.",
        "error_503": "Servis şu anda kullanılamıyor. Lütfen tekrar deneyin.",
        "error_400": "İstek geçersiz. Soruyu kontrol edip yeniden deneyin.",
        "error_connection": "Sunucuya bağlanılamadı.",
        "error_server": "Sunucuda bir hata oluştu, lütfen tekrar deneyin.",
        "language": "Dil",
        "loading": "Yükleniyor...",
        "generated_sql": "Üretilen SQL",
        "duplicate_grades": "Aynı öğrenci, ders ve tarih için birden fazla not var. Tabloda ilk değer gösteriliyor.",
    },
    "en": {
        "title": "Smart School Information System",
        "username": "Username",
        "password": "Password",
        "login_button": "Log in",
        "login_error": "Username or password is incorrect.",
        "welcome": "Welcome, {username}",
        "logout": "Log out",
        "question_box": "Your question",
        "ask_button": "Ask",
        "no_results": "No results.",
        "columns_by_subject": "Columns by subject",
        "error_401": "Your session has expired. Please log in again.",
        "error_429": "Too many requests. Try again in {seconds} seconds.",
        "error_503": "The service is unavailable. Please try again.",
        "error_400": "The request is invalid. Check the question and try again.",
        "error_connection": "Could not connect to the server.",
        "error_server": "A server error occurred, please try again.",
        "language": "Language",
        "loading": "Loading...",
        "generated_sql": "Generated SQL",
        "duplicate_grades": "More than one grade exists for the same student, subject, and date. The table shows the first value.",
    },
}


def get_text(lang: str, key: str) -> str:
    """Seçilen dildeki metni döndürür. Bilinmeyen dil Türkçeye düşer."""
    dil = lang if lang in STRINGS else "tr"
    metin = STRINGS[dil].get(key)
    if metin is None:
        metin = STRINGS["tr"].get(key, key)
    return metin
