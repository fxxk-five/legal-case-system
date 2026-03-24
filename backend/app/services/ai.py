from __future__ import annotations

import logging
import os
import re
import threading
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.core.errors import AppError, ErrorCode
from app.models.ai_analysis import AIAnalysisResult
from app.models.ai_task import AITask
from app.models.case import Case
from app.models.case_fact import CaseFact
from app.models.falsification import FalsificationRecord
from app.models.file import File
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.ai import AIRepository
from app.schemas.ai import (
    AITaskListItem,
    AITaskListResponse,
    AITaskRetryRequest,
    AITaskRetryResponse,
    AITaskStatusRead,
    AnalysisRequest,
    AnalysisResultListResponse,
    AnalysisResultRead,
    AnalysisStartResponse,
    CaseFactListResponse,
    CaseFactRead,
    DocumentParseRequest,
    DocumentParseResponse,
    FalsificationRecordRead,
    FalsificationRequest,
    FalsificationResultResponse,
    FalsificationStartResponse,
    FalsificationSummary,
)
from app.services.case_flow import create_case_flow
from app.services.case_visibility import build_visible_case_query, ensure_personal_tenant_lawyer_case_visible
from app.services.ai_queue import get_ai_queue_adapter, normalize_queue_driver
from app.services.openai_compatible import OpenAICompatibleProvider, ProviderReply


logger = logging.getLogger("app.ai")
_AUTO_REANALYZE_IDEMPOTENCY_PREFIX = "auto-reanalyze:"
_QUEUE_ATTEMPT_KEY = "__queue_attempt"


