from fastapi import Depends, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.security import ACCESS_TOKEN_TYPE
from app.core.roles import is_super_admin_role, is_tenant_admin_role, normalize_role
from app.core.statuses import is_active_user_status
from app.db.session import get_db, set_current_tenant_context
from app.models.user import User
from app.schemas.auth import TokenPayload


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def _auth_required(message: str = "登录状态无效，请重新登录。") -> AppError:
    return AppError(
        status_code=status.HTTP_401_UNAUTHORIZED,
        code=ErrorCode.AUTH_REQUIRED,
        message=message,
        detail=message,
    )


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(
            sub=payload.get("sub"),
            tenant_id=payload.get("tenant_id"),
            role=payload.get("role"),
            is_tenant_admin=payload.get("is_tenant_admin"),
            token_type=payload.get("token_type"),
        )
    except JWTError as exc:
        raise _auth_required() from exc

    if token_data.sub is None:
        raise _auth_required()
    if token_data.token_type != ACCESS_TOKEN_TYPE:
        raise _auth_required("登录状态无效，请重新登录。")

    user = db.query(User).filter(User.id == int(token_data.sub)).first()
    if user is None:
        raise _auth_required("用户不存在或已失效，请重新登录。")
    if not is_active_user_status(user.status):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.FORBIDDEN,
            message="当前账号已被禁用或未激活。",
            detail="当前账号已被禁用或未激活。",
        )
    if token_data.tenant_id is not None and user.tenant_id != token_data.tenant_id:
        raise _auth_required("租户鉴权失败，请重新登录。")

    user.role = normalize_role(user.role)
    set_current_tenant_context(
        db,
        user.tenant_id,
        is_super_admin=is_super_admin_role(user.role),
    )
    return user


def require_tenant_admin(current_user: User = Depends(get_current_user)) -> User:
    if not is_tenant_admin_role(current_user.role, is_tenant_admin=current_user.is_tenant_admin):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.FORBIDDEN,
            message="需要租户管理员权限。",
            detail="需要租户管理员权限。",
        )
    return current_user


def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    if not is_super_admin_role(current_user.role):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.FORBIDDEN,
            message="需要超级管理员权限。",
            detail="需要超级管理员权限。",
        )
    return current_user


def _is_mini_program_request(request: Request) -> bool:
    platform = (request.headers.get("X-Client-Platform") or "").strip().lower()
    source = (request.headers.get("X-Client-Source") or "").strip().lower()
    return platform == "mini-program" and source in {"wx-mini", "mini-program"}


def require_mini_program_source(request: Request) -> None:
    if not _is_mini_program_request(request):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.FORBIDDEN,
            message="该接口仅允许小程序端发起。",
            detail="该接口仅允许小程序端发起。",
        )


def require_client_mini_program_source(request: Request, current_user: User = Depends(get_current_user)) -> None:
    if current_user.role == "client" and not _is_mini_program_request(request):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.FORBIDDEN,
            message="当事人仅允许在小程序端访问该接口。",
            detail="当事人仅允许在小程序端访问该接口。",
        )
