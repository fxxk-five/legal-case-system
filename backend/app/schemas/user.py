from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.validators import validate_password, validate_phone


class LawyerCreate(BaseModel):
    phone: str = Field(min_length=11, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    real_name: str = Field(min_length=1, max_length=100)
    role: str = Field(default="lawyer", pattern="^(lawyer|org_lawyer|solo_lawyer|tenant_admin)$")

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, value: str) -> str:
        return validate_phone(value)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        return validate_password(value)


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    phone: str
    real_name: str
    role: str
    is_tenant_admin: bool
    status: int


class PendingUserSummary(UserSummary):
    pass


class UserStatusUpdate(BaseModel):
    status: int = Field(ge=0, le=3)
