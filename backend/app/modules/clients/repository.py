from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session, joinedload

from app.models.user import User
from app.modules.cases.models.case import Case
from app.modules.cases.policy import build_visible_case_query
from app.modules.files.models.file import File


class ClientsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_visible_cases(self, *, current_user: User) -> list[Case]:
        return (
            build_visible_case_query(self.db, current_user)
            .options(
                joinedload(Case.client),
                joinedload(Case.assigned_lawyer),
            )
            .all()
        )

    def list_case_files_by_case_ids(self, *, tenant_id: int, case_ids: Sequence[int]) -> list[File]:
        normalized_case_ids = [item for item in case_ids if item]
        if not normalized_case_ids:
            return []
        return (
            self.db.query(File)
            .filter(
                File.tenant_id == tenant_id,
                File.case_id.in_(normalized_case_ids),
            )
            .order_by(File.created_at.desc())
            .all()
        )

    def get_client(self, *, client_id: int, tenant_id: int) -> User | None:
        return (
            self.db.query(User)
            .filter(
                User.id == client_id,
                User.tenant_id == tenant_id,
                User.role == "client",
            )
            .first()
        )

    def find_phone_conflict(
        self,
        *,
        tenant_id: int,
        phone: str,
        exclude_user_id: int,
    ) -> User | None:
        return (
            self.db.query(User)
            .filter(
                User.tenant_id == tenant_id,
                User.phone == phone,
                User.id != exclude_user_id,
            )
            .first()
        )

    def update_client_profile(self, *, client: User, real_name: str, phone: str) -> None:
        client.real_name = real_name
        client.phone = phone
        self.db.add(client)
        self.db.commit()
