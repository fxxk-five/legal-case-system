from datetime import datetime, timezone
from secrets import token_hex

from sqlalchemy.orm import Session

from app.core.roles import normalize_role
from app.core.security import get_password_hash, verify_password
from app.core.statuses import TenantStatus, is_active_user_status
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import UserRegister
from app.schemas.validators import enforce_password, enforce_phone


def authenticate_user(
    db: Session,
    *,
    phone: str,
    password: str,
    tenant_id: int | None = None,
) -> User | None:
    phone = enforce_phone(phone)
    enforce_password(password)
    query = db.query(User).filter(User.phone == phone)
    if tenant_id is not None:
        query = query.filter(User.tenant_id == tenant_id)

    users = query.order_by(User.created_at.asc()).all()
    matched_users = [user for user in users if verify_password(password, user.password_hash)]
    if not matched_users:
        return None

    if tenant_id is None:
        active_matched = [user for user in matched_users if is_active_user_status(user.status)]
        if len(active_matched) > 1:
            raise ValueError("MULTIPLE_TENANTS_MATCHED")
        if len(active_matched) == 1:
            return active_matched[0]
        if len(matched_users) > 1:
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
    phone = enforce_phone(user_in.phone)
    password = enforce_password(user_in.password)
    user = User(
        tenant_id=tenant_id,
        phone=phone,
        real_name=user_in.real_name,
        role=normalize_role(role),
        is_tenant_admin=is_tenant_admin,
        password_hash=get_password_hash(password),
        status=status,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def generate_system_password() -> str:
    password = f"sys{token_hex(24)}1"
    return enforce_password(password)


def mark_user_logged_in(db: Session, *, user: User) -> User:
    now = datetime.now(timezone.utc)
    user.previous_login_at = user.last_login_at
    user.last_login_at = now
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
            .filter(Tenant.tenant_code == tenant_code, Tenant.status == int(TenantStatus.ACTIVE))
            .first()
        )

    tenants = (
        db.query(Tenant)
        .filter(Tenant.status == int(TenantStatus.ACTIVE))
        .order_by(Tenant.id.asc())
        .all()
    )
    if len(tenants) == 1:
        return tenants[0]
    return None
