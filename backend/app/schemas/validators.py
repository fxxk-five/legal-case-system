import re

from app.core.errors import AppError, ErrorCode


PHONE_REGEX = re.compile(r"^1[3-9]\d{9}$")
PASSWORD_REGEX = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)\S{8,128}$")
TENANT_CODE_REGEX = re.compile(r"^[a-z0-9_-]{3,50}$")
SMS_CODE_REGEX = re.compile(r"^\d{6}$")


def normalize_phone(phone: str) -> str:
    return phone.strip()


def validate_phone(phone: str) -> str:
    normalized = normalize_phone(phone)
    if not PHONE_REGEX.fullmatch(normalized):
        raise ValueError("手机号格式不正确，应为 11 位中国大陆手机号。")
    return normalized


def validate_password(password: str) -> str:
    if not PASSWORD_REGEX.fullmatch(password):
        raise ValueError("密码必须为 8-128 位，且包含字母与数字，不能包含空格。")
    return password


def validate_tenant_code(tenant_code: str) -> str:
    normalized = tenant_code.strip().lower()
    if not TENANT_CODE_REGEX.fullmatch(normalized):
        raise ValueError("tenant_code 仅允许小写字母、数字、下划线、中划线，长度 3-50。")
    return normalized


def validate_sms_code(code: str) -> str:
    normalized = code.strip()
    if not SMS_CODE_REGEX.fullmatch(normalized):
        raise ValueError("验证码必须为 6 位数字。")
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
