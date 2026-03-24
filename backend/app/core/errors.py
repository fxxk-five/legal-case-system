from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from fastapi import status


class ErrorCode(str, Enum):
    AUTH_REQUIRED = "AUTH_REQUIRED"
    FORBIDDEN = "FORBIDDEN"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFLICT = "CONFLICT"
    INTERNAL_ERROR = "INTERNAL_ERROR"

    TENANT_NOT_FOUND = "TENANT_NOT_FOUND"
    TENANT_INACTIVE = "TENANT_INACTIVE"
    TENANT_ACCESS_DENIED = "TENANT_ACCESS_DENIED"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    USER_ALREADY_EXISTS = "USER_ALREADY_EXISTS"
    USER_NOT_ACTIVE = "USER_NOT_ACTIVE"

    CASE_NOT_FOUND = "CASE_NOT_FOUND"
    CASE_ACCESS_DENIED = "CASE_ACCESS_DENIED"
    CASE_OPERATION_NOT_ALLOWED = "CASE_OPERATION_NOT_ALLOWED"

    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_ACCESS_DENIED = "FILE_ACCESS_DENIED"
    FILE_TOKEN_INVALID = "FILE_TOKEN_INVALID"
    FILE_UPLOAD_INVALID = "FILE_UPLOAD_INVALID"

    INVITE_NOT_FOUND = "INVITE_NOT_FOUND"
    INVITE_EXPIRED = "INVITE_EXPIRED"
    INVITE_INVALID = "INVITE_INVALID"
    INVITE_REQUIRED = "INVITE_REQUIRED"
    PHONE_NOT_VERIFIED = "PHONE_NOT_VERIFIED"
    SMS_CODE_RATE_LIMITED = "SMS_CODE_RATE_LIMITED"
    SMS_CODE_INVALID = "SMS_CODE_INVALID"
    SMS_CODE_EXPIRED = "SMS_CODE_EXPIRED"
    NOTIFICATION_NOT_FOUND = "NOTIFICATION_NOT_FOUND"

    AI_TASK_NOT_FOUND = "AI_TASK_NOT_FOUND"
    AI_ANALYSIS_NOT_FOUND = "AI_ANALYSIS_NOT_FOUND"
    AI_OPERATION_NOT_ALLOWED = "AI_OPERATION_NOT_ALLOWED"
    AI_TASK_CONFLICT = "AI_TASK_CONFLICT"
    AI_PROVIDER_ERROR = "AI_PROVIDER_ERROR"
    AI_BUDGET_EXCEEDED = "AI_BUDGET_EXCEEDED"

    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    WECHAT_API_ERROR = "WECHAT_API_ERROR"
    STORAGE_ERROR = "STORAGE_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"


ErrorDetail = str | dict[str, Any] | list[Any] | None


@dataclass(slots=True)
class AppError(Exception):
    status_code: int
    code: ErrorCode
    message: str
    detail: ErrorDetail = None

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def map_http_status_to_code(status_code: int) -> ErrorCode:
    if status_code == status.HTTP_401_UNAUTHORIZED:
        return ErrorCode.AUTH_REQUIRED
    if status_code == status.HTTP_403_FORBIDDEN:
        return ErrorCode.FORBIDDEN
    if status_code == status.HTTP_404_NOT_FOUND:
        return ErrorCode.RESOURCE_NOT_FOUND
    if status_code == status.HTTP_409_CONFLICT:
        return ErrorCode.CONFLICT
    if status_code in {status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY}:
        return ErrorCode.VALIDATION_ERROR
    if status_code in {
        status.HTTP_502_BAD_GATEWAY,
        status.HTTP_503_SERVICE_UNAVAILABLE,
        status.HTTP_504_GATEWAY_TIMEOUT,
    }:
        return ErrorCode.EXTERNAL_SERVICE_ERROR
    return ErrorCode.INTERNAL_ERROR