class AIService:
    def __init__(
        self,
        db: Session,
        request_id: str | None = None,
        session_factory: Callable[[], Session] | None = None,
        worker_id: str | None = None,
    ) -> None:
        self.db = db
        self.repo = AIRepository(db)
        self.request_id = request_id
        self.provider = OpenAICompatibleProvider()
        self.session_factory = session_factory or SessionLocal
        self.worker_id = worker_id

    def start_parse_document(
        self,
        *,
        case_id: int,
        payload: DocumentParseRequest,
        current_user: User,
        idempotency_key: str | None = None,
    ) -> DocumentParseResponse:
        case = self._get_case_or_raise(case_id=case_id, current_user=current_user)
        self._ensure_role_for_action(current_user=current_user, action="parse")
        self._ensure_personal_tenant_ai_access(current_user=current_user)

        file_record = self.repo.get_file(
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
        task, created_new = self._create_or_reuse_task(
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

        self._append_case_flow(
            case_id=case.id,
            tenant_id=case.tenant_id,
            action_type="analysis_started",
            content=f"Started parse task {task.task_id}.",
            operator_id=current_user.id,
            visible_to="both",
        )
        self.db.commit()
        self._schedule_task_execution(task_id=task.task_id)

        return DocumentParseResponse(
            task_id=task.task_id,
            status=task.status,
            message=task.message or "文档解析任务已创建。",
        )

    def list_case_facts(
        self,
        *,
        case_id: int,
        current_user: User,
        fact_type: str | None,
        min_confidence: float | None,
        page: int,
        page_size: int,
    ) -> CaseFactListResponse:
        self._get_case_or_raise(case_id=case_id, current_user=current_user)

        total, facts = self.repo.list_case_facts(
            case_id=case_id,
            tenant_id=current_user.tenant_id,
            fact_type=fact_type,
            min_confidence=min_confidence,
            page=page,
            page_size=page_size,
        )
        return CaseFactListResponse(
            total=total,
            items=[self._to_case_fact_read(item) for item in facts],
        )

    def start_analysis(
        self,
        *,
        case_id: int,
        payload: AnalysisRequest,
        current_user: User,
        idempotency_key: str | None = None,
    ) -> AnalysisStartResponse:
        case = self._get_case_or_raise(case_id=case_id, current_user=current_user)
        self._ensure_role_for_action(current_user=current_user, action="analyze")
        self._ensure_personal_tenant_ai_access(current_user=current_user)

        is_auto_trigger = bool(
            idempotency_key and idempotency_key.startswith(_AUTO_REANALYZE_IDEMPOTENCY_PREFIX)
        )
        model_override = self._resolve_budget_policy_for_analysis(
            case=case,
            current_user=current_user,
            is_auto_trigger=is_auto_trigger,
        )
        input_params = payload.model_dump()
        if model_override:
            input_params["model_override"] = model_override
        input_params["trigger_source"] = "auto" if is_auto_trigger else "manual"
        task, created_new = self._create_or_reuse_task(
            case=case,
            current_user=current_user,
            task_type="analyze",
            input_params=input_params,
            idempotency_key=idempotency_key,
        )
        if created_new:
            case.analysis_status = "queued"
            case.analysis_progress = 0
            self.db.add(case)
            self._append_case_flow(
                case_id=case.id,
                tenant_id=case.tenant_id,
                action_type="analysis_started",
                content=f"Started analyze task {task.task_id}.",
                operator_id=current_user.id,
                visible_to="both",
            )
            self._append_case_flow(
                case_id=case.id,
                tenant_id=case.tenant_id,
                action_type="analysis_progress_updated",
                content=f"Analyze task {task.task_id}: queued (0%).",
                operator_id=current_user.id,
                visible_to="both",
            )
            self.db.commit()
            self._schedule_task_execution(task_id=task.task_id)

        return AnalysisStartResponse(task_id=task.task_id, status=task.status)

    def list_analysis_results(
        self,
        *,
        case_id: int,
        current_user: User,
    ) -> AnalysisResultListResponse:
        self._get_case_or_raise(case_id=case_id, current_user=current_user)

        records = self.repo.list_analysis_results(case_id=case_id, tenant_id=current_user.tenant_id)
        return AnalysisResultListResponse(items=[self._to_analysis_result_read(item) for item in records])

    def start_falsification(
        self,
        *,
        case_id: int,
        payload: FalsificationRequest,
        current_user: User,
        idempotency_key: str | None = None,
    ) -> FalsificationStartResponse:
        case = self._get_case_or_raise(case_id=case_id, current_user=current_user)
        self._ensure_role_for_action(current_user=current_user, action="falsify")
        self._ensure_personal_tenant_ai_access(current_user=current_user)

        analysis = self.repo.get_analysis_result(
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
        task, created_new = self._create_or_reuse_task(
            case=case,
            current_user=current_user,
            task_type="falsify",
            input_params=input_params,
            idempotency_key=idempotency_key,
        )
        if created_new:
            self._append_case_flow(
                case_id=case.id,
                tenant_id=case.tenant_id,
                action_type="analysis_started",
                content=f"Started falsification task {task.task_id}.",
                operator_id=current_user.id,
                visible_to="both",
            )
            self.db.commit()
            self._schedule_task_execution(task_id=task.task_id)

        return FalsificationStartResponse(task_id=task.task_id, status=task.status)

    def list_falsification_results(
        self,
        *,
        case_id: int,
        current_user: User,
    ) -> FalsificationResultResponse:
        self._get_case_or_raise(case_id=case_id, current_user=current_user)
        self._ensure_role_for_action(current_user=current_user, action="view_falsification")

        records = self.repo.list_falsification_records(case_id=case_id, tenant_id=current_user.tenant_id)
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
            items=[self._to_falsification_read(item) for item in records],
        )

    def list_tasks(
        self,
        *,
        current_user: User,
        page: int,
        page_size: int,
        status_filter: str | None,
        task_type: str | None,
    ) -> AITaskListResponse:
        if current_user.role == "client":
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code=ErrorCode.AI_OPERATION_NOT_ALLOWED,
                message="当前角色无权查询AI任务列表。",
                detail="当前角色无权查询AI任务列表。",
            )

        if current_user.role == "lawyer":
            visible_case_ids = select(
                build_visible_case_query(self.db, current_user)
                .with_entities(Case.id)
                .subquery()
                .c.id
            )
            total, tasks = self.repo.list_tasks(
                tenant_id=current_user.tenant_id,
                page=page,
                page_size=page_size,
                status_filter=status_filter,
                task_type=task_type,
                visible_case_ids=visible_case_ids,
            )
        else:
            total, tasks = self.repo.list_tasks(
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
            items=[
                AITaskListItem(
                    id=item.task_id,
                    task_id=item.task_id,
                    case_id=item.case_id,
                    task_type=item.task_type,
                    status=item.status,
                    progress=item.progress,
                    retry_count=item.retry_count,
                    next_retry_at=item.next_retry_at,
                    worker_id=item.worker_id,
                    message=item.message,
                    error_message=item.error_message,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                )
                for item in tasks
            ],
        )

    def get_task_status(self, *, task_id: str, current_user: User) -> AITaskStatusRead:
        task = self.repo.get_task_by_task_id(task_id=task_id, tenant_id=current_user.tenant_id)
        if task is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code=ErrorCode.AI_TASK_NOT_FOUND,
                message="AI任务不存在。",
                detail="AI任务不存在。",
        )

        self._get_case_or_raise(case_id=task.case_id, current_user=current_user)

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

    def retry_task(
        self,
        *,
        task_id: str,
        payload: AITaskRetryRequest,
        current_user: User,
    ) -> AITaskRetryResponse:
        self._ensure_role_for_action(current_user=current_user, action="retry")
        self._ensure_personal_tenant_ai_access(current_user=current_user)

        source_task = self.repo.get_task_by_task_id(task_id=task_id, tenant_id=current_user.tenant_id)
        if source_task is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code=ErrorCode.AI_TASK_NOT_FOUND,
                message="AI任务不存在。",
                detail="AI任务不存在。",
            )

        self._get_case_or_raise(case_id=source_task.case_id, current_user=current_user)
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

        retry_task = self.repo.create_task(
            task_id=str(uuid4()),
            tenant_id=source_task.tenant_id,
            case_id=source_task.case_id,
            task_type=source_task.task_type,
            created_by=current_user.id,
            input_params=retry_input,
            request_id=self.request_id,
            idempotency_key=None,
        )
        self.db.commit()
        self.db.refresh(retry_task)
        self._append_case_flow(
            case_id=source_task.case_id,
            tenant_id=source_task.tenant_id,
            action_type="analysis_retried",
            content=f"Retried {source_task.task_type} task {source_task.task_id} as {retry_task.task_id}.",
            operator_id=current_user.id,
            visible_to="both",
        )
        self.db.commit()

        self._schedule_task_execution(task_id=retry_task.task_id)
        self.db.refresh(retry_task)
        return AITaskRetryResponse(
            task_id=retry_task.task_id,
            source_task_id=source_task.task_id,
            status=retry_task.status,
            message=retry_task.message or "AI任务重试已创建。",
        )

    def _create_or_reuse_task(
        self,
        *,
        case: Case,
        current_user: User,
        task_type: str,
        input_params: dict,
        idempotency_key: str | None,
    ) -> tuple[AITask, bool]:
        normalized_idempotency_key = self._normalize_idempotency_key(idempotency_key)
        if normalized_idempotency_key:
            existing_task = self.repo.get_task_by_idempotency_key(
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

        task = self.repo.create_task(
            task_id=str(uuid4()),
            tenant_id=current_user.tenant_id,
            case_id=case.id,
            task_type=task_type,
            created_by=current_user.id,
            input_params=input_params,
            request_id=self.request_id,
            idempotency_key=normalized_idempotency_key,
        )
        self.db.commit()
        self.db.refresh(task)
        return task, True

    def _is_db_queue_driver(self) -> bool:
        return normalize_queue_driver() == "db"

    def _should_run_inline(self) -> bool:
        return bool(settings.AI_DB_QUEUE_EAGER)

    def _schedule_task_execution(self, *, task_id: str) -> None:
        if self._is_db_queue_driver():
            if self._should_run_inline():
                self._process_task_by_id(task_id=task_id)
                return
            task = self.repo.get_task_for_worker(task_id=task_id)
            if task is not None:
                adapter = get_ai_queue_adapter("db")
                adapter.enqueue(task=task, request_id=self.request_id)
            return

        if self._should_run_inline():
            self._process_task_by_id(task_id=task_id)
            return

        task = self.repo.get_task_for_worker(task_id=task_id)
        if task is None:
            logger.warning("ai.task.missing_before_queue_dispatch task_id=%s request_id=%s", task_id, self.request_id)
            return
        adapter = get_ai_queue_adapter()
        adapter.enqueue(task=task, request_id=self.request_id)

    def _run_task_in_background(self, *, task_id: str) -> None:
        try:
            self._process_task_by_id(task_id=task_id)
        except Exception:  # noqa: BLE001
            logger.exception(
                "ai.task.background_crashed task_id=%s request_id=%s",
                task_id,
                self.request_id,
            )

    @classmethod
    def consume_queued_tasks_once(
        cls,
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
                service = cls(
                    db=db,
                    request_id=request_id,
                    session_factory=factory,
                    worker_id=worker_id,
                )
                if not service.consume_one_queued_task():
                    break
                consumed += 1
        return consumed

    def consume_one_queued_task(self) -> bool:
        if not self._is_db_queue_driver():
            return False

        self._recover_stale_processing_tasks()
        now = datetime.now(timezone.utc)
        task = self.repo.claim_next_runnable_task(now=now)
        if task is None:
            return False

        task.retry_count = self._get_queue_attempt(task)
        task.status = "processing"
        task.progress = max(task.progress, 1)
        task.message = "Task claimed by DB queue worker."
        task.started_at = now
        task.claimed_at = now
        task.heartbeat_at = now
        task.worker_id = self._effective_worker_id()
        task.next_retry_at = None
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        try:
            self._process_task_by_id(task_id=task.task_id)
        finally:
            self._apply_retry_or_dead_letter(task_id=task.task_id)

        return True

    def _recover_stale_processing_tasks(self) -> int:
        stale_seconds = max(int(settings.AI_DB_QUEUE_STALE_TASK_SECONDS), 30)
        stale_before = datetime.now(timezone.utc) - timedelta(seconds=stale_seconds)
        stale_tasks = self.repo.list_stale_processing_tasks(stale_before=stale_before, limit=20)
        if not stale_tasks:
            return 0

        recovered = 0
        now = datetime.now(timezone.utc)
        max_retries = max(int(settings.AI_DB_QUEUE_MAX_RETRIES), 0)
        backoff_seconds = max(int(settings.AI_DB_QUEUE_RETRY_BACKOFF_SECONDS), 0)
        for task in stale_tasks:
            last_worker_id = task.worker_id or "unknown-worker"
            next_attempt = self._get_queue_attempt(task) + 1
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
                self.db.add(task)
                if task.task_type == "analyze":
                    self._sync_case_analysis_state(
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
                self._append_case_flow(
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

            task.retry_count = self._get_queue_attempt(task)
            task.status = "dead"
            task.progress = min(task.progress, 99)
            task.message = "Task moved to dead-letter after stale worker recovery exhausted retries."
            task.error_message = "Worker heartbeat expired or worker stopped during processing."
            task.completed_at = now
            task.claimed_at = None
            task.heartbeat_at = None
            task.next_retry_at = None
            task.worker_id = None
            self.db.add(task)
            if task.task_type == "analyze":
                self._sync_case_analysis_state(
                    case_id=task.case_id,
                    tenant_id=task.tenant_id,
                    operator_id=task.created_by,
                    status_value="failed",
                    progress=min(task.progress, 99),
                    flow_content=f"Analyze task {task.task_id}: failed ({min(task.progress, 99)}%).",
                )
            self._append_case_flow(
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
            self.db.commit()
            logger.warning(
                "ai.queue.recovered_stale_tasks count=%s worker_id=%s request_id=%s",
                recovered,
                self._effective_worker_id(),
                self.request_id,
            )
        return recovered

    def _apply_retry_or_dead_letter(self, *, task_id: str) -> None:
        with self.session_factory() as db:
            service = AIService(
                db=db,
                request_id=self.request_id,
                session_factory=self.session_factory,
                worker_id=self.worker_id,
            )
            task = service.repo.get_task_for_worker(task_id=task_id)
            if task is None or task.status != "failed":
                return

            max_retries = max(int(settings.AI_DB_QUEUE_MAX_RETRIES), 0)
            attempt = service._get_queue_attempt(task)

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
                service.db.add(task)
                if task.task_type == "analyze":
                    service._sync_case_analysis_state(
                        case_id=task.case_id,
                        tenant_id=task.tenant_id,
                        operator_id=task.created_by,
                        status_value="retrying",
                        progress=0,
                        flow_content=f"Analyze task {task.task_id}: retrying ({next_attempt}/{max_retries}).",
                    )
                service._append_case_flow(
                    case_id=task.case_id,
                    tenant_id=task.tenant_id,
                    action_type="analysis_retry_scheduled",
                    content=f"Task {task.task_id} scheduled for retry ({next_attempt}/{max_retries}).",
                    operator_id=task.created_by,
                    visible_to="both",
                )
                service.db.commit()
                return

            task.retry_count = attempt
            task.status = "dead"
            task.message = "Task moved to dead-letter state after max retries."
            task.completed_at = datetime.now(timezone.utc)
            task.claimed_at = None
            task.heartbeat_at = None
            task.worker_id = None
            task.next_retry_at = None
            service.db.add(task)
            service._append_case_flow(
                case_id=task.case_id,
                tenant_id=task.tenant_id,
                action_type="analysis_dead_lettered",
                content=f"Task {task.task_id} moved to dead-letter after {attempt} retries.",
                operator_id=task.created_by,
                visible_to="both",
            )
            service.db.commit()

    def _process_task_by_id(self, *, task_id: str) -> None:
        with self.session_factory() as db:
            worker_service = AIService(
                db=db,
                request_id=self.request_id,
                session_factory=self.session_factory,
                worker_id=self.worker_id,
            )
            task = worker_service.repo.get_task_for_worker(task_id=task_id)
            if task is None or task.status in {"completed", "failed", "dead"}:
                return

            case = worker_service.repo.get_case(case_id=task.case_id, tenant_id=task.tenant_id)
            if case is None:
                worker_service._mark_failed(
                    task_id=task.id,
                    error_message="任务关联案件不存在。",
                    fallback_message="AI任务执行失败。",
                )
                return

            if task.created_by is None:
                worker_service._mark_failed(
                    task_id=task.id,
                    error_message="任务缺少创建人信息。",
                    fallback_message="AI任务执行失败。",
                )
                return

            current_user = worker_service.repo.get_user(user_id=task.created_by, tenant_id=task.tenant_id)
            if current_user is None:
                worker_service._mark_failed(
                    task_id=task.id,
                    error_message="任务创建人不存在或不可用。",
                    fallback_message="AI任务执行失败。",
                )
                return

            if task.task_type == "parse":
                file_id = int((task.input_params or {}).get("file_id") or 0)
                if file_id <= 0:
                    worker_service._mark_failed(
                        task_id=task.id,
                        error_message="任务缺少 file_id。",
                        fallback_message="文档解析失败。",
                    )
                    return
                file_record = worker_service.repo.get_file(
                    file_id=file_id,
                    case_id=case.id,
                    tenant_id=task.tenant_id,
                )
                if file_record is None:
                    worker_service._mark_failed(
                        task_id=task.id,
                        error_message="任务对应文件不存在。",
                        fallback_message="文档解析失败。",
                    )
                    return
                worker_service._execute_parse_task(
                    task=task,
                    case=case,
                    file_record=file_record,
                    parse_options=dict((task.input_params or {}).get("parse_options") or {}),
                    current_user=current_user,
                )
                return

            if task.task_type == "analyze":
                payload = AnalysisRequest.model_validate(task.input_params or {})
                worker_service._execute_analysis_task(
                    task=task,
                    case=case,
                    payload=payload,
                    current_user=current_user,
                )
                return

            if task.task_type == "falsify":
                payload = FalsificationRequest.model_validate(task.input_params or {})
                analysis = worker_service.repo.get_analysis_result(
                    analysis_id=payload.analysis_id,
                    case_id=case.id,
                    tenant_id=task.tenant_id,
                )
                if analysis is None:
                    worker_service._mark_failed(
                        task_id=task.id,
                        error_message="任务对应分析结果不存在。",
                        fallback_message="证伪验证失败。",
                    )
                    return
                worker_service._execute_falsification_task(
                    task=task,
                    analysis=analysis,
                    payload=payload,
                    current_user=current_user,
                )
                return

            worker_service._mark_failed(
                task_id=task.id,
                error_message=f"不支持的任务类型: {task.task_type}",
                fallback_message="AI任务执行失败。",
            )

    def _normalize_idempotency_key(self, idempotency_key: str | None) -> str | None:
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

    def _execute_parse_task(
        self,
        *,
        task: AITask,
        case: Case,
        file_record: File,
        parse_options: dict,
        current_user: User,
    ) -> None:
        try:
            self._mark_processing(task=task, message="正在解析文档...", progress=20)
            self.repo.delete_case_facts_for_file(
                case_id=case.id,
                tenant_id=case.tenant_id,
                file_id=file_record.id,
            )

            if settings.AI_MOCK_MODE:
                facts = self._build_parse_facts(
                    case=case,
                    file_record=file_record,
                    parse_options=parse_options,
                    created_by=current_user.id,
                )
            else:
                provider_reply = self.provider.generate_parse_facts(
                    case_number=case.case_number,
                    case_title=case.title,
                    file_name=file_record.file_name,
                    file_type=file_record.file_type,
                    parse_options=parse_options,
                )
                facts = self._build_parse_facts_from_provider(
                    case=case,
                    file_record=file_record,
                    created_by=current_user.id,
                    provider_reply=provider_reply,
                    fallback_parse_options=parse_options,
                )
            self.repo.save_case_facts(facts)
            self.db.flush()

            task.status = "completed"
            task.progress = 100
            task.result_id = facts[0].id if facts else None
            task.message = f"文档解析完成，共提取 {len(facts)} 条事实。"
            task.completed_at = datetime.now(timezone.utc)
            task.heartbeat_at = task.completed_at
            task.next_retry_at = None
            self.db.add(task)
            self._append_case_flow(
                case_id=case.id,
                tenant_id=case.tenant_id,
                action_type="analysis_completed",
                content=f"Parse task {task.task_id} completed.",
                operator_id=current_user.id,
                visible_to="both",
            )
            self.db.commit()
            self.db.refresh(task)
            logger.info(
                "ai.parse.completed task_id=%s case_id=%s facts=%s request_id=%s",
                task.task_id,
                case.id,
                len(facts),
                self.request_id,
            )
        except Exception as exc:  # noqa: BLE001
            self.db.rollback()
            self._mark_failed(task_id=task.id, error_message=str(exc), fallback_message="文档解析失败。")

    def _execute_analysis_task(
        self,
        *,
        task: AITask,
        case: Case,
        payload: AnalysisRequest,
        current_user: User,
    ) -> None:
        try:
            self._mark_processing(
                task=task,
                message="正在收集案件事实...",
                progress=20,
                stage="collecting_facts",
            )

            _, case_facts = self.repo.list_case_facts(
                case_id=case.id,
                tenant_id=case.tenant_id,
                fact_type=None,
                min_confidence=None,
                page=1,
                page_size=500,
            )
            fact_texts = [item.content for item in case_facts]
            self._mark_processing(
                task=task,
                message="正在生成分析结论...",
                progress=60,
                stage="generating_summary",
            )

            analysis_types = payload.analysis_types or ["legal_analysis", "case_strength", "strategy"]
            rows: list[AIAnalysisResult] = []
            model_override = str((task.input_params or {}).get("model_override") or "").strip() or None
            for index, analysis_type in enumerate(analysis_types):
                if settings.AI_MOCK_MODE:
                    summary = self._build_analysis_summary(
                        case=case,
                        analysis_type=analysis_type,
                        fact_texts=fact_texts,
                        focus_areas=payload.focus_areas,
                    )
                    win_rate = self._estimate_win_rate(case_facts_count=len(case_facts), offset=index)
                    strengths = self._build_strengths(case_facts)
                    weaknesses = self._build_weaknesses(case_facts)
                    recommendations = self._build_recommendations(payload.focus_areas)
                    applicable_laws = ["中华人民共和国民法典 第1165条"]
                    related_cases = ["(2024)京01民终1234号"]
                    ai_model = "mock-legal-v1"
                    token_usage = max(600, 300 + len(fact_texts) * 120)
                else:
                    provider_reply = self.provider.generate_analysis(
                        case_title=case.title,
                        analysis_type=analysis_type,
                        fact_texts=fact_texts,
                        focus_areas=payload.focus_areas,
                        include_precedents=payload.include_precedents,
                        model_override=model_override,
                    )
                    summary = str(provider_reply.payload.get("summary") or "").strip()
                    if not summary:
                        summary = self._build_analysis_summary(
                            case=case,
                            analysis_type=analysis_type,
                            fact_texts=fact_texts,
                            focus_areas=payload.focus_areas,
                        )
                    win_rate = self._normalize_win_rate(
                        provider_reply.payload.get("win_rate"),
                        default=self._estimate_win_rate(case_facts_count=len(case_facts), offset=index),
                    )
                    strengths = self._normalize_str_list(
                        provider_reply.payload.get("strengths"),
                        fallback=self._build_strengths(case_facts),
                    )
                    weaknesses = self._normalize_str_list(
                        provider_reply.payload.get("weaknesses"),
                        fallback=self._build_weaknesses(case_facts),
                    )
                    recommendations = self._normalize_str_list(
                        provider_reply.payload.get("recommendations"),
                        fallback=self._build_recommendations(payload.focus_areas),
                    )
                    applicable_laws = self._normalize_str_list(
                        provider_reply.payload.get("applicable_laws"),
                        fallback=["中华人民共和国民法典 第1165条"],
                    )
                    related_cases = self._normalize_str_list(
                        provider_reply.payload.get("related_cases"),
                        fallback=[],
                    )
                    ai_model = provider_reply.model
                    token_usage = max(int(provider_reply.token_usage or 0), 200)

                cost = Decimal(token_usage) / Decimal(1000) * Decimal(str(settings.AI_TOKEN_COST_PER_1K))

                row = AIAnalysisResult(
                    tenant_id=case.tenant_id,
                    case_id=case.id,
                    analysis_type=analysis_type,
                    result_data={
                        "summary": summary,
                        "win_rate": win_rate,
                        "focus_areas": payload.focus_areas,
                        "include_precedents": payload.include_precedents,
                        "applicable_laws": applicable_laws,
                        "legal_opinion": summary,
                    },
                    applicable_laws=applicable_laws,
                    related_cases=related_cases,
                    strengths=strengths,
                    weaknesses=weaknesses,
                    recommendations=recommendations,
                    ai_model=ai_model,
                    token_usage=token_usage,
                    cost=cost.quantize(Decimal("0.0001")),
                    created_by=current_user.id,
                )
                rows.append(row)

            self.repo.save_analysis_results(rows)
            self.db.flush()
            self._mark_processing(
                task=task,
                message="正在写入分析结果...",
                progress=90,
                stage="persisting_results",
            )

            task.status = "completed"
            task.progress = 100
            task.result_id = rows[0].id if rows else None
            task.message = f"法律分析完成，生成 {len(rows)} 条分析结果。"
            task.completed_at = datetime.now(timezone.utc)
            task.heartbeat_at = task.completed_at
            task.next_retry_at = None
            self.db.add(task)
            case.analysis_status = "completed"
            case.analysis_progress = 100
            self.db.add(case)
            self._append_case_flow(
                case_id=case.id,
                tenant_id=case.tenant_id,
                action_type="analysis_completed",
                content=f"Analyze task {task.task_id} completed.",
                operator_id=current_user.id,
                visible_to="both",
            )
            self._append_case_flow(
                case_id=case.id,
                tenant_id=case.tenant_id,
                action_type="analysis_progress_updated",
                content=f"Analyze task {task.task_id}: completed (100%).",
                operator_id=current_user.id,
                visible_to="both",
            )
            self.db.commit()
            self.db.refresh(task)
            logger.info(
                "ai.analysis.completed task_id=%s case_id=%s results=%s request_id=%s",
                task.task_id,
                case.id,
                len(rows),
                self.request_id,
            )
        except Exception as exc:  # noqa: BLE001
            self.db.rollback()
            self._mark_failed(task_id=task.id, error_message=str(exc), fallback_message="法律分析失败。")

    def _execute_falsification_task(
        self,
        *,
        task: AITask,
        analysis: AIAnalysisResult,
        payload: FalsificationRequest,
        current_user: User,
    ) -> None:
        try:
            self._mark_processing(task=task, message="正在执行证伪验证...", progress=35)

            records: list[FalsificationRecord] = []
            for iteration in range(1, payload.iteration_count + 1):
                for mode in payload.challenge_modes:
                    if settings.AI_MOCK_MODE:
                        basis = sum(ord(char) for char in f"{analysis.id}:{mode}:{iteration}")
                        is_falsified = basis % 3 == 0
                        severity = self._derive_severity(mode=mode, is_falsified=is_falsified)
                        challenge_question = f"[{mode}] 第 {iteration} 轮质询：该结论是否存在事实或法律层面的漏洞？"
                        response = "发现可证伪点，需补强证据链。" if is_falsified else "未发现可明确证伪点。"
                        improvement = (
                            "建议补充证据来源、时间线和条款适用依据。"
                            if is_falsified
                            else "维持当前论证结构，持续监测新增证据。"
                        )
                        ai_model = "mock-legal-v1"
                    else:
                        provider_reply = self.provider.generate_falsification(
                            case_title=analysis.case.title if analysis.case else "",
                            analysis_summary=str((analysis.result_data or {}).get("summary") or ""),
                            challenge_mode=mode,
                            iteration=iteration,
                        )
                        provider_payload = provider_reply.payload
                        is_falsified = bool(provider_payload.get("is_falsified", False))
                        severity = self._normalize_severity(
                            provider_payload.get("severity"),
                            fallback=self._derive_severity(mode=mode, is_falsified=is_falsified),
                        )
                        challenge_question = str(
                            provider_payload.get("challenge_question")
                            or f"[{mode}] 第 {iteration} 轮质询：该结论是否存在事实或法律层面的漏洞？"
                        )
                        response = str(
                            provider_payload.get("response")
                            or ("发现可证伪点，需补强证据链。" if is_falsified else "未发现可明确证伪点。")
                        )
                        improvement = str(
                            provider_payload.get("improvement_suggestion")
                            or (
                                "建议补充证据来源、时间线和条款适用依据。"
                                if is_falsified
                                else "维持当前论证结构，持续监测新增证据。"
                            )
                        )
                        ai_model = provider_reply.model

                    records.append(
                        FalsificationRecord(
                            tenant_id=analysis.tenant_id,
                            case_id=analysis.case_id,
                            analysis_id=analysis.id,
                            challenge_type=mode,
                            challenge_question=challenge_question,
                            response=response,
                            is_falsified=is_falsified,
                            severity=severity,
                            improvement_suggestion=improvement,
                            iteration=iteration,
                            ai_model=ai_model,
                            created_by=current_user.id,
                        )
                    )

            self.repo.save_falsification_records(records)
            self.db.flush()

            task.status = "completed"
            task.progress = 100
            task.result_id = records[0].id if records else None
            task.message = f"证伪验证完成，生成 {len(records)} 条记录。"
            task.completed_at = datetime.now(timezone.utc)
            task.heartbeat_at = task.completed_at
            task.next_retry_at = None
            self.db.add(task)
            self._append_case_flow(
                case_id=analysis.case_id,
                tenant_id=analysis.tenant_id,
                action_type="analysis_completed",
                content=f"Falsification task {task.task_id} completed.",
                operator_id=current_user.id,
                visible_to="both",
            )
            self.db.commit()
            self.db.refresh(task)
            logger.info(
                "ai.falsify.completed task_id=%s case_id=%s records=%s request_id=%s",
                task.task_id,
                analysis.case_id,
                len(records),
                self.request_id,
            )
        except Exception as exc:  # noqa: BLE001
            self.db.rollback()
            self._mark_failed(task_id=task.id, error_message=str(exc), fallback_message="证伪验证失败。")

    def _mark_processing(
        self,
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
        task.worker_id = task.worker_id or self._effective_worker_id()
        self.db.add(task)
        if task.task_type == "analyze":
            self._sync_case_analysis_state(
                case_id=task.case_id,
                tenant_id=task.tenant_id,
                operator_id=task.created_by,
                status_value=stage or "processing",
                progress=progress,
                flow_content=f"Analyze task {task.task_id}: {stage or 'processing'} ({progress}%).",
            )
        self.db.commit()
        self.db.refresh(task)

    def _mark_failed(self, *, task_id: int, error_message: str, fallback_message: str) -> None:
        task = self.repo.get_task_by_id(task_id=task_id)
        if task is None:
            return

        task.status = "failed"
        task.progress = min(task.progress, 99)
        task.message = fallback_message
        task.error_message = error_message
        task.completed_at = datetime.now(timezone.utc)
        task.heartbeat_at = datetime.now(timezone.utc)
        task.next_retry_at = None
        self.db.add(task)
        if task.task_type == "analyze":
            self._sync_case_analysis_state(
                case_id=task.case_id,
                tenant_id=task.tenant_id,
                operator_id=task.created_by,
                status_value="failed",
                progress=min(task.progress, 99),
                flow_content=f"Analyze task {task.task_id}: failed ({min(task.progress, 99)}%).",
            )
        self._append_case_flow(
            case_id=task.case_id,
            tenant_id=task.tenant_id,
            action_type="analysis_failed",
            content=f"{task.task_type.title()} task {task.task_id} failed.",
            operator_id=task.created_by,
            visible_to="both",
        )
        self.db.commit()
        self.db.refresh(task)
        logger.error(
            "ai.task.failed task_id=%s type=%s case_id=%s error=%s request_id=%s",
            task.task_id,
            task.task_type,
            task.case_id,
            error_message,
            self.request_id,
        )

    def _get_queue_attempt(self, task: AITask) -> int:
        try:
            retry_count = int(task.retry_count or 0)
        except (TypeError, ValueError):
            retry_count = 0
        if retry_count > 0:
            return retry_count

        raw_attempt = (task.input_params or {}).get(_QUEUE_ATTEMPT_KEY)
        try:
            return int(raw_attempt or 0)
        except (TypeError, ValueError):
            return 0

    def _effective_worker_id(self) -> str:
        configured = str(self.worker_id or settings.AI_DB_QUEUE_WORKER_ID or "").strip()
        if configured:
            return configured
        return os.getenv("HOSTNAME") or os.getenv("COMPUTERNAME") or "ai-worker"

    def _resolve_budget_policy_for_analysis(
        self,
        *,
        case: Case,
        current_user: User,
        is_auto_trigger: bool,
    ) -> str | None:
        tenant = self.db.query(Tenant).filter(Tenant.id == case.tenant_id).first()
        monthly_limit = self._to_decimal_or_none(
            tenant.ai_monthly_budget_limit if tenant is not None else settings.AI_MONTHLY_BUDGET_LIMIT
        )
        case_limit = self._to_decimal_or_none(
            case.ai_case_budget_limit
            if case.ai_case_budget_limit is not None
            else settings.AI_CASE_BUDGET_LIMIT
        )
        degrade_model = (
            str(
                (tenant.ai_budget_degrade_model if tenant is not None else "")
                or settings.AI_BUDGET_DEGRADE_MODEL
                or ""
            )
            .strip()
            or None
        )

        monthly_spent = Decimal("0")
        case_spent = Decimal("0")
        if monthly_limit is not None:
            month_start, month_end = self._month_window(datetime.now(timezone.utc))
            monthly_spent = self.repo.sum_analysis_cost_for_tenant_in_month(
                tenant_id=case.tenant_id,
                month_start=month_start,
                month_end=month_end,
            )
        if case_limit is not None:
            case_spent = self.repo.sum_analysis_cost_for_case(case_id=case.id, tenant_id=case.tenant_id)

        over_monthly = monthly_limit is not None and monthly_spent >= monthly_limit
        over_case = case_limit is not None and case_spent >= case_limit
        if not (over_monthly or over_case):
            return None

        reason_parts: list[str] = []
        if over_monthly and monthly_limit is not None:
            reason_parts.append(f"tenant monthly limit reached ({monthly_spent}/{monthly_limit})")
        if over_case and case_limit is not None:
            reason_parts.append(f"case limit reached ({case_spent}/{case_limit})")
        reason = "; ".join(reason_parts) or "budget limit reached"

        if not is_auto_trigger and degrade_model and degrade_model != settings.EFFECTIVE_AI_MODEL:
            self._append_case_flow(
                case_id=case.id,
                tenant_id=case.tenant_id,
                action_type="analysis_model_downgraded",
                content=f"Budget control applied; downgraded to model {degrade_model} ({reason}).",
                operator_id=current_user.id,
                visible_to="both",
            )
            self.db.commit()
            return degrade_model

        self._append_case_flow(
            case_id=case.id,
            tenant_id=case.tenant_id,
            action_type="analysis_budget_circuit_open",
            content=f"Budget circuit open; analyze request blocked ({reason}).",
            operator_id=current_user.id,
            visible_to="both",
        )
        self.db.commit()
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.AI_BUDGET_EXCEEDED,
            message="AI预算已超限，当前请求已被熔断。",
            detail=f"AI预算已超限，当前请求已被熔断。{reason}",
        )

    def _to_decimal_or_none(self, value: object | None) -> Decimal | None:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        try:
            parsed = Decimal(str(value))
        except Exception:  # noqa: BLE001
            return None
        if parsed <= 0:
            return None
        return parsed

    def _month_window(self, now: datetime) -> tuple[datetime, datetime]:
        current = now.astimezone(timezone.utc)
        month_start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1)
        return month_start, month_end

    def _sync_case_analysis_state(
        self,
        *,
        case_id: int,
        tenant_id: int,
        operator_id: int | None,
        status_value: str,
        progress: int,
        flow_content: str,
    ) -> None:
        case = self.repo.get_case(case_id=case_id, tenant_id=tenant_id)
        if case is None:
            return

        case.analysis_status = status_value
        case.analysis_progress = max(0, min(100, int(progress)))
        self.db.add(case)
        self._append_case_flow(
            case_id=case_id,
            tenant_id=tenant_id,
            action_type="analysis_progress_updated",
            content=flow_content,
            operator_id=operator_id,
            visible_to="both",
        )

    def _append_case_flow(
        self,
        *,
        case_id: int,
        tenant_id: int,
        action_type: str,
        content: str,
        operator_id: int | None,
        visible_to: str,
    ) -> None:
        case_exists = self.repo.get_case(case_id=case_id, tenant_id=tenant_id)
        if case_exists is None:
            return

        operator = None
        if operator_id is not None:
            operator = self.repo.get_user(user_id=operator_id, tenant_id=tenant_id)

        create_case_flow(
            db=self.db,
            tenant_id=tenant_id,
            case_id=case_id,
            action_type=action_type,
            content=content,
            operator=operator,
            visible_to=visible_to,
        )

    def _get_case_or_raise(self, *, case_id: int, current_user: User) -> Case:
        case = self.repo.get_case(case_id=case_id, tenant_id=current_user.tenant_id)
        if case is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code=ErrorCode.CASE_NOT_FOUND,
                message="案件不存在。",
                detail="案件不存在。",
            )
        ensure_personal_tenant_lawyer_case_visible(
            self.db,
            current_user=current_user,
            case_id=case.id,
        )

        if current_user.role == "client" and case.client_id != current_user.id:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code=ErrorCode.CASE_ACCESS_DENIED,
                message="无权访问该案件。",
                detail="无权访问该案件。",
            )
        return case

    def _ensure_role_for_action(self, *, current_user: User, action: str) -> None:
        if action in {"parse", "analyze", "falsify", "retry"} and current_user.role not in {
            "lawyer",
            "tenant_admin",
        }:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code=ErrorCode.AI_OPERATION_NOT_ALLOWED,
                message="当前角色无权执行该AI操作。",
                detail="当前角色无权执行该AI操作。",
            )

        if action == "view_falsification" and current_user.role == "client":
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code=ErrorCode.AI_OPERATION_NOT_ALLOWED,
                message="当前角色无权查看证伪结果。",
                detail="当前角色无权查看证伪结果。",
            )

    def _ensure_personal_tenant_ai_access(self, *, current_user: User) -> None:
        tenant = self.db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
        if tenant is None or tenant.type != "personal":
            return

        is_subscription_valid = (
            tenant.subscription_expire_at is not None
            and tenant.subscription_expire_at > datetime.now(timezone.utc)
        )
        has_balance = bool(tenant.balance and Decimal(str(tenant.balance)) > Decimal("0"))
        if not (is_subscription_valid or has_balance):
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code=ErrorCode.AI_OPERATION_NOT_ALLOWED,
                message="独户律师订阅已失效且余额不足，无法发起AI任务。",
                detail="独户律师订阅已失效且余额不足，无法发起AI任务。",
            )

    def _build_parse_facts(
        self,
        *,
        case: Case,
        file_record: File,
        parse_options: dict,
        created_by: int,
    ) -> list[CaseFact]:
        now_iso = datetime.now(timezone.utc).isoformat()
        facts: list[CaseFact] = []

        if parse_options.get("extract_parties", True):
            facts.append(
                CaseFact(
                    tenant_id=case.tenant_id,
                    case_id=case.id,
                    file_id=file_record.id,
                    fact_type="party",
                    content=self._mask_sensitive(f"案件当事人已绑定，案件标题：{case.title}"),
                    source_page=1,
                    confidence=0.93,
                    fact_metadata={"entity_type": "party", "source": "case_profile"},
                    created_by=created_by,
                )
            )

        if parse_options.get("extract_timeline", True):
            facts.append(
                CaseFact(
                    tenant_id=case.tenant_id,
                    case_id=case.id,
                    file_id=file_record.id,
                    fact_type="timeline",
                    content=f"文档 {file_record.file_name} 已上传并进入AI解析流程。",
                    source_page=1,
                    confidence=0.9,
                    fact_metadata={"date": now_iso, "source": "file_upload"},
                    created_by=created_by,
                )
            )

        if parse_options.get("extract_evidence", True):
            facts.append(
                CaseFact(
                    tenant_id=case.tenant_id,
                    case_id=case.id,
                    file_id=file_record.id,
                    fact_type="evidence",
                    content=f"已识别证据文件：{file_record.file_name}（{file_record.file_type}）。",
                    source_page=1,
                    confidence=0.88,
                    fact_metadata={"evidence_id": file_record.id, "source": "file_metadata"},
                    created_by=created_by,
                )
            )

        if parse_options.get("extract_laws", True):
            facts.append(
                CaseFact(
                    tenant_id=case.tenant_id,
                    case_id=case.id,
                    file_id=file_record.id,
                    fact_type="law_reference",
                    content="初步匹配《中华人民共和国民法典》第1165条（侵权责任一般条款）。",
                    source_page=1,
                    confidence=0.82,
                    fact_metadata={"law_name": "中华人民共和国民法典", "article": "第1165条"},
                    created_by=created_by,
                )
            )

        return facts

    def _build_parse_facts_from_provider(
        self,
        *,
        case: Case,
        file_record: File,
        created_by: int,
        provider_reply: ProviderReply,
        fallback_parse_options: dict,
    ) -> list[CaseFact]:
        facts_payload = provider_reply.payload.get("facts")
        if not isinstance(facts_payload, list) or not facts_payload:
            return self._build_parse_facts(
                case=case,
                file_record=file_record,
                parse_options=fallback_parse_options,
                created_by=created_by,
            )

        facts: list[CaseFact] = []
        allowed_fact_types = {"party", "timeline", "evidence", "law_reference"}
        for item in facts_payload[:20]:
            if not isinstance(item, dict):
                continue

            fact_type_raw = str(item.get("fact_type") or "timeline").strip().lower()
            fact_type = fact_type_raw if fact_type_raw in allowed_fact_types else "timeline"
            content = str(item.get("content") or "").strip()
            if not content:
                continue
            source_page = item.get("source_page")
            source_page_value = source_page if isinstance(source_page, int) and source_page > 0 else 1
            confidence = self._normalize_win_rate(item.get("confidence"), default=0.8)
            metadata = item.get("metadata")
            metadata_value = metadata if isinstance(metadata, dict) else {}

            facts.append(
                CaseFact(
                    tenant_id=case.tenant_id,
                    case_id=case.id,
                    file_id=file_record.id,
                    fact_type=fact_type,
                    content=self._mask_sensitive(content),
                    source_page=source_page_value,
                    confidence=confidence,
                    fact_metadata=metadata_value,
                    created_by=created_by,
                )
            )

        if not facts:
            return self._build_parse_facts(
                case=case,
                file_record=file_record,
                parse_options=fallback_parse_options,
                created_by=created_by,
            )
        return facts

    def _normalize_win_rate(self, value: object, *, default: float) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return default
        return max(0.0, min(1.0, round(parsed, 2)))

    def _normalize_str_list(self, value: object, *, fallback: list[str]) -> list[str]:
        if not isinstance(value, list):
            return fallback
        normalized = [str(item).strip() for item in value if str(item).strip()]
        return normalized[:8] if normalized else fallback

    def _normalize_severity(self, value: object, *, fallback: str) -> str:
        severity = str(value or "").strip().lower()
        if severity in {"critical", "major", "minor"}:
            return severity
        return fallback

    def _estimate_win_rate(self, *, case_facts_count: int, offset: int) -> float:
        base = 0.55 + min(case_facts_count, 20) * 0.01 - offset * 0.03
        if case_facts_count == 0:
            base = 0.42
        return max(0.2, min(0.95, round(base, 2)))

    def _build_analysis_summary(
        self,
        *,
        case: Case,
        analysis_type: str,
        fact_texts: list[str],
        focus_areas: list[str],
    ) -> str:
        focus = "、".join(focus_areas) if focus_areas else "证据链完整性与法律适用"
        facts_hint = f"已纳入 {len(fact_texts)} 条案件事实" if fact_texts else "当前事实较少，建议先补充材料"
        return f"[{analysis_type}] {case.title}：{facts_hint}，重点关注 {focus}。"

    def _build_strengths(self, facts: list[CaseFact]) -> list[str]:
        if not facts:
            return ["已建立基础案件信息，可继续补充关键证据。"]
        return [
            "证据与时间线已形成初步闭环。",
            "关键事实具备来源标记，便于后续举证。",
        ]

    def _build_weaknesses(self, facts: list[CaseFact]) -> list[str]:
        if len(facts) < 3:
            return ["事实样本偏少，建议继续上传关联材料。"]
        return [
            "部分事实仍依赖单一来源，抗辩稳定性一般。",
            "损失量化依据需要进一步补强。",
        ]

    def _build_recommendations(self, focus_areas: list[str]) -> list[str]:
        suggestions = [
            "补充证据目录与时间线对应关系表。",
            "针对争议焦点准备两套备选论证路径。",
            "在开庭前完成证据合法性与关联性复核。",
        ]
        if focus_areas:
            suggestions.insert(0, f"围绕重点关注项（{'、'.join(focus_areas)}）补充专项材料。")
        return suggestions[:4]

    def _derive_severity(self, *, mode: str, is_falsified: bool) -> str:
        if not is_falsified:
            return "minor"
        if mode == "evidence":
            return "critical"
        if mode == "logic":
            return "major"
        return "major"

    def _mask_sensitive(self, text: str) -> str:
        text = re.sub(r"(?<!\d)(1\d{2})\d{4}(\d{4})(?!\d)", r"\1****\2", text)
        text = re.sub(r"(?<!\d)(\d{6})\d{8}(\w{4})(?!\w)", r"\1********\2", text)
        return text

    def _to_case_fact_read(self, fact: CaseFact) -> CaseFactRead:
        metadata = fact.fact_metadata or {}
        occurrence_time = metadata.get("date") if isinstance(metadata, dict) else None
        evidence_id = metadata.get("evidence_id") if isinstance(metadata, dict) else None
        evidence_id_value = int(evidence_id) if isinstance(evidence_id, (int, float)) else None

        return CaseFactRead(
            id=fact.id,
            case_id=fact.case_id,
            file_id=fact.file_id,
            fact_type=fact.fact_type,
            content=fact.content,
            source_page=fact.source_page,
            confidence=float(fact.confidence),
            metadata=metadata,
            created_at=fact.created_at,
            description=fact.content,
            occurrence_time=occurrence_time,
            evidence_id=evidence_id_value,
        )

    def _to_analysis_result_read(self, row: AIAnalysisResult) -> AnalysisResultRead:
        result_data = row.result_data or {}
        summary = str(result_data.get("summary") or result_data.get("legal_opinion") or "")
        win_rate_raw = result_data.get("win_rate", 0.0)
        try:
            win_rate = float(win_rate_raw)
        except (TypeError, ValueError):
            win_rate = 0.0
        win_rate = max(0.0, min(1.0, win_rate))

        return AnalysisResultRead(
            id=row.id,
            case_id=row.case_id,
            analysis_type=row.analysis_type,
            result_data=result_data,
            applicable_laws=list(row.applicable_laws or []),
            related_cases=list(row.related_cases or []),
            strengths=list(row.strengths or []),
            weaknesses=list(row.weaknesses or []),
            recommendations=list(row.recommendations or []),
            ai_model=row.ai_model,
            token_usage=row.token_usage,
            cost=row.cost,
            created_at=row.created_at,
            summary=summary,
            win_rate=win_rate,
        )

    def _to_falsification_read(self, row: FalsificationRecord) -> FalsificationRecordRead:
        return FalsificationRecordRead(
            id=row.id,
            case_id=row.case_id,
            analysis_id=row.analysis_id,
            challenge_type=row.challenge_type,
            challenge_question=row.challenge_question,
            response=row.response,
            is_falsified=row.is_falsified,
            severity=row.severity,
            improvement_suggestion=row.improvement_suggestion,
            iteration=row.iteration,
            ai_model=row.ai_model,
            created_at=row.created_at,
            fact_description=row.challenge_question,
            reason=row.response,
            evidence_gap=row.improvement_suggestion,
        )
