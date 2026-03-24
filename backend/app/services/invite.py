from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe

from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.models.invite import Invite


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def create_lawyer_invite(
    db: Session,
    *,
    tenant_id: int,
    invited_by_user_id: int,
    role: str = "lawyer",
    expires_in_days: int = 7,
) -> Invite:
    existing = (
        db.query(Invite)
        .filter(
            Invite.tenant_id == tenant_id,
            Invite.invited_by_user_id == invited_by_user_id,
            Invite.role == role,
            Invite.status == "pending",
            Invite.expires_at > datetime.now(timezone.utc),
        )
        .order_by(Invite.created_at.desc())
        .first()
    )
    if existing is not None:
        return existing

    invite = Invite(
        tenant_id=tenant_id,
        invited_by_user_id=invited_by_user_id,
        role=role,
        token=token_urlsafe(32),
        expires_at=datetime.now(timezone.utc) + timedelta(days=expires_in_days),
        status="pending",
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite


def get_valid_invite(db: Session, *, token: str) -> Invite:
    invite = db.query(Invite).filter(Invite.token == token).first()
    if invite is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.INVITE_NOT_FOUND,
            message="邀请链接不存在。",
            detail="邀请链接不存在。",
        )

    if invite.status != "pending":
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.INVITE_INVALID,
            message="邀请链接已失效。",
            detail="邀请链接已失效。",
        )

    if _as_utc(invite.expires_at) < datetime.now(timezone.utc):
        invite.status = "expired"
        db.add(invite)
        db.commit()
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.INVITE_EXPIRED,
            message="邀请链接已过期。",
            detail="邀请链接已过期。",
        )

    return invite
