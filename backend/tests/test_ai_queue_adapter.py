from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.models.ai_task import AITask
from app.models.user import User
from app.services.ai_queue import DBQueueAdapter, get_ai_queue_adapter


def test_db_queue_adapter_serializes_message(session_factory, seeded_data):
    tenant_id = seeded_data["tenant"].id
    case_id = seeded_data["case"].id

    with session_factory() as db:
        lawyer = db.query(User).filter(User.tenant_id == tenant_id, User.role == "lawyer").first()
        assert lawyer is not None
        task = AITask(
            task_id=str(uuid4()),
            tenant_id=tenant_id,
            case_id=case_id,
            task_type="analyze",
            status="queued",
            progress=0,
            message="Task queued.",
            input_params={"analysis_types": ["legal_analysis"]},
            created_by=lawyer.id,
            retry_count=1,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        adapter = DBQueueAdapter()
        message = adapter.enqueue(task=task, request_id="req-db-queue")
        payload = message.to_payload()

    assert payload["task_id"] == task.task_id
    assert payload["tenant_id"] == tenant_id
    assert payload["case_id"] == case_id
    assert payload["task_type"] == "analyze"
    assert payload["retry_count"] == 1
    assert payload["request_id"] == "req-db-queue"


def test_tencent_queue_adapter_requires_runtime_config():
    adapter = get_ai_queue_adapter("tdmq")
    task = AITask(
        task_id=str(uuid4()),
        tenant_id=1,
        case_id=1,
        task_type="analyze",
        status="queued",
        progress=0,
        message="Task queued.",
        input_params={"analysis_types": ["legal_analysis"]},
        created_by=1,
    )

    with pytest.raises(AppError) as exc_info:
        adapter.enqueue(task=task, request_id="req-cloud-queue")

    exc = exc_info.value
    assert exc.status_code == 503
    assert exc.code.value == "EXTERNAL_SERVICE_ERROR"
    assert "TDMQ/CMQ" in exc.message
    assert "missing" in exc.detail
