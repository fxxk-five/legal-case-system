#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request


def _request(base_url: str, path: str, token: str) -> tuple[int, dict[str, str], bytes]:
    url = f"{base_url.rstrip('/')}{path}"
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Client-Platform": "mini-program",
            "X-Client-Source": "wx-mini",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, dict(resp.headers.items()), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers.items()), exc.read()


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _is_pdf(headers: dict[str, str], body: bytes) -> bool:
    content_type = (headers.get("Content-Type", "") or "").lower()
    return "application/pdf" in content_type or body.startswith(b"%PDF")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test for report visibility behavior (BE10/BE11).")
    parser.add_argument("--base-url", required=True, help="API base URL, e.g. https://example.com/api/v1")
    parser.add_argument("--case-id", required=True, type=int, help="Case ID")
    parser.add_argument("--lawyer-token", required=True, help="JWT token of lawyer/tenant_admin")
    parser.add_argument("--client-token", required=True, help="JWT token of client")
    args = parser.parse_args()

    case_id = args.case_id
    print(f"[INFO] base={args.base_url} case_id={case_id}")

    # 1) Latest report endpoint should return PDF for both roles.
    l_status, l_headers, l_body = _request(args.base_url, f"/cases/{case_id}/report", args.lawyer_token)
    _assert(l_status == 200, f"Lawyer latest report expected 200, got {l_status}")
    _assert(_is_pdf(l_headers, l_body), "Lawyer latest report is not PDF")
    print("[PASS] lawyer latest report")

    c_status, c_headers, c_body = _request(args.base_url, f"/cases/{case_id}/report", args.client_token)
    _assert(c_status == 200, f"Client latest report expected 200, got {c_status}")
    _assert(_is_pdf(c_headers, c_body), "Client latest report is not PDF")
    print("[PASS] client latest report")

    # 2) History list endpoint visibility.
    l_status, _, l_body = _request(args.base_url, f"/cases/{case_id}/reports", args.lawyer_token)
    _assert(l_status == 200, f"Lawyer report list expected 200, got {l_status}")
    lawyer_reports = json.loads(l_body.decode("utf-8") or "[]")
    _assert(isinstance(lawyer_reports, list), "Lawyer report list should be array")
    print(f"[PASS] lawyer report list size={len(lawyer_reports)}")

    c_status, _, c_body = _request(args.base_url, f"/cases/{case_id}/reports", args.client_token)
    _assert(c_status == 200, f"Client report list expected 200, got {c_status}")
    client_reports = json.loads(c_body.decode("utf-8") or "[]")
    _assert(isinstance(client_reports, list), "Client report list should be array")
    _assert(len(client_reports) <= 1, f"Client report list expected <=1 item, got {len(client_reports)}")
    print(f"[PASS] client report list size={len(client_reports)}")

    # 3) Version download access control if history exists.
    if lawyer_reports:
        report_name = lawyer_reports[0].get("file_name", "")
        _assert(bool(report_name), "Lawyer report list item missing file_name")
        encoded_name = urllib.parse.quote(report_name, safe="")
        path = f"/cases/{case_id}/reports/{encoded_name}"

        dl_status, dl_headers, dl_body = _request(args.base_url, path, args.lawyer_token)
        _assert(dl_status == 200, f"Lawyer history download expected 200, got {dl_status}")
        _assert(_is_pdf(dl_headers, dl_body), "Lawyer history download is not PDF")
        print("[PASS] lawyer history report download")

        dc_status, _, _ = _request(args.base_url, path, args.client_token)
        _assert(dc_status == 403, f"Client history download expected 403, got {dc_status}")
        print("[PASS] client history report forbidden")

    print("[DONE] smoke_report_visibility passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"[FAIL] {exc}")
        raise SystemExit(1)
