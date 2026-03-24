from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.legal_types import is_valid_legal_type, normalize_legal_type
from app.schemas.user import UserSummary
from app.schemas.validators import validate_phone


class CaseCreate(BaseModel):
    case_number: str | None = Field(default=None, min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=255)
    legal_type: str = Field(min_length=1, max_length=50)
    client_phone: str = Field(min_length=11, max_length=20)
    client_real_name: str = Field(default="未命名当事人", min_length=1, max_length=100)
    deadline: datetime | None = None

    @field_validator("client_phone")
    @classmethod
    def _validate_client_phone(cls, value: str) -> str:
        return validate_phone(value)

    @field_validator("legal_type")
    @classmethod
    def _validate_legal_type(cls, value: str) -> str:
        normalized = normalize_legal_type(value)
        if not is_valid_legal_type(normalized):
            raise ValueError("法律类型不合法。")
        return normalized


class CaseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    status: str | None = Field(default=None, min_length=1, max_length=30)
    legal_type: str | None = Field(default=None, min_length=1, max_length=50)
    deadline: datetime | None = None
    assigned_lawyer_id: int | None = None

    @field_validator("legal_type")
    @classmethod
    def _validate_legal_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_legal_type(value)
        if not is_valid_legal_type(normalized):
            raise ValueError("法律类型不合法。")
        return normalized


class CaseTimelineItem(BaseModel):
    event_type: str
    title: str
    description: str
    occurred_at: datetime
    operator_name: str | None = None


class CaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    case_number: str
    title: str
    legal_type: str
    status: str
    analysis_status: str
    analysis_progress: int
    deadline: datetime | None
    created_at: datetime
    updated_at: datetime
    client: UserSummary | None = None
    assigned_lawyer: UserSummary | None = None
    timeline: list[CaseTimelineItem] = Field(default_factory=list)


class CaseListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_number: str
    title: str
    legal_type: str
    status: str
    analysis_status: str
    analysis_progress: int
    created_at: datetime
    updated_at: datetime
    deadline: datetime | None
    client: UserSummary | None = None


class CaseInviteRead(BaseModel):
    case_id: int
    tenant_id: int
    token: str
    path: str


class CaseReportVersionRead(BaseModel):
    file_name: str
    report_scope: str
    generated_at: datetime
    is_latest: bool


class CaseReportAccessLinkRead(BaseModel):
    file_name: str
    access_url: str
    expires_in_seconds: int
