from __future__ import annotations

from uuid import uuid4

from app.modules.ai.models.ai_task import AITask
from app.modules.cases.models.case import Case
from app.models.tenant import Tenant
from app.models.user import User


def _create_task(*, db_session, case_id: int, tenant_id: int, status: str = "pending") -> AITask:
    task = AITask(
        task_id=str(uuid4()),
        tenant_id=tenant_id,
        case_id=case_id,
        task_type="analyze",
        status=status,
        progress=100 if status == "completed" else 20,
        message="test-task",
        input_params={},
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


def _login_lawyer(client) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={"phone": "13800000001", "password": "pwd123456"},
    )
    assert response.status_code == 200
    return response.json()


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_ws_requires_token(client):
    task_id = str(uuid4())
    with client.websocket_connect(f"/ws/ai/tasks/{task_id}") as websocket:
        payload = websocket.receive_json()
        assert payload["type"] == "failed"
        assert payload["task_id"] == task_id
        assert "Missing auth token." in payload["error"]


def test_ws_rejects_refresh_token(client, db_session, seeded_data):
    task = _create_task(
        db_session=db_session,
        case_id=seeded_data["case"].id,
        tenant_id=seeded_data["tenant"].id,
        status="completed",
    )
    login_payload = _login_lawyer(client)

    with client.websocket_connect(f"/ws/ai/tasks/{task.task_id}?token={login_payload['refresh_token']}") as websocket:
        payload = websocket.receive_json()
        assert payload["type"] == "failed"
        assert payload["task_id"] == task.task_id
        assert "access token is required" in payload["error"]


def test_ws_rejects_revoked_access_session(client, db_session, seeded_data):
    task = _create_task(
        db_session=db_session,
        case_id=seeded_data["case"].id,
        tenant_id=seeded_data["tenant"].id,
        status="completed",
    )
    login_payload = _login_lawyer(client)
    logout_resp = client.post(
        "/api/v1/auth/logout",
        headers=_auth_header(login_payload["access_token"]),
    )
    assert logout_resp.status_code == 204

    with client.websocket_connect(f"/ws/ai/tasks/{task.task_id}?token={login_payload['access_token']}") as websocket:
        payload = websocket.receive_json()
        assert payload["type"] == "failed"
        assert payload["task_id"] == task.task_id
        assert "session has expired" in payload["error"]


def test_ws_client_can_subscribe_own_case_task(client, db_session, seeded_data):
    task = _create_task(
        db_session=db_session,
        case_id=seeded_data["case"].id,
        tenant_id=seeded_data["tenant"].id,
        status="completed",
    )
    with client.websocket_connect(f"/ws/ai/tasks/{task.task_id}?token={seeded_data['client_token']}") as websocket:
        payload = websocket.receive_json()
        assert payload["task_id"] == task.task_id
        assert payload["progress"] == 100
        assert payload["type"] == "completed"
        assert "error" in payload


def test_ws_client_rejects_task_for_other_client_case(client, db_session, seeded_data):
    other_client = db_session.query(User).filter(User.phone == "13800000003").first()
    assert other_client is not None

    other_case = Case(
        tenant_id=seeded_data["tenant"].id,
        case_number="CASE-CLIENT-OTHER-001",
        title="Other Client Case",
        client_id=other_client.id,
        assigned_lawyer_id=seeded_data["case"].assigned_lawyer_id,
        status="new",
    )
    db_session.add(other_case)
    db_session.flush()

    task = _create_task(
        db_session=db_session,
        case_id=other_case.id,
        tenant_id=seeded_data["tenant"].id,
        status="processing",
    )

    with client.websocket_connect(f"/ws/ai/tasks/{task.task_id}?token={seeded_data['client_token']}") as websocket:
        payload = websocket.receive_json()
        assert payload["type"] == "failed"
        assert payload["task_id"] == task.task_id
        assert "access denied" in payload["error"]


def test_ws_rejects_cross_tenant_task(client, db_session, seeded_data):
    tenant = Tenant(
        tenant_code="tenant_other",
        name="Tenant Other",
        type="organization",
        status=1,
    )
    db_session.add(tenant)
    db_session.flush()

    other_lawyer = User(
        tenant_id=tenant.id,
        role="lawyer",
        is_tenant_admin=False,
        phone="13900000001",
        password_hash="x",
        real_name="Other Lawyer",
        status=1,
    )
    db_session.add(other_lawyer)
    db_session.flush()

    other_case = Case(
        tenant_id=tenant.id,
        case_number="CASE-OTHER-001",
        title="Other Case",
        client_id=None,
        assigned_lawyer_id=other_lawyer.id,
        status="new",
    )
    db_session.add(other_case)
    db_session.flush()

    foreign_task = _create_task(
        db_session=db_session,
        case_id=other_case.id,
        tenant_id=tenant.id,
        status="processing",
    )

    with client.websocket_connect(
        f"/ws/ai/tasks/{foreign_task.task_id}?token={seeded_data['lawyer_token']}"
    ) as websocket:
        payload = websocket.receive_json()
        assert payload["type"] == "failed"
        assert payload["task_id"] == foreign_task.task_id
        assert "AI task not found or access denied." in payload["error"]


def test_ws_lawyer_can_subscribe_same_tenant_task(client, db_session, seeded_data):
    task = _create_task(
        db_session=db_session,
        case_id=seeded_data["case"].id,
        tenant_id=seeded_data["tenant"].id,
        status="completed",
    )
    with client.websocket_connect(f"/ws/ai/tasks/{task.task_id}?token={seeded_data['lawyer_token']}") as websocket:
        payload = websocket.receive_json()
        assert payload["task_id"] == task.task_id
        assert payload["progress"] == 100
        assert payload["type"] == "completed"
        assert "error" in payload


def test_ws_since_compensation_pull(client, db_session, seeded_data):
    task = _create_task(
        db_session=db_session,
        case_id=seeded_data["case"].id,
        tenant_id=seeded_data["tenant"].id,
        status="processing",
    )
    with client.websocket_connect(
        f"/ws/ai/tasks/{task.task_id}?token={seeded_data['lawyer_token']}&since=1970-01-01T00:00:00Z"
    ) as websocket:
        payload = websocket.receive_json()
        assert payload["task_id"] == task.task_id
        assert payload["type"] == "progress"
        assert payload["error"] is None
