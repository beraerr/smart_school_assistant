"""FastAPI bağımlılıkları — Bearer JWT ve RLS oturum bağlamı."""

from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.core.database import AppSessionLocal, get_db
from backend.app.core.security import decode_access_token
from backend.app.models import User, UserRole

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Authorization header'daki JWT'den kullanıcıyı yükler."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kimlik doğrulama başarısız",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(credentials.credentials)
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception from None

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


def _sql_literal(value: str) -> str:
    """SET LOCAL için tek tırnaklı sabit üretir (parametre kabul etmez)."""
    return "'" + value.replace("'", "''") + "'"


def _role_setting(user: User) -> str:
    """RLS politikasının beklediği küçük harf rol adı (principal, teacher, ...)."""
    role = user.role
    if isinstance(role, UserRole):
        return role.value
    return str(role).lower()


def apply_rls_context(db: Session, current_user: User) -> None:
    """Açık transaction içinde Hafta 1 politikalarının okuduğu GUC'leri kurar.

    SET LOCAL transaction bitince silinir; bu yüzden burada commit edilmez.
    PostgreSQL SET komutu bağlı parametre kabul etmediği için değerler
    kaçışlı sabit olarak yazılır.
    """
    role = _role_setting(current_user)
    class_name = current_user.related_class or ""
    student_id = "" if current_user.related_id is None else str(current_user.related_id)

    # Bağlantıyı bu transaction'a sabitle; sonraki SELECT aynı transaction'da kalsın.
    db.connection()
    db.execute(text(f"SET LOCAL app.role = {_sql_literal(role)}"))
    db.execute(text(f"SET LOCAL app.class = {_sql_literal(class_name)}"))
    db.execute(text(f"SET LOCAL app.student_id = {_sql_literal(student_id)}"))


def get_db_with_context(
    current_user: User = Depends(get_current_user),
) -> Generator[Session, None, None]:
    """school_app oturumu açar ve kimliği doğrulanmış kullanıcının RLS bağlamını kurar."""
    db = AppSessionLocal()
    try:
        apply_rls_context(db, current_user)
        yield db
    finally:
        db.close()
