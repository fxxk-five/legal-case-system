from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.analytics.service import AnalyticsService
from app.modules.auth.deps import get_current_user
from app.models.user import User
from app.modules.analytics.schemas import (
    AIUsageRead,
    PromptSettingsRead,
    PromptSettingsUpdate,
    ProviderSettingsRead,
    ProviderSettingsUpdate,
)


router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _analytics_service(db: Session) -> AnalyticsService:
    return AnalyticsService(db)


@router.get("/ai-usage", response_model=AIUsageRead)
def get_ai_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIUsageRead:
    return _analytics_service(db).get_ai_usage(current_user=current_user)


@router.get("/prompts", response_model=PromptSettingsRead)
def get_prompt_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PromptSettingsRead:
    return _analytics_service(db).get_prompt_settings(current_user=current_user)


@router.put("/prompts", response_model=PromptSettingsRead)
def update_prompt_settings(
    payload: PromptSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PromptSettingsRead:
    return _analytics_service(db).update_prompt_settings(
        payload=payload,
        current_user=current_user,
    )


@router.get("/provider-settings", response_model=ProviderSettingsRead)
def get_provider_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProviderSettingsRead:
    return _analytics_service(db).get_provider_settings(current_user=current_user)


@router.put("/provider-settings", response_model=ProviderSettingsRead)
def update_provider_settings(
    payload: ProviderSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProviderSettingsRead:
    return _analytics_service(db).update_provider_settings(
        payload=payload,
        current_user=current_user,
    )

