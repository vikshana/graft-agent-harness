---
id: ADR-0042
title: Idempotency is three-layered
status: accepted
date: 2026-09-12
deciders: []
category: agent
tags: [agent, orchestration, durability]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
design: ../../design/durable-execution.md
legacy_id: D42
---

# ADR-0042 — Idempotency is three-layered

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D42`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Idempotency is three-layered:** `workflow_id` (caller-supplied key) for **run creation**; `deduplication_id` on the queue for **trigger dedupe** (alert storms re-firing); `(graft_run_id, step_id, idempotency_key)` for **write side effects**, forwarded to the Tool Gateway and to upstream idempotency facilities where they exist. Must survive retry, reconnect **and replay-after-fork**. **Forked/eval runs are structurally read-only** — denied write tool classes by the same capability-token mechanism as ADR-0013 — because `fork_workflow` deliberately re-executes and would otherwise re-file a Jira ticket or re-open a PR when replaying an incident.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
