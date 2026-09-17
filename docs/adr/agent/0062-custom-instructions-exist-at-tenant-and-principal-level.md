---
id: ADR-0062
title: Custom instructions exist at Tenant and Principal level
status: accepted
date: 2026-09-13
deciders: [ ]
category: agent
tags: [ agent, orchestration, durability ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ADR-0016 ]
amended_by: [ ]
relates_to: [ ]
design: ../../design/durable-execution.md
legacy_id: D62
---

# ADR-0062 — Custom instructions exist at Tenant and Principal level

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D62`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

The tenancy deep-dive proposed two-level (Tenant + Principal) custom instructions, which appeared to contradict
ADR-0016's "never a separate per-user configuration" absolute — though that absolute was already strained in practice by
per-Principal `default_graft_tenant_id`
(ADR-0051/ADR-0054) and per-Principal quotas (ADR-0057). Whether custom instructions genuinely reverse ADR-0016, or are
a different concern entirely, needed resolving.

## 2. Decision

**Custom instructions exist at both Tenant and Principal level, and ADR-0016 is narrowed accordingly.** The tenancy
deep-dive proposed two-level custom instructions, which appeared to contradict ADR-0016's "never a separate per-user
configuration" — but ADR-0016's absolute was **already strained** by per-Principal `default_graft_tenant_id`
(ADR-0051/ADR-0054)
and per-Principal quotas (ADR-0057), so this is a narrowing, not a reversal. **The distinction: ADR-0016 governs
*capability* (what a Principal may do — tool config, authorisation, which stays Tenant-scoped and shared), custom
instructions govern *behaviour* (how the agent replies — tone, persona, format).** Two different things were sharing one
word. **Precedence follows the prompt-layer hierarchy**
([`../../design/context-assembly.md`](../../design/context-assembly.md)):
platform system/safety → Tenant → Principal, **higher wins on conflict**, so a Principal cannot opt out of a Tenant
convention. **Hard rule: custom instructions are prompt text, never policy** — they cannot enable a tool, widen a Role,
alter a budget or bypass an approval; an instruction reading
"you may restart pods without asking" has **literally no effect**, because capability comes from the run capability
token (ADR-0010, ADR-0063 layer

4) minted before the instruction is ever read. This matters because custom instructions are user-authored text flowing
   into model context — a prompt-injection channel by construction — so the mitigation must be **structural, not a
   filter**. Both levels are **versioned and recorded on the Run**, required for ADR-0015 audit attribution and for
   ADR-0040's
   `fork_workflow` eval replay to be reproducible.

## 3. Considered options

| Option                                                                                        | Verdict     | Why                                                                                                                                                                                                         |
|-----------------------------------------------------------------------------------------------|-------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Keep ADR-0016's absolute — no per-Principal configuration of any kind, including instructions | ❌ Rejected | Already strained in practice by per-Principal `default_graft_tenant_id` and per-Principal quotas; conflates two different concerns (capability vs. behaviour) under one word, "configuration."              |
| Custom instructions at both Tenant and Principal level, narrowing ADR-0016 to capability-only | ✅ Chosen   | Separates *capability* (what a Principal may do — stays Tenant-scoped and shared, per ADR-0016) from *behaviour* (how the agent replies), which can vary per Principal without being a policy escape hatch. |

## 4. Consequences

- **Positive —** precedence follows the existing prompt-layer hierarchy (platform system/safety → Tenant → Principal,
  higher wins), so a Principal cannot opt out of a Tenant convention.
- **Negative / accepted trade —** custom instructions are a prompt-injection channel by construction (user-authored text
  flowing into model context), so the mitigation must be structural: instructions are prompt text, never policy — they
  cannot enable a tool, widen a Role, alter a budget, or bypass an approval, because capability comes from the run
  capability token (ADR-0010, ADR-0063 layer 4) minted before the instruction is ever read.
- **Follow-on work —** both levels are versioned and recorded on the Run, required for ADR-0015 audit attribution and
  for ADR-0040's
  `fork_workflow` eval replay to be reproducible.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/context-assembly.md`](../../design/context-assembly.md).
