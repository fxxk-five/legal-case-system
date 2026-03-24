from __future__ import annotations

import time


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _headers(token: str, idempotency_key: str) -> dict[str, str]:
    headers = auth_header(token)
    headers["Idempotency-Key"] = idempotency_key
    return headers


def test_parse_document_idempotency_reuse_same_payload(client, seeded_data):
    case_id = seeded_data["case"].id
    file_id = seeded_data["file"].id
    headers = _headers(seeded_data["lawyer_token"], "idem-parse-001")
    payload = {"file_id": file_id, "parse_options": {"extract_parties": True}}

    first_resp = client.post(
        f"/api/v1/ai/cases/{case_id}/parse-document",
        json=payload,
        headers=headers,
    )
    assert first_resp.status_code == 202
    first_task_id = first_resp.json()["task_id"]

    second_resp = client.post(
        f"/api/v1/ai/cases/{case_id}/parse-document",
        json=payload,
        headers=headers,
    )
    assert second_resp.status_code == 202
    second_data = second_resp.json()
    assert second_data["task_id"] == first_task_id
    assert second_data["status"] in {"queued", "pending", "processing", "completed", "failed"}


def test_parse_document_idempotency_conflict_with_different_payload(client, seeded_data):
    case_id = seeded_data["case"].id
    file_id = seeded_data["file"].id
    headers = _headers(seeded_data["lawyer_token"], "idem-parse-002")

    first_resp = client.post(
        f"/api/v1/ai/cases/{case_id}/parse-document",
        json={"file_id": file_id, "parse_options": {"extract_parties": True}},
        headers=headers,
    )
    assert first_resp.status_code == 202

    second_resp = client.post(
        f"/api/v1/ai/cases/{case_id}/parse-document",
        json={"file_id": file_id, "parse_options": {"extract_parties": False}},
        headers=headers,
    )
    assert second_resp.status_code == 409
    data = second_resp.json()
    assert data["code"] == "AI_TASK_CONFLICT"


def test_analyze_idempotency_reuse_same_payload(client, seeded_data):
    case_id = seeded_data["case"].id
    headers = _headers(seeded_data["lawyer_token"], "idem-analyze-001")
    payload = {"analysis_types": ["legal_analysis", "strategy"]}

    first_resp = client.post(
        f"/api/v1/ai/cases/{case_id}/analyze",
        json=payload,
        headers=headers,
    )
    assert first_resp.status_code == 202
    first_task_id = first_resp.json()["task_id"]

    second_resp = client.post(
        f"/api/v1/ai/cases/{case_id}/analyze",
        json=payload,
        headers=headers,
    )
    assert second_resp.status_code == 202
    assert second_resp.json()["task_id"] == first_task_id


def _wait_task_terminal_status(client, token: str, task_id: str, timeout_seconds: float = 20.0) -> dict:
    headers = auth_header(token)
    deadline = time.time() + timeout_seconds
    latest: dict = {}
    while time.time() < deadline:
        resp = client.get(f"/api/v1/ai/tasks/{task_id}", headers=headers)
        assert resp.status_code == 200
        latest = resp.json()
        if latest["status"] in {"completed", "failed"}:
            return latest
        time.sleep(0.15)
    return latest


def test_falsification_idempotency_reuse_same_payload(client, seeded_data):
    case_id = seeded_data["case"].id
    base_headers = auth_header(seeded_data["lawyer_token"])

    analyze_resp = client.post(
        f"/api/v1/ai/cases/{case_id}/analyze",
        json={"analysis_types": ["legal_analysis"]},
        headers=base_headers,
    )
    assert analyze_resp.status_code == 202
    analyze_task_id = analyze_resp.json()["task_id"]
    analyze_task_status = _wait_task_terminal_status(client, seeded_data["lawyer_token"], analyze_task_id)
    assert analyze_task_status["status"] == "completed"

    results_resp = client.get(f"/api/v1/ai/cases/{case_id}/analysis-results", headers=base_headers)
    assert results_resp.status_code == 200
    analysis_id = results_resp.json()["items"][0]["id"]

    headers = _headers(seeded_data["lawyer_token"], "idem-falsify-001")
    payload = {"analysis_id": analysis_id, "challenge_modes": ["logic"], "iteration_count": 2}

    first_resp = client.post(
        f"/api/v1/ai/cases/{case_id}/falsification",
        json=payload,
        headers=headers,
    )
    assert first_resp.status_code == 202
    first_task_id = first_resp.json()["task_id"]

    second_resp = client.post(
        f"/api/v1/ai/cases/{case_id}/falsification",
        json=payload,
        headers=headers,
    )
    assert second_resp.status_code == 202
    assert second_resp.json()["task_id"] == first_task_id
