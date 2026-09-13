#!/usr/bin/env python3
"""Generate docs/adr/DECISION-INDEX.md from ADR front matter.

The index is generated so it cannot drift from the ADRs it summarises.
Run after adding or changing any ADR:  python3 scripts/gen_adr_index.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADR_DIR = ROOT / "docs" / "adr"
OUT = ADR_DIR / "DECISION-INDEX.md"

CATEGORY_ORDER = [
    ("platform", "Platform", "Surfaces, Grafana ownership, regional deployment"),
    ("agent", "Agent", "Framework, run model, durable execution"),
    ("tools", "Tools", "Tool Gateway, MCP invariants, authority lattice"),
    ("identity", "Identity", "Authn, federation, approval authority"),
    ("tenancy", "Tenancy", "Scoping, roles, budgets, lifecycle"),
    ("streaming", "Streaming", "Event model, transport, control liveness"),
    ("observability", "Observability", "Telemetry, audit, compliance"),
    ("conventions", "Conventions", "Cross-cutting normative rules"),
]

STATUS_MARK = {
    "accepted": "🟢",
    "proposed": "🟡",
    "superseded": "⚪",
    "rejected": "🔴",
    "deprecated": "⚪",
}

CORE = ["ADR-0021", "ADR-0051", "ADR-0052", "ADR-0059", "ADR-0002", "ADR-0036",
        "ADR-0037", "ADR-0039", "ADR-0007", "ADR-0068", "ADR-0063", "ADR-0010",
        "ADR-0013", "ADR-0014", "ADR-0065", "ADR-0015", "ADR-0049"]

R_REDIRECTS = {
    "R3": "ADR-0051", "R4": "ADR-0054", "R5": "ADR-0010",
    "R6": "ADR-0011", "R7": "ADR-0033", "R8": "ADR-0037",
}


def parse_front_matter(path: Path) -> dict[str, str] | None:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line or line.startswith("#"):
            continue
        k, _, v = line.partition(":")
        fm[k.strip()] = v.split("#")[0].strip()
    fm["_path"] = str(path.relative_to(ADR_DIR))
    return fm


def rel_links(raw: str, index: dict[str, dict]) -> str:
    ids = [x.strip() for x in raw.strip("[]").split(",") if x.strip()]
    out = []
    for i in ids:
        if i in index:
            out.append(f"[{i}]({index[i]['_path']})")
        else:
            out.append(i)
    return ", ".join(out)


def main() -> int:
    adrs: dict[str, dict] = {}
    for p in sorted(ADR_DIR.rglob("*.md")):
        if p.name.startswith("0000-") or p.parent == ADR_DIR:
            continue
        fm = parse_front_matter(p)
        if fm and "id" in fm:
            adrs[fm["id"]] = fm

    if not adrs:
        print("no ADRs found", file=sys.stderr)
        return 1

    L: list[str] = []
    L.append("# Decision index\n")
    L.append(
        "> **Generated — do not edit by hand.** "
        "Run `python3 scripts/gen_adr_index.py` after adding or changing an ADR.\n>\n"
        "> Conventions: [`README.md`](./README.md). "
        "Vocabulary: [`../GLOSSARY.md`](../GLOSSARY.md), which wins on conflict.\n"
    )
    total = len(adrs)
    active = sum(1 for a in adrs.values() if a.get("status") == "accepted")
    L.append(f"\n**{total} decisions · {active} accepted · "
             f"{total - active} superseded/other**\n")

    L.append("\n---\n\n## Start here — the core reading path\n")
    L.append("The decisions that constrain everything else, in dependency order. "
             "Roughly one sitting; the rest are consulted on demand.\n")
    for i, aid in enumerate(CORE, 1):
        a = adrs.get(aid)
        if a:
            L.append(f"{i}. [{aid} — {a['title']}]({a['_path']})")
    L.append("")

    for key, label, blurb in CATEGORY_ORDER:
        rows = sorted((a for a in adrs.values() if a.get("category") == key),
                      key=lambda x: x["id"])
        if not rows:
            continue
        L.append(f"\n---\n\n## {label}\n")
        L.append(f"*{blurb}*\n")
        designs = {r.get("design") for r in rows if r.get("design")}
        for d in sorted(designs):
            clean = d.replace("../../", "../")
            L.append(f"Mechanism: [`{clean}`]({clean})\n")
        L.append("| ADR | Title | Status | Date | Links |")
        L.append("|---|---|---|---|---|")
        for r in rows:
            st = r.get("status", "?")
            mark = STATUS_MARK.get(st, "")
            links = []
            if r.get("supersedes", "[]") != "[]":
                links.append("supersedes " + rel_links(r["supersedes"], adrs))
            if r.get("superseded_by", "[]") != "[]":
                links.append("**superseded by** " + rel_links(r["superseded_by"], adrs))
            if r.get("amends", "[]") != "[]":
                links.append("amends " + rel_links(r["amends"], adrs))
            if r.get("amended_by", "[]") != "[]":
                links.append("amended by " + rel_links(r["amended_by"], adrs))
            title = r["title"]
            if st == "superseded":
                title = f"~~{title}~~"
            L.append(f"| [{r['id']}]({r['_path']}) | {title} | {mark} {st} | "
                     f"{r.get('date','')} | {'; '.join(links)} |")

    L.append("\n---\n\n## Legacy identifier map\n")
    L.append("The register used `D`-numbers and `R`-numbers. Both are accepted "
             "aliases in prose; these are the canonical targets.\n")
    L.append("| Legacy | Canonical |")
    L.append("|---|---|")
    legacy = sorted(
        ((a["legacy_id"], a) for a in adrs.values()
         if a.get("legacy_id") and a["legacy_id"] != "null"),
        key=lambda kv: int(kv[0][1:]),
    )
    for lid, a in legacy:
        L.append(f"| `{lid}` | [{a['id']}]({a['_path']}) |")
    for lid, target in R_REDIRECTS.items():
        a = adrs.get(target)
        if a:
            L.append(f"| `{lid}` | [{a['id']}]({a['_path']}) |")
    L.append("\n**Folded sub-decisions** — no longer separate documents:\n")
    L.append("| Legacy | Now |")
    L.append("|---|---|")
    L.append("| `D4a` | section 2 of [ADR-0004](tools/0004-no-arbitrary-code-execution-in-v1.md) |")
    L.append("| `D7b` | section 2 of [ADR-0007](tools/0007-the-tool-gateway-is-a-separate-service.md) |")
    L.append("| `D7a` | promoted to [ADR-0070](tools/0070-all-mcp-servers-are-streamable-http-never-stdio.md) |")
    L.append("| `D8a` | promoted to [ADR-0071](observability/0071-two-telemetry-sinks-with-an-internal-only-eval-sink.md) |")
    L.append("")

    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} — {total} ADRs, {active} accepted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
