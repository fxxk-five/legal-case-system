import re
import secrets

from pydantic import ValidationError

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.roles import normalize_role, role_values_for_query
from app.core.security import create_access_token
from app.core.statuses import (
    TenantStatus,
    UserStatus,
    can_transition_tenant_status,
    can_transition_user_status,
    is_active_tenant_status,
)
from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_super_admin, require_tenant_admin
from app.models.case import Case
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import UserRegister
from app.schemas.tenant import (
    TenantCreateOrganization,
    TenantCreatePersonal,
    TenantCreateResult,
    TenantJoinRequest,
    TenantJoinResult,
    TenantAIBudgetRead,
    TenantAIBudgetUpdate,
    CaseAIBudgetRead,
    CaseAIBudgetUpdate,
    TenantPreview,
    TenantRead,
    TenantStatusUpdate,
    TenantUpdate,
)
from app.services.auth import create_user


router = APIRouter(prefix="/tenants", tags=["Tenants"])


def _normalize_tenant_code(raw_value: str | None, prefix: str) -> str:
    if raw_value:
        normalized = re.sub(r"[^a-zA-Z0-9]+", "-", raw_value.strip().lower()).strip("-")
        if len(normalized) >= 3:
            return normalized[:50]
    suffix = secrets.token_hex(3)
    return f"{prefix}-{suffix}"


def _ensure_unique_tenant_code(db: Session, candidate: str, prefix: str) -> str:
    current = candidate
    while (
        db.query(Tenant)
        .filter(Tenant.tenant_code == current)
        .first()
        is not None
    ):
        current = _normalize_tenant_code(None, prefix)
    return current


def _build_create_result(tenant: Tenant, admin_user: User) -> TenantCreateResult:
    access_token = create_access_token(
        admin_user.id,
        extra_data={
            "tenant_id": tenant.id,
            "role": admin_user.role,
            "is_tenant_admin": admin_user.is_tenant_admin,
        },
    )
    return TenantCreateResult(
        tenant=tenant,
        access_token=access_token,
        user_id=admin_user.id,
    )


def _get_tenant_by_code_or_404(db: Session, tenant_code: str) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.tenant_code == tenant_code).first()
    if tenant is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.TENANT_NOT_FOUND,
            message="租户不存在。",
            detail="租户不存在。",
        )
    return tenant


