from datetime import datetime, timedelta, timezone

from app.core.statuses import UserStatus
from app.models.case import Case
from app.models.invite import Invite
from app.models.tenant import Tenant
from app.models.user import User
from app.models.web_login_ticket import WebLoginTicket
from app.services.mini_program import create_case_invite_token, exchange_code_for_identity


def _mini_headers() -> dict[str, str]:
    return {
        "X-Client-Platform": "mini-program",
        "X-Client-Source": "wx-mini",
    }


def _mini_auth_headers(access_token: str) -> dict[str, str]:
    return {
        **_mini_headers(),
        "Authorization": f"Bearer {access_token}",
    }


def _start_wechat_login(client, code: str, **extra: object) -> dict:
    payload = {"code": code, **extra}
    response = client.post("/api/v1/auth/wx-mini-login", json=payload, headers=_mini_headers())
    assert response.status_code == 200
    return response.json()


def test_wx_mini_login_returns_ticket_for_unbound_identity(client, seeded_data):
    _ = seeded_data
    payload = _start_wechat_login(client, "unbound-lawyer")
    assert payload["need_bind_phone"] is True
    assert payload["login_state"] == "NEED_PHONE_AUTH"
    assert payload["wx_session_ticket"]
    assert payload["access_token"] is None


def test_wx_mini_login_signs_in_bound_user_directly(client, db_session, seeded_data):
    _ = seeded_data
    identity = exchange_code_for_identity("bound-lawyer")
    lawyer = db_session.query(User).filter(User.phone == "13800000001").one()
    lawyer.wechat_openid = identity.openid
    lawyer.wechat_unionid = identity.unionid
    db_session.add(lawyer)
    db_session.commit()

    payload = _start_wechat_login(client, "bound-lawyer")
    assert payload["need_bind_phone"] is False
    assert payload["login_state"] == "LOGGED_IN"
    assert payload["access_token"]
    assert payload["refresh_token"]
    assert payload["user"]["phone"] == "13800000001"


def test_wx_mini_login_invite_mode_forces_phone_confirmation_for_bound_user(client, db_session, seeded_data):
    seeded_case: Case = seeded_data["case"]
    invite_token = create_case_invite_token(seeded_case.id, seeded_case.tenant_id)
    identity = exchange_code_for_identity("bound-invite-client")
    bound_client = db_session.query(User).filter(User.phone == "13800000002").one()
    bound_client.wechat_openid = identity.openid
    bound_client.wechat_unionid = identity.unionid
    db_session.add(bound_client)
    db_session.commit()

    payload = _start_wechat_login(client, "bound-invite-client", case_invite_token=invite_token)
    assert payload["need_bind_phone"] is True
    assert payload["login_state"] == "NEED_PHONE_AUTH"
    assert payload["wx_session_ticket"]
    assert payload["access_token"] is None


