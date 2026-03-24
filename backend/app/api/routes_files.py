import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File as FastAPIFile, Request, Response, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.roles import normalize_role
from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_client_mini_program_source
from app.models.ai_task import AITask
from app.models.case import Case
from app.models.file import File
from app.models.user import User
from app.schemas.ai import AnalysisRequest
from app.schemas.file import FileAccessLinkRead, FileRead, FileUploadCompleteRequest, FileUploadPolicyRead
from app.services.ai import AIService
from app.services.case_flow import create_case_flow
from app.services.case_visibility import ensure_personal_tenant_lawyer_case_visible
from app.services.file import (
    build_storage_download_url,
    create_direct_upload_completion_token,
    create_file_access_token,
    create_stored_file_record,
    delete_storage_object,
    decode_direct_upload_completion_token,
    decode_file_access_token,
    move_storage_object,
    resolve_storage_path,
    save_upload_file,
    storage_object_exists,
    validate_upload_policy_request,
)
from app.services.storage import get_storage_backend


router = APIRouter(prefix="/files", tags=["Files"])
logger = logging.getLogger("app.api.files")
_AUTO_REANALYZE_DEBOUNCE_SECONDS = 300


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
    if normalize_role(current_user.role) == "client" and file_record.uploader_role == "lawyer":
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


def _get_case(db: Session, *, case_id: int, current_user: User) -> Case:
    case = db.query(Case).filter(Case.id == case_id, Case.tenant_id == current_user.tenant_id).first()
    if case is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.CASE_NOT_FOUND,
            message="案件不存在。",
            detail="案件不存在。",
        )
    ensure_personal_tenant_lawyer_case_visible(
        db,
        current_user=current_user,
        case_id=case.id,
    )
    return case


def _ensure_case_access(db: Session, case: Case, current_user: User) -> None:
    if normalize_role(current_user.role) == "client" and case.client_id != current_user.id:
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.FILE_ACCESS_DENIED,
            message="无权访问该案件文件。",
            detail="无权访问该案件文件。",
        )
    ensure_personal_tenant_lawyer_case_visible(
        db,
        current_user=current_user,
        case_id=case.id,
        status_code=status.HTTP_403_FORBIDDEN,
        code=ErrorCode.FILE_ACCESS_DENIED,
        message="无权访问该案件文件。",
        detail="无权访问该案件文件。",
    )


def _get_file_or_404(db: Session, *, file_id: int, tenant_id: int) -> File:
    file_record = (
        db.query(File)
        .options(joinedload(File.case))
        .filter(File.id == file_id, File.tenant_id == tenant_id)
        .first()
    )
    if file_record is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.FILE_NOT_FOUND,
            message="文件不存在。",
            detail="文件不存在。",
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
            message="文件内容不存在。",
            detail="文件内容不存在。",
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


def _ensure_delete_access(file_record: File, current_user: User) -> None:
    role = normalize_role(current_user.role)
    if role != "client":
        return

    if _client_can_download_file(file_record=file_record, current_user=current_user):
        return

    raise AppError(
        status_code=status.HTTP_403_FORBIDDEN,
        code=ErrorCode.FILE_ACCESS_DENIED,
        message="Current role cannot delete this file.",
        detail="Current role cannot delete this file.",
    )


def _auto_reanalyze_idempotency_key(*, case_id: int, now: datetime) -> str:
    bucket = int(now.timestamp()) // _AUTO_REANALYZE_DEBOUNCE_SECONDS
    return f"auto-reanalyze:{case_id}:{bucket}"


def _find_existing_auto_reanalyze_task(
    db: Session,
    *,
    tenant_id: int,
    case_id: int,
    operator_id: int,
    idempotency_key: str,
) -> AITask | None:
    return (
        db.query(AITask)
        .filter(
            AITask.tenant_id == tenant_id,
            AITask.case_id == case_id,
            AITask.task_type == "analyze",
            AITask.created_by == operator_id,
            AITask.idempotency_key == idempotency_key,
        )
        .order_by(AITask.created_at.desc(), AITask.id.desc())
        .first()
    )


