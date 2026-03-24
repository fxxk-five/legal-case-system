from __future__ import annotations

import os
import tempfile
from datetime import timedelta
from pathlib import Path

from fastapi import UploadFile, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.security import create_access_token
from app.models.file import File
from app.services.storage import get_storage_backend

_UPLOAD_CHUNK_SIZE = 1024 * 1024

_DANGEROUS_EXTENSIONS = {
    ".exe",
    ".bat",
    ".cmd",
    ".com",
    ".scr",
    ".ps1",
    ".sh",
    ".vbs",
    ".js",
    ".jar",
    ".msi",
    ".php",
    ".py",
    ".rb",
    ".pl",
    ".cgi",
    ".dll",
    ".so",
    ".apk",
}

_DANGEROUS_MIME_TYPES = {
    "application/x-msdownload",
    "application/x-sh",
    "application/x-bat",
    "application/x-cmd",
    "application/x-dosexec",
    "application/javascript",
    "text/javascript",
    "text/x-python",
    "application/x-python-code",
    "application/x-php",
    "application/x-perl",
    "application/x-ruby",
    "application/x-msdos-program",
    "application/vnd.microsoft.portable-executable",
}

_EXTENSION_TO_ALLOWED_MIME = {
    ".pdf": {"application/pdf"},
    ".doc": {"application/msword"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".xls": {"application/vnd.ms-excel"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg", "image/jpg"},
    ".jpeg": {"image/jpeg", "image/jpg"},
    ".txt": {"text/plain"},
}

_EXTENSION_TO_DETECTED_MIME = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".txt": "text/plain",
}


def _normalize_content_type(content_type: str | None) -> str:
    return (content_type or "").split(";", maxsplit=1)[0].strip().lower()


def _upload_invalid(*, status_code: int, message: str) -> AppError:
    return AppError(
        status_code=status_code,
        code=ErrorCode.FILE_UPLOAD_INVALID,
        message=message,
        detail=message,
    )


def _file_token_invalid(message: str) -> AppError:
    return AppError(
        status_code=status.HTTP_400_BAD_REQUEST,
        code=ErrorCode.FILE_TOKEN_INVALID,
        message=message,
        detail=message,
    )


def _validate_file_name(filename: str | None) -> str:
    if filename is None:
        raise _upload_invalid(status_code=status.HTTP_400_BAD_REQUEST, message="Uploaded file name is required.")

    normalized = filename.strip()
    if not normalized:
        raise _upload_invalid(status_code=status.HTTP_400_BAD_REQUEST, message="Uploaded file name is required.")
    if len(normalized) > 255:
        raise _upload_invalid(status_code=status.HTTP_400_BAD_REQUEST, message="Uploaded file name exceeds 255 characters.")
    if any(ord(ch) < 32 for ch in normalized):
        raise _upload_invalid(status_code=status.HTTP_400_BAD_REQUEST, message="Uploaded file name contains control characters.")
    if "\x00" in normalized:
        raise _upload_invalid(status_code=status.HTTP_400_BAD_REQUEST, message="Uploaded file name contains invalid characters.")
    if any(token in normalized for token in ("../", "..\\", "/", "\\")):
        raise _upload_invalid(status_code=status.HTTP_400_BAD_REQUEST, message="Uploaded file name cannot contain path separators.")

    return normalized


def _validate_file_type(*, file_name: str, content_type: str | None) -> tuple[str, str]:
    extension = Path(file_name).suffix.lower().strip()
    normalized_content_type = _normalize_content_type(content_type)

    if extension in _DANGEROUS_EXTENSIONS or normalized_content_type in _DANGEROUS_MIME_TYPES:
        raise _upload_invalid(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            message="Potentially dangerous file types are not allowed.",
        )

    allowed_extensions = {ext.lower().strip() for ext in settings.FILE_UPLOAD_ALLOWED_EXTENSIONS}
    allowed_mime_types = {mime.lower().strip() for mime in settings.FILE_UPLOAD_ALLOWED_MIME_TYPES}

    if extension not in allowed_extensions:
        raise _upload_invalid(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            message=f"Unsupported file extension: {extension or 'none'}.",
        )

    expected_mime_types = _EXTENSION_TO_ALLOWED_MIME.get(extension, set())

    if normalized_content_type and normalized_content_type != "application/octet-stream":
        if normalized_content_type not in allowed_mime_types:
            raise _upload_invalid(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                message=f"Unsupported file MIME type: {normalized_content_type}.",
            )
        if expected_mime_types and normalized_content_type not in expected_mime_types:
            raise _upload_invalid(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                message=(
                    f"File extension and MIME type do not match: extension {extension}, "
                    f"MIME type {normalized_content_type}."
                ),
            )

    detected_mime = _EXTENSION_TO_DETECTED_MIME.get(extension, "application/octet-stream")
    return extension, detected_mime


def prepare_upload_file_metadata(*, file_name: str, content_type: str | None = None) -> tuple[str, str]:
    normalized_name = _validate_file_name(file_name)
    _, detected_mime = _validate_file_type(file_name=normalized_name, content_type=content_type)
    return normalized_name, detected_mime


def validate_upload_policy_request(*, file_name: str, content_type: str | None = None) -> tuple[str, str]:
    return prepare_upload_file_metadata(file_name=file_name, content_type=content_type)


def _delete_file_safely(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


def _write_upload_stream(*, upload: UploadFile, target_path: Path) -> int:
    total_size = 0
    max_size_bytes = settings.FILE_UPLOAD_MAX_SIZE_BYTES

    try:
        with target_path.open("wb") as file_obj:
            while True:
                chunk = upload.file.read(_UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > max_size_bytes:
                    raise _upload_invalid(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        message=f"Uploaded file exceeds max size limit ({max_size_bytes} bytes).",
                    )
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
    db.add(record)
    db.commit()
    db.refresh(record)
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
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


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


def create_file_access_token(*, file_id: int, tenant_id: int) -> str:
    return create_access_token(
        subject=f"file-access:{file_id}",
        expires_delta=timedelta(minutes=settings.FILE_ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_data={"file_id": file_id, "tenant_id": tenant_id, "scene": "file_access"},
    )


def decode_file_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise _file_token_invalid("File access token is invalid or expired.") from exc

    if payload.get("scene") != "file_access":
        raise _file_token_invalid("File access token is invalid or expired.")

    if not isinstance(payload.get("file_id"), int) or not isinstance(payload.get("tenant_id"), int):
        raise _file_token_invalid("File access token is invalid or expired.")

    return payload


def create_direct_upload_completion_token(
    *,
    tenant_id: int,
    case_id: int,
    uploader_id: int,
    uploader_role: str,
    storage_key: str,
    file_name: str,
    content_type: str,
    upload_storage_key: str | None = None,
) -> str:
    return create_access_token(
        subject=f"direct-upload-complete:{tenant_id}:{case_id}:{uploader_id}:{storage_key}",
        expires_delta=timedelta(minutes=settings.FILE_ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_data={
            "tenant_id": tenant_id,
            "case_id": case_id,
            "uploader_id": uploader_id,
            "uploader_role": uploader_role,
            "storage_key": storage_key,
            "file_name": file_name,
            "content_type": content_type,
            "scene": "direct_upload_complete",
            "upload_storage_key": upload_storage_key or storage_key,
        },
    )


def decode_direct_upload_completion_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise _file_token_invalid("Direct upload completion token is invalid or expired.") from exc

    if payload.get("scene") != "direct_upload_complete":
        raise _file_token_invalid("Direct upload completion token is invalid or expired.")

    int_fields = ("tenant_id", "case_id", "uploader_id")
    str_fields = ("uploader_role", "storage_key", "file_name", "content_type", "upload_storage_key")

    if any(not isinstance(payload.get(field_name), int) for field_name in int_fields):
        raise _file_token_invalid("Direct upload completion token is invalid or expired.")
    if any(not isinstance(payload.get(field_name), str) or not str(payload.get(field_name)).strip() for field_name in str_fields):
        raise _file_token_invalid("Direct upload completion token is invalid or expired.")

    return payload
