from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.user import User
from app.modules.notifications.models.notification import Notification


class NotificationsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_notifications(self, *, current_user: User, unread_only: bool) -> list[Notification]:
        query = (
            self.db.query(Notification)
            .filter(
                Notification.user_id == current_user.id,
                Notification.tenant_id == current_user.tenant_id,
            )
            .order_by(Notification.created_at.desc())
        )
        if unread_only:
            query = query.filter(Notification.is_read.is_(False))
        return query.all()

    def get_notification(self, *, notification_id: int, current_user: User) -> Notification | None:
        return (
            self.db.query(Notification)
            .filter(
                Notification.id == notification_id,
                Notification.user_id == current_user.id,
                Notification.tenant_id == current_user.tenant_id,
            )
            .first()
        )

    def save(self, notification: Notification) -> None:
        self.db.add(notification)

    def save_and_refresh(self, notification: Notification) -> None:
        self.save(notification)
        self.db.commit()
        self.db.refresh(notification)
