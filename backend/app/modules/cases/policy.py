from __future__ import annotations

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Query, Session

from app.core.errors import AppError, ErrorCode
from app.core.roles import normalize_role
from app.models.case import Case
from app.models.file import File
from app.models.tenant import Tenant
from app.models.user import User


def is_personal_tenant_lawyer(db: Session, current_user: User) -> bool:
    if normalize_role(current_user.role) != "lawyer":
        return False
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    return tenant is not None and tenant.type == "personal"


def apply_visible_case_scope(query: Query, *, db: Session, current_user: User) -> Query:
    role = normalize_role(current_user.role)
    if role == "client":
        return query.filter(Case.client_id == current_user.id)
    if not is_personal_tenant_lawyer(db, current_user):
        return query

    uploaded_case_ids = select(
        db.query(File.case_id)
        .filter(File.tenant_id == current_user.tenant_id, File.uploader_id == current_user.id)
        .distinct()
        .subquery()
        .c.case_id
    )
    return query.filter(Case.id.in_(uploaded_case_ids))


def build_visible_case_query(db: Session, current_user: User) -> Query:
    query = db.query(Case).filter(Case.tenant_id == current_user.tenant_id)
    return apply_visible_case_scope(query, db=db, current_user=current_user)


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
    if not is_personal_tenant_lawyer(db, current_user):
        return

    visible = (
        db.query(File.id)
        .filter(
            File.tenant_id == current_user.tenant_id,
            File.case_id == case_id,
            File.uploader_id == current_user.id,
        )
        .first()
    )
    if visible is not None:
        return

    raise AppError(
        status_code=status_code,
        code=code,
        message=message,
        detail=detail,
    )
