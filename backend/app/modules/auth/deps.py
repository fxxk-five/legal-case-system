from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.client_source import is_mini_program_request
from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.roles import is_super_admin_role, is_tenant_admin_role, normalize_role
from app.core.security import ACCESS_TOKEN_TYPE
from app.core.statuses import is_active_user_status
from app.db.session import get_db, set_current_tenant_context
from app.models.auth_session import AuthSession
from app.models.user import User
from app.schemas.auth import TokenPayload


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def _auth_required(message: str = "Authentication is required.") -> AppError:
    return AppError(
        status_code=status.HTTP_401_UNAUTHORIZED,
        code=ErrorCode.AUTH_REQUIRED,
        message=message,
        detail=message,
    )


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(
            sub=payload.get("sub"),
            tenant_id=payload.get("tenant_id"),
            role=payload.get("role"),
            is_tenant_admin=payload.get("is_tenant_admin"),
            token_type=payload.get("token_type"),
            sid=payload.get("sid"),
        )
    except JWTError as exc:
        raise _auth_required() from exc

    if token_data.sub is None:
        raise _auth_required()
    if token_data.token_type != ACCESS_TOKEN_TYPE:
        raise _auth_required("Access token is invalid.")

    user = db.query(User).filter(User.id == int(token_data.sub)).first()
    if user is None:
        raise _auth_required("User does not exist or is no longer valid.")
    if not is_active_user_status(user.status):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.FORBIDDEN,
            message="Current account is not active.",
            detail="Current account is not active.",
        )
    if token_data.tenant_id is not None and user.tenant_id != token_data.tenant_id:
        raise _auth_required("Tenant authentication failed.")

    session_id = token_data.sid
    if session_id is None:
        if settings.IS_PRODUCTION:
            raise _auth_required("Session-bound access token is required.")
    else:
        auth_session = (
            db.query(AuthSession)
            .filter(
                AuthSession.id == int(session_id),
                AuthSession.user_id == user.id,
                AuthSession.tenant_id == user.tenant_id,
            )
            .first()
        )
        if auth_session is None or auth_session.is_revoked:
            raise _auth_required("Login session has expired.")
        expires_at = _as_utc(auth_session.expires_at)
        if expires_at is None or expires_at <= datetime.now(timezone.utc):
            raise _auth_required("Login session has expired.")
        setattr(user, "_auth_session_id", auth_session.id)

    user.role = normalize_role(user.role)
    set_current_tenant_context(
        db,
        user.tenant_id,
        is_super_admin=is_super_admin_role(user.role),
    )
    return user


def require_tenant_admin(current_user: User = Depends(get_current_user)) -> User:
    if not is_tenant_admin_role(current_user.role, is_tenant_admin=current_user.is_tenant_admin):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.FORBIDDEN,
            message="Tenant admin permission is required.",
            detail="Tenant admin permission is required.",
        )
    return current_user


def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    if not is_super_admin_role(current_user.role):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.FORBIDDEN,
            message="Super admin permission is required.",
            detail="Super admin permission is required.",
        )
    return current_user


def require_mini_program_source(request: Request) -> None:
    if not is_mini_program_request(request):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.FORBIDDEN,
            message="This endpoint only accepts mini program traffic.",
            detail="This endpoint only accepts mini program traffic.",
        )


def require_client_mini_program_source(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> None:
    if current_user.role == "client" and not is_mini_program_request(request):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.FORBIDDEN,
            message="Client access is restricted to the mini program.",
            detail="Client access is restricted to the mini program.",
        )
