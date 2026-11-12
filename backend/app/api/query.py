"""Konuşmalı /query: araç çağrısı RLS, doğrulama ve satır sınırı altında kalır."""

import math
import time
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user, get_db_with_context
from backend.app.core.access_context import set_access_context
from backend.app.core.logging_config import log_query, query_logger
from backend.app.core.rate_limiter import limiter
from backend.app.core.sql_safety import aggregates_without_rank, validate_select_only
from backend.app.models import User, UserRole
from backend.app.services.assistant_service import run_assistant
from backend.app.services.explain_service import build_explanation
from config.settings import settings

router = APIRouter(tags=["query"])

_YOGUNLUK_MESAJI = "Şu anda yoğunluk var, lütfen tekrar deneyin"
_SATIR_LIMITI = 500
_GECMIS_OGESI = 6
_GECMIS_UZUNLUK = 600
_ROLLER = frozenset({"user", "assistant"})
_TEK_KAYIT = frozenset({"parent", "student"})
KAPSAM_UYARISI = (
    "Bu sonuç yalnızca çocuğun kendi kayıtlarından hesaplandı; sınıf veya okul "
    "geneli DEĞİLDİR. Sınıf/okul bilgisi için student_rank kullan."
)


class HistoryItem(BaseModel):
    role: str = ""
    content: str = ""


class QueryRequest(BaseModel):
    question: str
    history: list[HistoryItem] = Field(default_factory=list)
    lang: Literal["tr", "en"] = "tr"


class QueryResponse(BaseModel):
    answer: str
    row_count: int
    results: list[dict]
    explanation: str
    sql: list[str] | None = None


def _model_istemcisi():
    import anthropic

    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _yogunluk_hatasi(exc: BaseException) -> bool:
    """529 veya overloaded yanıtı."""
    if getattr(exc, "status_code", None) == 529:
        return True
    if type(exc).__name__ == "OverloadedError":
        return True
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict) and error.get("type") == "overloaded_error":
            return True
    return "overloaded" in str(exc).lower()


def _hucre(deger: object) -> object:
    if isinstance(deger, datetime):
        return deger.isoformat()
    if isinstance(deger, date):
        return deger.isoformat()
    if isinstance(deger, Decimal):
        return float(deger)
    return deger


def _rol(user: User) -> str:
    role = user.role
    if isinstance(role, UserRole):
        return role.value
    return str(role).lower()


def _dil(lang: str) -> str:
    return "en" if lang == "en" else "tr"


def _gecmis(ogeler: list[HistoryItem]) -> list[dict]:
    """Geçmiş güvenilmez girdidir: son 6 öğe, 600 karakter, yalnız iki rol."""
    temiz: list[dict] = []
    for oge in ogeler:
        if oge.role not in _ROLLER:
            continue
        temiz.append({"role": oge.role, "content": oge.content[:_GECMIS_UZUNLUK]})
    return temiz[-_GECMIS_OGESI:]


def _zaman_asimi(db: Session) -> None:
    db.execute(text("SELECT set_config('statement_timeout', '5000', true)"))


def _db_hatasi_logla(sql: str, exc: BaseException) -> None:
    """Veritabanı hata metnini sunucu loguna yazar. Modele ve kullanıcıya gitmez."""
    import json

    metin = str(getattr(exc, "orig", None) or exc).replace("\n", " ")
    query_logger.error(
        json.dumps(
            {"event": "query_db_error", "sql": sql, "error": metin},
            ensure_ascii=False,
        )
    )


@router.post(
    "/query",
    response_model=QueryResponse,
    response_model_exclude_none=True,
)
def run_query(
    body: QueryRequest,
    current_user: User = Depends(get_current_user),
) -> QueryResponse:
    """Hız sınırı soru başınadır. Yetki JWT ve RLS oturumundan gelir."""
    role = _rol(current_user)
    baglam: dict[str, object] = {
        "row_count": 0,
        "llm_calls": 0,
        "tool_calls": 0,
        "llm_ms": 0,
        "db_ms": 0,
        "rate_limited": False,
        "sql": None,
    }

    def _sure(basla: float) -> int:
        return int(round((time.perf_counter() - basla) * 1000))

    oturum = None
    db: Session | None = None
    try:
        izin, bekle = limiter.allow(current_user.username)
        if not izin:
            baglam["rate_limited"] = True
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Çok fazla istek",
                headers={"Retry-After": str(max(1, math.ceil(bekle)))},
            )

        question = body.question.strip()
        if not question:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Soru metni boş olamaz",
            )

        dil = _dil(body.lang)

        def run_sql(sql: str) -> dict:
            nonlocal oturum, db
            try:
                validate_select_only(sql)
            except ValueError:
                return {"ok": False}
            if db is None:
                oturum = get_db_with_context(current_user)
                db = next(oturum)
            basla_db = time.perf_counter()
            try:
                _zaman_asimi(db)
                sonuc = db.execute(text(sql))
                satirlar = sonuc.mappings().fetchmany(_SATIR_LIMITI)
                rows = [
                    {anahtar: _hucre(deger) for anahtar, deger in satir.items()}
                    for satir in satirlar
                ]
            except DBAPIError as exc:
                baglam["db_ms"] = int(baglam["db_ms"]) + _sure(basla_db)
                _db_hatasi_logla(sql, exc)
                db.rollback()
                set_access_context(
                    db,
                    role,
                    current_user.related_class,
                    current_user.related_id,
                )
                _zaman_asimi(db)
                return {"ok": False}
            baglam["db_ms"] = int(baglam["db_ms"]) + _sure(basla_db)
            sonuc_govdesi: dict = {
                "ok": True,
                "rows": rows,
                "row_count": len(rows),
                "truncated": len(rows) >= _SATIR_LIMITI,
            }
            if role in _TEK_KAYIT and aggregates_without_rank(sql):
                sonuc_govdesi["scope_warning"] = KAPSAM_UYARISI
            return sonuc_govdesi

        try:
            asistan = run_assistant(
                [*_gecmis(body.history), {"role": "user", "content": question}],
                role,
                dil,
                client=_model_istemcisi(),
                run_sql=run_sql,
            )
        except Exception as exc:
            if _yogunluk_hatasi(exc):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=_YOGUNLUK_MESAJI,
                ) from exc
            raise

        baglam["row_count"] = asistan.row_count
        baglam["llm_calls"] = asistan.llm_calls
        baglam["tool_calls"] = asistan.tool_calls
        baglam["llm_ms"] = asistan.llm_ms
        baglam["sql"] = asistan.sql
        return QueryResponse(
            answer=asistan.answer,
            row_count=asistan.row_count,
            results=asistan.results,
            explanation=build_explanation(role, current_user.related_class, dil),
            sql=asistan.sql if settings.SHOW_SQL and asistan.sql else None,
        )
    finally:
        if oturum is not None:
            oturum.close()
        sql_kaydi = baglam["sql"] if isinstance(baglam["sql"], list) and baglam["sql"] else None
        log_query(
            event="query",
            user=current_user.username,
            role=role,
            row_count=int(baglam["row_count"]),
            llm_calls=int(baglam["llm_calls"]),
            tool_calls=int(baglam["tool_calls"]),
            llm_ms=int(baglam["llm_ms"]),
            db_ms=int(baglam["db_ms"]),
            rate_limited=bool(baglam["rate_limited"]),
            sql=sql_kaydi,
        )
