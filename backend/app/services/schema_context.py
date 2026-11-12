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


def reset_schema_context() -> None:
    """Testlerin önbelleği temizlemesi için."""
    global _onbellek
    _onbellek = None


def _bugun() -> str:
    """REFERENCE_DATE doluysa o gün, boşsa takvim günü. YYYY-MM-DD."""
    ham = settings.REFERENCE_DATE.strip()
    if not ham:
        return date.today().isoformat()
    return date.fromisoformat(ham).isoformat()


def build_schema_context() -> str:
    """Süper kullanıcı bağlantısıyla şema özetini kurar ve önbelleğe alır."""
    global _onbellek
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
        tarih = db.execute(
            text("SELECT MIN(date) AS ilk, MAX(date) AS son FROM grades")
        ).one()
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

    ilk = tarih.ilk.isoformat() if tarih.ilk is not None else ""
    son = tarih.son.isoformat() if tarih.son is not None else ""
    veri_ilk = veri.ilk.isoformat() if veri.ilk is not None else ""
    veri_son = veri.son.isoformat() if veri.son is not None else ""
    en_dusuk = "" if olcek.en_dusuk is None else str(olcek.en_dusuk)
    en_yuksek = "" if olcek.en_yuksek is None else str(olcek.en_yuksek)
    _onbellek = "\n".join(
        [
            "Şema özeti:",
            f"- attendance.status değerleri: {', '.join(durumlar) or '-'}",
            "- toplam devamsızlık = students.total_absences; ayrıntı = attendance (status)",
            f"- grades.subject değerleri: {', '.join(dersler) or '-'}",
            f"- sınıf adları: {', '.join(siniflar) or '-'}",
            f"- grades.date aralığı: {ilk} .. {son}",
            (
                f"Bugünün tarihi: {_bugun()}. "
                f"Veri aralığı: {veri_ilk}–{veri_son}. "
                "'dün', 'bu hafta', 'bu ay', 'geçen ay' gibi ifadeler bu tarihe göre yorumlanır; "
                "tarih aralıklarını SQL'e yaz. "
                'Veri aralığı dışında kalan dönemde "o dönemde kayıt yok" de.'
            ),
            f"- not ölçeği (min/max): {en_dusuk} .. {en_yuksek}",
            *_yonetmelik(),
            f"- {_YOK}",
        ]
    )
    return _onbellek
