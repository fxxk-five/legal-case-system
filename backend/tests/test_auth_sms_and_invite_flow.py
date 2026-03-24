from __future__ import annotations

from datetime import timedelta

from app.core.security import create_access_token, get_password_hash
from app.models.invite import Invite
from app.models.tenant import Tenant
from app.models.user import User


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _send_sms_and_verify(client, phone: str, purpose: str = "register") -> str:
    send_resp = client.post("/api/v1/auth/sms/send", json={"phone": phone, "purpose": purpose})
    assert send_resp.status_code == 200

    request_id = send_resp.json()["request_id"]

    from app.main import app

    session_factory = app.state.session_factory
    with session_factory() as db:
        from app.models.sms_code import SmsCode

        sms = db.query(SmsCode).filter(SmsCode.request_id == request_id).first()
        assert sms is not None
        verify_resp = client.post(
            "/api/v1/auth/sms/verify",
            json={"phone": phone, "code": sms.code, "purpose": purpose},
        )
    assert verify_resp.status_code == 200
    return verify_resp.json()["verification_token"]


def _send_sms_and_get_code(client, phone: str, purpose: str = "login") -> str:
    send_resp = client.post("/api/v1/auth/sms/send", json={"phone": phone, "purpose": purpose})
    assert send_resp.status_code == 200
    request_id = send_resp.json()["request_id"]

    from app.main import app

    session_factory = app.state.session_factory
    with session_factory() as db:
        from app.models.sms_code import SmsCode

        sms = db.query(SmsCode).filter(SmsCode.request_id == request_id).first()
        assert sms is not None
        return sms.code


def test_sms_send_verify_register_success(client):
    token = _send_sms_and_verify(client, "13800001001")
    assert token


