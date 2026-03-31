from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INVITES_SERVICE_PATH = PROJECT_ROOT / "app" / "modules" / "invites" / "service.py"


def test_invites_service_does_not_use_raw_session_commit_or_refresh() -> None:
    violations: list[str] = []

    for lineno, line in enumerate(INVITES_SERVICE_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "self.db.commit(" in stripped or "self.db.refresh(" in stripped:
            violations.append(f"{INVITES_SERVICE_PATH.relative_to(PROJECT_ROOT)}:{lineno}: {stripped}")

    assert violations == [], "Invites service still uses raw session commit/refresh:\n" + "\n".join(violations)
