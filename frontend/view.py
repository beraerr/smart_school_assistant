"""Sorgu tablosunu derse göre sütunlara çevirir."""

import pandas as pd


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
