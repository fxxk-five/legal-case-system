from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_SERVICE_PATH = PROJECT_ROOT / "app" / "modules" / "ai" / "services" / "analysis_service.py"
PARSE_SERVICE_PATH = PROJECT_ROOT / "app" / "modules" / "ai" / "services" / "parse_service.py"
FALSIFICATION_SERVICE_PATH = PROJECT_ROOT / "app" / "modules" / "ai" / "services" / "falsification_service.py"

RAW_SESSION_PATTERNS = (
    "service.db.add(",
    "service.db.flush(",
    "service.db.commit(",
    "service.db.refresh(",
    "service.db.rollback(",
)


def _collect_violations(path: Path) -> list[str]:
    violations: list[str] = []

    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if any(pattern in stripped for pattern in RAW_SESSION_PATTERNS):
            violations.append(f"{path.relative_to(PROJECT_ROOT)}:{lineno}: {stripped}")

    return violations


def test_analysis_service_does_not_use_raw_session_writes() -> None:
    violations = _collect_violations(ANALYSIS_SERVICE_PATH)
    assert violations == [], "Analysis service still uses raw session operations:\n" + "\n".join(violations)


def test_parse_service_does_not_use_raw_session_writes() -> None:
    violations = _collect_violations(PARSE_SERVICE_PATH)
    assert violations == [], "Parse service still uses raw session operations:\n" + "\n".join(violations)


def test_falsification_service_does_not_use_raw_session_writes() -> None:
    violations = _collect_violations(FALSIFICATION_SERVICE_PATH)
    assert violations == [], "Falsification service still uses raw session operations:\n" + "\n".join(violations)
