from decimal import Decimal
from typing import Any

from sqlalchemy import DECIMAL, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class AIAnalysisResult(Base, TimestampMixin):
    __tablename__ = "ai_analysis_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False, index=True)
    analysis_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    result_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    applicable_laws: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    related_cases: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    strengths: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    weaknesses: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    recommendations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    ai_model: Mapped[str] = mapped_column(String(100), nullable=False)
    token_usage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost: Mapped[Decimal] = mapped_column(DECIMAL(10, 4), nullable=False, default=Decimal("0.0000"))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)

    case = relationship("Case")

