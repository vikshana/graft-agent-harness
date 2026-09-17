---
id: ADR-0063
title: Tool authority is a five-layer narrowing lattice
status: accepted
date: 2026-09-13
deciders: []
category: tools
tags: [tools, mcp, authority]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
design: ../../design/tool-registry-and-authority.md
legacy_id: D63
---

# ADR-0063 — Tool authority is a five-layer narrowing lattice

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D63`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/tool-registry-and-authority.md`](../../design/tool-registry-and-authority.md).

---

## 1. Context

Tool authority needed a model that satisfies several requirements at once:
a platform-wide kill switch effective on in-flight runs; per-Tenant policy
that can be more restrictive than the platform default but never more
permissive; per-run and per-call narrowing; policy granularity at the tool
level (not the server level, since a server may mix safe read tools with
dangerous write tools); and resistance to prompt injection via
upstream-supplied tool descriptions and to unreviewed changes in an
upstream tool's behaviour ("rug pull").

## 2. Decision

**Tool authority is a five-layer monotonically-narrowing lattice; the
platform has the ultimate say.** `L1 platform catalogue` (what exists) →
`L2 platform policy` (what may **ever** be enabled — hard deny, not
customer-raisable) → `L3 Tenant policy` (what **is** enabled;
`tenant_admin`, versioned, step-up for write classes, ADR-0016) →
`L4 run capability token` (what **this run** may call; ADR-0010, ADR-0013,
ADR-0042) → `L5 call-time check` (may **this Principal**, **now**;
ADR-0023, ADR-0056, ADR-0044). **Effective capability is the intersection;
no layer can grant what a layer above has not.** L1 and L2 are
deliberately separate — collapsing them means the only way to forbid
something globally is to delete the integration, which also removes its
safe read-only tools; L2 is also the **platform-wide kill switch**,
effective on in-flight runs at their next tool call because L5
re-evaluates per call. **Policy granularity is the tool, not the server** —
enabling `grafana-mcp` must not enable its write set, and ADR-0022's
"minimum role across enabled tools" is only meaningful if enablement is
per tool; **ToolClass** (`read`/`write`/`destructive`) is the unit of
policy and approval, **Tool** the unit of enablement. **Tool definitions
are pinned by hash: if an upstream MCP server changes a tool's name,
description or schema, it is treated as not-enabled until re-approved** —
without this, L3 approval is an approval of whatever the upstream happens
to serve at call time (the "rug pull" case). **Upstream tool descriptions
are untrusted input** and are **never forwarded to the model** — the
registry serves our own curated description, storing the upstream's for
diffing only, because a description injected into model context is a
direct prompt-injection channel from a third party. **Deny by default:**
discovery produces registry *candidates for review*, never live
capability. **Verified 2026-09-13 against OWASP LLM06:2025 (Excessive
Agency)**, whose three root causes (excessive functionality / permissions
/ autonomy) map one-for-one onto the layers, and whose mitigation 7 —
**complete mediation** — *"implement authorization in downstream systems rather than relying on an LLM to decide if an action is allowed"* —
is the whole argument for ADR-0007; also cross-checked against the **MCP
Security Best Practices** document, two of whose named attacks (**token
passthrough**, **stdio-in-proxy**) are already closed by ADR-0010/ADR-0019
and ADR-0070.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| Collapse L1 (catalogue) and L2 (platform policy) into a single layer | ❌ Rejected | The only way to forbid something globally would then be to delete the integration entirely, which also removes its safe read-only tools. |
| Policy granularity at the server level (enable/disable a whole MCP server) | ❌ Rejected | A server may mix safe read tools with dangerous write tools — enabling `grafana-mcp` must not enable its write set; ADR-0022's "minimum role across enabled tools" only makes sense if enablement is per tool. |
| Trust upstream tool descriptions and forward them to the model | ❌ Rejected | A description injected into model context is a direct prompt-injection channel from a third party; the registry instead serves its own curated description. |
| Treat upstream tool-definition changes as automatically still-approved | ❌ Rejected | Would let L3 approval silently cover whatever the upstream happens to serve at call time (the "rug pull" case); definitions are instead pinned by hash and re-reviewed on change. |
| Five-layer monotonically-narrowing lattice (L1–L5), effective capability = intersection | ✅ Chosen | Satisfies the kill-switch, per-Tenant, per-run and per-call narrowing requirements simultaneously, verified against OWASP LLM06:2025 and MCP Security Best Practices. |

## 4. Consequences

- **Positive —** a platform-wide kill switch (L2) is effective on
  in-flight runs at their next tool call, because L5 re-evaluates per
  call; the model never sees untrusted upstream tool descriptions.
- **Negative / accepted trade —** tool definitions pinned by hash means any
  upstream change to a tool's name, description or schema requires
  re-approval before it can be used again — an operational overhead
  compared to trusting upstream changes automatically.
- **Follow-on work —** the registry must store both the curated
  description (served to the model) and the upstream's original (for
  diffing) to detect rug-pull changes.
- **Revisit trigger —** none observed; verified against OWASP LLM06:2025
  and the MCP Security Best Practices document (see Verification).

## 5. Verification

- Verified 2026-09-13 against **OWASP LLM06:2025 (Excessive Agency)**: its three root causes (excessive functionality / permissions / autonomy) map one-for-one onto the five layers, and its mitigation 7 — complete mediation, "implement authorization in downstream systems rather than relying on an LLM to decide if an action is allowed" — is the whole argument for ADR-0007.
- Cross-checked against the **MCP Security Best Practices** document: two of its named attacks (token passthrough, stdio-in-proxy) are already closed by ADR-0010/ADR-0019 and ADR-0070 respectively.
