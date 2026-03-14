from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db.session import get_db
from app.models.invite import Invite
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import Token, UserLogin, UserRead, UserRegister
from app.schemas.invite import InviteRegister
from app.services.auth import authenticate_user, create_user
from app.services.invite import get_valid_invite


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserRegister, db: Session = Depends(get_db)) -> User:
    tenant = db.query(Tenant).filter(Tenant.id == 1).first()
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="默认租户不存在，请先执行初始化脚本。",
        )

    existing_user = (
        db.query(User)
        .filter(User.tenant_id == tenant.id, User.phone == user_in.phone)
        .first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该手机号已注册。",
        )

    return create_user(db, user_in=user_in, tenant_id=tenant.id)


@router.post("/login", response_model=Token)
def login(user_in: UserLogin, db: Session = Depends(get_db)) -> Token:
    user = authenticate_user(db, phone=user_in.phone, password=user_in.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="手机号或密码错误。",
        )

    return Token(
        access_token=create_access_token(
            user.id,
            extra_data={"tenant_id": user.tenant_id, "role": user.role},
        )
    )


@router.post("/invite-register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user_by_invite(invite_in: InviteRegister, db: Session = Depends(get_db)) -> User:
    invite = get_valid_invite(db, token=invite_in.token)

    existing_user = (
        db.query(User)
        .filter(User.tenant_id == invite.tenant_id, User.phone == invite_in.phone)
        .first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该手机号已存在于当前租户。",
        )

    user = create_user(
        db,
        user_in=UserRegister(
            phone=invite_in.phone,
            password=invite_in.password,
            real_name=invite_in.real_name,
        ),
        tenant_id=invite.tenant_id,
        role=invite.role,
        status=0,
    )

    invite.status = "used"
    db.add(invite)
    db.commit()

    return user
