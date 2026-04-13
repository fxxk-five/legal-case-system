from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.deps import get_current_user
from app.modules.notifications.models.notification import Notification
from app.modules.notifications.service import NotificationsService
from app.models.user import User
from app.modules.notifications.schemas import NotificationRead


router = APIRouter(prefix="/notifications", tags=["Notifications"])


def _notifications_service(db: Session) -> NotificationsService:
    return NotificationsService(db)


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Notification]:
    return _notifications_service(db).list_notifications(
        unread_only=unread_only,
        current_user=current_user,
    )


@router.patch("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Notification:
    return _notifications_service(db).mark_notification_read(
        notification_id=notification_id,
        current_user=current_user,
    )

