from __future__ import annotations

import time
from uuid import uuid4

from app.core.security import get_password_hash
from app.models.ai_task import AITask
from app.models.case import Case
from app.models.file import File
from app.models.user import User


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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


def test_ai_full_chain_with_case_binding(client, seeded_data):
    case_id = seeded_data["case"].id
    file_id = seeded_data["file"].id
    headers = auth_header(seeded_data["lawyer_token"])

    parse_resp = client.post(
        f"/api/v1/ai/cases/{case_id}/parse-document",
        json={"file_id": file_id, "parse_options": {"extract_parties": True}},
        headers=headers,
    )
    assert parse_resp.status_code == 202
    parse_data = parse_resp.json()
    assert parse_data["task_id"]
    assert parse_data["status"] in {"queued", "pending", "processing", "completed", "failed"}

    parse_task_status = _wait_task_terminal_status(client, seeded_data["lawyer_token"], parse_data["task_id"])
    assert parse_task_status["status"] == "completed"

    facts_resp = client.get(f"/api/v1/ai/cases/{case_id}/facts", headers=headers)
    assert facts_resp.status_code == 200
    facts_data = facts_resp.json()
    assert facts_data["total"] >= 1
    assert all(item["case_id"] == case_id for item in facts_data["items"])

    analyze_resp = client.post(
        f"/api/v1/ai/cases/{case_id}/analyze",
        json={"analysis_types": ["legal_analysis", "strategy"]},
        headers=headers,
    )
    assert analyze_resp.status_code == 202
    analyze_task_id = analyze_resp.json()["task_id"]
    analyze_task_status = _wait_task_terminal_status(client, seeded_data["lawyer_token"], analyze_task_id)
    assert analyze_task_status["status"] == "completed"

    results_resp = client.get(f"/api/v1/ai/cases/{case_id}/analysis-results", headers=headers)
    assert results_resp.status_code == 200
    results_data = results_resp.json()
    assert len(results_data["items"]) >= 1
    analysis_id = results_data["items"][0]["id"]

    falsify_resp = client.post(
        f"/api/v1/ai/cases/{case_id}/falsification",
        json={"analysis_id": analysis_id, "challenge_modes": ["logic", "evidence"], "iteration_count": 2},
        headers=headers,
    )
    assert falsify_resp.status_code == 202
    falsify_task_status = _wait_task_terminal_status(
        client,
        seeded_data["lawyer_token"],
        falsify_resp.json()["task_id"],
    )
    assert falsify_task_status["status"] == "completed"

    falsify_results_resp = client.get(
        f"/api/v1/ai/cases/{case_id}/falsification-results",
        headers=headers,
    )
    assert falsify_results_resp.status_code == 200
    falsify_data = falsify_results_resp.json()
    assert falsify_data["summary"]["total_challenges"] >= 1
    assert all(item["case_id"] == case_id for item in falsify_data["items"])

    task_status_resp = client.get(f"/api/v1/ai/tasks/{analyze_task_id}", headers=headers)
    assert task_status_resp.status_code == 200
    task_data = task_status_resp.json()
    assert task_data["task_id"] == analyze_task_id
    assert task_data["status"] in {"queued", "processing", "completed", "failed", "pending"}


def test_ai_permissions_for_client_role(client, seeded_data):
    case_id = seeded_data["case"].id
    file_id = seeded_data["file"].id

    lawyer_headers = auth_header(seeded_data["lawyer_token"])
    client_headers = auth_header(seeded_data["client_token"])

    # Prepare analysis so client can view analysis results.
    analyze_resp = client.post(
        f"/api/v1/ai/cases/{case_id}/analyze",
        json={"analysis_types": ["legal_analysis"]},
        headers=lawyer_headers,
    )
    assert analyze_resp.status_code == 202
    _wait_task_terminal_status(client, seeded_data["lawyer_token"], analyze_resp.json()["task_id"])

    parse_resp = client.post(
        f"/api/v1/ai/cases/{case_id}/parse-document",
        json={"file_id": file_id},
        headers=client_headers,
    )
    assert parse_resp.status_code == 403
    parse_error = parse_resp.json()
    assert parse_error["code"] == "AI_OPERATION_NOT_ALLOWED"

    analysis_view_resp = client.get(f"/api/v1/ai/cases/{case_id}/analysis-results", headers=client_headers)
    assert analysis_view_resp.status_code == 200

    falsify_view_resp = client.get(
        f"/api/v1/ai/cases/{case_id}/falsification-results",
        headers=client_headers,
    )
    assert falsify_view_resp.status_code == 403
    assert falsify_view_resp.json()["code"] == "AI_OPERATION_NOT_ALLOWED"


