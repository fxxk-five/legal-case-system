from pathlib import Path

from fastapi import APIRouter, Depends, File as FastAPIFile, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.case import Case
from app.models.file import File
from app.models.user import User
from app.schemas.file import FileRead
from app.services.file import save_upload_file


router = APIRouter(prefix="/files", tags=["Files"])


def _get_case(db: Session, *, case_id: int, tenant_id: int) -> Case:
    case = db.query(Case).filter(Case.id == case_id, Case.tenant_id == tenant_id).first()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="案件不存在。")
    return case


def _ensure_case_access(case: Case, current_user: User) -> None:
    if current_user.role == "client" and case.client_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该案件文件。")


@router.post("/upload", response_model=FileRead, status_code=status.HTTP_201_CREATED)
def upload_case_file(
    case_id: int,
    upload: UploadFile = FastAPIFile(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> File:
    case = _get_case(db, case_id=case_id, tenant_id=current_user.tenant_id)
    _ensure_case_access(case, current_user)
    if current_user.role == "client" and case.client_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该案件尚未关联当事人。")
    return save_upload_file(
        tenant_id=current_user.tenant_id,
        case_id=case.id,
        uploader_id=current_user.id,
        upload=upload,
        db=db,
    )


@router.get("/case/{case_id}", response_model=list[FileRead])
def list_case_files(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[File]:
    case = _get_case(db, case_id=case_id, tenant_id=current_user.tenant_id)
    _ensure_case_access(case, current_user)
    return (
        db.query(File)
        .options(joinedload(File.uploader))
        .filter(File.case_id == case_id, File.tenant_id == current_user.tenant_id)
        .order_by(File.created_at.desc())
        .all()
    )


@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    file_record = (
        db.query(File)
        .options(joinedload(File.case))
        .filter(File.id == file_id, File.tenant_id == current_user.tenant_id)
        .first()
    )
    if file_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在。")

    if file_record.case is not None:
        _ensure_case_access(file_record.case, current_user)

    file_path = Path(file_record.file_url)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件内容不存在。")

    return FileResponse(path=file_path, filename=file_record.file_name, media_type=file_record.file_type)
