from __future__ import annotations

from collections.abc import Sequence

from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.roles import role_values_for_query
from app.core.statuses import UserStatus, can_transition_user_status
from app.models.user import User
from app.modules.invites.schemas import InviteCreateResponse
from app.modules.invites.service import InvitesService
from app.modules.users.schemas import LawyerCreate, UserStatusUpdate
from app.modules.users.repository import UsersRepository


class UsersService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = UsersRepository(db)
        self.invites_service = InvitesService(db)

    @staticmethod
    def reject_direct_lawyer_creation(*, lawyer_in: LawyerCreate, current_user: User) -> User:
        _ = (lawyer_in, current_user)
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.INVITE_REQUIRED,
            message="Organization lawyers must register via invite link.",
            detail="Organization lawyers must register via invite link.",
        )

    def list_lawyers(self, *, current_user: User) -> list[User]:
        return self.repository.list_tenant_users(
            tenant_id=current_user.tenant_id,
            roles=role_values_for_query("lawyer", "tenant_admin"),
        )

    def invite_lawyer(self, *, current_user: User) -> InviteCreateResponse:
        invite = self.invites_service.create_lawyer_invite(
            tenant_id=current_user.tenant_id,
            invited_by_user_id=current_user.id,
        )
        return InviteCreateResponse(
            token=invite.token,
            register_path=f"pages/login/index?scene=lawyer-invite&token={invite.token}",
            expires_at=invite.expires_at,
        )

    def list_pending_users(self, *, current_user: User) -> list[User]:
        return self.repository.list_tenant_users(
            tenant_id=current_user.tenant_id,
            roles=role_values_for_query("lawyer", "tenant_admin"),
            status=int(UserStatus.PENDING_APPROVAL),
        )

    def _get_tenant_user_or_404(
        self,
        *,
        user_id: int,
        tenant_id: int,
        roles: Sequence[str] | None = None,
        target_status: int | None = None,
        message: str,
    ) -> User:
        user = self.repository.get_tenant_user(
            user_id=user_id,
            tenant_id=tenant_id,
            roles=roles,
            status=target_status,
        )
        if user is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code=ErrorCode.USER_NOT_FOUND,
                message=message,
                detail=message,
            )
        return user

    def approve_user(
        self,
        *,
        user_id: int,
        current_user: User,
        roles: Sequence[str] | None = None,
    ) -> User:
        user = self._get_tenant_user_or_404(
            user_id=user_id,
            tenant_id=current_user.tenant_id,
            roles=roles,
            message="User not found.",
        )
        if not can_transition_user_status(user.status, int(UserStatus.ACTIVE)):
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                code=ErrorCode.CONFLICT,
                message="Current member status cannot be approved.",
                detail="Current member status cannot be approved.",
            )

        user.status = int(UserStatus.ACTIVE)
        self.repository.save_commit_refresh(user)
        return user

    def reject_user(self, *, user_id: int, current_user: User) -> None:
        user = self._get_tenant_user_or_404(
            user_id=user_id,
            tenant_id=current_user.tenant_id,
            target_status=int(UserStatus.PENDING_APPROVAL),
            message="Pending user not found.",
        )
        self.repository.delete_and_commit(user)

    def update_user_status(
        self,
        *,
        user_id: int,
        user_in: UserStatusUpdate,
        current_user: User,
    ) -> User:
        user = self._get_tenant_user_or_404(
            user_id=user_id,
            tenant_id=current_user.tenant_id,
            message="User not found.",
        )
        if user.status != user_in.status and not can_transition_user_status(user.status, user_in.status):
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                code=ErrorCode.CONFLICT,
                message="Invalid member status transition.",
                detail="Invalid member status transition.",
            )

        user.status = user_in.status
        self.repository.save_commit_refresh(user)
        return user

    def list_all_users(self) -> list[User]:
        return self.repository.list_all_users()

