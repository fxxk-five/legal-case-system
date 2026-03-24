from __future__ import annotations


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_upload_file_rejects_when_size_exceeds_limit(client, seeded_data, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "LOCAL_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "FILE_UPLOAD_MAX_SIZE_BYTES", 8)

    response = client.post(
        "/api/v1/files/upload",
        params={"case_id": seeded_data["case"].id},
        headers=_auth_header(seeded_data["lawyer_token"]),
        files={"upload": ("too-large.txt", b"123456789", "text/plain")},
    )

    assert response.status_code == 413
    payload = response.json()
    assert payload["code"] == "FILE_UPLOAD_INVALID"
    assert "exceeds max size limit" in payload["message"].lower()


def test_upload_file_rejects_when_type_not_allowed(client, seeded_data, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "LOCAL_STORAGE_DIR", str(tmp_path))

    response = client.post(
        "/api/v1/files/upload",
        params={"case_id": seeded_data["case"].id},
        headers=_auth_header(seeded_data["lawyer_token"]),
        files={"upload": ("dangerous.exe", b"MZ", "application/octet-stream")},
    )

    assert response.status_code == 415
    payload = response.json()
    assert payload["code"] == "FILE_UPLOAD_INVALID"
    assert "dangerous file types" in payload["message"].lower() or "unsupported" in payload["message"].lower()


def test_upload_file_accepts_allowed_pdf(client, seeded_data, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "LOCAL_STORAGE_DIR", str(tmp_path))

    upload_resp = client.post(
        "/api/v1/files/upload",
        params={"case_id": seeded_data["case"].id},
        headers=_auth_header(seeded_data["lawyer_token"]),
        files={"upload": ("evidence.pdf", b"%PDF-1.4\n1 0 obj\n", "application/pdf")},
    )

    assert upload_resp.status_code == 201
    upload_payload = upload_resp.json()
    assert upload_payload["file_name"] == "evidence.pdf"
    assert upload_payload["file_type"] == "application/pdf"

    list_resp = client.get(
        f"/api/v1/files/case/{seeded_data['case'].id}",
        headers=_auth_header(seeded_data["lawyer_token"]),
    )
    assert list_resp.status_code == 200
    assert any(item["id"] == upload_payload["id"] for item in list_resp.json())
