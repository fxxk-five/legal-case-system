from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Query

from app.core.roles import is_tenant_admin_role
from app.modules.analytics.repository import AnalyticsRepository
from app.modules.cases.models.case import Case
from app.modules.files.models.file import File
from app.models.user import User


class AnalyticsDashboardService:
    def __init__(self, repository: AnalyticsRepository) -> None:
        self.repository = repository

    def _count_dashboard_deltas(
        self,
        *,
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

        delta_pending_member_count = 0
        if is_tenant_admin_role(current_user.role, is_tenant_admin=current_user.is_tenant_admin):
            delta_pending_member_count = self.repository.count_pending_members(
                tenant_id=current_user.tenant_id,
                baseline=baseline,
            )

        return {
            "has_login_baseline": True,
            "delta_since": baseline.isoformat(),
            "delta_case_count": visible_cases.filter(Case.created_at > baseline).count(),
            "delta_file_count": visible_files.filter(File.created_at > baseline).count(),
            "delta_file_case_count": self.repository.count_distinct_file_cases_since(
                tenant_id=current_user.tenant_id,
                visible_case_ids=visible_case_ids,
                baseline=baseline,
            ),
            "delta_deadline_risk_count": visible_cases.filter(
                Case.status != "done",
                Case.deadline.is_not(None),
                Case.deadline > now,
                Case.deadline <= risk_deadline,
                Case.updated_at > baseline,
            ).count(),
            "delta_pending_member_count": delta_pending_member_count,
        }

    def get_dashboard_stats(self, *, current_user: User) -> dict[str, object]:
        tenant_id = current_user.tenant_id
        lawyer_count = self.repository.count_tenant_lawyers(tenant_id=tenant_id)
        client_total = self.repository.count_tenant_clients(tenant_id=tenant_id)

        visible_cases = self.repository.build_visible_cases_query(current_user=current_user)
        visible_files = self.repository.build_visible_files_query(
            current_user=current_user,
            visible_cases=visible_cases,
        )

        pending_member_count: int | None = None
        if is_tenant_admin_role(current_user.role, is_tenant_admin=current_user.is_tenant_admin):
            pending_member_count = self.repository.count_pending_members(tenant_id=tenant_id)

        payload: dict[str, object] = {
            "lawyer_count": lawyer_count,
            "client_total": client_total,
            "case_count": visible_cases.count(),
            "pending_lawyer_count": pending_member_count or 0,
            "case_total": visible_cases.count(),
            "case_in_progress": visible_cases.filter(Case.status != "done").count(),
            "case_closed": visible_cases.filter(Case.status == "done").count(),
            "pending_member_count": pending_member_count,
            "can_view_pending_members": pending_member_count is not None,
        }
        payload.update(
            self._count_dashboard_deltas(
                current_user=current_user,
                visible_cases=visible_cases,
                visible_files=visible_files,
            )
        )
        return payload
