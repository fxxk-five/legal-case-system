from __future__ import annotations

from typing import Callable

from fastapi import Request, status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.statuses import TenantStatus, UserStatus
from app.integrations.wechat.service import (
    WechatMiniIdentity,
    exchange_phone_code_for_phone_number,
)
from app.models.tenant import Tenant
from app.models.user import User
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import (
    Token,
    UserRegister,
    WechatMiniBind,
    WechatMiniBindExisting,
    WechatMiniLoginResult,
    WechatMiniPhoneLogin,
)
from app.modules.cases.models.case import Case
from app.modules.auth.services.wechat_account_binding_service import WechatAccountBindingService


class WechatBindingService:
    def __init__(
        self,
        db: Session,
        *,
        issue_token_pair: Callable[..., Token],
        resolve_login_channel: Callable[..., str],
        ensure_user_can_login: Callable[..., None],
        resolve_tenant_by_code: Callable[[str], Tenant],
        resolve_lawyer_invite: Callable[..., object],
        resolve_wechat_tenant_context: Callable[..., tuple[Tenant, dict | None]],
        has_wechat_invite_context: Callable[..., bool],
        find_user_by_wechat_identity: Callable[..., User | None],
        ensure_wechat_identity_available: Callable[..., None],
        bind_wechat_identity: Callable[..., None],
        build_wechat_login_result: Callable[..., WechatMiniLoginResult],
        build_pending_approval_result: Callable[..., WechatMiniLoginResult],
        auth_required: Callable[[str], AppError],
    ) -> None:
        self.db = db
        self.issue_token_pair = issue_token_pair
        self.resolve_login_channel = resolve_login_channel
        self.ensure_user_can_login = ensure_user_can_login
        self.resolve_tenant_by_code = resolve_tenant_by_code
        self.resolve_lawyer_invite = resolve_lawyer_invite
        self.resolve_wechat_tenant_context = resolve_wechat_tenant_context
        self.has_wechat_invite_context = has_wechat_invite_context
        self.find_user_by_wechat_identity = find_user_by_wechat_identity
        self.ensure_wechat_identity_available = ensure_wechat_identity_available
        self.bind_wechat_identity = bind_wechat_identity
        self.build_wechat_login_result = build_wechat_login_result
        self.build_pending_approval_result = build_pending_approval_result
        self.auth_required = auth_required
        self.repository = AuthRepository(db)
        self.account_binding_service = WechatAccountBindingService(
            db,
            issue_token_pair=issue_token_pair,
            resolve_login_channel=resolve_login_channel,
            ensure_user_can_login=ensure_user_can_login,
            resolve_tenant_by_code=resolve_tenant_by_code,
            ensure_wechat_identity_available=ensure_wechat_identity_available,
            bind_wechat_identity=bind_wechat_identity,
            build_wechat_login_result=build_wechat_login_result,
            auth_required=auth_required,
        )

    def wx_mini_phone_login(
        self,
        *,
        login_in: WechatMiniPhoneLogin,
        request: Request,
    ) -> WechatMiniLoginResult:
        from app.modules.auth.service import create_user, generate_system_password

        from app.integrations.wechat.service import decode_wechat_login_ticket

        identity = decode_wechat_login_ticket(login_in.wx_session_ticket)
        lawyer_invite = (
            self.resolve_lawyer_invite(token=login_in.lawyer_invite_token)
            if login_in.lawyer_invite_token
            else None
        )
        invite_mode = self.has_wechat_invite_context(
            case_invite_token=login_in.case_invite_token,
            lawyer_invite_token=login_in.lawyer_invite_token,
        )
        bound_user = self.find_user_by_wechat_identity(identity=identity)
        if bound_user is not None and not invite_mode:
            self.ensure_user_can_login(bound_user)
            tokens = self.issue_token_pair(
                user=bound_user,
                request=request,
                channel=self.resolve_login_channel(request, prefer_wechat=True),
            )
            return self.build_wechat_login_result(
                identity=identity,
                tokens=tokens,
                user=bound_user,
                need_bind_phone=False,
            )

        phone = exchange_phone_code_for_phone_number(login_in.phone_code)
        invite_payload = None
        if lawyer_invite is not None:
            tenant = self.repository.get_tenant_by_id(tenant_id=lawyer_invite.tenant_id)
            if tenant is None or int(tenant.status) != int(TenantStatus.ACTIVE):
                raise AppError(
                    status_code=status.HTTP_404_NOT_FOUND,
                    code=ErrorCode.TENANT_NOT_FOUND,
                    message="目标机构不存在或已停用。",
                    detail="目标机构不存在或已停用。",
                )
        else:
            tenant, invite_payload = self.resolve_wechat_tenant_context(
                phone=phone,
                tenant_code=login_in.tenant_code,
                case_invite_token=login_in.case_invite_token,
            )

        user = self.repository.get_user_by_tenant_phone(
            tenant_id=tenant.id,
            phone=phone,
        )
        if user is None:
            if lawyer_invite is None and invite_payload is None:
                raise AppError(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    code=ErrorCode.INVITE_REQUIRED,
                    message="当前手机号尚未开通账号，请使用案件邀请或机构邀请进入。",
                    detail="当前手机号尚未开通账号，请使用案件邀请或机构邀请进入。",
                )

            if lawyer_invite is not None:
                user = create_user(
                    self.db,
                    user_in=UserRegister(
                        phone=phone,
                        password=generate_system_password(),
                        real_name=(login_in.real_name or f"律师{phone[-4:]}").strip(),
                    ),
                    tenant_id=tenant.id,
                    role=lawyer_invite.role,
                    status=int(UserStatus.PENDING_APPROVAL),
                    must_reset_password=True,
                )
            else:
                user = create_user(
                    self.db,
                    user_in=UserRegister(
                        phone=phone,
                        password=generate_system_password(),
                        real_name=(login_in.real_name or f"当事人{phone[-4:]}").strip(),
                    ),
                    tenant_id=tenant.id,
                    role="client",
                    status=int(UserStatus.ACTIVE),
                    must_reset_password=True,
                )

        self.ensure_wechat_identity_available(identity=identity, user=user)
        self.bind_wechat_identity(user, identity=identity, phone=phone)
        self.repository.save(user)

        if lawyer_invite is not None and lawyer_invite.status == "pending":
            lawyer_invite.used_count += 1
            if lawyer_invite.used_count >= lawyer_invite.max_uses:
                lawyer_invite.status = "used"
            self.repository.save(lawyer_invite)

        if invite_payload is not None:
            case = self.repository.get_case(
                case_id=int(invite_payload["case_id"]),
                tenant_id=tenant.id,
            )
            if case is None:
                raise AppError(
                    status_code=status.HTTP_404_NOT_FOUND,
                    code=ErrorCode.CASE_NOT_FOUND,
                    message="案件不存在。",
                    detail="案件不存在。",
                )
            case.client_id = user.id
            self.repository.save(case)

        if int(user.status) == int(UserStatus.PENDING_APPROVAL):
            self.repository.commit_and_refresh(user)
            return self.build_pending_approval_result(identity=identity, user=user)

        self.ensure_user_can_login(user)
        tokens = self.issue_token_pair(
            user=user,
            request=request,
            channel=self.resolve_login_channel(request, prefer_wechat=True),
        )
        return self.build_wechat_login_result(
            identity=identity,
            tokens=tokens,
            user=user,
            need_bind_phone=False,
        )

    def wx_mini_bind_existing(
        self,
        *,
        bind_in: WechatMiniBindExisting,
        request: Request,
    ) -> WechatMiniLoginResult:
        return self.account_binding_service.wx_mini_bind_existing(
            bind_in=bind_in,
            request=request,
        )

    def wx_mini_bind(
        self,
        *,
        bind_in: WechatMiniBind,
        request: Request,
    ) -> WechatMiniLoginResult:
        return self.account_binding_service.wx_mini_bind(
            bind_in=bind_in,
            request=request,
        )
