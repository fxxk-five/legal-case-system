from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserSummary


class CaseCreate(BaseModel):
    case_number: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=255)
    client_phone: str = Field(min_length=6, max_length=20)
    client_real_name: str = Field(default="未命名当事人", min_length=1, max_length=100)
    deadline: datetime | None = None


class CaseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    status: str | None = Field(default=None, min_length=1, max_length=30)
    deadline: datetime | None = None
    assigned_lawyer_id: int | None = None


class CaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    case_number: str
    title: str
    status: str
    deadline: datetime | None
    created_at: datetime
    client: UserSummary | None = None
    assigned_lawyer: UserSummary | None = None
    timeline: list["CaseTimelineItem"] = Field(default_factory=list)


class CaseListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_number: str
    title: str
    status: str
    created_at: datetime
    deadline: datetime | None
    client: UserSummary | None = None


class CaseInviteRead(BaseModel):
    case_id: int
    tenant_id: int
    token: str
    path: str


class CaseTimelineItem(BaseModel):
    event_type: str
    title: str
    description: str
    occurred_at: datetime
