"""FastAPI uygulama giriş noktası — Hafta 2: login, sağlık ve RLS bağlamı."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.auth import router as auth_router
from backend.app.api.debug import router as debug_router

app = FastAPI(
    title="Akıllı Okul Bilgi Sistemi",
    description="Hafta 2 — JWT kimlik doğrulama ve PostgreSQL RLS oturum bağlamı",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(debug_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Sunucu ayakta mı — basit sağlık kontrolü."""
    return {"status": "ok"}
