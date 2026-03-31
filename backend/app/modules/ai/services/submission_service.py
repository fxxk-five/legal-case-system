from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import status

from app.core.errors import AppError, ErrorCode
from app.models.user import User
from app.modules.ai.schemas import (
    AnalysisRequest,
    AnalysisStartResponse,
    DocumentParseRequest,
    DocumentParseResponse,
    FalsificationRequest,
    FalsificationStartResponse,
)

if TYPE_CHECKING:
    from app.modules.ai.service import AIService


def start_parse_document(
    service: AIService,
    *,
    case_id: int,
    payload: DocumentParseRequest,
    current_user: User,
    idempotency_key: str | None = None,
) -> DocumentParseResponse:
    case = service._get_case_or_raise(case_id=case_id, current_user=current_user)
    service._ensure_role_for_action(current_user=current_user, action="parse")
    service._ensure_personal_tenant_ai_access(current_user=current_user)

    file_record = service.repo.get_file(
        file_id=payload.file_id,
        case_id=case.id,
        tenant_id=current_user.tenant_id,
    )
    if file_record is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.FILE_NOT_FOUND,
            message="文件不存在或不属于当前案件。",
            detail="文件不存在或不属于当前案件。",
        )

    input_params = {
        "file_id": payload.file_id,
        "parse_options": payload.parse_options.model_dump(),
    }
    task, created_new = service._create_or_reuse_task(
        case=case,
        current_user=current_user,
        task_type="parse",
        input_params=input_params,
        idempotency_key=idempotency_key,
    )
    if not created_new:
        return DocumentParseResponse(
            task_id=task.task_id,
            status=task.status,
            message=task.message or "文档解析任务已存在。",
        )

    service._append_case_flow(
        case_id=case.id,
        tenant_id=case.tenant_id,
        action_type="analysis_started",
        content=f"Started parse task {task.task_id}.",
        operator_id=current_user.id,
        visible_to="both",
    )
    service.repo.commit()
    service._schedule_task_execution(task_id=task.task_id)

    return DocumentParseResponse(
        task_id=task.task_id,
        status=task.status,
        message=task.message or "文档解析任务已创建。",
    )


def start_analysis(
    service: AIService,
    *,
    case_id: int,
    payload: AnalysisRequest,
    current_user: User,
    idempotency_key: str | None = None,
) -> AnalysisStartResponse:
    case = service._get_case_or_raise(case_id=case_id, current_user=current_user)
    service._ensure_role_for_action(current_user=current_user, action="analyze")
    service._ensure_personal_tenant_ai_access(current_user=current_user)

    is_auto_trigger = bool(
        idempotency_key and idempotency_key.startswith("auto-reanalyze:")
    )
    model_override = service._resolve_budget_policy_for_analysis(
        case=case,
        current_user=current_user,
        is_auto_trigger=is_auto_trigger,
    )
    input_params = payload.model_dump()
    if model_override:
        input_params["model_override"] = model_override
    input_params["trigger_source"] = "auto" if is_auto_trigger else "manual"
    task, created_new = service._create_or_reuse_task(
        case=case,
        current_user=current_user,
        task_type="analyze",
        input_params=input_params,
        idempotency_key=idempotency_key,
    )
    if created_new:
        case.analysis_status = "queued"
        case.analysis_progress = 0
        service.repo.save(case)
        service._append_case_flow(
            case_id=case.id,
            tenant_id=case.tenant_id,
            action_type="analysis_started",
            content=f"Started analyze task {task.task_id}.",
            operator_id=current_user.id,
            visible_to="both",
        )
        service._append_case_flow(
            case_id=case.id,
            tenant_id=case.tenant_id,
            action_type="analysis_progress_updated",
            content=f"Analyze task {task.task_id}: queued (0%).",
            operator_id=current_user.id,
            visible_to="both",
        )
        service.repo.commit()
        service._schedule_task_execution(task_id=task.task_id)

    return AnalysisStartResponse(task_id=task.task_id, status=task.status)


def start_falsification(
    service: AIService,
    *,
    case_id: int,
    payload: FalsificationRequest,
    current_user: User,
    idempotency_key: str | None = None,
) -> FalsificationStartResponse:
    case = service._get_case_or_raise(case_id=case_id, current_user=current_user)
    service._ensure_role_for_action(current_user=current_user, action="falsify")
    service._ensure_personal_tenant_ai_access(current_user=current_user)

    analysis = service.repo.get_analysis_result(
        analysis_id=payload.analysis_id,
        case_id=case.id,
        tenant_id=current_user.tenant_id,
    )
    if analysis is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.AI_ANALYSIS_NOT_FOUND,
            message="分析结果不存在。",
            detail="分析结果不存在。",
        )

    input_params = payload.model_dump()
    task, created_new = service._create_or_reuse_task(
        case=case,
        current_user=current_user,
        task_type="falsify",
        input_params=input_params,
        idempotency_key=idempotency_key,
    )
    if created_new:
        service._append_case_flow(
            case_id=case.id,
            tenant_id=case.tenant_id,
            action_type="analysis_started",
            content=f"Started falsification task {task.task_id}.",
            operator_id=current_user.id,
            visible_to="both",
        )
        service.repo.commit()
        service._schedule_task_execution(task_id=task.task_id)

    return FalsificationStartResponse(task_id=task.task_id, status=task.status)
