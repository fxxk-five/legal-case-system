#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from uuid import uuid4


def _request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    token: str = "",
    payload: dict | None = None,
    mini: bool = False,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict]:
    url = f"{base_url.rstrip('/')}{path}"
    body = None
    merged_headers = {
        "Content-Type": "application/json",
        "X-Request-ID": f"qa02-{uuid4()}",
    }
    if token:
        merged_headers["Authorization"] = f"Bearer {token}"
    if mini:
        merged_headers["X-Client-Platform"] = "mini-program"
        merged_headers["X-Client-Source"] = "wx-mini"
    if headers:
        merged_headers.update(headers)
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url, method=method, headers=merged_headers, data=body)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
            parsed = json.loads(data.decode("utf-8")) if data else {}
            return resp.status, parsed
    except urllib.error.HTTPError as exc:
        data = exc.read()
        parsed = json.loads(data.decode("utf-8")) if data else {}
        return exc.code, parsed


def _request_bytes(
    base_url: str,
    path: str,
    *,
    token: str = "",
    mini: bool = False,
) -> tuple[int, dict[str, str], bytes]:
    url = f"{base_url.rstrip('/')}{path}"
    headers = {"X-Request-ID": f"qa02-{uuid4()}"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if mini:
        headers["X-Client-Platform"] = "mini-program"
        headers["X-Client-Source"] = "wx-mini"
    req = urllib.request.Request(url, method="GET", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, dict(resp.headers.items()), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers.items()), exc.read()


def _build_multipart(file_path: Path, field_name: str = "upload") -> tuple[bytes, str]:
    boundary = f"----qa02-boundary-{uuid4().hex}"
    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    file_bytes = file_path.read_bytes()
    parts = []
    parts.append(f"--{boundary}\r\n".encode("utf-8"))
    parts.append(
        (
            f'Content-Disposition: form-data; name="{field_name}"; filename="{file_path.name}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("utf-8")
    )
    parts.append(file_bytes)
    parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), boundary


def _upload_case_file(base_url: str, *, case_id: int, token: str, file_path: Path) -> tuple[int, dict]:
    path = f"/cases/{case_id}/files"
    url = f"{base_url.rstrip('/')}{path}"
    body, boundary = _build_multipart(file_path)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Request-ID": f"qa02-{uuid4()}",
        "X-Client-Platform": "mini-program",
        "X-Client-Source": "wx-mini",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    req = urllib.request.Request(url, method="POST", headers=headers, data=body)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _assert_has_keys(payload: dict, keys: list[str], label: str) -> None:
    missing = [key for key in keys if key not in payload]
    _assert(not missing, f"{label} missing keys: {missing} payload={payload}")


def _login(base_url: str, *, phone: str, password: str, tenant_code: str = "") -> dict:
    payload: dict[str, str | None] = {"phone": phone, "password": password}
    if tenant_code:
        payload["tenant_code"] = tenant_code
    status, data = _request_json(base_url, "/auth/login", method="POST", payload=payload)
    _assert(status == 200, f"Login failed for {phone}: {status} {data}")
    _assert(bool(data.get("access_token")), f"Login missing access token for {phone}")
    _assert(bool(data.get("refresh_token")), f"Login missing refresh token for {phone}")
    return data


def _wait_case_analysis_terminal(base_url: str, *, case_id: int, token: str, timeout_seconds: int = 300) -> dict:
    deadline = time.time() + timeout_seconds
    latest: dict = {}
    while time.time() < deadline:
        status, payload = _request_json(base_url, f"/cases/{case_id}", token=token)
        _assert(status == 200, f"Get case failed while polling analysis: {status} {payload}")
        latest = payload
        analysis_status = str(payload.get("analysis_status") or "").lower()
        if analysis_status in {"completed", "failed", "dead"}:
            return payload
        time.sleep(2)
    return latest


def main() -> int:
    parser = argparse.ArgumentParser(description="QA02 full E2E: create -> invite -> client upload -> analyze -> report.")
    parser.add_argument("--base-url", required=True, help="API base URL, e.g. http://127.0.0.1:8000/api/v1")
    parser.add_argument("--lawyer-phone", default="13900000011")
    parser.add_argument("--lawyer-password", default="lawyer123456")
    parser.add_argument("--tenant-code", default="")
    parser.add_argument("--client-phone", default="")
    parser.add_argument("--client-name", default="QA02 自动化当事人")
    parser.add_argument("--client-password", default="client123456")
    parser.add_argument("--legal-type", default="civil_loan")
    parser.add_argument("--file-path", default="upload-smoke.txt")
    parser.add_argument("--timeout-seconds", type=int, default=300)
    args = parser.parse_args()

    file_path = Path(args.file_path)
    _assert(file_path.exists() and file_path.is_file(), f"File not found: {file_path}")

    client_phone = args.client_phone.strip() or f"139{int(time.time()) % 10_000_0000:08d}"
    case_title = f"QA02 全链路案件 {uuid4().hex[:8]}"

    print("[STEP] lawyer login")
    lawyer_login = _login(
        args.base_url,
        phone=args.lawyer_phone.strip(),
        password=args.lawyer_password,
        tenant_code=args.tenant_code.strip(),
    )
    lawyer_token = lawyer_login["access_token"]
    lawyer_refresh = lawyer_login["refresh_token"]
    print("[PASS] lawyer login")

    print("[STEP] verify profile + dashboard")
    status, lawyer_profile = _request_json(args.base_url, "/users/me", token=lawyer_token)
    _assert(status == 200, f"Get current lawyer failed: {status} {lawyer_profile}")
    _assert(str(lawyer_profile.get("phone") or "") == args.lawyer_phone.strip(), f"Unexpected lawyer profile: {lawyer_profile}")

    status, dashboard_payload = _request_json(args.base_url, "/stats/dashboard", token=lawyer_token)
    _assert(status == 200, f"Get dashboard stats failed: {status} {dashboard_payload}")
    _assert_has_keys(
        dashboard_payload,
        [
            "case_total",
            "client_total",
            "case_in_progress",
            "lawyer_count",
            "has_login_baseline",
            "delta_case_count",
            "delta_file_count",
            "delta_deadline_risk_count",
        ],
        "dashboard stats",
    )
    can_manage_members = bool(lawyer_profile.get("is_tenant_admin")) or str(lawyer_profile.get("role") or "") in {
        "tenant_admin",
        "super_admin",
    }
    print("[PASS] profile + dashboard")

    if can_manage_members:
        print("[STEP] verify lawyer management endpoints")
        status, lawyers_payload = _request_json(args.base_url, "/users/lawyers", token=lawyer_token)
        _assert(status == 200 and isinstance(lawyers_payload, list), f"List lawyers failed: {status} {lawyers_payload}")
        _assert(
            any(str(item.get("phone") or "") == args.lawyer_phone.strip() for item in lawyers_payload),
            f"Current lawyer not found in lawyer list: {lawyers_payload}",
        )
        status, pending_payload = _request_json(args.base_url, "/users/pending", token=lawyer_token)
        _assert(status == 200 and isinstance(pending_payload, list), f"List pending lawyers failed: {status} {pending_payload}")
        status, invite_lawyer_payload = _request_json(
            args.base_url,
            "/users/invite-lawyer",
            method="POST",
            token=lawyer_token,
        )
        _assert(status == 201, f"Invite lawyer failed: {status} {invite_lawyer_payload}")
        _assert(bool(invite_lawyer_payload.get("token")), f"Invite lawyer token missing: {invite_lawyer_payload}")
        _assert(
            str(invite_lawyer_payload.get("register_path") or "").startswith("/api/v1/auth/invite-register?token="),
            f"Invite lawyer register_path invalid: {invite_lawyer_payload}",
        )
        print("[PASS] lawyer management endpoints")
    else:
        print("[INFO] current lawyer is not tenant admin; skip lawyer management endpoint checks")

    print("[STEP] create case")
    case_payload = {
        "title": case_title,
        "legal_type": args.legal_type,
        "client_phone": client_phone,
        "client_real_name": args.client_name,
    }
    status, created_case = _request_json(args.base_url, "/cases", method="POST", token=lawyer_token, payload=case_payload)
    _assert(status == 201, f"Create case failed: {status} {created_case}")
    case_id = int(created_case["id"])
    print(f"[PASS] create case id={case_id} phone={client_phone}")

    print("[STEP] verify case detail + client management")
    status, lawyer_case_detail = _request_json(args.base_url, f"/cases/{case_id}", token=lawyer_token)
    _assert(status == 200, f"Get created case failed: {status} {lawyer_case_detail}")
    _assert(str(lawyer_case_detail.get("legal_type") or "") == args.legal_type, f"Case legal_type mismatch: {lawyer_case_detail}")
    _assert(
        str(((lawyer_case_detail.get("client") or {}).get("phone")) or "") == client_phone,
        f"Case client phone mismatch: {lawyer_case_detail}",
    )

    status, clients_payload = _request_json(
        args.base_url,
        f"/clients?sort_by=created_at&sort_order=desc&q={urllib.parse.quote(client_phone)}",
        token=lawyer_token,
    )
    _assert(status == 200 and isinstance(clients_payload, list), f"List clients failed: {status} {clients_payload}")
    matched_client = next((item for item in clients_payload if str(item.get("phone") or "") == client_phone), None)
    _assert(matched_client is not None, f"Created client not found in /clients: {clients_payload}")
    client_id = int(matched_client["id"])

    status, client_detail_payload = _request_json(args.base_url, f"/clients/{client_id}", token=lawyer_token)
    _assert(status == 200, f"Get client detail failed: {status} {client_detail_payload}")
    detail_cases = client_detail_payload.get("cases") or []
    _assert(
        any(int(item.get("id")) == case_id for item in detail_cases if item.get("id") is not None),
        f"Created case not found in client detail: {client_detail_payload}",
    )
    patched_name = f"{args.client_name}-V3"
    status, patched_client_payload = _request_json(
        args.base_url,
        f"/clients/{client_id}",
        method="PATCH",
        token=lawyer_token,
        payload={"real_name": patched_name, "phone": client_phone},
    )
    _assert(status == 200, f"Patch client failed: {status} {patched_client_payload}")
    _assert(str(patched_client_payload.get("real_name") or "") == patched_name, f"Patch client name mismatch: {patched_client_payload}")
    print("[PASS] case detail + client management")

    print("[STEP] generate invite token")
    status, invite_payload = _request_json(
        args.base_url,
        f"/cases/{case_id}/invite-qrcode",
        token=lawyer_token,
        mini=True,
    )
    _assert(status == 200, f"Invite generation failed: {status} {invite_payload}")
    _assert(bool(invite_payload.get("token")), f"Invite token missing: {invite_payload}")
    _assert(
        str(invite_payload.get("path") or "").startswith("pages/client/entry?token="),
        f"Invite path invalid for mini-program: {invite_payload}",
    )
    print("[PASS] invite token generated")

    print("[STEP] client login")
    client_login = _login(
        args.base_url,
        phone=client_phone,
        password=args.client_password,
        tenant_code=args.tenant_code.strip(),
    )
    client_token = client_login["access_token"]
    print("[PASS] client login")

    print("[STEP] verify client case visibility")
    status, client_cases_payload = _request_json(args.base_url, "/cases", token=client_token)
    _assert(status == 200 and isinstance(client_cases_payload, list), f"Client list cases failed: {status} {client_cases_payload}")
    _assert(len(client_cases_payload) == 1, f"Client should see exactly one case: {client_cases_payload}")
    _assert(int(client_cases_payload[0]["id"]) == case_id, f"Client visible case mismatch: {client_cases_payload}")
    print("[PASS] client case visibility")

    print("[STEP] client upload supplemental file")
    upload_status, upload_payload = _upload_case_file(
        args.base_url,
        case_id=case_id,
        token=client_token,
        file_path=file_path,
    )
    _assert(upload_status == 201, f"Client upload failed: {upload_status} {upload_payload}")
    _assert(upload_payload.get("id"), f"Upload response missing file id: {upload_payload}")
    print(f"[PASS] client upload file_id={upload_payload['id']}")

    print("[STEP] wait analysis terminal")
    case_terminal = _wait_case_analysis_terminal(
        args.base_url,
        case_id=case_id,
        token=lawyer_token,
        timeout_seconds=args.timeout_seconds,
    )
    _assert(str(case_terminal.get("analysis_status") or "").lower() == "completed", f"Analysis not completed: {case_terminal}")
    print("[PASS] analysis completed")

    print("[STEP] verify client detail + timeline")
    status, client_case_detail = _request_json(args.base_url, f"/cases/{case_id}", token=client_token)
    _assert(status == 200, f"Get client case detail failed: {status} {client_case_detail}")
    _assert(str(client_case_detail.get("analysis_status") or "").lower() == "completed", f"Client case analysis not completed: {client_case_detail}")
    timeline_items = client_case_detail.get("timeline") or []
    _assert(isinstance(timeline_items, list) and len(timeline_items) >= 1, f"Client timeline missing: {client_case_detail}")
    print("[PASS] client detail + timeline")

    print("[STEP] verify analysis results")
    status, result_payload = _request_json(args.base_url, f"/ai/cases/{case_id}/analysis-results", token=lawyer_token)
    _assert(status == 200, f"Get analysis results failed: {status} {result_payload}")
    items = result_payload.get("items") or []
    _assert(len(items) >= 1, f"No analysis results found: {result_payload}")
    print(f"[PASS] analysis results count={len(items)}")

    print("[STEP] verify analytics console endpoints")
    status, usage_payload = _request_json(args.base_url, "/analytics/ai-usage", token=lawyer_token)
    _assert(status == 200, f"Get AI usage failed: {status} {usage_payload}")
    _assert_has_keys(
        usage_payload,
        ["day", "week", "month", "task_type_breakdown", "status_breakdown", "model_breakdown"],
        "AI usage",
    )

    status, prompts_payload = _request_json(args.base_url, "/analytics/prompts", token=lawyer_token)
    _assert(status == 200, f"Get prompts failed: {status} {prompts_payload}")
    _assert_has_keys(prompts_payload, ["parse_prompt", "analyze_prompt", "falsify_prompt"], "prompt settings")

    status, prompts_save_payload = _request_json(
        args.base_url,
        "/analytics/prompts",
        method="PUT",
        token=lawyer_token,
        payload={
            "parse_prompt": prompts_payload.get("parse_prompt", ""),
            "analyze_prompt": prompts_payload.get("analyze_prompt", ""),
            "falsify_prompt": prompts_payload.get("falsify_prompt", ""),
        },
    )
    _assert(status == 200, f"Save prompts failed: {status} {prompts_save_payload}")

    status, provider_payload = _request_json(args.base_url, "/analytics/provider-settings", token=lawyer_token)
    _assert(status == 200, f"Get provider settings failed: {status} {provider_payload}")
    _assert_has_keys(provider_payload, ["provider_type", "base_url", "model", "editable", "locked"], "provider settings")
    if provider_payload.get("editable"):
        status, provider_save_payload = _request_json(
            args.base_url,
            "/analytics/provider-settings",
            method="PUT",
            token=lawyer_token,
            payload={
                "provider_type": provider_payload.get("provider_type", "openai_compatible"),
                "base_url": provider_payload.get("base_url", ""),
                "model": provider_payload.get("model", ""),
                "api_key": None,
            },
        )
        _assert(status == 200, f"Save provider settings failed: {status} {provider_save_payload}")

    status, task_list_payload = _request_json(
        args.base_url,
        "/ai/tasks?page=1&page_size=20",
        token=lawyer_token,
    )
    _assert(status == 200, f"List AI tasks failed: {status} {task_list_payload}")
    task_items = task_list_payload.get("items") or []
    _assert(any(int(item.get("case_id", 0)) == case_id for item in task_items), f"Created case not found in AI task list: {task_list_payload}")
    print("[PASS] analytics console endpoints")

    print("[STEP] download client report")
    status, headers, body = _request_bytes(args.base_url, f"/cases/{case_id}/report", token=client_token, mini=True)
    _assert(status == 200, f"Client report download failed: {status}")
    _assert("application/pdf" in (headers.get("Content-Type", "")).lower() or body.startswith(b"%PDF"), "Client report is not PDF")
    print("[PASS] client report download")

    print("[STEP] verify report visibility")
    status, lawyer_reports = _request_json(args.base_url, f"/cases/{case_id}/reports", token=lawyer_token)
    _assert(status == 200 and isinstance(lawyer_reports, list), f"Lawyer report list failed: {status} {lawyer_reports}")
    status, client_reports = _request_json(args.base_url, f"/cases/{case_id}/reports", token=client_token)
    _assert(status == 200 and isinstance(client_reports, list), f"Client report list failed: {status} {client_reports}")
    _assert(len(client_reports) <= 1, f"Client should see latest only: {client_reports}")
    print("[PASS] report visibility")

    print("[STEP] refresh + logout")
    status, refresh_payload = _request_json(
        args.base_url,
        "/auth/refresh",
        method="POST",
        payload={"refresh_token": lawyer_refresh},
    )
    _assert(status == 200 and refresh_payload.get("access_token"), f"Refresh token failed: {status} {refresh_payload}")
    refreshed_access = refresh_payload["access_token"]
    status, me_payload = _request_json(args.base_url, "/users/me", token=refreshed_access)
    _assert(status == 200, f"Refreshed token /users/me failed: {status} {me_payload}")
    status, _ = _request_json(
        args.base_url,
        "/auth/logout",
        method="POST",
        token=refreshed_access,
        payload={"refresh_token": refresh_payload.get("refresh_token")},
    )
    _assert(status == 204, f"Logout failed: {status}")
    print("[PASS] refresh + logout")

    print("[DONE] qa02_full_e2e passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"[FAIL] {exc}")
        raise SystemExit(1)
