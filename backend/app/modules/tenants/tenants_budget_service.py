from __future__ import annotations

from typing import Callable

from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.models.tenant import Tenant
from app.modules.tenants.repository import TenantsRepository
from app.modules.tenants.schemas import (
    CaseAIBudgetRead,
    CaseAIBudgetUpdate,
    TenantAIBudgetRead,
    TenantAIBudgetUpdate,
)


class TenantsBudgetService:
    def __init__(
        self,
        db: Session,
        *,
        repository: TenantsRepository,
        get_tenant_or_404: Callable[..., Tenant],
        to_float_or_none: Callable[[object | None], float | None],
    ) -> None:
        self.db = db
        self.repository = repository
        self.get_tenant_or_404 = get_tenant_or_404
        self.to_float_or_none = to_float_or_none

    def get_tenant_ai_budget(self, *, tenant_id: int) -> TenantAIBudgetRead:
        tenant = self.get_tenant_or_404(tenant_id=tenant_id)
        return TenantAIBudgetRead(
            tenant_id=tenant.id,
            ai_monthly_budget_limit=self.to_float_or_none(tenant.ai_monthly_budget_limit),
            ai_budget_degrade_model=tenant.ai_budget_degrade_model,
        )

    def update_tenant_ai_budget(self, *, tenant_id: int, payload: TenantAIBudgetUpdate) -> TenantAIBudgetRead:
        tenant = self.get_tenant_or_404(tenant_id=tenant_id)
        if payload.clear_monthly_budget_limit:
            tenant.ai_monthly_budget_limit = None
        elif payload.ai_monthly_budget_limit is not None:
            tenant.ai_monthly_budget_limit = payload.ai_monthly_budget_limit

        if payload.clear_budget_degrade_model:
            tenant.ai_budget_degrade_model = None
        elif payload.ai_budget_degrade_model is not None:
            normalized = payload.ai_budget_degrade_model.strip()
            tenant.ai_budget_degrade_model = normalized or None

        self.repository.save_and_refresh(tenant)

        return TenantAIBudgetRead(
            tenant_id=tenant.id,
            ai_monthly_budget_limit=self.to_float_or_none(tenant.ai_monthly_budget_limit),
            ai_budget_degrade_model=tenant.ai_budget_degrade_model,
        )

    def get_case_ai_budget(self, *, tenant_id: int, case_id: int) -> CaseAIBudgetRead:
        case = self.repository.get_case(case_id=case_id, tenant_id=tenant_id)
        if case is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code=ErrorCode.CASE_NOT_FOUND,
                message="Case not found.",
                detail="Case not found.",
            )
        return CaseAIBudgetRead(
            case_id=case.id,
            tenant_id=case.tenant_id,
            ai_case_budget_limit=self.to_float_or_none(case.ai_case_budget_limit),
        )

    def update_case_ai_budget(
        self,
        *,
        tenant_id: int,
        case_id: int,
        payload: CaseAIBudgetUpdate,
    ) -> CaseAIBudgetRead:
        case = self.repository.get_case(case_id=case_id, tenant_id=tenant_id)
        if case is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code=ErrorCode.CASE_NOT_FOUND,
                message="Case not found.",
                detail="Case not found.",
            )

        if payload.clear_case_budget_limit:
            case.ai_case_budget_limit = None
        elif payload.ai_case_budget_limit is not None:
            case.ai_case_budget_limit = payload.ai_case_budget_limit

        self.repository.save_and_refresh(case)

        return CaseAIBudgetRead(
            case_id=case.id,
            tenant_id=case.tenant_id,
            ai_case_budget_limit=self.to_float_or_none(case.ai_case_budget_limit),
        )

