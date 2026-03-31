from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"
LEGACY_SERVICES_ROOT = APP_ROOT / "services"


def test_backend_source_does_not_import_legacy_services_package() -> None:
    violations: list[str] = []

    for file_path in APP_ROOT.glob("**/*.py"):
        if file_path.is_relative_to(LEGACY_SERVICES_ROOT):
            continue

        for lineno, line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "app.services." not in stripped:
                continue

            violations.append(
                f"{file_path.relative_to(PROJECT_ROOT)}:{lineno}: {stripped}"
            )

    assert violations == [], "Legacy service imports remain:\n" + "\n".join(violations)
