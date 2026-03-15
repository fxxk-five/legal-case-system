import hashlib
import json
from datetime import timedelta
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings
from app.core.security import create_access_token


def exchange_code_for_openid(code: str) -> str:
    if settings.WECHAT_MINIAPP_MOCK_LOGIN:
        digest = hashlib.sha1(code.encode("utf-8")).hexdigest()
        return f"mock_{digest[:24]}"

    if not settings.WECHAT_MINIAPP_APP_ID or not settings.WECHAT_MINIAPP_APP_SECRET:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未配置微信小程序 AppID 或 AppSecret。",
        )

    query = urlencode(
        {
            "appid": settings.WECHAT_MINIAPP_APP_ID,
            "secret": settings.WECHAT_MINIAPP_APP_SECRET,
            "js_code": code,
            "grant_type": "authorization_code",
        }
    )
    url = f"https://api.weixin.qq.com/sns/jscode2session?{query}"

    try:
        with urlopen(url, timeout=10) as response:
            payload: dict[str, Any] = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="调用微信登录接口失败。",
        ) from exc

    openid = payload.get("openid")
    if not openid:
        message = payload.get("errmsg") or "微信登录失败。"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    return str(openid)


def create_case_invite_token(case_id: int, tenant_id: int) -> str:
    return create_access_token(
        subject=f"case-invite:{case_id}",
        expires_delta=timedelta(days=7),
        extra_data={"case_id": case_id, "tenant_id": tenant_id, "scene": "client_case_entry"},
    )


def decode_case_invite_token(token: str) -> dict[str, Any]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="案件邀请令牌无效或已过期。",
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise credentials_exception from exc

    if payload.get("scene") != "client_case_entry":
        raise credentials_exception

    case_id = payload.get("case_id")
    tenant_id = payload.get("tenant_id")
    if not isinstance(case_id, int) or not isinstance(tenant_id, int):
        raise credentials_exception
    return payload
