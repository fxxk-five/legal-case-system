from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_WECHAT_SERVICE_PATH = PROJECT_ROOT / "app" / "modules" / "auth" / "web_wechat_service.py"
ACCOUNT_SERVICE_PATH = PROJECT_ROOT / "app" / "modules" / "auth" / "account_service.py"
SESSION_SERVICE_PATH = PROJECT_ROOT / "app" / "modules" / "auth" / "session_service.py"
WECHAT_BINDING_SERVICE_PATH = (
    PROJECT_ROOT / "app" / "modules" / "auth" / "services" / "wechat_binding_service.py"
)
WECHAT_ACCOUNT_BINDING_SERVICE_PATH = (
    PROJECT_ROOT / "app" / "modules" / "auth" / "services" / "wechat_account_binding_service.py"
)


def test_web_wechat_service_does_not_use_raw_session_writes() -> None:
    violations: list[str] = []

    for lineno, line in enumerate(WEB_WECHAT_SERVICE_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "self.db." not in stripped:
            continue

        violations.append(f"{WEB_WECHAT_SERVICE_PATH.relative_to(PROJECT_ROOT)}:{lineno}: {stripped}")

    assert violations == [], "Web WeChat service still uses raw session operations:\n" + "\n".join(violations)


def test_account_service_does_not_use_raw_session_writes() -> None:
    violations: list[str] = []

    for lineno, line in enumerate(ACCOUNT_SERVICE_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "db.add(" in stripped or "db.commit(" in stripped or "db.refresh(" in stripped:
            violations.append(f"{ACCOUNT_SERVICE_PATH.relative_to(PROJECT_ROOT)}:{lineno}: {stripped}")

    assert violations == [], "Account service still uses raw session operations:\n" + "\n".join(violations)


def test_session_service_does_not_use_raw_session_writes() -> None:
    violations: list[str] = []

    for lineno, line in enumerate(SESSION_SERVICE_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "self.db.flush(" in stripped or "self.db.commit(" in stripped or "self.db.refresh(" in stripped:
            violations.append(f"{SESSION_SERVICE_PATH.relative_to(PROJECT_ROOT)}:{lineno}: {stripped}")

    assert violations == [], "Session service still uses raw session operations:\n" + "\n".join(violations)


def test_wechat_binding_service_does_not_use_raw_session_writes() -> None:
    violations: list[str] = []

    for lineno, line in enumerate(WECHAT_BINDING_SERVICE_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if (
            "self.db.add(" in stripped
            or "self.db.commit(" in stripped
            or "self.db.refresh(" in stripped
        ):
            violations.append(f"{WECHAT_BINDING_SERVICE_PATH.relative_to(PROJECT_ROOT)}:{lineno}: {stripped}")

    assert violations == [], "Wechat binding service still uses raw session operations:\n" + "\n".join(
        violations
    )


def test_wechat_binding_service_does_not_use_low_level_repository_transaction_calls() -> None:
    violations: list[str] = []

    for lineno, line in enumerate(WECHAT_BINDING_SERVICE_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "self.repository.commit(" in stripped or "self.repository.refresh(" in stripped:
            violations.append(f"{WECHAT_BINDING_SERVICE_PATH.relative_to(PROJECT_ROOT)}:{lineno}: {stripped}")

    assert violations == [], "Wechat binding service still uses low-level repository transaction calls:\n" + "\n".join(
        violations
    )


def test_wechat_account_binding_service_does_not_use_raw_session_writes() -> None:
    violations: list[str] = []

    for lineno, line in enumerate(
        WECHAT_ACCOUNT_BINDING_SERVICE_PATH.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if (
            "self.db.add(" in stripped
            or "self.db.commit(" in stripped
            or "self.db.refresh(" in stripped
        ):
            violations.append(
                f"{WECHAT_ACCOUNT_BINDING_SERVICE_PATH.relative_to(PROJECT_ROOT)}:{lineno}: {stripped}"
            )

    assert violations == [], "Wechat account binding service still uses raw session operations:\n" + "\n".join(
        violations
    )
