from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class CaseFlow(Base, TimestampMixin):
    __tablename__ = "case_flows"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False, index=True)
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    operator_name: Mapped[str | None] = mapped_column(String(100))
    action_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    visible_to: Mapped[str] = mapped_column(String(20), nullable=False, default="both", index=True)

    tenant = relationship("Tenant")
    case = relationship("Case", back_populates="flows")
    operator = relationship("User")
