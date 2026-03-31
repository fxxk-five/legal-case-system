from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.roles import can_manage_case_role
from app.modules.ai.models.ai_analysis import AIAnalysisResult
from app.modules.ai.models.ai_task import AITask
from app.modules.analytics.dashboard_service import AnalyticsDashboardService
from app.modules.analytics.repository import AnalyticsRepository
from app.models.tenant import Tenant
from app.models.user import User
from app.modules.analytics.schemas import (
    AIModelBreakdownItem,
    AIUsageBreakdownItem,
    AIUsageRead,
    AIUsageWindowRead,
    PromptSettingsRead,
    PromptSettingsUpdate,
    ProviderSettingsRead,
    ProviderSettingsUpdate,
)

DEFAULT_PROMPT_SETTINGS = {
    "parse_prompt": "",
    "analyze_prompt": "",
    "falsify_prompt": "",
}

DEFAULT_PROVIDER_SETTINGS = {
    "provider_type": "openai_compatible",
    "base_url": "",
    "model": "",
    "api_key": "",
}

TASK_TYPE_LABELS = {
    "parse": "Document Parsing",
    "analyze": "Legal Analysis",
    "falsify": "Falsification Check",
}

TASK_STATUS_LABELS = {
    "queued": "Queued",
    "pending": "Pending",
    "processing": "Processing",
    "completed": "Completed",
    "failed": "Failed",
    "dead": "Dead",
    "retrying": "Retrying",
}


class AnalyticsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = AnalyticsRepository(db)
        self.dashboard_service = AnalyticsDashboardService(self.repository)

    @staticmethod
    def _require_analytics_access(current_user: User) -> None:
        if can_manage_case_role(current_user.role):
            return
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.FORBIDDEN,
            message="Current role cannot access analytics.",
            detail="Current role cannot access analytics.",
        )

    def _get_tenant_or_404(self, *, tenant_id: int) -> Tenant:
        tenant = self.repository.get_tenant(tenant_id=tenant_id)
        if tenant is not None:
            return tenant
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.TENANT_NOT_FOUND,
            message="Tenant not found.",
            detail="Tenant not found.",
        )

    @staticmethod
    def _float_cost(value: Decimal | None) -> float:
        if value is None:
            return 0.0
        return float(value)

    @staticmethod
    def _ensure_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _build_window(
        self,
        *,
        tasks: list[AITask],
        results: list[AIAnalysisResult],
        baseline: datetime,
    ) -> AIUsageWindowRead:
        baseline_utc = self._ensure_utc(baseline)
        min_utc = datetime.min.replace(tzinfo=timezone.utc)
        return AIUsageWindowRead(
            task_count=sum(
                1
                for item in tasks
                if (self._ensure_utc(item.created_at) or min_utc) >= baseline_utc
            ),
            token_usage=sum(
                item.token_usage
                for item in results
                if (self._ensure_utc(item.created_at) or min_utc) >= baseline_utc
            ),
            cost_total=round(
                sum(
                    self._float_cost(item.cost)
                    for item in results
                    if (self._ensure_utc(item.created_at) or min_utc) >= baseline_utc
                ),
                4,
            ),
        )

    @staticmethod
    def _mask_secret(value: str) -> str:
        if not value:
            return ""
        if len(value) <= 8:
            return "*" * len(value)
        return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"

    def get_ai_usage(self, *, current_user: User) -> AIUsageRead:
        self._require_analytics_access(current_user)

        now = datetime.now(timezone.utc)
        tasks = self.repository.list_tenant_tasks(tenant_id=current_user.tenant_id)
        results = self.repository.list_tenant_results(tenant_id=current_user.tenant_id)

        task_type_counter: dict[str, int] = {}
        status_counter: dict[str, int] = {}
        for item in tasks:
            task_type_counter[item.task_type] = task_type_counter.get(item.task_type, 0) + 1
            status_counter[item.status] = status_counter.get(item.status, 0) + 1

        model_counter: dict[str, dict[str, float | int | str]] = {}
        for item in results:
            model_bucket = model_counter.setdefault(
                item.ai_model,
                {
                    "model": item.ai_model,
                    "result_count": 0,
                    "token_usage": 0,
                    "cost_total": 0.0,
                },
            )
            model_bucket["result_count"] += 1
            model_bucket["token_usage"] += item.token_usage
            model_bucket["cost_total"] += self._float_cost(item.cost)

        return AIUsageRead(
            day=self._build_window(tasks=tasks, results=results, baseline=now - timedelta(days=1)),
            week=self._build_window(tasks=tasks, results=results, baseline=now - timedelta(days=7)),
            month=self._build_window(tasks=tasks, results=results, baseline=now - timedelta(days=30)),
            task_type_breakdown=[
                AIUsageBreakdownItem(
                    key=key,
                    label=TASK_TYPE_LABELS.get(key, key),
                    count=count,
                )
                for key, count in sorted(task_type_counter.items(), key=lambda item: item[1], reverse=True)
            ],
            status_breakdown=[
                AIUsageBreakdownItem(
                    key=key,
                    label=TASK_STATUS_LABELS.get(key, key),
                    count=count,
                )
                for key, count in sorted(status_counter.items(), key=lambda item: item[1], reverse=True)
            ],
            model_breakdown=[
                AIModelBreakdownItem(
                    model=str(bucket["model"]),
                    result_count=int(bucket["result_count"]),
                    token_usage=int(bucket["token_usage"]),
                    cost_total=round(float(bucket["cost_total"]), 4),
                )
                for bucket in sorted(model_counter.values(), key=lambda item: float(item["cost_total"]), reverse=True)
            ],
        )

    def get_prompt_settings(self, *, current_user: User) -> PromptSettingsRead:
        self._require_analytics_access(current_user)
        tenant = self._get_tenant_or_404(tenant_id=current_user.tenant_id)
        payload = {**DEFAULT_PROMPT_SETTINGS, **(tenant.ai_prompt_settings or {})}
        return PromptSettingsRead(**payload)

    def update_prompt_settings(self, *, payload: PromptSettingsUpdate, current_user: User) -> PromptSettingsRead:
        self._require_analytics_access(current_user)
        tenant = self._get_tenant_or_404(tenant_id=current_user.tenant_id)
        tenant.ai_prompt_settings = payload.model_dump()
        self.repository.save(tenant)
        self.repository.commit_and_refresh(tenant)
        return PromptSettingsRead(**{**DEFAULT_PROMPT_SETTINGS, **(tenant.ai_prompt_settings or {})})

    def get_provider_settings(self, *, current_user: User) -> ProviderSettingsRead:
        self._require_analytics_access(current_user)
        tenant = self._get_tenant_or_404(tenant_id=current_user.tenant_id)
        payload = {**DEFAULT_PROVIDER_SETTINGS, **(tenant.ai_provider_settings or {})}
        return ProviderSettingsRead(
            provider_type=str(payload["provider_type"]),
            base_url=str(payload["base_url"]),
            model=str(payload["model"]),
            api_key_masked=self._mask_secret(str(payload.get("api_key") or "")),
            editable=not tenant.ai_provider_locked,
            locked=tenant.ai_provider_locked,
        )

    def update_provider_settings(
        self,
        *,
        payload: ProviderSettingsUpdate,
        current_user: User,
    ) -> ProviderSettingsRead:
        self._require_analytics_access(current_user)
        tenant = self._get_tenant_or_404(tenant_id=current_user.tenant_id)

        if tenant.ai_provider_locked:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code=ErrorCode.FORBIDDEN,
                message="Provider settings are locked and cannot be edited by tenant.",
                detail="Provider settings are locked and cannot be edited by tenant.",
            )

        existing = {**DEFAULT_PROVIDER_SETTINGS, **(tenant.ai_provider_settings or {})}
        if payload.api_key is not None:
            existing["api_key"] = payload.api_key.strip()
        existing["provider_type"] = payload.provider_type.strip() or DEFAULT_PROVIDER_SETTINGS["provider_type"]
        existing["base_url"] = payload.base_url.strip()
        existing["model"] = payload.model.strip()

        tenant.ai_provider_settings = existing
        self.repository.save(tenant)
        self.repository.commit_and_refresh(tenant)

        return ProviderSettingsRead(
            provider_type=str(existing["provider_type"]),
            base_url=str(existing["base_url"]),
            model=str(existing["model"]),
            api_key_masked=self._mask_secret(str(existing.get("api_key") or "")),
            editable=True,
            locked=False,
        )

    def get_dashboard_stats(self, *, current_user: User) -> dict[str, object]:
        return self.dashboard_service.get_dashboard_stats(
            current_user=current_user,
        )

