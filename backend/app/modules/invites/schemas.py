from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.validators import validate_password, validate_phone


class InviteCreateResponse(BaseModel):
    token: str
    register_path: str
    expires_at: datetime


class InviteRegister(BaseModel):
    token: str
    phone: str = Field(min_length=11, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    real_name: str = Field(min_length=1, max_length=100)
    phone_verification_token: str | None = Field(default=None, min_length=16, max_length=255)

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, value: str) -> str:
        return validate_phone(value)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        return validate_password(value)


class InviteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    invited_by_user_id: int
    role: str
    token: str
    expires_at: datetime
    status: str