def _to_float_or_none(value: object | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@router.post("/personal", response_model=TenantCreateResult, status_code=status.HTTP_201_CREATED)
def create_personal_tenant(
    tenant_in: TenantCreatePersonal,
    db: Session = Depends(get_db),
) -> TenantCreateResult:
    if db.query(User).filter(User.phone == tenant_in.admin_phone).first():
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.USER_ALREADY_EXISTS,
            message="该手机号已被使用。",
            detail="该手机号已被使用。",
        )

    tenant_code = _ensure_unique_tenant_code(
        db,
        _normalize_tenant_code(tenant_in.tenant_code or tenant_in.workspace_name, "personal"),
        "personal",
    )
    tenant = Tenant(
        tenant_code=tenant_code,
        name=tenant_in.workspace_name,
        type="personal",
        status=int(TenantStatus.ACTIVE),
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    admin_user = create_user(
        db,
        user_in=UserRegister(
            phone=tenant_in.admin_phone,
            password=tenant_in.admin_password,
            real_name=tenant_in.admin_real_name,
        ),
        tenant_id=tenant.id,
        role=normalize_role("tenant_admin"),
        is_tenant_admin=True,
    )
    return _build_create_result(tenant, admin_user)


@router.post("/organization", response_model=TenantCreateResult, status_code=status.HTTP_201_CREATED)
def create_organization_tenant(
    tenant_in: TenantCreateOrganization,
    db: Session = Depends(get_db),
) -> TenantCreateResult:
    if db.query(User).filter(User.phone == tenant_in.admin_phone).first():
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.USER_ALREADY_EXISTS,
            message="该手机号已被使用。",
            detail="该手机号已被使用。",
        )

    tenant_code = _ensure_unique_tenant_code(
        db,
        _normalize_tenant_code(tenant_in.tenant_code or tenant_in.name, "org"),
        "org",
    )
    tenant = Tenant(
        tenant_code=tenant_code,
        name=tenant_in.name,
        type="organization",
        status=int(TenantStatus.ACTIVE),
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    admin_user = create_user(
        db,
        user_in=UserRegister(
            phone=tenant_in.admin_phone,
            password=tenant_in.admin_password,
            real_name=tenant_in.admin_real_name,
        ),
        tenant_id=tenant.id,
        role=normalize_role("tenant_admin"),
        is_tenant_admin=True,
    )
    return _build_create_result(tenant, admin_user)


@router.post("/join", response_model=TenantJoinResult, status_code=status.HTTP_201_CREATED)
def join_tenant(
    join_in: TenantJoinRequest,
    db: Session = Depends(get_db),
) -> TenantJoinResult:
    tenant = _get_tenant_by_code_or_404(db, join_in.tenant_code)
    if tenant.type == "organization":
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.INVITE_REQUIRED,
            message="机构律师必须通过邀请链接注册。",
            detail="机构律师必须通过邀请链接注册。",
        )
    if not is_active_tenant_status(tenant.status):
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.TENANT_INACTIVE,
            message="目标租户未启用。",
            detail="目标租户未启用。",
        )

    existing_user = (
        db.query(User)
        .filter(User.tenant_id == tenant.id, User.phone == join_in.phone)
        .first()
    )
    if existing_user:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.USER_ALREADY_EXISTS,
            message="该手机号已存在于当前租户。",
            detail="该手机号已存在于当前租户。",
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
            message="机构律师注册参数不合法。",
            detail=exc.errors(),
        ) from exc

    user = create_user(
        db,
        user_in=payload,
        tenant_id=tenant.id,
        role="lawyer",
        status=int(UserStatus.PENDING_APPROVAL),
    )
    return TenantJoinResult(
        tenant=tenant,
        user_id=user.id,
        status=user.status,
        message="加入申请已提交，等待租户管理员审批。",
    )


@router.get("/invite/{tenant_code}", response_model=TenantPreview)
def preview_tenant_by_code(
    tenant_code: str,
    db: Session = Depends(get_db),
) -> Tenant:
    return _get_tenant_by_code_or_404(db, tenant_code)


@router.get("/{tenant_id}/preview", response_model=TenantPreview)
def preview_tenant_by_id(
    tenant_id: int,
    db: Session = Depends(get_db),
) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if tenant is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.TENANT_NOT_FOUND,
            message="租户不存在。",
            detail="租户不存在。",
        )
    return tenant


@router.get("/current", response_model=TenantRead)
def get_current_tenant(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if tenant is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.TENANT_NOT_FOUND,
            message="租户不存在。",
            detail="租户不存在。",
        )
    return tenant


@router.get("", response_model=list[TenantRead])
def list_all_tenants(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> list[Tenant]:
    return db.query(Tenant).order_by(Tenant.id.asc()).all()


@router.patch("/current", response_model=TenantRead)
def update_current_tenant(
    tenant_in: TenantUpdate,
    current_user: User = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if tenant is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.TENANT_NOT_FOUND,
            message="租户不存在。",
            detail="租户不存在。",
        )

    tenant.name = tenant_in.name
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@router.patch("/{tenant_id}/status", response_model=TenantRead)
def update_tenant_status(
    tenant_id: int,
    tenant_in: TenantStatusUpdate,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> Tenant:
    _ = current_user
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if tenant is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.TENANT_NOT_FOUND,
            message="租户不存在。",
            detail="租户不存在。",
        )
    if not can_transition_tenant_status(tenant.status, tenant_in.status):
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.CONFLICT,
            message="租户状态流转不合法。",
            detail="租户状态流转不合法。",
        )
    tenant.status = tenant_in.status
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@router.get("/{tenant_id}/ai-budget", response_model=TenantAIBudgetRead)
def get_tenant_ai_budget(
    tenant_id: int,
    _: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> TenantAIBudgetRead:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if tenant is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.TENANT_NOT_FOUND,
            message="租户不存在。",
            detail="租户不存在。",
        )
    return TenantAIBudgetRead(
        tenant_id=tenant.id,
        ai_monthly_budget_limit=_to_float_or_none(tenant.ai_monthly_budget_limit),
        ai_budget_degrade_model=tenant.ai_budget_degrade_model,
    )


