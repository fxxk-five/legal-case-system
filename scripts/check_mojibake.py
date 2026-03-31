from __future__ import annotations

import argparse
import sys
from pathlib import Path


DEFAULT_TARGETS = [
    "web-frontend/src",
    "mini-program",
    "backend/app",
]

TEXT_EXTENSIONS = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".py",
    ".ts",
    ".tsx",
    ".txt",
    ".vue",
    ".yaml",
    ".yml",
}

EXCLUDED_DIR_NAMES = {
    "__pycache__",
    ".git",
    ".idea",
    ".runtime",
    "coverage",
    "dist",
    "node_modules",
}

SUSPICIOUS_TOKENS = [
    "\u951f",
    "\u00c3",
    "\u00c2",
    "\u00e2",
    "\u5997",
    "\u9427",
    "\u95ed\u20ac",
    "\u9353\ue807",
    "\u93a2\u6d23\u5a06",
    "\u74c7\u950b",
]


def should_skip(path: Path) -> bool:
    if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
        return True
    return path.suffix.lower() not in TEXT_EXTENSIONS


def scan_file(path: Path) -> list[tuple[int, str]]:
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    matches: list[tuple[int, str]] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        if any(token in line for token in SUSPICIOUS_TOKENS):
            matches.append((line_number, line.strip()))
    return matches


def iter_target_files(root: Path, targets: list[str]) -> list[Path]:
    files: list[Path] = []
    for target in targets:
        resolved = (root / target).resolve()
        if not resolved.exists():
            continue
        if resolved.is_file():
            if not should_skip(resolved):
                files.append(resolved)
            continue
        for path in resolved.rglob("*"):
            if path.is_file() and not should_skip(path):
                files.append(path)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan repo text files for common mojibake patterns.")
    parser.add_argument("targets", nargs="*", default=DEFAULT_TARGETS, help="Paths to scan, relative to repo root.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    findings: list[tuple[Path, int, str]] = []

    for path in iter_target_files(repo_root, args.targets):
        for line_number, line in scan_file(path):
            findings.append((path, line_number, line))

    if not findings:
        print("No suspicious mojibake patterns found.")
        return 0

    print("Suspicious mojibake patterns found:")
    for path, line_number, line in findings:
        relative_path = path.relative_to(repo_root)
        print(f"{relative_path}:{line_number}: {line}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
