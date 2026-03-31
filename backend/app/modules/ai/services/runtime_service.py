from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from app.core.config import settings
from app.modules.ai.models.ai_task import AITask
from app.modules.ai.services.runtime_helpers import effective_worker_id, get_queue_attempt

if TYPE_CHECKING:
    from app.modules.ai.service import AIService


logger = logging.getLogger("app.ai")


def mark_processing(
    service: AIService,
    *,
    task: AITask,
    message: str,
    progress: int,
    stage: str | None = None,
) -> None:
    if task.status in {"completed", "failed", "dead"}:
        return

    now = datetime.now(timezone.utc)
    task.status = "processing"
    task.progress = progress
    task.message = message
    task.started_at = task.started_at or now
    task.claimed_at = task.claimed_at or now
    task.heartbeat_at = now
    task.worker_id = task.worker_id or effective_worker_id(service)
    service.repo.save(task)
    if task.task_type == "analyze":
        service._sync_case_analysis_state(
            case_id=task.case_id,
            tenant_id=task.tenant_id,
            operator_id=task.created_by,
            status_value=stage or "processing",
            progress=progress,
            flow_content=f"Analyze task {task.task_id}: {stage or 'processing'} ({progress}%).",
        )
    service.repo.commit_and_refresh(task)


def mark_failed(
    service: AIService,
    *,
    task_id: int,
    error_message: str,
    fallback_message: str,
) -> None:
    task = service.repo.get_task_by_id(task_id=task_id)
    if task is None:
        return

    task.status = "failed"
    task.progress = min(task.progress, 99)
    task.message = fallback_message
    task.error_message = fallback_message
    task.completed_at = datetime.now(timezone.utc)
    task.heartbeat_at = datetime.now(timezone.utc)
    task.next_retry_at = None
    service.repo.save(task)
    if task.task_type == "analyze":
        service._sync_case_analysis_state(
            case_id=task.case_id,
            tenant_id=task.tenant_id,
            operator_id=task.created_by,
            status_value="failed",
            progress=min(task.progress, 99),
            flow_content=f"Analyze task {task.task_id}: failed ({min(task.progress, 99)}%).",
        )
    service._append_case_flow(
        case_id=task.case_id,
        tenant_id=task.tenant_id,
        action_type="analysis_failed",
        content=f"{task.task_type.title()} task {task.task_id} failed.",
        operator_id=task.created_by,
        visible_to="both",
    )
    service.repo.commit_and_refresh(task)
    logger.error(
        "ai.task.failed task_id=%s type=%s case_id=%s error=%s request_id=%s",
        task.task_id,
        task.task_type,
        task.case_id,
        error_message,
        service.request_id,
    )


