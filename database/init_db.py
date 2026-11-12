"""
Create all Week 1 tables on the configured PostgreSQL database.

Run from the week-01 project root:
    python database/init_db.py
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from database.base import Base, engine
import database.models  # noqa: F401 — register models on Base.metadata


def init_db() -> None:
    """Create tables for User, Student, Teacher, Grade, and Attendance."""
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    print(f"Using database: {engine.url}")
    init_db()
    tables = sorted(Base.metadata.tables.keys())
    print(f"Created {len(tables)} tables: {', '.join(tables)}")
    