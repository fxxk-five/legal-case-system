from __future__ import annotations

from typing import Callable

from fastapi import Request, status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.roles import normalize_role
from app.core.statuses import TenantStatus, UserStatus
from app.integrations.sms.service import SmsRequestContext, verify_sms_code
from app.integrations.wechat.service import decode_case_invite_token
from app.models.tenant import Tenant
from app.models.user import User
from app.modules.auth.account_service import authenticate_user
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import LoginAdviceRequest, LoginAdviceResponse, SmsCodeLoginRequest, Token, UserLogin
from app.modules.auth.session_service import AuthSessionService


class AuthLoginService:
    def __init__(
        self,
        db: Session,
        *,
        session_service: AuthSessionService,
        ensure_user_can_login: Callable[..., None],
        resolve_login_channel: Callable[..., str],
        resolve_tenant_by_code: Callable[[str], Tenant],
        build_sms_request_context: Callable[[Request | None], SmsRequestContext],
    ) -> None:
        self.db = db
        self.repository = AuthRepository(db)
        self.session_service = session_service
        self.ensure_user_can_login = ensure_user_can_login
        self.resolve_login_channel = resolve_login_channel
        self.resolve_tenant_by_code = resolve_tenant_by_code
        self.build_sms_request_context = build_sms_request_context

    def _resolve_login_tenant(self, *, tenant_code: str | None) -> Tenant | None:
        normalized_code = (tenant_code or "").strip()
        if not normalized_code:
            return None
        return self.resolve_tenant_by_code(normalized_code)

    def _resolve_case_invite_context_for_login(self, *, case_invite_token: str) -> tuple[Tenant, dict]:
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

    def resolve_login_context(
        self,
        *,
        tenant_code: str | None,
        case_invite_token: str | None,
    ) -> tuple[Tenant | None, dict | None]:
        tenant = self._resolve_login_tenant(tenant_code=tenant_code)
        invite_payload = None

        if case_invite_token:
            invite_tenant, invite_payload = self._resolve_case_invite_context_for_login(
                case_invite_token=case_invite_token,
            )
            if tenant is not None and tenant.id != invite_tenant.id:
                raise AppError(
                    status_code=status.HTTP_409_CONFLICT,
                    code=ErrorCode.CONFLICT,
                    message="tenant_code 与案件邀请不一致，请确认后重试。",
                    detail="tenant_code 与案件邀请不一致，请确认后重试。",
                )
            tenant = invite_tenant

        return tenant, invite_payload

    def apply_case_invite_binding(
        self,
        *,
        user: User,
        invite_payload: dict | None,
    ) -> None:
        if invite_payload is None:
            return
        if normalize_role(user.role) != "client":
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code=ErrorCode.FORBIDDEN,
                message="案件邀请仅允许当事人账号登录并绑定。",
                detail="案件邀请仅允许当事人账号登录并绑定。",
            )

        case = self.repository.get_case(
            case_id=int(invite_payload["case_id"]),
            tenant_id=user.tenant_id,
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

    def _resolve_sms_login_user(
        self,
        *,
        phone: str,
        tenant_code: str | None,
        case_invite_token: str | None,
    ) -> tuple[User, dict | None]:
        tenant, invite_payload = self.resolve_login_context(
            tenant_code=tenant_code,
            case_invite_token=case_invite_token,
        )
        if tenant is not None:
            user = self.repository.get_user_by_tenant_phone(
                tenant_id=tenant.id,
                phone=phone,
            )
            if user is None:
                raise AppError(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    code=ErrorCode.AUTH_REQUIRED,
                    message="手机号或验证码错误。",
                    detail="手机号或验证码错误。",
                )
            return user, invite_payload

        matched_users = self.repository.list_users_by_phone(phone=phone)
        if not matched_users:
            raise AppError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code=ErrorCode.AUTH_REQUIRED,
                message="手机号或验证码错误。",
                detail="手机号或验证码错误。",
            )

        tenant_ids = sorted({user.tenant_id for user in matched_users})
        if len(tenant_ids) > 1:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code=ErrorCode.VALIDATION_ERROR,
                message="该手机号存在于多个租户，请填写 tenant_code 后再登录。",
                detail="该手机号存在于多个租户，请填写 tenant_code 后再登录。",
            )

        return matched_users[0], invite_payload

    @staticmethod
    def _resolve_recommended_entry(*, matched_users: list[User], has_case_invite: bool) -> str:
        if has_case_invite:
            return "mini-program"
        normalized_roles = {normalize_role(user.role) for user in matched_users}
        if "client" in normalized_roles:
            return "mini-program"
        return "web"

    @staticmethod
    def _resolve_support_hint(
        *,
        requires_tenant_code: bool,
        requires_admin_approval: bool,
        recommended_entry: str,
    ) -> str:
        if requires_tenant_code:
            return "当前手机号存在多个租户，请先填写 tenant_code；如仍失败，请确认当前角色、当前登录端、是否首登或刚被邀请。"
        if requires_admin_approval:
            return "当前账号处于待审批状态，请联系租户管理员审批；支持排查请先确认当前角色、当前登录端、是否首登或刚被邀请。"
        if recommended_entry == "mini-program":
            return "当前账号建议优先使用小程序完成业务操作；如登录异常，请先确认当前角色、当前登录端、是否首登或刚被邀请。"
        return "可继续在 Web 或小程序登录；如登录失败，请先确认当前角色、当前登录端、是否首登或刚被邀请。"

    def get_login_advice(self, *, advice_in: LoginAdviceRequest) -> LoginAdviceResponse:
        tenant, invite_payload = self.resolve_login_context(
            tenant_code=advice_in.tenant_code,
            case_invite_token=advice_in.case_invite_token,
        )
        if tenant is not None:
            matched_users = self.repository.list_users_by_phone(
                phone=advice_in.phone,
                tenant_id=tenant.id,
            )
            tenant_count = 1 if matched_users else 0
        else:
            matched_users = self.repository.list_users_by_phone(phone=advice_in.phone)
            tenant_count = len({user.tenant_id for user in matched_users})

        requires_tenant_code = tenant is None and tenant_count > 1
        requires_admin_approval = any(int(user.status) == int(UserStatus.PENDING_APPROVAL) for user in matched_users)
        login_state = "not_found"
        if matched_users:
            login_state = "pending_approval" if requires_admin_approval else "ready"

        recommended_entry = self._resolve_recommended_entry(
            matched_users=matched_users,
            has_case_invite=invite_payload is not None,
        )

        return LoginAdviceResponse(
            phone=advice_in.phone,
            requires_tenant_code=requires_tenant_code,
            requires_admin_approval=requires_admin_approval,
            recommended_entry=recommended_entry,
            login_state=login_state,
            support_hint=self._resolve_support_hint(
                requires_tenant_code=requires_tenant_code,
                requires_admin_approval=requires_admin_approval,
                recommended_entry=recommended_entry,
            ),
        )

    def login_by_sms_code(self, *, sms_in: SmsCodeLoginRequest, request: Request) -> Token:
        verify_sms_code(
            self.db,
            phone=sms_in.phone,
            code=sms_in.code,
            purpose="login",
            context=self.build_sms_request_context(request),
        )

        user, invite_payload = self._resolve_sms_login_user(
            phone=sms_in.phone,
            tenant_code=sms_in.tenant_code,
            case_invite_token=sms_in.case_invite_token,
        )
        self.ensure_user_can_login(user, allow_pending=True)
        self.apply_case_invite_binding(user=user, invite_payload=invite_payload)

        return self.session_service.issue_token_pair(
            user=user,
            request=request,
            channel="web_sms",
        )

    def login(self, *, user_in: UserLogin, request: Request) -> Token:
        tenant, invite_payload = self.resolve_login_context(
            tenant_code=user_in.tenant_code,
            case_invite_token=user_in.case_invite_token,
        )
        tenant_id = tenant.id if tenant is not None else None

        try:
            user = authenticate_user(
                self.db,
                phone=user_in.phone,
                password=user_in.password,
                tenant_id=tenant_id,
                allow_pending=True,
            )
        except ValueError as exc:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code=ErrorCode.VALIDATION_ERROR,
                message="该手机号存在于多个租户，请填写 tenant_code 后再登录。",
                detail="该手机号存在于多个租户，请填写 tenant_code 后再登录。",
            ) from exc

        if user is None:
            raise AppError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code=ErrorCode.AUTH_REQUIRED,
                message="手机号或密码错误。",
                detail="手机号或密码错误。",
            )

        self.ensure_user_can_login(user, allow_pending=True)
        self.apply_case_invite_binding(user=user, invite_payload=invite_payload)

        return self.session_service.issue_token_pair(
            user=user,
            request=request,
            channel=self.resolve_login_channel(request),
        )
