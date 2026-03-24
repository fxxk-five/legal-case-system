from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.models.ai_analysis import AIAnalysisResult
from app.models.ai_task import AITask
from app.models.case_flow import CaseFlow
from app.models.tenant import Tenant
from app.models.user import User
from app.scripts.ai_worker import is_heartbeat_fresh, write_heartbeat
from app.services.ai import AIService


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@contextmanager
def override_settings(**changes):
    original = {key: getattr(settings, key) for key in changes}
    try:
        for key, value in changes.items():
            setattr(settings, key, value)
        yield
    finally:
        for key, value in original.items():
            setattr(settings, key, value)


def test_db_queue_worker_consumes_task(client, seeded_data, session_factory):
    case_id = seeded_data["case"].id
    headers = auth_header(seeded_data["lawyer_token"])

    with override_settings(QUEUE_DRIVER="db", AI_DB_QUEUE_EAGER=False):
        resp = client.post(
            f"/api/v1/ai/cases/{case_id}/analyze",
            json={"analysis_types": ["legal_analysis"]},
            headers=headers,
        )
        assert resp.status_code == 202
        task_id = resp.json()["task_id"]

        queued_status = client.get(f"/api/v1/ai/tasks/{task_id}", headers=headers)
        assert queued_status.status_code == 200
        assert queued_status.json()["status"] in {"queued", "retrying"}

        consumed = AIService.consume_queued_tasks_once(session_factory=session_factory, max_tasks=1)
        assert consumed == 1

        done_status = client.get(f"/api/v1/ai/tasks/{task_id}", headers=headers)
        assert done_status.status_code == 200
        assert done_status.json()["status"] == "completed"


def test_db_queue_dead_letter_after_retry_exhausted(client, seeded_data, session_factory):
    case_id = seeded_data["case"].id
    tenant_id = seeded_data["tenant"].id
    headers = auth_header(seeded_data["lawyer_token"])

    with session_factory() as db:
        lawyer = db.query(User).filter(User.tenant_id == tenant_id, User.role == "lawyer").first()
        assert lawyer is not None
        task = AITask(
            task_id=str(uuid4()),
            tenant_id=tenant_id,
            case_id=case_id,
            task_type="parse",
            status="queued",
            progress=0,
            message="Task queued.",
            input_params={},
            created_by=lawyer.id,
        )
        db.add(task)
        db.commit()
        dead_task_id = task.task_id

    with override_settings(
        QUEUE_DRIVER="db",
        AI_DB_QUEUE_EAGER=False,
        AI_DB_QUEUE_MAX_RETRIES=1,
        AI_DB_QUEUE_RETRY_BACKOFF_SECONDS=300,
    ):
        assert AIService.consume_queued_tasks_once(session_factory=session_factory, max_tasks=1) == 1
        assert AIService.consume_queued_tasks_once(session_factory=session_factory, max_tasks=1) == 0

        with session_factory() as db:
            retrying_task = db.query(AITask).filter(AITask.task_id == dead_task_id).first()
            assert retrying_task is not None
            assert retrying_task.status == "retrying"
            assert retrying_task.retry_count == 1
            assert retrying_task.next_retry_at is not None
            retrying_task.next_retry_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.add(retrying_task)
            db.commit()

        assert AIService.consume_queued_tasks_once(session_factory=session_factory, max_tasks=1) == 1

    dead_status = client.get(f"/api/v1/ai/tasks/{dead_task_id}", headers=headers)
    assert dead_status.status_code == 200
    assert dead_status.json()["status"] == "dead"
    assert dead_status.json()["retry_count"] == 1

    with session_factory() as db:
        flow = (
            db.query(CaseFlow)
            .filter(
                CaseFlow.case_id == case_id,
                CaseFlow.tenant_id == tenant_id,
                CaseFlow.action_type == "analysis_dead_lettered",
            )
            .first()
        )
        assert flow is not None


