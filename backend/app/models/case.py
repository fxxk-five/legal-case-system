from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class Case(Base, TimestampMixin):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    case_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    assigned_lawyer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="new", index=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tenant = relationship("Tenant", back_populates="cases")
    client = relationship("User", back_populates="client_cases", foreign_keys=[client_id])
    assigned_lawyer = relationship(
        "User",
        back_populates="assigned_cases",
        foreign_keys=[assigned_lawyer_id],
    )
    files = relationship("File", back_populates="case")
