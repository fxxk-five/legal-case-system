from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import time
from uuid import uuid4

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.ai_queue import normalize_queue_driver
from app.services.ai import AIService


logger = logging.getLogger("app.ai.worker")


def _default_worker_id() -> str:
    configured = str(settings.AI_DB_QUEUE_WORKER_ID or "").strip()
    if configured:
        return configured
    return "ai-worker"


def write_heartbeat(
    *,
    heartbeat_file: Path,
    worker_id: str,
    consumed_total: int,
    status: str,
) -> None:
    payload = {
        "worker_id": worker_id,
        "status": status,
        "consumed_total": consumed_total,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    heartbeat_file.parent.mkdir(parents=True, exist_ok=True)
    heartbeat_file.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")


def is_heartbeat_fresh(*, heartbeat_file: Path, max_age_seconds: int) -> bool:
    if not heartbeat_file.exists():
        return False
    try:
        payload = json.loads(heartbeat_file.read_text(encoding="utf-8"))
        updated_at_raw = str(payload.get("updated_at") or "").strip()
        if not updated_at_raw:
            return False
        updated_at = datetime.fromisoformat(updated_at_raw)
    except Exception:  # noqa: BLE001
        return False

    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    age_seconds = (datetime.now(timezone.utc) - updated_at.astimezone(timezone.utc)).total_seconds()
    return age_seconds <= max(1, max_age_seconds)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run DB queue worker for AI tasks.")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Consume at most one batch and exit.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1,
        help="How many tasks to consume per loop iteration.",
    )
    parser.add_argument(
        "--max-tasks",
        type=int,
        default=0,
        help="Stop after this many consumed tasks (0 means unlimited).",
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=settings.AI_DB_QUEUE_POLL_SECONDS,
        help="Sleep seconds when no task is available.",
    )
    parser.add_argument(
        "--worker-id",
        default=_default_worker_id(),
        help="Logical worker identifier written into queue claims and heartbeat state.",
    )
    parser.add_argument(
        "--heartbeat-file",
        default=settings.AI_DB_QUEUE_HEARTBEAT_FILE,
        help="Heartbeat state file used by container health checks.",
    )
    parser.add_argument(
        "--healthcheck",
        action="store_true",
        help="Validate the worker heartbeat file and exit with 0/1.",
    )
    parser.add_argument(
        "--healthcheck-max-age-seconds",
        type=int,
        default=settings.AI_DB_QUEUE_HEALTHCHECK_MAX_AGE_SECONDS,
        help="Maximum accepted heartbeat age for health checks.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    heartbeat_file = Path(args.heartbeat_file)

    if args.healthcheck:
        is_fresh = is_heartbeat_fresh(
            heartbeat_file=heartbeat_file,
            max_age_seconds=args.healthcheck_max_age_seconds,
        )
        return 0 if is_fresh else 1

    request_id = f"ai-worker-{uuid4()}"
    consumed_total = 0
    batch_size = max(1, args.batch_size)
    max_tasks = max(0, args.max_tasks)
    poll_seconds = max(0.1, args.poll_seconds)
    worker_id = str(args.worker_id).strip() or _default_worker_id()
    queue_driver = normalize_queue_driver()

    if queue_driver != "db":
        logger.error(
            "ai.worker.unsupported_driver driver=%s message=%s",
            queue_driver,
            "Current worker script only consumes DB queue. Cloud queue transport requires a dedicated consumer.",
        )
        return 2

    write_heartbeat(
        heartbeat_file=heartbeat_file,
        worker_id=worker_id,
        consumed_total=consumed_total,
        status="starting",
    )

    while True:
        consumed = AIService.consume_queued_tasks_once(
            session_factory=SessionLocal,
            request_id=request_id,
            max_tasks=batch_size,
            worker_id=worker_id,
        )
        consumed_total += consumed
        write_heartbeat(
            heartbeat_file=heartbeat_file,
            worker_id=worker_id,
            consumed_total=consumed_total,
            status="working" if consumed else "idle",
        )

        if args.once:
            break
        if max_tasks and consumed_total >= max_tasks:
            break
        if consumed == 0:
            time.sleep(poll_seconds)

    write_heartbeat(
        heartbeat_file=heartbeat_file,
        worker_id=worker_id,
        consumed_total=consumed_total,
        status="stopped",
    )
    logger.info(
        "ai.worker.exit consumed_total=%s request_id=%s worker_id=%s",
        consumed_total,
        request_id,
        worker_id,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
