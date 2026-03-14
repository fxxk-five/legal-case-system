from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import Token, UserLogin, UserRead, UserRegister
from app.services.auth import authenticate_user, create_user


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
