#!/usr/bin/env python3
"""Enforce the current Python architecture import boundaries.

The reference harness must not import customer-system SDKs or clients directly.
Generic HTTP modules remain allowed: a future Authority Service HTTP MCP client
is an internal-service boundary, not a direct customer-system client. DBOS is a
special case and may only be imported by the future ``harness/runtime.py`` seam.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = ROOT / "harness"
DBOS_ROOT = "dbos"
DBOS_RUNTIME = Path("harness/runtime.py")
FORBIDDEN_CUSTOMER_CLIENT_ROOTS = frozenset(
    {
        "boto3",
        "botocore",
        "grafana_api",
        "grafana_client",
        "kubernetes",
        "kubernetes_asyncio",
        "prometheus_api_client",
        "redis",
        "slack_sdk",
    }
)


def python_files(paths: list[Path]) -> list[Path]:
    """Return sorted Python files under the requested paths."""
    files: list[Path] = []
    for supplied_path in paths:
        path = supplied_path if supplied_path.is_absolute() else ROOT / supplied_path
        if path.is_dir():
            files.extend(sorted(path.rglob("*.py")))
        elif path.suffix == ".py":
            files.append(path)
        else:
            print(f"WARN {supplied_path}: skipped (not a Python file)", file=sys.stderr)
    return files


def relative_path(path: Path) -> Path:
    """Return a repository-relative path for stable rule matching and output."""
    return path.resolve().relative_to(ROOT)


def imported_roots(node: ast.Import | ast.ImportFrom) -> set[str]:
    """Extract top-level imported package names from an AST import node."""
    if isinstance(node, ast.Import):
        return {alias.name.split(".", 1)[0] for alias in node.names}
    if node.module is None:
        return set()
    return {node.module.split(".", 1)[0]}


def check_file(path: Path) -> list[str]:
    """Check one Python source file and return architecture violations."""
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (OSError, SyntaxError) as exc:
        return [f"{path}: unable to parse: {exc}"]

    relative = relative_path(path)
    errors: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        for imported in imported_roots(node):
            if imported == DBOS_ROOT and relative != DBOS_RUNTIME:
                errors.append(
                    f"{relative}:{node.lineno}: DBOS imports are restricted to {DBOS_RUNTIME}"
                )
            if imported in FORBIDDEN_CUSTOMER_CLIENT_ROOTS:
                errors.append(
                    f"{relative}:{node.lineno}: forbidden direct customer client import {imported}"
                )

    if "stdio" in source.lower():
        errors.append(f"{relative}: stdio MCP configuration is forbidden")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, default=[DEFAULT_PATH])
    args = parser.parse_args()

    files = python_files(args.paths)
    errors = [error for path in files for error in check_file(path)]
    for error in errors:
        print(f"ERROR {error}")
    print(f"checked {len(files)} Python file(s)")
    print(f"{len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
