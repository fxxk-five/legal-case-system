from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class CaseNumberSequence(Base, TimestampMixin):
    __tablename__ = "case_number_sequences"
    __table_args__ = (
        UniqueConstraint("tenant_id", "year", name="uq_case_number_sequences_tenant_year"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    next_value: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    tenant = relationship("Tenant")
