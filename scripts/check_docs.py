#!/usr/bin/env python3
"""Documentation hygiene checks. Intended for CI.

  1. every relative markdown link resolves
  2. every ADR-NNNN reference resolves to a real ADR
  3. ADR front matter is complete and `category` matches the directory
  4. every accepted ADR names a design document that exists
  5. no references to deleted directories (research/, open-questions/)

Usage: python3 scripts/check_docs.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
ADR_DIR = DOCS / "adr"

REQUIRED_FM = ["id", "title", "status", "date", "category", "design"]
VALID_STATUS = {"proposed", "accepted", "rejected", "superseded", "deprecated"}
DEAD_PATH_RE = re.compile(r"(?:research|open-questions)/[\w][\w.-]*")
PROVENANCE = ("Promoted from", "Migrated from", "git history", "git show")

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)#][^)]*?)\)")
ADR_REF_RE = re.compile(r"\bADR-(\d{4})\b")

errors: list[str] = []
warnings: list[str] = []


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def parse_fm(path: Path) -> dict[str, str] | None:
    m = re.match(r"^---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.S)
    if not m:
        return None
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith("#"):
            k, _, v = line.partition(":")
            fm[k.strip()] = v.split("#")[0].strip()
    return fm


def main() -> int:
    md_files = sorted(DOCS.rglob("*.md"))

    # ---- collect known ADR ids
    adr_ids: set[str] = set()
    for p in ADR_DIR.rglob("*.md"):
        if p.parent == ADR_DIR:
            continue
        fm = parse_fm(p)
        if fm and "id" in fm:
            adr_ids.add(fm["id"])

    for p in md_files:
        text = p.read_text(encoding="utf-8")

        # ---- 1. relative links resolve
        for link in LINK_RE.findall(text):
            link = link.split("#")[0].strip()
            if not link or link.startswith(("http://", "https://", "mailto:")):
                continue
            if not (p.parent / link).resolve().exists():
                errors.append(f"{rel(p)}: dead link -> {link}")

        # ---- 2. ADR references resolve
        for num in ADR_REF_RE.findall(text):
            if p.name == "0000-template.md":
                continue
            aid = f"ADR-{num}"
            if aid not in adr_ids:
                errors.append(f"{rel(p)}: reference to unknown {aid}")

        # ---- 5. dead directories
        if "check_docs" not in p.name:
            for line in text.splitlines():
                # provenance notes intentionally name the removed source
                if any(k in line for k in PROVENANCE):
                    continue
                for hit in set(DEAD_PATH_RE.findall(line)):
                    warnings.append(
                        f"{rel(p)}: reference to removed path '{hit}'")

    # ---- 3 & 4. ADR front matter
    for p in sorted(ADR_DIR.rglob("*.md")):
        if p.parent == ADR_DIR or p.name.startswith("0000-"):
            continue
        fm = parse_fm(p)
        if fm is None:
            errors.append(f"{rel(p)}: missing YAML front matter")
            continue
        for key in REQUIRED_FM:
            if key not in fm or not fm[key]:
                errors.append(f"{rel(p)}: front matter missing '{key}'")
        if fm.get("status") not in VALID_STATUS:
            errors.append(f"{rel(p)}: invalid status '{fm.get('status')}'")
        if fm.get("category") != p.parent.name:
            errors.append(
                f"{rel(p)}: category '{fm.get('category')}' "
                f"!= directory '{p.parent.name}'"
            )
        design = fm.get("design", "")
        if fm.get("status") == "accepted":
            if design in ("", "none"):
                warnings.append(f"{rel(p)}: accepted ADR names no design doc")
            elif not (p.parent / design).resolve().exists():
                errors.append(f"{rel(p)}: design doc not found -> {design}")
        if fm.get("status") == "superseded" and fm.get("superseded_by", "[]") == "[]":
            errors.append(f"{rel(p)}: status superseded but superseded_by is empty")

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    print(f"\nchecked {len(md_files)} markdown files, {len(adr_ids)} ADRs")
    print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
