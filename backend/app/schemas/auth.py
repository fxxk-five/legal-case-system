from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.validators import validate_password, validate_phone, validate_sms_code, validate_tenant_code


class UserRegister(BaseModel):
    phone: str = Field(min_length=11, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    real_name: str = Field(min_length=1, max_length=100)
    tenant_code: str | None = Field(default=None, min_length=3, max_length=50)

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, value: str) -> str:
        return validate_phone(value)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        return validate_password(value)

    @field_validator("tenant_code")
    @classmethod
    def _validate_tenant_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_tenant_code(value)


class PhoneRegisterRequest(BaseModel):
    phone: str = Field(min_length=11, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    real_name: str = Field(min_length=1, max_length=100)
    tenant_code: str | None = Field(default=None, min_length=3, max_length=50)
    phone_verification_token: str = Field(min_length=16, max_length=255)

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, value: str) -> str:
        return validate_phone(value)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        return validate_password(value)

    @field_validator("tenant_code")
    @classmethod
    def _validate_tenant_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_tenant_code(value)


class UserLogin(BaseModel):
    phone: str = Field(min_length=11, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    tenant_code: str | None = Field(default=None, min_length=3, max_length=50)

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, value: str) -> str:
        return validate_phone(value)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        return validate_password(value)

    @field_validator("tenant_code")
    @classmethod
    def _validate_tenant_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_tenant_code(value)


class SmsSendRequest(BaseModel):
    phone: str = Field(min_length=11, max_length=20)
    purpose: str = Field(default="register", pattern="^(register|login)$")

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, value: str) -> str:
        return validate_phone(value)


class SmsSendResponse(BaseModel):
    phone: str
    expires_in_seconds: int
    retry_after_seconds: int
    request_id: str


class SmsVerifyRequest(BaseModel):
    phone: str = Field(min_length=11, max_length=20)
    code: str = Field(min_length=6, max_length=6)
    purpose: str = Field(default="register", pattern="^(register|login)$")

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, value: str) -> str:
        return validate_phone(value)

    @field_validator("code")
    @classmethod
    def _validate_code(cls, value: str) -> str:
        return validate_sms_code(value)


class SmsVerifyResponse(BaseModel):
    phone: str
    verification_token: str
    expires_in_seconds: int


class SmsCodeLoginRequest(BaseModel):
    phone: str = Field(min_length=11, max_length=20)
    code: str = Field(min_length=6, max_length=6)
    tenant_code: str | None = Field(default=None, min_length=3, max_length=50)

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, value: str) -> str:
        return validate_phone(value)

    @field_validator("code")
    @classmethod
    def _validate_code(cls, value: str) -> str:
        return validate_sms_code(value)

    @field_validator("tenant_code")
    @classmethod
    def _validate_tenant_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_tenant_code(value)


class WechatMiniLogin(BaseModel):
    code: str = Field(min_length=1, max_length=255)
    case_invite_token: str | None = Field(default=None, min_length=16, max_length=4096)
    lawyer_invite_token: str | None = Field(default=None, min_length=16, max_length=4096)


class WechatMiniPhoneLogin(BaseModel):
    phone_code: str = Field(min_length=1, max_length=255)
    wx_session_ticket: str = Field(min_length=16, max_length=2048)
    tenant_code: str | None = Field(default=None, min_length=3, max_length=50)
    case_invite_token: str | None = Field(default=None, min_length=16, max_length=4096)
    lawyer_invite_token: str | None = Field(default=None, min_length=16, max_length=4096)
    real_name: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("tenant_code")
    @classmethod
    def _validate_tenant_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_tenant_code(value)


class WechatMiniBindExisting(BaseModel):
    phone: str = Field(min_length=11, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    wx_session_ticket: str = Field(min_length=16, max_length=2048)
    tenant_code: str | None = Field(default=None, min_length=3, max_length=50)

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, value: str) -> str:
        return validate_phone(value)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        return validate_password(value)

    @field_validator("tenant_code")
    @classmethod
    def _validate_tenant_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_tenant_code(value)


class WechatMiniBind(BaseModel):
    wx_session_ticket: str = Field(min_length=16, max_length=2048)
    phone: str = Field(min_length=11, max_length=20)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    real_name: str | None = Field(default=None, min_length=1, max_length=100)
    tenant_id: int | None = None
    tenant_code: str | None = Field(default=None, min_length=3, max_length=50)
    role: str = Field(default="client", pattern="^(lawyer|org_lawyer|solo_lawyer|client|tenant_admin|super_admin)$")
    case_invite_token: str | None = None

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, value: str) -> str:
        return validate_phone(value)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_password(value)

    @field_validator("tenant_code")
    @classmethod
    def _validate_tenant_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_tenant_code(value)


class Token(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=16, max_length=2048)


class LogoutRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=16, max_length=2048)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    phone: str
    real_name: str
    role: str
    is_tenant_admin: bool
    status: int


class WechatMiniLoginResult(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    wechat_openid: str
    need_bind_phone: bool
    login_state: str = "LOGGED_IN"
    wx_session_ticket: str | None = None
    user: UserRead | None = None


class WebWechatLoginTicketCreateRead(BaseModel):
    ticket: str
    status: str
    expires_at: datetime
    expires_in_seconds: int
    mini_program_page: str
    mini_program_scene: str
    launch_path: str
    qr_code_url: str
    poll_url: str


class WebWechatLoginTicketStatusRead(BaseModel):
    ticket: str
    status: str
    expires_at: datetime
    expires_in_seconds: int
    confirmed_at: datetime | None = None
    consumed_at: datetime | None = None
    can_exchange: bool = False
    user: UserRead | None = None


class TokenPayload(BaseModel):
    sub: str | None = None
    tenant_id: int | None = None
    role: str | None = None
    is_tenant_admin: bool | None = None
    token_type: str | None = None
    sid: int | None = None
