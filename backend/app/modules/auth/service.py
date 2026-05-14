from __future__ import annotations

from fastapi import Request, status
from sqlalchemy.orm import Session

from app.core.client_source import is_mini_program_request as is_mini_program_request_source
from app.core.errors import AppError, ErrorCode
from app.core.statuses import UserStatus, is_active_user_status
from app.integrations.sms.service import (
    SmsRequestContext,
    assert_phone_verified,
)
from app.models.tenant import Tenant
from app.models.user import User
from app.modules.auth import account_service as _account_service
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import (
    LoginAdviceRequest,
    LoginAdviceResponse,
    PasswordChangeRequest,
    PhoneRegisterRequest,
    SmsCodeLoginRequest,
    SmsSendRequest,
    SmsSendResponse,
    SmsVerifyRequest,
    SmsVerifyResponse,
    Token,
    UserLogin,
    UserRegister,
)
from app.modules.auth.session_service import AuthSessionService
from app.modules.auth.services import AuthLoginService, AuthSmsService
from app.modules.invites.schemas import InviteRegister

authenticate_user = _account_service.authenticate_user
create_user = _account_service.create_user
issue_session_bound_access_token = _account_service.issue_session_bound_access_token
generate_system_password = _account_service.generate_system_password
mark_user_logged_in = _account_service.mark_user_logged_in
set_user_password = _account_service.set_user_password
change_user_password = _account_service.change_user_password
register_user_from_invite = _account_service.register_user_from_invite
resolve_tenant_for_registration = _account_service.resolve_tenant_for_registration


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = AuthRepository(db)
        self.session_service = AuthSessionService(
            db,
            ensure_user_can_login=self.ensure_user_can_login,
            resolve_login_channel=self.resolve_login_channel,
        )
        self.login_service = AuthLoginService(
            db,
            session_service=self.session_service,
            ensure_user_can_login=self.ensure_user_can_login,
            resolve_login_channel=self.resolve_login_channel,
            resolve_tenant_by_code=self.resolve_tenant_by_code,
            build_sms_request_context=self._build_sms_request_context,
        )
        self.sms_auth_service = AuthSmsService(db)

    @staticmethod
    def _is_mini_program_request(request: Request | None) -> bool:
        return is_mini_program_request_source(request)

    @classmethod
    def resolve_login_channel(cls, request: Request | None, *, prefer_wechat: bool = False) -> str:
        if prefer_wechat:
            return "mini_wechat"
        if cls._is_mini_program_request(request):
            return "mini_password"
        return "web_password"

    @staticmethod
    def _resolve_client_ip(request: Request | None) -> str | None:
        return AuthSmsService._resolve_client_ip(request)

    @classmethod
    def _build_sms_request_context(cls, request: Request | None) -> SmsRequestContext:
        return AuthSmsService.build_sms_request_context(request)

    @staticmethod
    def ensure_user_can_login(user: User, *, allow_pending: bool = False) -> None:
        if is_active_user_status(user.status):
            return
        if allow_pending and int(user.status) == int(UserStatus.PENDING_APPROVAL):
            return
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.USER_NOT_ACTIVE,
            message="当前账号未激活，请联系管理员。",
            detail="当前账号未激活，请联系管理员。",
        )

    def resolve_tenant_by_code(self, tenant_code: str) -> Tenant:
        tenant = self.repository.get_active_tenant_by_code(tenant_code=tenant_code)
        if tenant is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code=ErrorCode.TENANT_NOT_FOUND,
                message="目标租户不存在或已停用。",
                detail="目标租户不存在或已停用。",
            )
        return tenant

    def _resolve_login_tenant(self, *, tenant_code: str | None) -> Tenant | None:
        return self.login_service._resolve_login_tenant(tenant_code=tenant_code)

    def _resolve_case_invite_context_for_login(self, *, case_invite_token: str) -> tuple[Tenant, dict]:
        return self.login_service._resolve_case_invite_context_for_login(case_invite_token=case_invite_token)

    def resolve_login_context(
        self,
        *,
        tenant_code: str | None,
        case_invite_token: str | None,
    ) -> tuple[Tenant | None, dict | None]:
        return self.login_service.resolve_login_context(
            tenant_code=tenant_code,
            case_invite_token=case_invite_token,
        )

    def apply_case_invite_binding(
        self,
        *,
        user: User,
        invite_payload: dict | None,
    ) -> None:
        self.login_service.apply_case_invite_binding(
            user=user,
            invite_payload=invite_payload,
        )

    def _resolve_sms_login_user(
        self,
        *,
        phone: str,
        tenant_code: str | None,
        case_invite_token: str | None,
    ) -> tuple[User, dict | None]:
        return self.login_service._resolve_sms_login_user(
            phone=phone,
            tenant_code=tenant_code,
            case_invite_token=case_invite_token,
        )

    def send_phone_sms(self, *, request: Request, sms_in: SmsSendRequest) -> SmsSendResponse:
        return self.sms_auth_service.send_phone_sms(request=request, sms_in=sms_in)

    def verify_phone_sms(self, *, request: Request, sms_in: SmsVerifyRequest) -> SmsVerifyResponse:
        return self.sms_auth_service.verify_phone_sms(request=request, sms_in=sms_in)

    def login_by_sms_code(self, *, sms_in: SmsCodeLoginRequest, request: Request) -> Token:
        return self.login_service.login_by_sms_code(
            sms_in=sms_in,
            request=request,
        )

    def register_user(self, *, user_in: PhoneRegisterRequest) -> User:
        assert_phone_verified(
            self.db,
            phone=user_in.phone,
            purpose="register",
            verification_token=user_in.phone_verification_token,
        )

        tenant = self.resolve_tenant_for_registration(tenant_code=user_in.tenant_code)
        if tenant is None:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code=ErrorCode.VALIDATION_ERROR,
                message="无法确定注册目标租户，请传入 tenant_code 或先创建租户。",
                detail="无法确定注册目标租户，请传入 tenant_code 或先创建租户。",
            )
        if tenant.type == "organization":
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code=ErrorCode.INVITE_REQUIRED,
                message="机构律师必须通过邀请链接注册。",
                detail="机构律师必须通过邀请链接注册。",
            )

        existing_user = self.repository.get_user_by_tenant_phone(
            tenant_id=tenant.id,
            phone=user_in.phone,
        )
        if existing_user is not None:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                code=ErrorCode.USER_ALREADY_EXISTS,
                message="该手机号已注册。",
                detail="该手机号已注册。",
            )

        return create_user(
            self.db,
            user_in=UserRegister(
                phone=user_in.phone,
                password=user_in.password,
                real_name=user_in.real_name,
                tenant_code=user_in.tenant_code,
            ),
            tenant_id=tenant.id,
        )

    def login(self, *, user_in: UserLogin, request: Request) -> Token:
        return self.login_service.login(
            user_in=user_in,
            request=request,
        )

    def get_login_advice(self, *, advice_in: LoginAdviceRequest) -> LoginAdviceResponse:
        return self.login_service.get_login_advice(advice_in=advice_in)

    def change_password(
        self,
        *,
        current_user: User,
        password_in: PasswordChangeRequest,
    ) -> User:
        return change_user_password(
            self.db,
            user=current_user,
            password_in=password_in,
        )

    def register_user_from_invite(self, *, invite_in: InviteRegister) -> User:
        return register_user_from_invite(self.db, invite_in=invite_in)

    def resolve_tenant_for_registration(self, *, tenant_code: str | None) -> Tenant | None:
        return resolve_tenant_for_registration(self.db, tenant_code=tenant_code)
