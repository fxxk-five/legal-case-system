from __future__ import annotations

from typing import Callable

from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.roles import normalize_role
from app.core.statuses import TenantStatus
from app.integrations.wechat.service import decode_case_invite_token
from app.models.tenant import Tenant
from app.modules.auth.repository import AuthRepository
from app.modules.invites.models.invite import Invite
from app.modules.invites.service import InvitesService


class WechatContextService:
    def __init__(
        self,
        db: Session,
        *,
        resolve_tenant_by_code: Callable[[str], Tenant],
    ) -> None:
        self.db = db
        self.repository = AuthRepository(db)
        self.resolve_tenant_by_code = resolve_tenant_by_code

    def resolve_lawyer_invite(self, *, token: str) -> Invite:
        invite = InvitesService(self.db).get_valid_invite(token=token)
        if normalize_role(invite.role) != "lawyer":
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code=ErrorCode.INVITE_INVALID,
                message="当前邀请仅支持机构律师加入。",
                detail="当前邀请仅支持机构律师加入。",
            )
        return invite

    def resolve_wechat_tenant_context(
        self,
        *,
        phone: str,
        tenant_code: str | None,
        case_invite_token: str | None,
    ) -> tuple[Tenant, dict | None]:
        invite_payload = None
        if case_invite_token:
            invite_payload = decode_case_invite_token(case_invite_token)
            tenant = self.repository.get_tenant_by_id(tenant_id=int(invite_payload["tenant_id"]))
            if tenant is None or int(tenant.status) != int(TenantStatus.ACTIVE):
                raise AppError(
                    status_code=status.HTTP_404_NOT_FOUND,
                    code=ErrorCode.TENANT_NOT_FOUND,
                    message="目标租户不存在或已停用。",
                    detail="目标租户不存在或已停用。",
                )
            return tenant, invite_payload

        if tenant_code:
            return self.resolve_tenant_by_code(tenant_code), None

        matched_users = self.repository.list_users_by_phone(phone=phone)
        tenant_ids = sorted({user.tenant_id for user in matched_users})
        if len(tenant_ids) > 1:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                code=ErrorCode.CONFLICT,
                message="该手机号匹配多个租户，请先指定 tenant_code 或使用案件邀请继续登录。",
                detail="该手机号匹配多个租户，请先指定 tenant_code 或使用案件邀请继续登录。",
            )

        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.VALIDATION_ERROR,
            message="请提供 tenant_code 或案件邀请后再继续微信登录。",
            detail="请提供 tenant_code 或案件邀请后再继续微信登录。",
        )

    @staticmethod
    def has_wechat_invite_context(*, case_invite_token: str | None, lawyer_invite_token: str | None) -> bool:
        return bool((case_invite_token or "").strip() or (lawyer_invite_token or "").strip())
