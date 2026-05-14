from fastapi import APIRouter, Depends, File as FastAPIFile, Query, Request, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.modules.auth.deps import (
    get_current_user,
    require_client_mini_program_source,
    require_mini_program_session,
)
from app.modules.cases.schemas import (
    CaseClientRemarkUpdate,
    CaseCreate,
    CaseInviteRead,
    CaseLawyerRead,
    CaseLawyerRemarkUpdate,
    CaseListItem,
    CaseRead,
    CaseReportAccessLinkRead,
    CaseReportVersionRead,
    CaseUpdate,
)
from app.modules.cases.service import CaseService
from app.modules.files.case_file_service import CaseFileService
from app.modules.files.schemas import FileRead, FileUploadCompleteRequest, FileUploadPolicyRead


router = APIRouter(prefix="/cases", tags=["Cases"])


def _service(db: Session) -> CaseService:
    return CaseService(db)


def _file_service(db: Session) -> CaseFileService:
    return CaseFileService(db)


@router.post("", response_model=CaseLawyerRead, status_code=status.HTTP_201_CREATED)
def create_case(
    case_in: CaseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseRead | CaseLawyerRead:
    return _service(db).create_case(case_in=case_in, current_user=current_user)


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
) -> list[CaseListItem]:
    return _service(db).list_cases(
        request=request,
        response=response,
        status_filter=status_filter,
        legal_type=legal_type,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
        skip=skip,
        limit=limit,
        current_user=current_user,
    )


@router.get("/{case_id}", response_model=None)
def get_case(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseRead | CaseLawyerRead:
    return _service(db).get_case(case_id=case_id, current_user=current_user)


@router.patch("/{case_id}/client-remark", response_model=CaseRead)
def update_client_remark(
    case_id: int,
    payload: CaseClientRemarkUpdate,
    _: None = Depends(require_client_mini_program_source),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseRead:
    return _service(db).update_client_remark(
        case_id=case_id,
        payload=payload,
        current_user=current_user,
    )


@router.patch("/{case_id}/lawyer-remark", response_model=CaseLawyerRead)
def update_lawyer_remark(
    case_id: int,
    payload: CaseLawyerRemarkUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseLawyerRead:
    return _service(db).update_lawyer_remark(
        case_id=case_id,
        payload=payload,
        current_user=current_user,
    )


@router.get("/{case_id}/files", response_model=list[FileRead])
def list_case_files_canonical(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FileRead]:
    return _file_service(db).list_case_files(
        case_id=case_id,
        current_user=current_user,
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
    return _file_service(db).upload_case_file(
        request=request,
        case_id=case_id,
        description=description,
        upload=upload,
        current_user=current_user,
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
    return _file_service(db).get_file_upload_policy(
        case_id=case_id,
        file_name=file_name,
        content_type=content_type,
        current_user=current_user,
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
    return _file_service(db).complete_file_upload(
        request=request,
        payload=payload,
        current_user=current_user,
        expected_case_id=case_id,
    )


@router.get("/{case_id}/reports", response_model=list[CaseReportVersionRead])
def list_case_report_versions(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CaseReportVersionRead]:
    return _service(db).list_case_report_versions(case_id=case_id, current_user=current_user)


@router.get("/{case_id}/report/access-link", response_model=CaseReportAccessLinkRead)
def get_case_report_access_link(
    case_id: int,
    regenerate: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseReportAccessLinkRead:
    return _service(db).get_case_report_access_link(
        case_id=case_id,
        regenerate=regenerate,
        current_user=current_user,
    )


@router.get("/{case_id}/reports/{report_name}/access-link", response_model=CaseReportAccessLinkRead)
def get_case_report_version_access_link(
    case_id: int,
    report_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseReportAccessLinkRead:
    return _service(db).get_case_report_version_access_link(
        case_id=case_id,
        report_name=report_name,
        current_user=current_user,
    )


@router.get("/{case_id}/reports/{report_name}", response_model=None)
def download_case_report_version(
    case_id: int,
    report_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    return _service(db).download_case_report_version(
        case_id=case_id,
        report_name=report_name,
        current_user=current_user,
    )


@router.get("/{case_id}/report", response_model=None)
def download_case_report(
    case_id: int,
    regenerate: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    return _service(db).download_case_report(
        case_id=case_id,
        regenerate=regenerate,
        current_user=current_user,
    )


@router.patch("/{case_id}", response_model=CaseLawyerRead)
def update_case(
    case_id: int,
    case_in: CaseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseLawyerRead:
    return _service(db).update_case(
        case_id=case_id,
        case_in=case_in,
        current_user=current_user,
    )


@router.get("/{case_id}/invite-qrcode", response_model=CaseInviteRead)
def get_case_invite_qrcode(
    case_id: int,
    _: None = Depends(require_mini_program_session),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseInviteRead:
    return _service(db).get_case_invite_qrcode(case_id=case_id, current_user=current_user)
