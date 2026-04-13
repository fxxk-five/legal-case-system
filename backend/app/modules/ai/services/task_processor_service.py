from __future__ import annotations

from typing import TYPE_CHECKING

from app.modules.ai.schemas import AnalysisRequest, FalsificationRequest

if TYPE_CHECKING:
    from app.modules.ai.service import AIService


def process_task_by_id(service: AIService, *, task_id: str) -> None:
    with service.session_factory() as db:
        worker_service = service.__class__(
            db=db,
            request_id=service.request_id,
            session_factory=service.session_factory,
            worker_id=service.worker_id,
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
            _process_parse_task(worker_service, task=task, case=case, current_user=current_user)
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


def _process_parse_task(service: AIService, *, task, case, current_user) -> None:
    file_id = int((task.input_params or {}).get("file_id") or 0)
    if file_id <= 0:
        service._mark_failed(
            task_id=task.id,
            error_message="任务缺少 file_id。",
            fallback_message="文档解析失败。",
        )
        return
    file_record = service.repo.get_file(
        file_id=file_id,
        case_id=case.id,
        tenant_id=task.tenant_id,
    )
    if file_record is None:
        service._mark_failed(
            task_id=task.id,
            error_message="任务对应文件不存在。",
            fallback_message="文档解析失败。",
        )
        return
    service._execute_parse_task(
        task=task,
        case=case,
        file_record=file_record,
        parse_options=dict((task.input_params or {}).get("parse_options") or {}),
        current_user=current_user,
    )
