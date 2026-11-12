"""Doğal dil sorusunu tek bir SELECT ifadesine çevirir."""

from config.settings import settings

_SEMA = """
students(id, name, class_name, total_absences, parent_id)
grades(id, student_id, subject, grade, date)
attendance(id, student_id, date, status)
""".strip()

_SISTEM = f"""Okul veritabanı için tek bir PostgreSQL SELECT ifadesi yaz.

Şema:
{_SEMA}

Kurallar:
- Yalnızca tek bir SELECT ifadesi üret.
- Yalnızca students, grades ve attendance tablolarını kullan.
- Erişim filtresi ekleme (sınıf, öğrenci id). Bunu veritabanı uygular.
- Başka hiçbir metin ya da açıklama yazma.
"""


def _kod_blogunu_temizle(metin: str) -> str:
    """Yanıttaki markdown kod bloğu işaretlerini kaldırır."""
    temiz = metin.strip()
    if not temiz.startswith("```"):
        return temiz

    satirlar = temiz.splitlines()
    if satirlar and satirlar[0].startswith("```"):
        satirlar = satirlar[1:]
    if satirlar and satirlar[-1].strip() == "```":
        satirlar = satirlar[:-1]
    return "\n".join(satirlar).strip()


def translate_question_to_sql(question: str, client=None) -> str:
    """Doğal dil sorusundan tek bir SELECT metni döndürür.

    client verilmezse ayarlardaki anahtarla gerçek istemci oluşturulur.
    Testler sahte bir client geçebilir.
    """
    if client is None:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    mesaj = client.messages.create(
        model=settings.LLM_MODEL,
        max_tokens=1024,
        temperature=0,
        system=_SISTEM,
        messages=[{"role": "user", "content": question}],
    )

    parcalar: list[str] = []
    for blok in mesaj.content:
        if getattr(blok, "type", None) == "text":
            parcalar.append(blok.text)
    return _kod_blogunu_temizle("".join(parcalar))
