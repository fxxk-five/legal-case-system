from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal

from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session

from app.models.user import User

from app.models.ai_analysis import AIAnalysisResult
from app.models.ai_task import AITask
from app.models.case import Case
from app.models.case_fact import CaseFact
from app.models.falsification import FalsificationRecord
from app.models.file import File


class AIRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_case(self, *, case_id: int, tenant_id: int) -> Case | None:
        return (
            self.db.query(Case)
            .filter(Case.id == case_id, Case.tenant_id == tenant_id)
            .first()
        )

    def get_file(self, *, file_id: int, case_id: int, tenant_id: int) -> File | None:
        return (
            self.db.query(File)
            .filter(
                File.id == file_id,
                File.case_id == case_id,
                File.tenant_id == tenant_id,
            )
            .first()
        )

    def get_analysis_result(
        self,
        *,
        analysis_id: int,
        case_id: int,
        tenant_id: int,
    ) -> AIAnalysisResult | None:
        return (
            self.db.query(AIAnalysisResult)
            .filter(
                AIAnalysisResult.id == analysis_id,
                AIAnalysisResult.case_id == case_id,
                AIAnalysisResult.tenant_id == tenant_id,
            )
            .first()
        )

    def create_task(
        self,
        *,
        task_id: str,
        tenant_id: int,
        case_id: int,
        task_type: str,
        created_by: int,
        input_params: dict,
        request_id: str | None,
        idempotency_key: str | None,
    ) -> AITask:
        task = AITask(
            task_id=task_id,
            tenant_id=tenant_id,
            case_id=case_id,
            task_type=task_type,
            status="queued",
            progress=0,
            message="Task queued.",
            input_params=input_params,
            created_by=created_by,
            request_id=request_id,
            idempotency_key=idempotency_key,
            retry_count=0,
            next_retry_at=None,
            claimed_at=None,
            heartbeat_at=None,
            worker_id=None,
        )
        self.db.add(task)
        self.db.flush()
        return task

    def get_task_by_idempotency_key(
        self,
        *,
        tenant_id: int,
        case_id: int,
        task_type: str,
        created_by: int,
        idempotency_key: str,
    ) -> AITask | None:
        return (
            self.db.query(AITask)
            .filter(
                AITask.tenant_id == tenant_id,
                AITask.case_id == case_id,
                AITask.task_type == task_type,
                AITask.created_by == created_by,
                AITask.idempotency_key == idempotency_key,
            )
            .order_by(AITask.created_at.desc(), AITask.id.desc())
            .first()
        )

    def get_task_by_task_id(self, *, task_id: str, tenant_id: int) -> AITask | None:
        return (
            self.db.query(AITask)
            .filter(AITask.task_id == task_id, AITask.tenant_id == tenant_id)
            .first()
        )

    def get_task_by_id(self, *, task_id: int) -> AITask | None:
        return self.db.query(AITask).filter(AITask.id == task_id).first()

    def get_task_for_worker(self, *, task_id: str) -> AITask | None:
        return self.db.query(AITask).filter(AITask.task_id == task_id).first()

    def claim_next_runnable_task(self, *, now: datetime) -> AITask | None:
        return (
            self.db.query(AITask)
            .filter(
                AITask.status.in_(("queued", "retrying")),
                or_(AITask.next_retry_at.is_(None), AITask.next_retry_at <= now),
            )
            .order_by(AITask.created_at.asc(), AITask.id.asc())
            .with_for_update(skip_locked=True)
            .first()
        )

    def list_stale_processing_tasks(
        self,
        *,
        stale_before: datetime,
        limit: int,
    ) -> list[AITask]:
        stale_condition = or_(
            and_(AITask.heartbeat_at.is_not(None), AITask.heartbeat_at <= stale_before),
            and_(
                AITask.heartbeat_at.is_(None),
                AITask.claimed_at.is_not(None),
                AITask.claimed_at <= stale_before,
            ),
            and_(
                AITask.heartbeat_at.is_(None),
                AITask.claimed_at.is_(None),
                AITask.started_at.is_not(None),
                AITask.started_at <= stale_before,
            ),
        )
        return (
            self.db.query(AITask)
            .filter(AITask.status == "processing", stale_condition)
            .order_by(AITask.updated_at.asc(), AITask.id.asc())
            .limit(max(1, limit))
            .with_for_update(skip_locked=True)
            .all()
        )

    def get_user(self, *, user_id: int, tenant_id: int) -> User | None:
        return (
            self.db.query(User)
            .filter(
                User.id == user_id,
                User.tenant_id == tenant_id,
            )
            .first()
        )

    def list_tasks(
        self,
        *,
        tenant_id: int,
        page: int,
        page_size: int,
        status_filter: str | None,
        task_type: str | None,
        visible_case_ids: Iterable[int] | None = None,
    ) -> tuple[int, list[AITask]]:
        query = self.db.query(AITask).filter(AITask.tenant_id == tenant_id)
        if visible_case_ids is not None:
            query = query.filter(AITask.case_id.in_(visible_case_ids))

        if status_filter:
            query = query.filter(AITask.status == status_filter)
        if task_type:
            query = query.filter(AITask.task_type == task_type)

        total = query.count()
        items = (
            query.order_by(desc(AITask.created_at), desc(AITask.id))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return total, items

    def list_case_facts(
        self,
        *,
        case_id: int,
        tenant_id: int,
        fact_type: str | None,
        min_confidence: float | None,
        page: int,
        page_size: int,
    ) -> tuple[int, list[CaseFact]]:
        query = self.db.query(CaseFact).filter(
            CaseFact.case_id == case_id,
            CaseFact.tenant_id == tenant_id,
        )
        if fact_type:
            query = query.filter(CaseFact.fact_type == fact_type)
        if min_confidence is not None:
            query = query.filter(CaseFact.confidence >= min_confidence)

        total = query.count()
        items = (
            query.order_by(CaseFact.created_at.desc(), CaseFact.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return total, items

    def list_analysis_results(self, *, case_id: int, tenant_id: int) -> list[AIAnalysisResult]:
        return (
            self.db.query(AIAnalysisResult)
            .filter(
                AIAnalysisResult.case_id == case_id,
                AIAnalysisResult.tenant_id == tenant_id,
            )
            .order_by(AIAnalysisResult.created_at.desc(), AIAnalysisResult.id.desc())
            .all()
        )

    def list_falsification_records(
        self,
        *,
        case_id: int,
        tenant_id: int,
    ) -> list[FalsificationRecord]:
        return (
            self.db.query(FalsificationRecord)
            .filter(
                FalsificationRecord.case_id == case_id,
                FalsificationRecord.tenant_id == tenant_id,
            )
            .order_by(FalsificationRecord.created_at.desc(), FalsificationRecord.id.desc())
            .all()
        )

    def delete_case_facts_for_file(self, *, case_id: int, tenant_id: int, file_id: int) -> None:
        (
            self.db.query(CaseFact)
            .filter(
                CaseFact.case_id == case_id,
                CaseFact.tenant_id == tenant_id,
                CaseFact.file_id == file_id,
            )
            .delete(synchronize_session=False)
        )

    def save_case_facts(self, facts: Iterable[CaseFact]) -> None:
        self.db.add_all(list(facts))

    def save_analysis_results(self, results: Iterable[AIAnalysisResult]) -> None:
        self.db.add_all(list(results))

    def save_falsification_records(self, records: Iterable[FalsificationRecord]) -> None:
        self.db.add_all(list(records))

    def sum_analysis_cost_for_case(self, *, case_id: int, tenant_id: int) -> Decimal:
        total = (
            self.db.query(func.coalesce(func.sum(AIAnalysisResult.cost), 0))
            .filter(
                AIAnalysisResult.case_id == case_id,
                AIAnalysisResult.tenant_id == tenant_id,
            )
            .scalar()
        )
        return Decimal(str(total or 0))

    def sum_analysis_cost_for_tenant_in_month(
        self,
        *,
        tenant_id: int,
        month_start: datetime,
        month_end: datetime,
    ) -> Decimal:
        total = (
            self.db.query(func.coalesce(func.sum(AIAnalysisResult.cost), 0))
            .filter(
                AIAnalysisResult.tenant_id == tenant_id,
                AIAnalysisResult.created_at >= month_start,
                AIAnalysisResult.created_at < month_end,
            )
            .scalar()
        )
        return Decimal(str(total or 0))
