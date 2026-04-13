from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import jwt

from app.core.config import settings
from app.core.security import REFRESH_TOKEN_TYPE
from app.core.security import get_password_hash
from app.core.statuses import UserStatus
from app.core.security import create_access_token
from app.models.auth_session import AuthSession
from app.models.tenant import Tenant
from app.models.user import User


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


def test_pending_user_refresh_keeps_limited_session_available(client, db_session):
    tenant = Tenant(tenant_code="tenant_pending_refresh", name="Tenant Pending Refresh", type="organization", status=1)
    db_session.add(tenant)
    db_session.flush()

    user = User(
        tenant_id=tenant.id,
        role="lawyer",
        is_tenant_admin=False,
        phone="13800002021",
        password_hash=get_password_hash("Pass123456"),
        real_name="Pending Refresh User",
        status=int(UserStatus.PENDING_APPROVAL),
    )
    db_session.add(user)
    db_session.commit()

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"phone": "13800002021", "password": "Pass123456", "tenant_code": "tenant_pending_refresh"},
    )
    assert login_resp.status_code == 200
    login_payload = login_resp.json()

    refresh_resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_payload["refresh_token"]},
    )
    assert refresh_resp.status_code == 200
    refreshed_payload = refresh_resp.json()
    assert refreshed_payload["access_token"]
    assert refreshed_payload["refresh_token"]

    me_resp = client.get("/api/v1/users/me", headers=_auth_header(refreshed_payload["access_token"]))
    assert me_resp.status_code == 200
    assert me_resp.json()["status"] == int(UserStatus.PENDING_APPROVAL)


def test_login_creates_auth_session_and_refresh_rotates_token(client, db_session, seeded_data):
    _ = seeded_data
    lawyer = db_session.query(User).filter(User.phone == "13800000001").one()
    existing_session_ids = {
        session.id for session in db_session.query(AuthSession).filter(AuthSession.user_id == lawyer.id).all()
    }
    login_payload = _login_lawyer(client)

    sessions = db_session.query(AuthSession).filter(AuthSession.user_id == lawyer.id).all()
    login_sessions = [session for session in sessions if session.id not in existing_session_ids]
    assert len(login_sessions) == 1
    original_hash = login_sessions[0].refresh_token_hash
    assert login_sessions[0].is_revoked is False

    refresh_resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_payload["refresh_token"]},
    )
    assert refresh_resp.status_code == 200
    refreshed_payload = refresh_resp.json()
    assert refreshed_payload["refresh_token"] != login_payload["refresh_token"]

    db_session.expire_all()
    rotated_session = db_session.query(AuthSession).filter(AuthSession.id == login_sessions[0].id).one()
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


def test_refresh_rejects_non_numeric_subject(client):
    refresh_token = jwt.encode(
        {
            "sub": "invalid-user-id",
            "sid": 1,
            "tenant_id": 1,
            "token_type": REFRESH_TOKEN_TYPE,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    refresh_resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert refresh_resp.status_code == 401
    assert refresh_resp.json().get("code") == "AUTH_REQUIRED"


def test_logout_endpoint_revokes_current_refresh_session(client, db_session, seeded_data):
    _ = seeded_data
    lawyer = db_session.query(User).filter(User.phone == "13800000001").one()
    existing_session_ids = {
        session.id for session in db_session.query(AuthSession).filter(AuthSession.user_id == lawyer.id).all()
    }
    login_payload = _login_lawyer(client)
    login_session = (
        db_session.query(AuthSession)
        .filter(AuthSession.user_id == lawyer.id, AuthSession.id.not_in(existing_session_ids))
        .one()
    )

    logout_resp = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": login_payload["refresh_token"]},
        headers=_auth_header(login_payload["access_token"]),
    )
    assert logout_resp.status_code == 204

    db_session.expire_all()
    session = db_session.query(AuthSession).filter(AuthSession.id == login_session.id).one()
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
    lawyer = db_session.query(User).filter(User.phone == "13800000001").one()
    existing_session_ids = {
        session.id for session in db_session.query(AuthSession).filter(AuthSession.user_id == lawyer.id).all()
    }
    login_payload = _login_lawyer(client)
    login_session = (
        db_session.query(AuthSession)
        .filter(AuthSession.user_id == lawyer.id, AuthSession.id.not_in(existing_session_ids))
        .one()
    )

    logout_resp = client.post(
        "/api/v1/auth/logout",
        headers=_auth_header(login_payload["access_token"]),
    )
    assert logout_resp.status_code == 204

    db_session.expire_all()
    session = db_session.query(AuthSession).filter(AuthSession.id == login_session.id).one()
    assert session.is_revoked is True

    me_resp = client.get("/api/v1/users/me", headers=_auth_header(login_payload["access_token"]))
    assert me_resp.status_code == 401
    assert me_resp.json().get("code") == "AUTH_REQUIRED"


def test_access_token_without_session_is_rejected(client, db_session, seeded_data):
    _ = seeded_data
    lawyer = db_session.query(User).filter(User.phone == "13800000001").one()
    legacy_token = create_access_token(
        lawyer.id,
        extra_data={
            "tenant_id": lawyer.tenant_id,
            "role": lawyer.role,
            "is_tenant_admin": lawyer.is_tenant_admin,
        },
    )

    me_resp = client.get("/api/v1/users/me", headers=_auth_header(legacy_token))
    assert me_resp.status_code == 401
    assert me_resp.json().get("code") == "AUTH_REQUIRED"


def test_personal_tenant_creation_returns_session_bound_access_token(client, db_session):
    response = client.post(
        "/api/v1/tenants/personal",
        json={
            "workspace_name": "Bootstrap Workspace",
            "admin_phone": "13800009991",
            "admin_password": "Pass123456",
            "admin_real_name": "Bootstrap Admin",
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["access_token"]
    assert payload["token_type"] == "bearer"

    db_session.expire_all()
    created_user = db_session.query(User).filter(User.phone == "13800009991").one()
    created_session = db_session.query(AuthSession).filter(AuthSession.user_id == created_user.id).one()
    assert created_session.channel == "tenant_bootstrap"
    assert created_session.is_revoked is False

    me_resp = client.get("/api/v1/users/me", headers=_auth_header(payload["access_token"]))
    assert me_resp.status_code == 200
    assert me_resp.json()["phone"] == "13800009991"
