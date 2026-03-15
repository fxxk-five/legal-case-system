from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import UserRegister


def authenticate_user(
    db: Session,
    *,
    phone: str,
    password: str,
    tenant_id: int | None = None,
) -> User | None:
    query = db.query(User).filter(User.phone == phone, User.status == 1)
    if tenant_id is not None:
        query = query.filter(User.tenant_id == tenant_id)

    users = query.order_by(User.created_at.asc()).all()
    matched_users = [user for user in users if verify_password(password, user.password_hash)]
    if not matched_users:
        return None
    if tenant_id is None and len(matched_users) > 1:
        raise ValueError("MULTIPLE_TENANTS_MATCHED")
    return matched_users[0]


def create_user(
    db: Session,
    *,
    user_in: UserRegister,
    tenant_id: int,
    role: str = "lawyer",
    is_tenant_admin: bool = False,
    status: int = 1,
) -> User:
    user = User(
        tenant_id=tenant_id,
        phone=user_in.phone,
        real_name=user_in.real_name,
        role=role,
        is_tenant_admin=is_tenant_admin,
        password_hash=get_password_hash(user_in.password),
        status=status,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def resolve_tenant_for_registration(
    db: Session,
    *,
    tenant_code: str | None,
) -> Tenant | None:
    if tenant_code:
        return (
            db.query(Tenant)
            .filter(Tenant.tenant_code == tenant_code, Tenant.status == 1)
            .first()
        )

    tenants = db.query(Tenant).filter(Tenant.status == 1).order_by(Tenant.id.asc()).all()
    if len(tenants) == 1:
        return tenants[0]
    return None
