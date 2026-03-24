from __future__ import annotations

from datetime import datetime, timezone


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_create_case_auto_generates_case_number(client, seeded_data):
    payload = {
        "title": "Auto Number Case",
        "legal_type": "civil_loan",
        "client_phone": "13800000123",
        "client_real_name": "Auto Client",
    }

    response = client.post("/api/v1/cases", json=payload, headers=_auth_header(seeded_data["lawyer_token"]))

    assert response.status_code == 201
    data = response.json()
    expected_year = datetime.now(timezone.utc).year
    assert data["case_number"].startswith(f"TENANTDEMO-{expected_year}-LOAN-")
    assert data["analysis_status"] == "not_started"
    assert data["analysis_progress"] == 0

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "phone": payload["client_phone"],
            "password": "client123456",
            "tenant_code": seeded_data["tenant"].tenant_code,
        },
    )
    assert login_response.status_code == 401
    assert login_response.json()["code"] == "AUTH_REQUIRED"


def test_create_case_manual_case_number_conflict(client, seeded_data):
    payload = {
        "case_number": "CASE-001",
        "title": "Duplicate Case Number",
        "legal_type": "labor_dispute",
        "client_phone": "13800000124",
        "client_real_name": "Dup Client",
    }

    response = client.post("/api/v1/cases", json=payload, headers=_auth_header(seeded_data["lawyer_token"]))

    assert response.status_code == 409
    assert response.json()["code"] == "CONFLICT"


def test_upload_file_persists_uploader_role_and_parse_status(client, seeded_data, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "LOCAL_STORAGE_DIR", str(tmp_path))

    response = client.post(
        "/api/v1/files/upload",
        params={"case_id": seeded_data["case"].id, "description": "supplemental evidence"},
        headers=_auth_header(seeded_data["lawyer_token"]),
        files={"upload": ("supplement.pdf", b"%PDF-1.4\n", "application/pdf")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["uploader_role"] == "lawyer"
    assert payload["parse_status"] == "pending"
    assert payload["description"] == "supplemental evidence"
