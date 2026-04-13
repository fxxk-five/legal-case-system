import os
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

sys.path.append(os.getcwd())

from app.core.statuses import UserStatus
from app.db.session import SessionLocal
from app.modules.cases.models.case import Case
from app.modules.notifications.models.notification import Notification
from app.models.user import User


SLA_REMINDER_HOURS = 2
SLA_REMINDER_LOOKBACK_HOURS = 24


def create_deadline_notifications(db: Session) -> int:
    target_date = datetime.now(timezone.utc) + timedelta(days=3)
    cases = (
        db.query(Case)
        .filter(Case.deadline.is_not(None), Case.deadline <= target_date)
        .all()
    )

    created = 0
    for case in cases:
        if case.assigned_lawyer_id is None:
            continue

        exists = (
            db.query(Notification)
            .filter(
                Notification.user_id == case.assigned_lawyer_id,
                Notification.title == "case_deadline_reminder",
                Notification.content.contains(case.case_number),
            )
            .first()
        )
        if exists:
            continue

        notification = Notification(
            tenant_id=case.tenant_id,
            user_id=case.assigned_lawyer_id,
            title="case_deadline_reminder",
            content=f"Case {case.case_number} will reach its deadline within 3 days.",
            is_read=False,
        )
        db.add(notification)
        created += 1

    db.commit()
    return created


def _has_pending_lawyer_sla_notification(
    db: Session,
    *,
    admin_user_id: int,
    pending_user_id: int,
    now: datetime,
) -> bool:
    lookback = now - timedelta(hours=SLA_REMINDER_LOOKBACK_HOURS)
    exists = (
        db.query(Notification)
        .filter(
            Notification.user_id == admin_user_id,
            Notification.title == "pending_lawyer_approval_sla_reminder",
            Notification.content.contains(f"user_id={pending_user_id}"),
            Notification.created_at >= lookback,
        )
        .first()
    )
    return exists is not None


def create_pending_lawyer_approval_notifications(db: Session, *, sla_hours: int = SLA_REMINDER_HOURS) -> int:
    now = datetime.now(timezone.utc)
    deadline = now - timedelta(hours=max(1, int(sla_hours)))
    pending_lawyers = (
        db.query(User)
        .filter(
            User.status == int(UserStatus.PENDING_APPROVAL),
            User.created_at <= deadline,
            User.role.in_(["lawyer", "org_lawyer", "solo_lawyer"]),
        )
        .all()
    )

    created = 0
    for pending_user in pending_lawyers:
        tenant_admins = (
            db.query(User)
            .filter(
                User.tenant_id == pending_user.tenant_id,
                or_(User.role == "tenant_admin", User.is_tenant_admin.is_(True)),
                User.status == int(UserStatus.ACTIVE),
            )
            .all()
        )
        if not tenant_admins:
            continue

        for admin in tenant_admins:
            if _has_pending_lawyer_sla_notification(
                db,
                admin_user_id=admin.id,
                pending_user_id=pending_user.id,
                now=now,
            ):
                continue

            notification = Notification(
                tenant_id=pending_user.tenant_id,
                user_id=admin.id,
                title="pending_lawyer_approval_sla_reminder",
                content=(
                    "Pending lawyer approval exceeded SLA "
                    f"({sla_hours}h): user_id={pending_user.id}, phone={pending_user.phone}."
                ),
                is_read=False,
            )
            db.add(notification)
            created += 1

    db.commit()
    return created


def main() -> None:
    with SessionLocal() as db:
        deadline_created = create_deadline_notifications(db)
        sla_created = create_pending_lawyer_approval_notifications(db)
        print(
            "Notifications created: "
            f"deadline={deadline_created}, pending_lawyer_sla={sla_created}, total={deadline_created + sla_created}"
        )


if __name__ == "__main__":
    main()
