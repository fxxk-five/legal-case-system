from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.analytics.service import AnalyticsService
from app.modules.auth.deps import get_current_user
from app.models.user import User


router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("/dashboard")
def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return AnalyticsService(db).get_dashboard_stats(current_user=current_user)
