from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db, set_current_tenant_context
from app.models.user import User
from app.schemas.auth import TokenPayload


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="登录状态无效，请重新登录。",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(
            sub=payload.get("sub"),
            tenant_id=payload.get("tenant_id"),
            role=payload.get("role"),
            is_tenant_admin=payload.get("is_tenant_admin"),
        )
    except JWTError as exc:
        raise credentials_exception from exc

    if token_data.sub is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(token_data.sub)).first()
    if user is None:
        raise credentials_exception
    if user.status != 1:
        raise credentials_exception
    if token_data.tenant_id is not None and user.tenant_id != token_data.tenant_id:
        raise credentials_exception
    set_current_tenant_context(db, user.tenant_id)
    return user


def require_tenant_admin(current_user: User = Depends(get_current_user)) -> User:
    if not (current_user.is_tenant_admin or current_user.role == "tenant_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要租户管理员权限。",
        )
    return current_user
