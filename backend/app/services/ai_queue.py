from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Literal

from fastapi import status

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.models.ai_task import AITask


logger = logging.getLogger("app.ai.queue")
QueueDriver = Literal["db", "tdmq", "cmq"]


@dataclass(slots=True)
class AIQueueMessage:
    task_id: str
    tenant_id: int
    case_id: int
    task_type: str
    created_by: int | None
    request_id: str | None
    queued_at: str
    retry_count: int

    @classmethod
    def from_task(cls, *, task: AITask, request_id: str | None) -> "AIQueueMessage":
        return cls(
            task_id=task.task_id,
            tenant_id=task.tenant_id,
            case_id=task.case_id,
            task_type=task.task_type,
            created_by=task.created_by,
            request_id=request_id or task.request_id,
            queued_at=datetime.now(timezone.utc).isoformat(),
            retry_count=int(task.retry_count or 0),
        )

    def to_payload(self) -> dict[str, object]:
        return asdict(self)


class BaseAIQueueAdapter:
    driver_name: str

    def enqueue(self, *, task: AITask, request_id: str | None) -> AIQueueMessage:
        raise NotImplementedError


class DBQueueAdapter(BaseAIQueueAdapter):
    driver_name = "db"

    def enqueue(self, *, task: AITask, request_id: str | None) -> AIQueueMessage:
        message = AIQueueMessage.from_task(task=task, request_id=request_id)
        logger.info(
            "ai.queue.enqueue driver=db task_id=%s case_id=%s request_id=%s",
            task.task_id,
            task.case_id,
            request_id,
        )
        return message


class TencentCloudQueueAdapter(BaseAIQueueAdapter):
    def __init__(self, *, driver_name: str) -> None:
        self.driver_name = driver_name

    def enqueue(self, *, task: AITask, request_id: str | None) -> AIQueueMessage:
        message = AIQueueMessage.from_task(task=task, request_id=request_id)
        detail = {
            "driver": self.driver_name,
            "region": settings.TENCENT_QUEUE_REGION.strip(),
            "namespace": settings.TENCENT_QUEUE_NAMESPACE.strip(),
            "topic_name": settings.TENCENT_QUEUE_TOPIC_NAME.strip(),
            "subscription_name": settings.TENCENT_QUEUE_SUBSCRIPTION_NAME.strip(),
            "endpoint": settings.TENCENT_QUEUE_ENDPOINT.strip(),
        }
        missing = [
            key
            for key, value in {
                "TENCENT_QUEUE_REGION": settings.TENCENT_QUEUE_REGION,
                "TENCENT_QUEUE_NAMESPACE": settings.TENCENT_QUEUE_NAMESPACE,
                "TENCENT_QUEUE_TOPIC_NAME": settings.TENCENT_QUEUE_TOPIC_NAME,
                "TENCENT_QUEUE_SUBSCRIPTION_NAME": settings.TENCENT_QUEUE_SUBSCRIPTION_NAME,
                "TENCENT_QUEUE_SECRET_ID": settings.TENCENT_QUEUE_SECRET_ID,
                "TENCENT_QUEUE_SECRET_KEY": settings.TENCENT_QUEUE_SECRET_KEY,
            }.items()
            if not str(value or "").strip()
        ]
        if missing:
            detail["missing"] = missing
            raise AppError(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="云队列适配器未完成运行配置，无法启用 `TDMQ/CMQ`。",
                detail=detail,
            )

        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message="当前仓库已提供 `TDMQ/CMQ` 适配边界，但真实腾讯云消息收发仍需接入官方 SDK/HTTP 客户端后再启用。",
            detail={**detail, "payload": message.to_payload()},
        )


def normalize_queue_driver(driver: str | None = None) -> QueueDriver:
    normalized = str(driver or settings.QUEUE_DRIVER or "db").strip().lower()
    if normalized in {"db", "tdmq", "cmq"}:
        return normalized
    raise AppError(
        status_code=status.HTTP_400_BAD_REQUEST,
        code=ErrorCode.VALIDATION_ERROR,
        message="不支持的队列驱动。",
        detail={"queue_driver": normalized},
    )


def get_ai_queue_adapter(driver: str | None = None) -> BaseAIQueueAdapter:
    normalized = normalize_queue_driver(driver)
    if normalized == "db":
        return DBQueueAdapter()
    return TencentCloudQueueAdapter(driver_name=normalized)
