from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.core.config import settings
from app.integrations.llm.service import ProviderReply
from app.models.user import User
from app.modules.ai.models.ai_task import AITask
from app.modules.ai.schemas import CaseFactRead
from app.modules.cases.models.case import Case
from app.modules.cases.models.case_fact import CaseFact
from app.modules.files.models.file import File

if TYPE_CHECKING:
    from app.modules.ai.service import AIService


logger = logging.getLogger("app.ai")


def execute_parse_task(
    service: AIService,
    *,
    task: AITask,
    case: Case,
    file_record: File,
    parse_options: dict,
    current_user: User,
) -> None:
    try:
        service._mark_processing(task=task, message="正在解析文档...", progress=20)
        service.repo.delete_case_facts_for_file(
            case_id=case.id,
            tenant_id=case.tenant_id,
            file_id=file_record.id,
        )
        case_context = service._build_case_context(case=case)

        if settings.AI_MOCK_MODE:
            facts = build_parse_facts(
                service,
                case=case,
                file_record=file_record,
                parse_options=parse_options,
                created_by=current_user.id,
            )
        else:
            provider_reply = service.provider.generate_parse_facts(
                case_number=case.case_number,
                case_title=case.title,
                file_name=file_record.file_name,
                file_type=file_record.file_type,
                parse_options=parse_options,
                case_context=case_context,
            )
            facts = build_parse_facts_from_provider(
                service,
                case=case,
                file_record=file_record,
                created_by=current_user.id,
                provider_reply=provider_reply,
                fallback_parse_options=parse_options,
            )
        service.repo.save_case_facts(facts)
        service.repo.flush()

        task.status = "completed"
        task.progress = 100
        task.result_id = facts[0].id if facts else None
        task.message = f"文档解析完成，共提取 {len(facts)} 条事实。"
        task.completed_at = datetime.now(timezone.utc)
        task.heartbeat_at = task.completed_at
        task.next_retry_at = None
        service.repo.save(task)
        service._append_case_flow(
            case_id=case.id,
            tenant_id=case.tenant_id,
            action_type="analysis_completed",
            content=f"Parse task {task.task_id} completed.",
            operator_id=current_user.id,
            visible_to="both",
        )
        service.repo.commit()
        service.repo.refresh(task)
        logger.info(
            "ai.parse.completed task_id=%s case_id=%s facts=%s request_id=%s",
            task.task_id,
            case.id,
            len(facts),
            service.request_id,
        )
    except Exception as exc:  # noqa: BLE001
        service.repo.rollback()
        service._mark_failed(task_id=task.id, error_message=str(exc), fallback_message="文档解析失败。")


def build_parse_facts(
    service: AIService,
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
                content=service._mask_sensitive(f"案件当事人已绑定，案件标题：{case.title}"),
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


def build_parse_facts_from_provider(
    service: AIService,
    *,
    case: Case,
    file_record: File,
    created_by: int,
    provider_reply: ProviderReply,
    fallback_parse_options: dict,
) -> list[CaseFact]:
    facts_payload = provider_reply.payload.get("facts")
    if not isinstance(facts_payload, list) or not facts_payload:
        return build_parse_facts(
            service,
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
        confidence = service._normalize_win_rate(item.get("confidence"), default=0.8)
        metadata = item.get("metadata")
        metadata_value = metadata if isinstance(metadata, dict) else {}

        facts.append(
            CaseFact(
                tenant_id=case.tenant_id,
                case_id=case.id,
                file_id=file_record.id,
                fact_type=fact_type,
                content=service._mask_sensitive(content),
                source_page=source_page_value,
                confidence=confidence,
                fact_metadata=metadata_value,
                created_by=created_by,
            )
        )

    if not facts:
        return build_parse_facts(
            service,
            case=case,
            file_record=file_record,
            parse_options=fallback_parse_options,
            created_by=created_by,
        )
    return facts


def to_case_fact_read(fact: CaseFact) -> CaseFactRead:
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
