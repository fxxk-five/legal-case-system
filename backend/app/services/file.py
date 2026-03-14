from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.file import File


def save_upload_file(*, tenant_id: int, case_id: int, uploader_id: int, upload: UploadFile, db: Session) -> File:
    storage_root = Path(settings.LOCAL_STORAGE_DIR)
    target_dir = storage_root / f"tenant_{tenant_id}" / f"case_{case_id}"
    target_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(upload.filename or "").suffix
    generated_name = f"{uuid4().hex}{suffix}"
    target_path = target_dir / generated_name

    with target_path.open("wb") as file_obj:
        file_obj.write(upload.file.read())

    record = File(
        tenant_id=tenant_id,
        case_id=case_id,
        uploader_id=uploader_id,
        file_name=upload.filename or generated_name,
        file_url=str(target_path.as_posix()),
        file_type=upload.content_type or "application/octet-stream",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
