import os
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

sys.path.append(os.getcwd())

from app.db.session import SessionLocal
from app.models.case import Case
from app.models.notification import Notification


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
            user_id=case.assigned_lawyer_id,
            title="case_deadline_reminder",
            content=f"Case {case.case_number} will reach its deadline within 3 days.",
            is_read=False,
        )
        db.add(notification)
        created += 1

    db.commit()
    return created


def main() -> None:
    with SessionLocal() as db:
        created = create_deadline_notifications(db)
        print(f"Notifications created: {created}")


if __name__ == "__main__":
    main()
