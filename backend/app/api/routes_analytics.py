from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.roles import can_manage_case_role
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.ai_analysis import AIAnalysisResult
from app.models.ai_task import AITask
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.analytics import (
    AIModelBreakdownItem,
    AIUsageBreakdownItem,
    AIUsageRead,
    AIUsageWindowRead,
    PromptSettingsRead,
    PromptSettingsUpdate,
    ProviderSettingsRead,
    ProviderSettingsUpdate,
)


router = APIRouter(prefix="/analytics", tags=["Analytics"])

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
    "parse": "文档解析",
    "analyze": "法律分析",
    "falsify": "证伪核验",
}

TASK_STATUS_LABELS = {
    "queued": "排队中",
    "pending": "待处理",
    "processing": "处理中",
    "completed": "已完成",
    "failed": "失败",
    "dead": "死信",
    "retrying": "重试中",
}


def _require_analytics_access(current_user: User) -> None:
    if can_manage_case_role(current_user.role):
        return

    raise AppError(
        status_code=status.HTTP_403_FORBIDDEN,
        code=ErrorCode.FORBIDDEN,
        message="当前角色不能访问分析管理。",
        detail="当前角色不能访问分析管理。",
    )


def _get_tenant_or_404(db: Session, tenant_id: int) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if tenant is not None:
        return tenant

    raise AppError(
        status_code=status.HTTP_404_NOT_FOUND,
        code=ErrorCode.TENANT_NOT_FOUND,
        message="机构不存在。",
        detail="机构不存在。",
    )


def _float_cost(value: Decimal | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _build_window(
    *,
    tasks: list[AITask],
    results: list[AIAnalysisResult],
    baseline: datetime,
) -> AIUsageWindowRead:
    baseline_utc = _ensure_utc(baseline)
    return AIUsageWindowRead(
        task_count=sum(
            1
            for item in tasks
            if (_ensure_utc(item.created_at) or datetime.min.replace(tzinfo=timezone.utc)) >= baseline_utc
        ),
        token_usage=sum(
            item.token_usage
            for item in results
            if (_ensure_utc(item.created_at) or datetime.min.replace(tzinfo=timezone.utc)) >= baseline_utc
        ),
        cost_total=round(
            sum(
                _float_cost(item.cost)
                for item in results
                if (_ensure_utc(item.created_at) or datetime.min.replace(tzinfo=timezone.utc)) >= baseline_utc
            ),
            4,
        ),
    )


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


@router.get("/ai-usage", response_model=AIUsageRead)
def get_ai_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIUsageRead:
    _require_analytics_access(current_user)

    now = datetime.now(timezone.utc)
    day_start = now - timedelta(days=1)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)

    tasks = (
        db.query(AITask)
        .filter(AITask.tenant_id == current_user.tenant_id)
        .order_by(AITask.created_at.desc())
        .all()
    )
    results = (
        db.query(AIAnalysisResult)
        .filter(AIAnalysisResult.tenant_id == current_user.tenant_id)
        .order_by(AIAnalysisResult.created_at.desc())
        .all()
    )

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
        model_bucket["cost_total"] += _float_cost(item.cost)

    return AIUsageRead(
        day=_build_window(tasks=tasks, results=results, baseline=day_start),
        week=_build_window(tasks=tasks, results=results, baseline=week_start),
        month=_build_window(tasks=tasks, results=results, baseline=month_start),
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


@router.get("/prompts", response_model=PromptSettingsRead)
def get_prompt_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PromptSettingsRead:
    _require_analytics_access(current_user)
    tenant = _get_tenant_or_404(db, current_user.tenant_id)
    payload = {**DEFAULT_PROMPT_SETTINGS, **(tenant.ai_prompt_settings or {})}
    return PromptSettingsRead(**payload)


@router.put("/prompts", response_model=PromptSettingsRead)
def update_prompt_settings(
    payload: PromptSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PromptSettingsRead:
    _require_analytics_access(current_user)
    tenant = _get_tenant_or_404(db, current_user.tenant_id)
    tenant.ai_prompt_settings = payload.model_dump()
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return PromptSettingsRead(**{**DEFAULT_PROMPT_SETTINGS, **(tenant.ai_prompt_settings or {})})


@router.get("/provider-settings", response_model=ProviderSettingsRead)
def get_provider_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProviderSettingsRead:
    _require_analytics_access(current_user)
    tenant = _get_tenant_or_404(db, current_user.tenant_id)
    payload = {**DEFAULT_PROVIDER_SETTINGS, **(tenant.ai_provider_settings or {})}
    return ProviderSettingsRead(
        provider_type=str(payload["provider_type"]),
        base_url=str(payload["base_url"]),
        model=str(payload["model"]),
        api_key_masked=_mask_secret(str(payload.get("api_key") or "")),
        editable=not tenant.ai_provider_locked,
        locked=tenant.ai_provider_locked,
    )


@router.put("/provider-settings", response_model=ProviderSettingsRead)
def update_provider_settings(
    payload: ProviderSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProviderSettingsRead:
    _require_analytics_access(current_user)
    tenant = _get_tenant_or_404(db, current_user.tenant_id)

    if tenant.ai_provider_locked:
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.FORBIDDEN,
            message="当前 Provider 配置已锁定，不允许租户侧编辑。",
            detail="当前 Provider 配置已锁定，不允许租户侧编辑。",
        )

    existing = {**DEFAULT_PROVIDER_SETTINGS, **(tenant.ai_provider_settings or {})}
    if payload.api_key is not None:
        existing["api_key"] = payload.api_key.strip()
    existing["provider_type"] = payload.provider_type.strip() or DEFAULT_PROVIDER_SETTINGS["provider_type"]
    existing["base_url"] = payload.base_url.strip()
    existing["model"] = payload.model.strip()

    tenant.ai_provider_settings = existing
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return ProviderSettingsRead(
        provider_type=str(existing["provider_type"]),
        base_url=str(existing["base_url"]),
        model=str(existing["model"]),
        api_key_masked=_mask_secret(str(existing.get("api_key") or "")),
        editable=True,
        locked=False,
    )
