#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from uuid import uuid4


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict | None = None,
    token: str = "",
    mini: bool = False,
) -> tuple[int, dict]:
    url = f"{base_url.rstrip('/')}{path}"
    body = None
    headers = {
        "Content-Type": "application/json",
        "X-Request-ID": f"smoke-wechat-{uuid4()}",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if mini:
        headers["X-Client-Platform"] = "mini-program"
        headers["X-Client-Source"] = "wx-mini"
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url, method=method, headers=headers, data=body)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw.decode("utf-8")) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        return exc.code, json.loads(raw.decode("utf-8")) if raw else {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test for mini WeChat direct login flow.")
    parser.add_argument("--base-url", required=True, help="API base URL, e.g. http://127.0.0.1:8000/api/v1")
    parser.add_argument("--phone", required=True, help="Existing account phone")
    parser.add_argument("--password", required=True, help="Existing account password")
    parser.add_argument("--tenant-code", default="", help="Optional tenant_code")
    parser.add_argument("--login-code", default="smoke-wechat-bind-existing", help="Mock/WeChat login code")
    args = parser.parse_args()

    print("[STEP] start wx-mini-login")
    status, login_payload = _request_json(
        args.base_url,
        "/auth/wx-mini-login",
        method="POST",
        payload={"code": args.login_code},
        mini=True,
    )
    _assert(status == 200, f"wx-mini-login failed: {status} {login_payload}")
    _assert(login_payload.get("need_bind_phone") is True, f"unexpected login payload: {login_payload}")
    ticket = str(login_payload.get("wx_session_ticket") or "")
    _assert(ticket, f"wx_session_ticket missing: {login_payload}")
    print("[PASS] got wx_session_ticket")

    print("[STEP] bind existing account")
    bind_payload = {
        "phone": args.phone,
        "password": args.password,
        "wx_session_ticket": ticket,
    }
    if args.tenant_code.strip():
        bind_payload["tenant_code"] = args.tenant_code.strip()
    status, bound_payload = _request_json(
        args.base_url,
        "/auth/wx-mini-bind-existing",
        method="POST",
        payload=bind_payload,
        mini=True,
    )
    _assert(status == 200, f"wx-mini-bind-existing failed: {status} {bound_payload}")
    access_token = str(bound_payload.get("access_token") or "")
    refresh_token = str(bound_payload.get("refresh_token") or "")
    _assert(access_token and refresh_token, f"token missing after bind: {bound_payload}")
    print("[PASS] bind existing account")

    print("[STEP] verify second wx-mini-login direct sign-in")
    status, direct_payload = _request_json(
        args.base_url,
        "/auth/wx-mini-login",
        method="POST",
        payload={"code": args.login_code},
        mini=True,
    )
    _assert(status == 200, f"second wx-mini-login failed: {status} {direct_payload}")
    _assert(direct_payload.get("need_bind_phone") is False, f"expected direct login: {direct_payload}")
    _assert(direct_payload.get("access_token"), f"direct login missing access_token: {direct_payload}")
    print("[PASS] direct sign-in works")

    print("[STEP] logout current session")
    status, _ = _request_json(
        args.base_url,
        "/auth/logout",
        method="POST",
        payload={"refresh_token": refresh_token},
        token=access_token,
        mini=True,
    )
    _assert(status == 204, f"logout failed: {status}")
    print("[PASS] logout current session")

    print("[STEP] verify revoked refresh token cannot be reused")
    status, refresh_payload = _request_json(
        args.base_url,
        "/auth/refresh",
        method="POST",
        payload={"refresh_token": refresh_token},
        mini=True,
    )
    _assert(status == 401, f"revoked refresh token should fail: {status} {refresh_payload}")
    _assert(refresh_payload.get("code") == "AUTH_REQUIRED", f"unexpected refresh payload: {refresh_payload}")
    print("[PASS] revoked refresh token rejected")

    print("[DONE] smoke_wechat_direct_login passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"[FAIL] {exc}")
        raise SystemExit(1)
