from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_tenant_admin
from app.models.user import User
from app.schemas.auth import UserRegister
from app.schemas.user import LawyerCreate, UserSummary
from app.services.auth import create_user
from app.schemas.auth import UserRead


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get("/lawyers", response_model=list[UserSummary])
def list_lawyers(
    current_user: User = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
) -> list[User]:
    return (
        db.query(User)
        .filter(
            User.tenant_id == current_user.tenant_id,
            User.role.in_(["lawyer", "tenant_admin"]),
        )
        .order_by(User.created_at.desc())
        .all()
    )


@router.post("/lawyers", response_model=UserSummary, status_code=status.HTTP_201_CREATED)
def create_lawyer(
    lawyer_in: LawyerCreate,
    current_user: User = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
) -> User:
    existing_user = (
        db.query(User)
        .filter(User.tenant_id == current_user.tenant_id, User.phone == lawyer_in.phone)
        .first()
    )
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该手机号已存在。")

    return create_user(
        db,
        user_in=UserRegister(
            phone=lawyer_in.phone,
            password=lawyer_in.password,
            real_name=lawyer_in.real_name,
        ),
        tenant_id=current_user.tenant_id,
        role=lawyer_in.role,
        is_tenant_admin=lawyer_in.role == "tenant_admin",
    )
