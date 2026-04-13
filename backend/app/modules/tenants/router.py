from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.roles import role_values_for_query
from app.db.session import get_db
from app.modules.auth.deps import get_current_user_allow_pending, require_super_admin, require_tenant_admin
from app.models.tenant import Tenant
from app.models.user import User
from app.modules.tenants.service import TenantsService
from app.modules.users.service import UsersService
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
    TenantPreview,
    TenantRead,
    TenantStatusUpdate,
    TenantUpdate,
)


router = APIRouter(prefix="/tenants", tags=["Tenants"])


def _tenants_service(db: Session) -> TenantsService:
    return TenantsService(db)


@router.post("/personal", response_model=TenantCreateResult, status_code=status.HTTP_201_CREATED)
def create_personal_tenant(
    tenant_in: TenantCreatePersonal,
    db: Session = Depends(get_db),
) -> TenantCreateResult:
    return _tenants_service(db).create_personal_tenant(tenant_in=tenant_in)


@router.post("/organization", response_model=TenantCreateResult, status_code=status.HTTP_201_CREATED)
def create_organization_tenant(
    tenant_in: TenantCreateOrganization,
    db: Session = Depends(get_db),
) -> TenantCreateResult:
    return _tenants_service(db).create_organization_tenant(tenant_in=tenant_in)


@router.post("/join", response_model=TenantJoinResult, status_code=status.HTTP_201_CREATED)
def join_tenant(
    join_in: TenantJoinRequest,
    db: Session = Depends(get_db),
) -> TenantJoinResult:
    return _tenants_service(db).join_tenant(join_in=join_in)


@router.get("/invite/{tenant_code}", response_model=TenantPreview)
def preview_tenant_by_code(
    tenant_code: str,
    db: Session = Depends(get_db),
) -> Tenant:
    return _tenants_service(db).preview_tenant_by_code(tenant_code=tenant_code)


@router.get("/{tenant_id}/preview", response_model=TenantPreview)
def preview_tenant_by_id(
    tenant_id: int,
    db: Session = Depends(get_db),
) -> Tenant:
    return _tenants_service(db).preview_tenant_by_id(tenant_id=tenant_id)


@router.get("/current", response_model=TenantRead)
def get_current_tenant(
    current_user: User = Depends(get_current_user_allow_pending),
    db: Session = Depends(get_db),
) -> Tenant:
    return _tenants_service(db).get_current_tenant(current_user=current_user)


@router.get("", response_model=list[TenantRead])
def list_all_tenants(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> list[Tenant]:
    _ = current_user
    return _tenants_service(db).list_all_tenants()


@router.patch("/current", response_model=TenantRead)
def update_current_tenant(
    tenant_in: TenantUpdate,
    current_user: User = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
) -> Tenant:
    return _tenants_service(db).update_current_tenant(
        tenant_in=tenant_in,
        current_user=current_user,
    )


@router.patch("/{tenant_id}/status", response_model=TenantRead)
def update_tenant_status(
    tenant_id: int,
    tenant_in: TenantStatusUpdate,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> Tenant:
    _ = current_user
    return _tenants_service(db).update_tenant_status(
        tenant_id=tenant_id,
        tenant_in=tenant_in,
    )


@router.get("/{tenant_id}/ai-budget", response_model=TenantAIBudgetRead)
def get_tenant_ai_budget(
    tenant_id: int,
    _: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> TenantAIBudgetRead:
    return _tenants_service(db).get_tenant_ai_budget(tenant_id=tenant_id)


@router.patch("/{tenant_id}/ai-budget", response_model=TenantAIBudgetRead)
def update_tenant_ai_budget(
    tenant_id: int,
    payload: TenantAIBudgetUpdate,
    _: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> TenantAIBudgetRead:
    return _tenants_service(db).update_tenant_ai_budget(
        tenant_id=tenant_id,
        payload=payload,
    )


@router.get("/{tenant_id}/cases/{case_id}/ai-budget", response_model=CaseAIBudgetRead)
def get_case_ai_budget(
    tenant_id: int,
    case_id: int,
    _: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> CaseAIBudgetRead:
    return _tenants_service(db).get_case_ai_budget(
        tenant_id=tenant_id,
        case_id=case_id,
    )


@router.patch("/{tenant_id}/cases/{case_id}/ai-budget", response_model=CaseAIBudgetRead)
def update_case_ai_budget(
    tenant_id: int,
    case_id: int,
    payload: CaseAIBudgetUpdate,
    _: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> CaseAIBudgetRead:
    return _tenants_service(db).update_case_ai_budget(
        tenant_id=tenant_id,
        case_id=case_id,
        payload=payload,
    )


@router.patch("/members/{user_id}/approve", status_code=status.HTTP_200_OK)
def approve_tenant_member(
    user_id: int,
    current_user: User = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
) -> dict[str, str | int]:
    user = UsersService(db).approve_user(
        user_id=user_id,
        current_user=current_user,
        roles=role_values_for_query("lawyer", "tenant_admin"),
    )
    return {"message": "Member approved.", "user_id": user.id, "status": user.status}

