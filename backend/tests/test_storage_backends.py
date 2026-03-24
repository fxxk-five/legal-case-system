from __future__ import annotations

from pathlib import Path

from app.models.file import File


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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


def test_cos_upload_policy_defaults_to_server_proxy(monkeypatch):
    from app.services.storage import get_storage_backend

    fake_client = FakeCOSClient()
    _configure_cos_settings(monkeypatch, fake_client, direct_upload_enabled=False)

    backend = get_storage_backend()
    policy = backend.build_upload_policy(
        tenant_id=11,
        case_id=22,
        file_name="evidence.pdf",
        content_type="application/pdf",
    )

    assert backend.backend_name == "cos"
    assert policy.mode == "server_proxy"
    assert policy.upload_url == "/api/v1/files/upload?case_id=22"
    assert policy.storage_key.endswith(".pdf")


def test_cos_upload_policy_can_switch_to_direct_post(monkeypatch):
    from app.services.storage import get_storage_backend

    fake_client = FakeCOSClient()
    _configure_cos_settings(monkeypatch, fake_client, direct_upload_enabled=True)

    backend = get_storage_backend()
    policy = backend.build_upload_policy(
        tenant_id=11,
        case_id=22,
        file_name="evidence.pdf",
        content_type="application/pdf",
    )

    assert policy.mode == "direct_post"
    assert policy.upload_url == "https://test-bucket.cos.ap-shanghai.myqcloud.com/"
    assert policy.file_field_name == "file"
    assert policy.form_fields["key"] == policy.storage_key
    assert policy.form_fields["Content-Type"] == "application/pdf"
    assert "/_pending/" in policy.storage_key


