from __future__ import annotations

from pathlib import Path

from fastapi import status

from app.core.config import settings
from app.core.errors import AppError, ErrorCode

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


def validate_upload_size_bytes(size_bytes: int) -> None:
    max_size_bytes = settings.FILE_UPLOAD_MAX_SIZE_BYTES
    if size_bytes > max_size_bytes:
        raise _upload_invalid(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            message=f"Uploaded file exceeds max size limit ({max_size_bytes} bytes).",
        )
