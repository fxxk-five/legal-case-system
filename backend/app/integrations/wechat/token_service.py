from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import status
from jose import JWTError, jwt

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.security import create_access_token


WECHAT_LOGIN_TICKET_ERROR_MESSAGE = "微信登录凭证已失效，请重新发起登录。"
CASE_INVITE_TOKEN_ERROR_MESSAGE = "案件邀请链接无效或已过期。"


def create_wechat_login_ticket_payload(
    *,
    openid: str,
    unionid: str | None,
    scene: str,
    expire_minutes: int,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": f"wx-mini:{openid}",
        "scene": scene,
        "openid": openid,
        "exp": now + timedelta(minutes=expire_minutes),
        "iat": now,
    }
    if unionid:
        payload["unionid"] = unionid
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_wechat_login_ticket_payload(*, ticket: str, scene: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(ticket, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.AUTH_REQUIRED,
            message=WECHAT_LOGIN_TICKET_ERROR_MESSAGE,
            detail=WECHAT_LOGIN_TICKET_ERROR_MESSAGE,
        ) from exc

    if payload.get("scene") != scene:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.AUTH_REQUIRED,
            message=WECHAT_LOGIN_TICKET_ERROR_MESSAGE,
            detail=WECHAT_LOGIN_TICKET_ERROR_MESSAGE,
        )
    return payload


def create_case_invite_token_payload(case_id: int, tenant_id: int) -> str:
    return create_access_token(
        subject=f"case-invite:{case_id}",
        expires_delta=timedelta(days=7),
        extra_data={"case_id": case_id, "tenant_id": tenant_id, "scene": "client_case_entry"},
    )


def decode_case_invite_token_payload(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.INVITE_INVALID,
            message=CASE_INVITE_TOKEN_ERROR_MESSAGE,
            detail=CASE_INVITE_TOKEN_ERROR_MESSAGE,
        ) from exc

    if payload.get("scene") != "client_case_entry":
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.INVITE_INVALID,
            message=CASE_INVITE_TOKEN_ERROR_MESSAGE,
            detail=CASE_INVITE_TOKEN_ERROR_MESSAGE,
        )

    case_id = payload.get("case_id")
    tenant_id = payload.get("tenant_id")
    if not isinstance(case_id, int) or not isinstance(tenant_id, int):
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.INVITE_INVALID,
            message=CASE_INVITE_TOKEN_ERROR_MESSAGE,
            detail=CASE_INVITE_TOKEN_ERROR_MESSAGE,
        )
    return payload
