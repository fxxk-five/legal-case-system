import logging
import re
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, File as FastAPIFile, Query, Request, Response, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Session, joinedload

from app.api.pagination import resolve_pagination_params
from app.core.errors import AppError, ErrorCode
from app.core.config import settings
from app.core.legal_types import normalize_legal_type
from app.core.roles import can_manage_case_role, normalize_role
from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_client_mini_program_source, require_mini_program_source
from app.models.ai_analysis import AIAnalysisResult
from app.models.case import Case
from app.models.file import File
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import UserRegister
from app.schemas.case import (
    CaseCreate,
    CaseInviteRead,
    CaseReportAccessLinkRead,
    CaseListItem,
    CaseRead,
    CaseReportVersionRead,
    CaseTimelineItem,
    CaseUpdate,
)
from app.schemas.file import FileRead, FileUploadCompleteRequest, FileUploadPolicyRead
from app.api.routes_files import (
    complete_file_upload_impl as _legacy_complete_file_upload_impl,
    get_file_upload_policy as _legacy_get_file_upload_policy,
    list_case_files as _legacy_list_case_files,
    upload_case_file as _legacy_upload_case_file,
)
from app.services.auth import create_user, generate_system_password
from app.services.case_number import generate_case_number, normalize_case_number
from app.services.case_visibility import build_visible_case_query, ensure_personal_tenant_lawyer_case_visible
from app.services.case_flow import create_case_flow, list_case_flows_for_viewer
from app.services.mini_program import create_case_invite_token
from app.services.report import ReportService
from app.services.storage import StorageObjectInfo, get_storage_backend


router = APIRouter(prefix="/cases", tags=["Cases"])
logger = logging.getLogger("app.api.cases")
REPORT_FILE_PATTERN = re.compile(r"^report-(client|lawyer)-(\d{14})\.pdf$")
REPORT_CONTENT_TYPE = "application/pdf"


@dataclass
class CaseReportObject:
    file_name: str
    storage_key: str
    report_scope: str
    generated_at: datetime


def _build_case_timeline(db: Session, case: Case, *, viewer_role: str) -> list[CaseTimelineItem]:
    flows = list_case_flows_for_viewer(
        db=db,
        tenant_id=case.tenant_id,
        case_id=case.id,
        viewer_role=viewer_role,
    )
    return [
        CaseTimelineItem(
            event_type=item.action_type,
            title=item.action_type.replace("_", " ").title(),
            description=item.content,
            occurred_at=item.created_at,
            operator_name=item.operator_name,
        )
        for item in flows
    ]


def _get_case_or_404(db: Session, *, case_id: int, current_user: User) -> Case:
    case = (
        db.query(Case)
        .options(joinedload(Case.client), joinedload(Case.assigned_lawyer))
        .filter(Case.id == case_id, Case.tenant_id == current_user.tenant_id)
        .first()
    )
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


def _case_number_exists(db: Session, *, tenant_id: int, case_number: str) -> bool:
    return (
        db.query(Case.id)
        .filter(Case.tenant_id == tenant_id, Case.case_number == case_number)
        .first()
        is not None
    )


def _resolve_report_scope(viewer_role: str) -> str:
    return "client" if normalize_role(viewer_role) == "client" else "lawyer"


def _get_case_report_prefix(case: Case) -> str:
    return (Path(f"tenant_{case.tenant_id}") / f"case_{case.id}" / "reports").as_posix().rstrip("/") + "/"


