from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.validators import validate_password, validate_phone, validate_tenant_code


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
    admin_phone: str = Field(min_length=11, max_length=20)
    admin_password: str = Field(min_length=8, max_length=128)
    admin_real_name: str = Field(min_length=1, max_length=100)
    tenant_code: str | None = Field(default=None, min_length=3, max_length=50)

    @field_validator("admin_phone")
    @classmethod
    def _validate_phone(cls, value: str) -> str:
        return validate_phone(value)

    @field_validator("admin_password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        return validate_password(value)

    @field_validator("tenant_code")
    @classmethod
    def _validate_tenant_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_tenant_code(value)


class TenantCreateOrganization(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    contact_name: str = Field(min_length=1, max_length=100)
    admin_phone: str = Field(min_length=11, max_length=20)
    admin_password: str = Field(min_length=8, max_length=128)
    admin_real_name: str = Field(min_length=1, max_length=100)
    tenant_code: str | None = Field(default=None, min_length=3, max_length=50)

    @field_validator("admin_phone")
    @classmethod
    def _validate_phone(cls, value: str) -> str:
        return validate_phone(value)

    @field_validator("admin_password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        return validate_password(value)

    @field_validator("tenant_code")
    @classmethod
    def _validate_tenant_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_tenant_code(value)


class TenantJoinRequest(BaseModel):
    tenant_code: str = Field(min_length=3, max_length=50)
    phone: str = Field(min_length=11, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    real_name: str = Field(min_length=1, max_length=100)

    @field_validator("tenant_code")
    @classmethod
    def _validate_tenant_code(cls, value: str) -> str:
        return validate_tenant_code(value)

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, value: str) -> str:
        return validate_phone(value)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        return validate_password(value)


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


class TenantStatusUpdate(BaseModel):
    status: int = Field(ge=0, le=3)


class TenantAIBudgetRead(BaseModel):
    tenant_id: int
    ai_monthly_budget_limit: float | None = None
    ai_budget_degrade_model: str | None = None


class TenantAIBudgetUpdate(BaseModel):
    ai_monthly_budget_limit: float | None = Field(default=None, ge=0)
    ai_budget_degrade_model: str | None = Field(default=None, max_length=100)
    clear_monthly_budget_limit: bool = False
    clear_budget_degrade_model: bool = False


class CaseAIBudgetRead(BaseModel):
    case_id: int
    tenant_id: int
    ai_case_budget_limit: float | None = None


class CaseAIBudgetUpdate(BaseModel):
    ai_case_budget_limit: float | None = Field(default=None, ge=0)
    clear_case_budget_limit: bool = False
