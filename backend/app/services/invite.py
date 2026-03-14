from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.invite import Invite


def create_lawyer_invite(
    db: Session,
    *,
    tenant_id: int,
    invited_by_user_id: int,
    role: str = "lawyer",
    expires_in_days: int = 7,
) -> Invite:
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="邀请链接不存在。")

    if invite.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邀请链接已失效。")

    if invite.expires_at < datetime.now(timezone.utc):
        invite.status = "expired"
        db.add(invite)
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邀请链接已过期。")

    return invite
