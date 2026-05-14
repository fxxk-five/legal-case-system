from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.integrations.storage.service import get_storage_backend
from app.modules.files import access_service as _access_service
from app.modules.files import upload_service as _upload_service
from app.modules.files.models.file import File

prepare_upload_file_metadata = _upload_service.prepare_upload_file_metadata
validate_upload_policy_request = _upload_service.validate_upload_policy_request
validate_upload_size_bytes = _upload_service.validate_upload_size_bytes
save_upload_file = _upload_service.save_upload_file
create_stored_file_record = _upload_service.create_stored_file_record

create_file_access_grant = _access_service.create_file_access_grant
consume_file_access_grant = _access_service.consume_file_access_grant
create_direct_upload_completion_token = _access_service.create_direct_upload_completion_token
decode_direct_upload_completion_token = _access_service.decode_direct_upload_completion_token


def resolve_storage_path(file_record: File) -> Path:
    return get_storage_backend().resolve_local_path(storage_key=file_record.file_url)


def storage_object_exists(file_record: File) -> bool:
    return get_storage_backend().object_exists(storage_key=file_record.file_url)


def move_storage_object(*, source_key: str, target_key: str) -> None:
    get_storage_backend().move_object(source_key=source_key, target_key=target_key)


def delete_storage_object(file_record: File) -> str | None:
    backend = get_storage_backend()
    if settings.STORAGE_DELETE_POLICY == "archive":
        return backend.archive_object(storage_key=file_record.file_url)

    backend.delete_object(storage_key=file_record.file_url)
    return None


def build_storage_download_url(*, file_record: File, expires_seconds: int) -> str | None:
    return get_storage_backend().build_private_download_url(
        storage_key=file_record.file_url,
        file_name=file_record.file_name,
        content_type=file_record.file_type,
        expires_seconds=expires_seconds,
    )
