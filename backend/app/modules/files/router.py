from fastapi import APIRouter, Depends, File as FastAPIFile, Request, Response, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.roles import normalize_role
from app.db.session import get_db
from app.integrations.storage.service import get_storage_backend
from app.models.user import User
from app.modules.auth.deps import get_current_user, require_client_mini_program_source
from app.modules.cases.flow import create_case_flow
from app.modules.cases.models.case import Case
from app.modules.cases.policy import ensure_personal_tenant_lawyer_case_visible
from app.modules.files.case_file_service import CaseFileService
from app.modules.files.models.file import File
from app.modules.files.repository import FilesRepository
from app.modules.files.schemas import FileAccessLinkRead, FileRead, FileUploadCompleteRequest, FileUploadPolicyRead
from app.modules.files.service import (
    build_storage_download_url,
    consume_file_access_grant,
    delete_storage_object,
    resolve_storage_path,
    storage_object_exists,
)


router = APIRouter(prefix="/files", tags=["Files"])


def _client_can_download_file(*, file_record: File, current_user: User) -> bool:
    return file_record.uploader_role == "client" and file_record.uploader_id == current_user.id


def _can_download_file(*, file_record: File, current_user: User) -> bool:
    return normalize_role(current_user.role) != "client" or _client_can_download_file(
        file_record=file_record,
        current_user=current_user,
    )


def _to_file_read(file_record: File, *, current_user: User) -> FileRead:
    can_download = _can_download_file(file_record=file_record, current_user=current_user)
    description = file_record.description
    if normalize_role(current_user.role) == "client":
        description = None

    return FileRead(
        id=file_record.id,
        tenant_id=file_record.tenant_id,
        case_id=file_record.case_id,
        uploader_id=file_record.uploader_id,
        uploader_role=file_record.uploader_role,
        file_name=file_record.file_name,
        download_url=file_record.download_url if can_download else None,
        can_download=can_download,
        file_type=file_record.file_type,
        description=description,
        parse_status=file_record.parse_status,
        created_at=file_record.created_at,
        uploader=file_record.uploader,
    )


def _case_file_service(db: Session) -> CaseFileService:
    return CaseFileService(db)


def _ensure_case_access(db: Session, case: Case, current_user: User) -> None:
    if normalize_role(current_user.role) == "client" and case.client_id != current_user.id:
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.FILE_ACCESS_DENIED,
            message="Current user cannot access this case file.",
            detail="Current user cannot access this case file.",
        )
    ensure_personal_tenant_lawyer_case_visible(
        db,
        current_user=current_user,
        case_id=case.id,
        status_code=status.HTTP_403_FORBIDDEN,
        code=ErrorCode.FILE_ACCESS_DENIED,
        message="Current user cannot access this case file.",
        detail="Current user cannot access this case file.",
    )


def _get_file_or_404(db: Session, *, file_id: int, tenant_id: int) -> File:
    file_record = FilesRepository(db).get_file(
        file_id=file_id,
        tenant_id=tenant_id,
        with_case=True,
    )
    if file_record is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.FILE_NOT_FOUND,
            message="File does not exist.",
            detail="File does not exist.",
        )
    return file_record


