from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CASE_FILE_SERVICE_PATH = PROJECT_ROOT / "app" / "modules" / "files" / "case_file_service.py"
UPLOAD_SERVICE_PATH = PROJECT_ROOT / "app" / "modules" / "files" / "upload_service.py"


def test_case_file_service_does_not_use_raw_session_writes() -> None:
    violations: list[str] = []

    for lineno, line in enumerate(CASE_FILE_SERVICE_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "self.db.commit(" in stripped or "self.db.refresh(" in stripped:
            violations.append(f"{CASE_FILE_SERVICE_PATH.relative_to(PROJECT_ROOT)}:{lineno}: {stripped}")

    assert violations == [], "Case file service still uses raw session operations:\n" + "\n".join(violations)


def test_upload_service_does_not_use_raw_session_writes() -> None:
    violations: list[str] = []

    for lineno, line in enumerate(UPLOAD_SERVICE_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "db.add(" in stripped or "db.commit(" in stripped or "db.refresh(" in stripped:
            violations.append(f"{UPLOAD_SERVICE_PATH.relative_to(PROJECT_ROOT)}:{lineno}: {stripped}")

    assert violations == [], "Upload service still uses raw session operations:\n" + "\n".join(violations)
