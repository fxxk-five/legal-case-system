from __future__ import annotations

from app.core.security import create_access_token, get_password_hash
from app.models.tenant import Tenant
from app.models.user import User


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _make_token(user: User) -> str:
    return create_access_token(
        user.id,
        extra_data={
            "tenant_id": user.tenant_id,
            "role": user.role,
            "is_tenant_admin": user.is_tenant_admin,
        },
    )


def test_super_admin_can_update_tenant_status_and_invalid_reverse_transition_is_rejected(client, db_session):
    tenant = Tenant(
        tenant_code="tenant-status-flow",
        name="Tenant Status Flow",
        type="organization",
        status=1,
    )
    db_session.add(tenant)
    db_session.flush()

    super_admin = User(
        tenant_id=tenant.id,
        role="super_admin",
        is_tenant_admin=False,
        phone="13800001001",
        password_hash=get_password_hash("pwd123456"),
        real_name="Super Admin",
        status=1,
    )
    db_session.add(super_admin)
    db_session.commit()

    token = _make_token(super_admin)

    to_archived = client.patch(
        f"/api/v1/tenants/{tenant.id}/status",
        headers=_auth_header(token),
        json={"status": 3},
    )
    assert to_archived.status_code == 200
    assert to_archived.json()["status"] == 3

    back_to_active = client.patch(
        f"/api/v1/tenants/{tenant.id}/status",
        headers=_auth_header(token),
        json={"status": 1},
    )
    assert back_to_active.status_code == 409
    assert back_to_active.json()["code"] == "CONFLICT"


def test_invalid_user_status_transition_is_rejected(client, db_session, seeded_data):
    tenant = seeded_data["tenant"]

    tenant_admin = User(
        tenant_id=tenant.id,
        role="tenant_admin",
        is_tenant_admin=True,
        phone="13800001002",
        password_hash=get_password_hash("pwd123456"),
        real_name="Tenant Admin",
        status=1,
    )
    pending_lawyer = User(
        tenant_id=tenant.id,
        role="lawyer",
        is_tenant_admin=False,
        phone="13800001003",
        password_hash=get_password_hash("pwd123456"),
        real_name="Pending Lawyer",
        status=0,
    )
    db_session.add_all([tenant_admin, pending_lawyer])
    db_session.commit()

    admin_token = _make_token(tenant_admin)

    approve_resp = client.patch(
        f"/api/v1/users/{pending_lawyer.id}/approve",
        headers=_auth_header(admin_token),
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == 1

    reverse_resp = client.patch(
        f"/api/v1/users/{pending_lawyer.id}/status",
        headers=_auth_header(admin_token),
        json={"status": 0},
    )
    assert reverse_resp.status_code == 409
    assert reverse_resp.json()["code"] == "CONFLICT"


def test_org_lawyer_role_alias_can_create_case(client, db_session, seeded_data):
    tenant = seeded_data["tenant"]

    org_lawyer = User(
        tenant_id=tenant.id,
        role="org_lawyer",
        is_tenant_admin=False,
        phone="13800001004",
        password_hash=get_password_hash("pwd123456"),
        real_name="Org Lawyer",
        status=1,
    )
    db_session.add(org_lawyer)
    db_session.commit()

    org_lawyer_token = _make_token(org_lawyer)

    create_case_resp = client.post(
        "/api/v1/cases",
        headers=_auth_header(org_lawyer_token),
        json={
            "case_number": "CASE-ORG-LAWYER-001",
            "title": "Org Lawyer Create Case",
            "legal_type": "other",
            "client_phone": "13800001999",
            "client_real_name": "Client For Org Lawyer",
        },
    )
    assert create_case_resp.status_code == 201
    assert create_case_resp.json()["case_number"] == "CASE-ORG-LAWYER-001"
