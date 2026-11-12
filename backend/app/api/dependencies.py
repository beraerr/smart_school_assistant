"""FastAPI bağımlılıkları — Bearer JWT ve RLS oturum bağlamı."""

from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.app.core.access_context import set_access_context
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


def _role_setting(user: User) -> str:
    """RLS politikasının beklediği küçük harf rol adı (principal, teacher, ...)."""
    role = user.role
    if isinstance(role, UserRole):
        return role.value
    return str(role).lower()


def get_db_with_context(
    current_user: User = Depends(get_current_user),
) -> Generator[Session, None, None]:
    """school_app oturumu açar ve kimliği doğrulanmış kullanıcının RLS bağlamını kurar.

    Bağlam yalnızca bu transaction için kurulur; istek bitince commit edilmez.
    """
    db = AppSessionLocal()
    try:
        # Bağlantıyı bu transaction'a sabitle; sonraki SELECT aynı transaction'da kalsın.
        db.connection()
        set_access_context(
            db,
            _role_setting(current_user),
            current_user.related_class,
            current_user.related_id,
        )
        yield db
    finally:
        db.close()
