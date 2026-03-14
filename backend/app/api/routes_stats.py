from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_tenant_admin
from app.models.case import Case
from app.models.user import User


router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("/dashboard")
def get_dashboard_stats(
    current_user: User = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    tenant_id = current_user.tenant_id
    lawyer_count = (
        db.query(User)
        .filter(User.tenant_id == tenant_id, User.role.in_(["lawyer", "tenant_admin"]))
        .count()
    )
    case_count = db.query(Case).filter(Case.tenant_id == tenant_id).count()
    pending_lawyer_count = (
        db.query(User)
        .filter(
            User.tenant_id == tenant_id,
            User.role.in_(["lawyer", "tenant_admin"]),
            User.status == 0,
        )
        .count()
    )
    return {
        "lawyer_count": lawyer_count,
        "case_count": case_count,
        "pending_lawyer_count": pending_lawyer_count,
    }
