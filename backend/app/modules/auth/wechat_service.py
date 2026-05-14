from __future__ import annotations

from typing import Callable

from fastapi import Request, status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.integrations.wechat.service import (
    WechatMiniIdentity,
    create_wechat_login_ticket,
    exchange_code_for_identity,
)
from app.models.tenant import Tenant
from app.models.user import User
from app.modules.auth.schemas import (
    Token,
    WechatMiniBind,
    WechatMiniBindExisting,
    WechatMiniLogin,
    WechatMiniLoginResult,
    WechatMiniPhoneLogin,
)
from app.modules.auth.services import (
    WechatBindingService,
    WechatContextService,
    WechatIdentityService,
    WechatResultFactory,
)


class WechatAuthService:
    def __init__(
        self,
        db: Session,
        *,
        issue_token_pair: Callable[..., Token],
        resolve_login_channel: Callable[..., str],
        ensure_user_can_login: Callable[..., None],
        resolve_tenant_by_code: Callable[[str], Tenant],
    ) -> None:
        self.db = db
        self.issue_token_pair = issue_token_pair
        self.resolve_login_channel = resolve_login_channel
        self.ensure_user_can_login = ensure_user_can_login
        self.resolve_tenant_by_code = resolve_tenant_by_code
        self.identity_service = WechatIdentityService(db)
        self.context_service = WechatContextService(
            db,
            resolve_tenant_by_code=resolve_tenant_by_code,
        )
        self.binding_service = WechatBindingService(
            db,
            issue_token_pair=issue_token_pair,
            resolve_login_channel=resolve_login_channel,
            ensure_user_can_login=ensure_user_can_login,
            resolve_tenant_by_code=resolve_tenant_by_code,
            resolve_lawyer_invite=self._resolve_lawyer_invite,
            resolve_wechat_tenant_context=self._resolve_wechat_tenant_context,
            has_wechat_invite_context=self._has_wechat_invite_context,
            find_user_by_wechat_identity=self._find_user_by_wechat_identity,
            ensure_wechat_identity_available=self._ensure_wechat_identity_available,
            bind_wechat_identity=self._bind_wechat_identity,
            build_wechat_login_result=self._build_wechat_login_result,
            build_pending_approval_result=self._build_pending_approval_result,
            auth_required=self._auth_required,
        )

    @staticmethod
    def _auth_required(message: str = "登录状态无效，请重新登录。") -> AppError:
        return AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=ErrorCode.AUTH_REQUIRED,
            message=message,
            detail=message,
        )

    def _resolve_lawyer_invite(self, *, token: str):
        return self.context_service.resolve_lawyer_invite(token=token)

    def _find_user_by_wechat_identity(self, *, identity: WechatMiniIdentity) -> User | None:
        return self.identity_service.find_user_by_wechat_identity(identity=identity)

    def _resolve_wechat_tenant_context(
        self,
        *,
        phone: str,
        tenant_code: str | None,
        case_invite_token: str | None,
    ) -> tuple[Tenant, dict | None]:
        return self.context_service.resolve_wechat_tenant_context(
            phone=phone,
            tenant_code=tenant_code,
            case_invite_token=case_invite_token,
        )

    @staticmethod
    def _has_wechat_invite_context(*, case_invite_token: str | None, lawyer_invite_token: str | None) -> bool:
        return WechatContextService.has_wechat_invite_context(
            case_invite_token=case_invite_token,
            lawyer_invite_token=lawyer_invite_token,
        )

    @staticmethod
    def _bind_wechat_identity(user: User, *, identity: WechatMiniIdentity, phone: str) -> None:
        WechatIdentityService.bind_wechat_identity(
            user,
            identity=identity,
            phone=phone,
        )

    def _ensure_wechat_identity_available(self, *, identity: WechatMiniIdentity, user: User) -> None:
        self.identity_service.ensure_wechat_identity_available(
            identity=identity,
            user=user,
        )

    @staticmethod
    def _build_wechat_login_result(
        *,
        identity: WechatMiniIdentity,
        tokens: Token | None = None,
        user: User | None = None,
        need_bind_phone: bool,
        wx_session_ticket: str | None = None,
    ) -> WechatMiniLoginResult:
        return WechatResultFactory.build_wechat_login_result(
            identity=identity,
            tokens=tokens,
            user=user,
            need_bind_phone=need_bind_phone,
            wx_session_ticket=wx_session_ticket,
        )

    @staticmethod
    def _build_pending_approval_result(
        *,
        identity: WechatMiniIdentity,
        user: User,
    ) -> WechatMiniLoginResult:
        return WechatResultFactory.build_pending_approval_result(
            identity=identity,
            user=user,
        )

    def wx_mini_login(self, *, login_in: WechatMiniLogin, request: Request) -> WechatMiniLoginResult:
        identity = exchange_code_for_identity(login_in.code)
        user = self._find_user_by_wechat_identity(identity=identity)
        invite_mode = self._has_wechat_invite_context(
            case_invite_token=login_in.case_invite_token,
            lawyer_invite_token=login_in.lawyer_invite_token,
        )
        if user is None or invite_mode:
            return self._build_wechat_login_result(
                identity=identity,
                need_bind_phone=True,
                wx_session_ticket=create_wechat_login_ticket(identity),
            )

        self.ensure_user_can_login(user)
        tokens = self.issue_token_pair(
            user=user,
            request=request,
            channel=self.resolve_login_channel(request, prefer_wechat=True),
        )
        return self._build_wechat_login_result(
            identity=identity,
            tokens=tokens,
            user=user,
            need_bind_phone=False,
        )

    def wx_mini_phone_login(
        self,
        *,
        login_in: WechatMiniPhoneLogin,
        request: Request,
    ) -> WechatMiniLoginResult:
        return self.binding_service.wx_mini_phone_login(
            login_in=login_in,
            request=request,
        )

    def wx_mini_bind_existing(
        self,
        *,
        bind_in: WechatMiniBindExisting,
        request: Request,
    ) -> WechatMiniLoginResult:
        return self.binding_service.wx_mini_bind_existing(
            bind_in=bind_in,
            request=request,
        )

    def wx_mini_bind(
        self,
        *,
        bind_in: WechatMiniBind,
        request: Request,
    ) -> WechatMiniLoginResult:
        return self.binding_service.wx_mini_bind(
            bind_in=bind_in,
            request=request,
        )
