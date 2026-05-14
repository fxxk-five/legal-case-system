from __future__ import annotations

import re
import sys
from pathlib import Path


ROUTER_IMPORT_PATTERN = re.compile(r"from\s+app\.modules\.[\w_]+\.router\s+import")
DB_QUERY_PATTERN = re.compile(r"\bdb\.query\s*\(")


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    router_files = sorted((project_root / "backend" / "app" / "modules").glob("**/router.py"))
    violations: list[str] = []

    for router_file in router_files:
        text = router_file.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if ROUTER_IMPORT_PATTERN.search(line):
                violations.append(
                    f"{router_file.relative_to(project_root)}:{lineno}: router-to-router import is forbidden"
                )
            if DB_QUERY_PATTERN.search(line):
                violations.append(
                    f"{router_file.relative_to(project_root)}:{lineno}: db.query(...) in router is forbidden"
                )

    if violations:
        print("Router boundary check failed:")
        for row in violations:
            print(f"- {row}")
        return 1

    print(f"Router boundary check passed ({len(router_files)} router files scanned).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
