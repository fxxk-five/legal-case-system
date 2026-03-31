from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from fastapi import status

from app.core.errors import AppError, ErrorCode
from app.models.user import User
from app.modules.ai.models.ai_task import AITask
from app.modules.ai.schemas import AITaskRetryRequest, AITaskRetryResponse
from app.modules.cases.models.case import Case

if TYPE_CHECKING:
    from app.modules.ai.service import AIService


def retry_task(
    service: AIService,
    *,
    task_id: str,
    payload: AITaskRetryRequest,
    current_user: User,
) -> AITaskRetryResponse:
    service._ensure_role_for_action(current_user=current_user, action="retry")
    service._ensure_personal_tenant_ai_access(current_user=current_user)

    source_task = service.repo.get_task_by_task_id(task_id=task_id, tenant_id=current_user.tenant_id)
    if source_task is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.AI_TASK_NOT_FOUND,
            message="AI任务不存在。",
            detail="AI任务不存在。",
        )

    service._get_case_or_raise(case_id=source_task.case_id, current_user=current_user)
    if source_task.status != "failed":
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.CONFLICT,
            message="仅失败任务支持重试。",
            detail="仅失败任务支持重试。",
        )

    retry_input = dict(source_task.input_params or {})
    retry_input["source_task_id"] = source_task.task_id
    retry_input["retry_reason"] = payload.reason

    retry_task_record = service.repo.create_task(
        task_id=str(uuid4()),
        tenant_id=source_task.tenant_id,
        case_id=source_task.case_id,
        task_type=source_task.task_type,
        created_by=current_user.id,
        input_params=retry_input,
        request_id=service.request_id,
        idempotency_key=None,
    )
    service.repo.commit_and_refresh(retry_task_record)
    service._append_case_flow(
        case_id=source_task.case_id,
        tenant_id=source_task.tenant_id,
        action_type="analysis_retried",
        content=f"Retried {source_task.task_type} task {source_task.task_id} as {retry_task_record.task_id}.",
        operator_id=current_user.id,
        visible_to="both",
    )
    service.repo.commit()

    service._schedule_task_execution(task_id=retry_task_record.task_id)
    service.repo.refresh(retry_task_record)
    return AITaskRetryResponse(
        task_id=retry_task_record.task_id,
        source_task_id=source_task.task_id,
        status=retry_task_record.status,
        message=retry_task_record.message or "AI任务重试已创建。",
    )


def create_or_reuse_task(
    service: AIService,
    *,
    case: Case,
    current_user: User,
    task_type: str,
    input_params: dict,
    idempotency_key: str | None,
) -> tuple[AITask, bool]:
    normalized_idempotency_key = normalize_idempotency_key(idempotency_key)
    if normalized_idempotency_key:
        existing_task = service.repo.get_task_by_idempotency_key(
            tenant_id=current_user.tenant_id,
            case_id=case.id,
            task_type=task_type,
            created_by=current_user.id,
            idempotency_key=normalized_idempotency_key,
        )
        if existing_task is not None:
            if (existing_task.input_params or {}) != input_params:
                raise AppError(
                    status_code=status.HTTP_409_CONFLICT,
                    code=ErrorCode.AI_TASK_CONFLICT,
                    message="幂等键冲突，请更换 Idempotency-Key。",
                    detail="幂等键冲突，请更换 Idempotency-Key。",
                )
            return existing_task, False

    task = service.repo.create_task(
        task_id=str(uuid4()),
        tenant_id=current_user.tenant_id,
        case_id=case.id,
        task_type=task_type,
        created_by=current_user.id,
        input_params=input_params,
        request_id=service.request_id,
        idempotency_key=normalized_idempotency_key,
    )
    service.repo.commit_and_refresh(task)
    return task, True


def normalize_idempotency_key(idempotency_key: str | None) -> str | None:
    if idempotency_key is None:
        return None
    normalized = idempotency_key.strip()
    if not normalized:
        return None
    if len(normalized) > 128:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.VALIDATION_ERROR,
            message="Idempotency-Key 长度不能超过 128。",
            detail="Idempotency-Key 长度不能超过 128。",
        )
    return normalized
