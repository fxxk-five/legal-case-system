#!/usr/bin/env python3
from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.integrations.wechat.service import create_case_invite_token
from app.main import app
from app.models.sms_code import SmsCode
from app.models.tenant import Tenant
from app.models.user import User
from app.models.web_login_ticket import WebLoginTicket
from app.modules.cases.models.case import Case

API_PREFIX = "/api/v1"
DEFAULT_PASSWORD = "Pass123456"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _mini_headers(token: str = "") -> dict[str, str]:
    headers = {
        "X-Client-Platform": "mini-program",
        "X-Client-Source": "wx-mini",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _auth_headers(token: str, *, mini: bool = False) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if mini:
        headers.update(_mini_headers())
    return headers


class LoginMatrixHarness:
    def __init__(self) -> None:
        self._original_settings: dict[str, object] = {}
        self.engine = None
        self.session_factory = None
        self.client: TestClient | None = None
        self._client_ctx = None
        self.ids: dict[str, int] = {}

    def __enter__(self) -> "LoginMatrixHarness":
        self._patch_settings()
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.session_factory = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

        def override_get_db() -> Iterator[Session]:
            with self.session_scope() as db:
                yield db

        app.dependency_overrides[get_db] = override_get_db
        app.state.session_factory = self.session_factory

        self._client_ctx = TestClient(app)
        self.client = self._client_ctx.__enter__()
        self._seed()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._client_ctx is not None:
            self._client_ctx.__exit__(exc_type, exc, tb)
        app.dependency_overrides.clear()
        if hasattr(app.state, "session_factory"):
            delattr(app.state, "session_factory")
        if self.engine is not None:
            Base.metadata.drop_all(bind=self.engine)
            self.engine.dispose()
        self._restore_settings()

    def _patch_settings(self) -> None:
        runtime_dir = ROOT / ".runtime"
        runtime_dir.mkdir(exist_ok=True)
        self._original_settings = {
            "AI_MOCK_MODE": settings.AI_MOCK_MODE,
            "QUEUE_DRIVER": settings.QUEUE_DRIVER,
            "AI_DB_QUEUE_EAGER": settings.AI_DB_QUEUE_EAGER,
            "AI_DB_QUEUE_EAGER_BLOCKING": settings.AI_DB_QUEUE_EAGER_BLOCKING,
            "AI_DB_QUEUE_HEARTBEAT_FILE": settings.AI_DB_QUEUE_HEARTBEAT_FILE,
            "TENCENT_QUEUE_REGION": settings.TENCENT_QUEUE_REGION,
            "TENCENT_QUEUE_NAMESPACE": settings.TENCENT_QUEUE_NAMESPACE,
            "TENCENT_QUEUE_TOPIC_NAME": settings.TENCENT_QUEUE_TOPIC_NAME,
            "TENCENT_QUEUE_SUBSCRIPTION_NAME": settings.TENCENT_QUEUE_SUBSCRIPTION_NAME,
            "TENCENT_QUEUE_ENDPOINT": settings.TENCENT_QUEUE_ENDPOINT,
            "TENCENT_QUEUE_SECRET_ID": settings.TENCENT_QUEUE_SECRET_ID,
            "TENCENT_QUEUE_SECRET_KEY": settings.TENCENT_QUEUE_SECRET_KEY,
        }
        settings.AI_MOCK_MODE = True
        settings.QUEUE_DRIVER = "db"
        settings.AI_DB_QUEUE_EAGER = True
        settings.AI_DB_QUEUE_EAGER_BLOCKING = True
        settings.AI_DB_QUEUE_HEARTBEAT_FILE = str(runtime_dir / "smoke-login-matrix-heartbeat.json")
        settings.TENCENT_QUEUE_REGION = ""
        settings.TENCENT_QUEUE_NAMESPACE = ""
        settings.TENCENT_QUEUE_TOPIC_NAME = ""
        settings.TENCENT_QUEUE_SUBSCRIPTION_NAME = ""
        settings.TENCENT_QUEUE_ENDPOINT = ""
        settings.TENCENT_QUEUE_SECRET_ID = ""
        settings.TENCENT_QUEUE_SECRET_KEY = ""

    def _restore_settings(self) -> None:
        for key, value in self._original_settings.items():
            setattr(settings, key, value)

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        _assert(self.session_factory is not None, "session_factory is not ready")
        db = self.session_factory()
        try:
            yield db
        finally:
            db.close()

    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: dict | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict]:
        _assert(self.client is not None, "client is not ready")
        response = self.client.request(method, f"{API_PREFIX}{path}", json=payload, headers=headers or {})
        data = response.json() if response.content else {}
        return response.status_code, data

    def _seed(self) -> None:
        with self.session_scope() as db:
            tenant_main = Tenant(
                tenant_code="tenant_login_matrix",
                name="Tenant Login Matrix",
                type="organization",
                status=1,
            )
            tenant_other = Tenant(
                tenant_code="tenant_login_matrix_other",
                name="Tenant Login Matrix Other",
                type="organization",
                status=1,
            )
            db.add_all([tenant_main, tenant_other])
            db.flush()

            lawyer = self._create_user(db, tenant_main.id, "lawyer", "13810000101", DEFAULT_PASSWORD, "Web Password Lawyer")
            mini_client = self._create_user(db, tenant_main.id, "client", "13810000102", DEFAULT_PASSWORD, "Mini Password Client")
            sms_lawyer = self._create_user(db, tenant_main.id, "lawyer", "13810000103", DEFAULT_PASSWORD, "Web SMS Lawyer")
            sms_client = self._create_user(db, tenant_main.id, "client", "13810000104", DEFAULT_PASSWORD, "Mini SMS Client")
            reset_client = self._create_user(
                db,
                tenant_main.id,
                "client",
                "13810000105",
                "TempPass123",
                "Reset Required Client",
                must_reset_password=True,
            )
            wechat_lawyer = self._create_user(db, tenant_main.id, "lawyer", "13810000106", DEFAULT_PASSWORD, "Mini WeChat Lawyer")
            password_invite_client_a = self._create_user(
                db,
                tenant_main.id,
                "client",
                "13810000107",
                DEFAULT_PASSWORD,
                "Password Invite Client A",
            )
            password_invite_client_b = self._create_user(
                db,
                tenant_other.id,
                "client",
                "13810000107",
                DEFAULT_PASSWORD,
                "Password Invite Client B",
            )
            sms_invite_client_a = self._create_user(
                db,
                tenant_main.id,
                "client",
                "13810000108",
                DEFAULT_PASSWORD,
                "SMS Invite Client A",
            )
            sms_invite_client_b = self._create_user(
                db,
                tenant_other.id,
                "client",
                "13810000108",
                DEFAULT_PASSWORD,
                "SMS Invite Client B",
            )
            invite_lawyer = self._create_user(db, tenant_main.id, "lawyer", "13810000109", DEFAULT_PASSWORD, "Invite Lawyer")

            password_invite_case = self._create_case(
                db,
                tenant_id=tenant_main.id,
                case_number="CASE-LOGIN-PWD-001",
                title="Password Invite Binding",
                assigned_lawyer_id=invite_lawyer.id,
            )
            sms_invite_case = self._create_case(
                db,
                tenant_id=tenant_main.id,
                case_number="CASE-LOGIN-SMS-001",
                title="SMS Invite Binding",
                assigned_lawyer_id=invite_lawyer.id,
            )
            mini_invite_case = self._create_case(
                db,
                tenant_id=tenant_main.id,
                case_number="CASE-LOGIN-WX-001",
                title="Mini WeChat Invite Binding",
                assigned_lawyer_id=invite_lawyer.id,
            )
            db.commit()

            self.ids = {
                "tenant_main_id": tenant_main.id,
                "tenant_other_id": tenant_other.id,
                "lawyer_id": lawyer.id,
                "mini_client_id": mini_client.id,
                "sms_lawyer_id": sms_lawyer.id,
                "sms_client_id": sms_client.id,
                "reset_client_id": reset_client.id,
                "wechat_lawyer_id": wechat_lawyer.id,
                "password_invite_client_a_id": password_invite_client_a.id,
                "password_invite_client_b_id": password_invite_client_b.id,
                "sms_invite_client_a_id": sms_invite_client_a.id,
                "sms_invite_client_b_id": sms_invite_client_b.id,
                "password_invite_case_id": password_invite_case.id,
                "sms_invite_case_id": sms_invite_case.id,
                "mini_invite_case_id": mini_invite_case.id,
            }

    @staticmethod
    def _create_user(
        db: Session,
        tenant_id: int,
        role: str,
        phone: str,
        password: str,
        real_name: str,
        *,
        must_reset_password: bool = False,
    ) -> User:
        user = User(
            tenant_id=tenant_id,
            role=role,
            is_tenant_admin=False,
            phone=phone,
            password_hash=get_password_hash(password),
            real_name=real_name,
            status=1,
            must_reset_password=must_reset_password,
        )
        db.add(user)
        db.flush()
        return user

    @staticmethod
    def _create_case(
        db: Session,
        *,
        tenant_id: int,
        case_number: str,
        title: str,
        assigned_lawyer_id: int,
    ) -> Case:
        case = Case(
            tenant_id=tenant_id,
            case_number=case_number,
            title=title,
            legal_type="other",
            client_id=None,
            assigned_lawyer_id=assigned_lawyer_id,
            status="new",
        )
        db.add(case)
        db.flush()
        return case

    def _send_sms_and_get_code(self, phone: str) -> str:
        status, payload = self.request_json("POST", "/auth/sms/send", payload={"phone": phone, "purpose": "login"})
        _assert(status == 200, f"sms/send failed for {phone}: {status} {payload}")
        request_id = str(payload.get("request_id") or "")
        _assert(request_id, f"sms/send missing request_id for {phone}: {payload}")
        with self.session_scope() as db:
            sms = db.query(SmsCode).filter(SmsCode.request_id == request_id).first()
            _assert(sms is not None, f"sms code not found for request_id={request_id}")
            return sms.code

    def _login_password(
        self,
        *,
        phone: str,
        password: str,
        tenant_code: str = "",
        case_invite_token: str = "",
        mini: bool = False,
    ) -> dict:
        payload: dict[str, str] = {"phone": phone, "password": password}
        if tenant_code:
            payload["tenant_code"] = tenant_code
        if case_invite_token:
            payload["case_invite_token"] = case_invite_token
        status, data = self.request_json(
            "POST",
            "/auth/login",
            payload=payload,
            headers=_mini_headers() if mini else None,
        )
        _assert(status == 200, f"password login failed for {phone}: {status} {data}")
        _assert(bool(data.get("access_token")), f"password login missing access_token for {phone}: {data}")
        _assert(bool(data.get("refresh_token")), f"password login missing refresh_token for {phone}: {data}")
        return data

    def _login_sms(
        self,
        *,
        phone: str,
        tenant_code: str = "",
        case_invite_token: str = "",
        mini: bool = False,
    ) -> dict:
        payload: dict[str, str] = {"phone": phone, "code": self._send_sms_and_get_code(phone)}
        if tenant_code:
            payload["tenant_code"] = tenant_code
        if case_invite_token:
            payload["case_invite_token"] = case_invite_token
        status, data = self.request_json(
            "POST",
            "/auth/sms-login",
            payload=payload,
            headers=_mini_headers() if mini else None,
        )
        _assert(status == 200, f"sms login failed for {phone}: {status} {data}")
        _assert(bool(data.get("access_token")), f"sms login missing access_token for {phone}: {data}")
        _assert(bool(data.get("refresh_token")), f"sms login missing refresh_token for {phone}: {data}")
        return data

    def _current_user(self, token: str, *, mini: bool = False) -> dict:
        status, data = self.request_json("GET", "/users/me", headers=_auth_headers(token, mini=mini))
        _assert(status == 200, f"/users/me failed: {status} {data}")
        return data

    def _user(self, user_id: int) -> User:
        with self.session_scope() as db:
            user = db.query(User).filter(User.id == user_id).first()
            _assert(user is not None, f"user {user_id} not found")
            db.expunge(user)
            return user

    def _case(self, case_id: int) -> Case:
        with self.session_scope() as db:
            case = db.query(Case).filter(Case.id == case_id).first()
            _assert(case is not None, f"case {case_id} not found")
            db.expunge(case)
            return case

    def run(self) -> None:
        self.check_web_password_login()
        self.check_mini_password_login()
        self.check_web_sms_login()
        self.check_mini_sms_login()
        self.check_password_invite_auto_bind()
        self.check_sms_invite_auto_bind()
        self.check_mini_wechat_login_and_web_qr_exchange()
        self.check_mini_wechat_invite_auto_bind()
        self.check_force_reset_password_flow()

    def check_web_password_login(self) -> None:
        login = self._login_password(
            phone="13810000101",
            password=DEFAULT_PASSWORD,
            tenant_code="tenant_login_matrix",
        )
        me = self._current_user(login["access_token"])
        _assert(me["phone"] == "13810000101", f"unexpected web password profile: {me}")
        user = self._user(self.ids["lawyer_id"])
        _assert(user.last_login_channel == "web_password", f"unexpected channel: {user.last_login_channel}")
        print("[PASS] web password login")

    def check_mini_password_login(self) -> None:
        login = self._login_password(
            phone="13810000102",
            password=DEFAULT_PASSWORD,
            tenant_code="tenant_login_matrix",
            mini=True,
        )
        me = self._current_user(login["access_token"], mini=True)
        _assert(me["phone"] == "13810000102", f"unexpected mini password profile: {me}")
        user = self._user(self.ids["mini_client_id"])
        _assert(user.last_login_channel == "mini_password", f"unexpected channel: {user.last_login_channel}")
        print("[PASS] mini password login")

    def check_web_sms_login(self) -> None:
        login = self._login_sms(phone="13810000103", tenant_code="tenant_login_matrix")
        me = self._current_user(login["access_token"])
        _assert(me["phone"] == "13810000103", f"unexpected web sms profile: {me}")
        user = self._user(self.ids["sms_lawyer_id"])
        _assert(user.last_login_channel == "web_sms", f"unexpected channel: {user.last_login_channel}")
        print("[PASS] web sms login")

    def check_mini_sms_login(self) -> None:
        login = self._login_sms(phone="13810000104", tenant_code="tenant_login_matrix", mini=True)
        me = self._current_user(login["access_token"], mini=True)
        _assert(me["phone"] == "13810000104", f"unexpected mini sms profile: {me}")
        print("[PASS] mini sms login")

    def check_password_invite_auto_bind(self) -> None:
        invite_token = create_case_invite_token(self.ids["password_invite_case_id"], self.ids["tenant_main_id"])
        self._login_password(
            phone="13810000107",
            password=DEFAULT_PASSWORD,
            case_invite_token=invite_token,
        )
        invited_case = self._case(self.ids["password_invite_case_id"])
        _assert(
            invited_case.client_id == self.ids["password_invite_client_a_id"],
            f"password invite case not bound correctly: client_id={invited_case.client_id}",
        )
        print("[PASS] password invite auto-bind")

    def check_sms_invite_auto_bind(self) -> None:
        invite_token = create_case_invite_token(self.ids["sms_invite_case_id"], self.ids["tenant_main_id"])
        self._login_sms(phone="13810000108", case_invite_token=invite_token)
        invited_case = self._case(self.ids["sms_invite_case_id"])
        _assert(
            invited_case.client_id == self.ids["sms_invite_client_a_id"],
            f"sms invite case not bound correctly: client_id={invited_case.client_id}",
        )
        print("[PASS] sms invite auto-bind")

    def check_mini_wechat_login_and_web_qr_exchange(self) -> None:
        start_status, start_payload = self.request_json(
            "POST",
            "/auth/wx-mini-login",
            payload={"code": "login-matrix-bind-existing"},
            headers=_mini_headers(),
        )
        _assert(start_status == 200, f"wx-mini-login start failed: {start_status} {start_payload}")
        _assert(start_payload["need_bind_phone"] is True, f"expected bind flow: {start_payload}")
        ticket = str(start_payload.get("wx_session_ticket") or "")
        _assert(ticket, f"wx-mini-login missing ticket: {start_payload}")

        bind_status, bind_payload = self.request_json(
            "POST",
            "/auth/wx-mini-bind-existing",
            payload={
                "phone": "13810000106",
                "password": DEFAULT_PASSWORD,
                "tenant_code": "tenant_login_matrix",
                "wx_session_ticket": ticket,
            },
            headers=_mini_headers(),
        )
        _assert(bind_status == 200, f"wx-mini-bind-existing failed: {bind_status} {bind_payload}")
        _assert(bind_payload["user"]["phone"] == "13810000106", f"unexpected bind payload: {bind_payload}")

        user = self._user(self.ids["wechat_lawyer_id"])
        _assert(user.last_login_channel == "mini_wechat", f"unexpected mini wechat channel: {user.last_login_channel}")
        _assert(bool(user.wechat_openid), "wechat openid was not saved")

        direct_status, direct_payload = self.request_json(
            "POST",
            "/auth/wx-mini-login",
            payload={"code": "login-matrix-bind-existing"},
            headers=_mini_headers(),
        )
        _assert(direct_status == 200, f"wx-mini-login direct failed: {direct_status} {direct_payload}")
        _assert(direct_payload["need_bind_phone"] is False, f"expected direct login: {direct_payload}")
        direct_token = str(direct_payload.get("access_token") or "")
        _assert(direct_token, f"direct wx-mini-login missing access_token: {direct_payload}")

        create_status, create_payload = self.request_json("POST", "/auth/web-wechat-login")
        _assert(create_status == 201, f"web-wechat-login create failed: {create_status} {create_payload}")
        web_ticket = str(create_payload.get("ticket") or "")
        _assert(web_ticket, f"web-wechat-login missing ticket: {create_payload}")

        confirm_status, confirm_payload = self.request_json(
            "POST",
            f"/auth/web-wechat-login/{web_ticket}/confirm",
            headers=_mini_headers(direct_token),
        )
        _assert(confirm_status == 200, f"web ticket confirm failed: {confirm_status} {confirm_payload}")
        _assert(confirm_payload["status"] == "confirmed", f"unexpected confirm payload: {confirm_payload}")

        exchange_status, exchange_payload = self.request_json(
            "POST",
            f"/auth/web-wechat-login/{web_ticket}/exchange",
        )
        _assert(exchange_status == 200, f"web ticket exchange failed: {exchange_status} {exchange_payload}")
        me = self._current_user(exchange_payload["access_token"])
        _assert(me["phone"] == "13810000106", f"unexpected exchanged profile: {me}")

        with self.session_scope() as db:
            ticket_record = db.query(WebLoginTicket).filter(WebLoginTicket.ticket == web_ticket).first()
            _assert(ticket_record is not None, "web login ticket record missing")
            _assert(ticket_record.status == "consumed", f"unexpected ticket status: {ticket_record.status}")

        refreshed_user = self._user(self.ids["wechat_lawyer_id"])
        _assert(
            refreshed_user.last_login_channel == "web_wechat_scan",
            f"unexpected web wechat channel: {refreshed_user.last_login_channel}",
        )
        print("[PASS] mini wechat bind/direct + web qr exchange")

    def check_mini_wechat_invite_auto_bind(self) -> None:
        invite_token = create_case_invite_token(self.ids["mini_invite_case_id"], self.ids["tenant_main_id"])
        start_status, start_payload = self.request_json(
            "POST",
            "/auth/wx-mini-login",
            payload={"code": "login-matrix-invite-client", "case_invite_token": invite_token},
            headers=_mini_headers(),
        )
        _assert(start_status == 200, f"invite wx-mini-login failed: {start_status} {start_payload}")
        _assert(start_payload["need_bind_phone"] is True, f"invite wx-mini-login should need phone bind: {start_payload}")

        bind_status, bind_payload = self.request_json(
            "POST",
            "/auth/wx-mini-phone-login",
            payload={
                "phone_code": "13810000110",
                "wx_session_ticket": start_payload["wx_session_ticket"],
                "case_invite_token": invite_token,
                "real_name": "Invite Matrix Client",
            },
            headers=_mini_headers(),
        )
        _assert(bind_status == 200, f"wx-mini-phone-login invite failed: {bind_status} {bind_payload}")
        _assert(bind_payload["user"]["phone"] == "13810000110", f"unexpected invite bind payload: {bind_payload}")
        _assert(bind_payload["user"]["must_reset_password"] is True, f"expected reset flag: {bind_payload}")

        me = self._current_user(bind_payload["access_token"], mini=True)
        _assert(me["must_reset_password"] is True, f"expected reset flag in /users/me: {me}")

        with self.session_scope() as db:
            created_user = db.query(User).filter(User.phone == "13810000110").first()
            _assert(created_user is not None, "invited mini user was not created")
            _assert(created_user.must_reset_password is True, "invited mini user reset flag missing")
            invited_case = db.query(Case).filter(Case.id == self.ids["mini_invite_case_id"]).first()
            _assert(invited_case is not None, "mini invite case missing")
            _assert(invited_case.client_id == created_user.id, f"mini invite case not bound: {invited_case.client_id}")
        print("[PASS] mini wechat invite auto-bind")

    def check_force_reset_password_flow(self) -> None:
        login = self._login_password(
            phone="13810000105",
            password="TempPass123",
            tenant_code="tenant_login_matrix",
        )
        before = self._current_user(login["access_token"])
        _assert(before["must_reset_password"] is True, f"expected reset-required user: {before}")

        change_status, change_payload = self.request_json(
            "POST",
            "/auth/password",
            payload={"new_password": "NewPass123456"},
            headers=_auth_headers(login["access_token"]),
        )
        _assert(change_status == 200, f"change password failed: {change_status} {change_payload}")
        _assert(change_payload["must_reset_password"] is False, f"reset flag not cleared: {change_payload}")

        old_status, old_payload = self.request_json(
            "POST",
            "/auth/login",
            payload={
                "phone": "13810000105",
                "password": "TempPass123",
                "tenant_code": "tenant_login_matrix",
            },
        )
        _assert(old_status == 401, f"old password should be rejected: {old_status} {old_payload}")

        relogin = self._login_password(
            phone="13810000105",
            password="NewPass123456",
            tenant_code="tenant_login_matrix",
        )
        after = self._current_user(relogin["access_token"])
        _assert(after["must_reset_password"] is False, f"reset flag should stay cleared: {after}")
        print("[PASS] force-reset password flow")


def main() -> int:
    with LoginMatrixHarness() as harness:
        harness.run()
    print("[DONE] smoke_login_matrix passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"[FAIL] {exc}")
        raise SystemExit(1)
