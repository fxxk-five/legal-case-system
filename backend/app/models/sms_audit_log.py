from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.db.mixins import TimestampMixin


class SmsAuditLog(Base, TimestampMixin):
    __tablename__ = "sms_audit_logs"
    __table_args__ = (
        Index(
            "ix_sms_audit_logs_action_client_ip_created_at",
            "action",
            "client_ip",
            "created_at",
        ),
        Index(
            "ix_sms_audit_logs_action_device_fingerprint_created_at",
            "action",
            "device_fingerprint",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    result: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    client_ip: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    device_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    detail: Mapped[str | None] = mapped_column(String(255), nullable=True)