@router.patch("/{tenant_id}/ai-budget", response_model=TenantAIBudgetRead)
def update_tenant_ai_budget(
    tenant_id: int,
    payload: TenantAIBudgetUpdate,
    _: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> TenantAIBudgetRead:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if tenant is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.TENANT_NOT_FOUND,
            message="租户不存在。",
            detail="租户不存在。",
        )

    if payload.clear_monthly_budget_limit:
        tenant.ai_monthly_budget_limit = None
    elif payload.ai_monthly_budget_limit is not None:
        tenant.ai_monthly_budget_limit = payload.ai_monthly_budget_limit

    if payload.clear_budget_degrade_model:
        tenant.ai_budget_degrade_model = None
    elif payload.ai_budget_degrade_model is not None:
        normalized = payload.ai_budget_degrade_model.strip()
        tenant.ai_budget_degrade_model = normalized or None

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return TenantAIBudgetRead(
        tenant_id=tenant.id,
        ai_monthly_budget_limit=_to_float_or_none(tenant.ai_monthly_budget_limit),
        ai_budget_degrade_model=tenant.ai_budget_degrade_model,
    )


@router.get("/{tenant_id}/cases/{case_id}/ai-budget", response_model=CaseAIBudgetRead)
def get_case_ai_budget(
    tenant_id: int,
    case_id: int,
    _: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> CaseAIBudgetRead:
    case = db.query(Case).filter(Case.id == case_id, Case.tenant_id == tenant_id).first()
    if case is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.CASE_NOT_FOUND,
            message="案件不存在。",
            detail="案件不存在。",
        )
    return CaseAIBudgetRead(
        case_id=case.id,
        tenant_id=case.tenant_id,
        ai_case_budget_limit=_to_float_or_none(case.ai_case_budget_limit),
    )


@router.patch("/{tenant_id}/cases/{case_id}/ai-budget", response_model=CaseAIBudgetRead)
def update_case_ai_budget(
    tenant_id: int,
    case_id: int,
    payload: CaseAIBudgetUpdate,
    _: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> CaseAIBudgetRead:
    case = db.query(Case).filter(Case.id == case_id, Case.tenant_id == tenant_id).first()
    if case is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.CASE_NOT_FOUND,
            message="案件不存在。",
            detail="案件不存在。",
        )

    if payload.clear_case_budget_limit:
        case.ai_case_budget_limit = None
    elif payload.ai_case_budget_limit is not None:
        case.ai_case_budget_limit = payload.ai_case_budget_limit

    db.add(case)
    db.commit()
    db.refresh(case)

    return CaseAIBudgetRead(
        case_id=case.id,
        tenant_id=case.tenant_id,
        ai_case_budget_limit=_to_float_or_none(case.ai_case_budget_limit),
    )


@router.patch("/members/{user_id}/approve", status_code=status.HTTP_200_OK)
def approve_tenant_member(
    user_id: int,
    current_user: User = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
) -> dict[str, str | int]:
    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.tenant_id == current_user.tenant_id,
            User.role.in_(role_values_for_query("lawyer", "tenant_admin")),
        )
        .first()
    )
    if user is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.USER_NOT_FOUND,
            message="用户不存在。",
            detail="用户不存在。",
        )
    if not can_transition_user_status(user.status, int(UserStatus.ACTIVE)):
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.CONFLICT,
            message="该成员当前状态不允许审批通过。",
            detail="该成员当前状态不允许审批通过。",
        )

    user.status = int(UserStatus.ACTIVE)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "成员审批通过。", "user_id": user.id, "status": user.status}