def test_sms_login_success_after_code_verification(client, db_session):
    tenant = Tenant(tenant_code="tenant_sms_login_1", name="Tenant SMS Login", type="personal", status=1)
    db_session.add(tenant)
    db_session.flush()
    user = User(
        tenant_id=tenant.id,
        role="lawyer",
        is_tenant_admin=False,
        phone="13800001031",
        password_hash=get_password_hash("Pass123456"),
        real_name="Sms Login User",
        status=1,
    )
    db_session.add(user)
    db_session.commit()

    code = _send_sms_and_get_code(client, "13800001031", purpose="login")
    response = client.post(
        "/api/v1/auth/sms-login",
        json={
            "phone": "13800001031",
            "code": code,
            "tenant_code": "tenant_sms_login_1",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"]
    assert payload["refresh_token"]


def test_sms_login_requires_tenant_code_when_phone_exists_in_multiple_tenants(client, db_session):
    tenant_a = Tenant(tenant_code="tenant_sms_login_a", name="Tenant SMS A", type="organization", status=1)
    tenant_b = Tenant(tenant_code="tenant_sms_login_b", name="Tenant SMS B", type="organization", status=1)
    db_session.add_all([tenant_a, tenant_b])
    db_session.flush()
    db_session.add_all(
        [
            User(
                tenant_id=tenant_a.id,
                role="lawyer",
                is_tenant_admin=False,
                phone="13800001032",
                password_hash=get_password_hash("Pass123456"),
                real_name="Sms Multi A",
                status=1,
            ),
            User(
                tenant_id=tenant_b.id,
                role="lawyer",
                is_tenant_admin=False,
                phone="13800001032",
                password_hash=get_password_hash("Pass123456"),
                real_name="Sms Multi B",
                status=1,
            ),
        ]
    )
    db_session.commit()

    code = _send_sms_and_get_code(client, "13800001032", purpose="login")
    ambiguous_resp = client.post(
        "/api/v1/auth/sms-login",
        json={
            "phone": "13800001032",
            "code": code,
        },
    )
    assert ambiguous_resp.status_code == 400
    assert ambiguous_resp.json()["code"] == "VALIDATION_ERROR"

    success_resp = client.post(
        "/api/v1/auth/sms-login",
        json={
            "phone": "13800001032",
            "code": code,
            "tenant_code": "tenant_sms_login_a",
        },
    )
    assert success_resp.status_code == 200
    assert success_resp.json()["access_token"]


def test_sms_verify_wrong_code_too_many_times_is_rate_limited(client):
    send_resp = client.post("/api/v1/auth/sms/send", json={"phone": "13800001020", "purpose": "register"})
    assert send_resp.status_code == 200

    for _ in range(4):
        bad_resp = client.post(
            "/api/v1/auth/sms/verify",
            json={"phone": "13800001020", "code": "000000", "purpose": "register"},
        )
        assert bad_resp.status_code == 400
        assert bad_resp.json()["code"] == "SMS_CODE_INVALID"

    locked_resp = client.post(
        "/api/v1/auth/sms/verify",
        json={"phone": "13800001020", "code": "000000", "purpose": "register"},
    )
    assert locked_resp.status_code == 429
    assert locked_resp.json()["code"] == "SMS_CODE_RATE_LIMITED"


def test_sms_verify_expired_code(client):
    send_resp = client.post("/api/v1/auth/sms/send", json={"phone": "13800001003", "purpose": "register"})
    assert send_resp.status_code == 200
    request_id = send_resp.json()["request_id"]

    from app.main import app

    session_factory = app.state.session_factory
    with session_factory() as db:
        from app.models.sms_code import SmsCode

        sms = db.query(SmsCode).filter(SmsCode.request_id == request_id).first()
        assert sms is not None
        sms.expires_at = sms.expires_at - timedelta(minutes=10)
        db.add(sms)
        db.commit()

    verify_resp = client.post(
        "/api/v1/auth/sms/verify",
        json={"phone": "13800001003", "code": "000000", "purpose": "register"},
    )
    assert verify_resp.status_code == 400
    assert verify_resp.json()["code"] == "SMS_CODE_EXPIRED"


def test_register_requires_phone_verification(client, db_session):
    tenant = Tenant(tenant_code="tenant_sms_1", name="Tenant SMS", type="organization", status=1)
    db_session.add(tenant)
    db_session.commit()

    resp = client.post(
        "/api/v1/auth/register",
        json={
            "phone": "13800001004",
            "password": "Pass123456",
            "real_name": "NoVerify",
            "tenant_code": "tenant_sms_1",
            "phone_verification_token": "invalid_token_123",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "PHONE_NOT_VERIFIED"


def test_register_success_after_phone_verification(client, db_session):
    tenant = Tenant(tenant_code="tenant_sms_2", name="Tenant SMS2", type="personal", status=1)
    db_session.add(tenant)
    db_session.commit()

    verify_token = _send_sms_and_verify(client, "13800001005")
    register_resp = client.post(
        "/api/v1/auth/register",
        json={
            "phone": "13800001005",
            "password": "Pass123456",
            "real_name": "Verified User",
            "tenant_code": "tenant_sms_2",
            "phone_verification_token": verify_token,
        },
    )
    assert register_resp.status_code == 201
    payload = register_resp.json()
    assert payload["phone"] == "13800001005"


def test_invite_register_requires_valid_invite(client, db_session):
    tenant = Tenant(tenant_code="tenant_invite_1", name="Tenant Invite", type="organization", status=1)
    db_session.add(tenant)
    db_session.flush()

    admin = User(
        tenant_id=tenant.id,
        role="tenant_admin",
        is_tenant_admin=True,
        phone="13800001006",
        password_hash=get_password_hash("Pass123456"),
        real_name="Invite Admin",
        status=1,
    )
    db_session.add(admin)
    db_session.commit()

    verify_token = _send_sms_and_verify(client, "13800001007")
    resp = client.post(
        "/api/v1/auth/invite-register",
        json={
            "token": "not-exist-token",
            "phone": "13800001007",
            "password": "Pass123456",
            "real_name": "Invitee",
            "phone_verification_token": verify_token,
        },
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "INVITE_NOT_FOUND"


def test_invite_register_pending_user_login_forbidden_until_approved(client, db_session):
    tenant = Tenant(tenant_code="tenant_join_1", name="Tenant Join", type="organization", status=1)
    db_session.add(tenant)
    db_session.flush()

    admin = User(
        tenant_id=tenant.id,
        role="tenant_admin",
        is_tenant_admin=True,
        phone="13800001008",
        password_hash=get_password_hash("Pass123456"),
        real_name="Join Admin",
        status=1,
    )
    db_session.add(admin)
    db_session.flush()

    invite = Invite(
        tenant_id=tenant.id,
        invited_by_user_id=admin.id,
        role="lawyer",
        token="invite-token-join-1",
        expires_at=admin.created_at + timedelta(days=7),
        status="pending",
    )
    db_session.add(invite)
    db_session.commit()

    verify_token = _send_sms_and_verify(client, "13800001018")
    reg_resp = client.post(
        "/api/v1/auth/invite-register",
        json={
            "token": "invite-token-join-1",
            "phone": "13800001018",
            "password": "Pass123456",
            "real_name": "Join User",
            "phone_verification_token": verify_token,
        },
    )
    assert reg_resp.status_code == 201
    assert reg_resp.json()["status"] == 0

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"phone": "13800001018", "password": "Pass123456", "tenant_code": "tenant_join_1"},
    )
    assert login_resp.status_code == 403
    assert login_resp.json()["code"] == "USER_NOT_ACTIVE"

    admin_token = create_access_token(
        admin.id,
        extra_data={
            "tenant_id": admin.tenant_id,
            "role": admin.role,
            "is_tenant_admin": admin.is_tenant_admin,
        },
    )
    approve_resp = client.patch(
        f"/api/v1/users/{reg_resp.json()['id']}/approve",
        headers=_auth_header(admin_token),
    )
    assert approve_resp.status_code == 200

    login_ok = client.post(
        "/api/v1/auth/login",
        json={"phone": "13800001018", "password": "Pass123456", "tenant_code": "tenant_join_1"},
    )
    assert login_ok.status_code == 200
    assert login_ok.json()["access_token"]


def test_super_admin_can_list_all_tenants_and_users(client, db_session):
    t1 = Tenant(tenant_code="tenant_sa_1", name="Tenant SA 1", type="organization", status=1)
    t2 = Tenant(tenant_code="tenant_sa_2", name="Tenant SA 2", type="organization", status=1)
    db_session.add_all([t1, t2])
    db_session.flush()

    u1 = User(
        tenant_id=t1.id,
        role="lawyer",
        is_tenant_admin=False,
        phone="13800001009",
        password_hash=get_password_hash("Pass123456"),
        real_name="Tenant1 Lawyer",
        status=1,
    )
    u2 = User(
        tenant_id=t2.id,
        role="lawyer",
        is_tenant_admin=False,
        phone="13800001010",
        password_hash=get_password_hash("Pass123456"),
        real_name="Tenant2 Lawyer",
        status=1,
    )
    super_admin = User(
        tenant_id=t1.id,
        role="super_admin",
        is_tenant_admin=False,
        phone="13800001011",
        password_hash=get_password_hash("Pass123456"),
        real_name="Super Admin",
        status=1,
    )
    db_session.add_all([u1, u2, super_admin])
    db_session.commit()

    token = create_access_token(
        super_admin.id,
        extra_data={
            "tenant_id": super_admin.tenant_id,
            "role": super_admin.role,
            "is_tenant_admin": super_admin.is_tenant_admin,
        },
    )

    tenants_resp = client.get("/api/v1/tenants", headers=_auth_header(token))
    assert tenants_resp.status_code == 200
    tenant_codes = {item["tenant_code"] for item in tenants_resp.json()}
    assert "tenant_sa_1" in tenant_codes
    assert "tenant_sa_2" in tenant_codes

    users_resp = client.get("/api/v1/users", headers=_auth_header(token))
    assert users_resp.status_code == 200
    users = users_resp.json()
    assert any(item["phone"] == "13800001009" for item in users)
    assert any(item["phone"] == "13800001010" for item in users)


def test_non_super_admin_cannot_list_all_tenants_and_users(client, db_session):
    tenant = Tenant(tenant_code="tenant_no_sa", name="Tenant No SA", type="organization", status=1)
    db_session.add(tenant)
    db_session.flush()

    normal_user = User(
        tenant_id=tenant.id,
        role="tenant_admin",
        is_tenant_admin=True,
        phone="13800001012",
        password_hash=get_password_hash("Pass123456"),
        real_name="Tenant Admin",
        status=1,
    )
    db_session.add(normal_user)
    db_session.commit()

    token = create_access_token(
        normal_user.id,
        extra_data={
            "tenant_id": normal_user.tenant_id,
            "role": normal_user.role,
            "is_tenant_admin": normal_user.is_tenant_admin,
        },
    )

    tenants_resp = client.get("/api/v1/tenants", headers=_auth_header(token))
    assert tenants_resp.status_code == 403
    assert tenants_resp.json()["code"] == "FORBIDDEN"

    users_resp = client.get("/api/v1/users", headers=_auth_header(token))
    assert users_resp.status_code == 403
    assert users_resp.json()["code"] == "FORBIDDEN"


def test_org_tenant_register_requires_invite(client, db_session):
    tenant = Tenant(tenant_code="tenant_org_1", name="Tenant Org", type="organization", status=1)
    db_session.add(tenant)
    db_session.commit()

    verify_token = _send_sms_and_verify(client, "13800001019")
    register_resp = client.post(
        "/api/v1/auth/register",
        json={
            "phone": "13800001019",
            "password": "Pass123456",
            "real_name": "Org Direct Register",
            "tenant_code": "tenant_org_1",
            "phone_verification_token": verify_token,
        },
    )
    assert register_resp.status_code == 400
    assert register_resp.json()["code"] == "INVITE_REQUIRED"


def test_phone_password_validation_in_schema(client):
    resp = client.post(
        "/api/v1/auth/sms/send",
        json={"phone": "123456", "purpose": "register"},
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"phone": "13800001013", "password": "simple"},
    )
    assert login_resp.status_code == 422
    assert login_resp.json()["code"] == "VALIDATION_ERROR"
