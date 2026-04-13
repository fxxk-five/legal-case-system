from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.core.config import settings
from app.core.errors import AppError, ErrorCode


def storage_error(message: str, *, detail: str | None = None) -> AppError:
    return AppError(
        status_code=500,
        code=ErrorCode.STORAGE_ERROR,
        message=message,
        detail=detail or message,
    )


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
    completion_url: str | None = None
    completion_token: str | None = None
    expires_in_seconds: int | None = None


@dataclass
class StorageObjectInfo:
    storage_key: str
    modified_at: datetime | None = None

    @property
    def file_name(self) -> str:
        return Path(self.storage_key).name


class BaseStorageBackend:
    backend_name = "base"

    def build_storage_key(self, *, tenant_id: int, case_id: int, file_name: str) -> str:
        suffix = Path(file_name).suffix
        generated_name = f"{uuid4().hex}{suffix}"
        return (Path(f"tenant_{tenant_id}") / f"case_{case_id}" / "files" / generated_name).as_posix()

    def build_pending_storage_key(self, *, tenant_id: int, case_id: int, file_name: str) -> str:
        suffix = Path(file_name).suffix
        generated_name = f"{uuid4().hex}{suffix}"
        return (Path(f"tenant_{tenant_id}") / f"case_{case_id}" / settings.STORAGE_PENDING_PREFIX / generated_name).as_posix()

    def build_retention_storage_key(self, *, storage_key: str, archived_at: datetime | None = None) -> str:
        timestamp = (archived_at or datetime.now(timezone.utc)).strftime("%Y%m%d%H%M%S")
        return (Path(settings.STORAGE_RETENTION_PREFIX) / f"deleted_at={timestamp}" / Path(storage_key)).as_posix()

    def build_upload_policy(self, *, tenant_id: int, case_id: int, file_name: str, content_type: str | None) -> UploadPolicy:
        raise NotImplementedError

    def save_local_file(
        self,
        *,
        local_path: Path,
        storage_key: str,
        content_type: str,
    ) -> None:
        raise NotImplementedError

    def save_bytes(
        self,
        *,
        data: bytes,
        storage_key: str,
        content_type: str,
    ) -> None:
        raise NotImplementedError

    def move_object(self, *, source_key: str, target_key: str) -> None:
        raise NotImplementedError

    def build_private_download_url(
        self,
        *,
        storage_key: str,
        file_name: str,
        content_type: str | None,
        expires_seconds: int,
    ) -> str | None:
        return None

    def delete_object(self, *, storage_key: str) -> None:
        raise NotImplementedError

    def archive_object(self, *, storage_key: str) -> str | None:
        raise NotImplementedError

    def object_exists(self, *, storage_key: str) -> bool:
        raise NotImplementedError

    def get_object_size(self, *, storage_key: str) -> int | None:
        raise NotImplementedError

    def resolve_local_path(self, *, storage_key: str) -> Path:
        raise NotImplementedError

    def list_objects(self, *, prefix: str, suffix: str | None = None) -> list[StorageObjectInfo]:
        raise NotImplementedError
