from __future__ import annotations

from fastapi import status
from sqlalchemy.orm import Query, Session

from app.core.errors import AppError, ErrorCode
from app.models.user import User
from app.modules.cases.repository import CasesRepository


def is_personal_tenant_lawyer(db: Session, current_user: User) -> bool:
    return CasesRepository(db).is_personal_tenant_lawyer(current_user=current_user)


def apply_visible_case_scope(query: Query, *, db: Session, current_user: User) -> Query:
    return CasesRepository(db).apply_visible_case_scope(query, current_user=current_user)


def build_visible_case_query(db: Session, current_user: User) -> Query:
    return CasesRepository(db).build_visible_case_query(current_user=current_user)


def ensure_personal_tenant_lawyer_case_visible(
    db: Session,
    *,
    current_user: User,
    case_id: int,
    status_code: int = status.HTTP_404_NOT_FOUND,
    code: ErrorCode = ErrorCode.CASE_NOT_FOUND,
    message: str = "Case not found.",
    detail: str = "Case not found.",
) -> None:
    repo = CasesRepository(db)
    if not repo.is_personal_tenant_lawyer(current_user=current_user):
        return

    if repo.user_has_uploaded_file_for_case(
        tenant_id=current_user.tenant_id,
        case_id=case_id,
        uploader_id=current_user.id,
    ):
        return

    raise AppError(
        status_code=status_code,
        code=code,
        message=message,
        detail=detail,
    )
