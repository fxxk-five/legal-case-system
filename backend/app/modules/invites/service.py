from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe

from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.modules.invites.models.invite import Invite
from app.modules.invites.repository import InvitesRepository


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class InvitesService:
    def __init__(self, db: Session) -> None:
        self.repository = InvitesRepository(db)

    def create_lawyer_invite(
        self,
        *,
        tenant_id: int,
        invited_by_user_id: int,
        role: str = "lawyer",
        expires_in_days: int = 7,
        max_uses: int = 1,
    ) -> Invite:
        now = datetime.now(timezone.utc)
        existing = self.repository.find_latest_pending_invite(
            tenant_id=tenant_id,
            invited_by_user_id=invited_by_user_id,
            role=role,
            now=now,
        )
        if existing is not None:
            return existing

        invite = Invite(
            tenant_id=tenant_id,
            invited_by_user_id=invited_by_user_id,
            role=role,
            token=token_urlsafe(32),
            expires_at=now + timedelta(days=expires_in_days),
            status="pending",
            max_uses=max_uses,
            used_count=0,
        )
        self.repository.save_commit_refresh(invite)
        return invite

    def get_valid_invite(self, *, token: str) -> Invite:
        invite = self.repository.get_by_token(token=token)
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
            self.repository.save_and_commit(invite)
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code=ErrorCode.INVITE_EXPIRED,
                message="邀请链接已过期。",
                detail="邀请链接已过期。",
            )

        if invite.used_count >= invite.max_uses:
            invite.status = "exhausted"
            self.repository.save_and_commit(invite)
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code=ErrorCode.INVITE_INVALID,
                message="邀请链接使用次数已达上限。",
                detail="邀请链接使用次数已达上限。",
            )

        return invite

    def consume_invite(self, *, invite: Invite) -> Invite:
        invite.used_count += 1
        if invite.used_count >= invite.max_uses:
            invite.status = "used"
        self.repository.save(invite)
        return invite


def create_lawyer_invite(
    db: Session,
    *,
    tenant_id: int,
    invited_by_user_id: int,
    role: str = "lawyer",
    expires_in_days: int = 7,
    max_uses: int = 1,
) -> Invite:
    return InvitesService(db).create_lawyer_invite(
        tenant_id=tenant_id,
        invited_by_user_id=invited_by_user_id,
        role=role,
        expires_in_days=expires_in_days,
        max_uses=max_uses,
    )


def get_valid_invite(db: Session, *, token: str) -> Invite:
    return InvitesService(db).get_valid_invite(token=token)
