from pydantic import BaseModel, ConfigDict, Field


class TenantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_code: str
    name: str
    type: str
    status: int


class TenantUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class TenantCreatePersonal(BaseModel):
    workspace_name: str = Field(min_length=1, max_length=100)
    admin_phone: str = Field(min_length=6, max_length=20)
    admin_password: str = Field(min_length=6, max_length=128)
    admin_real_name: str = Field(min_length=1, max_length=100)
    tenant_code: str | None = Field(default=None, min_length=3, max_length=50)


class TenantCreateOrganization(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    contact_name: str = Field(min_length=1, max_length=100)
    admin_phone: str = Field(min_length=6, max_length=20)
    admin_password: str = Field(min_length=6, max_length=128)
    admin_real_name: str = Field(min_length=1, max_length=100)
    tenant_code: str | None = Field(default=None, min_length=3, max_length=50)


class TenantJoinRequest(BaseModel):
    tenant_code: str = Field(min_length=3, max_length=50)
    phone: str = Field(min_length=6, max_length=20)
    password: str = Field(min_length=6, max_length=128)
    real_name: str = Field(min_length=1, max_length=100)


class TenantPreview(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_code: str
    name: str
    type: str
    status: int


class TenantCreateResult(BaseModel):
    tenant: TenantRead
    access_token: str
    token_type: str = "bearer"
    user_id: int


class TenantJoinResult(BaseModel):
    tenant: TenantRead
    user_id: int
    status: int
    message: str
