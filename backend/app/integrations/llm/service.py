from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib import error as url_error
from urllib import request as url_request

from fastapi import status

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.integrations.llm.payload_utils import (
    ensure_provider_configured,
    extract_provider_error,
    parse_json_payload,
    summarize_provider_error,
    summarize_provider_payload,
)


logger = logging.getLogger("app.ai.provider")


@dataclass(slots=True)
class ProviderReply:
    payload: dict[str, Any]
    model: str
    token_usage: int


class OpenAICompatibleProvider:
    def __init__(self) -> None:
        self.api_base = settings.EFFECTIVE_OPENAI_BASE_URL.rstrip("/")
        self.api_key = settings.OPENAI_API_KEY.strip()
        self.model = settings.EFFECTIVE_AI_MODEL
        self.timeout_seconds = settings.OPENAI_TIMEOUT_SECONDS

    def _ensure_provider_ready(self) -> None:
        ensure_provider_configured(
            api_key=self.api_key,
            api_base=self.api_base,
            model=self.model,
            logger=logger,
        )

    def generate_parse_facts(
        self,
        *,
        case_number: str,
        case_title: str,
        file_name: str,
        file_type: str,
        parse_options: dict,
        case_context: dict[str, Any] | None = None,
        model_override: str | None = None,
    ) -> ProviderReply:
        self._ensure_provider_ready()

        system_prompt = (
            "你是法律案件事实提取助手。必须仅返回 JSON。"
            "不要返回 markdown，不要返回解释性文本。"
        )
        user_prompt = json.dumps(
            {
                "task": "generate_case_facts_from_metadata",
                "case_number": case_number,
                "case_title": case_title,
                "file_name": file_name,
                "file_type": file_type,
                "parse_options": parse_options,
                "case_context": case_context or {},
                "output_schema": {
                    "facts": [
                        {
                            "fact_type": "party|timeline|evidence|law_reference",
                            "content": "string",
                            "source_page": 1,
                            "confidence": 0.9,
                            "metadata": {
                                "date": datetime.now(timezone.utc).isoformat(),
                                "law_name": "optional",
                                "article": "optional",
                            },
                        }
                    ]
                },
                "constraints": [
                    "facts length between 2 and 8",
                    "confidence range 0.5~0.99",
                    "content concise and business-safe",
                    "case_context remarks may supplement missing factual background",
                ],
            },
            ensure_ascii=False,
        )

        return self._chat_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            model_override=model_override,
        )

    def generate_analysis(
        self,
        *,
        case_title: str,
        analysis_type: str,
        fact_texts: list[str],
        focus_areas: list[str],
        include_precedents: bool,
        case_context: dict[str, Any] | None = None,
        model_override: str | None = None,
    ) -> ProviderReply:
        self._ensure_provider_ready()

        system_prompt = "你是资深法律分析助手。必须仅返回 JSON。"
        user_prompt = json.dumps(
            {
                "task": "legal_analysis",
                "case_title": case_title,
                "analysis_type": analysis_type,
                "fact_texts": fact_texts[:60],
                "focus_areas": focus_areas,
                "include_precedents": include_precedents,
                "case_context": case_context or {},
                "output_schema": {
                    "summary": "string",
                    "win_rate": 0.68,
                    "strengths": ["string"],
                    "weaknesses": ["string"],
                    "recommendations": ["string"],
                    "applicable_laws": ["string"],
                    "related_cases": ["string"],
                },
                "constraints": [
                    "win_rate range 0~1",
                    "strengths/weaknesses/recommendations each 2~5 items",
                    "when case_context contains remarks, incorporate them into reasoning priorities",
                ],
            },
            ensure_ascii=False,
        )

        return self._chat_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            model_override=model_override,
        )

    def generate_falsification(
        self,
        *,
        case_title: str,
        analysis_summary: str,
        challenge_mode: str,
        iteration: int,
        model_override: str | None = None,
    ) -> ProviderReply:
        self._ensure_provider_ready()

        system_prompt = "你是法律论证证伪助手。必须仅返回 JSON。"
        user_prompt = json.dumps(
            {
                "task": "falsification",
                "case_title": case_title,
                "analysis_summary": analysis_summary,
                "challenge_mode": challenge_mode,
                "iteration": iteration,
                "output_schema": {
                    "challenge_question": "string",
                    "response": "string",
                    "is_falsified": False,
                    "severity": "critical|major|minor",
                    "improvement_suggestion": "string",
                },
            },
            ensure_ascii=False,
        )

        return self._chat_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.4,
            model_override=model_override,
        )

    def _chat_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        model_override: str | None = None,
    ) -> ProviderReply:
        endpoint = f"{self.api_base}/chat/completions"
        resolved_model = (model_override or self.model).strip()
        payload = {
            "model": resolved_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": settings.OPENAI_MAX_TOKENS,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        req = url_request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with url_request.urlopen(req, timeout=self.timeout_seconds) as resp:
                resp_body = resp.read().decode("utf-8")
                raw = json.loads(resp_body)
        except url_error.HTTPError as exc:
            raw_error = exc.read().decode("utf-8", errors="ignore")
            detail = extract_provider_error(raw_error)
            logger.error(
                "ai.provider.http_error status=%s body_length=%s summary=%s",
                exc.code,
                len(raw_error),
                summarize_provider_error(raw_error),
            )
            raise AppError(
                status_code=status.HTTP_502_BAD_GATEWAY,
                code=ErrorCode.AI_PROVIDER_ERROR,
                message=f"AI服务调用失败：{detail}",
                detail=detail,
            ) from exc
        except url_error.URLError as exc:
            logger.error("ai.provider.network_error error=%s", exc)
            raise AppError(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="AI服务连接超时或网络不可达。",
                detail=str(exc),
            ) from exc
        except Exception as exc:  # noqa: BLE001
            logger.exception("ai.provider.unknown_error")
            raise AppError(
                status_code=status.HTTP_502_BAD_GATEWAY,
                code=ErrorCode.AI_PROVIDER_ERROR,
                message="AI服务返回异常。",
                detail=str(exc),
            ) from exc

        try:
            content = raw["choices"][0]["message"]["content"]
            parsed = parse_json_payload(content)
            model = str(raw.get("model") or resolved_model)
            usage = int((raw.get("usage") or {}).get("total_tokens") or 0)
            return ProviderReply(payload=parsed, model=model, token_usage=usage)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "ai.provider.invalid_response summary=%s error=%s",
                summarize_provider_payload(raw),
                type(exc).__name__,
            )
            raise AppError(
                status_code=status.HTTP_502_BAD_GATEWAY,
                code=ErrorCode.AI_PROVIDER_ERROR,
                message="AI服务返回内容无法解析。",
                detail=str(exc),
            ) from exc