def test_direct_upload_policy_includes_completion_metadata(client, seeded_data, monkeypatch):
    fake_client = FakeCOSClient()
    _configure_cos_settings(monkeypatch, fake_client, direct_upload_enabled=True)

    response = client.get(
        "/api/v1/files/upload-policy",
        params={"case_id": seeded_data["case"].id, "file_name": "evidence.pdf"},
        headers=_auth_header(seeded_data["lawyer_token"]),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "direct_post"
    assert payload["completion_url"] == f"/api/v1/cases/{seeded_data['case'].id}/files/complete-upload"
    assert payload["completion_token"]
    assert payload["expires_in_seconds"] == 600


def test_complete_direct_upload_creates_file_record(client, db_session, seeded_data, monkeypatch):
    fake_client = FakeCOSClient()
    _configure_cos_settings(monkeypatch, fake_client, direct_upload_enabled=True)

    policy_response = client.get(
        "/api/v1/files/upload-policy",
        params={"case_id": seeded_data["case"].id, "file_name": "evidence.pdf"},
        headers=_auth_header(seeded_data["lawyer_token"]),
    )
    assert policy_response.status_code == 200
    policy = policy_response.json()
    fake_client.objects[policy["storage_key"]] = {
        "body": b"%PDF-1.4\ndirect\n",
        "content_type": "application/pdf",
    }

    complete_response = client.post(
        policy["completion_url"],
        json={"completion_token": policy["completion_token"]},
        headers=_auth_header(seeded_data["lawyer_token"]),
    )

    assert complete_response.status_code == 200
    payload = complete_response.json()
    assert payload["file_name"] == "evidence.pdf"

    db_session.expire_all()
    file_record = db_session.query(File).filter(File.id == payload["id"]).first()
    assert file_record is not None
    assert file_record.file_url != policy["storage_key"]
    assert "/files/" in file_record.file_url
    assert file_record.file_url in fake_client.objects
    assert policy["storage_key"] not in fake_client.objects


def test_complete_direct_upload_is_idempotent(client, db_session, seeded_data, monkeypatch):
    fake_client = FakeCOSClient()
    _configure_cos_settings(monkeypatch, fake_client, direct_upload_enabled=True)

    policy_response = client.get(
        "/api/v1/files/upload-policy",
        params={"case_id": seeded_data["case"].id, "file_name": "evidence.pdf"},
        headers=_auth_header(seeded_data["lawyer_token"]),
    )
    policy = policy_response.json()
    fake_client.objects[policy["storage_key"]] = {
        "body": b"%PDF-1.4\ndirect\n",
        "content_type": "application/pdf",
    }

    first = client.post(
        policy["completion_url"],
        json={"completion_token": policy["completion_token"]},
        headers=_auth_header(seeded_data["lawyer_token"]),
    )
    second = client.post(
        policy["completion_url"],
        json={"completion_token": policy["completion_token"]},
        headers=_auth_header(seeded_data["lawyer_token"]),
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]

    db_session.expire_all()
    file_record = db_session.query(File).filter(File.id == first.json()["id"]).first()
    assert file_record is not None
    records = (
        db_session.query(File)
        .filter(File.tenant_id == seeded_data["tenant"].id, File.file_url == file_record.file_url)
        .all()
    )
    assert len(records) == 1


def test_complete_direct_upload_rejects_missing_storage_object(client, seeded_data, monkeypatch):
    fake_client = FakeCOSClient()
    _configure_cos_settings(monkeypatch, fake_client, direct_upload_enabled=True)

    policy_response = client.get(
        "/api/v1/files/upload-policy",
        params={"case_id": seeded_data["case"].id, "file_name": "evidence.pdf"},
        headers=_auth_header(seeded_data["lawyer_token"]),
    )
    policy = policy_response.json()

    complete_response = client.post(
        policy["completion_url"],
        json={"completion_token": policy["completion_token"]},
        headers=_auth_header(seeded_data["lawyer_token"]),
    )

    assert complete_response.status_code == 400
    assert complete_response.json()["code"] == "FILE_UPLOAD_INVALID"


def test_delete_file_archives_object_when_retention_enabled(client, db_session, seeded_data, monkeypatch):
    from app.core.config import settings

    fake_client = FakeCOSClient()
    _configure_cos_settings(monkeypatch, fake_client, direct_upload_enabled=False)
    monkeypatch.setattr(settings, "STORAGE_DELETE_POLICY", "archive")

    response = client.post(
        "/api/v1/files/upload",
        params={"case_id": seeded_data["case"].id},
        headers=_auth_header(seeded_data["lawyer_token"]),
        files={"upload": ("archive-me.pdf", b"%PDF-1.4\narchive\n", "application/pdf")},
    )
    assert response.status_code == 201
    file_id = response.json()["id"]

    db_session.expire_all()
    file_record = db_session.query(File).filter(File.id == file_id).first()
    assert file_record is not None
    original_key = file_record.file_url
    assert original_key in fake_client.objects

    delete_response = client.delete(
        f"/api/v1/files/{file_id}",
        headers=_auth_header(seeded_data["lawyer_token"]),
    )
    assert delete_response.status_code == 204
    assert original_key not in fake_client.objects
    assert any(key.startswith("_retained/") and key.endswith(Path(original_key).name) for key in fake_client.objects)


def test_upload_file_persists_bytes_to_cos_via_server_proxy(client, db_session, seeded_data, monkeypatch):
    fake_client = FakeCOSClient()
    _configure_cos_settings(monkeypatch, fake_client, direct_upload_enabled=False)

    response = client.post(
        "/api/v1/files/upload",
        params={"case_id": seeded_data["case"].id},
        headers=_auth_header(seeded_data["lawyer_token"]),
        files={"upload": ("cos-evidence.pdf", b"%PDF-1.4\ncloud\n", "application/pdf")},
    )

    assert response.status_code == 201
    payload = response.json()

    db_session.expire_all()
    file_record = db_session.query(File).filter(File.id == payload["id"]).first()
    assert file_record is not None
    assert file_record.file_url in fake_client.objects
    assert fake_client.objects[file_record.file_url]["body"] == b"%PDF-1.4\ncloud\n"
    assert fake_client.objects[file_record.file_url]["content_type"] == "application/pdf"


def test_access_link_returns_signed_cos_url(client, db_session, seeded_data, monkeypatch):
    fake_client = FakeCOSClient()
    _configure_cos_settings(monkeypatch, fake_client, direct_upload_enabled=False)

    file_record = File(
        tenant_id=seeded_data["tenant"].id,
        case_id=seeded_data["case"].id,
        uploader_id=seeded_data["case"].assigned_lawyer_id,
        uploader_role="lawyer",
        file_name="signed-report.pdf",
        file_url="tenant_1/case_1/signed-report.pdf",
        file_type="application/pdf",
        parse_status="pending",
    )
    db_session.add(file_record)
    db_session.commit()
    fake_client.objects[file_record.file_url] = {
        "body": b"%PDF-1.4\nsigned\n",
        "content_type": "application/pdf",
    }

    response = client.get(
        f"/api/v1/files/{file_record.id}/access-link",
        headers=_auth_header(seeded_data["lawyer_token"]),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["file_id"] == file_record.id
    assert payload["access_url"] == "https://cos.example.com/tenant_1/case_1/signed-report.pdf?expires=600"


def test_cos_backend_lists_objects_by_prefix(monkeypatch):
    from app.services.storage import get_storage_backend

    fake_client = FakeCOSClient()
    _configure_cos_settings(monkeypatch, fake_client, direct_upload_enabled=False)
    fake_client.objects["tenant_1/case_2/reports/report-lawyer-20260323010101.pdf"] = {
        "body": b"%PDF-1.4\none\n",
        "content_type": "application/pdf",
    }
    fake_client.objects["tenant_1/case_2/reports/report-client-20260323010102.pdf"] = {
        "body": b"%PDF-1.4\ntwo\n",
        "content_type": "application/pdf",
    }
    fake_client.objects["tenant_1/case_3/reports/other.pdf"] = {
        "body": b"%PDF-1.4\nskip\n",
        "content_type": "application/pdf",
    }

    backend = get_storage_backend()
    objects = backend.list_objects(prefix="tenant_1/case_2/reports/", suffix=".pdf")

    assert [item.storage_key for item in objects] == [
        "tenant_1/case_2/reports/report-client-20260323010102.pdf",
        "tenant_1/case_2/reports/report-lawyer-20260323010101.pdf",
    ]
