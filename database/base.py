import os

from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import declarative_base, sessionmaker

from config.settings import DATABASE_URL


def with_psycopg2_driver(database_url: str):
    """Use psycopg2 when the URL does not name a driver.

    SQLAlchemy 2.1 treats a bare ``postgresql://`` URL as psycopg 3. This
    project depends on psycopg2-binary.
    """
    url = make_url(database_url)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg2")
    return url


engine = create_engine(
    with_psycopg2_driver(DATABASE_URL),
    echo=os.getenv("SQL_ECHO", "").lower() in ("1", "true", "yes"),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
