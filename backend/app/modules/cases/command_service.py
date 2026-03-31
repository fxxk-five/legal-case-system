from __future__ import annotations

from fastapi import status

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.legal_types import normalize_legal_type
from app.core.roles import can_manage_case_role
from app.integrations.wechat.service import create_case_invite_token
from app.models.user import User
from app.modules.auth.schemas import UserRegister
from app.modules.auth.service import create_user, generate_system_password
from app.modules.cases.flow import create_case_flow
from app.modules.cases.helpers import ensure_case_editor, get_case_or_404, serialize_case_for_viewer, validate_status_transition
from app.modules.cases.models.case import Case
from app.modules.cases.numbering import generate_case_number, normalize_case_number
from app.modules.cases.repository import CasesRepository
from app.modules.cases.schemas import CaseCreate, CaseInviteRead, CaseLawyerRead, CaseRead, CaseUpdate


class CaseCommandService:
    def __init__(self, db) -> None:
        self.db = db
        self.repo = CasesRepository(db)

    def create_case(self, *, case_in: CaseCreate, current_user: User) -> CaseRead | CaseLawyerRead:
        if not can_manage_case_role(current_user.role):
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code=ErrorCode.CASE_OPERATION_NOT_ALLOWED,
                message="当前角色不能创建案件。",
                detail="当前角色不能创建案件。",
            )

        client = self.repo.find_client_by_phone(tenant_id=current_user.tenant_id, phone=case_in.client_phone)
        if client is None:
            client = create_user(
                self.db,
                user_in=UserRegister(
                    phone=case_in.client_phone,
                    password=generate_system_password(),
                    real_name=case_in.client_real_name,
                ),
                tenant_id=current_user.tenant_id,
                role="client",
                must_reset_password=True,
            )

        case_number = normalize_case_number(case_in.case_number)
        if case_number is None:
            tenant = self.repo.get_tenant(tenant_id=current_user.tenant_id)
            if tenant is None:
                raise AppError(
                    status_code=status.HTTP_404_NOT_FOUND,
                    code=ErrorCode.TENANT_NOT_FOUND,
                    message="Tenant not found.",
                    detail="Tenant not found.",
                )

            for _ in range(10):
                candidate = generate_case_number(
                    db=self.db,
                    tenant_id=current_user.tenant_id,
                    tenant_code=tenant.tenant_code,
                    legal_type=case_in.legal_type,
                )
                if not self.repo.case_number_exists(tenant_id=current_user.tenant_id, case_number=candidate):
                    case_number = candidate
                    break
            if case_number is None:
                raise AppError(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Failed to generate case number. Please retry.",
                    detail="Failed to generate case number. Please retry.",
                )
        elif self.repo.case_number_exists(tenant_id=current_user.tenant_id, case_number=case_number):
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                code=ErrorCode.CONFLICT,
                message="Case number already exists.",
                detail="Case number already exists.",
            )

        case = Case(
            tenant_id=current_user.tenant_id,
            case_number=case_number,
            title=case_in.title,
            legal_type=normalize_legal_type(case_in.legal_type),
            client_id=client.id,
            assigned_lawyer_id=current_user.id,
            status="new",
            deadline=case_in.deadline,
            upload_guide=case_in.upload_guide,
        )
        self.repo.save_and_flush(case)
        create_case_flow(
            db=self.db,
            tenant_id=current_user.tenant_id,
            case_id=case.id,
            action_type="case_created",
            content=f"Created case {case.case_number}.",
            operator=current_user,
            visible_to="both",
        )
        self.repo.commit_and_refresh(case)

        created_case = get_case_or_404(self.db, case_id=case.id, current_user=current_user)
        return serialize_case_for_viewer(db=self.db, case=created_case, current_user=current_user)

    def update_case(
        self,
        *,
        case_id: int,
        case_in: CaseUpdate,
        current_user: User,
    ) -> CaseLawyerRead:
        case = get_case_or_404(self.db, case_id=case_id, current_user=current_user)
        ensure_case_editor(case=case, current_user=current_user)

        if case_in.status is not None:
            validate_status_transition(current_status=case.status, new_status=case_in.status)

        if case_in.title is not None:
            case.title = case_in.title
        if case_in.status is not None:
            case.status = case_in.status
        if case_in.legal_type is not None:
            case.legal_type = normalize_legal_type(case_in.legal_type)
        if case_in.deadline is not None:
            case.deadline = case_in.deadline
        if "upload_guide" in case_in.model_fields_set:
            case.upload_guide = case_in.upload_guide
        if case_in.assigned_lawyer_id is not None:
            lawyer = self.repo.find_assignable_lawyer(
                tenant_id=current_user.tenant_id,
                user_id=case_in.assigned_lawyer_id,
            )
            if lawyer is None:
                raise AppError(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    code=ErrorCode.USER_NOT_FOUND,
                    message="指派律师不存在。",
                    detail="指派律师不存在。",
                )
            case.assigned_lawyer_id = lawyer.id

        self.repo.save_commit_refresh(case)
        case = get_case_or_404(self.db, case_id=case.id, current_user=current_user)
        return serialize_case_for_viewer(db=self.db, case=case, current_user=current_user)

    def get_case_invite_qrcode(self, *, case_id: int, current_user: User) -> CaseInviteRead:
        case = get_case_or_404(self.db, case_id=case_id, current_user=current_user)
        ensure_case_editor(case=case, current_user=current_user)

        token = create_case_invite_token(case_id=case.id, tenant_id=case.tenant_id)
        path = f"{settings.WECHAT_MINIAPP_CLIENT_ENTRY_PAGE}?scene=client-case&token={token}"
        return CaseInviteRead(case_id=case.id, tenant_id=case.tenant_id, token=token, path=path)