def test_db_queue_recovers_stale_processing_task(session_factory, seeded_data):
    case_id = seeded_data["case"].id
    tenant_id = seeded_data["tenant"].id
    stale_worker_id = "worker-stale-01"

    with session_factory() as db:
        lawyer = db.query(User).filter(User.tenant_id == tenant_id, User.role == "lawyer").first()
        assert lawyer is not None
        task = AITask(
            task_id=str(uuid4()),
            tenant_id=tenant_id,
            case_id=case_id,
            task_type="analyze",
            status="processing",
            progress=40,
            message="Task claimed by DB queue worker.",
            input_params={"analysis_types": ["legal_analysis"]},
            created_by=lawyer.id,
            started_at=datetime.now(timezone.utc) - timedelta(minutes=30),
            claimed_at=datetime.now(timezone.utc) - timedelta(minutes=30),
            heartbeat_at=datetime.now(timezone.utc) - timedelta(minutes=30),
            worker_id=stale_worker_id,
        )
        db.add(task)
        db.commit()
        stale_task_id = task.task_id

    with override_settings(
        QUEUE_DRIVER="db",
        AI_DB_QUEUE_EAGER=False,
        AI_DB_QUEUE_MAX_RETRIES=2,
        AI_DB_QUEUE_RETRY_BACKOFF_SECONDS=300,
        AI_DB_QUEUE_STALE_TASK_SECONDS=60,
    ):
        assert AIService.consume_queued_tasks_once(session_factory=session_factory, max_tasks=1) == 0

    with session_factory() as db:
        recovered = db.query(AITask).filter(AITask.task_id == stale_task_id).first()
        assert recovered is not None
        assert recovered.status == "retrying"
        assert recovered.retry_count == 1
        assert recovered.next_retry_at is not None
        assert recovered.worker_id is None

        flow = (
            db.query(CaseFlow)
            .filter(
                CaseFlow.case_id == case_id,
                CaseFlow.tenant_id == tenant_id,
                CaseFlow.action_type == "analysis_retry_scheduled",
                CaseFlow.content.contains(stale_worker_id),
            )
            .first()
        )
        assert flow is not None


def test_ai_worker_heartbeat_file_healthcheck(tmp_path):
    heartbeat_file = Path(tmp_path) / "worker-heartbeat.json"

    assert is_heartbeat_fresh(heartbeat_file=heartbeat_file, max_age_seconds=30) is False

    write_heartbeat(
        heartbeat_file=heartbeat_file,
        worker_id="worker-01",
        consumed_total=5,
        status="idle",
    )
    assert is_heartbeat_fresh(heartbeat_file=heartbeat_file, max_age_seconds=30) is True

    payload = heartbeat_file.read_text(encoding="utf-8")
    assert "worker-01" in payload


def test_super_admin_can_update_budget_configs(client, seeded_data, session_factory):
    tenant_id = seeded_data["tenant"].id
    case_id = seeded_data["case"].id

    with session_factory() as db:
        super_admin = User(
            tenant_id=tenant_id,
            role="super_admin",
            is_tenant_admin=False,
            phone="13800000009",
            password_hash=get_password_hash("pwd123456"),
            real_name="Super Admin",
            status=1,
        )
        db.add(super_admin)
        db.commit()
        db.refresh(super_admin)
        super_token = create_access_token(
            super_admin.id,
            extra_data={
                "tenant_id": super_admin.tenant_id,
                "role": super_admin.role,
                "is_tenant_admin": super_admin.is_tenant_admin,
            },
        )

    headers = auth_header(super_token)
    patch_tenant = client.patch(
        f"/api/v1/tenants/{tenant_id}/ai-budget",
        json={"ai_monthly_budget_limit": 199.99, "ai_budget_degrade_model": "gpt-cheap"},
        headers=headers,
    )
    assert patch_tenant.status_code == 200
    assert patch_tenant.json()["ai_monthly_budget_limit"] == 199.99
    assert patch_tenant.json()["ai_budget_degrade_model"] == "gpt-cheap"

    patch_case = client.patch(
        f"/api/v1/tenants/{tenant_id}/cases/{case_id}/ai-budget",
        json={"ai_case_budget_limit": 9.9},
        headers=headers,
    )
    assert patch_case.status_code == 200
    assert patch_case.json()["ai_case_budget_limit"] == 9.9

    read_case = client.get(f"/api/v1/tenants/{tenant_id}/cases/{case_id}/ai-budget", headers=headers)
    assert read_case.status_code == 200
    assert read_case.json()["ai_case_budget_limit"] == 9.9


