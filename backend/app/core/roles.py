from __future__ import annotations

ROLE_SUPER_ADMIN = "super_admin"
ROLE_TENANT_ADMIN = "tenant_admin"
ROLE_LAWYER = "lawyer"
ROLE_CLIENT = "client"

ROLE_ORG_LAWYER = "org_lawyer"
ROLE_SOLO_LAWYER = "solo_lawyer"

ROLE_ALIASES: dict[str, str] = {
    ROLE_ORG_LAWYER: ROLE_LAWYER,
    ROLE_SOLO_LAWYER: ROLE_LAWYER,
}

ALLOWED_ROLES: set[str] = {
    ROLE_SUPER_ADMIN,
    ROLE_TENANT_ADMIN,
    ROLE_LAWYER,
    ROLE_CLIENT,
    ROLE_ORG_LAWYER,
    ROLE_SOLO_LAWYER,
}


def normalize_role(role: str) -> str:
    normalized = (role or "").strip().lower()
    normalized = ROLE_ALIASES.get(normalized, normalized)
    return normalized


def is_super_admin_role(role: str) -> bool:
    return normalize_role(role) == ROLE_SUPER_ADMIN


def is_tenant_admin_role(role: str, *, is_tenant_admin: bool = False) -> bool:
    return is_tenant_admin or normalize_role(role) == ROLE_TENANT_ADMIN


def can_manage_case_role(role: str) -> bool:
    return normalize_role(role) in {ROLE_LAWYER, ROLE_TENANT_ADMIN}


def can_manage_lawyer_role(role: str) -> bool:
    return normalize_role(role) == ROLE_TENANT_ADMIN
