"""Doğal dil sorusunu RLS oturumunda, üretilen SQL'i değiştirmeden çalıştırır."""

import logging
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text

from backend.app.api.dependencies import get_current_user, get_db_with_context
from backend.app.core.sql_safety import validate_select_only
from backend.app.models import User
from backend.app.services.llm_service import translate_question_to_sql

logger = logging.getLogger("uvicorn.error")

router = APIRouter(tags=["query"])

_YOGUNLUK_MESAJI = "Şu anda yoğunluk var, lütfen tekrar deneyin"
_SATIR_LIMITI = 500


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    question: str
    row_count: int
    results: list[dict]


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


@router.post("/query", response_model=QueryResponse)
def run_query(
    body: QueryRequest,
    current_user: User = Depends(get_current_user),
) -> QueryResponse:
    """Kimlik, SQL üretimi, doğrulama, sonra RLS bağlamında olduğu gibi çalıştırma."""
    question = body.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Soru metni boş olamaz",
        )

    try:
        sql = translate_question_to_sql(question)
    except Exception as exc:
        if _yogunluk_hatasi(exc):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=_YOGUNLUK_MESAJI,
            ) from exc
        raise

    try:
        validate_select_only(sql)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    logger.info("Üretilen SQL: %s", sql)

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
        return QueryResponse(
            question=body.question,
            row_count=len(results),
            results=results,
        )
    finally:
        oturum.close()
