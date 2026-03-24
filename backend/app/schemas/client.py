from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.validators import validate_phone


class ClientCaseSummary(BaseModel):
    id: int
    case_number: str
    title: str
    legal_type: str
    status: str
    deadline: datetime | None = None
    updated_at: datetime
    assigned_lawyer_name: str | None = None


class ClientListItem(BaseModel):
    id: int
    real_name: str
    phone: str
    status: int
    created_at: datetime
    updated_at: datetime
    case_count: int
    last_uploaded_at: datetime | None = None


class ClientDetailRead(BaseModel):
    id: int
    real_name: str
    phone: str
    status: int
    created_at: datetime
    updated_at: datetime
    case_count: int
    last_uploaded_at: datetime | None = None
    cases: list[ClientCaseSummary] = Field(default_factory=list)


class ClientUpdate(BaseModel):
    real_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=11, max_length=20)

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, value: str) -> str:
        return validate_phone(value)
