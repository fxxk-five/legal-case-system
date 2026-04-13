from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.wechat_identity import (
    decrypt_wechat_identifier,
    encrypt_wechat_identifier,
    hash_wechat_identifier,
)
from app.db.base_class import Base
from app.db.mixins import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "phone", name="uq_users_tenant_phone"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    is_tenant_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    must_reset_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    _wechat_openid_ciphertext: Mapped[str | None] = mapped_column("wechat_openid_ciphertext", String(512))
    wechat_openid_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    _wechat_unionid_ciphertext: Mapped[str | None] = mapped_column("wechat_unionid_ciphertext", String(512))
    wechat_unionid_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
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

    @property
    def wechat_openid(self) -> str | None:
        return decrypt_wechat_identifier(self._wechat_openid_ciphertext, kind="openid")

    @wechat_openid.setter
    def wechat_openid(self, value: str | None) -> None:
        normalized = (value or "").strip() or None
        if normalized is None:
            self._wechat_openid_ciphertext = None
            self.wechat_openid_hash = None
            return
        self._wechat_openid_ciphertext = encrypt_wechat_identifier(normalized, kind="openid")
        self.wechat_openid_hash = hash_wechat_identifier(normalized, kind="openid")

    @property
    def wechat_unionid(self) -> str | None:
        return decrypt_wechat_identifier(self._wechat_unionid_ciphertext, kind="unionid")

    @wechat_unionid.setter
    def wechat_unionid(self, value: str | None) -> None:
        normalized = (value or "").strip() or None
        if normalized is None:
            self._wechat_unionid_ciphertext = None
            self.wechat_unionid_hash = None
            return
        self._wechat_unionid_ciphertext = encrypt_wechat_identifier(normalized, kind="unionid")
        self.wechat_unionid_hash = hash_wechat_identifier(normalized, kind="unionid")

