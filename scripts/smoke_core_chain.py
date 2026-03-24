#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
import time
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4


def _headers(token: str, *, mini: bool = False, idempotency_key: str | None = None) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Request-ID": f"smoke-{uuid4()}",
    }
    if mini:
        headers["X-Client-Platform"] = "mini-program"
        headers["X-Client-Source"] = "wx-mini"
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def _request_json(
    base_url: str,
    path: str,
    token: str,
    *,
    method: str = "GET",
    payload: dict | None = None,
    mini: bool = False,
    idempotency_key: str | None = None,
) -> tuple[int, dict]:
    url = f"{base_url.rstrip('/')}{path}"
    body = None
    headers = _headers(token, mini=mini, idempotency_key=idempotency_key)
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, method=method, headers=headers, data=body)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            parsed = json.loads(data.decode("utf-8")) if data else {}
            return resp.status, parsed
    except urllib.error.HTTPError as exc:
        data = exc.read()
        parsed = json.loads(data.decode("utf-8")) if data else {}
        return exc.code, parsed


def _build_multipart(file_path: Path, field_name: str = "upload") -> tuple[bytes, str]:
    boundary = f"----smoke-boundary-{uuid4().hex}"
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
    body = b"".join(parts)
    return body, boundary


def _upload_file(base_url: str, case_id: int, token: str, file_path: Path) -> tuple[int, dict]:
    url = f"{base_url.rstrip('/')}/cases/{case_id}/files"
    body, boundary = _build_multipart(file_path)
    headers = _headers(token, mini=True)
    headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    req = urllib.request.Request(url, method="POST", headers=headers, data=body)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            parsed = json.loads(resp.read().decode("utf-8"))
            return resp.status, parsed
    except urllib.error.HTTPError as exc:
        parsed = json.loads(exc.read().decode("utf-8"))
        return exc.code, parsed


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _poll_task(base_url: str, token: str, task_id: str, timeout_seconds: int = 120) -> dict:
    deadline = time.time() + timeout_seconds
    latest: dict = {}
    while time.time() < deadline:
        status, payload = _request_json(base_url, f"/ai/tasks/{task_id}", token)
        _assert(status == 200, f"Task status query failed: {status} {payload}")
        latest = payload
        if payload.get("status") in {"completed", "failed"}:
            return payload
        time.sleep(2)
    return latest


def _list_cases(base_url: str, token: str) -> list[dict]:
    status, payload = _request_json(base_url, "/cases", token)
    _assert(status == 200, f"List cases failed: {status} {payload}")
    _assert(isinstance(payload, list) and len(payload) > 0, "No case found; please create one first.")
    return payload


def _find_case_id(base_url: str, lawyer_token: str, *, client_token: str = "") -> int:
    lawyer_cases = _list_cases(base_url, lawyer_token)
    if not client_token:
        case_id = lawyer_cases[0].get("id")
        _assert(isinstance(case_id, int), f"Invalid case id in response: {lawyer_cases[0]}")
        return case_id

    client_cases = _list_cases(base_url, client_token)
    client_case_ids = {item.get("id") for item in client_cases if isinstance(item.get("id"), int)}
    for item in lawyer_cases:
        case_id = item.get("id")
        if isinstance(case_id, int) and case_id in client_case_ids:
            return case_id
    raise AssertionError("No shared case found between lawyer and client; please pass --case-id explicitly.")


def _download_report(base_url: str, token: str, case_id: int, *, regenerate: bool = True) -> int:
    suffix = "?regenerate=true" if regenerate else ""
    url = f"{base_url.rstrip('/')}/cases/{case_id}/report{suffix}"
    req = urllib.request.Request(url, method="GET", headers=_headers(token, mini=True))
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read()
            _assert(resp.status == 200, f"Report download status is {resp.status}")
            _assert(body.startswith(b"%PDF"), "Report response is not PDF")
            return resp.status
    except urllib.error.HTTPError as exc:
        data = exc.read().decode("utf-8", errors="ignore")
        raise AssertionError(f"Report download failed: {exc.code} {data}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test for core chain (upload -> parse -> analyze -> report).")
    parser.add_argument("--base-url", required=True, help="API base URL, e.g. https://example.com/api/v1")
    parser.add_argument("--lawyer-token", required=True, help="JWT token for lawyer/tenant_admin")
    parser.add_argument("--client-token", default="", help="Optional client token for report role validation")
    parser.add_argument("--case-id", type=int, default=0, help="Optional case id; empty means auto-pick first case")
    parser.add_argument("--file-path", default="upload-smoke.txt", help="File to upload as evidence")
    args = parser.parse_args()

    file_path = Path(args.file_path)
    _assert(file_path.exists() and file_path.is_file(), f"File not found: {file_path}")

    case_id = (
        args.case_id
        if args.case_id > 0
        else _find_case_id(args.base_url, args.lawyer_token, client_token=args.client_token)
    )
    print(f"[INFO] using case_id={case_id}")

    upload_status, upload_payload = _upload_file(args.base_url, case_id, args.lawyer_token, file_path)
    _assert(upload_status == 201, f"Upload failed: {upload_status} {upload_payload}")
    file_id = upload_payload.get("id")
    _assert(isinstance(file_id, int), f"Upload response missing file id: {upload_payload}")
    print(f"[PASS] upload file id={file_id}")

    parse_status, parse_payload = _request_json(
        args.base_url,
        f"/ai/cases/{case_id}/parse-document",
        args.lawyer_token,
        method="POST",
        payload={"file_id": file_id},
        idempotency_key=f"smoke-parse-{uuid4().hex}",
    )
    _assert(parse_status == 202, f"Parse start failed: {parse_status} {parse_payload}")
    parse_task_id = parse_payload.get("task_id")
    _assert(parse_task_id, f"Parse response missing task id: {parse_payload}")
    parse_terminal = _poll_task(args.base_url, args.lawyer_token, parse_task_id)
    _assert(parse_terminal.get("status") == "completed", f"Parse task not completed: {parse_terminal}")
    print(f"[PASS] parse task completed id={parse_task_id}")

    analyze_status, analyze_payload = _request_json(
        args.base_url,
        f"/ai/cases/{case_id}/analyze",
        args.lawyer_token,
        method="POST",
        payload={},
        idempotency_key=f"smoke-analyze-{uuid4().hex}",
    )
    _assert(analyze_status == 202, f"Analyze start failed: {analyze_status} {analyze_payload}")
    analyze_task_id = analyze_payload.get("task_id")
    _assert(analyze_task_id, f"Analyze response missing task id: {analyze_payload}")
    analyze_terminal = _poll_task(args.base_url, args.lawyer_token, analyze_task_id)
    _assert(analyze_terminal.get("status") == "completed", f"Analyze task not completed: {analyze_terminal}")
    print(f"[PASS] analyze task completed id={analyze_task_id}")

    result_status, result_payload = _request_json(args.base_url, f"/ai/cases/{case_id}/analysis-results", args.lawyer_token)
    _assert(result_status == 200, f"Analysis result failed: {result_status} {result_payload}")
    items = result_payload.get("items") or []
    _assert(len(items) >= 1, "No analysis results found after analyze task completion")
    print(f"[PASS] analysis results count={len(items)}")

    _download_report(args.base_url, args.lawyer_token, case_id)
    print("[PASS] lawyer report download")

    if args.client_token:
        _download_report(args.base_url, args.client_token, case_id)
        print("[PASS] client report download")

    print("[DONE] smoke_core_chain passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"[FAIL] {exc}")
        raise SystemExit(1)
