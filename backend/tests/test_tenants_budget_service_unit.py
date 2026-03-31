from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.errors import AppError, ErrorCode
from app.modules.tenants.tenants_budget_service import TenantsBudgetService
from app.modules.tenants.schemas import CaseAIBudgetUpdate, TenantAIBudgetUpdate


class _FakeDB:
    def __init__(self) -> None:
        self.commit_count = 0
        self.refreshed: list[object] = []

    def commit(self) -> None:
        self.commit_count += 1

    def refresh(self, obj: object) -> None:
        self.refreshed.append(obj)


class _FakeRepo:
    def __init__(self, db: _FakeDB) -> None:
        self.db = db
        self.saved: list[object] = []
        self.cases: dict[tuple[int, int], object] = {}

    def save(self, obj: object) -> None:
        self.saved.append(obj)

    def save_and_refresh(self, obj: object) -> None:
        self.save(obj)
        self.db.commit()
        self.db.refresh(obj)

    def get_case(self, *, case_id: int, tenant_id: int):
        return self.cases.get((tenant_id, case_id))


def _to_float_or_none(value):
    return float(value) if value is not None else None


def test_get_tenant_ai_budget_returns_current_values():
    fake_db = _FakeDB()
    fake_repo = _FakeRepo(fake_db)
    tenant = SimpleNamespace(
        id=3,
        ai_monthly_budget_limit=123.45,
        ai_budget_degrade_model="gpt-4o-mini",
    )

    service = TenantsBudgetService(
        fake_db,
        repository=fake_repo,
        get_tenant_or_404=lambda **_: tenant,
        to_float_or_none=_to_float_or_none,
    )

    result = service.get_tenant_ai_budget(tenant_id=tenant.id)

    assert result.tenant_id == 3
    assert result.ai_monthly_budget_limit == 123.45
    assert result.ai_budget_degrade_model == "gpt-4o-mini"


def test_update_tenant_ai_budget_clear_values_and_persist():
    fake_db = _FakeDB()
    fake_repo = _FakeRepo(fake_db)
    tenant = SimpleNamespace(
        id=8,
        ai_monthly_budget_limit=999.0,
        ai_budget_degrade_model="legacy-model",
    )
    payload = TenantAIBudgetUpdate(
        clear_monthly_budget_limit=True,
        clear_budget_degrade_model=True,
    )

    service = TenantsBudgetService(
        fake_db,
        repository=fake_repo,
        get_tenant_or_404=lambda **_: tenant,
        to_float_or_none=_to_float_or_none,
    )

    result = service.update_tenant_ai_budget(tenant_id=tenant.id, payload=payload)

    assert tenant.ai_monthly_budget_limit is None
    assert tenant.ai_budget_degrade_model is None
    assert fake_db.commit_count == 1
    assert fake_db.refreshed == [tenant]
    assert fake_repo.saved == [tenant]
    assert result.ai_monthly_budget_limit is None
    assert result.ai_budget_degrade_model is None


def test_get_case_ai_budget_missing_case_raises_not_found():
    fake_db = _FakeDB()
    fake_repo = _FakeRepo(fake_db)
    service = TenantsBudgetService(
        fake_db,
        repository=fake_repo,
        get_tenant_or_404=lambda **_: None,
        to_float_or_none=_to_float_or_none,
    )

    with pytest.raises(AppError) as exc_info:
        service.get_case_ai_budget(tenant_id=1, case_id=404)

    assert exc_info.value.code == ErrorCode.CASE_NOT_FOUND


def test_update_case_ai_budget_updates_limit_and_persists():
    fake_db = _FakeDB()
    fake_repo = _FakeRepo(fake_db)
    case = SimpleNamespace(
        id=11,
        tenant_id=2,
        ai_case_budget_limit=20.0,
    )
    fake_repo.cases[(2, 11)] = case
    payload = CaseAIBudgetUpdate(ai_case_budget_limit=66.6)

    service = TenantsBudgetService(
        fake_db,
        repository=fake_repo,
        get_tenant_or_404=lambda **_: None,
        to_float_or_none=_to_float_or_none,
    )

    result = service.update_case_ai_budget(tenant_id=2, case_id=11, payload=payload)

    assert case.ai_case_budget_limit == 66.6
    assert fake_db.commit_count == 1
    assert fake_db.refreshed == [case]
    assert fake_repo.saved == [case]
    assert result.case_id == 11
    assert result.tenant_id == 2
    assert result.ai_case_budget_limit == 66.6

