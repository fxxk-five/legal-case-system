from __future__ import annotations

from uuid import uuid4

from app.models.ai_task import AITask
from app.models.case import Case
from app.models.case_flow import CaseFlow
from app.models.file import File


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _mini_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Client-Platform": "mini-program",
        "X-Client-Source": "wx-mini",
    }


class FakeCOSClient:
    def __init__(self) -> None:
        self.objects: dict[str, dict[str, bytes | str]] = {}

    def put_file(self, *, local_path, storage_key: str, content_type: str) -> None:
        self.objects[storage_key] = {
            "body": local_path.read_bytes(),
            "content_type": content_type,
        }

    def put_bytes(self, *, data: bytes, storage_key: str, content_type: str) -> None:
        self.objects[storage_key] = {
            "body": data,
            "content_type": content_type,
        }

    def copy(self, *, source_key: str, target_key: str) -> None:
        source = self.objects.get(source_key)
        if source is None:
            raise KeyError(source_key)
        self.objects[target_key] = dict(source)

    def delete(self, *, storage_key: str) -> None:
        self.objects.pop(storage_key, None)

    def exists(self, *, storage_key: str) -> bool:
        return storage_key in self.objects

    def list_objects(self, *, prefix: str):
        from app.services.storage import StorageObjectInfo

        keys = sorted(key for key in self.objects if key.startswith(prefix))
        return [StorageObjectInfo(storage_key=key) for key in keys]

    def build_download_url(
        self,
        *,
        storage_key: str,
        file_name: str,
        content_type: str | None,
        expires_seconds: int,
    ) -> str:
        _ = file_name, content_type
        return f"https://cos.example.com/{storage_key}?expires={expires_seconds}"


def _configure_cos_settings(monkeypatch, fake_client: FakeCOSClient, *, direct_upload_enabled: bool = False) -> None:
    from app.core.config import settings
    from app.services import storage as storage_module

    monkeypatch.setattr(settings, "STORAGE_BACKEND", "cos")
    monkeypatch.setattr(settings, "STORAGE_DIRECT_UPLOAD_ENABLED", direct_upload_enabled)
    monkeypatch.setattr(settings, "STORAGE_PUBLIC_BASE_URL", "")
    monkeypatch.setattr(settings, "TENCENT_COS_SECRET_ID", "test-secret-id")
    monkeypatch.setattr(settings, "TENCENT_COS_SECRET_KEY", "test-secret-key")
    monkeypatch.setattr(settings, "TENCENT_COS_BUCKET", "test-bucket")
    monkeypatch.setattr(settings, "TENCENT_COS_REGION", "ap-shanghai")
    monkeypatch.setattr(storage_module, "_create_cos_client", lambda: fake_client)


def test_case_detail_reads_persisted_flows_with_visibility_filter(client, db_session, seeded_data):
    case = seeded_data["case"]
    tenant = seeded_data["tenant"]

    db_session.add_all(
        [
            CaseFlow(
                tenant_id=tenant.id,
                case_id=case.id,
                action_type="lawyer_internal",
                content="lawyer-only event",
                visible_to="lawyer",
            ),
            CaseFlow(
                tenant_id=tenant.id,
                case_id=case.id,
                action_type="shared_event",
                content="shared event",
                visible_to="both",
            ),
            CaseFlow(
                tenant_id=tenant.id,
                case_id=case.id,
                action_type="client_notice",
                content="client-only event",
                visible_to="client",
            ),
        ]
    )
    db_session.commit()

    client_resp = client.get(f"/api/v1/cases/{case.id}", headers=_auth_header(seeded_data["client_token"]))
    assert client_resp.status_code == 200
    client_events = {item["event_type"] for item in client_resp.json()["timeline"]}
    assert "shared_event" in client_events
    assert "client_notice" in client_events
    assert "lawyer_internal" not in client_events

    lawyer_resp = client.get(f"/api/v1/cases/{case.id}", headers=_auth_header(seeded_data["lawyer_token"]))
    assert lawyer_resp.status_code == 200
    lawyer_events = {item["event_type"] for item in lawyer_resp.json()["timeline"]}
    assert "shared_event" in lawyer_events
    assert "lawyer_internal" in lawyer_events
    assert "client_notice" not in lawyer_events


def test_create_case_writes_case_created_flow(client, db_session, seeded_data):
    payload = {
        "title": "Flow Created Case",
        "legal_type": "contract_dispute",
        "client_phone": "13800000151",
        "client_real_name": "Flow Client",
    }
    response = client.post("/api/v1/cases", json=payload, headers=_auth_header(seeded_data["lawyer_token"]))

    assert response.status_code == 201
    case_id = response.json()["id"]

    flow = (
        db_session.query(CaseFlow)
        .filter(CaseFlow.case_id == case_id, CaseFlow.action_type == "case_created")
        .first()
    )
    assert flow is not None
    assert flow.visible_to == "both"