def _parse_report_file_metadata(file_name: str, *, modified_at: datetime | None = None) -> tuple[str, datetime]:
    match = REPORT_FILE_PATTERN.match(file_name)
    if match is None:
        return "unknown", modified_at or datetime.now(timezone.utc)
    report_scope = match.group(1)
    timestamp = datetime.strptime(match.group(2), "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    return report_scope, timestamp


def _to_case_report_object(item: StorageObjectInfo) -> CaseReportObject:
    report_scope, generated_at = _parse_report_file_metadata(
        item.file_name,
        modified_at=item.modified_at,
    )
    return CaseReportObject(
        file_name=item.file_name,
        storage_key=item.storage_key,
        report_scope=report_scope,
        generated_at=generated_at,
    )


def _list_case_reports(case: Case) -> list[CaseReportObject]:
    backend = get_storage_backend()
    reports = [
        _to_case_report_object(item)
        for item in backend.list_objects(prefix=_get_case_report_prefix(case), suffix=".pdf")
    ]
    reports.sort(key=lambda item: (item.generated_at, item.file_name), reverse=True)
    return reports


def _resolve_latest_case_report(case: Case, *, report_scope: str) -> CaseReportObject | None:
    report_files = _list_case_reports(case)
    if not report_files:
        return None

    scoped_files = [item for item in report_files if item.report_scope == report_scope]
    if scoped_files:
        return scoped_files[0]

    if report_scope == "lawyer":
        return report_files[0]
    return None


def _build_case_report_versions(case: Case, *, viewer_role: str) -> list[CaseReportVersionRead]:
    report_files = _list_case_reports(case)
    if not report_files:
        return []

    viewer_scope = _resolve_report_scope(viewer_role)
    if viewer_scope == "client":
        latest_client_report = _resolve_latest_case_report(case, report_scope="client")
        if latest_client_report is None:
            return []
        return [
            CaseReportVersionRead(
                file_name=latest_client_report.file_name,
                report_scope=latest_client_report.report_scope,
                generated_at=latest_client_report.generated_at,
                is_latest=True,
            )
        ]

    latest_by_scope: dict[str, CaseReportObject] = {}
    versions: list[CaseReportVersionRead] = []
    for file_path in report_files:
        scope = file_path.report_scope
        generated_at = file_path.generated_at
        if scope not in latest_by_scope:
            latest_by_scope[scope] = file_path
        versions.append(
            CaseReportVersionRead(
                file_name=file_path.file_name,
                report_scope=scope,
                generated_at=generated_at,
                is_latest=False,
            )
        )

    for row in versions:
        latest_path = latest_by_scope.get(row.report_scope)
        row.is_latest = latest_path is not None and latest_path.file_name == row.file_name
    return versions


def _resolve_case_report_by_name(case: Case, *, report_name: str) -> CaseReportObject | None:
    if not report_name.endswith(".pdf"):
        return None
    safe_name = Path(report_name).name
    if safe_name != report_name:
        return None
    for item in _list_case_reports(case):
        if item.file_name == safe_name:
            return item
    return None


'''
def _build_case_report_response(report: CaseReportObject) -> Response:
    backend = get_storage_backend()
    download_url = backend.build_private_download_url(
        storage_key=report.storage_key,
        file_name=report.file_name,
        content_type=REPORT_CONTENT_TYPE,
        expires_seconds=settings.FILE_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    if download_url:
        return RedirectResponse(url=download_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    if not backend.object_exists(storage_key=report.storage_key):
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.FILE_NOT_FOUND,
            message="鎶ュ憡鏂囦欢涓嶅瓨鍦ㄣ€?,
            detail="鎶ュ憡鏂囦欢涓嶅瓨鍦ㄣ€?,
        )

    return FileResponse(
        path=backend.resolve_local_path(storage_key=report.storage_key),
        filename=report.file_name,
        media_type=REPORT_CONTENT_TYPE,
    )
'''


def _render_case_report_response(report: CaseReportObject) -> Response:
    backend = get_storage_backend()
    download_url = backend.build_private_download_url(
        storage_key=report.storage_key,
        file_name=report.file_name,
        content_type=REPORT_CONTENT_TYPE,
        expires_seconds=settings.FILE_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    if download_url:
        return RedirectResponse(url=download_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    if not backend.object_exists(storage_key=report.storage_key):
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.FILE_NOT_FOUND,
            message="Report file does not exist.",
            detail="Report file does not exist.",
        )

    return FileResponse(
        path=backend.resolve_local_path(storage_key=report.storage_key),
        filename=report.file_name,
        media_type=REPORT_CONTENT_TYPE,
    )


def _build_case_report_access_url(report: CaseReportObject, *, case_id: int, latest: bool) -> str:
    backend = get_storage_backend()
    download_url = backend.build_private_download_url(
        storage_key=report.storage_key,
        file_name=report.file_name,
        content_type=REPORT_CONTENT_TYPE,
        expires_seconds=settings.FILE_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    if download_url:
        return download_url
    if latest:
        return f"{settings.API_V1_STR}/cases/{case_id}/report"
    return f"{settings.API_V1_STR}/cases/{case_id}/reports/{quote(report.file_name)}"


def _build_case_report_payload(
    *,
    db: Session,
    case: Case,
    viewer: User,
) -> dict:
    timeline = _build_case_timeline(db, case, viewer_role=viewer.role)
    files = _legacy_list_case_files(case_id=case.id, current_user=viewer, db=db)

    analyses = (
        db.query(AIAnalysisResult)
        .filter(
            AIAnalysisResult.case_id == case.id,
            AIAnalysisResult.tenant_id == case.tenant_id,
        )
        .order_by(AIAnalysisResult.created_at.desc(), AIAnalysisResult.id.desc())
        .limit(20)
        .all()
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "role": normalize_role(viewer.role),
        "case": {
            "id": case.id,
            "case_number": case.case_number,
            "title": case.title,
            "legal_type": case.legal_type,
            "status": case.status,
            "analysis_status": case.analysis_status,
            "analysis_progress": case.analysis_progress,
            "deadline": case.deadline.isoformat() if case.deadline else None,
            "client_name": case.client.real_name if case.client else None,
            "lawyer_name": case.assigned_lawyer.real_name if case.assigned_lawyer else None,
        },
        "timeline": [
            {
                "event_type": item.event_type,
                "title": item.title,
                "description": item.description,
                "occurred_at": item.occurred_at.isoformat(),
            }
            for item in timeline
        ],
        "files": [
            {
                "id": item.id,
                "file_name": item.file_name,
                "file_type": item.file_type,
                "description": item.description,
                "parse_status": item.parse_status,
                "uploader_role": item.uploader_role,
            }
            for item in files
        ],
        "analyses": [
            {
                "analysis_type": row.analysis_type,
                "summary": str((row.result_data or {}).get("summary") or ""),
                "applicable_laws": list(row.applicable_laws or []),
                "related_cases": list(row.related_cases or []),
                "strengths": list(row.strengths or []),
                "weaknesses": list(row.weaknesses or []),
                "recommendations": list(row.recommendations or []),
                "created_at": row.created_at.isoformat(),
            }
            for row in analyses
        ],
    }


def _persist_generated_report(*, case: Case, report_scope: str, pdf_bytes: bytes) -> CaseReportObject:
    backend = get_storage_backend()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    file_name = f"report-{report_scope}-{ts}.pdf"
    storage_key = _get_case_report_prefix(case) + file_name
    backend.save_bytes(
        data=pdf_bytes,
        storage_key=storage_key,
        content_type=REPORT_CONTENT_TYPE,
    )
    return CaseReportObject(
        file_name=file_name,
        storage_key=storage_key,
        report_scope=report_scope,
        generated_at=datetime.strptime(ts, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc),
    )


@router.post("", response_model=CaseRead, status_code=status.HTTP_201_CREATED)
def create_case(
    case_in: CaseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Case:
    if not can_manage_case_role(current_user.role):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.CASE_OPERATION_NOT_ALLOWED,
            message="当前角色不能创建案件。",
            detail="当前角色不能创建案件。",
        )

    client = (
        db.query(User)
        .filter(User.tenant_id == current_user.tenant_id, User.phone == case_in.client_phone)
        .first()
    )
    if client is None:
        client = create_user(
            db,
            user_in=UserRegister(
                phone=case_in.client_phone,
                password=generate_system_password(),
                real_name=case_in.client_real_name,
            ),
            tenant_id=current_user.tenant_id,
            role="client",
        )

    case_number = normalize_case_number(case_in.case_number)
    if case_number is None:
        tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
        if tenant is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code=ErrorCode.TENANT_NOT_FOUND,
                message="Tenant not found.",
                detail="Tenant not found.",
            )

        for _ in range(10):
            candidate = generate_case_number(
                db=db,
                tenant_id=current_user.tenant_id,
                tenant_code=tenant.tenant_code,
                legal_type=case_in.legal_type,
            )
            if not _case_number_exists(db, tenant_id=current_user.tenant_id, case_number=candidate):
                case_number = candidate
                break
        if case_number is None:
            raise AppError(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                code=ErrorCode.INTERNAL_ERROR,
                message="Failed to generate case number. Please retry.",
                detail="Failed to generate case number. Please retry.",
            )
    elif _case_number_exists(db, tenant_id=current_user.tenant_id, case_number=case_number):
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.CONFLICT,
            message="Case number already exists.",
            detail="Case number already exists.",
        )

    case = Case(
        tenant_id=current_user.tenant_id,
        case_number=case_number,
        title=case_in.title,
        legal_type=normalize_legal_type(case_in.legal_type),
        client_id=client.id,
        assigned_lawyer_id=current_user.id,
        status="new",
        deadline=case_in.deadline,
    )
    db.add(case)
    db.flush()
    create_case_flow(
        db=db,
        tenant_id=current_user.tenant_id,
        case_id=case.id,
        action_type="case_created",
        content=f"Created case {case.case_number}.",
        operator=current_user,
        visible_to="both",
    )
    db.commit()
    db.refresh(case)

    return _get_case_or_404(db, case_id=case.id, current_user=current_user)


@router.get("", response_model=list[CaseListItem])
def list_cases(
    request: Request,
    response: Response,
    status_filter: str | None = Query(default=None, alias="status"),
    legal_type: str | None = Query(default=None, min_length=1, max_length=50),
    q: str | None = Query(default=None, min_length=1, max_length=100),
    sort_by: str = Query(default="created_at", pattern="^(created_at|updated_at|deadline|legal_type)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    skip: int | None = Query(default=None, ge=0),
    limit: int | None = Query(default=None, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Case]:
    pagination = resolve_pagination_params(page=page, page_size=page_size, skip=skip, limit=limit)

    if pagination.source in {"legacy", "mixed"}:
        logger.info(
            "cases.pagination.legacy request_id=%s user_id=%s source=%s page=%s page_size=%s skip=%s limit=%s",
            getattr(request.state, "request_id", None),
            current_user.id,
            pagination.source,
            pagination.page,
            pagination.page_size,
            pagination.skip,
            pagination.limit,
        )

    query = build_visible_case_query(db, current_user).options(joinedload(Case.client))

    if status_filter:
        query = query.filter(Case.status == status_filter)
    if legal_type:
        query = query.filter(Case.legal_type == normalize_legal_type(legal_type))

    keyword = (q or "").strip()
    if keyword:
        like_kw = f"%{keyword}%"
        query = query.filter(
            or_(
                Case.case_number.ilike(like_kw),
                Case.title.ilike(like_kw),
            )
        )

    sort_column = {
        "created_at": Case.created_at,
        "updated_at": Case.updated_at,
        "deadline": Case.deadline,
        "legal_type": Case.legal_type,
    }[sort_by]
    order_by_clause = asc(sort_column) if sort_order == "asc" else desc(sort_column)

    # 稳定排序，避免相同时间字段导致分页抖动。
    query = query.order_by(order_by_clause, desc(Case.id))

    total_count = query.count()
    cases = query.offset(pagination.skip).limit(pagination.limit).all()
    response.headers["X-Page"] = str(pagination.page)
    response.headers["X-Page-Size"] = str(pagination.page_size)
    response.headers["X-Total-Count"] = str(total_count)
    response.headers["X-Total-Pages"] = str((total_count + pagination.page_size - 1) // pagination.page_size)
    return cases


@router.get("/{case_id}", response_model=CaseRead)
def get_case(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Case:
    case = _get_case_or_404(db, case_id=case_id, current_user=current_user)
    if normalize_role(current_user.role) == "client" and case.client_id != current_user.id:
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.CASE_ACCESS_DENIED,
            message="无权查看该案件。",
            detail="无权查看该案件。",
        )
    case.timeline = _build_case_timeline(db, case, viewer_role=current_user.role)
    return case


@router.get("/{case_id}/files", response_model=list[FileRead])
def list_case_files_canonical(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FileRead]:
    return _legacy_list_case_files(
        case_id=case_id,
        current_user=current_user,
        db=db,
    )


@router.post("/{case_id}/files", response_model=FileRead, status_code=status.HTTP_201_CREATED)
def upload_case_file_canonical(
    request: Request,
    case_id: int,
    description: str | None = None,
    upload: UploadFile = FastAPIFile(...),
    _: None = Depends(require_client_mini_program_source),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileRead:
    return _legacy_upload_case_file(
        request=request,
        case_id=case_id,
        description=description,
        upload=upload,
        _=None,
        current_user=current_user,
        db=db,
    )


@router.get("/{case_id}/files/upload-policy", response_model=FileUploadPolicyRead)
def get_case_file_upload_policy_canonical(
    case_id: int,
    file_name: str,
    content_type: str | None = None,
    _: None = Depends(require_client_mini_program_source),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileUploadPolicyRead:
    return _legacy_get_file_upload_policy(
        case_id=case_id,
        file_name=file_name,
        content_type=content_type,
        _=None,
        current_user=current_user,
        db=db,
    )


@router.post("/{case_id}/files/complete-upload", response_model=FileRead)
def complete_case_file_upload_canonical(
    case_id: int,
    request: Request,
    payload: FileUploadCompleteRequest,
    _: None = Depends(require_client_mini_program_source),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileRead:
    return _legacy_complete_file_upload_impl(
        request=request,
        payload=payload,
        current_user=current_user,
        db=db,
        expected_case_id=case_id,
    )


@router.get("/{case_id}/reports", response_model=list[CaseReportVersionRead])
def list_case_report_versions(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CaseReportVersionRead]:
    case = _get_case_or_404(db, case_id=case_id, current_user=current_user)
    if normalize_role(current_user.role) == "client" and case.client_id != current_user.id:
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.CASE_ACCESS_DENIED,
            message="无权查看该案件。",
            detail="无权查看该案件。",
        )
    return _build_case_report_versions(case, viewer_role=current_user.role)


'''
@router.get("/{case_id}/report/access-link", response_model=CaseReportAccessLinkRead)
def get_case_report_access_link(
    case_id: int,
    regenerate: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseReportAccessLinkRead:
    case = _get_case_or_404(db, case_id=case_id, current_user=current_user)
    viewer_role = normalize_role(current_user.role)
    if viewer_role == "client" and case.client_id != current_user.id:
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.CASE_ACCESS_DENIED,
            message="鏃犳潈鏌ョ湅璇ユ浠躲€?,
            detail="鏃犳潈鏌ョ湅璇ユ浠躲€?,
        )

    report_scope = _resolve_report_scope(current_user.role)
    latest_report = _resolve_latest_case_report(case, report_scope=report_scope)
    if latest_report is None or regenerate:
        payload = _build_case_report_payload(db=db, case=case, viewer=current_user)
        pdf_bytes = ReportService().generate_case_report_pdf(payload)
        latest_report = _persist_generated_report(case=case, report_scope=report_scope, pdf_bytes=pdf_bytes)

    return CaseReportAccessLinkRead(
        file_name=latest_report.file_name,
        access_url=_build_case_report_access_url(latest_report, case_id=case.id, latest=True),
        expires_in_seconds=settings.FILE_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/{case_id}/reports/{report_name}/access-link", response_model=CaseReportAccessLinkRead)
def get_case_report_version_access_link(
    case_id: int,
    report_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseReportAccessLinkRead:
    case = _get_case_or_404(db, case_id=case_id, current_user=current_user)
    viewer_role = normalize_role(current_user.role)
    if viewer_role == "client":
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.CASE_ACCESS_DENIED,
            message="褰撲簨浜轰粎鍙笅杞芥渶鏂版姤鍛娿€?,
            detail="褰撲簨浜轰粎鍙笅杞芥渶鏂版姤鍛娿€?,
        )

    report = _resolve_case_report_by_name(case, report_name=report_name)
    if report is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.FILE_NOT_FOUND,
            message="鎶ュ憡鏂囦欢涓嶅瓨鍦ㄣ€?,
            detail="鎶ュ憡鏂囦欢涓嶅瓨鍦ㄣ€?,
        )

    return CaseReportAccessLinkRead(
        file_name=report.file_name,
        access_url=_build_case_report_access_url(report, case_id=case.id, latest=False),
        expires_in_seconds=settings.FILE_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
'''


@router.get("/{case_id}/report/access-link", response_model=CaseReportAccessLinkRead)
def get_case_report_access_link(
    case_id: int,
    regenerate: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseReportAccessLinkRead:
    case = _get_case_or_404(db, case_id=case_id, current_user=current_user)
    viewer_role = normalize_role(current_user.role)
    if viewer_role == "client" and case.client_id != current_user.id:
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.CASE_ACCESS_DENIED,
            message="Current user cannot access this case report.",
            detail="Current user cannot access this case report.",
        )

    report_scope = _resolve_report_scope(current_user.role)
    latest_report = _resolve_latest_case_report(case, report_scope=report_scope)
    if latest_report is None or regenerate:
        payload = _build_case_report_payload(db=db, case=case, viewer=current_user)
        pdf_bytes = ReportService().generate_case_report_pdf(payload)
        latest_report = _persist_generated_report(case=case, report_scope=report_scope, pdf_bytes=pdf_bytes)

    return CaseReportAccessLinkRead(
        file_name=latest_report.file_name,
        access_url=_build_case_report_access_url(latest_report, case_id=case.id, latest=True),
        expires_in_seconds=settings.FILE_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/{case_id}/reports/{report_name}/access-link", response_model=CaseReportAccessLinkRead)
def get_case_report_version_access_link(
    case_id: int,
    report_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseReportAccessLinkRead:
    case = _get_case_or_404(db, case_id=case_id, current_user=current_user)
    viewer_role = normalize_role(current_user.role)
    if viewer_role == "client":
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.CASE_ACCESS_DENIED,
            message="Current user cannot access historical case reports.",
            detail="Current user cannot access historical case reports.",
        )

    report = _resolve_case_report_by_name(case, report_name=report_name)
    if report is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.FILE_NOT_FOUND,
            message="Report file does not exist.",
            detail="Report file does not exist.",
        )

    return CaseReportAccessLinkRead(
        file_name=report.file_name,
        access_url=_build_case_report_access_url(report, case_id=case.id, latest=False),
        expires_in_seconds=settings.FILE_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/{case_id}/reports/{report_name}", response_model=None)
def download_case_report_version(
    case_id: int,
    report_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    case = _get_case_or_404(db, case_id=case_id, current_user=current_user)
    viewer_role = normalize_role(current_user.role)
    if viewer_role == "client":
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.CASE_ACCESS_DENIED,
            message="当事人仅可下载最新报告。",
            detail="当事人仅可下载最新报告。",
        )
    report_path = _resolve_case_report_by_name(case, report_name=report_name)
    if report_path is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.FILE_NOT_FOUND,
            message="报告文件不存在。",
            detail="报告文件不存在。",
        )
    return _render_case_report_response(report_path)


@router.get("/{case_id}/report", response_model=None)
def download_case_report(
    case_id: int,
    regenerate: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    case = _get_case_or_404(db, case_id=case_id, current_user=current_user)
    viewer_role = normalize_role(current_user.role)
    if viewer_role == "client" and case.client_id != current_user.id:
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.CASE_ACCESS_DENIED,
            message="无权查看该案件。",
            detail="无权查看该案件。",
        )

    report_scope = _resolve_report_scope(current_user.role)
    latest_report = _resolve_latest_case_report(case, report_scope=report_scope)
    if latest_report is not None and not regenerate:
        return _render_case_report_response(latest_report)

    report_service = ReportService()
    try:
        payload = _build_case_report_payload(db=db, case=case, viewer=current_user)
        pdf_bytes = report_service.generate_case_report_pdf(payload)
        generated_path = _persist_generated_report(case=case, report_scope=report_scope, pdf_bytes=pdf_bytes)
    except AppError:
        if latest_report is not None:
            return _render_case_report_response(latest_report)
        raise

    return _render_case_report_response(generated_path)


@router.patch("/{case_id}", response_model=CaseRead)
def update_case(
    case_id: int,
    case_in: CaseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Case:
    case = _get_case_or_404(db, case_id=case_id, current_user=current_user)
    is_owner = case.assigned_lawyer_id == current_user.id
    is_admin = current_user.is_tenant_admin or normalize_role(current_user.role) == "tenant_admin"
    if not (is_owner or is_admin):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.CASE_OPERATION_NOT_ALLOWED,
            message="无权修改该案件。",
            detail="无权修改该案件。",
        )

    if case_in.title is not None:
        case.title = case_in.title
    if case_in.status is not None:
        case.status = case_in.status
    if case_in.legal_type is not None:
        case.legal_type = normalize_legal_type(case_in.legal_type)
    if case_in.deadline is not None:
        case.deadline = case_in.deadline
    if case_in.assigned_lawyer_id is not None:
        lawyer = (
            db.query(User)
            .filter(
                User.id == case_in.assigned_lawyer_id,
                User.tenant_id == current_user.tenant_id,
                User.role.in_(["lawyer", "tenant_admin"]),
            )
            .first()
        )
        if lawyer is None:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code=ErrorCode.USER_NOT_FOUND,
                message="指派律师不存在。",
                detail="指派律师不存在。",
            )
        case.assigned_lawyer_id = lawyer.id

    db.add(case)
    db.commit()
    db.refresh(case)
    case = _get_case_or_404(db, case_id=case.id, current_user=current_user)
    case.timeline = _build_case_timeline(db, case, viewer_role=current_user.role)
    return case


@router.get("/{case_id}/invite-qrcode", response_model=CaseInviteRead)
def get_case_invite_qrcode(
    case_id: int,
    _: None = Depends(require_mini_program_source),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseInviteRead:
    case = _get_case_or_404(db, case_id=case_id, current_user=current_user)
    if not can_manage_case_role(current_user.role):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.CASE_OPERATION_NOT_ALLOWED,
            message="当前角色不能邀请当事人。",
            detail="当前角色不能邀请当事人。",
        )

    token = create_case_invite_token(case_id=case.id, tenant_id=case.tenant_id)
    path = f"{settings.WECHAT_MINIAPP_CLIENT_ENTRY_PAGE}?scene=client-case&token={token}"
    return CaseInviteRead(case_id=case.id, tenant_id=case.tenant_id, token=token, path=path)
