from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_SERVICE_PATH = PROJECT_ROOT / "app" / "modules" / "ai" / "services" / "analysis_service.py"
PARSE_SERVICE_PATH = PROJECT_ROOT / "app" / "modules" / "ai" / "services" / "parse_service.py"
FALSIFICATION_SERVICE_PATH = PROJECT_ROOT / "app" / "modules" / "ai" / "services" / "falsification_service.py"
RUNTIME_SERVICE_PATH = PROJECT_ROOT / "app" / "modules" / "ai" / "services" / "runtime_service.py"
TASK_COMMAND_SERVICE_PATH = PROJECT_ROOT / "app" / "modules" / "ai" / "services" / "task_command_service.py"
WORKER_DISPATCH_SERVICE_PATH = PROJECT_ROOT / "app" / "modules" / "ai" / "services" / "worker_dispatch_service.py"
SUBMISSION_SERVICE_PATH = PROJECT_ROOT / "app" / "modules" / "ai" / "services" / "submission_service.py"
BUDGET_SERVICE_PATH = PROJECT_ROOT / "app" / "modules" / "ai" / "services" / "budget_service.py"
FLOW_SERVICE_PATH = PROJECT_ROOT / "app" / "modules" / "ai" / "services" / "flow_service.py"

RAW_SESSION_PATTERNS = (
    "service.db.add(",
    "service.db.flush(",
    "service.db.commit(",
    "service.db.refresh(",
    "service.db.rollback(",
    "retry_service.db.add(",
    "retry_service.db.flush(",
    "retry_service.db.commit(",
    "retry_service.db.refresh(",
    "retry_service.db.rollback(",
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


def test_runtime_service_does_not_use_raw_session_writes() -> None:
    violations = _collect_violations(RUNTIME_SERVICE_PATH)
    assert violations == [], "Runtime service still uses raw session operations:\n" + "\n".join(violations)


def test_task_command_service_does_not_use_raw_session_writes() -> None:
    violations = _collect_violations(TASK_COMMAND_SERVICE_PATH)
    assert violations == [], "Task command service still uses raw session operations:\n" + "\n".join(violations)


def test_worker_dispatch_service_does_not_use_raw_session_writes() -> None:
    violations = _collect_violations(WORKER_DISPATCH_SERVICE_PATH)
    assert violations == [], "Worker dispatch service still uses raw session operations:\n" + "\n".join(violations)


def test_submission_service_does_not_use_raw_session_writes() -> None:
    violations = _collect_violations(SUBMISSION_SERVICE_PATH)
    assert violations == [], "Submission service still uses raw session operations:\n" + "\n".join(violations)


def test_budget_service_does_not_use_raw_session_writes() -> None:
    violations = _collect_violations(BUDGET_SERVICE_PATH)
    assert violations == [], "Budget service still uses raw session operations:\n" + "\n".join(violations)


def test_flow_service_does_not_use_raw_session_writes() -> None:
    violations = _collect_violations(FLOW_SERVICE_PATH)
    assert violations == [], "Flow service still uses raw session operations:\n" + "\n".join(violations)
