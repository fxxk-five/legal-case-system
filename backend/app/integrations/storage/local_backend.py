from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.integrations.storage.base import BaseStorageBackend, StorageObjectInfo, UploadPolicy, storage_error


class LocalStorageBackend(BaseStorageBackend):
    backend_name = "local"

    def build_upload_policy(self, *, tenant_id: int, case_id: int, file_name: str, content_type: str | None) -> UploadPolicy:
        return UploadPolicy(
            mode="server_proxy",
            upload_url=f"{settings.API_V1_STR}/files/upload?case_id={case_id}",
            storage_key=self.build_storage_key(tenant_id=tenant_id, case_id=case_id, file_name=file_name),
        )

    def save_local_file(
        self,
        *,
        local_path: Path,
        storage_key: str,
        content_type: str,
    ) -> None:
        target_path = self.resolve_local_path(storage_key=storage_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(local_path), str(target_path))

    def save_bytes(
        self,
        *,
        data: bytes,
        storage_key: str,
        content_type: str,
    ) -> None:
        target_path = self.resolve_local_path(storage_key=storage_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(data)

    def move_object(self, *, source_key: str, target_key: str) -> None:
        source_path = self.resolve_local_path(storage_key=source_key)
        if not source_path.exists():
            raise storage_error(
                "Source object does not exist.",
                detail="Source object does not exist.",
            )

        target_path = self.resolve_local_path(storage_key=target_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_path), str(target_path))

    def delete_object(self, *, storage_key: str) -> None:
        file_path = self.resolve_local_path(storage_key=storage_key)
        try:
            if file_path.exists():
                file_path.unlink()
        except OSError:
            pass

    def archive_object(self, *, storage_key: str) -> str | None:
        source_path = self.resolve_local_path(storage_key=storage_key)
        if not source_path.exists():
            return None

        archived_key = self.build_retention_storage_key(storage_key=storage_key)
        archived_path = self.resolve_local_path(storage_key=archived_key)
        archived_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_path), str(archived_path))
        return archived_key

    def object_exists(self, *, storage_key: str) -> bool:
        return self.resolve_local_path(storage_key=storage_key).exists()

    def get_object_size(self, *, storage_key: str) -> int | None:
        file_path = self.resolve_local_path(storage_key=storage_key)
        if not file_path.exists():
            return None
        return file_path.stat().st_size

    def resolve_local_path(self, *, storage_key: str) -> Path:
        file_ref = Path(storage_key)
        local_root = Path(settings.LOCAL_STORAGE_DIR)
        if file_ref.is_absolute():
            return file_ref
        if len(file_ref.parts) > 0 and file_ref.parts[0] == local_root.name:
            return Path(*file_ref.parts)
        return local_root / file_ref

    def list_objects(self, *, prefix: str, suffix: str | None = None) -> list[StorageObjectInfo]:
        target_dir = self.resolve_local_path(storage_key=prefix)
        if not target_dir.exists() or not target_dir.is_dir():
            return []

        local_root = Path(settings.LOCAL_STORAGE_DIR)
        objects: list[StorageObjectInfo] = []
        for path in target_dir.iterdir():
            if not path.is_file():
                continue
            if suffix and not path.name.endswith(suffix):
                continue
            try:
                storage_key = path.relative_to(local_root).as_posix()
            except ValueError:
                storage_key = path.as_posix()
            objects.append(
                StorageObjectInfo(
                    storage_key=storage_key,
                    modified_at=datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc),
                )
            )
        return objects
