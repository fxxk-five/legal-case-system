import re
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_tenant_admin
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import UserRegister
from app.schemas.tenant import (
    TenantCreateOrganization,
    TenantCreatePersonal,
    TenantCreateResult,
    TenantJoinRequest,
    TenantJoinResult,
    TenantPreview,
    TenantRead,
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="租户不存在。")
    return tenant


@router.post("/personal", response_model=TenantCreateResult, status_code=status.HTTP_201_CREATED)
def create_personal_tenant(
    tenant_in: TenantCreatePersonal,
    db: Session = Depends(get_db),
) -> TenantCreateResult:
    if db.query(User).filter(User.phone == tenant_in.admin_phone).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该手机号已被使用。")

    tenant_code = _ensure_unique_tenant_code(
        db,
        _normalize_tenant_code(tenant_in.tenant_code or tenant_in.workspace_name, "personal"),
        "personal",
    )
    tenant = Tenant(
        tenant_code=tenant_code,
        name=tenant_in.workspace_name,
        type="personal",
        status=1,
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
        role="tenant_admin",
        is_tenant_admin=True,
    )
    return _build_create_result(tenant, admin_user)


@router.post("/organization", response_model=TenantCreateResult, status_code=status.HTTP_201_CREATED)
def create_organization_tenant(
    tenant_in: TenantCreateOrganization,
    db: Session = Depends(get_db),
) -> TenantCreateResult:
    if db.query(User).filter(User.phone == tenant_in.admin_phone).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该手机号已被使用。")

    tenant_code = _ensure_unique_tenant_code(
        db,
        _normalize_tenant_code(tenant_in.tenant_code or tenant_in.name, "org"),
        "org",
    )
    tenant = Tenant(
        tenant_code=tenant_code,
        name=tenant_in.name,
        type="organization",
        status=1,
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
        role="tenant_admin",
        is_tenant_admin=True,
    )
    return _build_create_result(tenant, admin_user)


@router.post("/join", response_model=TenantJoinResult, status_code=status.HTTP_201_CREATED)
def join_tenant(
    join_in: TenantJoinRequest,
    db: Session = Depends(get_db),
) -> TenantJoinResult:
    tenant = _get_tenant_by_code_or_404(db, join_in.tenant_code)
    if tenant.status != 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="目标租户未启用。")

    existing_user = (
        db.query(User)
        .filter(User.tenant_id == tenant.id, User.phone == join_in.phone)
        .first()
    )
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该手机号已存在于当前租户。")

    user = create_user(
        db,
        user_in=UserRegister(
            phone=join_in.phone,
            password=join_in.password,
            real_name=join_in.real_name,
        ),
        tenant_id=tenant.id,
        role="lawyer",
        status=0,
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="租户不存在。")
    return tenant


@router.get("/current", response_model=TenantRead)
def get_current_tenant(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="租户不存在。")
    return tenant


@router.patch("/current", response_model=TenantRead)
def update_current_tenant(
    tenant_in: TenantUpdate,
    current_user: User = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="租户不存在。")

    tenant.name = tenant_in.name
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


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
            User.role.in_(["lawyer", "tenant_admin"]),
        )
        .first()
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在。")
    if user.status == 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该成员已是激活状态。")

    user.status = 1
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "成员审批通过。", "user_id": user.id, "status": user.status}
