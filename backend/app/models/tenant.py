from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, JSON, Numeric, String
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
    ai_monthly_budget_limit: Mapped[float | None] = mapped_column(Numeric(12, 2))
    ai_budget_degrade_model: Mapped[str | None] = mapped_column(String(100))
    ai_prompt_settings: Mapped[dict | None] = mapped_column(JSON, default=dict)
    ai_provider_settings: Mapped[dict | None] = mapped_column(JSON, default=dict)
    ai_provider_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    users = relationship("User", back_populates="tenant")
    cases = relationship("Case", back_populates="tenant")
    files = relationship("File", back_populates="tenant")
    invites = relationship("Invite", back_populates="tenant")
