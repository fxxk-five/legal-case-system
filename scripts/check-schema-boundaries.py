from __future__ import annotations

import re
from pathlib import Path


SCHEMA_REFERENCE_PATTERN = re.compile(r"\bapp\.schemas\b")


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    targets = [
        project_root / "backend" / "app",
        project_root / "backend" / "tests",
    ]

    files: list[Path] = []
    for base in targets:
        files.extend(sorted(base.glob("**/*.py")))

    violations: list[str] = []
    for file_path in files:
        if file_path.is_relative_to(project_root / "backend" / "app" / "schemas"):
            continue
        lines = file_path.read_text(encoding="utf-8").splitlines()
        for lineno, line in enumerate(lines, start=1):
            if not SCHEMA_REFERENCE_PATTERN.search(line):
                continue
            if line.strip().startswith("#"):
                continue

            violations.append(
                f"{file_path.relative_to(project_root)}:{lineno}: "
                "app.schemas.* is forbidden outside app/schemas compatibility package"
            )

    if violations:
        print("Schema boundary check failed:")
        for row in violations:
            print(f"- {row}")
        return 1

    print(
        "Schema boundary check passed "
        f"({len(files)} python files scanned)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
