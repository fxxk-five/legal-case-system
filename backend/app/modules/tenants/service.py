from __future__ import annotations

from fastapi import status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.statuses import UserStatus, can_transition_tenant_status, is_active_tenant_status
from app.models.tenant import Tenant
from app.models.user import User
from app.modules.auth.schemas import UserRegister
from app.modules.auth.service import create_user
from app.modules.tenants.provisioning_service import TenantsProvisioningService
from app.modules.tenants.repository import TenantsRepository
from app.modules.tenants.schemas import (
    CaseAIBudgetRead,
    CaseAIBudgetUpdate,
    TenantAIBudgetRead,
    TenantAIBudgetUpdate,
    TenantCreateOrganization,
    TenantCreatePersonal,
    TenantCreateResult,
    TenantJoinRequest,
    TenantJoinResult,
    TenantStatusUpdate,
    TenantUpdate,
)
from app.modules.tenants.tenants_budget_service import TenantsBudgetService


class TenantsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = TenantsRepository(db)
        self.provisioning_service = TenantsProvisioningService(db, repository=self.repository)
        self.budget_service = TenantsBudgetService(
            db,
            repository=self.repository,
            get_tenant_or_404=self._get_tenant_or_404,
            to_float_or_none=self._to_float_or_none,
        )

    @staticmethod
    def _to_float_or_none(value: object | None) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _get_tenant_by_code_or_404(self, *, tenant_code: str) -> Tenant:
        tenant = self.repository.get_tenant_by_code(tenant_code=tenant_code)
        if tenant is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code=ErrorCode.TENANT_NOT_FOUND,
                message="Tenant not found.",
                detail="Tenant not found.",
            )
        return tenant

    def _get_tenant_or_404(self, *, tenant_id: int) -> Tenant:
        tenant = self.repository.get_tenant_by_id(tenant_id=tenant_id)
        if tenant is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code=ErrorCode.TENANT_NOT_FOUND,
                message="Tenant not found.",
                detail="Tenant not found.",
            )
        return tenant

    def create_personal_tenant(self, *, tenant_in: TenantCreatePersonal) -> TenantCreateResult:
        return self.provisioning_service.create_personal_tenant(tenant_in=tenant_in)

    def create_organization_tenant(self, *, tenant_in: TenantCreateOrganization) -> TenantCreateResult:
        return self.provisioning_service.create_organization_tenant(tenant_in=tenant_in)

    def join_tenant(self, *, join_in: TenantJoinRequest) -> TenantJoinResult:
        tenant = self._get_tenant_by_code_or_404(tenant_code=join_in.tenant_code)
        if tenant.type == "organization":
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code=ErrorCode.INVITE_REQUIRED,
                message="Organization lawyers must register via invite link.",
                detail="Organization lawyers must register via invite link.",
            )
        if not is_active_tenant_status(tenant.status):
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code=ErrorCode.TENANT_INACTIVE,
                message="Target tenant is not active.",
                detail="Target tenant is not active.",
            )

        existing_user = self.repository.get_tenant_user_by_phone(
            tenant_id=tenant.id,
            phone=join_in.phone,
        )
        if existing_user is not None:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                code=ErrorCode.USER_ALREADY_EXISTS,
                message="Phone number already exists in current tenant.",
                detail="Phone number already exists in current tenant.",
            )

        try:
            payload = UserRegister(
                phone=join_in.phone,
                password=join_in.password,
                real_name=join_in.real_name,
            )
        except ValidationError as exc:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code=ErrorCode.VALIDATION_ERROR,
                message="Invalid payload for tenant join.",
                detail=exc.errors(),
            ) from exc

        user = create_user(
            self.db,
            user_in=payload,
            tenant_id=tenant.id,
            role="lawyer",
            status=int(UserStatus.PENDING_APPROVAL),
        )
        return TenantJoinResult(
            tenant=tenant,
            user_id=user.id,
            status=user.status,
            message="Join request submitted and waiting for tenant admin review.",
        )

    def preview_tenant_by_code(self, *, tenant_code: str) -> Tenant:
        return self._get_tenant_by_code_or_404(tenant_code=tenant_code)

    def preview_tenant_by_id(self, *, tenant_id: int) -> Tenant:
        return self._get_tenant_or_404(tenant_id=tenant_id)

    def get_current_tenant(self, *, current_user: User) -> Tenant:
        return self._get_tenant_or_404(tenant_id=current_user.tenant_id)

    def list_all_tenants(self) -> list[Tenant]:
        return self.repository.list_all_tenants()

    def update_current_tenant(self, *, tenant_in: TenantUpdate, current_user: User) -> Tenant:
        tenant = self._get_tenant_or_404(tenant_id=current_user.tenant_id)
        tenant.name = tenant_in.name
        self.repository.save_and_refresh(tenant)
        return tenant

    def update_tenant_status(self, *, tenant_id: int, tenant_in: TenantStatusUpdate) -> Tenant:
        tenant = self._get_tenant_or_404(tenant_id=tenant_id)
        if not can_transition_tenant_status(tenant.status, tenant_in.status):
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                code=ErrorCode.CONFLICT,
                message="Invalid tenant status transition.",
                detail="Invalid tenant status transition.",
            )
        tenant.status = tenant_in.status
        self.repository.save_and_refresh(tenant)
        return tenant

    def get_tenant_ai_budget(self, *, tenant_id: int) -> TenantAIBudgetRead:
        return self.budget_service.get_tenant_ai_budget(
            tenant_id=tenant_id,
        )

    def update_tenant_ai_budget(self, *, tenant_id: int, payload: TenantAIBudgetUpdate) -> TenantAIBudgetRead:
        return self.budget_service.update_tenant_ai_budget(
            tenant_id=tenant_id,
            payload=payload,
        )

    def get_case_ai_budget(self, *, tenant_id: int, case_id: int) -> CaseAIBudgetRead:
        return self.budget_service.get_case_ai_budget(
            tenant_id=tenant_id,
            case_id=case_id,
        )

    def update_case_ai_budget(
        self,
        *,
        tenant_id: int,
        case_id: int,
        payload: CaseAIBudgetUpdate,
    ) -> CaseAIBudgetRead:
        return self.budget_service.update_case_ai_budget(
            tenant_id=tenant_id,
            case_id=case_id,
            payload=payload,
        )
