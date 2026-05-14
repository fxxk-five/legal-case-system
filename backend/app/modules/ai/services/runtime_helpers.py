from __future__ import annotations

import os
from typing import Any

from app.core.config import settings
from app.modules.ai.models.ai_task import AITask


_QUEUE_ATTEMPT_KEY = "__queue_attempt"


def get_queue_attempt(task: AITask) -> int:
    try:
        retry_count = int(task.retry_count or 0)
    except (TypeError, ValueError):
        retry_count = 0
    if retry_count > 0:
        return retry_count

    raw_attempt = (task.input_params or {}).get(_QUEUE_ATTEMPT_KEY)
    try:
        return int(raw_attempt or 0)
    except (TypeError, ValueError):
        return 0


def effective_worker_id(service: Any) -> str:
    configured = str(getattr(service, "worker_id", "") or settings.AI_DB_QUEUE_WORKER_ID or "").strip()
    if configured:
        return configured
    return os.getenv("HOSTNAME") or os.getenv("COMPUTERNAME") or "ai-worker"
