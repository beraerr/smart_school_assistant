"""Açılışta bir kez okunan şema özeti. Öğrenci adı ve kimliği içermez."""

from datetime import date

from sqlalchemy import text

from backend.app.core.database import SessionLocal
from config.settings import settings

_YOK = (
    "Ders programı, veli toplantısı, servis, "
    "iletişim bilgisi veritabanında YOKTUR."
)


def _yonetmelik() -> list[str]:
    satirlar = [
        f"- Okul yönetmeliği: 100'lük sistemde ders geçme notu {settings.PASS_GRADE}'dir. "
        "Sınıf geçme için ek kurallar vardır; kesin sınıf geçme durumu için "
        "sınıf öğretmeni veya okul idaresiyle görüşmeyi öner.",
    ]
    etiketler = settings.GRADE_LABELS.strip()
    if etiketler:
        satirlar.append(f"- Not dönüşümü: {etiketler}")
    else:
        satirlar.append("- Not dönüşüm tablosu tanımlı değil; 5'lik veya harf dönüşümü yapma.")
    return satirlar

_onbellek: str | None = None
_veri_araligi: tuple[date | None, date | None] | None = None


def reset_schema_context() -> None:
    """Testlerin önbelleği temizlemesi için."""
    global _onbellek, _veri_araligi
    _onbellek = None
    _veri_araligi = None


def veri_araligi() -> tuple[date | None, date | None]:
    """Not ve devamsızlık kayıtlarının (ilk, son) tarihi; kayıt yoksa (None, None).

    Özetle birlikte tek okumada kurulur ve önbelleğe alınır. Bu değer RLS
    dışında, tüm tablolardan okunur; istek başına app.today ile kesilerek
    kullanılmalıdır.
    """
    if _veri_araligi is None:
        build_schema_context()
    assert _veri_araligi is not None
    return _veri_araligi


def build_schema_context() -> str:
    """Süper kullanıcı bağlantısıyla şema özetini kurar ve önbelleğe alır."""
    global _onbellek, _veri_araligi
    if _onbellek is not None:
        return _onbellek

    db = SessionLocal()
    try:
        durumlar = db.execute(
            text("SELECT DISTINCT status FROM attendance ORDER BY status")
        ).scalars().all()
        dersler = db.execute(
            text("SELECT DISTINCT subject FROM grades ORDER BY subject")
        ).scalars().all()
        siniflar = db.execute(
            text("SELECT DISTINCT class_name FROM students ORDER BY class_name")
        ).scalars().all()
        veri = db.execute(
            text(
                "SELECT MIN(tarih) AS ilk, MAX(tarih) AS son FROM ("
                "SELECT date AS tarih FROM grades "
                "UNION ALL "
                "SELECT date FROM attendance"
                ") AS kayitlar"
            )
        ).one()
        olcek = db.execute(
            text("SELECT MIN(grade) AS en_dusuk, MAX(grade) AS en_yuksek FROM grades")
        ).one()
    finally:
        db.close()

    _veri_araligi = (veri.ilk, veri.son)
    en_dusuk = "" if olcek.en_dusuk is None else str(olcek.en_dusuk)
    en_yuksek = "" if olcek.en_yuksek is None else str(olcek.en_yuksek)
    _onbellek = "\n".join(
        [
            "Şema özeti:",
            f"- attendance.status değerleri: {', '.join(durumlar) or '-'}",
            "- devamsızlık = attendance tablosu; status='absent' mazeretsiz, status='excused' mazeretli (ayrı say)",
            f"- grades.subject değerleri: {', '.join(dersler) or '-'}",
            f"- sınıf adları: {', '.join(siniflar) or '-'}",
            f"- not ölçeği (min/max): {en_dusuk} .. {en_yuksek}",
            *_yonetmelik(),
            f"- {_YOK}",
        ]
    )
    return _onbellek
