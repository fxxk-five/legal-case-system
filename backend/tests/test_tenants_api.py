from __future__ import annotations

from app.core.security import get_password_hash
from app.core.statuses import UserStatus
from app.models.auth_session import AuthSession
from app.models.tenant import Tenant
from app.models.user import User
from app.modules.auth.service import issue_session_bound_access_token


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _make_token(db_session, user: User) -> str:
    return issue_session_bound_access_token(db_session, user=user, channel="test_tenants_api")


def test_create_organization_tenant_returns_session_bound_access_token(client, db_session):
    response = client.post(
        "/api/v1/tenants/organization",
        json={
            "name": "Org Workspace",
            "contact_name": "Owner",
            "admin_phone": "13800004001",
            "admin_password": "Pass123456",
            "admin_real_name": "Org Admin",
            "tenant_code": "org-workspace",
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["access_token"]
    assert payload["tenant"]["tenant_code"] == "org-workspace"
    assert payload["tenant"]["type"] == "organization"

    db_session.expire_all()
    created_user = db_session.query(User).filter(User.phone == "13800004001").one()
    created_session = db_session.query(AuthSession).filter(AuthSession.user_id == created_user.id).one()
    assert created_session.channel == "tenant_bootstrap"
    assert created_session.is_revoked is False


def test_tenant_admin_can_read_and_update_current_tenant(client, db_session):
    tenant = Tenant(tenant_code="tenant_current_api", name="Tenant Current", type="organization", status=1)
    db_session.add(tenant)
    db_session.flush()

    tenant_admin = User(
        tenant_id=tenant.id,
        role="tenant_admin",
        is_tenant_admin=True,
        phone="13800004011",
        password_hash=get_password_hash("pwd123456"),
        real_name="Tenant Admin",
        status=int(UserStatus.ACTIVE),
    )
    db_session.add(tenant_admin)
    db_session.commit()

    token = _make_token(db_session, tenant_admin)

    current_resp = client.get("/api/v1/tenants/current", headers=_auth_header(token))
    assert current_resp.status_code == 200
    assert current_resp.json()["tenant_code"] == "tenant_current_api"

    update_resp = client.patch(
        "/api/v1/tenants/current",
        json={"name": "Tenant Current Updated"},
        headers=_auth_header(token),
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Tenant Current Updated"

    db_session.expire_all()
    updated_tenant = db_session.query(Tenant).filter(Tenant.id == tenant.id).one()
    assert updated_tenant.name == "Tenant Current Updated"


def test_personal_tenant_join_creates_pending_user(client, db_session):
    tenant = Tenant(tenant_code="tenant_join_api", name="Tenant Join API", type="personal", status=1)
    db_session.add(tenant)
    db_session.commit()

    response = client.post(
        "/api/v1/tenants/join",
        json={
            "tenant_code": "tenant_join_api",
            "phone": "13800004021",
            "password": "Pass123456",
            "real_name": "Join Member",
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["tenant"]["tenant_code"] == "tenant_join_api"
    assert payload["status"] == int(UserStatus.PENDING_APPROVAL)

    created_user = db_session.query(User).filter(User.phone == "13800004021").one()
    assert created_user.tenant_id == tenant.id
    assert created_user.status == int(UserStatus.PENDING_APPROVAL)