def _schedule_auto_reanalysis(
    *,
    request: Request,
    db: Session,
    case: Case,
    upload_user: User,
) -> None:
    case.analysis_status = "pending_reanalysis"
    case.analysis_progress = 0
    db.add(case)

    if case.assigned_lawyer_id is None:
        create_case_flow(
            db=db,
            tenant_id=case.tenant_id,
            case_id=case.id,
            action_type="analysis_auto_reanalyze_skipped",
            content="Supplemental upload detected, but no assigned lawyer was found.",
            operator=upload_user,
            visible_to="both",
        )
        return

    operator = (
        db.query(User)
        .filter(
            User.id == case.assigned_lawyer_id,
            User.tenant_id == case.tenant_id,
            User.status == 1,
        )
        .first()
    )
    if operator is None:
        create_case_flow(
            db=db,
            tenant_id=case.tenant_id,
            case_id=case.id,
            action_type="analysis_auto_reanalyze_skipped",
            content="Supplemental upload detected, but assigned lawyer is unavailable.",
            operator=upload_user,
            visible_to="both",
        )
        return

    now = datetime.now(timezone.utc)
    idempotency_key = _auto_reanalyze_idempotency_key(case_id=case.id, now=now)
    existing_task = _find_existing_auto_reanalyze_task(
        db,
        tenant_id=case.tenant_id,
        case_id=case.id,
        operator_id=operator.id,
        idempotency_key=idempotency_key,
    )

    ai_service = AIService(
        db=db,
        request_id=getattr(request.state, "request_id", None),
        session_factory=getattr(request.app.state, "session_factory", None),
    )
    result = ai_service.start_analysis(
        case_id=case.id,
        payload=AnalysisRequest(),
        current_user=operator,
        idempotency_key=idempotency_key,
    )

    if existing_task is not None and existing_task.task_id == result.task_id:
        create_case_flow(
            db=db,
            tenant_id=case.tenant_id,
            case_id=case.id,
            action_type="analysis_auto_reanalyze_debounced",
            content=(
                f"Supplemental upload detected; reused analyze task {result.task_id} "
                "within 5-minute debounce window."
            ),
            operator=upload_user,
            visible_to="both",
        )
        return

    create_case_flow(
        db=db,
        tenant_id=case.tenant_id,
        case_id=case.id,
        action_type="analysis_auto_reanalyze_queued",
        content=f"Supplemental upload detected; queued analyze task {result.task_id}.",
        operator=upload_user,
        visible_to="both",
    )


def _ensure_case_upload_allowed(case: Case, current_user: User) -> None:
    if normalize_role(current_user.role) != "client":
        return
    if case.client_id is not None:
        return

    raise AppError(
        status_code=status.HTTP_400_BAD_REQUEST,
        code=ErrorCode.FILE_UPLOAD_INVALID,
        message="Current case is not bound to a client user.",
        detail="Current case is not bound to a client user.",
    )


def _build_upload_completion_url(*, case_id: int) -> str:
    return f"{settings.API_V1_STR}/cases/{case_id}/files/complete-upload"


def _to_upload_policy_read(*, policy, backend_name: str) -> FileUploadPolicyRead:
    return FileUploadPolicyRead(
        mode=policy.mode,
        upload_url=policy.upload_url,
        method=policy.method,
        headers=policy.headers,
        form_fields=policy.form_fields,
        file_field_name=policy.file_field_name,
        storage_key=policy.storage_key,
        completion_url=policy.completion_url,
        completion_token=policy.completion_token,
        expires_in_seconds=policy.expires_in_seconds,
        backend=backend_name,
    )