def recover_stale_processing_tasks(service: AIService) -> int:
    stale_seconds = max(int(settings.AI_DB_QUEUE_STALE_TASK_SECONDS), 30)
    stale_before = datetime.now(timezone.utc) - timedelta(seconds=stale_seconds)
    stale_tasks = service.repo.list_stale_processing_tasks(stale_before=stale_before, limit=20)
    if not stale_tasks:
        return 0

    recovered = 0
    now = datetime.now(timezone.utc)
    max_retries = max(int(settings.AI_DB_QUEUE_MAX_RETRIES), 0)
    backoff_seconds = max(int(settings.AI_DB_QUEUE_RETRY_BACKOFF_SECONDS), 0)
    for task in stale_tasks:
        last_worker_id = task.worker_id or "unknown-worker"
        next_attempt = get_queue_attempt(task) + 1
        if next_attempt <= max_retries:
            task.retry_count = next_attempt
            task.status = "retrying"
            task.progress = 0
            task.message = f"Recovered stale task; retry scheduled ({next_attempt}/{max_retries})."
            task.error_message = "Worker heartbeat expired or worker stopped during processing."
            task.started_at = None
            task.completed_at = None
            task.claimed_at = None
            task.heartbeat_at = None
            task.next_retry_at = now + timedelta(seconds=backoff_seconds * max(1, next_attempt))
            task.worker_id = None
            service.repo.save(task)
            if task.task_type == "analyze":
                service._sync_case_analysis_state(
                    case_id=task.case_id,
                    tenant_id=task.tenant_id,
                    operator_id=task.created_by,
                    status_value="retrying",
                    progress=0,
                    flow_content=(
                        f"Analyze task {task.task_id}: retrying after stale worker recovery "
                        f"({next_attempt}/{max_retries})."
                    ),
                )
            service._append_case_flow(
                case_id=task.case_id,
                tenant_id=task.tenant_id,
                action_type="analysis_retry_scheduled",
                content=(
                    f"Task {task.task_id} recovered from stale worker {last_worker_id}; "
                    f"retry scheduled ({next_attempt}/{max_retries})."
                ),
                operator_id=task.created_by,
                visible_to="both",
            )
            recovered += 1
            continue

        task.retry_count = get_queue_attempt(task)
        task.status = "dead"
        task.progress = min(task.progress, 99)
        task.message = "Task moved to dead-letter after stale worker recovery exhausted retries."
        task.error_message = "Worker heartbeat expired or worker stopped during processing."
        task.completed_at = now
        task.claimed_at = None
        task.heartbeat_at = None
        task.next_retry_at = None
        task.worker_id = None
        service.repo.save(task)
        if task.task_type == "analyze":
            service._sync_case_analysis_state(
                case_id=task.case_id,
                tenant_id=task.tenant_id,
                operator_id=task.created_by,
                status_value="failed",
                progress=min(task.progress, 99),
                flow_content=f"Analyze task {task.task_id}: failed ({min(task.progress, 99)}%).",
            )
        service._append_case_flow(
            case_id=task.case_id,
            tenant_id=task.tenant_id,
            action_type="analysis_dead_lettered",
            content=(
                f"Task {task.task_id} moved to dead-letter after stale worker {last_worker_id} "
                "stopped sending heartbeats."
            ),
            operator_id=task.created_by,
            visible_to="both",
        )
        recovered += 1

    if recovered:
        service.repo.commit()
        logger.warning(
            "ai.queue.recovered_stale_tasks count=%s worker_id=%s request_id=%s",
            recovered,
            effective_worker_id(service),
            service.request_id,
        )
    return recovered


def apply_retry_or_dead_letter(service: AIService, *, task_id: str) -> None:
    with service.session_factory() as db:
        retry_service = service.__class__(
            db=db,
            request_id=service.request_id,
            session_factory=service.session_factory,
            worker_id=service.worker_id,
        )
        task = retry_service.repo.get_task_for_worker(task_id=task_id)
        if task is None or task.status != "failed":
            return

        max_retries = max(int(settings.AI_DB_QUEUE_MAX_RETRIES), 0)
        attempt = get_queue_attempt(task)

        if attempt < max_retries:
            next_attempt = attempt + 1
            next_retry_at = datetime.now(timezone.utc) + timedelta(
                seconds=max(int(settings.AI_DB_QUEUE_RETRY_BACKOFF_SECONDS), 0) * max(1, next_attempt)
            )
            task.retry_count = next_attempt
            task.status = "retrying"
            task.progress = 0
            task.message = f"Retry scheduled ({next_attempt}/{max_retries})."
            task.started_at = None
            task.completed_at = None
            task.claimed_at = None
            task.heartbeat_at = None
            task.worker_id = None
            task.next_retry_at = next_retry_at
            retry_service.repo.save(task)
            if task.task_type == "analyze":
                retry_service._sync_case_analysis_state(
                    case_id=task.case_id,
                    tenant_id=task.tenant_id,
                    operator_id=task.created_by,
                    status_value="retrying",
                    progress=0,
                    flow_content=f"Analyze task {task.task_id}: retrying ({next_attempt}/{max_retries}).",
                )
            retry_service._append_case_flow(
                case_id=task.case_id,
                tenant_id=task.tenant_id,
                action_type="analysis_retry_scheduled",
                content=f"Task {task.task_id} scheduled for retry ({next_attempt}/{max_retries}).",
                operator_id=task.created_by,
                visible_to="both",
            )
            retry_service.repo.commit()
            return

        task.retry_count = attempt
        task.status = "dead"
        task.message = "Task moved to dead-letter state after max retries."
        task.completed_at = datetime.now(timezone.utc)
        task.claimed_at = None
        task.heartbeat_at = None
        task.worker_id = None
        task.next_retry_at = None
        retry_service.repo.save(task)
        retry_service._append_case_flow(
            case_id=task.case_id,
            tenant_id=task.tenant_id,
            action_type="analysis_dead_lettered",
            content=f"Task {task.task_id} moved to dead-letter after {attempt} retries.",
            operator_id=task.created_by,
            visible_to="both",
        )
        retry_service.repo.commit()
