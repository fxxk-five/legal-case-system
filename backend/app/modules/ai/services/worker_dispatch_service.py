from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.modules.ai.queue import get_ai_queue_adapter, normalize_queue_driver

if TYPE_CHECKING:
    from app.modules.ai.service import AIService


logger = logging.getLogger("app.ai")


def is_db_queue_driver() -> bool:
    return normalize_queue_driver() == "db"


def should_run_inline() -> bool:
    return bool(settings.AI_DB_QUEUE_EAGER and settings.AI_DB_QUEUE_EAGER_BLOCKING)


def should_run_eager_in_background() -> bool:
    return bool(settings.AI_DB_QUEUE_EAGER and not settings.AI_DB_QUEUE_EAGER_BLOCKING)


def start_background_task(service: AIService, *, task_id: str) -> None:
    thread = threading.Thread(
        target=run_task_in_background,
        kwargs={"service": service, "task_id": task_id},
        daemon=True,
        name=f"ai-task-{task_id[:8]}",
    )
    thread.start()


def schedule_task_execution(service: AIService, *, task_id: str) -> None:
    if is_db_queue_driver():
        if should_run_inline():
            service._process_task_by_id(task_id=task_id)
            return
        if should_run_eager_in_background():
            start_background_task(service, task_id=task_id)
            return
        task = service.repo.get_task_for_worker(task_id=task_id)
        if task is not None:
            adapter = get_ai_queue_adapter("db")
            adapter.enqueue(task=task, request_id=service.request_id)
        return

    if should_run_inline():
        service._process_task_by_id(task_id=task_id)
        return
    if should_run_eager_in_background():
        start_background_task(service, task_id=task_id)
        return

    task = service.repo.get_task_for_worker(task_id=task_id)
    if task is None:
        logger.warning(
            "ai.task.missing_before_queue_dispatch task_id=%s request_id=%s",
            task_id,
            service.request_id,
        )
        return
    adapter = get_ai_queue_adapter()
    adapter.enqueue(task=task, request_id=service.request_id)


def run_task_in_background(service: AIService, *, task_id: str) -> None:
    try:
        service._process_task_by_id(task_id=task_id)
    except Exception:  # noqa: BLE001
        logger.exception(
            "ai.task.background_crashed task_id=%s request_id=%s",
            task_id,
            service.request_id,
        )


def consume_queued_tasks_once(
    service_cls: type[AIService],
    *,
    session_factory: Callable[[], Session] | None = None,
    request_id: str | None = None,
    max_tasks: int = 1,
    worker_id: str | None = None,
) -> int:
    factory = session_factory or SessionLocal
    consumed = 0
    for _ in range(max(1, max_tasks)):
        with factory() as db:
            service = service_cls(
                db=db,
                request_id=request_id,
                session_factory=factory,
                worker_id=worker_id,
            )
            if not consume_one_queued_task(service):
                break
            consumed += 1
    return consumed


def consume_one_queued_task(service: AIService) -> bool:
    if not is_db_queue_driver():
        return False

    service._recover_stale_processing_tasks()
    now = datetime.now(timezone.utc)
    task = service.repo.claim_next_runnable_task(now=now)
    if task is None:
        return False

    task.retry_count = service._get_queue_attempt(task)
    task.status = "processing"
    task.progress = max(task.progress, 1)
    task.message = "Task claimed by DB queue worker."
    task.started_at = now
    task.claimed_at = now
    task.heartbeat_at = now
    task.worker_id = service._effective_worker_id()
    task.next_retry_at = None
    service.repo.save_commit_refresh(task)

    try:
        service._process_task_by_id(task_id=task.task_id)
    finally:
        service._apply_retry_or_dead_letter(task_id=task.task_id)

    return True
