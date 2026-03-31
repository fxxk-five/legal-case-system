from __future__ import annotations

from app.models.user import User
from app.modules.cases.flow import create_case_flow
from app.modules.cases.helpers import (
    append_client_remark,
    ensure_case_client_owner,
    ensure_case_editor,
    get_case_or_404,
    serialize_case_for_viewer,
)
from app.modules.cases.repository import CasesRepository
from app.modules.cases.schemas import CaseClientRemarkUpdate, CaseLawyerRead, CaseLawyerRemarkUpdate, CaseRead


class CaseRemarkService:
    def __init__(self, db) -> None:
        self.db = db
        self.repo = CasesRepository(db)

    def update_client_remark(
        self,
        *,
        case_id: int,
        payload: CaseClientRemarkUpdate,
        current_user: User,
    ) -> CaseRead:
        case = get_case_or_404(self.db, case_id=case_id, current_user=current_user)
        ensure_case_client_owner(case=case, current_user=current_user)

        case.client_remark = append_client_remark(
            existing_remark=case.client_remark,
            incoming_remark=payload.client_remark,
        )
        create_case_flow(
            db=self.db,
            tenant_id=case.tenant_id,
            case_id=case.id,
            action_type="client_remark_updated",
            content="当事人更新了补充说明。",
            operator=current_user,
            visible_to="both",
        )
        self.repo.save_commit_refresh(case)
        return serialize_case_for_viewer(db=self.db, case=case, current_user=current_user)

    def update_lawyer_remark(
        self,
        *,
        case_id: int,
        payload: CaseLawyerRemarkUpdate,
        current_user: User,
    ) -> CaseLawyerRead:
        case = get_case_or_404(self.db, case_id=case_id, current_user=current_user)
        ensure_case_editor(case=case, current_user=current_user)

        case.lawyer_remark = payload.lawyer_remark or None
        create_case_flow(
            db=self.db,
            tenant_id=case.tenant_id,
            case_id=case.id,
            action_type="lawyer_remark_updated",
            content="律师更新了内部备注。",
            operator=current_user,
            visible_to="lawyer",
        )
        self.repo.save_commit_refresh(case)
        return serialize_case_for_viewer(db=self.db, case=case, current_user=current_user)
