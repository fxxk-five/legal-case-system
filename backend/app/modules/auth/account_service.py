from __future__ import annotations

from datetime import datetime, timedelta, timezone
from secrets import token_hex

from fastapi import status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.roles import normalize_role
from app.core.security import create_access_token, get_password_hash, verify_password
from app.core.statuses import UserStatus, is_active_user_status
from app.core.validators import enforce_existing_password, enforce_password, enforce_phone
from app.integrations.sms.service import assert_phone_verified
from app.models.auth_session import AuthSession
from app.models.tenant import Tenant
from app.models.user import User
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import PasswordChangeRequest, UserRegister
from app.modules.invites.schemas import InviteRegister
from app.modules.invites.service import InvitesService


def authenticate_user(
    db: Session,
    *,
    phone: str,
    password: str,
    tenant_id: int | None = None,
    allow_pending: bool = False,
) -> User | None:
    phone = enforce_phone(phone)
    enforce_existing_password(password)

    users = AuthRepository(db).list_users_by_phone(
        phone=phone,
        tenant_id=tenant_id,
    )
    matched_users = [user for user in users if verify_password(password, user.password_hash)]
    if not matched_users:
        return None

    if tenant_id is None:
        active_matched = [user for user in matched_users if is_active_user_status(user.status)]
        if len(active_matched) > 1:
            raise ValueError("MULTIPLE_TENANTS_MATCHED")
        if len(active_matched) == 1:
            return active_matched[0]
        if (
            allow_pending
            and len(matched_users) == 1
            and int(matched_users[0].status) == int(UserStatus.PENDING_APPROVAL)
        ):
            return matched_users[0]
        return None

    return matched_users[0]


def create_user(
    db: Session,
    *,
    user_in: UserRegister,
    tenant_id: int,
    role: str = "lawyer",
    is_tenant_admin: bool = False,
    status: int = 1,
    must_reset_password: bool = False,
) -> User:
    repository = AuthRepository(db)
    phone = enforce_phone(user_in.phone)
    password = enforce_password(user_in.password)
    user = User(
        tenant_id=tenant_id,
        phone=phone,
        real_name=user_in.real_name,
        role=normalize_role(role),
        is_tenant_admin=is_tenant_admin,
        must_reset_password=must_reset_password,
        password_hash=get_password_hash(password),
        status=status,
    )
    repository.save_commit_refresh(user)
    return user


def issue_session_bound_access_token(
    db: Session,
    *,
    user: User,
    channel: str = "direct",
    device_type: str | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    repository = AuthRepository(db)
    if user.id is None:
        raise ValueError("user must be persisted before issuing a session-bound access token")

    now = datetime.now(timezone.utc)
    access_ttl = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    auth_session = AuthSession(
        user_id=user.id,
        tenant_id=user.tenant_id,
        refresh_token_hash=token_hex(32),
        expires_at=now + access_ttl,
        last_used_at=now,
        is_revoked=False,
        revoked_at=None,
        channel=channel,
        device_type=device_type,
    )
    repository.save_commit_refresh(auth_session)

    return create_access_token(
        user.id,
        expires_delta=access_ttl,
        extra_data={
            "tenant_id": user.tenant_id,
            "role": user.role,
            "is_tenant_admin": user.is_tenant_admin,
            "sid": auth_session.id,
        },
    )


def generate_system_password() -> str:
    password = f"Sys{token_hex(24)}1"
    return enforce_password(password)


def mark_user_logged_in(db: Session, *, user: User) -> User:
    repository = AuthRepository(db)
    now = datetime.now(timezone.utc)
    user.previous_login_at = user.last_login_at
    user.last_login_at = now
    repository.save_commit_refresh(user)
    return user


def set_user_password(
    db: Session,
    *,
    user: User,
    new_password: str,
) -> User:
    repository = AuthRepository(db)
    password = enforce_password(new_password)
    user.password_hash = get_password_hash(password)
    user.must_reset_password = False
    repository.save_commit_refresh(user)
    return user


def change_user_password(
    db: Session,
    *,
    user: User,
    password_in: PasswordChangeRequest,
) -> User:
    if not user.must_reset_password:
        if not password_in.current_password:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code=ErrorCode.VALIDATION_ERROR,
                message="Current password is required.",
                detail="Current password is required.",
            )
        if not verify_password(password_in.current_password, user.password_hash):
            raise AppError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code=ErrorCode.AUTH_REQUIRED,
                message="Current password is incorrect.",
                detail="Current password is incorrect.",
            )

    return set_user_password(
        db,
        user=user,
        new_password=password_in.new_password,
    )


def register_user_from_invite(
    db: Session,
    *,
    invite_in: InviteRegister,
) -> User:
    repository = AuthRepository(db)
    invites_service = InvitesService(db)
    invite = invites_service.get_valid_invite(token=invite_in.token)

    assert_phone_verified(
        db,
        phone=invite_in.phone,
        purpose="register",
        verification_token=invite_in.phone_verification_token or "",
    )

    existing_user = repository.get_user_by_tenant_phone(
        tenant_id=invite.tenant_id,
        phone=invite_in.phone,
    )
    if existing_user is not None:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.USER_ALREADY_EXISTS,
            message="Phone number already exists in this tenant.",
            detail="Phone number already exists in this tenant.",
        )

    user = create_user(
        db,
        user_in=UserRegister(
            phone=invite_in.phone,
            password=invite_in.password,
            real_name=invite_in.real_name,
        ),
        tenant_id=invite.tenant_id,
        role=invite.role,
        status=int(UserStatus.PENDING_APPROVAL),
    )

    invites_service.consume_invite(invite=invite)
    repository.commit()
    return user


def resolve_tenant_for_registration(
    db: Session,
    *,
    tenant_code: str | None,
) -> Tenant | None:
    normalized_code = (tenant_code or "").strip()
    if not normalized_code:
        return None
    return AuthRepository(db).get_active_tenant_by_code(tenant_code=normalized_code)
