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
    file_url: str
    file_type: str
    created_at: datetime
    uploader: UserSummary | None = None
