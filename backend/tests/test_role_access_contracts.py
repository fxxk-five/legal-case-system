from __future__ import annotations

from app.core.security import create_access_token, get_password_hash
from app.models.case import Case
from app.models.file import File
from app.models.notification import Notification
from app.models.tenant import Tenant
from app.models.user import User


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _mini_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Client-Platform": "mini-program",
        "X-Client-Source": "wx-mini",
    }


def test_invite_qrcode_requires_mini_program_source(client, seeded_data):
    case_id = seeded_data["case"].id
    lawyer_token = seeded_data["lawyer_token"]

    forbidden_resp = client.get(f"/api/v1/cases/{case_id}/invite-qrcode", headers=_auth_header(lawyer_token))
    assert forbidden_resp.status_code == 403
    assert forbidden_resp.json()["code"] == "FORBIDDEN"

    ok_resp = client.get(f"/api/v1/cases/{case_id}/invite-qrcode", headers=_mini_headers(lawyer_token))
    assert ok_resp.status_code == 200
    payload = ok_resp.json()
    assert payload["case_id"] == case_id
    assert payload["tenant_id"] == seeded_data["tenant"].id
    assert payload["token"]
    assert payload["path"].startswith("pages/login/index?scene=client-case&token=")


def test_client_file_upload_policy_requires_mini_program_source(client, seeded_data):
    case_id = seeded_data["case"].id
    client_token = seeded_data["client_token"]

    forbidden_resp = client.get(
        f"/api/v1/files/upload-policy?case_id={case_id}&file_name=evidence.pdf",
        headers=_auth_header(client_token),
    )
    assert forbidden_resp.status_code == 403
    assert forbidden_resp.json()["code"] == "FORBIDDEN"

    ok_resp = client.get(
        f"/api/v1/files/upload-policy?case_id={case_id}&file_name=evidence.pdf",
        headers=_mini_headers(client_token),
    )
    assert ok_resp.status_code == 200
    assert ok_resp.json()["file_field_name"] == "upload"


def test_personal_lawyer_cases_only_related_to_self_uploaded_files(client, db_session, seeded_data):
    tenant = seeded_data["tenant"]
    tenant.type = "personal"
    db_session.add(tenant)

    another_lawyer = User(
        tenant_id=tenant.id,
        role="lawyer",
        is_tenant_admin=False,
        phone="13800000999",
        password_hash=get_password_hash("pwd123456"),
        real_name="Another Lawyer",
        status=1,
    )
    db_session.add(another_lawyer)
    db_session.flush()

    another_case = Case(
        tenant_id=tenant.id,
        case_number="CASE-PERSONAL-OTHER",
        title="Other Personal Case",
        client_id=seeded_data["case"].client_id,
        assigned_lawyer_id=another_lawyer.id,
        status="new",
    )
    db_session.add(another_case)
    db_session.flush()

    another_case_file = File(
        tenant_id=tenant.id,
        case_id=another_case.id,
        uploader_id=another_lawyer.id,
        file_name="other.pdf",
        file_url="storage/tenant_demo/other.pdf",
        file_type="application/pdf",
    )
    db_session.add(another_case_file)
    db_session.commit()

    resp = client.get("/api/v1/cases", headers=_auth_header(seeded_data["lawyer_token"]))
    assert resp.status_code == 200
    case_ids = [item["id"] for item in resp.json()]
    assert seeded_data["case"].id in case_ids
    assert another_case.id not in case_ids


def test_personal_lawyer_hidden_case_endpoints_are_blocked(client, db_session, seeded_data):
    tenant = seeded_data["tenant"]
    tenant.type = "personal"
    db_session.add(tenant)

    another_lawyer = User(
        tenant_id=tenant.id,
        role="lawyer",
        is_tenant_admin=False,
        phone="13800000998",
        password_hash=get_password_hash("pwd123456"),
        real_name="Another Hidden Lawyer",
        status=1,
    )
    db_session.add(another_lawyer)
    db_session.flush()

    another_case = Case(
        tenant_id=tenant.id,
        case_number="CASE-PERSONAL-HIDDEN",
        title="Hidden Personal Case",
        client_id=seeded_data["case"].client_id,
        assigned_lawyer_id=another_lawyer.id,
        status="new",
    )
    db_session.add(another_case)
    db_session.flush()

    db_session.add(
        File(
            tenant_id=tenant.id,
            case_id=another_case.id,
            uploader_id=another_lawyer.id,
            file_name="hidden.pdf",
            file_url="storage/tenant_demo/hidden.pdf",
            file_type="application/pdf",
        )
    )
    db_session.commit()

    detail_resp = client.get(f"/api/v1/cases/{another_case.id}", headers=_auth_header(seeded_data["lawyer_token"]))
    assert detail_resp.status_code == 404
    assert detail_resp.json()["code"] == "CASE_NOT_FOUND"

    files_resp = client.get(f"/api/v1/files/case/{another_case.id}", headers=_auth_header(seeded_data["lawyer_token"]))
    assert files_resp.status_code == 404
    assert files_resp.json()["code"] == "CASE_NOT_FOUND"

    reports_resp = client.get(
        f"/api/v1/cases/{another_case.id}/reports",
        headers=_auth_header(seeded_data["lawyer_token"]),
    )
    assert reports_resp.status_code == 404
    assert reports_resp.json()["code"] == "CASE_NOT_FOUND"


