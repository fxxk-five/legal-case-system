from __future__ import annotations

import logging
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.integrations.llm.service import OpenAICompatibleProvider
from app.modules.ai.repository import AIRepository
from app.modules.ai.services import (
    access_service,
    analysis_service,
    budget_service,
    context_service,
    falsification_service,
    flow_service,
    parse_service,
    query_service,
    runtime_service,
    submission_service,
    task_command_service,
    task_processor_service,
    worker_dispatch_service,
)


logger = logging.getLogger("app.ai")


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

    start_parse_document = submission_service.start_parse_document
    list_case_facts = query_service.list_case_facts
    start_analysis = submission_service.start_analysis
    list_analysis_results = query_service.list_analysis_results
    start_falsification = submission_service.start_falsification
    list_falsification_results = query_service.list_falsification_results
    list_tasks = query_service.list_tasks
    get_task_status = query_service.get_task_status
    retry_task = task_command_service.retry_task

    _create_or_reuse_task = task_command_service.create_or_reuse_task
    _is_db_queue_driver = staticmethod(worker_dispatch_service.is_db_queue_driver)
    _should_run_inline = staticmethod(worker_dispatch_service.should_run_inline)
    _should_run_eager_in_background = staticmethod(worker_dispatch_service.should_run_eager_in_background)
    _start_background_task = worker_dispatch_service.start_background_task
    _schedule_task_execution = worker_dispatch_service.schedule_task_execution
    _run_task_in_background = worker_dispatch_service.run_task_in_background
    consume_queued_tasks_once = classmethod(worker_dispatch_service.consume_queued_tasks_once)
    consume_one_queued_task = worker_dispatch_service.consume_one_queued_task
    _recover_stale_processing_tasks = runtime_service.recover_stale_processing_tasks
    _apply_retry_or_dead_letter = runtime_service.apply_retry_or_dead_letter
    _process_task_by_id = task_processor_service.process_task_by_id
    _normalize_idempotency_key = staticmethod(task_command_service.normalize_idempotency_key)

    _execute_parse_task = parse_service.execute_parse_task
    _execute_analysis_task = analysis_service.execute_analysis_task
    _execute_falsification_task = falsification_service.execute_falsification_task
    _mark_processing = runtime_service.mark_processing
    _mark_failed = runtime_service.mark_failed
    _get_queue_attempt = staticmethod(runtime_service.get_queue_attempt)
    _effective_worker_id = runtime_service.effective_worker_id

    _resolve_budget_policy_for_analysis = budget_service.resolve_budget_policy_for_analysis
    _to_decimal_or_none = staticmethod(budget_service.to_decimal_or_none)
    _month_window = staticmethod(budget_service.month_window)
    _ensure_personal_tenant_ai_access = budget_service.ensure_personal_tenant_ai_access

    _sync_case_analysis_state = flow_service.sync_case_analysis_state
    _append_case_flow = flow_service.append_case_flow
    _get_case_or_raise = access_service.get_case_or_raise
    _ensure_role_for_action = access_service.ensure_role_for_action

    _build_parse_facts = parse_service.build_parse_facts
    _build_parse_facts_from_provider = parse_service.build_parse_facts_from_provider
    _normalize_win_rate = staticmethod(analysis_service.normalize_win_rate)
    _normalize_str_list = staticmethod(analysis_service.normalize_str_list)
    _normalize_severity = staticmethod(falsification_service.normalize_severity)
    _estimate_win_rate = staticmethod(analysis_service.estimate_win_rate)
    _build_analysis_summary = analysis_service.build_analysis_summary
    _build_strengths = staticmethod(analysis_service.build_strengths)
    _build_weaknesses = staticmethod(analysis_service.build_weaknesses)
    _build_recommendations = staticmethod(analysis_service.build_recommendations)
    _build_case_context = context_service.build_case_context
    _build_case_context_notes = staticmethod(context_service.build_case_context_notes)
    _sanitize_case_context_text = context_service.sanitize_case_context_text
    _derive_severity = staticmethod(falsification_service.derive_severity)
    _mask_sensitive = staticmethod(context_service.mask_sensitive)
