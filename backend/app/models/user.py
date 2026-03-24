from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
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
    wechat_unionid: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)
    wechat_bound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    wechat_phone_snapshot: Mapped[str | None] = mapped_column(String(20))
    real_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    previous_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_channel: Mapped[str | None] = mapped_column(String(30), index=True)

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
    sent_invites = relationship("Invite", back_populates="invited_by")
    notifications = relationship("Notification", back_populates="user")
    auth_sessions = relationship("AuthSession", back_populates="user", cascade="all, delete-orphan")
