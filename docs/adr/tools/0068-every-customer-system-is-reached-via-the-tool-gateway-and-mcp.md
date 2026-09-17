---
id: ADR-0068
title: Every customer system is reached via the Tool Gateway and MCP
status: accepted
date: 2026-09-13
deciders: []
category: tools
tags: [tools, mcp, authority]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: [ADR-0007, ADR-0018]
design: ../../design/tool-registry-and-authority.md
legacy_id: D68
---

# ADR-0068 — Every customer system is reached via the Tool Gateway and MCP

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D68`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/tool-registry-and-authority.md`](../../design/tool-registry-and-authority.md).

---

## 1. Context

ADR-0018 established the Tool Gateway → MCP → Grafana pattern for Grafana
specifically. As more customer-system integrations (Kubernetes, GitHub,
ticketing) were added, whether that pattern was Grafana-specific or a
general invariant — and what legitimate exceptions to it exist — needed
settling explicitly, since a single unreviewed direct client would bypass
the five-layer authority lattice (ADR-0063), credential resolution
(ADR-0018), throttling (ADR-0044), result reduction (ADR-0034) and audit
emission (ADR-0015) all at once.

## 2. Decision

**The harness never reaches a customer system directly. Every
agent-reachable customer system is reached Tool Gateway → MCP server →
system, without exception.** Generalises what was already true for
Grafana (ADR-0018) and makes it the invariant rather than the pattern:
Kubernetes is reached only via `k8s-mcp`, GitHub only via `github-mcp`,
ticketing only via its MCP server, telemetry only via `grafana-mcp`'s
datasource path. **Rationale is not uniformity but enforceability** — the
five-layer lattice (ADR-0063), per-call credential resolution (ADR-0018),
per-connection throttles protecting customer infrastructure (ADR-0044),
result reduction (ADR-0034) and audit emission (ADR-0015) all live at the
Tool Gateway, so a direct client is a hole in all five at once, and the
hole would be invisible in the audit chain rather than merely undesirable.
**Three exceptions, all non-agent-driven and all named explicitly:**
(1) scheduled workflows calling the Grafana admin API for service-account
provisioning, drift reconciliation and rotation (ADR-0022, ADR-0053) —
platform-internal, no agent in the loop; (2) the Tool Gateway itself
calling Grafana's access-control API for check-then-act (ADR-0023) — an
authorisation check, not a tool call, and the gateway is the enforcement
point rather than a bypass of it; (3) surface adapters calling Slack and
the plugin backend calling Grafana for narration and streaming
(ADR-0067) — output on our own surfaces, not action on a customer system.
**Anything not on that list that opens a direct client to a customer
system is a review defect.** L1 may keep drawing a single arrow from the
system box to each customer system — that is what L1 *is* — but from L2
down every such arrow passes through the gateway.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| Treat the Tool Gateway → MCP pattern as Grafana-specific, letting other integrations reach customer systems directly | ❌ Rejected | A direct client would bypass the five-layer authority lattice, credential resolution, throttling, result reduction and audit emission simultaneously — and the gap would be invisible in the audit chain. |
| Make Tool Gateway → MCP → system the invariant for every agent-reachable customer system, with only three explicitly named, non-agent-driven exceptions | ✅ Chosen | Preserves enforceability platform-wide; the three exceptions are all non-agent-driven and individually justified, so nothing agent-facing bypasses the gateway. |

## 4. Consequences

- **Positive —** the five enforcement mechanisms that live at the Tool
  Gateway (authority lattice, credentials, throttling, result reduction,
  audit) apply uniformly to every customer-system integration, present and
  future.
- **Negative / accepted trade —** three named exceptions exist
  (service-account provisioning workflows, the gateway's own
  check-then-act call, and narration adapters) and must be kept to exactly
  that list — anything else opening a direct client is a review defect.
- **Follow-on work —** new customer-system integrations must be added as
  MCP servers behind the gateway, not as direct clients.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original
  register entry was marked "verified live" for this decision. Mechanism:
  [`../../design/tool-registry-and-authority.md`](../../design/tool-registry-and-authority.md).
