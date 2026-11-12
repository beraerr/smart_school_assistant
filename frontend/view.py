"""Sorgu tablosunu derse göre sütunlara çevirir. Risk tablosunu sıralar."""

import html
import math
from collections.abc import Mapping, Sequence

import pandas as pd

AMBER_BG = "#FFF3E0"
AMBER_TEXT = "#8A5200"

_RISK_ALANLARI = (
    "student",
    "class_name",
    "grade_average",
    "absences",
    "grade_rank",
    "absence_rank",
    "flag",
)


def has_duplicate_grades(df: pd.DataFrame) -> bool:
    """Aynı öğrenci, ders ve tarih için birden fazla satır var mı."""
    kolonlar = ["name", "subject"]
    if "date" in df.columns:
        kolonlar.append("date")
    if not set(kolonlar).issubset(df.columns):
        return False
    return bool(df.duplicated(subset=kolonlar, keep=False).any())


def pivot_grades(df: pd.DataFrame) -> pd.DataFrame:
    """name satır, subject sütun, grade değer. Tarih varsa satır adı ve tarih olur."""
    index: str | list[str] = ["name", "date"] if "date" in df.columns else "name"
    return df.pivot_table(
        index=index,
        columns="subject",
        values="grade",
        aggfunc="first",
    )


def risk_siniflari(rows: Sequence[Mapping]) -> list[str]:
    """Tablodaki sınıf adları, süzgeç listesi için sıralı."""
    return sorted(
        {str(row.get("class_name") or "") for row in rows if row.get("class_name")}
    )


def risk_filtre(rows: Sequence[Mapping], sinif: str) -> list[Mapping]:
    """Boş sınıf tüm satırları bırakır."""
    if not sinif:
        return list(rows)
    return [row for row in rows if row.get("class_name") == sinif]


def _sayi(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _risk_sirala(rows: Sequence[Mapping]) -> list[Mapping]:
    return sorted(
        rows,
        key=lambda row: (
            0 if row.get("flagged") else 1,
            str(row.get("class_name") or ""),
            str(row.get("name") or ""),
            int(row.get("student_id") or 0),
        ),
    )


def risk_kartlari(rows: Sequence[Mapping]) -> list[dict[str, str]]:
    """Bayraklı öğrenciler, tablo ile aynı sırada. Bayrak yoksa liste boştur."""
    kartlar = []
    for row in _risk_sirala(rows):
        if not row.get("flagged"):
            continue
        ad = row.get("name")
        gerekce = row.get("reason")
        kartlar.append(
            {
                "name": "" if ad is None else str(ad),
                "class_name": str(row.get("class_name") or ""),
                "reason": "" if gerekce is None else str(gerekce),
            }
        )
    return kartlar


def risk_kart_html(kart: Mapping[str, str]) -> str:
    """Sol kenarı amber olan kart. Kırmızı yok."""
    return (
        f'<div class="risk-card" style="border-left: 4px solid {AMBER_TEXT}; '
        f"background-color: {AMBER_BG}; color: {AMBER_TEXT}; "
        'padding: 0.75rem 0.95rem; margin-bottom: 0.6rem;">'
        f"<strong>{html.escape(str(kart.get('name') or ''))}</strong>"
        f"<div>{html.escape(str(kart.get('class_name') or ''))}</div>"
        f"<div>{html.escape(str(kart.get('reason') or ''))}</div>"
        "</div>"
    )


def bayrak_stili(deger: object, bayrak_evet: str) -> str:
    """Bayraklı hücre amber. Kırmızı yok."""
    if bayrak_evet and str(deger) == bayrak_evet:
        return f"background-color: {AMBER_BG}; color: {AMBER_TEXT}; font-weight: 600"
    return ""


def risk_tablosu(
    rows: Sequence[Mapping],
    basliklar: Mapping[str, str],
    bayrak_evet: str,
) -> pd.DataFrame:
    """Bayraklı öğrenciler üstte. Gerekçe tabloda yok; not ortalaması sayıdır."""
    kayitlar = []
    for row in _risk_sirala(rows):
        not_sirasi = row.get("grade_rank")
        devam_sirasi = row.get("absence_rank")
        ad = row.get("name")
        kayitlar.append(
            {
                basliklar["student"]: "" if ad is None else str(ad),
                basliklar["class_name"]: str(row.get("class_name") or ""),
                basliklar["grade_average"]: _sayi(row.get("grade_average")),
                basliklar["absences"]: int(row.get("unexcused_absences") or 0),
                basliklar["grade_rank"]: "" if not_sirasi is None else str(not_sirasi),
                basliklar["absence_rank"]: "" if devam_sirasi is None else str(devam_sirasi),
                basliklar["flag"]: bayrak_evet if row.get("flagged") else "",
            }
        )
    kolonlar = [basliklar[alan] for alan in _RISK_ALANLARI]
    tablo = pd.DataFrame(kayitlar, columns=kolonlar)
    tablo[basliklar["grade_average"]] = pd.to_numeric(
        tablo[basliklar["grade_average"]], errors="coerce"
    )
    return tablo


def risk_stili(df: pd.DataFrame, bayrak_sutunu: str, bayrak_evet: str):
    """Bayrak sütunundaki dikkat rozetini amber boyar."""
    if df.empty or bayrak_sutunu not in df.columns:
        return df.style

    def boya(sutun):
        return [bayrak_stili(deger, bayrak_evet) for deger in sutun]

    return df.style.apply(boya, subset=[bayrak_sutunu])
