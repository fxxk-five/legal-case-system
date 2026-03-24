from __future__ import annotations

import json
from urllib import error as url_error
from urllib import request as url_request

from fastapi import status

from app.core.config import settings
from app.core.errors import AppError, ErrorCode


class ReportService:
    def __init__(self) -> None:
        self.base_url = (settings.REPORT_SERVICE_BASE_URL or "").strip().rstrip("/")
        self.timeout_seconds = settings.REPORT_SERVICE_TIMEOUT_SECONDS

    def is_enabled(self) -> bool:
        return bool(self.base_url)

    def generate_case_report_pdf(self, payload: dict) -> bytes:
        if not self.is_enabled():
            raise AppError(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="REPORT_SERVICE_BASE_URL 未配置，无法生成报告。",
                detail="REPORT_SERVICE_BASE_URL 未配置，无法生成报告。",
            )

        endpoint = f"{self.base_url}/api/v1/reports/render"
        request_payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = url_request.Request(
            endpoint,
            data=request_payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with url_request.urlopen(req, timeout=self.timeout_seconds) as resp:
                content_type = (resp.headers.get("Content-Type") or "").lower()
                body = resp.read()
                if resp.status != status.HTTP_200_OK:
                    raise AppError(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                        message="报告服务返回异常状态。",
                        detail=f"报告服务状态码: {resp.status}",
                    )
                if "application/pdf" not in content_type:
                    raise AppError(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                        message="报告服务返回格式异常。",
                        detail=f"报告服务返回 Content-Type: {content_type}",
                    )
                return body
        except AppError:
            raise
        except url_error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise AppError(
                status_code=status.HTTP_502_BAD_GATEWAY,
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="报告服务调用失败。",
                detail=detail or f"HTTP {exc.code}",
            ) from exc
        except url_error.URLError as exc:
            raise AppError(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="报告服务连接超时或不可达。",
                detail=str(exc),
            ) from exc
