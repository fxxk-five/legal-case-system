from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.models.sms_audit_log import SmsAuditLog

SMS_SEND_INTERVAL_SECONDS = 60
SMS_VERIFY_MAX_FAIL_COUNT = 5
SMS_VERIFY_LOCK_SECONDS = 300

SMS_SEND_IP_WINDOW_SECONDS = 600
SMS_SEND_IP_MAX_COUNT = 20
SMS_SEND_DEVICE_WINDOW_SECONDS = 600
SMS_SEND_DEVICE_MAX_COUNT = 8
SMS_VERIFY_IP_WINDOW_SECONDS = 600
SMS_VERIFY_IP_MAX_COUNT = 30
SMS_VERIFY_DEVICE_WINDOW_SECONDS = 600
SMS_VERIFY_DEVICE_MAX_COUNT = 12


@dataclass(frozen=True)
class SmsRequestContext:
    client_ip: str | None = None
    device_fingerprint: str | None = None
    request_id: str | None = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def build_rate_limit_error(*, retry_after: int) -> AppError:
    return AppError(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        code=ErrorCode.SMS_CODE_RATE_LIMITED,
        message=f"验证码请求过于频繁，请 {retry_after} 秒后重试。",
        detail=f"验证码请求过于频繁，请 {retry_after} 秒后重试。",
    )


def build_verify_locked_error(*, retry_after: int) -> AppError:
    return AppError(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        code=ErrorCode.SMS_CODE_RATE_LIMITED,
        message=f"验证码校验次数过多，请 {retry_after} 秒后重试。",
        detail=f"验证码校验次数过多，请 {retry_after} 秒后重试。",
    )


def record_sms_audit(
    db: Session,
    *,
    phone: str,
    purpose: str,
    action: str,
    result: str,
    context: SmsRequestContext | None,
    detail: str | None = None,
) -> SmsAuditLog:
    audit_log = SmsAuditLog(
        phone=phone,
        purpose=purpose,
        action=action,
        result=result,
        client_ip=context.client_ip if context else None,
        device_fingerprint=context.device_fingerprint if context else None,
        request_id=context.request_id if context else None,
        detail=detail,
    )
    db.add(audit_log)
    return audit_log


def _recent_attempt_timestamps(
    db: Session,
    *,
    action: str,
    field_name: str,
    field_value: str | None,
    window_seconds: int,
    now: datetime,
) -> list[datetime]:
    if not field_value:
        return []

    column = getattr(SmsAuditLog, field_name)
    since = now - timedelta(seconds=window_seconds)
    rows = (
        db.query(SmsAuditLog.created_at)
        .filter(
            SmsAuditLog.action == action,
            column == field_value,
            SmsAuditLog.created_at >= since,
        )
        .order_by(SmsAuditLog.created_at.asc())
        .all()
    )
    return [as_utc(created_at) for created_at, in rows if created_at is not None]


def _rate_limit_retry_after(
    *,
    timestamps: list[datetime],
    window_seconds: int,
    limit: int,
    now: datetime,
) -> int | None:
    if len(timestamps) < limit:
        return None

    expire_count = len(timestamps) - limit + 1
    boundary = timestamps[expire_count - 1]
    retry_after = int((boundary + timedelta(seconds=window_seconds) - now).total_seconds())
    return max(1, retry_after)


def _enforce_dimension_rate_limit(
    db: Session,
    *,
    phone: str,
    purpose: str,
    action: str,
    field_name: str,
    field_value: str | None,
    window_seconds: int,
    limit: int,
    result: str,
    now: datetime,
    context: SmsRequestContext | None,
) -> None:
    timestamps = _recent_attempt_timestamps(
        db,
        action=action,
        field_name=field_name,
        field_value=field_value,
        window_seconds=window_seconds,
        now=now,
    )
    retry_after = _rate_limit_retry_after(
        timestamps=timestamps,
        window_seconds=window_seconds,
        limit=limit,
        now=now,
    )
    if retry_after is None:
        return

    record_sms_audit(
        db,
        phone=phone,
        purpose=purpose,
        action=action,
        result=result,
        context=context,
        detail=f"{field_name}:{field_value}",
    )
    db.commit()
    raise build_rate_limit_error(retry_after=retry_after)


def enforce_request_rate_limits(
    db: Session,
    *,
    phone: str,
    purpose: str,
    action: str,
    context: SmsRequestContext | None,
    now: datetime,
) -> None:
    if context is None:
        return

    if action == "send":
        _enforce_dimension_rate_limit(
            db,
            phone=phone,
            purpose=purpose,
            action=action,
            field_name="client_ip",
            field_value=context.client_ip,
            window_seconds=SMS_SEND_IP_WINDOW_SECONDS,
            limit=SMS_SEND_IP_MAX_COUNT,
            result="ip_rate_limited",
            now=now,
            context=context,
        )
        _enforce_dimension_rate_limit(
            db,
            phone=phone,
            purpose=purpose,
            action=action,
            field_name="device_fingerprint",
            field_value=context.device_fingerprint,
            window_seconds=SMS_SEND_DEVICE_WINDOW_SECONDS,
            limit=SMS_SEND_DEVICE_MAX_COUNT,
            result="device_rate_limited",
            now=now,
            context=context,
        )
        return

    _enforce_dimension_rate_limit(
        db,
        phone=phone,
        purpose=purpose,
        action=action,
        field_name="client_ip",
        field_value=context.client_ip,
        window_seconds=SMS_VERIFY_IP_WINDOW_SECONDS,
        limit=SMS_VERIFY_IP_MAX_COUNT,
        result="ip_rate_limited",
        now=now,
        context=context,
    )
    _enforce_dimension_rate_limit(
        db,
        phone=phone,
        purpose=purpose,
        action=action,
        field_name="device_fingerprint",
        field_value=context.device_fingerprint,
        window_seconds=SMS_VERIFY_DEVICE_WINDOW_SECONDS,
        limit=SMS_VERIFY_DEVICE_MAX_COUNT,
        result="device_rate_limited",
        now=now,
        context=context,
    )
