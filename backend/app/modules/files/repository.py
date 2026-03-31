from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from app.models.user import User
from app.modules.ai.models.ai_task import AITask
from app.modules.cases.models.case import Case
from app.modules.files.models.file import File
from app.modules.files.models.file_access_grant import FileAccessGrant


class FilesRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save(self, instance: object) -> None:
        self.db.add(instance)

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def refresh(self, instance: object) -> None:
        self.db.refresh(instance)

    def delete(self, instance: object) -> None:
        self.db.delete(instance)

    def save_and_commit(self, instance: object) -> None:
        self.save(instance)
        self.commit()

    def commit_and_refresh(self, instance: object) -> None:
        self.commit()
        self.refresh(instance)

    def save_commit_refresh(self, instance: object) -> None:
        self.save(instance)
        self.commit_and_refresh(instance)

    def get_case(self, *, case_id: int, tenant_id: int) -> Case | None:
        return (
            self.db.query(Case)
            .filter(
                Case.id == case_id,
                Case.tenant_id == tenant_id,
            )
            .first()
        )

    def get_file(
        self,
        *,
        file_id: int,
        tenant_id: int,
        with_case: bool = False,
        with_uploader: bool = False,
    ) -> File | None:
        query = self.db.query(File)
        if with_case:
            query = query.options(joinedload(File.case))
        if with_uploader:
            query = query.options(joinedload(File.uploader))

        return (
            query.filter(
                File.id == file_id,
                File.tenant_id == tenant_id,
            )
            .first()
        )

    def list_case_files(self, *, case_id: int, tenant_id: int) -> list[File]:
        return (
            self.db.query(File)
            .options(joinedload(File.uploader))
            .filter(
                File.case_id == case_id,
                File.tenant_id == tenant_id,
            )
            .order_by(File.created_at.desc())
            .all()
        )

    def find_file_by_storage_key(self, *, tenant_id: int, storage_key: str) -> File | None:
        return (
            self.db.query(File)
            .filter(
                File.tenant_id == tenant_id,
                File.file_url == storage_key,
            )
            .order_by(File.id.asc())
            .first()
        )

    def get_active_user(self, *, user_id: int, tenant_id: int) -> User | None:
        return (
            self.db.query(User)
            .filter(
                User.id == user_id,
                User.tenant_id == tenant_id,
                User.status == 1,
            )
            .first()
        )

    def find_auto_reanalyze_task(
        self,
        *,
        tenant_id: int,
        case_id: int,
        operator_id: int,
        idempotency_key: str,
    ) -> AITask | None:
        return (
            self.db.query(AITask)
            .filter(
                AITask.tenant_id == tenant_id,
                AITask.case_id == case_id,
                AITask.task_type == "analyze",
                AITask.created_by == operator_id,
                AITask.idempotency_key == idempotency_key,
            )
            .order_by(AITask.created_at.desc(), AITask.id.desc())
            .first()
        )

    def create_file_access_grant(
        self,
        *,
        file_id: int,
        tenant_id: int,
        issued_to_user_id: int | None,
        token_hash: str,
        expires_at: datetime,
    ) -> FileAccessGrant:
        grant = FileAccessGrant(
            file_id=file_id,
            tenant_id=tenant_id,
            issued_to_user_id=issued_to_user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.save_and_commit(grant)
        return grant

    def get_file_access_grant_by_token_hash(self, *, token_hash: str) -> FileAccessGrant | None:
        return (
            self.db.query(FileAccessGrant)
            .filter(FileAccessGrant.token_hash == token_hash)
            .first()
        )

    def mark_file_access_grant_used(self, *, grant: FileAccessGrant, used_at: datetime) -> None:
        grant.used_at = used_at
        self.save_and_commit(grant)