def test_upload_file_writes_flow_event(client, db_session, seeded_data, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "LOCAL_STORAGE_DIR", str(tmp_path))

    response = client.post(
        "/api/v1/files/upload",
        params={"case_id": seeded_data["case"].id},
        headers=_mini_headers(seeded_data["lawyer_token"]),
        files={"upload": ("flow.pdf", b"%PDF-1.4\n", "application/pdf")},
    )

    assert response.status_code == 201

    flow = (
        db_session.query(CaseFlow)
        .filter(
            CaseFlow.case_id == seeded_data["case"].id,
            CaseFlow.action_type == "file_uploaded",
            CaseFlow.content.contains("flow.pdf"),
        )
        .first()
    )
    assert flow is not None


def test_client_file_visibility_and_download_permissions(client, seeded_data):
    case_id = seeded_data["case"].id
    file_id = seeded_data["file"].id

    list_resp = client.get(f"/api/v1/files/case/{case_id}", headers=_auth_header(seeded_data["client_token"]))
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) == 1
    assert items[0]["uploader_role"] == "lawyer"
    assert items[0]["can_download"] is False
    assert items[0]["download_url"] is None

    link_resp = client.get(f"/api/v1/files/{file_id}/access-link", headers=_auth_header(seeded_data["client_token"]))
    assert link_resp.status_code == 403
    assert link_resp.json()["code"] == "FILE_ACCESS_DENIED"

    download_resp = client.get(f"/api/v1/files/{file_id}/download", headers=_auth_header(seeded_data["client_token"]))
    assert download_resp.status_code == 403
    assert download_resp.json()["code"] == "FILE_ACCESS_DENIED"


def test_lawyer_file_download_permissions_unchanged(client, seeded_data):
    file_id = seeded_data["file"].id

    link_resp = client.get(f"/api/v1/files/{file_id}/access-link", headers=_auth_header(seeded_data["lawyer_token"]))
    assert link_resp.status_code == 200
    assert link_resp.json()["file_id"] == file_id


def test_client_can_delete_own_uploaded_file_and_write_flow(client, db_session, seeded_data, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "LOCAL_STORAGE_DIR", str(tmp_path))

    upload_resp = client.post(
        "/api/v1/files/upload",
        params={"case_id": seeded_data["case"].id},
        headers=_mini_headers(seeded_data["client_token"]),
        files={"upload": ("own-evidence.pdf", b"%PDF-1.4\n", "application/pdf")},
    )
    assert upload_resp.status_code == 201
    file_id = upload_resp.json()["id"]

    delete_resp = client.delete(f"/api/v1/files/{file_id}", headers=_auth_header(seeded_data["client_token"]))
    assert delete_resp.status_code == 204

    file_record = db_session.query(File).filter(File.id == file_id).first()
    assert file_record is None

    flow = (
        db_session.query(CaseFlow)
        .filter(
            CaseFlow.case_id == seeded_data["case"].id,
            CaseFlow.action_type == "file_deleted",
            CaseFlow.content.contains("own-evidence.pdf"),
        )
        .first()
    )
    assert flow is not None
    assert flow.visible_to == "both"


def test_client_cannot_delete_lawyer_uploaded_file(client, seeded_data):
    file_id = seeded_data["file"].id

    response = client.delete(f"/api/v1/files/{file_id}", headers=_auth_header(seeded_data["client_token"]))
    assert response.status_code == 403
    assert response.json()["code"] == "FILE_ACCESS_DENIED"


