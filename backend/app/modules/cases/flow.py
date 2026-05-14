from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.roles import normalize_role
from app.modules.cases.models.case_flow import CaseFlow
from app.modules.cases.repository import CasesRepository
from app.models.user import User

_ALLOWED_VISIBLE_TO = {"lawyer", "client", "both"}


def create_case_flow(
    *,
    db: Session,
    tenant_id: int,
    case_id: int,
    action_type: str,
    content: str,
    operator: User | None = None,
    visible_to: str = "both",
) -> CaseFlow:
    visibility = (visible_to or "both").strip().lower()
    if visibility not in _ALLOWED_VISIBLE_TO:
        visibility = "both"

    return CasesRepository(db).add_case_flow(
        tenant_id=tenant_id,
        case_id=case_id,
        action_type=action_type,
        content=content,
        operator_id=operator.id if operator is not None else None,
        operator_name=operator.real_name if operator is not None else None,
        visible_to=visibility,
    )


def list_case_flows_for_viewer(
    *,
    db: Session,
    tenant_id: int,
    case_id: int,
    viewer_role: str,
) -> list[CaseFlow]:
    role = normalize_role(viewer_role)
    visible_values = {"client", "both"} if role == "client" else {"lawyer", "both"}

    return CasesRepository(db).list_case_flows_for_viewer(
        tenant_id=tenant_id,
        case_id=case_id,
        visible_values=visible_values,
    )
