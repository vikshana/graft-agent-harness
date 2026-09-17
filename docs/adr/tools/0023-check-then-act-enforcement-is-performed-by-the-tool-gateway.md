---
id: ADR-0023
title: Check-then-act enforcement is performed by the Tool Gateway
status: accepted
date: 2026-09-12
deciders: []
category: tools
tags: [tools, mcp, authority]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
design: ../../design/tool-registry-and-authority.md
legacy_id: D23
---

# ADR-0023 — Check-then-act enforcement is performed by the Tool Gateway

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D23`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/tool-registry-and-authority.md`](../../design/tool-registry-and-authority.md).

---

## 1. Context

Some tool calls need a "check-then-act" pattern — verifying a precondition
(e.g. current access-control state) before performing an action. That
check could be trusted from an assertion made by the Grafana plugin
backend, or performed independently by the component that actually enforces
tool authority.

## 2. Decision

**Check-then-act enforcement is performed by the Tool Gateway itself**,
never delegated to the Grafana plugin backend's assertion.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| Trust the Grafana plugin backend's assertion of the precondition | ❌ Rejected | Delegating the check to a caller's own assertion is exactly the confused-deputy pattern the Tool Gateway exists to avoid (ADR-0007); the plugin backend is not the enforcement point. |
| Tool Gateway performs the check itself, independently, before acting | ✅ Chosen | Keeps enforcement at the one place that is the actual security boundary, consistent with ADR-0007's rationale for a separate Tool Gateway. |

## 4. Consequences

- **Positive —** the check-then-act guarantee holds regardless of what any
  upstream caller asserts, preserving the confused-deputy protection
  ADR-0007 and ADR-0069 depend on.
- **Negative / accepted trade —** the Tool Gateway must have (or fetch) the
  information needed to perform the check itself, rather than trusting a
  caller-supplied assertion.
- **Follow-on work —** none recorded beyond the enforcement placement
  itself.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original
  register entry was marked "verified live" for this decision. Mechanism:
  [`../../design/tool-registry-and-authority.md`](../../design/tool-registry-and-authority.md).
