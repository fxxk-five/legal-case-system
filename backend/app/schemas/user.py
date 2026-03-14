from pydantic import BaseModel, ConfigDict, Field


class LawyerCreate(BaseModel):
    phone: str = Field(min_length=6, max_length=20)
    password: str = Field(min_length=6, max_length=128)
    real_name: str = Field(min_length=1, max_length=100)
    role: str = "lawyer"


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
    status: int = Field(ge=0, le=1)