def test_tenant_member_approve_requires_tenant_admin(client, db_session, seeded_data):
    tenant = seeded_data["tenant"]

    pending_lawyer = User(
        tenant_id=tenant.id,
        role="lawyer",
        is_tenant_admin=False,
        phone="13800000888",
        password_hash=get_password_hash("pwd123456"),
        real_name="Pending Lawyer",
        status=0,
    )
    tenant_admin = User(
        tenant_id=tenant.id,
        role="tenant_admin",
        is_tenant_admin=True,
        phone="13800000777",
        password_hash=get_password_hash("pwd123456"),
        real_name="Tenant Admin",
        status=1,
    )
    db_session.add_all([pending_lawyer, tenant_admin])
    db_session.commit()

    lawyer_forbidden = client.patch(
        f"/api/v1/tenants/members/{pending_lawyer.id}/approve",
        headers=_auth_header(seeded_data["lawyer_token"]),
    )
    assert lawyer_forbidden.status_code == 403
    assert lawyer_forbidden.json()["code"] == "FORBIDDEN"

    admin_token = create_access_token(
        tenant_admin.id,
        extra_data={
            "tenant_id": tenant_admin.tenant_id,
            "role": tenant_admin.role,
            "is_tenant_admin": tenant_admin.is_tenant_admin,
        },
    )
    approved_resp = client.patch(
        f"/api/v1/tenants/members/{pending_lawyer.id}/approve",
        headers=_auth_header(admin_token),
    )
    assert approved_resp.status_code == 200
    assert approved_resp.json()["status"] == 1


def test_lawyer_cannot_read_case_from_other_tenant_even_with_same_role(client, db_session, seeded_data):
    another_tenant = Tenant(
        tenant_code="tenant_cross_case",
        name="Tenant Cross Case",
        type="organization",
        status=1,
    )
    db_session.add(another_tenant)
    db_session.flush()

    another_lawyer = User(
        tenant_id=another_tenant.id,
        role="lawyer",
        is_tenant_admin=False,
        phone="13800000601",
        password_hash=get_password_hash("pwd123456"),
        real_name="Cross Tenant Lawyer",
        status=1,
    )
    db_session.add(another_lawyer)
    db_session.commit()

    another_lawyer_token = create_access_token(
        another_lawyer.id,
        extra_data={
            "tenant_id": another_lawyer.tenant_id,
            "role": another_lawyer.role,
            "is_tenant_admin": another_lawyer.is_tenant_admin,
        },
    )

    resp = client.get(f"/api/v1/cases/{seeded_data['case'].id}", headers=_auth_header(another_lawyer_token))
    assert resp.status_code == 404
    assert resp.json()["code"] == "CASE_NOT_FOUND"


def test_tenant_admin_cannot_approve_member_from_other_tenant(client, db_session, seeded_data):
    tenant_a = seeded_data["tenant"]
    pending_lawyer = User(
        tenant_id=tenant_a.id,
        role="lawyer",
        is_tenant_admin=False,
        phone="13800000602",
        password_hash=get_password_hash("pwd123456"),
        real_name="Tenant A Pending Lawyer",
        status=0,
    )
    another_tenant = Tenant(
        tenant_code="tenant_cross_member",
        name="Tenant Cross Member",
        type="organization",
        status=1,
    )
    db_session.add_all([pending_lawyer, another_tenant])
    db_session.flush()

    another_admin = User(
        tenant_id=another_tenant.id,
        role="tenant_admin",
        is_tenant_admin=True,
        phone="13800000603",
        password_hash=get_password_hash("pwd123456"),
        real_name="Cross Tenant Admin",
        status=1,
    )
    db_session.add(another_admin)
    db_session.commit()

    another_admin_token = create_access_token(
        another_admin.id,
        extra_data={
            "tenant_id": another_admin.tenant_id,
            "role": another_admin.role,
            "is_tenant_admin": another_admin.is_tenant_admin,
        },
    )

    resp = client.patch(
        f"/api/v1/tenants/members/{pending_lawyer.id}/approve",
        headers=_auth_header(another_admin_token),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "USER_NOT_FOUND"

    db_session.refresh(pending_lawyer)
    assert pending_lawyer.status == 0


def test_lawyer_cannot_mark_other_tenant_notification_as_read(client, db_session, seeded_data):
    tenant_a = seeded_data["tenant"]
    tenant_a_lawyer = (
        db_session.query(User)
        .filter(
            User.tenant_id == tenant_a.id,
            User.role == "lawyer",
            User.phone == "13800000001",
        )
        .first()
    )
    assert tenant_a_lawyer is not None

    notification = Notification(
        tenant_id=tenant_a.id,
        user_id=tenant_a_lawyer.id,
        title="Cross Tenant Notification",
        content="Should not be writable by another tenant.",
        is_read=False,
    )

    another_tenant = Tenant(
        tenant_code="tenant_cross_notification",
        name="Tenant Cross Notification",
        type="organization",
        status=1,
    )
    db_session.add(another_tenant)
    db_session.flush()

    another_lawyer = User(
        tenant_id=another_tenant.id,
        role="lawyer",
        is_tenant_admin=False,
        phone="13800000604",
        password_hash=get_password_hash("pwd123456"),
        real_name="Cross Notification Lawyer",
        status=1,
    )
    db_session.add_all([notification, another_lawyer])
    db_session.commit()

    another_lawyer_token = create_access_token(
        another_lawyer.id,
        extra_data={
            "tenant_id": another_lawyer.tenant_id,
            "role": another_lawyer.role,
            "is_tenant_admin": another_lawyer.is_tenant_admin,
        },
    )

    resp = client.patch(
        f"/api/v1/notifications/{notification.id}/read",
        headers=_auth_header(another_lawyer_token),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOTIFICATION_NOT_FOUND"

    db_session.refresh(notification)
    assert notification.is_read is False
