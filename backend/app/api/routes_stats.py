from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Query, Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.case import Case
from app.models.file import File
from app.models.user import User
from app.services.case_visibility import build_visible_case_query


router = APIRouter(prefix="/stats", tags=["Stats"])


def _build_visible_case_query(db: Session, current_user: User) -> Query:
    return build_visible_case_query(db, current_user)


def _build_visible_file_query(db: Session, current_user: User, visible_cases: Query) -> Query:
    visible_case_ids = select(visible_cases.with_entities(Case.id).subquery().c.id)
    query = db.query(File).filter(File.tenant_id == current_user.tenant_id, File.case_id.in_(visible_case_ids))
    if current_user.role == "client":
        query = query.filter(File.uploader_id == current_user.id)
    return query


def _count_dashboard_deltas(
    db: Session,
    current_user: User,
    visible_cases: Query,
    visible_files: Query,
) -> dict[str, int | str | bool | None]:
    baseline = current_user.previous_login_at
    if baseline is None:
        return {
            "has_login_baseline": False,
            "delta_since": None,
            "delta_case_count": 0,
            "delta_file_count": 0,
            "delta_file_case_count": 0,
            "delta_deadline_risk_count": 0,
            "delta_pending_member_count": 0,
        }

    now = datetime.now(timezone.utc)
    risk_deadline = now + timedelta(days=30)
    visible_case_ids = select(visible_cases.with_entities(Case.id).subquery().c.id)

    delta_case_count = visible_cases.filter(Case.created_at > baseline).count()
    delta_file_count = visible_files.filter(File.created_at > baseline).count()
    delta_file_case_count = (
        db.query(File.case_id)
        .filter(
            File.tenant_id == current_user.tenant_id,
            File.case_id.in_(visible_case_ids),
            File.created_at > baseline,
        )
        .distinct()
        .count()
    )
    delta_deadline_risk_count = (
        visible_cases.filter(
            Case.status != "done",
            Case.deadline.is_not(None),
            Case.deadline > now,
            Case.deadline <= risk_deadline,
            Case.updated_at > baseline,
        ).count()
    )

    delta_pending_member_count = 0
    if current_user.is_tenant_admin or current_user.role == "tenant_admin":
        delta_pending_member_count = (
            db.query(User)
            .filter(
                User.tenant_id == current_user.tenant_id,
                User.role.in_(["lawyer", "tenant_admin"]),
                User.status == 0,
                User.created_at > baseline,
            )
            .count()
        )

    return {
        "has_login_baseline": True,
        "delta_since": baseline.isoformat(),
        "delta_case_count": delta_case_count,
        "delta_file_count": delta_file_count,
        "delta_file_case_count": delta_file_case_count,
        "delta_deadline_risk_count": delta_deadline_risk_count,
        "delta_pending_member_count": delta_pending_member_count,
    }


@router.get("/dashboard")
def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    tenant_id = current_user.tenant_id

    lawyer_count = (
        db.query(User)
        .filter(User.tenant_id == tenant_id, User.role.in_(["lawyer", "tenant_admin"]))
        .count()
    )
    client_total = (
        db.query(User)
        .filter(User.tenant_id == tenant_id, User.role == "client")
        .count()
    )

    visible_cases = _build_visible_case_query(db, current_user)
    visible_files = _build_visible_file_query(db, current_user, visible_cases)

    case_total = visible_cases.count()
    case_in_progress = visible_cases.filter(Case.status != "done").count()
    case_closed = visible_cases.filter(Case.status == "done").count()

    pending_member_count: int | None = None
    if current_user.is_tenant_admin or current_user.role == "tenant_admin":
        pending_member_count = (
            db.query(User)
            .filter(
                User.tenant_id == tenant_id,
                User.role.in_(["lawyer", "tenant_admin"]),
                User.status == 0,
            )
            .count()
        )

    payload: dict[str, object] = {
        "lawyer_count": lawyer_count,
        "client_total": client_total,
        "case_count": case_total,
        "pending_lawyer_count": pending_member_count or 0,
        "case_total": case_total,
        "case_in_progress": case_in_progress,
        "case_closed": case_closed,
        "pending_member_count": pending_member_count,
        "can_view_pending_members": pending_member_count is not None,
    }
    payload.update(_count_dashboard_deltas(db, current_user, visible_cases, visible_files))
    return payload
