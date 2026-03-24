from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class FalsificationRecord(Base, TimestampMixin):
    __tablename__ = "falsification_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False, index=True)
    analysis_id: Mapped[int | None] = mapped_column(ForeignKey("ai_analysis_results.id"), index=True)
    challenge_type: Mapped[str] = mapped_column(String(50), nullable=False)
    challenge_question: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    is_falsified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    improvement_suggestion: Mapped[str | None] = mapped_column(Text)
    iteration: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    ai_model: Mapped[str] = mapped_column(String(100), nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)

    case = relationship("Case")
    analysis = relationship("AIAnalysisResult")

