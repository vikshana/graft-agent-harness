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

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**No arbitrary code execution in v1.** Read-only tools + server-side result reduction. Sandbox deferred to Phase 2.

### 2.4a — folded from legacy `D4a`

A `ToolExecutor` / sandbox seam must exist in v1 so Phase 2 adds micro-VM execution without a rewrite.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
