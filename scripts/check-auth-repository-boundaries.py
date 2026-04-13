from __future__ import annotations

import ast
import sys
from pathlib import Path


FORBIDDEN_DB_METHODS = {"query", "execute"}


def _is_db_receiver(node: ast.AST) -> bool:
    if isinstance(node, ast.Name):
        return node.id == "db"
    if isinstance(node, ast.Attribute):
        if node.attr == "db":
            return True
        return _is_db_receiver(node.value)
    return False


def _should_scan(path: Path) -> bool:
    if path.name in {"repository.py", "__init__.py"}:
        return False
    if path.name in {"router.py", "deps.py"}:
        return True
    if path.parent.name == "services":
        return True
    return "service" in path.stem


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    auth_root = project_root / "backend" / "app" / "modules" / "auth"
    files = sorted(auth_root.glob("**/*.py"))

    scanned_files = [path for path in files if _should_scan(path)]
    violations: list[str] = []

    for file_path in scanned_files:
        source = file_path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError as error:
            violations.append(
                f"{file_path.relative_to(project_root)}:{error.lineno or 1}:"
                f" syntax error while checking boundaries: {error.msg}"
            )
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue
            method_name = node.func.attr
            if method_name not in FORBIDDEN_DB_METHODS:
                continue
            if not _is_db_receiver(node.func.value):
                continue

            violations.append(
                f"{file_path.relative_to(project_root)}:{node.lineno}: "
                f"direct db.{method_name}(...) is forbidden in auth service/deps/router files"
            )

    if violations:
        print("Auth repository boundary check failed:")
        for row in violations:
            print(f"- {row}")
        return 1

    print(
        "Auth repository boundary check passed "
        f"({len(scanned_files)} files scanned)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
