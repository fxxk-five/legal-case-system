from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Query, Session

from app.core.roles import role_values_for_query
from app.modules.ai.models.ai_analysis import AIAnalysisResult
from app.modules.ai.models.ai_task import AITask
from app.modules.cases.models.case import Case
from app.modules.cases.policy import build_visible_case_query
from app.modules.files.models.file import File
from app.models.tenant import Tenant
from app.models.user import User


class AnalyticsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_tenant(self, *, tenant_id: int) -> Tenant | None:
        return self.db.query(Tenant).filter(Tenant.id == tenant_id).first()

    def list_tenant_tasks(self, *, tenant_id: int) -> list[AITask]:
        return (
            self.db.query(AITask)
            .filter(AITask.tenant_id == tenant_id)
            .order_by(AITask.created_at.desc())
            .all()
        )

    def list_tenant_results(self, *, tenant_id: int) -> list[AIAnalysisResult]:
        return (
            self.db.query(AIAnalysisResult)
            .filter(AIAnalysisResult.tenant_id == tenant_id)
            .order_by(AIAnalysisResult.created_at.desc())
            .all()
        )

    def build_visible_cases_query(self, *, current_user: User) -> Query:
        return build_visible_case_query(self.db, current_user)

    def build_visible_files_query(self, *, current_user: User, visible_cases: Query) -> Query:
        visible_case_ids = select(visible_cases.with_entities(Case.id).subquery().c.id)
        query = self.db.query(File).filter(
            File.tenant_id == current_user.tenant_id,
            File.case_id.in_(visible_case_ids),
        )
        if current_user.role == "client":
            query = query.filter(File.uploader_id == current_user.id)
        return query

    def count_distinct_file_cases_since(
        self,
        *,
        tenant_id: int,
        visible_case_ids: Select,
        baseline: datetime,
    ) -> int:
        return (
            self.db.query(File.case_id)
            .filter(
                File.tenant_id == tenant_id,
                File.case_id.in_(visible_case_ids),
                File.created_at > baseline,
            )
            .distinct()
            .count()
        )

    def count_tenant_lawyers(self, *, tenant_id: int) -> int:
        return (
            self.db.query(User)
            .filter(
                User.tenant_id == tenant_id,
                User.role.in_(role_values_for_query("lawyer", "tenant_admin")),
            )
            .count()
        )

    def count_tenant_clients(self, *, tenant_id: int) -> int:
        return self.db.query(User).filter(User.tenant_id == tenant_id, User.role == "client").count()

    def count_pending_members(
        self,
        *,
        tenant_id: int,
        baseline: datetime | None = None,
    ) -> int:
        query = self.db.query(User).filter(
            User.tenant_id == tenant_id,
            User.role.in_(role_values_for_query("lawyer", "tenant_admin")),
            User.status == 0,
        )
        if baseline is not None:
            query = query.filter(User.created_at > baseline)
        return query.count()

    def save(self, instance: object) -> None:
        self.db.add(instance)

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, instance: object) -> None:
        self.db.refresh(instance)

    def commit_and_refresh(self, instance: object) -> None:
        self.commit()
        self.refresh(instance)
