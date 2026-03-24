from __future__ import annotations


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def assert_error_shape(payload: dict) -> None:
    assert "code" in payload
    assert "message" in payload
    assert "detail" in payload
    assert "request_id" in payload


def test_file_access_token_invalid_returns_file_token_invalid(client):
    response = client.get("/api/v1/files/access/invalid-token")
    assert response.status_code == 400
    data = response.json()
    assert_error_shape(data)
    assert data["code"] == "FILE_TOKEN_INVALID"


def test_client_cannot_list_other_case_files(client, seeded_data):
    case_id = seeded_data["case"].id
    response = client.get(
        f"/api/v1/files/case/{case_id}",
        headers=auth_header(seeded_data["outsider_token"]),
    )
    assert response.status_code == 403
    data = response.json()
    assert_error_shape(data)
    assert data["code"] == "FILE_ACCESS_DENIED"


def test_non_admin_cannot_list_lawyers(client, seeded_data):
    response = client.get(
        "/api/v1/users/lawyers",
        headers=auth_header(seeded_data["lawyer_token"]),
    )
    assert response.status_code == 403
    data = response.json()
    assert_error_shape(data)
    assert data["code"] == "FORBIDDEN"


def test_client_cannot_create_case(client, seeded_data):
    response = client.post(
        "/api/v1/cases",
        headers=auth_header(seeded_data["client_token"]),
        json={
            "case_number": "CASE-FORBIDDEN-001",
            "title": "Forbidden Create",
            "legal_type": "other",
            "client_phone": "13800009999",
            "client_real_name": "Client A",
        },
    )
    assert response.status_code == 403
    data = response.json()
    assert_error_shape(data)
    assert data["code"] == "CASE_OPERATION_NOT_ALLOWED"


def test_client_cannot_view_other_case(client, seeded_data):
    case_id = seeded_data["case"].id
    response = client.get(
        f"/api/v1/cases/{case_id}",
        headers=auth_header(seeded_data["outsider_token"]),
    )
    assert response.status_code == 403
    data = response.json()
    assert_error_shape(data)
    assert data["code"] == "CASE_ACCESS_DENIED"


def test_organization_tenant_join_requires_invite(client, seeded_data):
    response = client.post(
        "/api/v1/tenants/join",
        json={
            "tenant_code": seeded_data["tenant"].tenant_code,
            "phone": "13800000001",
            "password": "Pwd123456",
            "real_name": "Dup",
        },
    )
    assert response.status_code == 400
    data = response.json()
    assert_error_shape(data)
    assert data["code"] == "INVITE_REQUIRED"


def test_auth_login_wrong_password_returns_validation_error(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"phone": "13800000001", "password": "wrong-pass"},
    )
    assert response.status_code == 422
    data = response.json()
    assert_error_shape(data)
    assert data["code"] == "VALIDATION_ERROR"


def test_mark_notification_not_found_returns_code(client, seeded_data):
    response = client.patch(
        "/api/v1/notifications/999/read",
        headers=auth_header(seeded_data["lawyer_token"]),
    )
    assert response.status_code == 404
    data = response.json()
    assert_error_shape(data)
    assert data["code"] == "NOTIFICATION_NOT_FOUND"


def test_invite_register_invalid_token_returns_invite_not_found(client):
    response = client.post(
        "/api/v1/auth/invite-register",
        json={
            "token": "invalid-token",
            "phone": "13800009998",
            "password": "Pwd123456",
            "real_name": "InviteUser",
        },
    )
    assert response.status_code == 404
    data = response.json()
    assert_error_shape(data)
    assert data["code"] == "INVITE_NOT_FOUND"


def test_preview_unknown_tenant_returns_tenant_not_found(client):
    response = client.get("/api/v1/tenants/invite/unknown_tenant_code")
    assert response.status_code == 404
    data = response.json()
    assert_error_shape(data)
    assert data["code"] == "TENANT_NOT_FOUND"
