#!/usr/bin/env python3
"""One-shot migration: DECISION-REGISTER.md table -> per-ADR files.

Lossless: each register cell is carried verbatim into the ADR body. Re-sectioning
the prose into Context / Considered options / Consequences is a per-ADR follow-up,
flagged with a TODO marker so it is visible rather than silently missing.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTER = ROOT / "docs" / "adr" / "DECISION-REGISTER.md"
ADR_DIR = ROOT / "docs" / "adr"

# d-number -> (category, title, date)
META: dict[str, tuple[str, str, str]] = {
    "1":  ("platform", "Grafana integration via the plugin backend proxy", "2026-09-12"),
    "2":  ("platform", "Trigger surfaces for v1 are the Grafana plugin and Slack", "2026-09-12"),
    "3":  ("agent", "Agent framework is LangGraph plus DeepAgents", "2026-09-12"),
    "4":  ("tools", "No arbitrary code execution in v1", "2026-09-12"),
    "5":  ("observability", "Observability is OTel-native", "2026-09-12"),
    "6":  ("streaming", "Streaming is decoupled from orchestration via a durable event log", "2026-09-12"),
    "7":  ("tools", "The Tool Gateway is a separate service", "2026-09-12"),
    "8":  ("observability", "Instrumentation is OpenLIT plus hand-written spans over OTLP", "2026-09-12"),
    "9":  ("identity", "Grafana identity forwarding via X-Grafana-Id is the primary inbound authn", "2026-09-12"),
    "10": ("identity", "The harness mints its own run-scoped capability token", "2026-09-12"),
    "11": ("identity", "Downstream credentials are hybrid, service-identity by default", "2026-09-12"),
    "12": ("identity", "Grafana service accounts are self-provisioned imperatively", "2026-09-12"),
    "13": ("identity", "system_initiated runs are structurally read-only", "2026-09-12"),
    "14": ("identity", "Approval is a re-authenticated human act that happens in Grafana", "2026-09-12"),
    "15": ("observability", "Audit records form an insert-only hash-chained DAG", "2026-09-12"),
    "16": ("tenancy", "Configuration is Tenant-scoped and shared", "2026-09-12"),
    "17": ("tenancy", "Limits form a ceiling chain", "2026-09-12"),
    "18": ("tools", "One logical grafana-mcp service with two credential hops", "2026-09-12"),
    "19": ("identity", "The MCP Authorization Server is logically distinct from the Tool Gateway", "2026-09-12"),
    "20": ("identity", "Slack account linking uses Sign in with Slack (OIDC)", "2026-09-12"),
    "21": ("platform", "The platform owns and operates the Grafana instance", "2026-09-12"),
    "22": ("identity", "Grafana service accounts are provisioned synchronously at Tenant creation", "2026-09-12"),
    "23": ("tools", "Check-then-act enforcement is performed by the Tool Gateway", "2026-09-12"),
    "24": ("identity", "Slack and system_initiated runs receive no per-user Grafana check", "2026-09-12"),
    "25": ("observability", "Compliance regime for v1 is PCI-DSS", "2026-09-12"),
    "26": ("identity", "Enforcement granularity is Grafana basic roles", "2026-09-12"),
    "27": ("tools", "Use the MCP SDK OAuthClientProvider for RFC 9728 discovery", "2026-09-12"),
    "28": ("identity", "Canonical Slack identity is keyed by slack_enterprise_id", "2026-09-12"),
    "29": ("streaming", "The event model is our own, internally versioned", "2026-09-12"),
    "30": ("streaming", "The durable event log is Postgres-only for v1", "2026-09-12"),
    "31": ("streaming", "Grafana surface streaming uses Grafana Live", "2026-09-12"),
    "32": ("streaming", "Shared runs use a soft-lock driver model", "2026-09-12"),
    "33": ("streaming", "The back-channel is plain REST", "2026-09-12"),
    "34": ("streaming", "Token-level narrative streaming on all surfaces", "2026-09-12"),
    "35": ("streaming", "Unattended-run notification via Slack summary and in-app inbox", "2026-09-12"),
    "36": ("agent", "Every agent interaction is the same run primitive", "2026-09-12"),
    "37": ("agent", "The durable-execution engine is DBOS Transact", "2026-09-12"),
    "38": ("agent", "Work rediscovery is ours to build", "2026-09-12"),
    "39": ("agent", "The run is the durable workflow", "2026-09-12"),
    "40": ("agent", "LangGraph is compiled with no checkpointer", "2026-09-12"),
    "41": ("agent", "Step granularity is one LLM call or one tool call", "2026-09-12"),
    "42": ("agent", "Idempotency is three-layered", "2026-09-12"),
    "43": ("agent", "Cancellation is effective at the next step boundary", "2026-09-12"),
    "44": ("tenancy", "Budget enforcement is split across three layers", "2026-09-12"),
    "45": ("agent", "Signal delivery is DBOS send and recv", "2026-09-12"),
    "46": ("agent", "Deploy strategy is blue/green on DBOS application version", "2026-09-12"),
    "47": ("agent", "All five durable-timer use cases ship in v1", "2026-09-12"),
    "48": ("agent", "A thin runtime seam isolates the durable-execution engine", "2026-09-12"),
    "49": ("platform", "Two independent regional deployments", "2026-09-13"),
    "50": ("tenancy", "Isolation is never thread-level", "2026-09-13"),
    "51": ("tenancy", "The scope model collapses to a single graft_tenant_id", "2026-09-13"),
    "52": ("conventions", "A normative glossary owns the ubiquitous language", "2026-09-13"),
    "53": ("tenancy", "Tenant lifecycle is discovered, provisioning, ready, suspended", "2026-09-13"),
    "54": ("tenancy", "Run ownership is private by default and irreversibly promotable", "2026-09-13"),
    "55": ("tenancy", "Approval authority is initiator-only", "2026-09-13"),
    "56": ("tenancy", "The IdP authenticates and the harness authorizes", "2026-09-13"),
    "57": ("tenancy", "Budget ceilings are per-scope with distinct at-cap behaviour", "2026-09-13"),
    "58": ("tenancy", "Schedules are a governed Tenant-scoped resource", "2026-09-13"),
    "59": ("conventions", "Every identifier is prefixed with the system that owns it", "2026-09-13"),
    "60": ("identity", "External references are modelled in three layers", "2026-09-13"),
    "61": ("identity", "Identity linking is mandatory and verified", "2026-09-13"),
    "62": ("agent", "Custom instructions exist at Tenant and Principal level", "2026-09-13"),
    "63": ("tools", "Tool authority is a five-layer narrowing lattice", "2026-09-13"),
    "64": ("streaming", "Shared-run control is one driver with explicit handover", "2026-09-13"),
    "65": ("identity", "Approval authority follows the driver", "2026-09-13"),
    "66": ("streaming", "Control liveness is three independent server-side clocks", "2026-09-13"),
    "67": ("tools", "Paging and on-call writes are classified, v1 ships read only", "2026-09-13"),
    "68": ("tools", "Every customer system is reached via the Tool Gateway and MCP", "2026-09-13"),
    "69": ("tools", "Token Service, Tool Gateway and Registry ship as one Authority Service", "2026-09-13"),
    # promoted from lettered sub-decisions / split clauses
    "70": ("tools", "All MCP servers are streamable-HTTP, never stdio", "2026-09-12"),
    "71": ("observability", "Two telemetry sinks with an internal-only eval sink", "2026-09-12"),
    "72": ("streaming", "Run list filters and web-frontend Tenant resolution", "2026-09-13"),
}

# lettered decisions folded into a parent (appended to the parent body)
FOLD = {"4a": "4", "7b": "7"}
# lettered decisions promoted to their own number
PROMOTE = {"7a": "70", "8a": "71"}

STATUS = {"55": "superseded"}

REL: dict[str, dict[str, list[str]]] = {
    "4":  {"relates_to": ["ADR-0007"]},
    "7":  {"relates_to": ["ADR-0070", "ADR-0068", "ADR-0069"]},
    "70": {"amends": ["ADR-0007"]},
    "71": {"amends": ["ADR-0008"], "relates_to": ["ADR-0040"]},
    "8":  {"amended_by": ["ADR-0071"]},
    "12": {"amended_by": ["ADR-0022"]},
    "22": {"amends": ["ADR-0012"]},
    "16": {"amended_by": ["ADR-0062"]},
    "62": {"amends": ["ADR-0016"]},
    "17": {"amended_by": ["ADR-0057"]},
    "57": {"amends": ["ADR-0017"]},
    "19": {"relates_to": ["ADR-0069"]},
    "69": {"relates_to": ["ADR-0019", "ADR-0007"]},
    "33": {"amended_by": ["ADR-0045"]},
    "45": {"amends": ["ADR-0033"]},
    "35": {"amended_by": ["ADR-0047"]},
    "47": {"amends": ["ADR-0035"]},
    "55": {"superseded_by": ["ADR-0065", "ADR-0066"]},
    "65": {"supersedes": ["ADR-0055"], "relates_to": ["ADR-0064", "ADR-0014"]},
    "64": {"amended_by": ["ADR-0065"], "relates_to": ["ADR-0072", "ADR-0032", "ADR-0066"]},
    "72": {"relates_to": ["ADR-0064"]},
    "28": {"amended_by": ["ADR-0052"]},
    "48": {"relates_to": ["ADR-0037", "ADR-0039", "ADR-0041"]},
    "18": {"relates_to": ["ADR-0068"]},
    "68": {"relates_to": ["ADR-0007", "ADR-0018"]},
}

DESIGN = {
    "platform": "../../design/platform-topology.md",
    "agent": "../../design/durable-execution.md",
    "tools": "../../design/tool-registry-and-authority.md",
    "identity": "../../design/external-identity-mapping.md",
    "tenancy": "../../design/tenancy-and-scoping.md",
    "streaming": "../../design/streaming-and-events.md",
    "observability": "../../design/audit-and-attribution.md",
    "conventions": "../../GLOSSARY.md",
}

TAGS = {
    "platform": ["platform", "deployment"],
    "agent": ["agent", "orchestration", "durability"],
    "tools": ["tools", "mcp", "authority"],
    "identity": ["identity", "authn", "authz"],
    "tenancy": ["tenancy", "scoping", "rbac"],
    "streaming": ["streaming", "events"],
    "observability": ["observability", "audit", "compliance"],
    "conventions": ["convention", "vocabulary"],
}


def slug(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s[:70].rstrip("-")


def parse_register() -> dict[str, str]:
    """Return {d-number: verbatim cell markdown}."""
    cells: dict[str, str] = {}
    for line in REGISTER.read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("|"):
            continue
        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        if len(parts) < 2:
            continue
        m = re.match(r"^~*\*\*D(\d+[a-z]?)\*\*~*", parts[0])
        if not m:
            continue
        cells[m.group(1)] = parts[1].strip()
    return cells


def yaml_list(v: list[str]) -> str:
    return "[" + ", ".join(v) + "]" if v else "[]"


def render(num: str, body: str, folded: list[tuple[str, str]]) -> str:
    cat, title, date = META[num]
    adr_id = f"ADR-{int(num):04d}"
    status = STATUS.get(num, "accepted")
    rel = REL.get(num, {})
    fm = [
        "---",
        f"id: {adr_id}",
        f"title: {title}",
        f"status: {status}",
        f"date: {date}",
        "deciders: []",
        f"category: {cat}",
        f"tags: {yaml_list(TAGS[cat])}",
        f"supersedes: {yaml_list(rel.get('supersedes', []))}",
        f"superseded_by: {yaml_list(rel.get('superseded_by', []))}",
        f"amends: {yaml_list(rel.get('amends', []))}",
        f"amended_by: {yaml_list(rel.get('amended_by', []))}",
        f"relates_to: {yaml_list(rel.get('relates_to', []))}",
        f"design: {DESIGN[cat]}",
        f"legacy_id: D{num}" if int(num) <= 69 else "legacy_id: null",
        "---",
        "",
    ]
    out = ["\n".join(fm)]
    out.append(f"# {adr_id} — {title}\n")
    out.append(
        f"> **Status: {status} ({date}).** Migrated verbatim from "
        f"`DECISION-REGISTER.md` (legacy `D{num}`).\n>\n"
        f"> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). "
        f"Mechanism: [`{DESIGN[cat]}`]({DESIGN[cat]}).\n"
    )
    out.append("---\n")
    out.append("## 1. Context\n")
    out.append(
        "<!-- TODO(migration): extract the forces from the Decision text below. "
        "The register did not separate them. -->\n"
    )
    out.append("## 2. Decision\n")
    out.append(body + "\n")
    for letter, text in folded:
        out.append(f"### 2.{letter} — folded from legacy `D{letter}`\n")
        out.append(text + "\n")
    out.append("## 3. Considered options\n")
    out.append(
        "<!-- TODO(migration): several register cells name the rejected option "
        "inline (\"considered and rejected\", \"chosen over\"). Lift them here. -->\n"
    )
    out.append("## 4. Consequences\n")
    out.append("<!-- TODO(migration): lift \"accepted tension\" / revisit metrics here. -->\n")
    out.append("## 5. Verification\n")
    out.append(
        "<!-- Claims marked \"verified live\" in the register carry their date "
        "inline in section 2; restate them here when this ADR is next touched. -->\n"
    )
    return "\n".join(out)


def main() -> None:
    cells = parse_register()
    print(f"parsed {len(cells)} register rows: {sorted(cells)}")

    # promote lettered decisions into their own numbers
    for letter, target in PROMOTE.items():
        if letter in cells:
            cells[target] = cells.pop(letter)

    # collect folds
    folds: dict[str, list[tuple[str, str]]] = {}
    for letter, parent in FOLD.items():
        if letter in cells:
            folds.setdefault(parent, []).append((letter, cells.pop(letter)))

    written = 0
    for num, body in sorted(cells.items(), key=lambda kv: int(kv[0])):
        if num not in META:
            print(f"  !! no metadata for D{num} — skipped")
            continue
        cat, title, _ = META[num]
        d = ADR_DIR / cat
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{int(num):04d}-{slug(title)}.md"
        path.write_text(render(num, body, folds.get(num, [])), encoding="utf-8")
        written += 1

    # ADR-0072 has no register row of its own: it is a split-out clause of D64.
    if "72" not in cells:
        cat, title, date = META["72"]
        d = ADR_DIR / cat
        d.mkdir(parents=True, exist_ok=True)
        body = (
            "**Run list filters are “Mine” and “Tenant”** — deliberately *not* the "
            "originally proposed “mine / my team / all”, because there is no “my team” "
            "(Group is not a scoping layer, ADR-0051) and no “all” (cross-Tenant listing "
            "does not exist, ADR-0051).\n\n"
            "**Web frontend (post-v1, ADR-0002): Tenant resolution is OIDC/SSO against the "
            "existing `graft_external_ref` mapping** (ADR-0060) — an explicit Tenant switcher "
            "seeded from the Principal's `default_graft_tenant_id`, active Tenant carried in "
            "the harness token exactly as every other surface. No new resolution mechanism is "
            "invented for it.\n\n"
            "> Split out of legacy `D64` during the 2026-09-13 ADR migration: these clauses "
            "survived D65's supersession of D64's approval clause, and were never about "
            "run control in the first place."
        )
        (d / f"{72:04d}-{slug(title)}.md").write_text(render("72", body, []), encoding="utf-8")
        written += 1

    print(f"wrote {written} ADR files")


if __name__ == "__main__":
    main()
