"""SQLAlchemy engine, session factory, declarative base ve FastAPI oturum bağımlılıkları.

İki ayrı bağlantı vardır:
- ``engine`` / ``get_db``: postgres süper kullanıcısı. Şema kurulumu, seed ve login
  okuması bunu kullanır; süper kullanıcı RLS'i bypass eder.
- ``app_engine`` / ``get_app_db``: ``school_app`` rolü. API'nin veri okuduğu
  bağlantı budur; NOSUPERUSER ve NOBYPASSRLS olduğu için Hafta 1 politikaları geçerlidir.
"""

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from config.settings import settings


def with_psycopg2_driver(database_url: str):
    """Sürücüsüz ``postgresql://`` adresini psycopg2'ye çevirir."""
    url = make_url(database_url)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg2")
    return url


def _make_engine(database_url: str):
    return create_engine(
        with_psycopg2_driver(database_url),
        echo=os.getenv("SQL_ECHO", "").lower() in ("1", "true", "yes"),
    )


engine = _make_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app_engine = _make_engine(settings.APP_DATABASE_URL)
AppSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=app_engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Süper kullanıcı oturumu — login ve yönetim betikleri için."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_app_db() -> Generator[Session, None, None]:
    """school_app oturumu — RLS bu bağlantıda uygulanır."""
    db = AppSessionLocal()
    try:
        yield db
    finally:
        db.close()
