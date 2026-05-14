from __future__ import annotations

from hashlib import sha256

from fastapi import Request
from sqlalchemy.orm import Session

from app.integrations.sms.service import (
    SMS_EXPIRE_SECONDS,
    SMS_SEND_INTERVAL_SECONDS,
    SMS_VERIFY_TOKEN_EXPIRE_SECONDS,
    SmsRequestContext,
    send_sms_code,
    verify_sms_code,
)
from app.modules.auth.schemas import SmsSendRequest, SmsSendResponse, SmsVerifyRequest, SmsVerifyResponse


SMS_DEVICE_FINGERPRINT_HEADERS = (
    "x-device-fingerprint",
    "user-agent",
    "x-client-platform",
    "x-client-source",
    "accept-language",
    "sec-ch-ua",
    "sec-ch-ua-platform",
)


class AuthSmsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _resolve_client_ip(request: Request | None) -> str | None:
        if request is None:
            return None

        forwarded_for = (request.headers.get("x-forwarded-for") or "").strip()
        if forwarded_for:
            candidate = forwarded_for.split(",")[0].strip()
            if candidate:
                return candidate[:64]

        real_ip = (request.headers.get("x-real-ip") or "").strip()
        if real_ip:
            return real_ip[:64]

        if request.client and request.client.host:
            return request.client.host[:64]
        return None

    @classmethod
    def build_sms_request_context(cls, request: Request | None) -> SmsRequestContext:
        client_ip = cls._resolve_client_ip(request)
        if request is None:
            return SmsRequestContext(client_ip=client_ip)

        fingerprint_parts: list[str] = []
        for header_name in SMS_DEVICE_FINGERPRINT_HEADERS:
            value = (request.headers.get(header_name) or "").strip()
            if value:
                fingerprint_parts.append(f"{header_name}={value}")

        if not fingerprint_parts and client_ip:
            fingerprint_parts.append(f"remote={client_ip}")

        device_fingerprint = (
            sha256("|".join(fingerprint_parts).encode("utf-8")).hexdigest()
            if fingerprint_parts
            else None
        )
        return SmsRequestContext(
            client_ip=client_ip,
            device_fingerprint=device_fingerprint,
            request_id=getattr(request.state, "request_id", None),
        )

    def send_phone_sms(self, *, request: Request, sms_in: SmsSendRequest) -> SmsSendResponse:
        sms = send_sms_code(
            self.db,
            phone=sms_in.phone,
            purpose=sms_in.purpose,
            context=self.build_sms_request_context(request),
        )
        return SmsSendResponse(
            phone=sms.phone,
            expires_in_seconds=SMS_EXPIRE_SECONDS,
            retry_after_seconds=SMS_SEND_INTERVAL_SECONDS,
            request_id=sms.request_id,
        )

    def verify_phone_sms(self, *, request: Request, sms_in: SmsVerifyRequest) -> SmsVerifyResponse:
        token = verify_sms_code(
            self.db,
            phone=sms_in.phone,
            code=sms_in.code,
            purpose=sms_in.purpose,
            context=self.build_sms_request_context(request),
        )
        return SmsVerifyResponse(
            phone=sms_in.phone,
            verification_token=token,
            expires_in_seconds=SMS_VERIFY_TOKEN_EXPIRE_SECONDS,
        )
