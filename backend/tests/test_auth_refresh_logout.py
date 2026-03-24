from __future__ import annotations

from app.models.auth_session import AuthSession


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login_lawyer(client) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={"phone": "13800000001", "password": "pwd123456"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("access_token")
    assert payload.get("refresh_token")
    return payload


def test_login_returns_refresh_token(client, seeded_data):
    _ = seeded_data
    payload = _login_lawyer(client)
    assert payload["token_type"] == "bearer"
    assert isinstance(payload["refresh_token"], str)
    assert len(payload["refresh_token"]) > 20


def test_refresh_token_generates_new_access_token(client, seeded_data):
    _ = seeded_data
    login_payload = _login_lawyer(client)

    refresh_resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_payload["refresh_token"]},
    )
    assert refresh_resp.status_code == 200
    refreshed_payload = refresh_resp.json()
    assert refreshed_payload.get("access_token")
    assert refreshed_payload.get("refresh_token")

    me_resp = client.get("/api/v1/users/me", headers=_auth_header(refreshed_payload["access_token"]))
    assert me_resp.status_code == 200
    assert me_resp.json().get("phone") == "13800000001"


def test_login_creates_auth_session_and_refresh_rotates_token(client, db_session, seeded_data):
    _ = seeded_data
    login_payload = _login_lawyer(client)

    sessions = db_session.query(AuthSession).all()
    assert len(sessions) == 1
    original_hash = sessions[0].refresh_token_hash
    assert sessions[0].is_revoked is False

    refresh_resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_payload["refresh_token"]},
    )
    assert refresh_resp.status_code == 200
    refreshed_payload = refresh_resp.json()
    assert refreshed_payload["refresh_token"] != login_payload["refresh_token"]

    db_session.expire_all()
    rotated_session = db_session.query(AuthSession).one()
    assert rotated_session.refresh_token_hash != original_hash
    assert rotated_session.is_revoked is False

    old_refresh_resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_payload["refresh_token"]},
    )
    assert old_refresh_resp.status_code == 401
    assert old_refresh_resp.json().get("code") == "AUTH_REQUIRED"


def test_refresh_rejects_access_token(client, seeded_data):
    _ = seeded_data
    login_payload = _login_lawyer(client)

    refresh_resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_payload["access_token"]},
    )
    assert refresh_resp.status_code == 401
    assert refresh_resp.json().get("code") == "AUTH_REQUIRED"


def test_logout_endpoint_revokes_current_refresh_session(client, db_session, seeded_data):
    _ = seeded_data
    login_payload = _login_lawyer(client)

    logout_resp = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": login_payload["refresh_token"]},
        headers=_auth_header(login_payload["access_token"]),
    )
    assert logout_resp.status_code == 204

    db_session.expire_all()
    session = db_session.query(AuthSession).one()
    assert session.is_revoked is True
    assert session.revoked_at is not None

    refresh_resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_payload["refresh_token"]},
    )
    assert refresh_resp.status_code == 401
    assert refresh_resp.json().get("code") == "AUTH_REQUIRED"


def test_logout_without_refresh_token_revokes_current_access_session(client, db_session, seeded_data):
    _ = seeded_data
    login_payload = _login_lawyer(client)

    logout_resp = client.post(
        "/api/v1/auth/logout",
        headers=_auth_header(login_payload["access_token"]),
    )
    assert logout_resp.status_code == 204

    db_session.expire_all()
    session = db_session.query(AuthSession).one()
    assert session.is_revoked is True

    me_resp = client.get("/api/v1/users/me", headers=_auth_header(login_payload["access_token"]))
    assert me_resp.status_code == 401
    assert me_resp.json().get("code") == "AUTH_REQUIRED"
