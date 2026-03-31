from __future__ import annotations

from typing import TYPE_CHECKING

from app.modules.cases.flow import create_case_flow

if TYPE_CHECKING:
    from app.modules.ai.service import AIService


def sync_case_analysis_state(
    service: AIService,
    *,
    case_id: int,
    tenant_id: int,
    operator_id: int | None,
    status_value: str,
    progress: int,
    flow_content: str,
) -> None:
    case = service.repo.get_case(case_id=case_id, tenant_id=tenant_id)
    if case is None:
        return

    case.analysis_status = status_value
    case.analysis_progress = max(0, min(100, int(progress)))
    service.repo.save(case)
    append_case_flow(
        service,
        case_id=case_id,
        tenant_id=tenant_id,
        action_type="analysis_progress_updated",
        content=flow_content,
        operator_id=operator_id,
        visible_to="both",
    )


def append_case_flow(
    service: AIService,
    *,
    case_id: int,
    tenant_id: int,
    action_type: str,
    content: str,
    operator_id: int | None,
    visible_to: str,
) -> None:
    case_exists = service.repo.get_case(case_id=case_id, tenant_id=tenant_id)
    if case_exists is None:
        return

    operator = None
    if operator_id is not None:
        operator = service.repo.get_user(user_id=operator_id, tenant_id=tenant_id)

    create_case_flow(
        db=service.db,
        tenant_id=tenant_id,
        case_id=case_id,
        action_type=action_type,
        content=content,
        operator=operator,
        visible_to=visible_to,
    )
