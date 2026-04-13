from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import status

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.validators import PHONE_REGEX
from app.integrations.wechat.token_service import (
    create_case_invite_token_payload,
    create_wechat_login_ticket_payload,
    decode_case_invite_token_payload,
    decode_wechat_login_ticket_payload,
)


WECHAT_LOGIN_TICKET_SCENE = "wx_mini_login_ticket"
WECHAT_LOGIN_TICKET_EXPIRE_MINUTES = 10
_WECHAT_ACCESS_TOKEN_CACHE: dict[str, Any] = {
    "value": "",
    "expires_at": 0.0,
}


@dataclass(slots=True)
class WechatMiniIdentity:
    openid: str
    unionid: str | None = None


def _wechat_api_error(message: str, *, status_code: int = status.HTTP_400_BAD_REQUEST) -> AppError:
    return AppError(
        status_code=status_code,
        code=ErrorCode.WECHAT_API_ERROR,
        message=message,
        detail=message,
    )


def _mock_identity_from_code(code: str) -> WechatMiniIdentity:
    digest = hashlib.sha1(code.encode("utf-8")).hexdigest()
    return WechatMiniIdentity(
        openid=f"mock_{digest[:24]}",
        unionid=f"mock_union_{digest[24:40]}",
    )


def _mock_phone_from_code(code: str) -> str:
    normalized = (code or "").strip()
    if PHONE_REGEX.fullmatch(normalized):
        return normalized

    for separator in (":", "|", ",", "_", "-"):
        parts = [part.strip() for part in normalized.split(separator)]
        for part in parts:
            if PHONE_REGEX.fullmatch(part):
                return part

    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()
    digits = "".join(str(int(char, 16) % 10) for char in digest[:9])
    return f"13{digits}"


def _load_json_response(request: Request) -> dict[str, Any]:
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # pragma: no cover
        raise _wechat_api_error("Failed to call WeChat API.", status_code=status.HTTP_502_BAD_GATEWAY) from exc


def _load_binary_response(request: Request) -> tuple[bytes, str]:
    try:
        with urlopen(request, timeout=10) as response:
            content_type = response.headers.get("Content-Type") or "application/octet-stream"
            return response.read(), content_type
    except Exception as exc:  # pragma: no cover
        raise _wechat_api_error("Failed to call WeChat API.", status_code=status.HTTP_502_BAD_GATEWAY) from exc


def _require_wechat_app_credentials() -> None:
    if settings.WECHAT_MINIAPP_MOCK_LOGIN:
        return
    if settings.WECHAT_MINIAPP_APP_ID and settings.WECHAT_MINIAPP_APP_SECRET:
        return
    raise _wechat_api_error("WeChat Mini Program AppID/AppSecret is not configured.")


def _get_wechat_access_token() -> str:
    if settings.WECHAT_MINIAPP_MOCK_LOGIN:
        return "mock-access-token"

    _require_wechat_app_credentials()
    now = time.time()
    cached_token = str(_WECHAT_ACCESS_TOKEN_CACHE.get("value") or "")
    cached_expires_at = float(_WECHAT_ACCESS_TOKEN_CACHE.get("expires_at") or 0.0)
    if cached_token and cached_expires_at - 60 > now:
        return cached_token

    query = urlencode(
        {
            "grant_type": "client_credential",
            "appid": settings.WECHAT_MINIAPP_APP_ID,
            "secret": settings.WECHAT_MINIAPP_APP_SECRET,
        }
    )
    url = f"https://api.weixin.qq.com/cgi-bin/token?{query}"
    payload = _load_json_response(Request(url, method="GET"))
    access_token = str(payload.get("access_token") or "")
    expires_in = int(payload.get("expires_in") or 7200)
    if not access_token:
        message = str(payload.get("errmsg") or "Failed to get WeChat access_token.")
        raise _wechat_api_error(message)

    _WECHAT_ACCESS_TOKEN_CACHE["value"] = access_token
    _WECHAT_ACCESS_TOKEN_CACHE["expires_at"] = now + expires_in
    return access_token


def exchange_code_for_identity(code: str) -> WechatMiniIdentity:
    if settings.WECHAT_MINIAPP_MOCK_LOGIN:
        return _mock_identity_from_code(code)

    _require_wechat_app_credentials()
    query = urlencode(
        {
            "appid": settings.WECHAT_MINIAPP_APP_ID,
            "secret": settings.WECHAT_MINIAPP_APP_SECRET,
            "js_code": code,
            "grant_type": "authorization_code",
        }
    )
    url = f"https://api.weixin.qq.com/sns/jscode2session?{query}"
    payload = _load_json_response(Request(url, method="GET"))

    openid = payload.get("openid")
    if not openid:
        message = str(payload.get("errmsg") or "WeChat login failed.")
        raise _wechat_api_error(message)

    unionid = payload.get("unionid")
    return WechatMiniIdentity(openid=str(openid), unionid=str(unionid) if unionid else None)


