"""Kimlik doğrulama uç noktaları."""

import math
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.rate_limiter import login_failure_limiter
from backend.app.core.security import create_access_token, verify_password
from backend.app.models import User
from config.settings import settings

# Var olmayan kullanıcıda da bir bcrypt karşılaştırması yapılsın.
_BILINMEYEN_HASH = "$2b$12$UY38de1rpiSNYlc4PzDYEeqX5wi.vJBvtv2aqff4jq10SOANWxyTW"
_YANLIS_GIRIS = "Kullanıcı adı veya parola hatalı"

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    related_id: int | None = None
    related_class: str | None = None

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    """Kullanıcı adı ve parola ile giriş; başarılıysa JWT döner."""
    engelli, bekle = login_failure_limiter.blocked_for(body.username)
    if engelli:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Çok fazla deneme",
            headers={"Retry-After": str(max(1, math.ceil(bekle)))},
        )

    user = db.query(User).filter(User.username == body.username).first()
    kayitli_hash = user.password_hash if user is not None else _BILINMEYEN_HASH
    parola_dogru = verify_password(body.password, kayitli_hash)
    if user is None or not parola_dogru:
        login_failure_limiter.allow(body.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_YANLIS_GIRIS,
            headers={"WWW-Authenticate": "Bearer"},
        )

    role_value = user.role.value if hasattr(user.role, "value") else str(user.role)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "role": role_value,
            "related_id": user.related_id,
            "related_class": user.related_class,
        },
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return LoginResponse(
        access_token=access_token,
        user=UserOut(
            id=user.id,
            username=user.username,
            role=role_value,
            related_id=user.related_id,
            related_class=user.related_class,
        ),
    )
