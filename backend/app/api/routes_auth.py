from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db.session import get_db
from app.models.case import Case
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import (
    Token,
    UserLogin,
    UserRead,
    UserRegister,
    WechatMiniBind,
    WechatMiniLogin,
    WechatMiniLoginResult,
)
from app.schemas.invite import InviteRegister
from app.services.auth import authenticate_user, create_user
from app.services.invite import get_valid_invite
from app.services.mini_program import decode_case_invite_token, exchange_code_for_openid


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


@router.post("/wx-mini-login", response_model=WechatMiniLoginResult)
def wx_mini_login(login_in: WechatMiniLogin, db: Session = Depends(get_db)) -> WechatMiniLoginResult:
    openid = exchange_code_for_openid(login_in.code)
    user = db.query(User).filter(User.wechat_openid == openid).first()
    if user is None:
        return WechatMiniLoginResult(wechat_openid=openid, need_bind_phone=True)

    if user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="当前账号未激活，请联系管理员。",
        )

    return WechatMiniLoginResult(
        access_token=create_access_token(
            user.id,
            extra_data={"tenant_id": user.tenant_id, "role": user.role},
        ),
        wechat_openid=openid,
        need_bind_phone=False,
        user=user,
    )


@router.post("/wx-mini-bind", response_model=WechatMiniLoginResult)
def wx_mini_bind(bind_in: WechatMiniBind, db: Session = Depends(get_db)) -> WechatMiniLoginResult:
    existing_openid_user = db.query(User).filter(User.wechat_openid == bind_in.wechat_openid).first()
    if existing_openid_user is not None:
        if existing_openid_user.status != 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="当前微信账号绑定的用户未激活。",
            )
        return WechatMiniLoginResult(
            access_token=create_access_token(
                existing_openid_user.id,
                extra_data={
                    "tenant_id": existing_openid_user.tenant_id,
                    "role": existing_openid_user.role,
                },
            ),
            wechat_openid=bind_in.wechat_openid,
            need_bind_phone=False,
            user=existing_openid_user,
        )

    invite_payload = None
    tenant_id = bind_in.tenant_id
    if bind_in.case_invite_token:
        invite_payload = decode_case_invite_token(bind_in.case_invite_token)
        tenant_id = int(invite_payload["tenant_id"])

    if tenant_id is None:
        tenant_id = 1

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="目标租户不存在。")

    user = db.query(User).filter(User.tenant_id == tenant_id, User.phone == bind_in.phone).first()
    if user is not None:
        if bind_in.password is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="绑定已有账号时必须输入密码。",
            )
        authenticated_user = authenticate_user(db, phone=bind_in.phone, password=bind_in.password)
        if authenticated_user is None or authenticated_user.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="手机号或密码错误，无法绑定微信。",
            )
    else:
        password = bind_in.password or "client123456"
        real_name = bind_in.real_name or ("当事人" if bind_in.role == "client" else "未命名用户")
        user = create_user(
            db,
            user_in=UserRegister(phone=bind_in.phone, password=password, real_name=real_name),
            tenant_id=tenant_id,
            role=bind_in.role,
            status=1 if bind_in.role == "client" else 0,
        )

    user.wechat_openid = bind_in.wechat_openid
    if bind_in.real_name and not user.real_name:
        user.real_name = bind_in.real_name
    db.add(user)

    if invite_payload is not None:
        case = (
            db.query(Case)
            .filter(Case.id == int(invite_payload["case_id"]), Case.tenant_id == tenant_id)
            .first()
        )
        if case is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="案件不存在。")
        case.client_id = user.id
        db.add(case)

    db.commit()
    db.refresh(user)

    return WechatMiniLoginResult(
        access_token=create_access_token(
            user.id,
            extra_data={"tenant_id": user.tenant_id, "role": user.role},
        ),
        wechat_openid=bind_in.wechat_openid,
        need_bind_phone=False,
        user=user,
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
