from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.models.file import File


def save_upload_file(*, tenant_id: int, case_id: int, uploader_id: int, upload: UploadFile, db: Session) -> File:
    if upload.filename is None or not upload.filename.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="上传文件名不能为空。")

    storage_root = Path(settings.LOCAL_STORAGE_DIR)
    target_dir = storage_root / f"tenant_{tenant_id}" / f"case_{case_id}"
    target_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(upload.filename or "").suffix
    generated_name = f"{uuid4().hex}{suffix}"
    target_path = target_dir / generated_name
    storage_key = Path(f"tenant_{tenant_id}") / f"case_{case_id}" / generated_name

    with target_path.open("wb") as file_obj:
        file_obj.write(upload.file.read())

    record = File(
        tenant_id=tenant_id,
        case_id=case_id,
        uploader_id=uploader_id,
        file_name=upload.filename or generated_name,
        file_url=str(storage_key.as_posix()),
        file_type=upload.content_type or "application/octet-stream",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def resolve_storage_path(file_record: File) -> Path:
    file_ref = Path(file_record.file_url)
    if file_ref.is_absolute():
        return file_ref
    local_root = Path(settings.LOCAL_STORAGE_DIR)
    candidates = []

    if len(file_ref.parts) > 0 and file_ref.parts[0] == local_root.name:
        candidates.append(Path(*file_ref.parts))

    candidates.append(local_root / file_ref)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0]


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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件访问令牌无效或已过期。",
        ) from exc

    if payload.get("scene") != "file_access":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件访问令牌无效或已过期。")

    if not isinstance(payload.get("file_id"), int) or not isinstance(payload.get("tenant_id"), int):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件访问令牌无效或已过期。")

    return payload
