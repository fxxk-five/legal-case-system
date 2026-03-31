from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.cases.models.case import Case
from app.models.tenant import Tenant
from app.models.user import User


class TenantsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_tenant_by_code(self, *, tenant_code: str) -> Tenant | None:
        return self.db.query(Tenant).filter(Tenant.tenant_code == tenant_code).first()

    def get_tenant_by_id(self, *, tenant_id: int) -> Tenant | None:
        return self.db.query(Tenant).filter(Tenant.id == tenant_id).first()

    def list_all_tenants(self) -> list[Tenant]:
        return self.db.query(Tenant).order_by(Tenant.id.asc()).all()

    def tenant_code_exists(self, *, tenant_code: str) -> bool:
        return self.db.query(Tenant).filter(Tenant.tenant_code == tenant_code).first() is not None

    def get_user_by_phone(self, *, phone: str) -> User | None:
        return self.db.query(User).filter(User.phone == phone).first()

    def get_tenant_user_by_phone(self, *, tenant_id: int, phone: str) -> User | None:
        return (
            self.db.query(User)
            .filter(
                User.tenant_id == tenant_id,
                User.phone == phone,
            )
            .first()
        )

    def get_case(self, *, case_id: int, tenant_id: int) -> Case | None:
        return (
            self.db.query(Case)
            .filter(
                Case.id == case_id,
                Case.tenant_id == tenant_id,
            )
            .first()
        )

    def save(self, instance: object) -> None:
        self.db.add(instance)

    def save_and_refresh(self, instance: object) -> None:
        self.save(instance)
        self.db.commit()
        self.db.refresh(instance)
