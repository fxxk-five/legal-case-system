from __future__ import annotations

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.roles import normalize_role
from app.models.case_flow import CaseFlow
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

    flow = CaseFlow(
        tenant_id=tenant_id,
        case_id=case_id,
        operator_id=operator.id if operator is not None else None,
        operator_name=operator.real_name if operator is not None else None,
        action_type=action_type,
        content=content,
        visible_to=visibility,
    )
    db.add(flow)
    return flow


def list_case_flows_for_viewer(
    *,
    db: Session,
    tenant_id: int,
    case_id: int,
    viewer_role: str,
) -> list[CaseFlow]:
    role = normalize_role(viewer_role)
    visible_values = {"client", "both"} if role == "client" else {"lawyer", "both"}

    return (
        db.query(CaseFlow)
        .filter(
            CaseFlow.tenant_id == tenant_id,
            CaseFlow.case_id == case_id,
            CaseFlow.visible_to.in_(visible_values),
        )
        .order_by(desc(CaseFlow.created_at), desc(CaseFlow.id))
        .all()
    )

