from __future__ import annotations

from app.core.security import get_password_hash
from app.core.statuses import UserStatus
from app.models.tenant import Tenant
from app.models.user import User
from app.modules.auth.service import issue_session_bound_access_token


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _make_token(db_session, user: User) -> str:
    return issue_session_bound_access_token(db_session, user=user, channel="test_users_api")


def test_tenant_admin_can_list_lawyers_and_pending_users(client, db_session):
    tenant = Tenant(tenant_code="tenant_users_api_1", name="Tenant Users API", type="organization", status=1)
    other_tenant = Tenant(tenant_code="tenant_users_api_2", name="Other Tenant Users API", type="organization", status=1)
    db_session.add_all([tenant, other_tenant])
    db_session.flush()

    tenant_admin = User(
        tenant_id=tenant.id,
        role="tenant_admin",
        is_tenant_admin=True,
        phone="13800003001",
        password_hash=get_password_hash("pwd123456"),
        real_name="Tenant Admin",
        status=int(UserStatus.ACTIVE),
    )
    active_lawyer = User(
        tenant_id=tenant.id,
        role="lawyer",
        is_tenant_admin=False,
        phone="13800003002",
        password_hash=get_password_hash("pwd123456"),
        real_name="Active Lawyer",
        status=int(UserStatus.ACTIVE),
    )
    pending_lawyer = User(
        tenant_id=tenant.id,
        role="lawyer",
        is_tenant_admin=False,
        phone="13800003003",
        password_hash=get_password_hash("pwd123456"),
        real_name="Pending Lawyer",
        status=int(UserStatus.PENDING_APPROVAL),
    )
    tenant_client = User(
        tenant_id=tenant.id,
        role="client",
        is_tenant_admin=False,
        phone="13800003004",
        password_hash=get_password_hash("pwd123456"),
        real_name="Tenant Client",
        status=int(UserStatus.ACTIVE),
    )
    external_lawyer = User(
        tenant_id=other_tenant.id,
        role="lawyer",
        is_tenant_admin=False,
        phone="13800003005",
        password_hash=get_password_hash("pwd123456"),
        real_name="External Lawyer",
        status=int(UserStatus.ACTIVE),
    )
    db_session.add_all([tenant_admin, active_lawyer, pending_lawyer, tenant_client, external_lawyer])
    db_session.commit()

    admin_token = _make_token(db_session, tenant_admin)

    lawyers_resp = client.get("/api/v1/users/lawyers", headers=_auth_header(admin_token))
    assert lawyers_resp.status_code == 200
    lawyer_phones = {item["phone"] for item in lawyers_resp.json()}
    assert "13800003001" in lawyer_phones
    assert "13800003002" in lawyer_phones
    assert "13800003003" in lawyer_phones
    assert "13800003004" not in lawyer_phones
    assert "13800003005" not in lawyer_phones

    pending_resp = client.get("/api/v1/users/pending", headers=_auth_header(admin_token))
    assert pending_resp.status_code == 200
    pending_payload = pending_resp.json()
    assert len(pending_payload) == 1
    assert pending_payload[0]["phone"] == "13800003003"


def test_tenant_admin_can_reject_pending_user(client, db_session):
    tenant = Tenant(tenant_code="tenant_users_reject", name="Tenant Users Reject", type="organization", status=1)
    db_session.add(tenant)
    db_session.flush()

    tenant_admin = User(
        tenant_id=tenant.id,
        role="tenant_admin",
        is_tenant_admin=True,
        phone="13800003011",
        password_hash=get_password_hash("pwd123456"),
        real_name="Tenant Admin",
        status=int(UserStatus.ACTIVE),
    )
    pending_lawyer = User(
        tenant_id=tenant.id,
        role="lawyer",
        is_tenant_admin=False,
        phone="13800003012",
        password_hash=get_password_hash("pwd123456"),
        real_name="Pending Lawyer",
        status=int(UserStatus.PENDING_APPROVAL),
    )
    db_session.add_all([tenant_admin, pending_lawyer])
    db_session.commit()

    admin_token = _make_token(db_session, tenant_admin)
    pending_user_id = pending_lawyer.id
    reject_resp = client.delete(
        f"/api/v1/users/{pending_user_id}/reject",
        headers=_auth_header(admin_token),
    )
    assert reject_resp.status_code == 204

    db_session.expire_all()
    rejected_user = db_session.query(User).filter(User.id == pending_user_id).first()
    assert rejected_user is None


def test_tenant_admin_can_invite_lawyer(client, db_session):
    tenant = Tenant(tenant_code="tenant_users_invite", name="Tenant Users Invite", type="organization", status=1)
    db_session.add(tenant)
    db_session.flush()

    tenant_admin = User(
        tenant_id=tenant.id,
        role="tenant_admin",
        is_tenant_admin=True,
        phone="13800003021",
        password_hash=get_password_hash("pwd123456"),
        real_name="Tenant Admin",
        status=int(UserStatus.ACTIVE),
    )
    db_session.add(tenant_admin)
    db_session.commit()

    admin_token = _make_token(db_session, tenant_admin)
    invite_resp = client.post(
        "/api/v1/users/invite-lawyer",
        headers=_auth_header(admin_token),
    )
    assert invite_resp.status_code == 201
    payload = invite_resp.json()
    assert payload["token"]
    assert payload["register_path"].startswith("pages/login/index?scene=lawyer-invite&token=")
