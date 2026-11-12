"""Ardışık isteklerde SET LOCAL bağlamının bir sonraki oturuma sızmadığını kanıtlar."""

import sys
from pathlib import Path

from sqlalchemy import text

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.core.access_context import set_access_context
from backend.app.core.database import SessionLocal, get_app_db
from backend.app.models import User, UserRole
from backend.tests import mock_veri


def _hesap_baglami(username: str) -> tuple[str, str | None, int | None]:
    """Seed hesabının rol, sınıf ve related_id değerlerini okur."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).one()
        role = user.role.value if isinstance(user.role, UserRole) else str(user.role)
        return role, user.related_class, user.related_id
    finally:
        db.close()


def _istekte_ogrenci_sayisi(username: str) -> int:
    """Ayrı bir get_app_db oturumunda hesabın bağlamıyla öğrenci sayar."""
    role, related_class, related_id = _hesap_baglami(username)
    uretec = get_app_db()
    db = next(uretec)
    try:
        db.connection()
        set_access_context(db, role, related_class, related_id)
        return db.execute(text("SELECT COUNT(*) FROM students")).scalar_one()
    finally:
        uretec.close()


def test_teacher_sonrasi_principal_baglami_sizmaz() -> None:
    """teacher1 kendi sınıfını görür; sonraki principal oturumu bütün okulu görür.

    İkinci oturum kendi bağlamını kurmadan önce app.role ve app.today boş olmalıdır.
    Önceki transaction'daki ayar havuzdaki bağlantıya taşınmaz.
    """
    teacher_sayisi = _istekte_ogrenci_sayisi("teacher1")
    assert teacher_sayisi == mock_veri.ogrenci_sayisi("9-A")

    uretec = get_app_db()
    db = next(uretec)
    try:
        db.connection()
        sizinti = db.execute(text("SELECT current_setting('app.role', true)")).scalar_one()
        assert sizinti in (None, "")
        bugun_sizinti = db.execute(
            text("SELECT current_setting('app.today', true)")
        ).scalar_one()
        assert bugun_sizinti in (None, "")

        role, related_class, related_id = _hesap_baglami("principal")
        set_access_context(db, role, related_class, related_id)
        principal_sayisi = db.execute(text("SELECT COUNT(*) FROM students")).scalar_one()
        assert principal_sayisi == mock_veri.ogrenci_sayisi()
    finally:
        uretec.close()
