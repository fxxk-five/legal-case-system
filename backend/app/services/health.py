from __future__ import annotations

from pathlib import Path
from typing import Callable

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal

SessionFactory = Callable[[], Session]


def _check_database(session_factory: SessionFactory | None = None) -> tuple[str, str | None]:
    factory = session_factory or SessionLocal
    db = factory()
    try:
        db.execute(text("SELECT 1"))
        return "ok", None
    except Exception as exc:  # pragma: no cover - branch covered via patched readiness payload in tests
        return "error", str(exc.__class__.__name__)
    finally:
        db.close()


def _check_local_storage() -> tuple[str, str | None]:
    try:
        storage_dir = Path(settings.LOCAL_STORAGE_DIR)
        storage_dir.mkdir(parents=True, exist_ok=True)
        probe_file = storage_dir / ".healthcheck_probe"
        probe_file.write_text("ok", encoding="utf-8")
        probe_file.unlink(missing_ok=True)
        return "ok", None
    except Exception as exc:  # pragma: no cover - depends on filesystem permission failures
        return "error", str(exc.__class__.__name__)


def _check_cos_storage() -> tuple[str, str | None]:
    try:
        from app.services.storage import get_storage_backend

        backend = get_storage_backend()
        if getattr(backend, "backend_name", "") != "cos":
            return "error", "InvalidStorageBackend"
        backend._get_client()
        return "ok", None
    except Exception as exc:  # pragma: no cover - depends on runtime config and SDK presence
        return "error", str(exc.__class__.__name__)


def build_liveness_payload() -> dict:
    return {
        "status": "alive",
        "service": "backend",
        "version": settings.VERSION,
    }


def build_readiness_payload(session_factory: SessionFactory | None = None) -> tuple[dict, bool]:
    checks: dict[str, str] = {}
    details: dict[str, str] = {}

    database_status, database_detail = _check_database(session_factory=session_factory)
    checks["database"] = database_status
    if database_detail:
        details["database"] = database_detail

    if settings.STORAGE_BACKEND == "local":
        storage_status, storage_detail = _check_local_storage()
        checks["storage"] = storage_status
        if storage_detail:
            details["storage"] = storage_detail
    elif settings.STORAGE_BACKEND == "cos":
        storage_status, storage_detail = _check_cos_storage()
        checks["storage"] = storage_status
        if storage_detail:
            details["storage"] = storage_detail

    required_statuses = [status for name, status in checks.items() if name in {"database", "storage"}]
    is_ready = all(status == "ok" for status in required_statuses)

    payload: dict = {
        "status": "ready" if is_ready else "not_ready",
        "service": "backend",
        "version": settings.VERSION,
        "checks": checks,
    }
    if details:
        payload["details"] = details
    return payload, is_ready
