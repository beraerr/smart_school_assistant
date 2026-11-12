"""FastAPI uygulama giriş noktası."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.auth import router as auth_router
from backend.app.api.query import router as query_router

app = FastAPI(
    title="Akıllı Okul Bilgi Sistemi",
    description="Kimlik doğrulama, doğal dil sorgusu ve PostgreSQL RLS",
    version="0.4.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(query_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Sunucu ayakta mı — basit sağlık kontrolü."""
    return {"status": "ok"}
