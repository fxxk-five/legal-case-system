from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from fastapi import status
from sqlalchemy import select

from app.core.errors import AppError, ErrorCode
from app.core.roles import normalize_role
from app.models.user import User
from app.modules.ai.models.ai_task import AITask
from app.modules.ai.schemas import (
    AITaskListItem,
    AITaskListResponse,
    AITaskStatusRead,
    AnalysisResultListResponse,
    CaseFactListResponse,
    FalsificationResultResponse,
    FalsificationSummary,
)
from app.modules.ai.services.analysis_result_mapper import to_analysis_result_read
from app.modules.ai.services.falsification_service import to_falsification_read
from app.modules.ai.services.parse_service import to_case_fact_read
from app.modules.cases.models.case import Case
from app.modules.cases.policy import build_visible_case_query

if TYPE_CHECKING:
    from app.modules.ai.service import AIService


def list_case_facts(
    service: AIService,
    *,
    case_id: int,
    current_user: User,
    fact_type: str | None,
    min_confidence: float | None,
    page: int,
    page_size: int,
) -> CaseFactListResponse:
    service._get_case_or_raise(case_id=case_id, current_user=current_user)

    total, facts = service.repo.list_case_facts(
        case_id=case_id,
        tenant_id=current_user.tenant_id,
        fact_type=fact_type,
        min_confidence=min_confidence,
        page=page,
        page_size=page_size,
    )
    return CaseFactListResponse(
        total=total,
        items=[to_case_fact_read(item) for item in facts],
    )


def list_analysis_results(
    service: AIService,
    *,
    case_id: int,
    current_user: User,
) -> AnalysisResultListResponse:
    service._get_case_or_raise(case_id=case_id, current_user=current_user)

    records = service.repo.list_analysis_results(
        case_id=case_id,
        tenant_id=current_user.tenant_id,
    )

    viewer_role = normalize_role(current_user.role)
    items = []
    for item in records:
        result = to_analysis_result_read(item)
        if viewer_role == "client":
            result = result.model_copy(update={"token_usage": 0, "cost": Decimal("0")})
        items.append(result)

    return AnalysisResultListResponse(items=items)


def list_falsification_results(
    service: AIService,
    *,
    case_id: int,
    current_user: User,
) -> FalsificationResultResponse:
    service._get_case_or_raise(case_id=case_id, current_user=current_user)
    service._ensure_role_for_action(current_user=current_user, action="view_falsification")

    records = service.repo.list_falsification_records(
        case_id=case_id,
        tenant_id=current_user.tenant_id,
    )
    critical = sum(1 for item in records if item.severity == "critical")
    major = sum(1 for item in records if item.severity == "major")
    minor = sum(1 for item in records if item.severity == "minor")
    falsified_count = sum(1 for item in records if item.is_falsified)

    return FalsificationResultResponse(
        summary=FalsificationSummary(
            total_challenges=len(records),
            falsified_count=falsified_count,
            critical_issues=critical,
            major_issues=major,
            minor_issues=minor,
        ),
        items=[to_falsification_read(item) for item in records],
    )


def list_tasks(
    service: AIService,
    *,
    current_user: User,
    page: int,
    page_size: int,
    status_filter: str | None,
    task_type: str | None,
) -> AITaskListResponse:
    viewer_role = normalize_role(current_user.role)
    if viewer_role == "client":
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.AI_OPERATION_NOT_ALLOWED,
            message="当前角色无权查询AI任务列表。",
            detail="当前角色无权查询AI任务列表。",
        )

    if viewer_role == "lawyer":
        visible_case_ids = select(
            build_visible_case_query(service.db, current_user)
            .with_entities(Case.id)
            .subquery()
            .c.id
        )
        total, tasks = service.repo.list_tasks(
            tenant_id=current_user.tenant_id,
            page=page,
            page_size=page_size,
            status_filter=status_filter,
            task_type=task_type,
            visible_case_ids=visible_case_ids,
        )
    else:
        total, tasks = service.repo.list_tasks(
            tenant_id=current_user.tenant_id,
            page=page,
            page_size=page_size,
            status_filter=status_filter,
            task_type=task_type,
        )

    return AITaskListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[_to_task_list_item(item) for item in tasks],
    )


def get_task_status(
    service: AIService,
    *,
    task_id: str,
    current_user: User,
) -> AITaskStatusRead:
    task = service.repo.get_task_by_task_id(task_id=task_id, tenant_id=current_user.tenant_id)
    if task is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.AI_TASK_NOT_FOUND,
            message="AI任务不存在。",
            detail="AI任务不存在。",
        )

    service._get_case_or_raise(case_id=task.case_id, current_user=current_user)

    estimated_completion = None
    if task.status in {"queued", "pending", "processing", "retrying"} and task.started_at is not None:
        estimated_completion = task.started_at + timedelta(seconds=120)

    return AITaskStatusRead(
        id=task.task_id,
        task_id=task.task_id,
        task_type=task.task_type,
        status=task.status,
        progress=task.progress,
        retry_count=task.retry_count,
        next_retry_at=task.next_retry_at,
        worker_id=task.worker_id,
        heartbeat_at=task.heartbeat_at,
        message=task.message,
        started_at=task.started_at,
        estimated_completion=estimated_completion,
        error_message=task.error_message,
    )


def _to_task_list_item(task: AITask) -> AITaskListItem:
    return AITaskListItem(
        id=task.task_id,
        task_id=task.task_id,
        case_id=task.case_id,
        task_type=task.task_type,
        status=task.status,
        progress=task.progress,
        retry_count=task.retry_count,
        next_retry_at=task.next_retry_at,
        worker_id=task.worker_id,
        message=task.message,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )
