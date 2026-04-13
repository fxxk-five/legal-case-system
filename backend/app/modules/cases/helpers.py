from __future__ import annotations

from datetime import datetime, timezone

from fastapi import status

from app.core.errors import AppError, ErrorCode
from app.core.roles import can_manage_case_role, is_tenant_admin_role, normalize_role
from app.models.user import User
from app.modules.cases.flow import list_case_flows_for_viewer
from app.modules.cases.models.case import Case
from app.modules.cases.policy import ensure_personal_tenant_lawyer_case_visible
from app.modules.cases.repository import CasesRepository
from app.modules.cases.schemas import CaseLawyerRead, CaseRead, CaseTimelineItem


ALLOWED_STATUS_TRANSITIONS = {
    "new": ["processing", "closed"],
    "processing": ["done", "closed"],
    "done": ["closed"],
    "open": ["closed"],
    "closed": ["archived"],
    "archived": [],
}


def validate_status_transition(current_status: str, new_status: str) -> None:
    if new_status == current_status:
        return
    allowed = ALLOWED_STATUS_TRANSITIONS.get(current_status, [])
    if new_status not in allowed:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.VALIDATION_ERROR,
            message=f"不允许从 {current_status} 转换到 {new_status}。",
            detail=f"不允许从 {current_status} 转换到 {new_status}。",
        )


def build_case_timeline(db, case: Case, *, viewer_role: str) -> list[CaseTimelineItem]:
    flows = list_case_flows_for_viewer(
        db=db,
        tenant_id=case.tenant_id,
        case_id=case.id,
        viewer_role=viewer_role,
    )
    return [
        CaseTimelineItem(
            event_type=item.action_type,
            title=item.action_type.replace("_", " ").title(),
            description=item.content,
            occurred_at=item.created_at,
            operator_name=item.operator_name,
        )
        for item in flows
    ]


def get_case_or_404(db, *, case_id: int, current_user: User) -> Case:
    case = CasesRepository(db).get_case_detail(case_id=case_id, tenant_id=current_user.tenant_id)
    if case is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.CASE_NOT_FOUND,
            message="案件不存在。",
            detail="案件不存在。",
        )
    ensure_personal_tenant_lawyer_case_visible(
        db,
        current_user=current_user,
        case_id=case.id,
    )
    return case


def ensure_case_client_owner(*, case: Case, current_user: User) -> None:
    if normalize_role(current_user.role) != "client" or case.client_id != current_user.id:
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.CASE_ACCESS_DENIED,
            message="无权操作该案件。",
            detail="无权操作该案件。",
        )


def ensure_case_editor(*, case: Case, current_user: User) -> None:
    if not can_manage_case_role(current_user.role):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.CASE_OPERATION_NOT_ALLOWED,
            message="无权修改该案件。",
            detail="无权修改该案件。",
        )

    is_owner = case.assigned_lawyer_id == current_user.id
    is_admin = is_tenant_admin_role(current_user.role, is_tenant_admin=current_user.is_tenant_admin)
    if is_owner or is_admin:
        return

    raise AppError(
        status_code=status.HTTP_403_FORBIDDEN,
        code=ErrorCode.CASE_OPERATION_NOT_ALLOWED,
        message="无权修改该案件。",
        detail="无权修改该案件。",
    )


def append_client_remark(*, existing_remark: str | None, incoming_remark: str) -> str:
    incoming = incoming_remark.strip()
    if not incoming:
        return (existing_remark or "").strip()

    existing = (existing_remark or "").strip()
    if not existing:
        return incoming

    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    return f"{existing}\n\n[{timestamp}] {incoming}"


def serialize_case_for_viewer(*, db, case: Case, current_user: User) -> CaseRead | CaseLawyerRead:
    case.timeline = build_case_timeline(db, case, viewer_role=current_user.role)
    if normalize_role(current_user.role) == "client":
        return CaseRead.model_validate(case)
    return CaseLawyerRead.model_validate(case)