def test_ai_error_branches_and_case_visibility(client, seeded_data):
    case_id = seeded_data["case"].id
    lawyer_headers = auth_header(seeded_data["lawyer_token"])
    outsider_headers = auth_header(seeded_data["outsider_token"])

    unauth_resp = client.get(f"/api/v1/ai/cases/{case_id}/facts")
    assert unauth_resp.status_code == 401
    assert unauth_resp.json()["code"] == "AUTH_REQUIRED"

    bad_file_resp = client.post(
        f"/api/v1/ai/cases/{case_id}/parse-document",
        json={"file_id": 999999},
        headers=lawyer_headers,
    )
    assert bad_file_resp.status_code == 404
    assert bad_file_resp.json()["code"] == "FILE_NOT_FOUND"

    outsider_resp = client.get(f"/api/v1/ai/cases/{case_id}/facts", headers=outsider_headers)
    assert outsider_resp.status_code == 403
    assert outsider_resp.json()["code"] == "CASE_ACCESS_DENIED"


def test_personal_lawyer_cannot_access_hidden_case_ai_endpoints(client, db_session, seeded_data):
    tenant = seeded_data["tenant"]
    tenant.type = "personal"
    db_session.add(tenant)

    another_lawyer = User(
        tenant_id=tenant.id,
        role="lawyer",
        is_tenant_admin=False,
        phone="13800000997",
        password_hash=get_password_hash("pwd123456"),
        real_name="Hidden AI Lawyer",
        status=1,
    )
    db_session.add(another_lawyer)
    db_session.flush()

    hidden_case = Case(
        tenant_id=tenant.id,
        case_number="CASE-AI-HIDDEN-001",
        title="Hidden AI Case",
        legal_type="other",
        client_id=seeded_data["case"].client_id,
        assigned_lawyer_id=another_lawyer.id,
        status="new",
    )
    db_session.add(hidden_case)
    db_session.flush()

    hidden_file = File(
        tenant_id=tenant.id,
        case_id=hidden_case.id,
        uploader_id=another_lawyer.id,
        uploader_role="lawyer",
        file_name="hidden-ai.pdf",
        file_url="storage/tenant_demo/hidden-ai.pdf",
        file_type="application/pdf",
    )
    hidden_task = AITask(
        task_id=str(uuid4()),
        tenant_id=tenant.id,
        case_id=hidden_case.id,
        task_type="analyze",
        status="queued",
        progress=0,
        message="queued",
        input_params={"analysis_types": ["legal_analysis"]},
        created_by=another_lawyer.id,
    )
    db_session.add_all([hidden_file, hidden_task])
    db_session.commit()

    facts_resp = client.get(f"/api/v1/ai/cases/{hidden_case.id}/facts", headers=auth_header(seeded_data["lawyer_token"]))
    assert facts_resp.status_code == 404
    assert facts_resp.json()["code"] == "CASE_NOT_FOUND"

    analyze_resp = client.post(
        f"/api/v1/ai/cases/{hidden_case.id}/analyze",
        json={"analysis_types": ["legal_analysis"]},
        headers=auth_header(seeded_data["lawyer_token"]),
    )
    assert analyze_resp.status_code == 404
    assert analyze_resp.json()["code"] == "CASE_NOT_FOUND"

    tasks_resp = client.get("/api/v1/ai/tasks", headers=auth_header(seeded_data["lawyer_token"]))
    assert tasks_resp.status_code == 200
    task_ids = [item["task_id"] for item in tasks_resp.json()["items"]]
    assert hidden_task.task_id not in task_ids


def test_ai_retry_for_failed_task(client, db_session, seeded_data):
    case_id = seeded_data["case"].id
    failed_task = AITask(
        task_id=str(uuid4()),
        tenant_id=seeded_data["tenant"].id,
        case_id=case_id,
        task_type="analyze",
        status="failed",
        progress=80,
        message="法律分析失败。",
        error_message="mock-error",
        input_params={"analysis_types": ["legal_analysis"]},
        created_by=1,
    )
    db_session.add(failed_task)
    db_session.commit()

    retry_resp = client.post(
        f"/api/v1/ai/tasks/{failed_task.task_id}/retry",
        json={"reason": "provider timeout"},
        headers=auth_header(seeded_data["lawyer_token"]),
    )
    assert retry_resp.status_code == 202
    payload = retry_resp.json()
    assert payload["source_task_id"] == failed_task.task_id
    assert payload["task_id"]
    assert payload["status"] in {"queued", "processing", "completed", "failed", "pending"}


