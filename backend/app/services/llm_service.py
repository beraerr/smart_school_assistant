"""Doğal dil sorusunu tek bir SELECT ifadesine çevirir."""

from config.settings import settings

_SEMA = """
students(id, name, class_name, total_absences, parent_id)
grades(id, student_id, subject, grade, date)
attendance(id, student_id, date, status)
""".strip()

_ORTAK = f"""Okul veritabanı için tek bir PostgreSQL SELECT ifadesi yaz.

Şema:
{_SEMA}

Kurallar:
- Yalnızca tek bir SELECT ifadesi üret.
- Yalnızca students, grades ve attendance tablolarını kullan.
- Ad aramalarında = yerine ILIKE '%...%' kullan.
- Birden fazla öğrenci döndürebilecek sorgularda name ve id SELECT listesinde olsun.
- Kendi WHERE koşuluna class_name veya student_id gibi erişim filtresi ekleme. Erişim filtresi ekleme; bunu veritabanı uygular.
- Başka hiçbir metin ya da açıklama yazma.
"""

_KARSILASTIRMA = """
- Başka öğrencilerle karşılaştırma, sıralama veya sınıf geneli istatistik gerektiren soruda SQL yazma.
- Bu durumda tam olarak NOT_SUPPORTED_COMPARISON döndür.
"""


def _sistem_promptu(role: str) -> str:
    if role.lower() in {"parent", "student"}:
        return _ORTAK + _KARSILASTIRMA
    return _ORTAK


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


def translate_question_to_sql(
    question: str,
    role: str,
    client=None,
    validation_error: str | None = None,
) -> str:
    """Doğal dil sorusundan tek bir SELECT metni veya NOT_SUPPORTED_COMPARISON döndürür.

    client verilmezse ayarlardaki anahtarla gerçek istemci oluşturulur.
    validation_error doluysa önceki doğrulama hatası modele iletilir.
    """
    if client is None:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    icerik = question
    if validation_error:
        icerik = (
            f"{question}\n\n"
            "Önceki yanıt geçersizdi.\n"
            f"Hata: {validation_error}\n"
            "Kurallara uygun tek bir SELECT yaz."
        )

    mesaj = client.messages.create(
        model=settings.LLM_MODEL,
        max_tokens=1024,
        temperature=0,
        system=_sistem_promptu(role),
        messages=[{"role": "user", "content": icerik}],
    )

    parcalar: list[str] = []
    for blok in mesaj.content:
        if getattr(blok, "type", None) == "text":
            parcalar.append(blok.text)
    return _kod_blogunu_temizle("".join(parcalar))
