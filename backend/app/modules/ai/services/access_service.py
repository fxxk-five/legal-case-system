from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import status

from app.core.errors import AppError, ErrorCode
from app.core.roles import normalize_role
from app.models.user import User
from app.modules.cases.models.case import Case
from app.modules.cases.policy import ensure_personal_tenant_lawyer_case_visible

if TYPE_CHECKING:
    from app.modules.ai.service import AIService


def get_case_or_raise(service: AIService, *, case_id: int, current_user: User) -> Case:
    case = service.repo.get_case(case_id=case_id, tenant_id=current_user.tenant_id)
    if case is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.CASE_NOT_FOUND,
            message="案件不存在。",
            detail="案件不存在。",
        )
    ensure_personal_tenant_lawyer_case_visible(
        service.db,
        current_user=current_user,
        case_id=case.id,
    )

    if normalize_role(current_user.role) == "client" and case.client_id != current_user.id:
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.CASE_ACCESS_DENIED,
            message="无权访问该案件。",
            detail="无权访问该案件。",
        )
    return case


def ensure_role_for_action(service: AIService, *, current_user: User, action: str) -> None:
    viewer_role = normalize_role(current_user.role)
    if action in {"parse", "analyze", "falsify", "retry"} and viewer_role not in {
        "lawyer",
        "tenant_admin",
    }:
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.AI_OPERATION_NOT_ALLOWED,
            message="当前角色无权执行该AI操作。",
            detail="当前角色无权执行该AI操作。",
        )

    if action == "view_falsification" and viewer_role == "client":
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.AI_OPERATION_NOT_ALLOWED,
            message="当前角色无权查看证伪结果。",
            detail="当前角色无权查看证伪结果。",
        )
