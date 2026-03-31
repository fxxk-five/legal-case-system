from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.core.config import settings
from app.models.user import User
from app.modules.ai.models.ai_analysis import AIAnalysisResult
from app.modules.ai.models.ai_task import AITask
from app.modules.ai.models.falsification import FalsificationRecord
from app.modules.ai.schemas import FalsificationRecordRead, FalsificationRequest

if TYPE_CHECKING:
    from app.modules.ai.service import AIService


logger = logging.getLogger("app.ai")


def execute_falsification_task(
    service: AIService,
    *,
    task: AITask,
    analysis: AIAnalysisResult,
    payload: FalsificationRequest,
    current_user: User,
) -> None:
    try:
        service._mark_processing(task=task, message="正在执行证伪验证...", progress=35)

        records: list[FalsificationRecord] = []
        for iteration in range(1, payload.iteration_count + 1):
            for mode in payload.challenge_modes:
                if settings.AI_MOCK_MODE:
                    basis = sum(ord(char) for char in f"{analysis.id}:{mode}:{iteration}")
                    is_falsified = basis % 3 == 0
                    severity = derive_severity(mode=mode, is_falsified=is_falsified)
                    challenge_question = f"[{mode}] 第 {iteration} 轮质询：该结论是否存在事实或法律层面的漏洞？"
                    response = "发现可证伪点，需补强证据链。" if is_falsified else "未发现可明确证伪点。"
                    improvement = (
                        "建议补充证据来源、时间线和条款适用依据。"
                        if is_falsified
                        else "维持当前论证结构，持续监测新增证据。"
                    )
                    ai_model = "mock-legal-v1"
                else:
                    provider_reply = service.provider.generate_falsification(
                        case_title=analysis.case.title if analysis.case else "",
                        analysis_summary=str((analysis.result_data or {}).get("summary") or ""),
                        challenge_mode=mode,
                        iteration=iteration,
                    )
                    provider_payload = provider_reply.payload
                    is_falsified = bool(provider_payload.get("is_falsified", False))
                    severity = normalize_severity(
                        provider_payload.get("severity"),
                        fallback=derive_severity(mode=mode, is_falsified=is_falsified),
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

        service.repo.save_falsification_records(records)
        service.repo.flush()

        task.status = "completed"
        task.progress = 100
        task.result_id = records[0].id if records else None
        task.message = f"证伪验证完成，生成 {len(records)} 条记录。"
        task.completed_at = datetime.now(timezone.utc)
        task.heartbeat_at = task.completed_at
        task.next_retry_at = None
        service.repo.save(task)
        service._append_case_flow(
            case_id=analysis.case_id,
            tenant_id=analysis.tenant_id,
            action_type="analysis_completed",
            content=f"Falsification task {task.task_id} completed.",
            operator_id=current_user.id,
            visible_to="both",
        )
        service.repo.commit()
        service.repo.refresh(task)
        logger.info(
            "ai.falsify.completed task_id=%s case_id=%s records=%s request_id=%s",
            task.task_id,
            analysis.case_id,
            len(records),
            service.request_id,
        )
    except Exception as exc:  # noqa: BLE001
        service.repo.rollback()
        service._mark_failed(task_id=task.id, error_message=str(exc), fallback_message="证伪验证失败。")


def normalize_severity(value: object, *, fallback: str) -> str:
    severity = str(value or "").strip().lower()
    if severity in {"critical", "major", "minor"}:
        return severity
    return fallback


def derive_severity(*, mode: str, is_falsified: bool) -> str:
    if not is_falsified:
        return "minor"
    if mode == "evidence":
        return "critical"
    if mode == "logic":
        return "major"
    return "major"


def to_falsification_read(row: FalsificationRecord) -> FalsificationRecordRead:
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
