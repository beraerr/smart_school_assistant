"""Geçici RLS kanıt uç noktası.

Hafta 4'te LLM entegrasyonu gelince bu dosya silinecek. Kimlik doğrulama →
oturum bağlamı → PostgreSQL zincirinin uçtan uca çalıştığını göstermek için
yalnızca öğrenci listesini döner; iş kuralı veya sorgu motoru içermez.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_db_with_context

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/students")
def debug_students(db: Session = Depends(get_db_with_context)) -> list[dict]:
    """RLS bağlamı kurulmuş oturumda görünen öğrencileri döner."""
    rows = db.execute(
        text("SELECT id, name, class_name FROM students ORDER BY id")
    ).mappings()
    return [dict(row) for row in rows]
