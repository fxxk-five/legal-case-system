from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class Case(Base, TimestampMixin):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    case_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    legal_type: Mapped[str] = mapped_column(String(50), nullable=False, default="other", index=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    assigned_lawyer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="new", index=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    analysis_status: Mapped[str] = mapped_column(String(30), nullable=False, default="not_started", index=True)
    analysis_progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ai_case_budget_limit: Mapped[float | None] = mapped_column(Numeric(12, 2))

    tenant = relationship("Tenant", back_populates="cases")
    client = relationship("User", back_populates="client_cases", foreign_keys=[client_id])
    assigned_lawyer = relationship(
        "User",
        back_populates="assigned_cases",
        foreign_keys=[assigned_lawyer_id],
    )
    files = relationship("File", back_populates="case")
    flows = relationship("CaseFlow", back_populates="case", cascade="all, delete-orphan")
