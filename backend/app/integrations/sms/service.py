from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.models.sms_code import SmsCode

SMS_EXPIRE_SECONDS = 300
SMS_VERIFY_TOKEN_EXPIRE_SECONDS = 600
SMS_SEND_INTERVAL_SECONDS = 60
SMS_VERIFY_MAX_FAIL_COUNT = 5
SMS_VERIFY_LOCK_SECONDS = 300


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _build_rate_limit_error(*, retry_after: int) -> AppError:
    return AppError(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        code=ErrorCode.SMS_CODE_RATE_LIMITED,
        message=f"验证码发送过于频繁，请 {retry_after} 秒后重试。",
        detail=f"验证码发送过于频繁，请 {retry_after} 秒后重试。",
    )


def _build_verify_locked_error(*, retry_after: int) -> AppError:
    return AppError(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        code=ErrorCode.SMS_CODE_RATE_LIMITED,
        message=f"验证码校验次数过多，请 {retry_after} 秒后重试。",
        detail=f"验证码校验次数过多，请 {retry_after} 秒后重试。",
    )


def send_sms_code(db: Session, *, phone: str, purpose: str) -> SmsCode:
    now = _utc_now()
    latest = (
        db.query(SmsCode)
        .filter(SmsCode.phone == phone, SmsCode.purpose == purpose)
        .order_by(SmsCode.created_at.desc())
        .first()
    )
    if latest is not None:
        latest_created_at = _as_utc(latest.created_at)
        if latest_created_at >= now - timedelta(seconds=SMS_SEND_INTERVAL_SECONDS):
            retry_after = int((latest_created_at + timedelta(seconds=SMS_SEND_INTERVAL_SECONDS) - now).total_seconds())
            raise _build_rate_limit_error(retry_after=max(1, retry_after))

    sms = SmsCode(
        phone=phone,
        purpose=purpose,
        code=f"{secrets.randbelow(1000000):06d}",
        request_id=secrets.token_hex(16),
        expires_at=now + timedelta(seconds=SMS_EXPIRE_SECONDS),
        verify_fail_count=0,
        verify_locked_until=None,
        verification_token=None,
        verification_expires_at=None,
        verification_consumed_at=None,
    )
    db.add(sms)
    db.commit()
    db.refresh(sms)
    return sms


def verify_sms_code(db: Session, *, phone: str, code: str, purpose: str) -> str:
    now = _utc_now()
    sms = (
        db.query(SmsCode)
        .filter(SmsCode.phone == phone, SmsCode.purpose == purpose)
        .order_by(SmsCode.created_at.desc())
        .first()
    )
    if sms is None or sms.consumed_at is not None:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.SMS_CODE_INVALID,
            message="验证码错误或已使用。",
            detail="验证码错误或已使用。",
        )

    expires_at = _as_utc(sms.expires_at)
    if expires_at < now:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.SMS_CODE_EXPIRED,
            message="验证码已过期，请重新获取。",
            detail="验证码已过期，请重新获取。",
        )

    locked_until = _as_utc(sms.verify_locked_until) if sms.verify_locked_until is not None else None
    if locked_until is not None and locked_until > now:
        retry_after = int((locked_until - now).total_seconds())
        raise _build_verify_locked_error(retry_after=max(1, retry_after))

    if sms.code != code:
        sms.verify_fail_count = int(sms.verify_fail_count or 0) + 1
        if sms.verify_fail_count >= SMS_VERIFY_MAX_FAIL_COUNT:
            sms.verify_locked_until = now + timedelta(seconds=SMS_VERIFY_LOCK_SECONDS)
            db.add(sms)
            db.commit()
            raise _build_verify_locked_error(retry_after=SMS_VERIFY_LOCK_SECONDS)

        db.add(sms)
        db.commit()
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.SMS_CODE_INVALID,
            message="验证码错误或已使用。",
            detail="验证码错误或已使用。",
        )

    sms.consumed_at = now
    sms.verify_fail_count = 0
    sms.verify_locked_until = None
    sms.verification_token = secrets.token_urlsafe(24)
    sms.verification_expires_at = now + timedelta(seconds=SMS_VERIFY_TOKEN_EXPIRE_SECONDS)
    sms.verification_consumed_at = None
    db.add(sms)
    db.commit()

    return sms.verification_token


def assert_phone_verified(db: Session, *, phone: str, purpose: str, verification_token: str) -> None:
    now = _utc_now()
    sms = (
        db.query(SmsCode)
        .filter(
            SmsCode.phone == phone,
            SmsCode.purpose == purpose,
            SmsCode.verification_token == verification_token,
        )
        .order_by(SmsCode.created_at.desc())
        .first()
    )

    if sms is None:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.PHONE_NOT_VERIFIED,
            message="手机号尚未完成验证码校验。",
            detail="手机号尚未完成验证码校验。",
        )

    expires_at = _as_utc(sms.verification_expires_at) if sms.verification_expires_at is not None else None
    if expires_at is None or expires_at < now:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.PHONE_NOT_VERIFIED,
            message="手机号验证令牌已过期，请重新验证。",
            detail="手机号验证令牌已过期，请重新验证。",
        )

    if sms.verification_consumed_at is not None:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.PHONE_NOT_VERIFIED,
            message="手机号验证令牌已被使用，请重新验证。",
            detail="手机号验证令牌已被使用，请重新验证。",
        )

    sms.verification_consumed_at = now
    db.add(sms)
    db.commit()
