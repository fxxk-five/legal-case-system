from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.security import create_access_token
from app.modules.files.repository import FilesRepository


def _file_token_invalid(message: str) -> AppError:
    return AppError(
        status_code=status.HTTP_400_BAD_REQUEST,
        code=ErrorCode.FILE_TOKEN_INVALID,
        message=message,
        detail=message,
    )


def _hash_ephemeral_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def create_file_access_grant(
    db: Session,
    *,
    file_id: int,
    tenant_id: int,
    issued_to_user_id: int | None,
) -> str:
    token = secrets.token_urlsafe(32)
    FilesRepository(db).create_file_access_grant(
        file_id=file_id,
        tenant_id=tenant_id,
        issued_to_user_id=issued_to_user_id,
        token_hash=_hash_ephemeral_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.FILE_ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return token


def consume_file_access_grant(
    db: Session,
    token: str,
    *,
    expected_user_id: int | None = None,
    expected_tenant_id: int | None = None,
) -> dict[str, int]:
    now = datetime.now(timezone.utc)
    repo = FilesRepository(db)
    grant = repo.get_file_access_grant_by_token_hash(token_hash=_hash_ephemeral_token(token))
    expires_at = _as_utc(grant.expires_at) if grant is not None else None
    if grant is None or grant.used_at is not None or expires_at is None or expires_at <= now:
        raise _file_token_invalid("File access token is invalid or expired.")
    if expected_tenant_id is not None and int(grant.tenant_id) != int(expected_tenant_id):
        raise _file_token_invalid("File access token is invalid or expired.")
    if grant.issued_to_user_id is not None and expected_user_id != int(grant.issued_to_user_id):
        raise _file_token_invalid("File access token is invalid or expired.")
    repo.mark_file_access_grant_used(grant=grant, used_at=now)
    return {
        "file_id": int(grant.file_id),
        "tenant_id": int(grant.tenant_id),
        "issued_to_user_id": int(grant.issued_to_user_id) if grant.issued_to_user_id is not None else 0,
    }


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
