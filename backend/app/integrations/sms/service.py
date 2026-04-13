from __future__ import annotations

import secrets
from datetime import timedelta

from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.integrations.sms.guard_service import (
    SMS_SEND_DEVICE_MAX_COUNT,
    SMS_SEND_DEVICE_WINDOW_SECONDS,
    SMS_SEND_INTERVAL_SECONDS,
    SMS_SEND_IP_MAX_COUNT,
    SMS_SEND_IP_WINDOW_SECONDS,
    SMS_VERIFY_DEVICE_MAX_COUNT,
    SMS_VERIFY_DEVICE_WINDOW_SECONDS,
    SMS_VERIFY_IP_MAX_COUNT,
    SMS_VERIFY_IP_WINDOW_SECONDS,
    SMS_VERIFY_LOCK_SECONDS,
    SMS_VERIFY_MAX_FAIL_COUNT,
    SmsRequestContext,
    as_utc,
    build_rate_limit_error,
    build_verify_locked_error,
    enforce_request_rate_limits,
    record_sms_audit,
    utc_now,
)
from app.models.sms_code import SmsCode

SMS_EXPIRE_SECONDS = 300
SMS_VERIFY_TOKEN_EXPIRE_SECONDS = 600


def send_sms_code(
    db: Session,
    *,
    phone: str,
    purpose: str,
    context: SmsRequestContext | None = None,
) -> SmsCode:
    now = utc_now()
    enforce_request_rate_limits(
        db,
        phone=phone,
        purpose=purpose,
        action="send",
        context=context,
        now=now,
    )

    latest = (
        db.query(SmsCode)
        .filter(SmsCode.phone == phone, SmsCode.purpose == purpose)
        .order_by(SmsCode.created_at.desc())
        .first()
    )
    if latest is not None:
        latest_created_at = as_utc(latest.created_at)
        if latest_created_at >= now - timedelta(seconds=SMS_SEND_INTERVAL_SECONDS):
            retry_after = int((latest_created_at + timedelta(seconds=SMS_SEND_INTERVAL_SECONDS) - now).total_seconds())
            record_sms_audit(
                db,
                phone=phone,
                purpose=purpose,
                action="send",
                result="phone_interval_limited",
                context=context,
            )
            db.commit()
            raise build_rate_limit_error(retry_after=max(1, retry_after))

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
    record_sms_audit(
        db,
        phone=phone,
        purpose=purpose,
        action="send",
        result="sent",
        context=context,
    )
    db.commit()
    db.refresh(sms)
    return sms


def verify_sms_code(
    db: Session,
    *,
    phone: str,
    code: str,
    purpose: str,
    context: SmsRequestContext | None = None,
) -> str:
    now = utc_now()
    enforce_request_rate_limits(
        db,
        phone=phone,
        purpose=purpose,
        action="verify",
        context=context,
        now=now,
    )

    sms = (
        db.query(SmsCode)
        .filter(SmsCode.phone == phone, SmsCode.purpose == purpose)
        .order_by(SmsCode.created_at.desc())
        .first()
    )
    if sms is None or sms.consumed_at is not None:
        record_sms_audit(
            db,
            phone=phone,
            purpose=purpose,
            action="verify",
            result="invalid_code",
            context=context,
            detail="missing_or_consumed",
        )
        db.commit()
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.SMS_CODE_INVALID,
            message="验证码错误或已使用。",
            detail="验证码错误或已使用。",
        )

    expires_at = as_utc(sms.expires_at)
    if expires_at < now:
        record_sms_audit(
            db,
            phone=phone,
            purpose=purpose,
            action="verify",
            result="expired_code",
            context=context,
        )
        db.commit()
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.SMS_CODE_EXPIRED,
            message="验证码已过期，请重新获取。",
            detail="验证码已过期，请重新获取。",
        )

    locked_until = as_utc(sms.verify_locked_until) if sms.verify_locked_until is not None else None
    if locked_until is not None and locked_until > now:
        retry_after = int((locked_until - now).total_seconds())
        record_sms_audit(
            db,
            phone=phone,
            purpose=purpose,
            action="verify",
            result="code_locked",
            context=context,
        )
        db.commit()
        raise build_verify_locked_error(retry_after=max(1, retry_after))

    if sms.code != code:
        sms.verify_fail_count = int(sms.verify_fail_count or 0) + 1
        result = "invalid_code"
        if sms.verify_fail_count >= SMS_VERIFY_MAX_FAIL_COUNT:
            sms.verify_locked_until = now + timedelta(seconds=SMS_VERIFY_LOCK_SECONDS)
            result = "code_locked"

        db.add(sms)
        record_sms_audit(
            db,
            phone=phone,
            purpose=purpose,
            action="verify",
            result=result,
            context=context,
        )
        db.commit()

        if result == "code_locked":
            raise build_verify_locked_error(retry_after=SMS_VERIFY_LOCK_SECONDS)

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
    record_sms_audit(
        db,
        phone=phone,
        purpose=purpose,
        action="verify",
        result="verified",
        context=context,
    )
    db.commit()

    return sms.verification_token


def assert_phone_verified(db: Session, *, phone: str, purpose: str, verification_token: str) -> None:
    now = utc_now()
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

    expires_at = as_utc(sms.verification_expires_at) if sms.verification_expires_at is not None else None
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
