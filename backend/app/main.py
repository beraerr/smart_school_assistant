"""FastAPI uygulama giriş noktası."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.auth import router as auth_router
from backend.app.api.query import router as query_router
from backend.app.api.risk import router as risk_router
from backend.app.core.logging_config import configure_logging
from backend.app.services.schema_context import build_schema_context
from config.settings import settings

configure_logging()
try:
    build_schema_context()
except Exception:
    pass

app = FastAPI(
    title="Akıllı Okul Bilgi Sistemi",
    description="Kimlik doğrulama, doğal dil sorgusu ve PostgreSQL RLS",
    version="0.4.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(query_router)
app.include_router(risk_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Sunucu ayakta mı — basit sağlık kontrolü."""
    return {"status": "ok"}