def _finalize_uploaded_file_record(
    *,
    request: Request,
    db: Session,
    case: Case,
    current_user: User,
    uploader_role: str,
    file_record: File,
    created: bool,
) -> FileRead:
    if created:
        create_case_flow(
            db=db,
            tenant_id=current_user.tenant_id,
            case_id=case.id,
            action_type="file_uploaded",
            content=f"Uploaded file {file_record.file_name}.",
            operator=current_user,
            visible_to="both",
        )

        if uploader_role == "client":
            try:
                _schedule_auto_reanalysis(
                    request=request,
                    db=db,
                    case=case,
                    upload_user=current_user,
                )
            except AppError as exc:
                logger.warning(
                    "files.auto_reanalyze_failed case_id=%s user_id=%s code=%s",
                    case.id,
                    current_user.id,
                    exc.code,
                )
                create_case_flow(
                    db=db,
                    tenant_id=current_user.tenant_id,
                    case_id=case.id,
                    action_type="analysis_auto_reanalyze_failed",
                    content=f"Supplemental upload detected; auto reanalysis failed ({exc.code}).",
                    operator=current_user,
                    visible_to="both",
                )
            except Exception:  # noqa: BLE001
                logger.exception(
                    "files.auto_reanalyze_failed_unexpected case_id=%s user_id=%s",
                    case.id,
                    current_user.id,
                )
                create_case_flow(
                    db=db,
                    tenant_id=current_user.tenant_id,
                    case_id=case.id,
                    action_type="analysis_auto_reanalyze_failed",
                    content="Supplemental upload detected; auto reanalysis failed unexpectedly.",
                    operator=current_user,
                    visible_to="both",
                )

        db.commit()
        db.refresh(file_record)

    return _to_file_read(file_record, current_user=current_user)


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
    case = _get_case(db, case_id=case_id, current_user=current_user)
    _ensure_case_access(db, case, current_user)
    if current_user.role == "client" and case.client_id is None:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.FILE_UPLOAD_INVALID,
            message="该案件尚未关联当事人。",
            detail="该案件尚未关联当事人。",
        )
    uploader_role = "client" if normalize_role(current_user.role) == "client" else "lawyer"
    file_record = save_upload_file(
        tenant_id=current_user.tenant_id,
        case_id=case.id,
        uploader_id=current_user.id,
        uploader_role=uploader_role,
        description=description,
        upload=upload,
        db=db,
    )
    create_case_flow(
        db=db,
        tenant_id=current_user.tenant_id,
        case_id=case.id,
        action_type="file_uploaded",
        content=f"Uploaded file {file_record.file_name}.",
        operator=current_user,
        visible_to="both",
    )
    if uploader_role == "client":
        try:
            _schedule_auto_reanalysis(
                request=request,
                db=db,
                case=case,
                upload_user=current_user,
            )
        except AppError as exc:
            logger.warning(
                "files.auto_reanalyze_failed case_id=%s user_id=%s code=%s",
                case.id,
                current_user.id,
                exc.code,
            )
            create_case_flow(
                db=db,
                tenant_id=current_user.tenant_id,
                case_id=case.id,
                action_type="analysis_auto_reanalyze_failed",
                content=f"Supplemental upload detected; auto reanalysis failed ({exc.code}).",
                operator=current_user,
                visible_to="both",
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "files.auto_reanalyze_failed_unexpected case_id=%s user_id=%s",
                case.id,
                current_user.id,
            )
            create_case_flow(
                db=db,
                tenant_id=current_user.tenant_id,
                case_id=case.id,
                action_type="analysis_auto_reanalyze_failed",
                content="Supplemental upload detected; auto reanalysis failed unexpectedly.",
                operator=current_user,
                visible_to="both",
            )
    db.commit()
    db.refresh(file_record)
    return _to_file_read(file_record, current_user=current_user)


@router.get("/upload-policy", response_model=FileUploadPolicyRead)
def get_file_upload_policy(
    case_id: int,
    file_name: str,
    content_type: str | None = None,
    _: None = Depends(require_client_mini_program_source),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileUploadPolicyRead:
    case = _get_case(db, case_id=case_id, current_user=current_user)
    _ensure_case_access(db, case, current_user)
    if current_user.role == "client" and case.client_id is None:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.FILE_UPLOAD_INVALID,
            message="该案件尚未关联当事人。",
            detail="该案件尚未关联当事人。",
        )

    normalized_file_name, detected_mime = validate_upload_policy_request(
        file_name=file_name,
        content_type=content_type,
    )

    backend = get_storage_backend()
    policy = backend.build_upload_policy(
        tenant_id=current_user.tenant_id,
        case_id=case.id,
        file_name=normalized_file_name,
        content_type=detected_mime,
    )
    if policy.mode == "direct_post":
        uploader_role = "client" if normalize_role(current_user.role) == "client" else "lawyer"
        final_storage_key = backend.build_storage_key(
            tenant_id=current_user.tenant_id,
            case_id=case.id,
            file_name=normalized_file_name,
        )
        policy.completion_url = _build_upload_completion_url(case_id=case.id)
        policy.completion_token = create_direct_upload_completion_token(
            tenant_id=current_user.tenant_id,
            case_id=case.id,
            uploader_id=current_user.id,
            uploader_role=uploader_role,
            storage_key=final_storage_key,
            file_name=normalized_file_name,
            content_type=detected_mime,
            upload_storage_key=policy.storage_key,
        )
        policy.expires_in_seconds = settings.FILE_ACCESS_TOKEN_EXPIRE_MINUTES * 60

    return _to_upload_policy_read(policy=policy, backend_name=backend.backend_name)


