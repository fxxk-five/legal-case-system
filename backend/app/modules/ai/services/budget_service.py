from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from fastapi import status

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.models.user import User
from app.modules.cases.models.case import Case

if TYPE_CHECKING:
    from app.modules.ai.service import AIService


def ensure_personal_tenant_ai_access(
    service: AIService,
    *,
    current_user: User,
) -> None:
    tenant = service.repo.get_tenant(tenant_id=current_user.tenant_id)
    if tenant is None or tenant.type != "personal":
        return

    is_subscription_valid = (
        tenant.subscription_expire_at is not None
        and tenant.subscription_expire_at > datetime.now(timezone.utc)
    )
    has_balance = bool(tenant.balance and Decimal(str(tenant.balance)) > Decimal("0"))
    if not (is_subscription_valid or has_balance):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.AI_OPERATION_NOT_ALLOWED,
            message="独户律师订阅已失效且余额不足，无法发起AI任务。",
            detail="独户律师订阅已失效且余额不足，无法发起AI任务。",
        )


def resolve_budget_policy_for_analysis(
    service: AIService,
    *,
    case: Case,
    current_user: User,
    is_auto_trigger: bool,
) -> str | None:
    tenant = service.repo.get_tenant(tenant_id=case.tenant_id)
    monthly_limit = to_decimal_or_none(
        tenant.ai_monthly_budget_limit if tenant is not None else settings.AI_MONTHLY_BUDGET_LIMIT
    )
    case_limit = to_decimal_or_none(
        case.ai_case_budget_limit
        if case.ai_case_budget_limit is not None
        else settings.AI_CASE_BUDGET_LIMIT
    )
    degrade_model = (
        str(
            (tenant.ai_budget_degrade_model if tenant is not None else "")
            or settings.AI_BUDGET_DEGRADE_MODEL
            or ""
        )
        .strip()
        or None
    )

    monthly_spent = Decimal("0")
    case_spent = Decimal("0")
    if monthly_limit is not None:
        month_start, month_end = month_window(datetime.now(timezone.utc))
        monthly_spent = service.repo.sum_analysis_cost_for_tenant_in_month(
            tenant_id=case.tenant_id,
            month_start=month_start,
            month_end=month_end,
        )
    if case_limit is not None:
        case_spent = service.repo.sum_analysis_cost_for_case(
            case_id=case.id,
            tenant_id=case.tenant_id,
        )

    over_monthly = monthly_limit is not None and monthly_spent >= monthly_limit
    over_case = case_limit is not None and case_spent >= case_limit
    if not (over_monthly or over_case):
        return None

    reason_parts: list[str] = []
    if over_monthly and monthly_limit is not None:
        reason_parts.append(f"tenant monthly limit reached ({monthly_spent}/{monthly_limit})")
    if over_case and case_limit is not None:
        reason_parts.append(f"case limit reached ({case_spent}/{case_limit})")
    reason = "; ".join(reason_parts) or "budget limit reached"

    if not is_auto_trigger and degrade_model and degrade_model != settings.EFFECTIVE_AI_MODEL:
        service._append_case_flow(
            case_id=case.id,
            tenant_id=case.tenant_id,
            action_type="analysis_model_downgraded",
            content=f"Budget control applied; downgraded to model {degrade_model} ({reason}).",
            operator_id=current_user.id,
            visible_to="both",
        )
        service.repo.commit()
        return degrade_model

    service._append_case_flow(
        case_id=case.id,
        tenant_id=case.tenant_id,
        action_type="analysis_budget_circuit_open",
        content=f"Budget circuit open; analyze request blocked ({reason}).",
        operator_id=current_user.id,
        visible_to="both",
    )
    service.repo.commit()
    raise AppError(
        status_code=status.HTTP_409_CONFLICT,
        code=ErrorCode.AI_BUDGET_EXCEEDED,
        message="AI预算已超限，当前请求已被熔断。",
        detail=f"AI预算已超限，当前请求已被熔断。{reason}",
    )


def to_decimal_or_none(value: object | None) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        parsed = Decimal(str(value))
    except Exception:  # noqa: BLE001
        return None
    if parsed <= 0:
        return None
    return parsed


def month_window(now: datetime) -> tuple[datetime, datetime]:
    current = now.astimezone(timezone.utc)
    month_start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if month_start.month == 12:
        month_end = month_start.replace(year=month_start.year + 1, month=1)
    else:
        month_end = month_start.replace(month=month_start.month + 1)
    return month_start, month_end
