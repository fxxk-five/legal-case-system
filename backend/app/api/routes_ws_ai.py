from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from app.core.config import settings
from app.core.roles import normalize_role
from app.db.session import SessionLocal
from app.models.ai_task import AITask
from app.models.case import Case
from app.models.user import User


router = APIRouter(tags=["AI-WebSocket"])


def _get_session_factory(websocket: WebSocket):
    return getattr(websocket.app.state, "session_factory", SessionLocal)


def _failed_payload(*, task_id: str, error: str) -> dict:
    return {
        "type": "failed",
        "task_id": task_id,
        "progress": 0,
        "error": error,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def _close_with_error(*, websocket: WebSocket, task_id: str, error: str, close_code: int) -> None:
    await websocket.send_json(_failed_payload(task_id=task_id, error=error))
    await websocket.close(code=close_code)


async def _client_disconnected(websocket: WebSocket) -> bool:
    try:
        await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
        return False
    except asyncio.TimeoutError:
        return False
    except WebSocketDisconnect:
        return True
    except RuntimeError:
        return True


def _client_owns_task_case(*, db, tenant_id: int, user_id: int, task: AITask) -> bool:
    return (
        db.query(Case.id)
        .filter(
            Case.id == task.case_id,
            Case.tenant_id == tenant_id,
            Case.client_id == user_id,
        )
        .first()
        is not None
    )


@router.websocket("/ws/ai/tasks/{task_id}")
async def ai_task_progress(websocket: WebSocket, task_id: str) -> None:
    await websocket.accept()
    session_factory = _get_session_factory(websocket)

    token = websocket.query_params.get("token")
    if not token:
        await _close_with_error(
            websocket=websocket,
            task_id=task_id,
            error="Missing auth token.",
            close_code=4401,
        )
        return

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        await _close_with_error(
            websocket=websocket,
            task_id=task_id,
            error="Authentication failed: invalid token.",
            close_code=4401,
        )
        return

    user_id_raw = payload.get("sub")
    tenant_id_raw = payload.get("tenant_id")

    try:
        user_id = int(user_id_raw)
        tenant_id = int(tenant_id_raw)
    except (TypeError, ValueError):
        await _close_with_error(
            websocket=websocket,
            task_id=task_id,
            error="Authentication failed: token payload is invalid.",
            close_code=4401,
        )
        return

    with session_factory() as db:
        user = (
            db.query(User)
            .filter(
                User.id == user_id,
                User.tenant_id == tenant_id,
            )
            .first()
        )
        if user is None or user.status != 1:
            await _close_with_error(
                websocket=websocket,
                task_id=task_id,
                error="Authentication failed: user is unavailable.",
                close_code=4401,
            )
            return

        viewer_role = normalize_role(user.role)

        task = (
            db.query(AITask)
            .filter(
                AITask.task_id == task_id,
                AITask.tenant_id == tenant_id,
            )
            .first()
        )
        if task is None:
            await _close_with_error(
                websocket=websocket,
                task_id=task_id,
                error="AI task not found or access denied.",
                close_code=4404,
            )
            return

        if viewer_role == "client" and not _client_owns_task_case(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            task=task,
        ):
            await _close_with_error(
                websocket=websocket,
                task_id=task_id,
                error="AI task not found or access denied.",
                close_code=4403,
            )
            return

    since_raw = websocket.query_params.get("since")
    since: datetime | None = None
    if since_raw:
        try:
            since = datetime.fromisoformat(since_raw.replace("Z", "+00:00"))
        except ValueError:
            since = None

    last_status: str | None = None
    last_progress: int | None = None

    try:
        while True:
            if await _client_disconnected(websocket):
                break

            with session_factory() as db:
                task = (
                    db.query(AITask)
                    .filter(
                        AITask.task_id == task_id,
                        AITask.tenant_id == tenant_id,
                    )
                    .first()
                )

                if task is None:
                    await websocket.send_json(
                        _failed_payload(task_id=task_id, error="AI task not found or access denied.")
                    )
                    break

                if viewer_role == "client" and not _client_owns_task_case(
                    db=db,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    task=task,
                ):
                    await websocket.send_json(
                        _failed_payload(task_id=task_id, error="AI task not found or access denied.")
                    )
                    break

                should_send = task.status != last_status or task.progress != last_progress
                latest_event_at = task.completed_at or task.started_at or task.updated_at or task.created_at
                if since is not None and latest_event_at is not None:
                    should_send = should_send or latest_event_at >= since

                if should_send:
                    payload = {
                        "type": "progress",
                        "task_id": task.task_id,
                        "progress": task.progress,
                        "message": task.message,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "error": None,
                    }
                    if task.status == "completed":
                        payload["type"] = "completed"
                    elif task.status == "failed":
                        payload["type"] = "failed"
                        payload["error"] = task.error_message or "AI task execution failed."
                    await websocket.send_json(payload)
                    last_status = task.status
                    last_progress = task.progress
                    since = None

                if task.status in {"completed", "failed"}:
                    break

            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            pass
