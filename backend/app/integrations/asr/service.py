from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from uuid import uuid4

import httpx
from fastapi import status

from app.core.config import settings
from app.core.errors import AppError, ErrorCode


_TENCENT_ASR_HOST = "asr.tencentcloudapi.com"
_TENCENT_ASR_ENDPOINT = f"https://{_TENCENT_ASR_HOST}"
_TENCENT_ASR_ACTION = "SentenceRecognition"
_TENCENT_ASR_VERSION = "2019-06-14"
_DEFAULT_ENGINE_TYPE = "16k_zh"


async def transcribe_audio_bytes(audio_bytes: bytes, *, voice_format: str) -> str:
    secret_id = (settings.TENCENT_ASR_SECRET_ID or "").strip()
    secret_key = (settings.TENCENT_ASR_SECRET_KEY or "").strip()
    if not secret_id or not secret_key:
        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message="ASR service is not configured.",
            detail="TENCENT_ASR_SECRET_ID / TENCENT_ASR_SECRET_KEY are required.",
        )

    payload = {
        "ProjectId": 0,
        "SubServiceType": 2,
        "EngSerViceType": _DEFAULT_ENGINE_TYPE,
        "SourceType": 1,
        "VoiceFormat": voice_format,
        "UsrAudioKey": str(uuid4()),
        "Data": base64.b64encode(audio_bytes).decode("utf-8"),
        "DataLen": len(audio_bytes),
    }
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    headers = _build_tencent_auth_headers(
        secret_id=secret_id,
        secret_key=secret_key,
        service="asr",
        host=_TENCENT_ASR_HOST,
        action=_TENCENT_ASR_ACTION,
        version=_TENCENT_ASR_VERSION,
        region=(settings.TENCENT_ASR_REGION or "").strip() or "ap-guangzhou",
        payload=payload_json,
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                _TENCENT_ASR_ENDPOINT,
                headers=headers,
                content=payload_json.encode("utf-8"),
            )
    except httpx.TimeoutException as exc:
        raise AppError(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message="ASR request timed out.",
            detail="ASR request timed out.",
        ) from exc
    except httpx.HTTPError as exc:
        raise AppError(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message="ASR request failed.",
            detail=str(exc),
        ) from exc

    try:
        result = response.json()
    except ValueError as exc:
        raise AppError(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message="ASR returned invalid JSON.",
            detail=response.text[:500],
        ) from exc

    response_payload = result.get("Response") if isinstance(result, dict) else None
    if not isinstance(response_payload, dict):
        raise AppError(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message="ASR returned an unexpected payload.",
            detail=result,
        )

    error_payload = response_payload.get("Error")
    if isinstance(error_payload, dict):
        error_message = str(error_payload.get("Message") or "upstream_error").strip()
        raise AppError(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message="ASR transcription failed.",
            detail=error_message or "upstream_error",
        )

    transcript = str(response_payload.get("Result") or "").strip()
    if not transcript:
        raise AppError(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message="ASR returned an empty transcript.",
            detail=response_payload,
        )
    return transcript


def _build_tencent_auth_headers(
    *,
    secret_id: str,
    secret_key: str,
    service: str,
    host: str,
    action: str,
    version: str,
    region: str,
    payload: str,
) -> dict[str, str]:
    algorithm = "TC3-HMAC-SHA256"
    timestamp = int(time.time())
    date = time.strftime("%Y-%m-%d", time.gmtime(timestamp))
    canonical_headers = f"content-type:application/json; charset=utf-8\nhost:{host}\n"
    signed_headers = "content-type;host"
    hashed_payload = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    canonical_request = f"POST\n/\n\n{canonical_headers}\n{signed_headers}\n{hashed_payload}"
    credential_scope = f"{date}/{service}/tc3_request"
    hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    string_to_sign = f"{algorithm}\n{timestamp}\n{credential_scope}\n{hashed_canonical_request}"

    def sign(key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    secret_date = sign(f"TC3{secret_key}".encode("utf-8"), date)
    secret_service = sign(secret_date, service)
    secret_signing = sign(secret_service, "tc3_request")
    signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    authorization = (
        f"{algorithm} Credential={secret_id}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    return {
        "Authorization": authorization,
        "Content-Type": "application/json; charset=utf-8",
        "Host": host,
        "X-TC-Action": action,
        "X-TC-Timestamp": str(timestamp),
        "X-TC-Version": version,
        "X-TC-Region": region,
    }
