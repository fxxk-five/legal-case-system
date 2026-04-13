from fastapi import Request
from sqlalchemy.orm import Session

from app.modules.audit.models.audit_log import AuditLog
from app.models.user import User


def log_audit(
    *,
    db: Session,
    user: User,
    action: str,
    resource_type: str,
    resource_id: int | None = None,
    detail: str | None = None,
    request: Request | None = None,
) -> None:
    client_ip = None
    request_id = None
    if request:
        client_ip = request.client.host if request.client else None
        request_id = getattr(request.state, "request_id", None)

    log = AuditLog(
        tenant_id=user.tenant_id,
        user_id=user.id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail,
        client_ip=client_ip,
        request_id=request_id,
    )
    db.add(log)
    db.commit()
