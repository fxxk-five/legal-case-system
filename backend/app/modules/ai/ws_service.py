from __future__ import annotations

from datetime import datetime, timezone

from app.core.roles import normalize_role
from app.models.auth_session import AuthSession
from app.models.user import User
from app.modules.ai.models.ai_task import AITask
from app.modules.ai.repository import AIRepository


class AIWebSocketService:
    def __init__(self, db) -> None:
        self.db = db
        self.repository = AIRepository(db)

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def resolve_active_access_session(
        self,
        *,
        user_id: int,
        tenant_id: int,
        session_id: int | None,
    ) -> AuthSession | None:
        if session_id is None:
            return None
        auth_session = self.repository.get_auth_session(
            session_id=session_id,
            user_id=user_id,
            tenant_id=tenant_id,
        )
        if auth_session is None or auth_session.is_revoked:
            return None
        expires_at = self._as_utc(auth_session.expires_at)
        if expires_at is None or expires_at <= datetime.now(timezone.utc):
            return None
        return auth_session

    def get_active_user(
        self,
        *,
        user_id: int,
        tenant_id: int,
    ) -> User | None:
        user = self.repository.get_user(
            user_id=user_id,
            tenant_id=tenant_id,
        )
        if user is None or user.status != 1:
            return None
        return user

    def get_viewer_role(self, *, user: User) -> str:
        return normalize_role(user.role)

    def get_visible_task(
        self,
        *,
        task_id: str,
        tenant_id: int,
        viewer_role: str,
        user_id: int,
    ) -> AITask | None:
        task = self.repository.get_task_by_task_id(
            task_id=task_id,
            tenant_id=tenant_id,
        )
        if task is None:
            return None
        if viewer_role == "client" and not self.repository.client_owns_task_case(
            tenant_id=tenant_id,
            user_id=user_id,
            case_id=task.case_id,
        ):
            return None
        return task
