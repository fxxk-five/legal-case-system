from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.integrations.storage.service import get_storage_backend
from app.modules.files.models.file import File
from app.modules.files import upload_policy_service as _upload_policy_service
from app.modules.files.repository import FilesRepository

_UPLOAD_CHUNK_SIZE = 1024 * 1024

prepare_upload_file_metadata = _upload_policy_service.prepare_upload_file_metadata
validate_upload_policy_request = _upload_policy_service.validate_upload_policy_request
validate_upload_size_bytes = _upload_policy_service.validate_upload_size_bytes


def _delete_file_safely(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


def _write_upload_stream(*, upload: UploadFile, target_path: Path) -> int:
    total_size = 0

    try:
        with target_path.open("wb") as file_obj:
            while True:
                chunk = upload.file.read(_UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                total_size += len(chunk)
                validate_upload_size_bytes(total_size)
                file_obj.write(chunk)
    except AppError:
        _delete_file_safely(target_path)
        raise
    except OSError as exc:
        _delete_file_safely(target_path)
        raise AppError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code=ErrorCode.STORAGE_ERROR,
            message="Failed to persist uploaded file.",
            detail="Failed to persist uploaded file.",
        ) from exc
    finally:
        upload.file.close()

    return total_size


def _write_upload_to_temp_file(*, upload: UploadFile, suffix: str) -> Path:
    fd, temp_path = tempfile.mkstemp(prefix="legal-upload-", suffix=suffix)
    os.close(fd)
    temp_file = Path(temp_path)
    try:
        _write_upload_stream(upload=upload, target_path=temp_file)
        return temp_file
    except Exception:
        _delete_file_safely(temp_file)
        raise


def save_upload_file(
    *,
    tenant_id: int,
    case_id: int,
    uploader_id: int,
    uploader_role: str,
    description: str | None = None,
    upload: UploadFile,
    db: Session,
) -> File:
    repo = FilesRepository(db)
    normalized_file_name, detected_mime = prepare_upload_file_metadata(
        file_name=upload.filename,
        content_type=upload.content_type,
    )
    suffix = Path(normalized_file_name).suffix.lower().strip()
    backend = get_storage_backend()
    storage_key = backend.build_storage_key(
        tenant_id=tenant_id,
        case_id=case_id,
        file_name=normalized_file_name,
    )
    temp_path = _write_upload_to_temp_file(upload=upload, suffix=suffix)
    try:
        backend.save_local_file(
            local_path=temp_path,
            storage_key=storage_key,
            content_type=detected_mime,
        )
    except AppError:
        _delete_file_safely(temp_path)
        raise
    except Exception as exc:  # noqa: BLE001
        _delete_file_safely(temp_path)
        raise AppError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code=ErrorCode.STORAGE_ERROR,
            message="Failed to persist uploaded file.",
            detail="Failed to persist uploaded file.",
        ) from exc

    record = File(
        tenant_id=tenant_id,
        case_id=case_id,
        uploader_id=uploader_id,
        uploader_role=uploader_role,
        file_name=normalized_file_name,
        file_url=storage_key,
        file_type=detected_mime,
        description=description,
        parse_status="pending",
    )
    repo.save_commit_refresh(record)
    return record


def create_stored_file_record(
    *,
    tenant_id: int,
    case_id: int,
    uploader_id: int,
    uploader_role: str,
    storage_key: str,
    file_name: str,
    content_type: str | None,
    description: str | None = None,
    db: Session,
) -> File:
    repo = FilesRepository(db)
    normalized_file_name, detected_mime = prepare_upload_file_metadata(
        file_name=file_name,
        content_type=content_type,
    )

    record = File(
        tenant_id=tenant_id,
        case_id=case_id,
        uploader_id=uploader_id,
        uploader_role=uploader_role,
        file_name=normalized_file_name,
        file_url=storage_key,
        file_type=detected_mime,
        description=description,
        parse_status="pending",
    )
    repo.save(record)
    try:
        repo.commit()
    except IntegrityError:
        repo.rollback()
        existing_record = repo.find_file_by_storage_key(tenant_id=tenant_id, storage_key=storage_key)
        if existing_record is None:
            raise
        return existing_record
    repo.refresh(record)
    return record
