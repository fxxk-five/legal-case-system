from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.statuses import UserStatus
from app.core.security import get_password_hash, verify_password
from app.modules.cases.models.case import Case
from app.modules.invites.models.invite import Invite
from app.models.tenant import Tenant
from app.models.user import User
from app.integrations.sms.service import (
    SMS_SEND_DEVICE_MAX_COUNT,
    SMS_SEND_IP_MAX_COUNT,
    SMS_VERIFY_DEVICE_MAX_COUNT,
    SMS_VERIFY_IP_MAX_COUNT,
)
from app.modules.auth.service import issue_session_bound_access_token
from app.integrations.wechat.service import create_case_invite_token


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _request_headers(*, ip: str | None = None, device: str | None = None) -> dict[str, str]:
    headers: dict[str, str] = {}
    if ip:
        headers["X-Forwarded-For"] = ip
    if device:
        headers["X-Device-Fingerprint"] = device
    return headers


def _phone(seed: int) -> str:
    return f"138{seed:08d}"


def _send_sms_and_verify(client, phone: str, purpose: str = "register", headers: dict[str, str] | None = None) -> str:
    send_resp = client.post("/api/v1/auth/sms/send", json={"phone": phone, "purpose": purpose}, headers=headers or {})
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
            headers=headers or {},
        )
    assert verify_resp.status_code == 200
    return verify_resp.json()["verification_token"]


def _send_sms_and_get_code(
    client,
    phone: str,
    purpose: str = "login",
    headers: dict[str, str] | None = None,
) -> str:
    send_resp = client.post("/api/v1/auth/sms/send", json={"phone": phone, "purpose": purpose}, headers=headers or {})
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


def test_sms_send_is_rate_limited_by_ip(client):
    shared_ip = "198.51.100.10"
    for index in range(SMS_SEND_IP_MAX_COUNT):
        response = client.post(
            "/api/v1/auth/sms/send",
            json={"phone": _phone(1000 + index), "purpose": "register"},
            headers=_request_headers(ip=shared_ip, device=f"send-ip-device-{index}"),
        )
        assert response.status_code == 200

    blocked = client.post(
        "/api/v1/auth/sms/send",
        json={"phone": _phone(2000), "purpose": "register"},
        headers=_request_headers(ip=shared_ip, device="send-ip-device-blocked"),
    )
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "SMS_CODE_RATE_LIMITED"


def test_sms_send_is_rate_limited_by_device(client):
    shared_device = "shared-send-device"
    for index in range(SMS_SEND_DEVICE_MAX_COUNT):
        response = client.post(
            "/api/v1/auth/sms/send",
            json={"phone": _phone(3000 + index), "purpose": "register"},
            headers=_request_headers(ip=f"198.51.101.{index + 1}", device=shared_device),
        )
        assert response.status_code == 200

    blocked = client.post(
        "/api/v1/auth/sms/send",
        json={"phone": _phone(4000), "purpose": "register"},
        headers=_request_headers(ip="198.51.102.1", device=shared_device),
    )
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "SMS_CODE_RATE_LIMITED"


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


