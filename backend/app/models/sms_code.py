from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class SmsCode(Base, TimestampMixin):
    __tablename__ = "sms_codes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    verify_fail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    verify_locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    verification_token: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    verification_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
