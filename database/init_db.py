"""
Yapılandırılmış PostgreSQL veritabanında tüm tabloları oluşturur.

Süper kullanıcı bağlantısını (DATABASE_URL) kullanır. Proje kökünden:
    python database/init_db.py
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.core.database import Base, engine
import backend.app.models  # noqa: F401 — modelleri Base.metadata'ya kaydet


def init_db() -> None:
    """User, Student, Teacher, Grade ve Attendance tablolarını oluşturur."""
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    print(f"Using database: {engine.url}")
    init_db()
    tables = sorted(Base.metadata.tables.keys())
    print(f"Created {len(tables)} tables: {', '.join(tables)}")
