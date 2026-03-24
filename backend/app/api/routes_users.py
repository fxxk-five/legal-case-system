from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.statuses import UserStatus, can_transition_user_status
from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_super_admin, require_tenant_admin
from app.models.user import User
from app.schemas.auth import UserRead
from app.schemas.invite import InviteCreateResponse
from app.schemas.user import LawyerCreate, UserStatusUpdate, UserSummary
from app.services.invite import create_lawyer_invite


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
    _ = (lawyer_in, current_user, db)
    # 保留路由以兼容旧前端，但业务上强制走“邀请注册 + 管理员审批”。
    raise AppError(
        status_code=status.HTTP_400_BAD_REQUEST,
        code=ErrorCode.INVITE_REQUIRED,
        message="机构律师仅支持邀请注册，请改用邀请链接。",
        detail="机构律师仅支持邀请注册，请改用邀请链接。",
    )


@router.post("/invite-lawyer", response_model=InviteCreateResponse, status_code=status.HTTP_201_CREATED)
def invite_lawyer(
    current_user: User = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
) -> InviteCreateResponse:
    invite = create_lawyer_invite(
        db,
        tenant_id=current_user.tenant_id,
        invited_by_user_id=current_user.id,
    )
    return InviteCreateResponse(
        token=invite.token,
        register_path=f"pages/login/index?scene=lawyer-invite&token={invite.token}",
        expires_at=invite.expires_at,
    )


@router.get("/pending", response_model=list[UserSummary])
def list_pending_users(
    current_user: User = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
) -> list[User]:
    return (
        db.query(User)
        .filter(
            User.tenant_id == current_user.tenant_id,
            User.role.in_(["lawyer", "tenant_admin"]),
            User.status == int(UserStatus.PENDING_APPROVAL),
        )
        .order_by(User.created_at.desc())
        .all()
    )


@router.patch("/{user_id}/approve", response_model=UserSummary)
def approve_user(
    user_id: int,
    current_user: User = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
) -> User:
    user = (
        db.query(User)
        .filter(User.id == user_id, User.tenant_id == current_user.tenant_id)
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
    return user


@router.delete("/{user_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
def reject_user(
    user_id: int,
    current_user: User = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
) -> None:
    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.tenant_id == current_user.tenant_id,
            User.status == int(UserStatus.PENDING_APPROVAL),
        )
        .first()
    )
    if user is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.USER_NOT_FOUND,
            message="待审批用户不存在。",
            detail="待审批用户不存在。",
        )

    db.delete(user)
    db.commit()
    return None


@router.patch("/{user_id}/status", response_model=UserSummary)
def update_user_status(
    user_id: int,
    user_in: UserStatusUpdate,
    current_user: User = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
) -> User:
    user = (
        db.query(User)
        .filter(User.id == user_id, User.tenant_id == current_user.tenant_id)
        .first()
    )
    if user is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.USER_NOT_FOUND,
            message="用户不存在。",
            detail="用户不存在。",
        )

    if user.status != user_in.status and not can_transition_user_status(user.status, user_in.status):
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.CONFLICT,
            message="成员状态流转不合法。",
            detail="成员状态流转不合法。",
        )

    user.status = user_in.status
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=list[UserSummary])
def list_all_users(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> list[User]:
    return db.query(User).order_by(User.id.asc()).all()
