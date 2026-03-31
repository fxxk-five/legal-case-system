from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TENANTS_MODULE_ROOT = PROJECT_ROOT / "app" / "modules" / "tenants"
TARGET_FILES = (
    TENANTS_MODULE_ROOT / "service.py",
    TENANTS_MODULE_ROOT / "provisioning_service.py",
    TENANTS_MODULE_ROOT / "tenants_budget_service.py",
)


def test_tenants_services_do_not_use_raw_session_commit_or_refresh() -> None:
    violations: list[str] = []

    for target in TARGET_FILES:
        for lineno, line in enumerate(target.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "self.db.commit(" in stripped or "self.db.refresh(" in stripped:
                violations.append(f"{target.relative_to(PROJECT_ROOT)}:{lineno}: {stripped}")

    assert violations == [], "Tenants services still use raw session commit/refresh:\n" + "\n".join(violations)
