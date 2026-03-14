from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tenant_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False, default="organization")
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    subscription_expire_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    balance: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    users = relationship("User", back_populates="tenant")
    cases = relationship("Case", back_populates="tenant")
    files = relationship("File", back_populates="tenant")
    invites = relationship("Invite", back_populates="tenant")
