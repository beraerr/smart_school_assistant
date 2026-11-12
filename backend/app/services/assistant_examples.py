"""Rol bazlı örnek sorular. Hazır cevap içermez. Risk sorusu yoktur."""

EXAMPLES: dict[str, dict[str, tuple[str, ...]]] = {
    "principal": {
        "tr": (
            "Ben kimim?",
            "Okulun ders bazında not ortalamaları nedir?",
            "Hangi sınıfın not ortalaması en düşük?",
            "9-A neden diğer sınıflardan düşük?",
            "Mazeretsiz devamsızlığı en yüksek 3 öğrenci kim?",
            "Sınıfların devamsızlık özetini göster.",
            "50'nin altında notu olan öğrenci var mı?",
            "60'ın altında notu olan öğrenciler kimler?",
            "Eylül ve Ekim not ortalamalarını karşılaştır.",
            "Geçen aya göre okul ortalaması nasıl değişti?",
            "Bugün kaç öğrenci okula gelmedi?",
            "Bu dönem hangi sınıfın ortalaması en düşük?",
        ),
        "en": (
            "Who am I?",
            "What are the school's grade averages by subject?",
            "Which class has the lowest grade average?",
            "Why is 9-A lower than the other classes?",
            "Which 3 students have the most unexcused absences?",
            "Show the absence summary by class.",
            "Is there a student with a grade below 50?",
            "Which students have a grade below 60?",
            "Compare the September and October grade averages.",
            "How did the school average change compared with last month?",
            "How many students did not come to school today?",
            "Which class has the lowest average this term?",
        ),
    },
    "teacher": {
        "tr": (
            "Ben kimim?",
            "Sınıfımın ders bazında not ortalamaları nedir?",
            "Sınıfımda mazeretsiz devamsızlığı en yüksek öğrenci kim?",
            "Sınıfımda 60'ın altında notu olan öğrenci var mı?",
            "Sınıfımın Eylül ve Ekim ortalamalarını karşılaştır.",
            "Zeynep bu hafta okula geldi mi?",
            "Bugün sınıfımdan kaç öğrenci gelmedi?",
            "Bu dönem sınıfımın not ortalaması nasıl?",
        ),
        "en": (
            "Who am I?",
            "What are my class's grade averages by subject?",
            "Which student in my class has the most unexcused absences?",
            "Is there a student in my class with a grade below 60?",
            "Compare my class's September and October averages.",
            "Did Zeynep come to school this week?",
            "How many students from my class did not come today?",
            "How is my class's grade average this term?",
        ),
    },
    "parent": {
        "tr": (
            "Ben kimim?",
            "Çocuğumun not ortalaması nedir?",
            "Çocuğumun en düşük olduğu ders hangisi?",
            "Çocuğumun devamsızlık durumu nedir?",
            "Çocuğumun Eylül ve Ekim notlarını karşılaştır.",
            "Çocuğum okulda mutsuz görünüyor, ne yapmalıyım?",
            "Çocuğumun bu dönemki devamsızlığı nasıl?",
        ),
        "en": (
            "Who am I?",
            "What is my child's grade average?",
            "Which subject is my child lowest in?",
            "What is my child's absence status?",
            "Compare my child's September and October grades.",
            "My child seems unhappy at school, what should I do?",
            "How is my child's absence this term?",
        ),
    },
    "student": {
        "tr": (
            "Ben kimim?",
            "Not ortalamam kaç?",
            "En düşük notum hangi derste?",
            "Kaç gün devamsızlığım var?",
            "Sınıfta kaçıncıyım?",
            "Eylül ve Ekim notlarımı karşılaştır.",
            "Bu dönem not ortalamam nasıl?",
        ),
        "en": (
            "Who am I?",
            "What is my grade average?",
            "Which subject is my lowest grade in?",
            "How many days of absence do I have?",
            "What is my rank in class?",
            "Compare my September and October grades.",
            "How is my grade average this term?",
        ),
    },
}


def example_questions(role: str, lang: str) -> list[dict[str, str]]:
    """Örnek sorular. Her kayıt yalnız question alanından oluşur."""
    rol = str(role or "").lower()
    dil = "en" if lang == "en" else "tr"
    tablo = EXAMPLES.get(rol)
    if tablo is None:
        return []
    return [{"question": soru} for soru in tablo[dil]]


def questions(role: str, lang: str) -> list[str]:
    """Oturumdaki rolün örnek soru metinleri. Bilinmeyen rol boş liste döner."""
    return [oge["question"] for oge in example_questions(role, lang)]
