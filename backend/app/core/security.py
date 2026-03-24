from datetime import datetime, timedelta, timezone
import hashlib
from typing import Any
from uuid import uuid4

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def _create_token(
    subject: str | Any,
    *,
    token_type: str,
    expires_delta: timedelta,
    extra_data: dict[str, Any] | None = None,
) -> str:
    issued_at = datetime.now(timezone.utc)
    expire = issued_at + expires_delta
    to_encode: dict[str, Any] = {
        "exp": expire,
        "iat": issued_at,
        "jti": uuid4().hex,
        "sub": str(subject),
        "token_type": token_type,
    }
    if extra_data:
        to_encode.update(extra_data)
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
    extra_data: dict[str, Any] | None = None,
) -> str:
    return _create_token(
        subject,
        token_type=ACCESS_TOKEN_TYPE,
        expires_delta=expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_data=extra_data,
    )


def create_refresh_token(
    subject: str | Any,
    *,
    session_id: int,
    expires_delta: timedelta | None = None,
    extra_data: dict[str, Any] | None = None,
) -> str:
    payload = {"sid": session_id}
    if extra_data:
        payload.update(extra_data)
    return _create_token(
        subject,
        token_type=REFRESH_TOKEN_TYPE,
        expires_delta=expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        extra_data=payload,
    )


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
