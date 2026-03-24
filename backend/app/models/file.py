from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class File(Base, TimestampMixin):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), index=True)
    uploader_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    uploader_role: Mapped[str] = mapped_column(String(20), nullable=False, default="lawyer", index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    parse_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", index=True)

    tenant = relationship("Tenant", back_populates="files")
    case = relationship("Case", back_populates="files")
    uploader = relationship("User", back_populates="uploaded_files")

    @property
    def download_url(self) -> str:
        return f"/api/v1/files/{self.id}/access-link"
