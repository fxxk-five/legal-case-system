from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
USERS_SERVICE_PATH = PROJECT_ROOT / "app" / "modules" / "users" / "service.py"


def test_users_service_does_not_use_raw_session_writes() -> None:
    violations: list[str] = []

    for lineno, line in enumerate(USERS_SERVICE_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if (
            "self.db.add(" in stripped
            or "self.db.commit(" in stripped
            or "self.db.refresh(" in stripped
            or "self.db.delete(" in stripped
            or "self.db.flush(" in stripped
        ):
            violations.append(f"{USERS_SERVICE_PATH.relative_to(PROJECT_ROOT)}:{lineno}: {stripped}")

    assert violations == [], "Users service still uses raw session operations:\n" + "\n".join(violations)
