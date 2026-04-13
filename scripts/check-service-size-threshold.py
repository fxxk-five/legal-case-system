from __future__ import annotations

import argparse
from pathlib import Path


def _iter_service_files(project_root: Path) -> list[Path]:
    modules_root = project_root / "backend" / "app" / "modules"
    integrations_root = project_root / "backend" / "app" / "integrations"

    module_service_files = [
        path
        for path in modules_root.glob("**/*.py")
        if "service" in path.stem
    ]
    integration_service_files = list(integrations_root.glob("**/service.py"))

    deduped_paths = {path.resolve(): path for path in module_service_files + integration_service_files}
    return sorted(deduped_paths.values())


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Warn or fail when backend service files exceed line-count threshold."
    )
    parser.add_argument("--threshold", type=int, default=280, help="Line threshold (default: 280)")
    parser.add_argument(
        "--fail-on-violation",
        action="store_true",
        help="Exit with non-zero code when files exceed threshold",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    service_files = _iter_service_files(project_root)

    violations: list[tuple[Path, int]] = []
    for file_path in service_files:
        total_lines = _line_count(file_path)
        if total_lines > args.threshold:
            violations.append((file_path, total_lines))

    if not violations:
        print(
            "Service size threshold check passed "
            f"({len(service_files)} files scanned, threshold={args.threshold})."
        )
        return 0

    print(f"Service size threshold exceeded (threshold={args.threshold}):")
    for path, lines in violations:
        print(f"- {path.relative_to(project_root)}: {lines} lines")
    print(
        f"Scanned {len(service_files)} service files; "
        f"{len(violations)} files exceed threshold."
    )

    if args.fail_on_violation:
        return 1

    print("Warning-only mode enabled; exiting with success.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