def exchange_code_for_openid(code: str) -> str:
    return exchange_code_for_identity(code).openid


def exchange_phone_code_for_phone_number(phone_code: str) -> str:
    if settings.WECHAT_MINIAPP_MOCK_LOGIN:
        return _mock_phone_from_code(phone_code)

    access_token = _get_wechat_access_token()
    url = f"https://api.weixin.qq.com/wxa/business/getuserphonenumber?access_token={access_token}"
    payload = json.dumps({"code": phone_code}).encode("utf-8")
    request = Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    body = _load_json_response(request)

    phone_info = body.get("phone_info") or {}
    phone_number = phone_info.get("purePhoneNumber") or phone_info.get("phoneNumber")
    if not phone_number:
        message = str(body.get("errmsg") or "Failed to get WeChat phone number.")
        raise _wechat_api_error(message)
    return str(phone_number)


def build_mock_mini_program_code_svg(*, title: str, subtitle: str = "", footer: str = "") -> bytes:
    safe_title = (title or "Mock WeChat Code").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_subtitle = (subtitle or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_footer = (footer or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="420" height="420" viewBox="0 0 420 420">
<rect width="420" height="420" rx="24" fill="#ffffff"/>
<rect x="40" y="40" width="340" height="340" rx="20" fill="#0f172a"/>
<rect x="82" y="82" width="256" height="256" rx="16" fill="#f8fafc"/>
<text x="210" y="118" font-size="22" text-anchor="middle" fill="#0f172a" font-family="Arial, sans-serif">{safe_title}</text>
<text x="210" y="210" font-size="18" text-anchor="middle" fill="#475569" font-family="Arial, sans-serif">{safe_subtitle}</text>
<text x="210" y="370" font-size="16" text-anchor="middle" fill="#64748b" font-family="Arial, sans-serif">{safe_footer}</text>
</svg>"""
    return svg.encode("utf-8")


def generate_mini_program_code(*, page: str, scene: str) -> tuple[bytes, str]:
    if settings.WECHAT_MINIAPP_MOCK_LOGIN:
        return (
            build_mock_mini_program_code_svg(
                title="Mock WeChat Scan",
                subtitle=page,
                footer=scene,
            ),
            "image/svg+xml",
        )

    access_token = _get_wechat_access_token()
    url = f"https://api.weixin.qq.com/wxa/getwxacodeunlimit?access_token={access_token}"
    payload = json.dumps(
        {
            "page": page,
            "scene": scene,
            "check_path": False,
        }
    ).encode("utf-8")
    request = Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    content, content_type = _load_binary_response(request)

    if content_type.startswith("application/json"):
        body = json.loads(content.decode("utf-8"))
        message = str(body.get("errmsg") or "Failed to generate WeChat mini-program code.")
        raise _wechat_api_error(message)

    return content, content_type


def create_wechat_login_ticket(identity: WechatMiniIdentity) -> str:
    return create_wechat_login_ticket_payload(
        openid=identity.openid,
        unionid=identity.unionid,
        scene=WECHAT_LOGIN_TICKET_SCENE,
        expire_minutes=WECHAT_LOGIN_TICKET_EXPIRE_MINUTES,
    )


def decode_wechat_login_ticket(ticket: str) -> WechatMiniIdentity:
    payload = decode_wechat_login_ticket_payload(
        ticket=ticket,
        scene=WECHAT_LOGIN_TICKET_SCENE,
    )

    openid = payload.get("openid")
    if not isinstance(openid, str) or not openid.strip():
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.AUTH_REQUIRED,
            message="WeChat login ticket is invalid or expired.",
            detail="WeChat login ticket is invalid or expired.",
        )

    unionid = payload.get("unionid")
    return WechatMiniIdentity(
        openid=openid.strip(),
        unionid=unionid.strip() if isinstance(unionid, str) and unionid.strip() else None,
    )


def create_case_invite_token(case_id: int, tenant_id: int) -> str:
    return create_case_invite_token_payload(case_id=case_id, tenant_id=tenant_id)


def decode_case_invite_token(token: str) -> dict[str, Any]:
    return decode_case_invite_token_payload(token=token)
