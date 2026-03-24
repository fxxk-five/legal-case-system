from collections.abc import Generator
import logging

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


logger = logging.getLogger("app.db.session")


engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

_TENANT_CONTEXT_KEY = "tenant_context_tenant_id"
_SUPER_ADMIN_CONTEXT_KEY = "tenant_context_is_super_admin"


def _apply_tenant_context(
    connection,
    *,
    tenant_id: int,
    is_super_admin: bool,
) -> None:
    if connection.dialect.name != "postgresql":
        return
    connection.execute(
        text("SELECT set_config('app.current_tenant', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )
    connection.execute(
        text("SELECT set_config('app.is_super_admin', :is_super_admin, true)"),
        {"is_super_admin": "1" if is_super_admin else "0"},
    )


@event.listens_for(SessionLocal, "after_begin")
def _reapply_tenant_context(session: Session, transaction, connection) -> None:
    _ = transaction
    tenant_id = session.info.get(_TENANT_CONTEXT_KEY)
    if tenant_id is None:
        return
    _apply_tenant_context(
        connection,
        tenant_id=int(tenant_id),
        is_super_admin=bool(session.info.get(_SUPER_ADMIN_CONTEXT_KEY, False)),
    )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def set_current_tenant_context(db: Session, tenant_id: int, *, is_super_admin: bool = False) -> None:
    db.info[_TENANT_CONTEXT_KEY] = int(tenant_id)
    db.info[_SUPER_ADMIN_CONTEXT_KEY] = bool(is_super_admin)
    bind = db.get_bind()
    if bind is None:
        return
    if bind.dialect.name != "postgresql":
        logger.debug("tenant context skipped for non-PostgreSQL dialect: %s", bind.dialect.name)
        return
    _apply_tenant_context(
        db.connection(),
        tenant_id=int(tenant_id),
        is_super_admin=bool(is_super_admin),
    )