def complete_file_upload_impl(
    *,
    request: Request,
    payload: FileUploadCompleteRequest,
    current_user: User,
    db: Session,
    expected_case_id: int | None = None,
) -> FileRead:
    token_payload = decode_direct_upload_completion_token(payload.completion_token)
    token_case_id = int(token_payload["case_id"])

    if expected_case_id is not None and token_case_id != expected_case_id:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.FILE_UPLOAD_INVALID,
            message="Completion token case does not match request case.",
            detail="Completion token case does not match request case.",
        )
    if int(token_payload["tenant_id"]) != current_user.tenant_id:
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.FILE_ACCESS_DENIED,
            message="Completion token tenant does not match current user.",
            detail="Completion token tenant does not match current user.",
        )

    case = _get_case(db, case_id=token_case_id, current_user=current_user)
    _ensure_case_access(db, case, current_user)
    _ensure_case_upload_allowed(case, current_user)

    uploader_role = "client" if normalize_role(current_user.role) == "client" else "lawyer"
    if int(token_payload["uploader_id"]) != current_user.id or str(token_payload["uploader_role"]) != uploader_role:
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.FILE_ACCESS_DENIED,
            message="Completion token uploader does not match current user.",
            detail="Completion token uploader does not match current user.",
        )

    storage_key = str(token_payload["storage_key"])
    upload_storage_key = str(token_payload.get("upload_storage_key") or storage_key)
    existing_file = (
        db.query(File)
        .filter(File.tenant_id == current_user.tenant_id, File.file_url == storage_key)
        .first()
    )
    if existing_file is not None:
        return _to_file_read(existing_file, current_user=current_user)

    backend = get_storage_backend()
    if upload_storage_key != storage_key:
        if not backend.object_exists(storage_key=storage_key):
            if not backend.object_exists(storage_key=upload_storage_key):
                raise AppError(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    code=ErrorCode.FILE_UPLOAD_INVALID,
                    message="Uploaded object was not found in storage.",
                    detail="Uploaded object was not found in storage.",
                )
            move_storage_object(source_key=upload_storage_key, target_key=storage_key)
    elif not backend.object_exists(storage_key=storage_key):
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.FILE_UPLOAD_INVALID,
            message="Uploaded object was not found in storage.",
            detail="Uploaded object was not found in storage.",
        )

    file_record = create_stored_file_record(
        tenant_id=current_user.tenant_id,
        case_id=case.id,
        uploader_id=current_user.id,
        uploader_role=uploader_role,
        storage_key=storage_key,
        file_name=str(token_payload["file_name"]),
        content_type=str(token_payload["content_type"]),
        description=payload.description,
        db=db,
    )
    return _finalize_uploaded_file_record(
        request=request,
        db=db,
        case=case,
        current_user=current_user,
        uploader_role=uploader_role,
        file_record=file_record,
        created=True,
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
    case = _get_case(db, case_id=case_id, current_user=current_user)
    _ensure_case_access(db, case, current_user)
    files = (
        db.query(File)
        .options(joinedload(File.uploader))
        .filter(File.case_id == case_id, File.tenant_id == current_user.tenant_id)
        .order_by(File.created_at.desc())
        .all()
    )
    return [_to_file_read(item, current_user=current_user) for item in files]


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

    token = create_file_access_token(file_id=file_record.id, tenant_id=file_record.tenant_id)
    return FileAccessLinkRead(
        file_id=file_record.id,
        file_name=file_record.file_name,
        access_url=f"/api/v1/files/access/{token}",
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
    db: Session = Depends(get_db),
) -> Response:
    payload = decode_file_access_token(token)
    file_record = _get_file_or_404(
        db,
        file_id=int(payload["file_id"]),
        tenant_id=int(payload["tenant_id"]),
    )
    return _build_file_response(file_record)


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    file_record = _get_file_or_404(db, file_id=file_id, tenant_id=current_user.tenant_id)
    if file_record.case is not None:
        _ensure_case_access(db, file_record.case, current_user)
    _ensure_delete_access(file_record, current_user)

    file_name = file_record.file_name
    case_id = file_record.case_id
    db.delete(file_record)
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
    db.commit()

    try:
        delete_storage_object(file_record)
    except Exception:  # noqa: BLE001
        # Keep API success when physical cleanup fails; DB state is source of truth.
        pass

    return Response(status_code=status.HTTP_204_NO_CONTENT)
