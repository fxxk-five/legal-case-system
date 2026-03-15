from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from app.core.config import settings


@dataclass
class UploadPolicy:
    mode: str
    upload_url: str
    method: str = "POST"
    headers: dict[str, str] = field(default_factory=dict)
    form_fields: dict[str, str] = field(default_factory=dict)
    file_field_name: str = "upload"
    storage_key: str = ""
    public_base_url: str = ""


class BaseStorageBackend:
    backend_name = "base"

    def build_storage_key(self, *, tenant_id: int, case_id: int, file_name: str) -> str:
        suffix = Path(file_name).suffix
        generated_name = f"{uuid4().hex}{suffix}"
        return (Path(f"tenant_{tenant_id}") / f"case_{case_id}" / generated_name).as_posix()

    def build_upload_policy(self, *, tenant_id: int, case_id: int, file_name: str, content_type: str | None) -> UploadPolicy:
        raise NotImplementedError


class LocalStorageBackend(BaseStorageBackend):
    backend_name = "local"

    def build_upload_policy(self, *, tenant_id: int, case_id: int, file_name: str, content_type: str | None) -> UploadPolicy:
        return UploadPolicy(
            mode="server_proxy",
            upload_url=f"{settings.API_V1_STR}/files/upload?case_id={case_id}",
            storage_key=self.build_storage_key(tenant_id=tenant_id, case_id=case_id, file_name=file_name),
        )


def get_storage_backend() -> BaseStorageBackend:
    if settings.STORAGE_BACKEND == "local":
        return LocalStorageBackend()
    return LocalStorageBackend()
