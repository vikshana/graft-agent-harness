#!/usr/bin/env python3
"""Check that DBOS steps declare pointer-only return types.

The repository has no application package yet, so this checker is deliberately
independent of the future runtime implementation. It walks Python source files,
finds functions decorated with ``@DBOS.step`` (including imported aliases), and
requires a recognised pointer return annotation.

Usage:
    python3 scripts/check_step_pointer_rule.py path/to/app [more paths ...]
    python3 scripts/check_step_pointer_rule.py --pointer-type ArtifactPointer path

A function without a return annotation, or with an annotation that is not one
of the configured pointer type names, fails. The default names are the
contract-level names currently reserved for Phase 1; application code may add
its concrete pointer type with ``--pointer-type``.
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

DEFAULT_POINTER_TYPES = {"ArtifactPointer", "ArtifactRef", "Pointer"}


class StepVisitor(ast.NodeVisitor):
    def __init__(self, path: Path, pointer_types: set[str]) -> None:
        self.path = path
        self.pointer_types = pointer_types
        self.errors: list[str] = []
        self.dbos_aliases = {"DBOS"}
        self.step_aliases: set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "dbos":
                self.dbos_aliases.add(alias.asname or "dbos")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "dbos":
            for alias in node.names:
                if alias.name == "DBOS":
                    self.dbos_aliases.add(alias.asname or "DBOS")
                if alias.name == "step":
                    self.step_aliases.add(alias.asname or "step")
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check(node)
        self.generic_visit(node)

    def _check(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if not any(self._is_step_decorator(decorator) for decorator in node.decorator_list):
            return
        annotation = node.returns
        if annotation is None:
            self.errors.append(
                f"{self.path}:{node.lineno}: {node.name} has no pointer return annotation"
            )
            return
        names = self._annotation_names(annotation)
        wrappers = {"Annotated", "Optional", "Union"}
        value_names = names - wrappers
        if not value_names or not value_names <= self.pointer_types:
            expected = ", ".join(sorted(self.pointer_types))
            self.errors.append(
                f"{self.path}:{node.lineno}: {node.name} returns "
                f"{ast.unparse(annotation)!r}; expected one of: {expected}"
            )

    def _is_step_decorator(self, node: ast.expr) -> bool:
        if isinstance(node, ast.Call):
            node = node.func
        if isinstance(node, ast.Attribute):
            return node.attr == "step" and self._root_name(node.value) in self.dbos_aliases
        return isinstance(node, ast.Name) and node.id in self.step_aliases

    @staticmethod
    def _root_name(node: ast.expr) -> str | None:
        return node.id if isinstance(node, ast.Name) else None

    @staticmethod
    def _annotation_names(node: ast.expr) -> set[str]:
        names: set[str] = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                names.add(child.id)
            elif isinstance(child, ast.Attribute):
                names.add(child.attr)
        return names


def check_file(path: Path, pointer_types: set[str]) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        return [f"{path}: unable to parse: {exc}"]
    visitor = StepVisitor(path, pointer_types)
    visitor.visit(tree)
    return visitor.errors


def python_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(path.rglob("*.py")))
        elif path.suffix == ".py":
            files.append(path)
        else:
            print(f"WARN {path}: skipped (not a Python file)", file=sys.stderr)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pointer-type",
        action="append",
        dest="pointer_types",
        help="recognised pointer type name; may be repeated",
    )
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    pointer_types = set(args.pointer_types or DEFAULT_POINTER_TYPES)
    files = python_files(args.paths)
    errors = [
        error
        for path in files
        for error in check_file(path, pointer_types)
    ]
    for error in errors:
        print(f"ERROR {error}")
    print(f"checked {len(files)} Python file(s)")
    print(f"{len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())


