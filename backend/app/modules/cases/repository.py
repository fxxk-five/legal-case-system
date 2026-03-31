from __future__ import annotations

from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Query, Session, joinedload

from app.core.legal_types import normalize_legal_type
from app.core.roles import normalize_role, role_values_for_query
from app.models.tenant import Tenant
from app.models.user import User
from app.modules.ai.models.ai_analysis import AIAnalysisResult
from app.modules.cases.models.case import Case
from app.modules.cases.models.case_flow import CaseFlow
from app.modules.cases.models.case_number_sequence import CaseNumberSequence
from app.modules.files.models.file import File


class CasesRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_case_detail(self, *, case_id: int, tenant_id: int) -> Case | None:
        return (
            self.db.query(Case)
            .options(joinedload(Case.client), joinedload(Case.assigned_lawyer))
            .filter(
                Case.id == case_id,
                Case.tenant_id == tenant_id,
            )
            .first()
        )

    def case_number_exists(self, *, tenant_id: int, case_number: str) -> bool:
        return (
            self.db.query(Case.id)
            .filter(
                Case.tenant_id == tenant_id,
                Case.case_number == case_number,
            )
            .first()
            is not None
        )

    def find_client_by_phone(self, *, tenant_id: int, phone: str) -> User | None:
        return (
            self.db.query(User)
            .filter(
                User.tenant_id == tenant_id,
                User.phone == phone,
            )
            .first()
        )

    def get_tenant(self, *, tenant_id: int) -> Tenant | None:
        return self.db.query(Tenant).filter(Tenant.id == tenant_id).first()

    def is_personal_tenant_lawyer(self, *, current_user: User) -> bool:
        if normalize_role(current_user.role) != "lawyer":
            return False
        tenant = self.get_tenant(tenant_id=current_user.tenant_id)
        return tenant is not None and tenant.type == "personal"

    def apply_visible_case_scope(self, query: Query, *, current_user: User) -> Query:
        role = normalize_role(current_user.role)
        if role == "client":
            return query.filter(Case.client_id == current_user.id)
        if not self.is_personal_tenant_lawyer(current_user=current_user):
            return query

        uploaded_case_ids = (
            self.db.query(File.case_id)
            .filter(
                File.tenant_id == current_user.tenant_id,
                File.uploader_id == current_user.id,
            )
            .distinct()
        )
        return query.filter(Case.id.in_(uploaded_case_ids))

    def build_visible_case_query(self, *, current_user: User) -> Query:
        query = self.db.query(Case).filter(Case.tenant_id == current_user.tenant_id)
        return self.apply_visible_case_scope(query, current_user=current_user)

    def user_has_uploaded_file_for_case(
        self,
        *,
        tenant_id: int,
        case_id: int,
        uploader_id: int,
    ) -> bool:
        return (
            self.db.query(File.id)
            .filter(
                File.tenant_id == tenant_id,
                File.case_id == case_id,
                File.uploader_id == uploader_id,
            )
            .first()
            is not None
        )

    def find_assignable_lawyer(self, *, tenant_id: int, user_id: int) -> User | None:
        return (
            self.db.query(User)
            .filter(
                User.id == user_id,
                User.tenant_id == tenant_id,
                User.role.in_(role_values_for_query("lawyer", "tenant_admin")),
            )
            .first()
        )

    def list_visible_cases(
        self,
        *,
        current_user: User,
        status_filter: str | None,
        legal_type: str | None,
        keyword: str,
        sort_by: str,
        sort_order: str,
        skip: int,
        limit: int,
    ) -> tuple[int, list[Case]]:
        query = self.build_visible_case_query(current_user=current_user).options(joinedload(Case.client))

        if status_filter:
            query = query.filter(Case.status == status_filter)
        if legal_type:
            query = query.filter(Case.legal_type == normalize_legal_type(legal_type))

        normalized_keyword = keyword.strip()
        if normalized_keyword:
            like_kw = f"%{normalized_keyword}%"
            query = query.filter(
                or_(
                    Case.case_number.ilike(like_kw),
                    Case.title.ilike(like_kw),
                    Case.client.has(User.real_name.ilike(like_kw)),
                )
            )

        sort_column = {
            "created_at": Case.created_at,
            "updated_at": Case.updated_at,
            "deadline": Case.deadline,
            "legal_type": Case.legal_type,
        }[sort_by]
        order_by_clause = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        query = query.order_by(order_by_clause, desc(Case.id))

        total_count = query.count()
        items = query.offset(skip).limit(limit).all()
        return total_count, items

    def add_case_flow(
        self,
        *,
        tenant_id: int,
        case_id: int,
        action_type: str,
        content: str,
        operator_id: int | None,
        operator_name: str | None,
        visible_to: str,
    ) -> CaseFlow:
        flow = CaseFlow(
            tenant_id=tenant_id,
            case_id=case_id,
            operator_id=operator_id,
            operator_name=operator_name,
            action_type=action_type,
            content=content,
            visible_to=visible_to,
        )
        self.db.add(flow)
        return flow

    def save(self, instance: object) -> None:
        self.db.add(instance)

    def flush(self) -> None:
        self.db.flush()

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, instance: object) -> None:
        self.db.refresh(instance)

    def save_and_flush(self, instance: object) -> None:
        self.save(instance)
        self.flush()

    def save_commit_refresh(self, instance: object) -> None:
        self.save(instance)
        self.commit()
        self.refresh(instance)

    def commit_and_refresh(self, instance: object) -> None:
        self.commit()
        self.refresh(instance)

    def list_case_flows_for_viewer(
        self,
        *,
        tenant_id: int,
        case_id: int,
        visible_values: set[str],
    ) -> list[CaseFlow]:
        return (
            self.db.query(CaseFlow)
            .filter(
                CaseFlow.tenant_id == tenant_id,
                CaseFlow.case_id == case_id,
                CaseFlow.visible_to.in_(visible_values),
            )
            .order_by(desc(CaseFlow.created_at), desc(CaseFlow.id))
            .all()
        )

    def get_case_number_sequence_for_update(
        self,
        *,
        tenant_id: int,
        year: int,
    ) -> CaseNumberSequence | None:
        return (
            self.db.query(CaseNumberSequence)
            .filter(
                CaseNumberSequence.tenant_id == tenant_id,
                CaseNumberSequence.year == year,
            )
            .with_for_update()
            .first()
        )

    def create_case_number_sequence(
        self,
        *,
        tenant_id: int,
        year: int,
        next_value: int = 1,
    ) -> CaseNumberSequence:
        sequence = CaseNumberSequence(
            tenant_id=tenant_id,
            year=year,
            next_value=next_value,
        )
        self.db.add(sequence)
        self.db.flush()
        return sequence

    def save_case_number_sequence(self, sequence: CaseNumberSequence) -> None:
        self.db.add(sequence)
        self.db.flush()

    def list_report_analysis_results(
        self,
        *,
        case_id: int,
        tenant_id: int,
        limit: int = 20,
    ) -> list[AIAnalysisResult]:
        return (
            self.db.query(AIAnalysisResult)
            .filter(
                AIAnalysisResult.case_id == case_id,
                AIAnalysisResult.tenant_id == tenant_id,
            )
            .order_by(AIAnalysisResult.created_at.desc(), AIAnalysisResult.id.desc())
            .limit(limit)
            .all()
        )
