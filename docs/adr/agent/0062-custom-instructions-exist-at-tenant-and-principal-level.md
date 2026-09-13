---
id: ADR-0062
title: Custom instructions exist at Tenant and Principal level
status: accepted
date: 2026-09-13
deciders: []
category: agent
tags: [agent, orchestration, durability]
supersedes: []
superseded_by: []
amends: [ADR-0016]
amended_by: []
relates_to: []
design: ../../design/durable-execution.md
legacy_id: D62
---

# ADR-0062 — Custom instructions exist at Tenant and Principal level

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D62`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Custom instructions exist at both Tenant and Principal level, and ADR-0016 is narrowed accordingly.** The tenancy deep-dive proposed two-level custom instructions, which appeared to contradict ADR-0016's “never a separate per-user configuration” — but ADR-0016's absolute was **already strained** by per-Principal `default_graft_tenant_id` (ADR-0051/ADR-0054) and per-Principal quotas (ADR-0057), so this is a narrowing, not a reversal. **The distinction: ADR-0016 governs *capability* (what a Principal may do — tool config, authorisation, which stays Tenant-scoped and shared), custom instructions govern *behaviour* (how the agent replies — tone, persona, format).** Two different things were sharing one word. **Precedence follows the prompt-layer hierarchy** ([`../../design/context-assembly.md`](../../design/context-assembly.md)): platform system/safety → Tenant → Principal, **higher wins on conflict**, so a Principal cannot opt out of a Tenant convention. **Hard rule: custom instructions are prompt text, never policy** — they cannot enable a tool, widen a Role, alter a budget or bypass an approval; an instruction reading “you may restart pods without asking” has **literally no effect**, because capability comes from the run capability token (ADR-0010, ADR-0063 layer 4) minted before the instruction is ever read. This matters because custom instructions are user-authored text flowing into model context — a prompt-injection channel by construction — so the mitigation must be **structural, not a filter**. Both levels are **versioned and recorded on the Run**, required for ADR-0015 audit attribution and for ADR-0040's `fork_workflow` eval replay to be reproducible.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
