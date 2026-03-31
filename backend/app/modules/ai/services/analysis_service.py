from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from app.core.config import settings
from app.models.user import User
from app.modules.ai.models.ai_analysis import AIAnalysisResult
from app.modules.ai.models.ai_task import AITask
from app.modules.ai.schemas import AnalysisRequest
from app.modules.ai.services.analysis_helpers import estimate_win_rate, normalize_str_list, normalize_win_rate
from app.modules.cases.models.case import Case
from app.modules.cases.models.case_fact import CaseFact

if TYPE_CHECKING:
    from app.modules.ai.service import AIService


logger = logging.getLogger("app.ai")


def execute_analysis_task(
    service: AIService,
    *,
    task: AITask,
    case: Case,
    payload: AnalysisRequest,
    current_user: User,
) -> None:
    try:
        service._mark_processing(
            task=task,
            message="正在收集案件事实...",
            progress=20,
            stage="collecting_facts",
        )

        _, case_facts = service.repo.list_case_facts(
            case_id=case.id,
            tenant_id=case.tenant_id,
            fact_type=None,
            min_confidence=None,
            page=1,
            page_size=500,
        )
        fact_texts = [item.content for item in case_facts]
        case_context = service._build_case_context(case=case)
        service._mark_processing(
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
                summary = build_analysis_summary(
                    service,
                    case=case,
                    analysis_type=analysis_type,
                    fact_texts=fact_texts,
                    focus_areas=payload.focus_areas,
                    case_context=case_context,
                )
                win_rate = estimate_win_rate(case_facts_count=len(case_facts), offset=index)
                strengths = build_strengths(case_facts)
                weaknesses = build_weaknesses(case_facts)
                recommendations = build_recommendations(
                    payload.focus_areas,
                    case_context=case_context,
                )
                applicable_laws = ["中华人民共和国民法典 第1165条"]
                related_cases = ["(2024)京01民终1234号"]
                ai_model = "mock-legal-v1"
                token_usage = max(600, 300 + len(fact_texts) * 120)
            else:
                provider_reply = service.provider.generate_analysis(
                    case_title=case.title,
                    analysis_type=analysis_type,
                    fact_texts=fact_texts,
                    focus_areas=payload.focus_areas,
                    include_precedents=payload.include_precedents,
                    case_context=case_context,
                    model_override=model_override,
                )
                summary = str(provider_reply.payload.get("summary") or "").strip()
                if not summary:
                    summary = build_analysis_summary(
                        service,
                        case=case,
                        analysis_type=analysis_type,
                        fact_texts=fact_texts,
                        focus_areas=payload.focus_areas,
                        case_context=case_context,
                    )
                win_rate = normalize_win_rate(
                    provider_reply.payload.get("win_rate"),
                    default=estimate_win_rate(case_facts_count=len(case_facts), offset=index),
                )
                strengths = normalize_str_list(
                    provider_reply.payload.get("strengths"),
                    fallback=build_strengths(case_facts),
                )
                weaknesses = normalize_str_list(
                    provider_reply.payload.get("weaknesses"),
                    fallback=build_weaknesses(case_facts),
                )
                recommendations = normalize_str_list(
                    provider_reply.payload.get("recommendations"),
                    fallback=build_recommendations(
                        payload.focus_areas,
                        case_context=case_context,
                    ),
                )
                applicable_laws = normalize_str_list(
                    provider_reply.payload.get("applicable_laws"),
                    fallback=["中华人民共和国民法典 第1165条"],
                )
                related_cases = normalize_str_list(
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
                    "case_context_used": {
                        "has_client_remark": bool(case_context.get("has_client_remark")),
                        "has_lawyer_remark": bool(case_context.get("has_lawyer_remark")),
                    },
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

        service.repo.save_analysis_results(rows)
        service.repo.flush()
        service._mark_processing(
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
        service.repo.save(task)
        case.analysis_status = "completed"
        case.analysis_progress = 100
        service.repo.save(case)
        service._append_case_flow(
            case_id=case.id,
            tenant_id=case.tenant_id,
            action_type="analysis_completed",
            content=f"Analyze task {task.task_id} completed.",
            operator_id=current_user.id,
            visible_to="both",
        )
        service._append_case_flow(
            case_id=case.id,
            tenant_id=case.tenant_id,
            action_type="analysis_progress_updated",
            content=f"Analyze task {task.task_id}: completed (100%).",
            operator_id=current_user.id,
            visible_to="both",
        )
        service.repo.commit()
        service.repo.refresh(task)
        logger.info(
            "ai.analysis.completed task_id=%s case_id=%s results=%s request_id=%s",
            task.task_id,
            case.id,
            len(rows),
            service.request_id,
        )
    except Exception as exc:  # noqa: BLE001
        service.repo.rollback()
        service._mark_failed(task_id=task.id, error_message=str(exc), fallback_message="法律分析失败。")


def build_analysis_summary(
    service: AIService,
    *,
    case: Case,
    analysis_type: str,
    fact_texts: list[str],
    focus_areas: list[str],
    case_context: dict[str, object] | None = None,
) -> str:
    focus = "、".join(focus_areas) if focus_areas else "证据链完整性与法律适用"
    facts_hint = f"已纳入 {len(fact_texts)} 条案件事实" if fact_texts else "当前事实较少，建议先补充材料"
    remark_notes = service._build_case_context_notes(case_context)
    remark_suffix = f" 已纳入备注上下文：{'；'.join(remark_notes)}。" if remark_notes else ""
    return f"[{analysis_type}] {case.title}：{facts_hint}，重点关注 {focus}。{remark_suffix}"


def build_strengths(facts: list[CaseFact]) -> list[str]:
    if not facts:
        return ["已建立基础案件信息，可继续补充关键证据。"]
    return [
        "证据与时间线已形成初步闭环。",
        "关键事实具备来源标记，便于后续举证。",
    ]


def build_weaknesses(facts: list[CaseFact]) -> list[str]:
    if len(facts) < 3:
        return ["事实样本偏少，建议继续上传关联材料。"]
    return [
        "部分事实仍依赖单一来源，抗辩稳定性一般。",
        "损失量化依据需要进一步补强。",
    ]


def build_recommendations(
    focus_areas: list[str],
    *,
    case_context: dict[str, object] | None = None,
) -> list[str]:
    suggestions = [
        "补充证据目录与时间线对应关系表。",
        "针对争议焦点准备两套备选论证路径。",
        "在开庭前完成证据合法性与关联性复核。",
    ]
    if case_context and case_context.get("has_client_remark"):
        suggestions.insert(0, "结合当事人补充说明，逐项核对材料背景、关键时间点与诉求表述。")
    if case_context and case_context.get("has_lawyer_remark"):
        suggestions.insert(0, "优先围绕律师内部备注中的争议焦点组织补证与论证。")
    if focus_areas:
        suggestions.insert(0, f"围绕重点关注项（{'、'.join(focus_areas)}）补充专项材料。")
    return suggestions[:4]
