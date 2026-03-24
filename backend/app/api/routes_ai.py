from fastapi import APIRouter, Depends, Header, Query, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.ai import (
    AITaskListResponse,
    AITaskRetryRequest,
    AITaskRetryResponse,
    AITaskStatusRead,
    AnalysisRequest,
    AnalysisResultListResponse,
    AnalysisStartResponse,
    CaseFactListResponse,
    DocumentParseRequest,
    DocumentParseResponse,
    FalsificationRequest,
    FalsificationResultResponse,
    FalsificationStartResponse,
)
from app.services.ai import AIService


router = APIRouter(prefix="/ai", tags=["AI"])


def _service(db: Session, request: Request) -> AIService:
    return AIService(
        db=db,
        request_id=getattr(request.state, "request_id", None),
        session_factory=getattr(request.app.state, "session_factory", None),
    )


@router.post(
    "/cases/{case_id}/parse-document",
    response_model=DocumentParseResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def parse_document(
    case_id: int,
    payload: DocumentParseRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentParseResponse:
    return _service(db, request).start_parse_document(
        case_id=case_id,
        payload=payload,
        current_user=current_user,
        idempotency_key=idempotency_key,
    )


@router.get("/cases/{case_id}/facts", response_model=CaseFactListResponse)
def list_case_facts(
    case_id: int,
    request: Request,
    fact_type: str | None = Query(default=None),
    min_confidence: float | None = Query(default=None, ge=0.0, le=1.0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseFactListResponse:
    return _service(db, request).list_case_facts(
        case_id=case_id,
        current_user=current_user,
        fact_type=fact_type,
        min_confidence=min_confidence,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/cases/{case_id}/analyze",
    response_model=AnalysisStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_analysis(
    case_id: int,
    payload: AnalysisRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalysisStartResponse:
    return _service(db, request).start_analysis(
        case_id=case_id,
        payload=payload,
        current_user=current_user,
        idempotency_key=idempotency_key,
    )


@router.get(
    "/cases/{case_id}/analysis-results",
    response_model=AnalysisResultListResponse,
)
def list_analysis_results(
    case_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalysisResultListResponse:
    return _service(db, request).list_analysis_results(
        case_id=case_id,
        current_user=current_user,
    )


@router.post(
    "/cases/{case_id}/falsification",
    response_model=FalsificationStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_falsification(
    case_id: int,
    payload: FalsificationRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FalsificationStartResponse:
    return _service(db, request).start_falsification(
        case_id=case_id,
        payload=payload,
        current_user=current_user,
        idempotency_key=idempotency_key,
    )


@router.get(
    "/cases/{case_id}/falsification-results",
    response_model=FalsificationResultResponse,
)
def list_falsification_results(
    case_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FalsificationResultResponse:
    return _service(db, request).list_falsification_results(
        case_id=case_id,
        current_user=current_user,
    )


@router.get("/tasks", response_model=AITaskListResponse)
def list_tasks(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    task_type: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AITaskListResponse:
    return _service(db, request).list_tasks(
        current_user=current_user,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        task_type=task_type,
    )


@router.get("/tasks/{task_id}", response_model=AITaskStatusRead)
def get_task_status(
    task_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AITaskStatusRead:
    return _service(db, request).get_task_status(task_id=task_id, current_user=current_user)


@router.post("/tasks/{task_id}/retry", response_model=AITaskRetryResponse, status_code=status.HTTP_202_ACCEPTED)
def retry_task(
    task_id: str,
    payload: AITaskRetryRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AITaskRetryResponse:
    return _service(db, request).retry_task(task_id=task_id, payload=payload, current_user=current_user)
