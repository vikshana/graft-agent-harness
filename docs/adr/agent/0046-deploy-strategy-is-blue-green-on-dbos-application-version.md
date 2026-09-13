---
id: ADR-0046
title: Deploy strategy is blue/green on DBOS application version
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
legacy_id: D46
---

# ADR-0046 — Deploy strategy is blue/green on DBOS application version

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D46`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Deploy strategy is blue/green with DBOS's auto-computed application version.** A DBOS application version defaults to a **hash of workflow source code**; every workflow is tagged with the version it started on, and **recovery only matches like versions**. We deliberately **do not** pin `application_version` to a git SHA or image tag — that would force a full drain on every deploy, including prompt-only changes; the auto-hash changes only when *what steps run, or in what order* changes, which is exactly when draining is required. In-flight runs finish on their original version (confirmed as the desired behaviour, 2026-09-12). New work is enqueued pinned to the latest version via `get_latest_application_version()`; scheduled workflows target the latest version automatically. **Colour retirement is gated in the deploy pipeline on `list_workflows(app_version=…, status=["ENQUEUED","PENDING"])` returning empty** — a machine check, not a human eyeball. `DBOS.patch()`/`deprecate_patch()` is the documented escape hatch for urgent fixes that must reach already-running investigations, not the default.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
