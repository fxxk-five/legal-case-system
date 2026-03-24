from __future__ import annotations

from enum import IntEnum


class TenantStatus(IntEnum):
    CREATED = 0
    ACTIVE = 1
    DISABLED = 2
    ARCHIVED = 3


class UserStatus(IntEnum):
    PENDING_APPROVAL = 0
    ACTIVE = 1
    DISABLED = 2
    REJECTED = 3


TENANT_ALLOWED_TRANSITIONS: dict[TenantStatus, set[TenantStatus]] = {
    TenantStatus.CREATED: {TenantStatus.ACTIVE},
    TenantStatus.ACTIVE: {TenantStatus.DISABLED, TenantStatus.ARCHIVED},
    TenantStatus.DISABLED: {TenantStatus.ACTIVE, TenantStatus.ARCHIVED},
    TenantStatus.ARCHIVED: set(),
}

USER_ALLOWED_TRANSITIONS: dict[UserStatus, set[UserStatus]] = {
    UserStatus.PENDING_APPROVAL: {UserStatus.ACTIVE, UserStatus.REJECTED},
    UserStatus.ACTIVE: {UserStatus.DISABLED},
    UserStatus.DISABLED: {UserStatus.ACTIVE},
    UserStatus.REJECTED: set(),
}


def is_active_tenant_status(status: int) -> bool:
    return int(status) == int(TenantStatus.ACTIVE)


def is_active_user_status(status: int) -> bool:
    return int(status) == int(UserStatus.ACTIVE)


def can_transition_tenant_status(current: int, target: int) -> bool:
    current_status = TenantStatus(int(current))
    target_status = TenantStatus(int(target))
    return target_status in TENANT_ALLOWED_TRANSITIONS[current_status]


def can_transition_user_status(current: int, target: int) -> bool:
    current_status = UserStatus(int(current))
    target_status = UserStatus(int(target))
    return target_status in USER_ALLOWED_TRANSITIONS[current_status]
