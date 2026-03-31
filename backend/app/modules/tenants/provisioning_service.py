from __future__ import annotations

import re
import secrets

from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.roles import normalize_role
from app.core.statuses import TenantStatus
from app.models.tenant import Tenant
from app.models.user import User
from app.modules.auth.schemas import UserRegister
from app.modules.auth.service import create_user, issue_session_bound_access_token
from app.modules.tenants.repository import TenantsRepository
from app.modules.tenants.schemas import TenantCreateOrganization, TenantCreatePersonal, TenantCreateResult


class TenantsProvisioningService:
    def __init__(self, db: Session, *, repository: TenantsRepository) -> None:
        self.db = db
        self.repository = repository

    @staticmethod
    def _normalize_tenant_code(raw_value: str | None, prefix: str) -> str:
        if raw_value:
            normalized = re.sub(r"[^a-zA-Z0-9]+", "-", raw_value.strip().lower()).strip("-")
            if len(normalized) >= 3:
                return normalized[:50]
        suffix = secrets.token_hex(3)
        return f"{prefix}-{suffix}"

    def _ensure_unique_tenant_code(self, *, candidate: str, prefix: str) -> str:
        current = candidate
        while self.repository.tenant_code_exists(tenant_code=current):
            current = self._normalize_tenant_code(None, prefix)
        return current

    def _build_create_result(self, *, tenant: Tenant, admin_user: User) -> TenantCreateResult:
        access_token = issue_session_bound_access_token(
            self.db,
            user=admin_user,
            channel="tenant_bootstrap",
        )
        return TenantCreateResult(
            tenant=tenant,
            access_token=access_token,
            user_id=admin_user.id,
        )

    def _ensure_admin_phone_available(self, *, phone: str) -> None:
        if self.repository.get_user_by_phone(phone=phone):
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                code=ErrorCode.USER_ALREADY_EXISTS,
                message="Phone number is already in use.",
                detail="Phone number is already in use.",
            )

    def _create_tenant_with_admin(
        self,
        *,
        tenant_code: str,
        tenant_name: str,
        tenant_type: str,
        admin_phone: str,
        admin_password: str,
        admin_real_name: str,
    ) -> TenantCreateResult:
        tenant = Tenant(
            tenant_code=tenant_code,
            name=tenant_name,
            type=tenant_type,
            status=int(TenantStatus.ACTIVE),
        )
        self.repository.save_and_refresh(tenant)

        admin_user = create_user(
            self.db,
            user_in=UserRegister(
                phone=admin_phone,
                password=admin_password,
                real_name=admin_real_name,
            ),
            tenant_id=tenant.id,
            role=normalize_role("tenant_admin"),
            is_tenant_admin=True,
        )
        return self._build_create_result(tenant=tenant, admin_user=admin_user)

    def create_personal_tenant(self, *, tenant_in: TenantCreatePersonal) -> TenantCreateResult:
        self._ensure_admin_phone_available(phone=tenant_in.admin_phone)
        tenant_code = self._ensure_unique_tenant_code(
            candidate=self._normalize_tenant_code(tenant_in.tenant_code or tenant_in.workspace_name, "personal"),
            prefix="personal",
        )
        return self._create_tenant_with_admin(
            tenant_code=tenant_code,
            tenant_name=tenant_in.workspace_name,
            tenant_type="personal",
            admin_phone=tenant_in.admin_phone,
            admin_password=tenant_in.admin_password,
            admin_real_name=tenant_in.admin_real_name,
        )

    def create_organization_tenant(self, *, tenant_in: TenantCreateOrganization) -> TenantCreateResult:
        self._ensure_admin_phone_available(phone=tenant_in.admin_phone)
        tenant_code = self._ensure_unique_tenant_code(
            candidate=self._normalize_tenant_code(tenant_in.tenant_code or tenant_in.name, "org"),
            prefix="org",
        )
        return self._create_tenant_with_admin(
            tenant_code=tenant_code,
            tenant_name=tenant_in.name,
            tenant_type="organization",
            admin_phone=tenant_in.admin_phone,
            admin_password=tenant_in.admin_password,
            admin_real_name=tenant_in.admin_real_name,
        )
