from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.user import UserSummary


class FileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    case_id: int | None
    uploader_id: int | None
    file_name: str
    download_url: str
    file_type: str
    created_at: datetime
    uploader: UserSummary | None = None


class FileAccessLinkRead(BaseModel):
    file_id: int
    file_name: str
    access_url: str
    expires_in_seconds: int


class FileUploadPolicyRead(BaseModel):
    mode: str
    upload_url: str
    method: str
    headers: dict[str, str]
    form_fields: dict[str, str]
    file_field_name: str
    storage_key: str
    backend: str
