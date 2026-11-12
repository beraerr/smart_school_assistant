"""Doğal dil sorusunu RLS oturumunda, üretilen SQL'i değiştirmeden çalıştırır."""

import math
import time
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text

from backend.app.api.dependencies import get_current_user, get_db_with_context
from backend.app.core.logging_config import log_query
from backend.app.core.rate_limiter import limiter
from backend.app.core.sql_safety import validate_select_only
from backend.app.models import User, UserRole
from backend.app.services.explain_service import build_explanation
from backend.app.services.intent_service import detect_intent
from backend.app.services.llm_service import translate_question_to_sql

router = APIRouter(tags=["query"])

_YOGUNLUK_MESAJI = "Şu anda yoğunluk var, lütfen tekrar deneyin"
_SATIR_LIMITI = 500
_DESTEKLENMEYEN = "NOT_SUPPORTED_COMPARISON"
_GENEL_RED = "Sorgu oluşturulamadı"

_SOHBET = {
    "tr": "Merhaba. Okul kayıtları hakkında bir sorunuz olursa yardımcı olabilirim.",
    "en": "Hello. I can help if you have a question about school records.",
}

_GIZLILIK = {
    "tr": (
        "Bu soru başka öğrencilerle karşılaştırma gerektiriyor. "
        "Veli/öğrenci hesabınız yalnızca kendi kaydınıza erişebildiği için "
        "bu karşılaştırma yapılamıyor."
    ),
    "en": (
        "This question requires comparison with other students. "
        "A parent or student account can access only its own record, "
        "so this comparison cannot be made."
    ),
}


class QueryRequest(BaseModel):
    question: str
    lang: Literal["tr", "en"] = "tr"


class QueryResponse(BaseModel):
    question: str
    row_count: int
    results: list[dict]
    explanation: str


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


@router.post("/query", response_model=QueryResponse)
def run_query(
    body: QueryRequest,
    current_user: User = Depends(get_current_user),
) -> QueryResponse:
    """Hız sınırı, niyet, SQL üretimi ve RLS altında çalıştırma."""
    role = _rol(current_user)
    baglam: dict[str, object] = {
        "intent": None,
        "row_count": 0,
        "llm_ms": 0,
        "db_ms": 0,
        "rate_limited": False,
        "sql": None,
    }

    def _sure(basla: float) -> int:
        return int(round((time.perf_counter() - basla) * 1000))

    def _llm(fn):
        basla = time.perf_counter()
        try:
            return fn()
        except Exception as exc:
            if _yogunluk_hatasi(exc):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=_YOGUNLUK_MESAJI,
                ) from exc
            raise
        finally:
            baglam["llm_ms"] = int(baglam["llm_ms"]) + _sure(basla)

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
        intent = _llm(lambda: detect_intent(question))
        baglam["intent"] = intent

        if intent == "chat":
            return QueryResponse(
                question=body.question,
                row_count=0,
                results=[],
                explanation=_SOHBET[dil],
            )

        hata: str | None = None
        sql = ""
        for deneme in range(2):

            def _uret(bildirilen: str | None = hata) -> str:
                return translate_question_to_sql(
                    question,
                    role,
                    validation_error=bildirilen,
                )

            sql = _llm(_uret)
            baglam["sql"] = sql
            if sql.strip() == _DESTEKLENMEYEN:
                return QueryResponse(
                    question=body.question,
                    row_count=0,
                    results=[],
                    explanation=_GIZLILIK[dil],
                )
            try:
                validate_select_only(sql)
            except ValueError as exc:
                hata = str(exc)
                if deneme == 0:
                    continue
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=_GENEL_RED,
                ) from exc
            break

        basla_db = time.perf_counter()
        oturum = get_db_with_context(current_user)
        db = next(oturum)
        try:
            db.execute(text("SELECT set_config('statement_timeout', '5000', true)"))
            sonuc = db.execute(text(sql))
            satirlar = sonuc.mappings().fetchmany(_SATIR_LIMITI)
            results = [
                {anahtar: _hucre(deger) for anahtar, deger in satir.items()}
                for satir in satirlar
            ]
        finally:
            baglam["db_ms"] = _sure(basla_db)
            oturum.close()

        baglam["row_count"] = len(results)
        return QueryResponse(
            question=body.question,
            row_count=len(results),
            results=results,
            explanation=build_explanation(role, current_user.related_class, dil),
        )
    finally:
        log_query(
            event="query",
            user=current_user.username,
            role=role,
            intent=baglam["intent"] if isinstance(baglam["intent"], str) else None,
            row_count=int(baglam["row_count"]),
            llm_ms=int(baglam["llm_ms"]),
            db_ms=int(baglam["db_ms"]),
            rate_limited=bool(baglam["rate_limited"]),
            sql=baglam["sql"] if isinstance(baglam["sql"], str) else None,
        )
