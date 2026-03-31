from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.user import User
from app.modules.ai.models.ai_task import AITask
from app.modules.ai.schemas import AnalysisRequest
from app.modules.ai.service import AIService
from app.modules.cases.flow import create_case_flow
from app.modules.cases.models.case import Case
from app.modules.files.repository import FilesRepository


logger = logging.getLogger("app.modules.files")
_AUTO_REANALYZE_DEBOUNCE_SECONDS = 300


class CaseFileReanalysisService:
    def __init__(self, db: Session, *, repository: FilesRepository | None = None) -> None:
        self.db = db
        self.repo = repository or FilesRepository(db)

    def run_after_upload(
        self,
        *,
        request: Request,
        case: Case,
        upload_user: User,
        uploader_role: str,
    ) -> None:
        if uploader_role != "client":
            return

        try:
            self._schedule_auto_reanalysis(
                request=request,
                case=case,
                upload_user=upload_user,
            )
        except AppError as exc:
            logger.warning(
                "files.auto_reanalyze_failed case_id=%s user_id=%s code=%s",
                case.id,
                upload_user.id,
                exc.code,
            )
            create_case_flow(
                db=self.db,
                tenant_id=upload_user.tenant_id,
                case_id=case.id,
                action_type="analysis_auto_reanalyze_failed",
                content=f"Supplemental upload detected; auto reanalysis failed ({exc.code}).",
                operator=upload_user,
                visible_to="both",
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "files.auto_reanalyze_failed_unexpected case_id=%s user_id=%s",
                case.id,
                upload_user.id,
            )
            create_case_flow(
                db=self.db,
                tenant_id=upload_user.tenant_id,
                case_id=case.id,
                action_type="analysis_auto_reanalyze_failed",
                content="Supplemental upload detected; auto reanalysis failed unexpectedly.",
                operator=upload_user,
                visible_to="both",
            )

    def _schedule_auto_reanalysis(
        self,
        *,
        request: Request,
        case: Case,
        upload_user: User,
    ) -> None:
        case.analysis_status = "pending_reanalysis"
        case.analysis_progress = 0
        self.repo.save(case)

        if case.assigned_lawyer_id is None:
            create_case_flow(
                db=self.db,
                tenant_id=case.tenant_id,
                case_id=case.id,
                action_type="analysis_auto_reanalyze_skipped",
                content="Supplemental upload detected, but no assigned lawyer was found.",
                operator=upload_user,
                visible_to="both",
            )
            return

        operator = self.repo.get_active_user(user_id=case.assigned_lawyer_id, tenant_id=case.tenant_id)
        if operator is None:
            create_case_flow(
                db=self.db,
                tenant_id=case.tenant_id,
                case_id=case.id,
                action_type="analysis_auto_reanalyze_skipped",
                content="Supplemental upload detected, but assigned lawyer is unavailable.",
                operator=upload_user,
                visible_to="both",
            )
            return

        now = datetime.now(timezone.utc)
        idempotency_key = self._auto_reanalyze_idempotency_key(case_id=case.id, now=now)
        existing_task = self._find_existing_auto_reanalyze_task(
            tenant_id=case.tenant_id,
            case_id=case.id,
            operator_id=operator.id,
            idempotency_key=idempotency_key,
        )

        ai_service = AIService(
            db=self.db,
            request_id=getattr(request.state, "request_id", None),
            session_factory=getattr(request.app.state, "session_factory", None),
        )
        result = ai_service.start_analysis(
            case_id=case.id,
            payload=AnalysisRequest(),
            current_user=operator,
            idempotency_key=idempotency_key,
        )

        if existing_task is not None and existing_task.task_id == result.task_id:
            create_case_flow(
                db=self.db,
                tenant_id=case.tenant_id,
                case_id=case.id,
                action_type="analysis_auto_reanalyze_debounced",
                content=(
                    f"Supplemental upload detected; reused analyze task {result.task_id} "
                    "within 5-minute debounce window."
                ),
                operator=upload_user,
                visible_to="both",
            )
            return

        create_case_flow(
            db=self.db,
            tenant_id=case.tenant_id,
            case_id=case.id,
            action_type="analysis_auto_reanalyze_queued",
            content=f"Supplemental upload detected; queued analyze task {result.task_id}.",
            operator=upload_user,
            visible_to="both",
        )

    def _auto_reanalyze_idempotency_key(self, *, case_id: int, now: datetime) -> str:
        bucket = int(now.timestamp()) // _AUTO_REANALYZE_DEBOUNCE_SECONDS
        return f"auto-reanalyze:{case_id}:{bucket}"

    def _find_existing_auto_reanalyze_task(
        self,
        *,
        tenant_id: int,
        case_id: int,
        operator_id: int,
        idempotency_key: str,
    ) -> AITask | None:
        return self.repo.find_auto_reanalyze_task(
            tenant_id=tenant_id,
            case_id=case_id,
            operator_id=operator_id,
            idempotency_key=idempotency_key,
        )
