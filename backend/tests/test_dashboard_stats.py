from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.security import create_access_token, get_password_hash
from app.models.case import Case
from app.models.file import File
from app.models.user import User


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _normalize_dt(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def test_login_updates_login_audit_fields(client, db_session, seeded_data):
    _ = seeded_data
    lawyer = db_session.query(User).filter(User.phone == "13800000001").first()
    assert lawyer is not None

    old_previous = datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc)
    old_last = datetime(2026, 3, 21, 10, 30, tzinfo=timezone.utc)
    lawyer.previous_login_at = old_previous
    lawyer.last_login_at = old_last
    db_session.add(lawyer)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"phone": "13800000001", "password": "pwd123456"},
    )
    assert response.status_code == 200

    db_session.refresh(lawyer)
    assert _normalize_dt(lawyer.previous_login_at) == _normalize_dt(old_last)
    assert lawyer.last_login_at is not None
    assert _normalize_dt(lawyer.last_login_at) > _normalize_dt(old_last)


def test_dashboard_stats_include_delta_since_previous_login(client, db_session, seeded_data):
    tenant = seeded_data["tenant"]
    baseline = datetime(2026, 3, 22, 8, 0, tzinfo=timezone.utc)
    old_time = baseline - timedelta(days=2)
    new_time = baseline + timedelta(hours=4)

    admin = User(
        tenant_id=tenant.id,
        role="tenant_admin",
        is_tenant_admin=True,
        phone="13800000009",
        password_hash=get_password_hash("pwd123456"),
        real_name="Admin",
        status=1,
        previous_login_at=baseline,
        last_login_at=baseline + timedelta(days=1),
    )
    db_session.add(admin)
    db_session.flush()

    for phone in ["13800000001", "13800000002", "13800000003"]:
        user = db_session.query(User).filter(User.phone == phone).first()
        assert user is not None
        user.created_at = old_time
        user.updated_at = old_time
        db_session.add(user)

    existing_case = db_session.query(Case).filter(Case.case_number == "CASE-001").first()
    assert existing_case is not None
    existing_case.created_at = old_time
    existing_case.updated_at = old_time
    db_session.add(existing_case)

    existing_file = db_session.query(File).filter(File.file_name == "claim.pdf").first()
    assert existing_file is not None
    existing_file.created_at = old_time
    existing_file.updated_at = old_time
    db_session.add(existing_file)

    new_client = User(
        tenant_id=tenant.id,
        role="client",
        is_tenant_admin=False,
        phone="13800000010",
        password_hash=get_password_hash("pwd123456"),
        real_name="New Client",
        status=1,
    )
    pending_lawyer = User(
        tenant_id=tenant.id,
        role="lawyer",
        is_tenant_admin=False,
        phone="13800000011",
        password_hash=get_password_hash("pwd123456"),
        real_name="Pending Lawyer",
        status=0,
    )
    db_session.add_all([new_client, pending_lawyer])
    db_session.flush()
    new_client.created_at = new_time
    new_client.updated_at = new_time
    pending_lawyer.created_at = new_time
    pending_lawyer.updated_at = new_time

    new_case = Case(
        tenant_id=tenant.id,
        case_number="CASE-002",
        title="New Risk Case",
        client_id=new_client.id,
        assigned_lawyer_id=admin.id,
        status="processing",
        deadline=baseline + timedelta(days=10),
    )
    db_session.add(new_case)
    db_session.flush()
    new_case.created_at = new_time
    new_case.updated_at = new_time

    new_files = [
        File(
            tenant_id=tenant.id,
            case_id=new_case.id,
            uploader_id=admin.id,
            uploader_role="tenant_admin",
            file_name="new-1.pdf",
            file_url="storage/tenant_demo/new-1.pdf",
            file_type="application/pdf",
        ),
        File(
            tenant_id=tenant.id,
            case_id=new_case.id,
            uploader_id=admin.id,
            uploader_role="tenant_admin",
            file_name="new-2.pdf",
            file_url="storage/tenant_demo/new-2.pdf",
            file_type="application/pdf",
        ),
        File(
            tenant_id=tenant.id,
            case_id=existing_case.id,
            uploader_id=admin.id,
            uploader_role="tenant_admin",
            file_name="existing-case-new.pdf",
            file_url="storage/tenant_demo/existing-case-new.pdf",
            file_type="application/pdf",
        ),
    ]
    db_session.add_all(new_files)
    db_session.flush()
    for item in new_files:
        item.created_at = new_time
        item.updated_at = new_time
        db_session.add(item)

    db_session.add(admin)
    db_session.commit()

    admin_token = create_access_token(
        admin.id,
        extra_data={
            "tenant_id": admin.tenant_id,
            "role": admin.role,
            "is_tenant_admin": admin.is_tenant_admin,
        },
    )

    response = client.get("/api/v1/stats/dashboard", headers=_auth_header(admin_token))
    assert response.status_code == 200
    payload = response.json()

    assert payload["case_total"] == 2
    assert payload["case_in_progress"] == 2
    assert payload["case_closed"] == 0
    assert payload["client_total"] == 3
    assert payload["pending_member_count"] == 1
    assert payload["can_view_pending_members"] is True
    assert payload["has_login_baseline"] is True
    assert payload["delta_since"]
    assert payload["delta_case_count"] == 1
    assert payload["delta_file_count"] == 3
    assert payload["delta_file_case_count"] == 2
    assert payload["delta_deadline_risk_count"] == 1
    assert payload["delta_pending_member_count"] == 1