def test_client_upload_triggers_auto_reanalysis_and_marks_case_pending(
    client,
    db_session,
    seeded_data,
    monkeypatch,
    tmp_path,
):
    from app.core.config import settings

    monkeypatch.setattr(settings, "LOCAL_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "AI_DB_QUEUE_EAGER", False)

    response = client.post(
        "/api/v1/files/upload",
        params={"case_id": seeded_data["case"].id},
        headers=_mini_headers(seeded_data["client_token"]),
        files={"upload": ("supplement-1.pdf", b"%PDF-1.4\n", "application/pdf")},
    )
    assert response.status_code == 201

    db_session.expire_all()
    case = db_session.query(Case).filter(Case.id == seeded_data["case"].id).first()
    assert case is not None
    assert case.analysis_status in {"pending_reanalysis", "queued"}
    assert case.analysis_progress == 0

    analyze_tasks = (
        db_session.query(AITask)
        .filter(AITask.case_id == case.id, AITask.task_type == "analyze")
        .all()
    )
    assert len(analyze_tasks) == 1
    assert analyze_tasks[0].created_by == case.assigned_lawyer_id

    flow = (
        db_session.query(CaseFlow)
        .filter(
            CaseFlow.case_id == case.id,
            CaseFlow.action_type == "analysis_auto_reanalyze_queued",
        )
        .first()
    )
    assert flow is not None


def test_client_direct_upload_completion_triggers_auto_reanalysis(
    client,
    db_session,
    seeded_data,
    monkeypatch,
):
    from app.core.config import settings

    monkeypatch.setattr(settings, "AI_DB_QUEUE_EAGER", False)
    fake_client = FakeCOSClient()
    _configure_cos_settings(monkeypatch, fake_client, direct_upload_enabled=True)

    policy_response = client.get(
        "/api/v1/files/upload-policy",
        params={"case_id": seeded_data["case"].id, "file_name": "supplement-direct.pdf"},
        headers=_mini_headers(seeded_data["client_token"]),
    )
    assert policy_response.status_code == 200
    policy = policy_response.json()
    fake_client.objects[policy["storage_key"]] = {
        "body": b"%PDF-1.4\ndirect-client\n",
        "content_type": "application/pdf",
    }

    complete_response = client.post(
        policy["completion_url"],
        json={"completion_token": policy["completion_token"]},
        headers=_mini_headers(seeded_data["client_token"]),
    )
    assert complete_response.status_code == 200

    db_session.expire_all()
    case = db_session.query(Case).filter(Case.id == seeded_data["case"].id).first()
    assert case is not None
    assert case.analysis_status in {"pending_reanalysis", "queued"}
    assert case.analysis_progress == 0

    analyze_tasks = (
        db_session.query(AITask)
        .filter(AITask.case_id == case.id, AITask.task_type == "analyze")
        .all()
    )
    assert len(analyze_tasks) == 1
    assert analyze_tasks[0].created_by == case.assigned_lawyer_id

    flow = (
        db_session.query(CaseFlow)
        .filter(
            CaseFlow.case_id == case.id,
            CaseFlow.action_type == "analysis_auto_reanalyze_queued",
        )
        .first()
    )
    assert flow is not None


def test_client_upload_within_debounce_window_reuses_single_analyze_task(
    client,
    db_session,
    seeded_data,
    monkeypatch,
    tmp_path,
):
    from app.core.config import settings

    monkeypatch.setattr(settings, "LOCAL_STORAGE_DIR", str(tmp_path))

    first = client.post(
        "/api/v1/files/upload",
        params={"case_id": seeded_data["case"].id},
        headers=_mini_headers(seeded_data["client_token"]),
        files={"upload": ("debounce-1.pdf", b"%PDF-1.4\n", "application/pdf")},
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/files/upload",
        params={"case_id": seeded_data["case"].id},
        headers=_mini_headers(seeded_data["client_token"]),
        files={"upload": ("debounce-2.pdf", b"%PDF-1.4\n", "application/pdf")},
    )
    assert second.status_code == 201

    db_session.expire_all()
    case = db_session.query(Case).filter(Case.id == seeded_data["case"].id).first()
    assert case is not None

    analyze_tasks = (
        db_session.query(AITask)
        .filter(AITask.case_id == case.id, AITask.task_type == "analyze")
        .all()
    )
    assert len(analyze_tasks) == 1

    debounced_flow = (
        db_session.query(CaseFlow)
        .filter(
            CaseFlow.case_id == case.id,
            CaseFlow.action_type == "analysis_auto_reanalyze_debounced",
        )
        .first()
    )
    assert debounced_flow is not None

def test_ai_start_and_retry_write_flow_events(client, db_session, seeded_data):
    case_id = seeded_data["case"].id
    headers = _auth_header(seeded_data["lawyer_token"])

    analyze_resp = client.post(
        f"/api/v1/ai/cases/{case_id}/analyze",
        json={"analysis_types": ["legal_analysis"]},
        headers=headers,
    )
    assert analyze_resp.status_code == 202
    analyze_task_id = analyze_resp.json()["task_id"]

    started_flow = (
        db_session.query(CaseFlow)
        .filter(
            CaseFlow.case_id == case_id,
            CaseFlow.action_type == "analysis_started",
            CaseFlow.content.contains(analyze_task_id),
        )
        .first()
    )
    assert started_flow is not None

    failed_task = AITask(
        task_id=str(uuid4()),
        tenant_id=seeded_data["tenant"].id,
        case_id=case_id,
        task_type="analyze",
        status="failed",
        progress=70,
        message="failed",
        error_message="mock-error",
        input_params={"analysis_types": ["legal_analysis"]},
        created_by=1,
    )
    db_session.add(failed_task)
    db_session.commit()

    retry_resp = client.post(
        f"/api/v1/ai/tasks/{failed_task.task_id}/retry",
        json={"reason": "flow-check"},
        headers=headers,
    )
    assert retry_resp.status_code == 202
    retry_task_id = retry_resp.json()["task_id"]

    retried_flow = (
        db_session.query(CaseFlow)
        .filter(
            CaseFlow.case_id == case_id,
            CaseFlow.action_type == "analysis_retried",
            CaseFlow.content.contains(retry_task_id),
        )
        .first()
    )
    assert retried_flow is not None
