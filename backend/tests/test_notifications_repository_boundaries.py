from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTIFICATIONS_SERVICE_PATH = PROJECT_ROOT / "app" / "modules" / "notifications" / "service.py"


def test_notifications_service_does_not_use_raw_session_commit_or_refresh() -> None:
    violations: list[str] = []

    for lineno, line in enumerate(NOTIFICATIONS_SERVICE_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "self.db.commit(" in stripped or "self.db.refresh(" in stripped:
            violations.append(f"{NOTIFICATIONS_SERVICE_PATH.relative_to(PROJECT_ROOT)}:{lineno}: {stripped}")

    assert violations == [], "Notifications service still uses raw session commit/refresh:\n" + "\n".join(
        violations
    )
