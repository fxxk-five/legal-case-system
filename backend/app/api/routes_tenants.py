from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_tenant_admin
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.tenant import TenantRead, TenantUpdate


router = APIRouter(prefix="/tenants", tags=["Tenants"])


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
