"""Code convention checks — project-specific rules that go beyond ruff."""

from __future__ import annotations

import re
import sys
from pathlib import Path

BANNED_APIS = [
    {
        "pattern": re.compile(r"wait_for_timeout"),
        "message": "Use page.wait_for_selector instead of wait_for_timeout",
        "exclude": [],
    },
]

REQUIRED_ENCODING = "utf-8"
ENCODING_METHODS = ["read_text", "write_text"]

SOURCE_DIRS = ["src", "tests", "examples"]


def _scan_files(root: Path) -> list[tuple[str, list[str]]]:
    """Yield (relative_path, lines) for all Python files in SOURCE_DIRS."""
    results: list[tuple[str, list[str]]] = []
    for source_dir in SOURCE_DIRS:
        dir_path = root / source_dir
        if not dir_path.exists():
            continue
        for py_file in dir_path.rglob("*.py"):
            rel = py_file.relative_to(root).as_posix()
            lines = py_file.read_text(encoding="utf-8").splitlines()
            results.append((rel, lines))
    return results


def check_banned_apis(files: list[tuple[str, list[str]]]) -> list[str]:
    violations: list[str] = []
    for rel, lines in files:
        for line_no, line in enumerate(lines, 1):
            for rule in BANNED_APIS:
                if rel in rule.get("exclude", []):
                    continue
                if rule["pattern"].search(line):
                    violations.append(f"  {rel}:{line_no}: {rule['message']}")
    return violations


def check_encoding(files: list[tuple[str, list[str]]]) -> list[str]:
    has_method = re.compile(r"\.(" + "|".join(ENCODING_METHODS) + r")\(")
    has_encoding = re.compile(r'encoding\s*=\s*["\']' + REQUIRED_ENCODING + r"[\"']")
    violations: list[str] = []
    for rel, lines in files:
        for line_no, line in enumerate(lines, 1):
            if has_method.search(line) and not has_encoding.search(line):
                violations.append(
                    f'  {rel}:{line_no}: missing encoding="{REQUIRED_ENCODING}" (Windows defaults to cp1252)'
                )
    return violations


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    files = _scan_files(root)
    failed = False

    for name, check in [
        ("Banned API usage", check_banned_apis),
        ("Missing encoding", check_encoding),
    ]:
        violations = check(files)
        if violations:
            print(f"{name}:")
            for v in violations:
                print(v)
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