def _build_file_response(file_record: File) -> Response:
    download_url = build_storage_download_url(
        file_record=file_record,
        expires_seconds=settings.FILE_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    if download_url:
        return RedirectResponse(url=download_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    file_path = resolve_storage_path(file_record)
    if not storage_object_exists(file_record):
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.FILE_NOT_FOUND,
            message="File content does not exist.",
            detail="File content does not exist.",
        )
    return FileResponse(path=file_path, filename=file_record.file_name, media_type=file_record.file_type)


def _ensure_download_access(file_record: File, current_user: User) -> None:
    if _can_download_file(file_record=file_record, current_user=current_user):
        return

    raise AppError(
        status_code=status.HTTP_403_FORBIDDEN,
        code=ErrorCode.FILE_ACCESS_DENIED,
        message="Current role cannot download this file.",
        detail="Current role cannot download this file.",
    )


@router.post("/upload", response_model=FileRead, status_code=status.HTTP_201_CREATED)
def upload_case_file(
    request: Request,
    case_id: int,
    description: str | None = None,
    upload: UploadFile = FastAPIFile(...),
    _: None = Depends(require_client_mini_program_source),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileRead:
    return _case_file_service(db).upload_case_file(
        request=request,
        case_id=case_id,
        description=description,
        upload=upload,
        current_user=current_user,
    )


@router.get("/upload-policy", response_model=FileUploadPolicyRead)
def get_file_upload_policy(
    case_id: int,
    file_name: str,
    content_type: str | None = None,
    _: None = Depends(require_client_mini_program_source),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileUploadPolicyRead:
    return _case_file_service(db).get_file_upload_policy(
        case_id=case_id,
        file_name=file_name,
        content_type=content_type,
        current_user=current_user,
    )


def complete_file_upload_impl(
    *,
    request: Request,
    payload: FileUploadCompleteRequest,
    current_user: User,
    db: Session,
    expected_case_id: int | None = None,
) -> FileRead:
    return _case_file_service(db).complete_file_upload(
        request=request,
        payload=payload,
        current_user=current_user,
        expected_case_id=expected_case_id,
    )


@router.post("/complete-upload", response_model=FileRead)
def complete_file_upload(
    request: Request,
    payload: FileUploadCompleteRequest,
    _: None = Depends(require_client_mini_program_source),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileRead:
    return complete_file_upload_impl(
        request=request,
        payload=payload,
        current_user=current_user,
        db=db,
    )


@router.get("/case/{case_id}", response_model=list[FileRead])
def list_case_files(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FileRead]:
    return _case_file_service(db).list_case_files(case_id=case_id, current_user=current_user)


@router.get("/{file_id}/access-link", response_model=FileAccessLinkRead)
def get_file_access_link(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileAccessLinkRead:
    file_record = _get_file_or_404(db, file_id=file_id, tenant_id=current_user.tenant_id)
    if file_record.case is not None:
        _ensure_case_access(db, file_record.case, current_user)
    _ensure_download_access(file_record, current_user)

    direct_url = build_storage_download_url(
        file_record=file_record,
        expires_seconds=settings.FILE_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    if direct_url:
        return FileAccessLinkRead(
            file_id=file_record.id,
            file_name=file_record.file_name,
            access_url=direct_url,
            expires_in_seconds=settings.FILE_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    return FileAccessLinkRead(
        file_id=file_record.id,
        file_name=file_record.file_name,
        access_url=f"{settings.API_V1_STR}/files/{file_record.id}/download",
        expires_in_seconds=settings.FILE_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/{file_id}/download", response_model=None)
def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    file_record = _get_file_or_404(db, file_id=file_id, tenant_id=current_user.tenant_id)
    if file_record.case is not None:
        _ensure_case_access(db, file_record.case, current_user)
    _ensure_download_access(file_record, current_user)
    return _build_file_response(file_record)


@router.get("/access/{token}", response_model=None)
def download_file_by_token(
    token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    payload = consume_file_access_grant(
        db,
        token,
        expected_user_id=current_user.id,
        expected_tenant_id=current_user.tenant_id,
    )
    file_record = _get_file_or_404(
        db,
        file_id=int(payload["file_id"]),
        tenant_id=int(payload["tenant_id"]),
    )
    if file_record.case is not None:
        _ensure_case_access(db, file_record.case, current_user)
    _ensure_download_access(file_record, current_user)
    return _build_file_response(file_record)


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    repo = FilesRepository(db)
    file_record = _get_file_or_404(db, file_id=file_id, tenant_id=current_user.tenant_id)
    if file_record.case is not None:
        _ensure_case_access(db, file_record.case, current_user)
    _case_file_service(db).ensure_delete_access(file_record=file_record, current_user=current_user)

    file_name = file_record.file_name
    case_id = file_record.case_id
    repo.delete(file_record)
    if case_id is not None:
        create_case_flow(
            db=db,
            tenant_id=current_user.tenant_id,
            case_id=case_id,
            action_type="file_deleted",
            content=f"Deleted file {file_name}.",
            operator=current_user,
            visible_to="both",
        )
    repo.commit()

    try:
        delete_storage_object(file_record)
    except Exception:  # noqa: BLE001
        pass

    return Response(status_code=status.HTTP_204_NO_CONTENT)
