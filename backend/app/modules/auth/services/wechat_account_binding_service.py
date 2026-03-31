from __future__ import annotations

from typing import Callable

from fastapi import Request, status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.statuses import UserStatus
from app.integrations.wechat.service import (
    WechatMiniIdentity,
    decode_case_invite_token,
    decode_wechat_login_ticket,
)
from app.models.tenant import Tenant
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import (
    Token,
    UserRegister,
    WechatMiniBind,
    WechatMiniBindExisting,
    WechatMiniLoginResult,
)
from app.modules.cases.models.case import Case


class WechatAccountBindingService:
    def __init__(
        self,
        db: Session,
        *,
        issue_token_pair: Callable[..., Token],
        resolve_login_channel: Callable[..., str],
        ensure_user_can_login: Callable[..., None],
        resolve_tenant_by_code: Callable[[str], Tenant],
        ensure_wechat_identity_available: Callable[..., None],
        bind_wechat_identity: Callable[..., None],
        build_wechat_login_result: Callable[..., WechatMiniLoginResult],
        auth_required: Callable[[str], AppError],
    ) -> None:
        self.db = db
        self.issue_token_pair = issue_token_pair
        self.resolve_login_channel = resolve_login_channel
        self.ensure_user_can_login = ensure_user_can_login
        self.resolve_tenant_by_code = resolve_tenant_by_code
        self.ensure_wechat_identity_available = ensure_wechat_identity_available
        self.bind_wechat_identity = bind_wechat_identity
        self.build_wechat_login_result = build_wechat_login_result
        self.auth_required = auth_required
        self.repository = AuthRepository(db)

    def wx_mini_bind_existing(
        self,
        *,
        bind_in: WechatMiniBindExisting,
        request: Request,
    ) -> WechatMiniLoginResult:
        from app.modules.auth.service import authenticate_user

        identity = decode_wechat_login_ticket(bind_in.wx_session_ticket)
        tenant = self.resolve_tenant_by_code(bind_in.tenant_code) if bind_in.tenant_code else None
        tenant_id = tenant.id if tenant is not None else None

        try:
            authenticated_user = authenticate_user(
                self.db,
                phone=bind_in.phone,
                password=bind_in.password,
                tenant_id=tenant_id,
            )
        except ValueError as exc:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                code=ErrorCode.CONFLICT,
                message="该手机号匹配多个租户，请先指定 tenant_code。",
                detail="该手机号匹配多个租户，请先指定 tenant_code。",
            ) from exc

        if authenticated_user is None:
            raise self.auth_required("手机号或密码错误，无法绑定微信。")

        self.ensure_user_can_login(authenticated_user)
        self.ensure_wechat_identity_available(identity=identity, user=authenticated_user)
        self.bind_wechat_identity(authenticated_user, identity=identity, phone=bind_in.phone)
        self.repository.save(authenticated_user)

        tokens = self.issue_token_pair(
            user=authenticated_user,
            request=request,
            channel=self.resolve_login_channel(request, prefer_wechat=True),
        )
        return self.build_wechat_login_result(
            identity=identity,
            tokens=tokens,
            user=authenticated_user,
            need_bind_phone=False,
        )

    def wx_mini_bind(
        self,
        *,
        bind_in: WechatMiniBind,
        request: Request,
    ) -> WechatMiniLoginResult:
        from app.modules.auth.service import authenticate_user, create_user, generate_system_password

        identity = decode_wechat_login_ticket(bind_in.wx_session_ticket)
        existing_user = (
            self.repository.get_user_by_tenant_phone(
                tenant_id=bind_in.tenant_id,
                phone=bind_in.phone,
            )
            if bind_in.tenant_id
            else None
        )
        if existing_user is None and bind_in.tenant_code:
            tenant = self.resolve_tenant_by_code(bind_in.tenant_code)
            existing_user = self.repository.get_user_by_tenant_phone(
                tenant_id=tenant.id,
                phone=bind_in.phone,
            )

        if existing_user is not None:
            self.ensure_user_can_login(existing_user)
            if bind_in.password is None:
                raise AppError(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    code=ErrorCode.VALIDATION_ERROR,
                    message="绑定已有账号时必须输入密码。",
                    detail="绑定已有账号时必须输入密码。",
                )
            authenticated_user = authenticate_user(
                self.db,
                phone=bind_in.phone,
                password=bind_in.password,
                tenant_id=existing_user.tenant_id,
            )
            if authenticated_user is None or authenticated_user.id != existing_user.id:
                raise self.auth_required("手机号或密码错误，无法绑定微信。")
            self.ensure_wechat_identity_available(identity=identity, user=existing_user)
            self.bind_wechat_identity(existing_user, identity=identity, phone=bind_in.phone)
            if bind_in.real_name and not existing_user.real_name:
                existing_user.real_name = bind_in.real_name
            self.repository.save(existing_user)
            tokens = self.issue_token_pair(
                user=existing_user,
                request=request,
                channel=self.resolve_login_channel(request, prefer_wechat=True),
            )
            return self.build_wechat_login_result(
                identity=identity,
                tokens=tokens,
                user=existing_user,
                need_bind_phone=False,
            )

        if not bind_in.case_invite_token:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code=ErrorCode.INVITE_REQUIRED,
                message="旧版绑定接口仅允许通过案件邀请创建当事人账号。",
                detail="旧版绑定接口仅允许通过案件邀请创建当事人账号。",
            )

        invite_payload = decode_case_invite_token(bind_in.case_invite_token)
        tenant = self.repository.get_tenant_by_id(tenant_id=int(invite_payload["tenant_id"]))
        if tenant is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code=ErrorCode.TENANT_NOT_FOUND,
                message="目标租户不存在。",
                detail="目标租户不存在。",
            )

        user = self.repository.get_user_by_tenant_phone(
            tenant_id=tenant.id,
            phone=bind_in.phone,
        )
        if user is None:
            user = create_user(
                self.db,
                user_in=UserRegister(
                    phone=bind_in.phone,
                    password=generate_system_password(),
                    real_name=(bind_in.real_name or f"当事人{bind_in.phone[-4:]}").strip(),
                ),
                tenant_id=tenant.id,
                role="client",
                status=int(UserStatus.ACTIVE),
                must_reset_password=True,
            )

        self.ensure_user_can_login(user)
        self.ensure_wechat_identity_available(identity=identity, user=user)
        self.bind_wechat_identity(user, identity=identity, phone=bind_in.phone)
        if bind_in.real_name and not user.real_name:
            user.real_name = bind_in.real_name
        self.repository.save(user)

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
