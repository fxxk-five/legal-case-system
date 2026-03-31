from __future__ import annotations

from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.models.user import User
from app.modules.notifications.models.notification import Notification
from app.modules.notifications.repository import NotificationsRepository


class NotificationsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = NotificationsRepository(db)

    def list_notifications(self, *, unread_only: bool, current_user: User) -> list[Notification]:
        return self.repository.list_notifications(
            current_user=current_user,
            unread_only=unread_only,
        )

    def mark_notification_read(self, *, notification_id: int, current_user: User) -> Notification:
        notification = self.repository.get_notification(
            notification_id=notification_id,
            current_user=current_user,
        )
        if notification is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code=ErrorCode.NOTIFICATION_NOT_FOUND,
                message="通知不存在。",
                detail="通知不存在。",
            )

        notification.is_read = True
        self.repository.save_and_refresh(notification)
        return notification
