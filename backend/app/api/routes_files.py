from fastapi import APIRouter, Depends, File as FastAPIFile, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.case import Case
from app.models.file import File
from app.models.user import User
from app.schemas.file import FileAccessLinkRead, FileRead, FileUploadPolicyRead
from app.services.file import (
    create_file_access_token,
    decode_file_access_token,
    resolve_storage_path,
    save_upload_file,
)
from app.services.storage import get_storage_backend


router = APIRouter(prefix="/files", tags=["Files"])


def _get_case(db: Session, *, case_id: int, tenant_id: int) -> Case:
    case = db.query(Case).filter(Case.id == case_id, Case.tenant_id == tenant_id).first()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="案件不存在。")
    return case


def _ensure_case_access(case: Case, current_user: User) -> None:
    if current_user.role == "client" and case.client_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该案件文件。")


def _get_file_or_404(db: Session, *, file_id: int, tenant_id: int) -> File:
    file_record = (
        db.query(File)
        .options(joinedload(File.case))
        .filter(File.id == file_id, File.tenant_id == tenant_id)
        .first()
    )
    if file_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在。")
    return file_record


def _build_file_response(file_record: File) -> FileResponse:
    file_path = resolve_storage_path(file_record)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件内容不存在。")
    return FileResponse(path=file_path, filename=file_record.file_name, media_type=file_record.file_type)


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


@router.get("/upload-policy", response_model=FileUploadPolicyRead)
def get_file_upload_policy(
    case_id: int,
    file_name: str,
    content_type: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileUploadPolicyRead:
    case = _get_case(db, case_id=case_id, tenant_id=current_user.tenant_id)
    _ensure_case_access(case, current_user)
    if current_user.role == "client" and case.client_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该案件尚未关联当事人。")

    backend = get_storage_backend()
    policy = backend.build_upload_policy(
        tenant_id=current_user.tenant_id,
        case_id=case.id,
        file_name=file_name,
        content_type=content_type,
    )
    return FileUploadPolicyRead(
        mode=policy.mode,
        upload_url=policy.upload_url,
        method=policy.method,
        headers=policy.headers,
        form_fields=policy.form_fields,
        file_field_name=policy.file_field_name,
        storage_key=policy.storage_key,
        backend=backend.backend_name,
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


@router.get("/{file_id}/access-link", response_model=FileAccessLinkRead)
def get_file_access_link(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileAccessLinkRead:
    file_record = _get_file_or_404(db, file_id=file_id, tenant_id=current_user.tenant_id)
    if file_record.case is not None:
        _ensure_case_access(file_record.case, current_user)

    token = create_file_access_token(file_id=file_record.id, tenant_id=file_record.tenant_id)
    return FileAccessLinkRead(
        file_id=file_record.id,
        file_name=file_record.file_name,
        access_url=f"/api/v1/files/access/{token}",
        expires_in_seconds=settings.FILE_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    file_record = _get_file_or_404(db, file_id=file_id, tenant_id=current_user.tenant_id)
    if file_record.case is not None:
        _ensure_case_access(file_record.case, current_user)
    return _build_file_response(file_record)


@router.get("/access/{token}")
def download_file_by_token(
    token: str,
    db: Session = Depends(get_db),
) -> FileResponse:
    payload = decode_file_access_token(token)
    file_record = _get_file_or_404(
        db,
        file_id=int(payload["file_id"]),
        tenant_id=int(payload["tenant_id"]),
    )
    return _build_file_response(file_record)
