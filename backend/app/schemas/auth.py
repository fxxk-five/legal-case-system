from pydantic import BaseModel, ConfigDict, Field


class UserRegister(BaseModel):
    phone: str = Field(min_length=6, max_length=20)
    password: str = Field(min_length=6, max_length=128)
    real_name: str = Field(min_length=1, max_length=100)


class UserLogin(BaseModel):
    phone: str = Field(min_length=6, max_length=20)
    password: str = Field(min_length=6, max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str | None = None
    tenant_id: int | None = None
    role: str | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    phone: str
    real_name: str
    role: str
    is_tenant_admin: bool
    status: int
