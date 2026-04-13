from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.roles import role_values_for_query
from app.db.session import get_db
from app.modules.auth.deps import (
    get_current_user_allow_pending,
    require_super_admin,
    require_tenant_admin,
)
from app.models.user import User
from app.modules.auth.schemas import UserRead
from app.modules.invites.schemas import InviteCreateResponse
from app.modules.users.schemas import LawyerCreate, UserStatusUpdate, UserSummary
from app.modules.users.service import UsersService


router = APIRouter(prefix="/users", tags=["Users"])


def _users_service(db: Session) -> UsersService:
    return UsersService(db)


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user_allow_pending)) -> User:
    return current_user


@router.get("/lawyers", response_model=list[UserSummary])
def list_lawyers(
    current_user: User = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
) -> list[User]:
    return _users_service(db).list_lawyers(
        current_user=current_user,
    )


@router.post("/lawyers", response_model=UserSummary, status_code=status.HTTP_201_CREATED)
def create_lawyer(
    lawyer_in: LawyerCreate,
    current_user: User = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
) -> User:
    return _users_service(db).reject_direct_lawyer_creation(
        lawyer_in=lawyer_in,
        current_user=current_user,
    )


@router.post("/invite-lawyer", response_model=InviteCreateResponse, status_code=status.HTTP_201_CREATED)
def invite_lawyer(
    current_user: User = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
) -> InviteCreateResponse:
    return _users_service(db).invite_lawyer(
        current_user=current_user,
    )


@router.get("/pending", response_model=list[UserSummary])
def list_pending_users(
    current_user: User = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
) -> list[User]:
    return _users_service(db).list_pending_users(
        current_user=current_user,
    )


@router.patch("/{user_id}/approve", response_model=UserSummary)
def approve_user(
    user_id: int,
    current_user: User = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
) -> User:
    return _users_service(db).approve_user(
        user_id=user_id,
        current_user=current_user,
        roles=role_values_for_query("lawyer", "tenant_admin"),
    )


@router.delete("/{user_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
def reject_user(
    user_id: int,
    current_user: User = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
) -> None:
    _users_service(db).reject_user(
        user_id=user_id,
        current_user=current_user,
    )
    return None


@router.patch("/{user_id}/status", response_model=UserSummary)
def update_user_status(
    user_id: int,
    user_in: UserStatusUpdate,
    current_user: User = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
) -> User:
    return _users_service(db).update_user_status(
        user_id=user_id,
        user_in=user_in,
        current_user=current_user,
    )


@router.get("", response_model=list[UserSummary])
def list_all_users(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> list[User]:
    _ = current_user
    return _users_service(db).list_all_users()

