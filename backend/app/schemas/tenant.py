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
