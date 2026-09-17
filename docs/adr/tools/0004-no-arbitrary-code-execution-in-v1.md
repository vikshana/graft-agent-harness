---
id: ADR-0004
title: No arbitrary code execution in v1
status: accepted
date: 2026-09-12
deciders: []
category: tools
tags: [tools, mcp, authority]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: [ADR-0007]
design: ../../design/tool-registry-and-authority.md
legacy_id: D4
---

# ADR-0004 — No arbitrary code execution in v1

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D4`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/tool-registry-and-authority.md`](../../design/tool-registry-and-authority.md).

---

## 1. Context

Investigations often benefit from ad-hoc code (e.g. a quick data-shaping
script over a large result set), but arbitrary code execution is a large
security surface — sandboxing (micro-VMs, gVisor, etc.) is real
infrastructure work that was not ready for v1. A decision was needed on
whether to build that sandbox now, defer it, or design so it can be added
later without a rewrite.

## 2. Decision

**No arbitrary code execution in v1.** Read-only tools + server-side
result reduction. Sandbox deferred to Phase 2.

### 2.4a — folded from legacy `D4a`

A `ToolExecutor` / sandbox seam must exist in v1 so Phase 2 adds micro-VM
execution without a rewrite.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| Build sandboxed arbitrary code execution (micro-VM) for v1 | ❌ Rejected | Real infrastructure work not ready for v1; not required if read-only tools plus server-side result reduction cover the actual use cases. |
| No arbitrary code execution in v1; read-only tools + server-side result reduction, with a `ToolExecutor`/sandbox seam reserved for Phase 2 | ✅ Chosen | Avoids building sandbox infrastructure before it's needed, while the reserved seam means Phase 2 can add micro-VM execution without a rewrite. |

## 4. Consequences

- **Positive —** avoids building and securing sandbox infrastructure before
  it is actually needed; server-side result reduction covers much of the
  "shape this data" use case without code execution.
- **Negative / accepted trade —** investigations that would genuinely
  benefit from ad-hoc code (e.g. custom data transforms) cannot do so in
  v1.
- **Follow-on work —** the `ToolExecutor`/sandbox seam must exist in v1's
  architecture even though nothing plugs into it yet, so Phase 2 does not
  require a rewrite.
- **Revisit trigger —** Phase 2 sandbox work (micro-VM execution).

## 5. Verification

- Not separately verified against a live source; no claim in the original
  register entry was marked "verified live" for this decision. Mechanism:
  [`../../design/tool-registry-and-authority.md`](../../design/tool-registry-and-authority.md).
