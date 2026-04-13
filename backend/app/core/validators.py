import re

from app.core.errors import AppError, ErrorCode


PHONE_REGEX = re.compile(r"^1[3-9]\d{9}$")
LEGACY_PASSWORD_REGEX = re.compile(r"^\S{8,128}$")
PASSWORD_REGEX = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)\S{10,128}$")
TENANT_CODE_REGEX = re.compile(r"^[a-z0-9_-]{3,50}$")
SMS_CODE_REGEX = re.compile(r"^\d{6}$")


def normalize_phone(phone: str) -> str:
    return phone.strip()


def validate_phone(phone: str) -> str:
    normalized = normalize_phone(phone)
    if not PHONE_REGEX.fullmatch(normalized):
        raise ValueError("Phone number must be an 11-digit mainland China mobile number.")
    return normalized


def validate_password(password: str) -> str:
    if not PASSWORD_REGEX.fullmatch(password):
        raise ValueError("Password must be 10-128 chars with upper, lower, and digit, without spaces.")
    return password


def validate_existing_password(password: str) -> str:
    if not LEGACY_PASSWORD_REGEX.fullmatch(password):
        raise ValueError("Password must be 8-128 characters without spaces.")
    return password


def validate_tenant_code(tenant_code: str) -> str:
    normalized = tenant_code.strip().lower()
    if not TENANT_CODE_REGEX.fullmatch(normalized):
        raise ValueError("tenant_code may only contain lowercase letters, numbers, _ or -, length 3-50.")
    return normalized


def validate_sms_code(code: str) -> str:
    normalized = code.strip()
    if not SMS_CODE_REGEX.fullmatch(normalized):
        raise ValueError("SMS code must be 6 digits.")
    return normalized


def enforce_phone(phone: str) -> str:
    try:
        return validate_phone(phone)
    except ValueError as exc:
        raise AppError(status_code=400, code=ErrorCode.VALIDATION_ERROR, message=str(exc), detail=str(exc)) from exc


def enforce_password(password: str) -> str:
    try:
        return validate_password(password)
    except ValueError as exc:
        raise AppError(status_code=400, code=ErrorCode.VALIDATION_ERROR, message=str(exc), detail=str(exc)) from exc


def enforce_existing_password(password: str) -> str:
    try:
        return validate_existing_password(password)
    except ValueError as exc:
        raise AppError(status_code=400, code=ErrorCode.VALIDATION_ERROR, message=str(exc), detail=str(exc)) from exc
