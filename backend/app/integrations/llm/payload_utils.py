from __future__ import annotations

import json
import re
from typing import Any

from fastapi import status

from app.core.config import settings
from app.core.errors import AppError, ErrorCode


def parse_json_payload(content: str) -> dict[str, Any]:
    text = content.strip()
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    if text.startswith("{") and text.endswith("}"):
        return json.loads(text)

    first = text.find("{")
    last = text.rfind("}")
    if first == -1 or last == -1 or first >= last:
        raise ValueError("no_json_object")
    return json.loads(text[first : last + 1])


def extract_provider_error(raw_error: str) -> str:
    try:
        parsed = json.loads(raw_error)
        return (
            parsed.get("error", {}).get("message")
            or parsed.get("message")
            or "upstream_error"
        )
    except Exception:  # noqa: BLE001
        return raw_error[:500] or "upstream_error"


def summarize_provider_error(raw_error: str) -> str:
    try:
        parsed = json.loads(raw_error)
    except Exception:  # noqa: BLE001
        return "non_json_error"

    error_payload = parsed.get("error")
    if isinstance(error_payload, dict):
        error_type = str(error_payload.get("type") or "unknown")
        error_code = str(error_payload.get("code") or "unknown")
        return f"json_error type={error_type} code={error_code}"
    return "json_error type=unknown code=unknown"


def summarize_provider_payload(raw: object) -> str:
    if not isinstance(raw, dict):
        return f"payload_type={type(raw).__name__}"

    choices = raw.get("choices")
    choice_count = len(choices) if isinstance(choices, list) else 0
    usage = raw.get("usage")
    usage_keys = sorted(usage.keys()) if isinstance(usage, dict) else []
    top_level_keys = sorted(str(key) for key in raw.keys())
    model = str(raw.get("model") or "")
    return (
        f"keys={top_level_keys} "
        f"choice_count={choice_count} "
        f"usage_keys={usage_keys} "
        f"model={model}"
    )


def ensure_provider_configured(
    *,
    api_key: str,
    api_base: str,
    model: str,
    logger,
) -> None:
    if not settings.AI_ENABLED:
        logger.error("ai.provider.disabled ai_enabled=%s", settings.AI_ENABLED)
        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=ErrorCode.AI_OPERATION_NOT_ALLOWED,
            message="AI功能未启用。",
            detail="AI功能未启用。",
        )
    if not api_key:
        logger.error(
            "ai.provider.misconfigured missing_api_key base=%s model=%s mock_mode=%s",
            api_base,
            model,
            settings.AI_MOCK_MODE,
        )
        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message="OPENAI_API_KEY 未配置。",
            detail="OPENAI_API_KEY 未配置。",
        )
    if not api_base:
        logger.error("ai.provider.misconfigured missing_api_base")
        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message="OPENAI_BASE_URL/OPENAI_API_BASE 未配置。",
            detail="OPENAI_BASE_URL/OPENAI_API_BASE 未配置。",
        )
    if not model:
        logger.error("ai.provider.misconfigured missing_model")
        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message="AI_MODEL/OPENAI_MODEL 未配置。",
            detail="AI_MODEL/OPENAI_MODEL 未配置。",
        )