def test_wx_mini_phone_login_binds_existing_account(client, db_session, seeded_data):
    _ = seeded_data
    login_payload = _start_wechat_login(client, "phone-bind-lawyer")

    response = client.post(
        "/api/v1/auth/wx-mini-phone-login",
        json={
            "phone_code": "13800000001",
            "wx_session_ticket": login_payload["wx_session_ticket"],
            "tenant_code": "tenant_demo",
        },
        headers=_mini_headers(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["need_bind_phone"] is False
    assert payload["user"]["phone"] == "13800000001"

    db_session.expire_all()
    lawyer = db_session.query(User).filter(User.phone == "13800000001").one()
    assert lawyer.wechat_openid is not None
    assert lawyer.wechat_phone_snapshot == "13800000001"
    assert lawyer.last_login_channel == "mini_wechat"


def test_wx_mini_phone_login_requires_tenant_context_for_existing_lawyer(client, db_session, seeded_data):
    _ = seeded_data
    another_tenant = Tenant(
        tenant_code="tenant_other",
        name="Tenant Other",
        type="organization",
        status=1,
    )
    db_session.add(another_tenant)
    db_session.flush()
    db_session.add(
        User(
            tenant_id=another_tenant.id,
            role="lawyer",
            is_tenant_admin=False,
            phone="13800000001",
            password_hash="unused",
            real_name="Duplicate Lawyer",
            status=int(UserStatus.ACTIVE),
        )
    )
    db_session.commit()

    login_payload = _start_wechat_login(client, "tenant-conflict")
    response = client.post(
        "/api/v1/auth/wx-mini-phone-login",
        json={
            "phone_code": "13800000001",
            "wx_session_ticket": login_payload["wx_session_ticket"],
        },
        headers=_mini_headers(),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "CONFLICT"


def test_wx_mini_phone_login_creates_client_from_invite(client, db_session, seeded_data):
    seeded_case: Case = seeded_data["case"]
    invite_token = create_case_invite_token(seeded_case.id, seeded_case.tenant_id)
    login_payload = _start_wechat_login(client, "invite-client")

    response = client.post(
        "/api/v1/auth/wx-mini-phone-login",
        json={
            "phone_code": "13800000009",
            "wx_session_ticket": login_payload["wx_session_ticket"],
            "case_invite_token": invite_token,
            "real_name": "Invited Client",
        },
        headers=_mini_headers(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["role"] == "client"
    assert payload["user"]["phone"] == "13800000009"

    db_session.expire_all()
    created_user = db_session.query(User).filter(User.phone == "13800000009").one()
    refreshed_case = db_session.query(Case).filter(Case.id == seeded_case.id).one()
    assert created_user.wechat_openid is not None
    assert refreshed_case.client_id == created_user.id

    password_login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "phone": "13800000009",
            "password": "client123456",
            "tenant_code": seeded_data["tenant"].tenant_code,
        },
    )
    assert password_login_resp.status_code == 401
    assert password_login_resp.json()["code"] == "AUTH_REQUIRED"


def test_wx_mini_phone_login_applies_case_invite_for_bound_user(client, db_session, seeded_data):
    seeded_case: Case = seeded_data["case"]
    bound_client = db_session.query(User).filter(User.phone == "13800000002").one()
    identity = exchange_code_for_identity("bound-invite-existing-client")
    bound_client.wechat_openid = identity.openid
    bound_client.wechat_unionid = identity.unionid

    invited_case = Case(
        tenant_id=seeded_case.tenant_id,
        case_number="CASE-INVITE-BOUND-001",
        title="Bound Client Invite Case",
        legal_type="other",
        client_id=None,
        assigned_lawyer_id=seeded_case.assigned_lawyer_id,
        status="new",
    )
    db_session.add_all([bound_client, invited_case])
    db_session.commit()

    invite_token = create_case_invite_token(invited_case.id, invited_case.tenant_id)
    login_payload = _start_wechat_login(
        client,
        "bound-invite-existing-client",
        case_invite_token=invite_token,
    )

    response = client.post(
        "/api/v1/auth/wx-mini-phone-login",
        json={
            "phone_code": "13800000002",
            "wx_session_ticket": login_payload["wx_session_ticket"],
            "case_invite_token": invite_token,
        },
        headers=_mini_headers(),
    )
    assert response.status_code == 200
    assert response.json()["access_token"]

    db_session.expire_all()
    refreshed_case = db_session.query(Case).filter(Case.id == invited_case.id).one()
    assert refreshed_case.client_id == bound_client.id


def test_wx_mini_phone_login_creates_pending_lawyer_from_invite(client, db_session, seeded_data):
    inviter = db_session.query(User).filter(User.phone == "13800000001").one()
    invite = Invite(
        tenant_id=inviter.tenant_id,
        invited_by_user_id=inviter.id,
        role="lawyer",
        token="lawyer-invite-token-00000001",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        status="pending",
    )
    db_session.add(invite)
    db_session.commit()

    login_payload = _start_wechat_login(client, "invite-lawyer")
    response = client.post(
        "/api/v1/auth/wx-mini-phone-login",
        json={
            "phone_code": "13800000008",
            "wx_session_ticket": login_payload["wx_session_ticket"],
            "lawyer_invite_token": invite.token,
            "real_name": "Invited Lawyer",
        },
        headers=_mini_headers(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["login_state"] == "PENDING_APPROVAL"
    assert payload["access_token"] is None
    assert payload["user"]["role"] == "lawyer"
    assert payload["user"]["status"] == int(UserStatus.PENDING_APPROVAL)

    db_session.expire_all()
    created_user = db_session.query(User).filter(User.phone == "13800000008").one()
    refreshed_invite = db_session.query(Invite).filter(Invite.token == invite.token).one()
    assert created_user.wechat_openid is not None
    assert refreshed_invite.status == "used"


def test_wx_mini_phone_login_returns_pending_state_for_pending_lawyer_account(client, db_session, seeded_data):
    _ = seeded_data
    lawyer = db_session.query(User).filter(User.phone == "13800000001").one()
    lawyer.status = int(UserStatus.PENDING_APPROVAL)
    db_session.add(lawyer)
    db_session.commit()

    login_payload = _start_wechat_login(client, "pending-lawyer")
    response = client.post(
        "/api/v1/auth/wx-mini-phone-login",
        json={
            "phone_code": "13800000001",
            "wx_session_ticket": login_payload["wx_session_ticket"],
            "tenant_code": "tenant_demo",
        },
        headers=_mini_headers(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["login_state"] == "PENDING_APPROVAL"
    assert payload["access_token"] is None


def test_wx_mini_bind_existing_binds_lawyer_account(client, db_session, seeded_data):
    _ = seeded_data
    login_payload = _start_wechat_login(client, "bind-existing-lawyer")

    response = client.post(
        "/api/v1/auth/wx-mini-bind-existing",
        json={
            "phone": "13800000001",
            "password": "pwd123456",
            "wx_session_ticket": login_payload["wx_session_ticket"],
            "tenant_code": "tenant_demo",
        },
        headers=_mini_headers(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["need_bind_phone"] is False
    assert payload["login_state"] == "LOGGED_IN"
    assert payload["user"]["phone"] == "13800000001"

    db_session.expire_all()
    lawyer = db_session.query(User).filter(User.phone == "13800000001").one()
    assert lawyer.wechat_openid is not None
    assert lawyer.last_login_channel == "mini_wechat"


def test_web_wechat_login_ticket_confirm_and_exchange(client, db_session, seeded_data):
    create_response = client.post("/api/v1/auth/web-wechat-login")
    assert create_response.status_code == 201
    ticket = create_response.json()["ticket"]

    confirm_response = client.post(
        f"/api/v1/auth/web-wechat-login/{ticket}/confirm",
        headers=_mini_auth_headers(seeded_data["lawyer_token"]),
    )
    assert confirm_response.status_code == 200
    confirm_payload = confirm_response.json()
    assert confirm_payload["status"] == "confirmed"
    assert confirm_payload["can_exchange"] is True

    exchange_response = client.post(f"/api/v1/auth/web-wechat-login/{ticket}/exchange")
    assert exchange_response.status_code == 200
    exchange_payload = exchange_response.json()
    assert exchange_payload["access_token"]
    assert exchange_payload["refresh_token"]

    db_session.expire_all()
    ticket_record = db_session.query(WebLoginTicket).filter(WebLoginTicket.ticket == ticket).one()
    assert ticket_record.status == "consumed"
    assert ticket_record.user_id is not None


def test_web_wechat_login_ticket_rejects_client_confirm(client, seeded_data):
    create_response = client.post("/api/v1/auth/web-wechat-login")
    assert create_response.status_code == 201
    ticket = create_response.json()["ticket"]

    response = client.post(
        f"/api/v1/auth/web-wechat-login/{ticket}/confirm",
        headers=_mini_auth_headers(seeded_data["client_token"]),
    )
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"
