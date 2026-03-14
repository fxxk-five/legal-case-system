from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.auth import UserRegister


def authenticate_user(db: Session, *, phone: str, password: str) -> User | None:
    user = db.query(User).filter(User.phone == phone).first()
    if not user or user.status != 1 or not verify_password(password, user.password_hash):
        return None
    return user


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
