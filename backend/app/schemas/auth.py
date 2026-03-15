from pydantic import BaseModel, ConfigDict, Field


class UserRegister(BaseModel):
    phone: str = Field(min_length=6, max_length=20)
    password: str = Field(min_length=6, max_length=128)
    real_name: str = Field(min_length=1, max_length=100)
    tenant_code: str | None = Field(default=None, min_length=3, max_length=50)


class UserLogin(BaseModel):
    phone: str = Field(min_length=6, max_length=20)
    password: str = Field(min_length=6, max_length=128)
    tenant_code: str | None = Field(default=None, min_length=3, max_length=50)


class WechatMiniLogin(BaseModel):
    code: str = Field(min_length=1, max_length=255)


class WechatMiniBind(BaseModel):
    wechat_openid: str = Field(min_length=6, max_length=100)
    phone: str = Field(min_length=6, max_length=20)
    password: str | None = Field(default=None, min_length=6, max_length=128)
    real_name: str | None = Field(default=None, min_length=1, max_length=100)
    tenant_id: int | None = None
    tenant_code: str | None = Field(default=None, min_length=3, max_length=50)
    role: str = Field(default="client", pattern="^(lawyer|client|tenant_admin)$")
    case_invite_token: str | None = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class WechatMiniLoginResult(BaseModel):
    access_token: str | None = None
    token_type: str = "bearer"
    wechat_openid: str
    need_bind_phone: bool
    user: "UserRead | None" = None


class TokenPayload(BaseModel):
    sub: str | None = None
    tenant_id: int | None = None
    role: str | None = None
    is_tenant_admin: bool | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    phone: str
    real_name: str
    role: str
    is_tenant_admin: bool
    status: int