def test_ai_retry_rejects_non_failed_task(client, db_session, seeded_data):
    case_id = seeded_data["case"].id
    completed_task = AITask(
        task_id=str(uuid4()),
        tenant_id=seeded_data["tenant"].id,
        case_id=case_id,
        task_type="analyze",
        status="completed",
        progress=100,
        message="ok",
        input_params={"analysis_types": ["legal_analysis"]},
        created_by=1,
    )
    db_session.add(completed_task)
    db_session.commit()

    retry_resp = client.post(
        f"/api/v1/ai/tasks/{completed_task.task_id}/retry",
        json={"reason": "manual"},
        headers=auth_header(seeded_data["lawyer_token"]),
    )
    assert retry_resp.status_code == 409
    assert retry_resp.json()["code"] == "CONFLICT"


def test_ai_retry_rejects_client_role(client, db_session, seeded_data):
    case_id = seeded_data["case"].id
    failed_task = AITask(
        task_id=str(uuid4()),
        tenant_id=seeded_data["tenant"].id,
        case_id=case_id,
        task_type="analyze",
        status="failed",
        progress=60,
        message="failed",
        error_message="mock-error",
        input_params={"analysis_types": ["legal_analysis"]},
        created_by=1,
    )
    db_session.add(failed_task)
    db_session.commit()

    retry_resp = client.post(
        f"/api/v1/ai/tasks/{failed_task.task_id}/retry",
        json={"reason": "manual"},
        headers=auth_header(seeded_data["client_token"]),
    )
    assert retry_resp.status_code == 403
    assert retry_resp.json()["code"] == "AI_OPERATION_NOT_ALLOWED"


def test_ai_task_is_queryable_immediately_after_creation(client, seeded_data):
    case_id = seeded_data["case"].id
    headers = auth_header(seeded_data["lawyer_token"])

    analyze_resp = client.post(
        f"/api/v1/ai/cases/{case_id}/analyze",
        json={"analysis_types": ["legal_analysis"]},
        headers=headers,
    )
    assert analyze_resp.status_code == 202
    task_id = analyze_resp.json()["task_id"]

    status_resp = client.get(f"/api/v1/ai/tasks/{task_id}", headers=headers)
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["task_id"] == task_id
    assert status_data["status"] in {"queued", "processing", "completed", "failed", "pending"}


def test_ai_retry_failed_task_transitions_to_failed_async(client, db_session, seeded_data):
    case_id = seeded_data["case"].id
    failed_task = AITask(
        task_id=str(uuid4()),
        tenant_id=seeded_data["tenant"].id,
        case_id=case_id,
        task_type="parse",
        status="failed",
        progress=70,
        message="文档解析失败。",
        error_message="mock-error",
        input_params={},
        created_by=1,
    )
    db_session.add(failed_task)
    db_session.commit()

    retry_resp = client.post(
        f"/api/v1/ai/tasks/{failed_task.task_id}/retry",
        json={"reason": "force failure"},
        headers=auth_header(seeded_data["lawyer_token"]),
    )
    assert retry_resp.status_code == 202
    retry_task_id = retry_resp.json()["task_id"]

    terminal_status = _wait_task_terminal_status(client, seeded_data["lawyer_token"], retry_task_id)
    assert terminal_status["status"] == "failed"
    assert terminal_status["error_message"]


def test_ai_task_list_endpoint_returns_items(client, seeded_data):
    case_id = seeded_data["case"].id
    headers = auth_header(seeded_data["lawyer_token"])

    analyze_resp = client.post(
        f"/api/v1/ai/cases/{case_id}/analyze",
        json={"analysis_types": ["legal_analysis"]},
        headers=headers,
    )
    assert analyze_resp.status_code == 202

    list_resp = client.get("/api/v1/ai/tasks?page=1&page_size=10", headers=headers)
    assert list_resp.status_code == 200
    payload = list_resp.json()
    assert payload["total"] >= 1
    assert payload["page"] == 1
    assert payload["page_size"] == 10
    assert isinstance(payload["items"], list)
    assert payload["items"][0]["task_id"]


def test_ai_task_list_forbidden_for_client(client, seeded_data):
    headers = auth_header(seeded_data["client_token"])
    response = client.get("/api/v1/ai/tasks", headers=headers)

    assert response.status_code == 403
    assert response.json()["code"] == "AI_OPERATION_NOT_ALLOWED"