def test_sms_login_allows_pending_account_with_limited_session(client, db_session):
    tenant = Tenant(tenant_code="tenant_sms_pending_1", name="Tenant SMS Pending", type="personal", status=1)
    db_session.add(tenant)
    db_session.flush()
    user = User(
        tenant_id=tenant.id,
        role="lawyer",
        is_tenant_admin=False,
        phone="13800001034",
        password_hash=get_password_hash("Pass123456"),
        real_name="Sms Pending User",
        status=int(UserStatus.PENDING_APPROVAL),
    )
    db_session.add(user)
    db_session.commit()

    code = _send_sms_and_get_code(client, "13800001034", purpose="login")
    response = client.post(
        "/api/v1/auth/sms-login",
        json={
            "phone": "13800001034",
            "code": code,
            "tenant_code": "tenant_sms_pending_1",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"]

    me_resp = client.get("/api/v1/users/me", headers=_auth_header(payload["access_token"]))
    assert me_resp.status_code == 200
    assert me_resp.json()["status"] == int(UserStatus.PENDING_APPROVAL)

    tenant_resp = client.get("/api/v1/tenants/current", headers=_auth_header(payload["access_token"]))
    assert tenant_resp.status_code == 200
    assert tenant_resp.json()["tenant_code"] == "tenant_sms_pending_1"


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

    from app.main import app

    session_factory = app.state.session_factory
    with session_factory() as db:
        from app.models.sms_code import SmsCode

        sms = (
            db.query(SmsCode)
            .filter(SmsCode.phone == "13800001032", SmsCode.purpose == "login")
            .order_by(SmsCode.created_at.desc())
            .first()
        )
        assert sms is not None
        sms.created_at = datetime.now(timezone.utc) - timedelta(seconds=120)
        db.add(sms)
        db.commit()

    code = _send_sms_and_get_code(client, "13800001032", purpose="login")
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


def test_login_advice_requires_tenant_code_when_phone_exists_in_multiple_tenants(client, db_session):
    tenant_a = Tenant(tenant_code="tenant_advice_a", name="Tenant Advice A", type="organization", status=1)
    tenant_b = Tenant(tenant_code="tenant_advice_b", name="Tenant Advice B", type="organization", status=1)
    db_session.add_all([tenant_a, tenant_b])
    db_session.flush()
    db_session.add_all(
        [
            User(
                tenant_id=tenant_a.id,
                role="lawyer",
                is_tenant_admin=False,
                phone="13800001059",
                password_hash=get_password_hash("Pass123456"),
                real_name="Advice Lawyer A",
                status=1,
            ),
            User(
                tenant_id=tenant_b.id,
                role="lawyer",
                is_tenant_admin=False,
                phone="13800001059",
                password_hash=get_password_hash("Pass123456"),
                real_name="Advice Lawyer B",
                status=1,
            ),
        ]
    )
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login-advice",
        json={"phone": "13800001059"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["requires_tenant_code"] is True
    assert payload["requires_admin_approval"] is False
    assert payload["recommended_entry"] == "web"
    assert payload["login_state"] == "ready"


def test_login_advice_pending_client_prefers_mini_program(client, db_session):
    tenant = Tenant(tenant_code="tenant_advice_client", name="Tenant Advice Client", type="organization", status=1)
    db_session.add(tenant)
    db_session.flush()
    db_session.add(
        User(
            tenant_id=tenant.id,
            role="client",
            is_tenant_admin=False,
            phone="13800001060",
            password_hash=get_password_hash("Pass123456"),
            real_name="Advice Pending Client",
            status=int(UserStatus.PENDING_APPROVAL),
        )
    )
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login-advice",
        json={"phone": "13800001060", "tenant_code": "tenant_advice_client"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["requires_tenant_code"] is False
    assert payload["requires_admin_approval"] is True
    assert payload["recommended_entry"] == "mini-program"
    assert payload["login_state"] == "pending_approval"


def test_sms_login_wrong_code_does_not_reveal_multi_tenant_state(client, db_session):
    tenant_a = Tenant(tenant_code="tenant_sms_enum_a", name="Tenant Enum A", type="organization", status=1)
    tenant_b = Tenant(tenant_code="tenant_sms_enum_b", name="Tenant Enum B", type="organization", status=1)
    db_session.add_all([tenant_a, tenant_b])
    db_session.flush()
    db_session.add_all(
        [
            User(
                tenant_id=tenant_a.id,
                role="lawyer",
                is_tenant_admin=False,
                phone="13800001033",
                password_hash=get_password_hash("Pass123456"),
                real_name="Sms Enum A",
                status=1,
            ),
            User(
                tenant_id=tenant_b.id,
                role="lawyer",
                is_tenant_admin=False,
                phone="13800001033",
                password_hash=get_password_hash("Pass123456"),
                real_name="Sms Enum B",
                status=1,
            ),
        ]
    )
    db_session.commit()

    code = _send_sms_and_get_code(client, "13800001033", purpose="login")
    wrong_code = "000000" if code != "000000" else "111111"
    response = client.post(
        "/api/v1/auth/sms-login",
        json={
            "phone": "13800001033",
            "code": wrong_code,
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "SMS_CODE_INVALID"


def test_sms_login_accepts_case_invite_context_and_binds_case(client, db_session):
    tenant_a = Tenant(tenant_code="tenant_sms_case_a", name="Tenant SMS Case A", type="organization", status=1)
    tenant_b = Tenant(tenant_code="tenant_sms_case_b", name="Tenant SMS Case B", type="organization", status=1)
    db_session.add_all([tenant_a, tenant_b])
    db_session.flush()

    lawyer = User(
        tenant_id=tenant_a.id,
        role="lawyer",
        is_tenant_admin=False,
        phone="13800001040",
        password_hash=get_password_hash("Pass123456"),
        real_name="Invite Lawyer",
        status=1,
    )
    invited_client = User(
        tenant_id=tenant_a.id,
        role="client",
        is_tenant_admin=False,
        phone="13800001041",
        password_hash=get_password_hash("Pass123456"),
        real_name="Invited Client A",
        status=1,
    )
    duplicate_client = User(
        tenant_id=tenant_b.id,
        role="client",
        is_tenant_admin=False,
        phone="13800001041",
        password_hash=get_password_hash("Pass123456"),
        real_name="Invited Client B",
        status=1,
    )
    db_session.add_all([lawyer, invited_client, duplicate_client])
    db_session.flush()

    invited_case = Case(
        tenant_id=tenant_a.id,
        case_number="CASE-SMS-INVITE-001",
        title="Invite Sms Bind",
        legal_type="other",
        client_id=None,
        assigned_lawyer_id=lawyer.id,
        status="new",
    )
    db_session.add(invited_case)
    db_session.commit()

    invite_token = create_case_invite_token(invited_case.id, tenant_a.id)
    code = _send_sms_and_get_code(client, "13800001041", purpose="login")

    response = client.post(
        "/api/v1/auth/sms-login",
        json={
            "phone": "13800001041",
            "code": code,
            "case_invite_token": invite_token,
        },
    )
    assert response.status_code == 200
    assert response.json()["access_token"]

    db_session.expire_all()
    refreshed_case = db_session.query(Case).filter(Case.id == invited_case.id).one()
    assert refreshed_case.client_id == invited_client.id


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


def test_sms_verify_is_rate_limited_by_ip(client):
    shared_ip = "203.0.113.10"
    for index in range(SMS_VERIFY_IP_MAX_COUNT):
        phone = _phone(5000 + index)
        code = _send_sms_and_get_code(
            client,
            phone,
            purpose="register",
            headers=_request_headers(ip=f"198.18.0.{(index % 200) + 1}", device=f"prepare-ip-{index}"),
        )
        wrong_code = "000000" if code != "000000" else "111111"
        response = client.post(
            "/api/v1/auth/sms/verify",
            json={"phone": phone, "code": wrong_code, "purpose": "register"},
            headers=_request_headers(ip=shared_ip, device=f"verify-ip-device-{index}"),
        )
        assert response.status_code == 400
        assert response.json()["code"] == "SMS_CODE_INVALID"

    blocked_phone = _phone(6000)
    blocked_code = _send_sms_and_get_code(
        client,
        blocked_phone,
        purpose="register",
        headers=_request_headers(ip="198.18.1.1", device="prepare-ip-blocked"),
    )
    blocked_wrong_code = "000000" if blocked_code != "000000" else "111111"
    blocked = client.post(
        "/api/v1/auth/sms/verify",
        json={"phone": blocked_phone, "code": blocked_wrong_code, "purpose": "register"},
        headers=_request_headers(ip=shared_ip, device="verify-ip-device-blocked"),
    )
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "SMS_CODE_RATE_LIMITED"


def test_sms_verify_is_rate_limited_by_device(client):
    shared_device = "shared-verify-device"
    for index in range(SMS_VERIFY_DEVICE_MAX_COUNT):
        phone = _phone(7000 + index)
        code = _send_sms_and_get_code(
            client,
            phone,
            purpose="register",
            headers=_request_headers(ip=f"198.19.0.{(index % 200) + 1}", device=f"prepare-device-{index}"),
        )
        wrong_code = "000000" if code != "000000" else "111111"
        response = client.post(
            "/api/v1/auth/sms/verify",
            json={"phone": phone, "code": wrong_code, "purpose": "register"},
            headers=_request_headers(ip=f"203.0.113.{(index % 200) + 1}", device=shared_device),
        )
        assert response.status_code == 400
        assert response.json()["code"] == "SMS_CODE_INVALID"

    blocked_phone = _phone(8000)
    blocked_code = _send_sms_and_get_code(
        client,
        blocked_phone,
        purpose="register",
        headers=_request_headers(ip="198.19.1.1", device="prepare-device-blocked"),
    )
    blocked_wrong_code = "000000" if blocked_code != "000000" else "111111"
    blocked = client.post(
        "/api/v1/auth/sms/verify",
        json={"phone": blocked_phone, "code": blocked_wrong_code, "purpose": "register"},
        headers=_request_headers(ip="203.0.114.1", device=shared_device),
    )
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "SMS_CODE_RATE_LIMITED"


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


def test_register_requires_explicit_tenant_code_even_for_single_tenant(client, db_session):
    tenant = Tenant(tenant_code="tenant_sms_explicit", name="Tenant Explicit", type="personal", status=1)
    db_session.add(tenant)
    db_session.commit()

    verify_token = _send_sms_and_verify(client, "13800001055")
    response = client.post(
        "/api/v1/auth/register",
        json={
            "phone": "13800001055",
            "password": "Pass123456",
            "real_name": "Need Tenant Code",
            "phone_verification_token": verify_token,
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_change_password_requires_current_password_when_reset_not_required(client, seeded_data):
    response = client.post(
        "/api/v1/auth/password",
        json={"new_password": "NewPass123456"},
        headers=_auth_header(seeded_data["lawyer_token"]),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_change_password_clears_must_reset_password_flag(client, db_session):
    tenant = Tenant(tenant_code="tenant_pwd_reset", name="Tenant Pwd Reset", type="personal", status=1)
    db_session.add(tenant)
    db_session.flush()
    user = User(
        tenant_id=tenant.id,
        role="client",
        is_tenant_admin=False,
        must_reset_password=True,
        phone="13800001056",
        password_hash=get_password_hash("TempPass123"),
        real_name="Reset Me",
        status=int(UserStatus.PENDING_APPROVAL),
    )
    db_session.add(user)
    db_session.commit()

    token = issue_session_bound_access_token(db_session, user=user, channel="test_password_change")

    response = client.post(
        "/api/v1/auth/password",
        json={"new_password": "NewPass123456"},
        headers=_auth_header(token),
    )

    assert response.status_code == 200
    assert response.json()["must_reset_password"] is False

    db_session.expire_all()
    refreshed = db_session.query(User).filter(User.id == user.id).one()
    assert refreshed.must_reset_password is False
    assert verify_password("NewPass123456", refreshed.password_hash)


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


def test_password_login_accepts_case_invite_context_and_binds_case(client, db_session):
    tenant_a = Tenant(tenant_code="tenant_pwd_case_a", name="Tenant Pwd Case A", type="organization", status=1)
    tenant_b = Tenant(tenant_code="tenant_pwd_case_b", name="Tenant Pwd Case B", type="organization", status=1)
    db_session.add_all([tenant_a, tenant_b])
    db_session.flush()

    lawyer = User(
        tenant_id=tenant_a.id,
        role="lawyer",
        is_tenant_admin=False,
        phone="13800001042",
        password_hash=get_password_hash("Pass123456"),
        real_name="Invite Password Lawyer",
        status=1,
    )
    invited_client = User(
        tenant_id=tenant_a.id,
        role="client",
        is_tenant_admin=False,
        phone="13800001043",
        password_hash=get_password_hash("Pass123456"),
        real_name="Invite Password Client A",
        status=1,
    )
    duplicate_client = User(
        tenant_id=tenant_b.id,
        role="client",
        is_tenant_admin=False,
        phone="13800001043",
        password_hash=get_password_hash("Pass123456"),
        real_name="Invite Password Client B",
        status=1,
    )
    db_session.add_all([lawyer, invited_client, duplicate_client])
    db_session.flush()

    invited_case = Case(
        tenant_id=tenant_a.id,
        case_number="CASE-PWD-INVITE-001",
        title="Invite Password Bind",
        legal_type="other",
        client_id=None,
        assigned_lawyer_id=lawyer.id,
        status="new",
    )
    db_session.add(invited_case)
    db_session.commit()

    invite_token = create_case_invite_token(invited_case.id, tenant_a.id)
    response = client.post(
        "/api/v1/auth/login",
        json={
            "phone": "13800001043",
            "password": "Pass123456",
            "case_invite_token": invite_token,
        },
    )
    assert response.status_code == 200
    assert response.json()["access_token"]

    db_session.expire_all()
    refreshed_case = db_session.query(Case).filter(Case.id == invited_case.id).one()
    assert refreshed_case.client_id == invited_client.id


def test_password_login_without_tenant_code_allows_single_pending_account(client, db_session):
    tenant = Tenant(tenant_code="tenant_inactive_login_1", name="Tenant Inactive Login", type="organization", status=1)
    db_session.add(tenant)
    db_session.flush()
    user = User(
        tenant_id=tenant.id,
        role="lawyer",
        is_tenant_admin=False,
        phone="13800001057",
        password_hash=get_password_hash("Pass123456"),
        real_name="Inactive Login User",
        status=int(UserStatus.PENDING_APPROVAL),
    )
    db_session.add(user)
    db_session.commit()

    ambiguous_login = client.post(
        "/api/v1/auth/login",
        json={"phone": "13800001057", "password": "Pass123456"},
    )
    assert ambiguous_login.status_code == 200
    ambiguous_payload = ambiguous_login.json()
    assert ambiguous_payload["access_token"]

    me_resp = client.get("/api/v1/users/me", headers=_auth_header(ambiguous_payload["access_token"]))
    assert me_resp.status_code == 200
    assert me_resp.json()["status"] == int(UserStatus.PENDING_APPROVAL)

    tenant_resp = client.get("/api/v1/tenants/current", headers=_auth_header(ambiguous_payload["access_token"]))
    assert tenant_resp.status_code == 200
    assert tenant_resp.json()["tenant_code"] == "tenant_inactive_login_1"

    scoped_login = client.post(
        "/api/v1/auth/login",
        json={"phone": "13800001057", "password": "Pass123456", "tenant_code": "tenant_inactive_login_1"},
    )
    assert scoped_login.status_code == 200
    assert scoped_login.json()["access_token"]


def test_password_login_without_tenant_code_rejects_multiple_inactive_accounts(client, db_session):
    tenant_a = Tenant(tenant_code="tenant_inactive_multi_a", name="Tenant Inactive Multi A", type="organization", status=1)
    tenant_b = Tenant(tenant_code="tenant_inactive_multi_b", name="Tenant Inactive Multi B", type="organization", status=1)
    db_session.add_all([tenant_a, tenant_b])
    db_session.flush()
    db_session.add_all(
        [
            User(
                tenant_id=tenant_a.id,
                role="lawyer",
                is_tenant_admin=False,
                phone="13800001058",
                password_hash=get_password_hash("Pass123456"),
                real_name="Inactive Multi A",
                status=int(UserStatus.PENDING_APPROVAL),
            ),
            User(
                tenant_id=tenant_b.id,
                role="lawyer",
                is_tenant_admin=False,
                phone="13800001058",
                password_hash=get_password_hash("Pass123456"),
                real_name="Inactive Multi B",
                status=int(UserStatus.DISABLED),
            ),
        ]
    )
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"phone": "13800001058", "password": "Pass123456"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REQUIRED"
    assert "tenant_code" not in response.text


def test_invite_register_pending_user_login_creates_limited_session_until_approved(client, db_session):
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
    assert login_resp.status_code == 200
    pending_payload = login_resp.json()
    assert pending_payload["access_token"]

    me_resp = client.get("/api/v1/users/me", headers=_auth_header(pending_payload["access_token"]))
    assert me_resp.status_code == 200
    assert me_resp.json()["status"] == int(UserStatus.PENDING_APPROVAL)

    cases_resp = client.get("/api/v1/cases", headers=_auth_header(pending_payload["access_token"]))
    assert cases_resp.status_code == 403

    admin_token = issue_session_bound_access_token(db_session, user=admin, channel="test_approve")
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

    token = issue_session_bound_access_token(db_session, user=super_admin, channel="test_super_admin")

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

    token = issue_session_bound_access_token(db_session, user=normal_user, channel="test_tenant_admin")

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
