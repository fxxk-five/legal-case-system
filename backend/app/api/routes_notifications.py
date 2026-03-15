from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationRead


router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Notification]:
    query = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.id,
            Notification.tenant_id == current_user.tenant_id,
        )
        .order_by(Notification.created_at.desc())
    )
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    return query.all()


@router.patch("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Notification:
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
            Notification.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="通知不存在。")

    notification.is_read = True
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification
