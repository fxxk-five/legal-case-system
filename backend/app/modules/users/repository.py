from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models.user import User


class UsersRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_tenant_users(
        self,
        *,
        tenant_id: int,
        roles: Sequence[str] | None = None,
        status: int | None = None,
    ) -> list[User]:
        query = self.db.query(User).filter(User.tenant_id == tenant_id)
        if roles:
            query = query.filter(User.role.in_(list(roles)))
        if status is not None:
            query = query.filter(User.status == status)
        return query.order_by(User.created_at.desc()).all()

    def get_tenant_user(
        self,
        *,
        user_id: int,
        tenant_id: int,
        roles: Sequence[str] | None = None,
        status: int | None = None,
    ) -> User | None:
        query = self.db.query(User).filter(
            User.id == user_id,
            User.tenant_id == tenant_id,
        )
        if roles:
            query = query.filter(User.role.in_(list(roles)))
        if status is not None:
            query = query.filter(User.status == status)
        return query.first()

    def list_all_users(self) -> list[User]:
        return self.db.query(User).order_by(User.id.asc()).all()

    def save(self, user: User) -> None:
        self.db.add(user)

    def delete(self, user: User) -> None:
        self.db.delete(user)

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, instance: object) -> None:
        self.db.refresh(instance)

    def save_commit_refresh(self, user: User) -> None:
        self.save(user)
        self.commit()
        self.refresh(user)

    def delete_and_commit(self, user: User) -> None:
        self.delete(user)
        self.commit()
