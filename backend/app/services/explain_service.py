"""RLS kapsamını kısa, sabit metinle açıklar. Dil modeli kullanmaz."""

_METIN = {
    "tr": {
        "principal": (
            "Bu sonuçlar, müdür hesabının okul genelinde görebildiği kayıtlardan gelir."
        ),
        "teacher": (
            "Bu sonuçlar, öğretmen hesabınıza atanmış sınıfın kayıtlarından gelir."
        ),
        "teacher_open": (
            "Bu sonuçlar, öğretmen hesabınıza açık olan kayıtlardan gelir."
        ),
        "parent": (
            "Bu sonuçlar, veli hesabınıza bağlı öğrencinin kayıtlarından gelir."
        ),
        "student": "Bu sonuçlar, öğrenci hesabınızın kendi kayıtlarından gelir.",
        "other": "Bu sonuçlar, hesabınıza açık kayıtlardan gelir.",
    },
    "en": {
        "principal": (
            "These results come from records a principal account can view across the school."
        ),
        "teacher": (
            "These results come from records of the class assigned to your teacher account."
        ),
        "teacher_open": "These results come from records open to your teacher account.",
        "parent": "These results come from the child linked to this parent account.",
        "student": "These results come from your own records on this student account.",
        "other": "These results come from records open to your account.",
    },
}


def build_explanation(role: str, related_class: str | None, lang: str) -> str:
    """Rolün görebildiği kapsama göre açıklama döndürür.

    Metin satır sayısını veya başka bir ölçüyü söylemez.
    related_class yalnızca öğretmen kapsamında sınıf atanıp atanmadığına bakmak için kullanılır;
    değeri metne yazılmaz.
    """
    dil = lang if lang in _METIN else "tr"
    tablo = _METIN[dil]
    rol = str(getattr(role, "value", role)).lower()
    if rol == "teacher":
        if related_class and str(related_class).strip():
            return tablo["teacher"]
        return tablo["teacher_open"]
    return tablo.get(rol, tablo["other"])
