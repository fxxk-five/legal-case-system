from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "phone", name="uq_users_tenant_phone"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    is_tenant_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    wechat_openid: Mapped[str | None] = mapped_column(String(100), unique=True)
    real_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    tenant = relationship("Tenant", back_populates="users")
    assigned_cases = relationship(
        "Case",
        back_populates="assigned_lawyer",
        foreign_keys="Case.assigned_lawyer_id",
    )
    client_cases = relationship(
        "Case",
        back_populates="client",
        foreign_keys="Case.client_id",
    )
    uploaded_files = relationship("File", back_populates="uploader")
