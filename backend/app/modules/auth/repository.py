from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.core.statuses import TenantStatus
from app.models.auth_session import AuthSession
from app.models.tenant import Tenant
from app.models.user import User
from app.models.web_login_ticket import WebLoginTicket
from app.modules.cases.models.case import Case


class AuthRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_by_id(self, *, user_id: int) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def list_users_by_phone(
        self,
        *,
        phone: str,
        tenant_id: int | None = None,
    ) -> list[User]:
        query = self.db.query(User).filter(User.phone == phone)
        if tenant_id is not None:
            query = query.filter(User.tenant_id == tenant_id)
        return query.order_by(User.created_at.asc()).all()

    def get_user_by_tenant_phone(self, *, tenant_id: int, phone: str) -> User | None:
        users = self.list_users_by_phone(phone=phone, tenant_id=tenant_id)
        return users[0] if users else None

    def get_active_tenant_by_code(self, *, tenant_code: str) -> Tenant | None:
        return (
            self.db.query(Tenant)
            .filter(
                Tenant.tenant_code == tenant_code,
                Tenant.status == int(TenantStatus.ACTIVE),
            )
            .first()
        )

    def get_tenant_by_id(self, *, tenant_id: int) -> Tenant | None:
        return self.db.query(Tenant).filter(Tenant.id == tenant_id).first()

    def get_user_by_wechat_unionid_hashes(self, *, unionid_hashes: Sequence[str]) -> User | None:
        if not unionid_hashes:
            return None
        return self.db.query(User).filter(User.wechat_unionid_hash.in_(unionid_hashes)).first()

    def get_user_by_wechat_openid_hashes(self, *, openid_hashes: Sequence[str]) -> User | None:
        if not openid_hashes:
            return None
        return self.db.query(User).filter(User.wechat_openid_hash.in_(openid_hashes)).first()

    def get_case(self, *, case_id: int, tenant_id: int) -> Case | None:
        return (
            self.db.query(Case)
            .filter(
                Case.id == case_id,
                Case.tenant_id == tenant_id,
            )
            .first()
        )

    def get_auth_session(
        self,
        *,
        session_id: int,
        user_id: int,
        tenant_id: int,
    ) -> AuthSession | None:
        return (
            self.db.query(AuthSession)
            .filter(
                AuthSession.id == session_id,
                AuthSession.user_id == user_id,
                AuthSession.tenant_id == tenant_id,
            )
            .first()
        )

    def get_web_login_ticket_by_ticket(self, *, ticket: str) -> WebLoginTicket | None:
        return self.db.query(WebLoginTicket).filter(WebLoginTicket.ticket == ticket).first()

    def save(self, instance: object) -> None:
        self.db.add(instance)

    def commit(self) -> None:
        self.db.commit()

    def flush(self) -> None:
        self.db.flush()

    def refresh(self, instance: object) -> None:
        self.db.refresh(instance)

    def save_commit_refresh(self, instance: object) -> None:
        self.save(instance)
        self.commit()
        self.refresh(instance)

    def save_and_commit(self, instance: object) -> None:
        self.save(instance)
        self.commit()
