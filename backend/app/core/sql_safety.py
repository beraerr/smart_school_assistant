"""Üretilen SQL'i çalıştırmadan önce doğrular. FastAPI'ye bağlı değildir."""

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError, SqlglotError

_IZINLI_TABLOLAR = frozenset({"students", "grades", "attendance"})

# FROM içindeki tablo fonksiyonları. Genel fonksiyon izin listesi Hafta 7'de.
ALLOWED_TABLE_FUNCTIONS = {"student_rank"}


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


def _tablo_referanslarini_denetle(ifade: exp.Expression) -> None:
    """Ağaçtaki her tablo referansı izinli üç tablodan biri olmalı.

    FROM içindeki tablo fonksiyonlarından yalnız student_rank kabul edilir.
    SELECT listesindeki diğer fonksiyon çağrılarına dokunulmaz.
    """
    takma_adlar: set[str] = set()
    for tablo in ifade.find_all(exp.Table):
        fonksiyon = _tablo_fonksiyon_adi(tablo)
        if fonksiyon is not None:
            if fonksiyon not in ALLOWED_TABLE_FUNCTIONS:
                raise ValueError(f"İzin verilmeyen tablo: {fonksiyon}")
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
