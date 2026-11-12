"""Üretilen SQL'i çalıştırmadan önce doğrular. FastAPI'ye bağlı değildir."""

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError, SqlglotError

_IZINLI_TABLOLAR = frozenset({"students", "grades", "attendance"})

# FROM içindeki tablo fonksiyonları. Skaler çağrı olarak serbest değildir.
ALLOWED_TABLE_FUNCTIONS = {"student_rank", "class_teacher"}

# Ayrıştırma ağacındaki diğer fonksiyon çağrıları. Listede olmayan her ad reddedilir.
_IZINLI_FONKSIYONLAR = frozenset(
    {
        "count",
        "sum",
        "avg",
        "min",
        "max",
        "round",
        "lower",
        "upper",
        "coalesce",
        "extract",
        "date_trunc",
        "now",
        "current_date",
        "rank",
        "dense_rank",
        "row_number",
    }
)

# sqlglot sınıf adı -> listedeki fonksiyon adı. NOW() CurrentTimestamp olur.
_SINIF_ADLARI = {
    "count": "count",
    "sum": "sum",
    "avg": "avg",
    "min": "min",
    "max": "max",
    "round": "round",
    "lower": "lower",
    "upper": "upper",
    "coalesce": "coalesce",
    "extract": "extract",
    "timestampttrunc": "date_trunc",
    "timestamptrunc": "date_trunc",
    "datetrunc": "date_trunc",
    "currenttimestamp": "now",
    "currentdate": "current_date",
    "rank": "rank",
    "denserank": "dense_rank",
    "rownumber": "row_number",
}


def _ifadeler(sql: str) -> list[exp.Expression]:
    try:
        ayrismis = sqlglot.parse(sql, read="postgres")
    except (ParseError, SqlglotError) as exc:
        raise ValueError("SQL ayrıştırılamadı") from exc
    return [ifade for ifade in ayrismis if ifade is not None]


def _tablo_fonksiyon_adi(tablo: exp.Table) -> str | None:
    """FROM öğesi fonksiyon çağrısıysa adını döndürür."""
    kaynak = tablo.this
    if isinstance(kaynak, exp.Identifier):
        return None
    if isinstance(kaynak, exp.Func):
        return (kaynak.name or "").lower()
    return None


def _fonksiyon_adi(dugum: exp.Func) -> str:
    if isinstance(dugum, exp.Anonymous):
        return (dugum.name or "").lower()
    sinif = type(dugum).__name__.lower()
    return _SINIF_ADLARI.get(sinif, sinif)


def _fonksiyonlari_denetle(ifade: exp.Expression, tablo_cagrilari: set[int]) -> None:
    """Her fonksiyon çağrısı izin listesinde olmalı. Tür dönüşümü çağrı sayılmaz."""
    for dugum in ifade.find_all(exp.Func):
        if isinstance(dugum, exp.Cast):
            continue
        if id(dugum) in tablo_cagrilari:
            continue
        ad = _fonksiyon_adi(dugum)
        if ad not in _IZINLI_FONKSIYONLAR:
            raise ValueError(f"İzin verilmeyen fonksiyon: {ad}")


def _tablo_referanslarini_denetle(ifade: exp.Expression) -> None:
    """Ağaçtaki her tablo referansı izinli üç tablodan biri olmalı.

    FROM içindeki tablo fonksiyonlarından yalnız student_rank ve class_teacher kabul edilir.
    """
    takma_adlar: set[str] = set()
    tablo_cagrilari: set[int] = set()
    for tablo in ifade.find_all(exp.Table):
        fonksiyon = _tablo_fonksiyon_adi(tablo)
        if fonksiyon is not None:
            if fonksiyon not in ALLOWED_TABLE_FUNCTIONS:
                raise ValueError(f"İzin verilmeyen tablo: {fonksiyon}")
            if isinstance(tablo.this, exp.Func):
                tablo_cagrilari.add(id(tablo.this))
            takma_adlar.add(fonksiyon)
            if tablo.alias:
                takma_adlar.add(tablo.alias.lower())
            continue
        ad = tablo.name.lower()
        if ad not in _IZINLI_TABLOLAR:
            raise ValueError(f"İzin verilmeyen tablo: {ad}")
        if tablo.alias:
            takma_adlar.add(tablo.alias.lower())

    for alt_sorgu in ifade.find_all(exp.Subquery):
        if alt_sorgu.alias:
            takma_adlar.add(alt_sorgu.alias.lower())

    for sutun in ifade.find_all(exp.Column):
        niteleyici = (sutun.table or "").lower()
        if not niteleyici:
            continue
        if niteleyici in _IZINLI_TABLOLAR or niteleyici in takma_adlar:
            continue
        raise ValueError(f"İzin verilmeyen tablo: {niteleyici}")

    _fonksiyonlari_denetle(ifade, tablo_cagrilari)


_TOPLAMA = (exp.Avg, exp.Count, exp.Sum, exp.Min, exp.Max)


def aggregates_without_rank(sql: str) -> bool:
    """SQL toplama fonksiyonu içeriyor ve student_rank kullanmıyorsa True."""
    try:
        ifadeler = _ifadeler(sql)
    except ValueError:
        return False
    toplama = False
    for ifade in ifadeler:
        for tablo in ifade.find_all(exp.Table):
            if _tablo_fonksiyon_adi(tablo) == "student_rank":
                return False
        if any(True for _ in ifade.find_all(*_TOPLAMA)):
            toplama = True
    return toplama


def validate_select_only(sql: str) -> None:
    """Tek bir SELECT ve yalnızca izinli tablolar varsa None döner; değilse ValueError."""
    if not sql or not sql.strip():
        raise ValueError("Boş SQL ifadesi kabul edilmez")

    ifadeler = _ifadeler(sql)
    if len(ifadeler) != 1:
        raise ValueError("Tam olarak bir SQL ifadesi olmalı")

    ifade = ifadeler[0]
    if not isinstance(ifade, exp.Select):
        raise ValueError("Yalnızca SELECT ifadesine izin verilir")

    _tablo_referanslarini_denetle(ifade)
