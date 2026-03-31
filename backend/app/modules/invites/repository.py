from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.modules.invites.models.invite import Invite


class InvitesRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def find_latest_pending_invite(
        self,
        *,
        tenant_id: int,
        invited_by_user_id: int,
        role: str,
        now: datetime,
    ) -> Invite | None:
        return (
            self.db.query(Invite)
            .filter(
                Invite.tenant_id == tenant_id,
                Invite.invited_by_user_id == invited_by_user_id,
                Invite.role == role,
                Invite.status == "pending",
                Invite.expires_at > now,
            )
            .order_by(Invite.created_at.desc())
            .first()
        )

    def get_by_token(self, *, token: str) -> Invite | None:
        return self.db.query(Invite).filter(Invite.token == token).first()

    def save(self, invite: Invite) -> None:
        self.db.add(invite)

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, invite: Invite) -> None:
        self.db.refresh(invite)

    def save_and_commit(self, invite: Invite) -> None:
        self.save(invite)
        self.commit()

    def save_commit_refresh(self, invite: Invite) -> None:
        self.save(invite)
        self.commit()
        self.refresh(invite)