def test_budget_circuit_blocks_auto_and_allows_manual_downgrade(client, seeded_data, session_factory):
    case_id = seeded_data["case"].id
    tenant_id = seeded_data["tenant"].id
    headers = auth_header(seeded_data["lawyer_token"])

    with session_factory() as db:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        lawyer = db.query(User).filter(User.tenant_id == tenant_id, User.role == "lawyer").first()
        assert tenant is not None
        assert lawyer is not None

        tenant.ai_monthly_budget_limit = Decimal("0.0100")
        tenant.ai_budget_degrade_model = "gpt-cheap"
        db.add(
            AIAnalysisResult(
                tenant_id=tenant_id,
                case_id=case_id,
                analysis_type="legal_analysis",
                result_data={"summary": "existing"},
                applicable_laws=[],
                related_cases=[],
                strengths=[],
                weaknesses=[],
                recommendations=[],
                ai_model="gpt-main",
                token_usage=1000,
                cost=Decimal("0.0100"),
                created_by=lawyer.id,
            )
        )
        db.commit()

    with override_settings(QUEUE_DRIVER="db", AI_DB_QUEUE_EAGER=False):
        manual_resp = client.post(
            f"/api/v1/ai/cases/{case_id}/analyze",
            json={"analysis_types": ["legal_analysis"]},
            headers=headers,
        )
        assert manual_resp.status_code == 202
        task_id = manual_resp.json()["task_id"]

        with session_factory() as db:
            task = db.query(AITask).filter(AITask.task_id == task_id).first()
            assert task is not None
            assert (task.input_params or {}).get("model_override") == "gpt-cheap"

        auto_resp = client.post(
            f"/api/v1/ai/cases/{case_id}/analyze",
            json={"analysis_types": ["legal_analysis"]},
            headers={**headers, "Idempotency-Key": "auto-reanalyze:1:1"},
        )
        assert auto_resp.status_code == 409
        assert auto_resp.json()["code"] == "AI_BUDGET_EXCEEDED"


def test_be08_analysis_progress_written_to_case_and_flows(client, seeded_data, session_factory):
    case_id = seeded_data["case"].id
    tenant_id = seeded_data["tenant"].id
    headers = auth_header(seeded_data["lawyer_token"])

    resp = client.post(
        f"/api/v1/ai/cases/{case_id}/analyze",
        json={"analysis_types": ["legal_analysis"]},
        headers=headers,
    )
    assert resp.status_code == 202

    with session_factory() as db:
        case = db.query(seeded_data["case"].__class__).filter_by(id=case_id, tenant_id=tenant_id).first()
        assert case is not None
        assert case.analysis_status == "completed"
        assert case.analysis_progress == 100

        progress_flows = (
            db.query(CaseFlow)
            .filter(
                CaseFlow.case_id == case_id,
                CaseFlow.tenant_id == tenant_id,
                CaseFlow.action_type == "analysis_progress_updated",
            )
            .all()
        )
        assert len(progress_flows) >= 3
        contents = [item.content for item in progress_flows]
        assert any("collecting_facts" in content for content in contents)
        assert any("generating_summary" in content for content in contents)
        assert any("persisting_results" in content for content in contents)
