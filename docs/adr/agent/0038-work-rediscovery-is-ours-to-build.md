---
id: ADR-0038
title: Work rediscovery is ours to build
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
legacy_id: D38
---

# ADR-0038 — Work rediscovery is ours to build

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D38`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Work rediscovery is ours to build — ~150 lines, not a durable engine.** Because Conductor is excluded, distributed recovery is **`executor_id`-pinned**: a dead pod's workflows recover only when a pod with that same executor ID restarts. Design: workers are a **StatefulSet** with executor IDs carrying pod ordinal **and deploy colour** (`blue-0`, `green-0`, per ADR-0046); each worker heartbeats `(executor_id, app_version, last_seen_at)` to a table we own; a **version-aware reaper** (itself a scheduled DBOS workflow) resumes `PENDING` workflows whose executor's heartbeat is stale, onto a live worker **of the matching version**. All runs are **enqueued, never started in-process**, confining the exposure window to genuinely in-flight runs.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
