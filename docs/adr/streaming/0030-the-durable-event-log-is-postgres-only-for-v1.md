---
id: ADR-0030
title: The durable event log is Postgres-only for v1
status: accepted
date: 2026-09-12
deciders: []
category: streaming
tags: [streaming, events]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
design: ../../design/streaming-and-events.md
legacy_id: D30
---

# ADR-0030 — The durable event log is Postgres-only for v1

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D30`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Durable event log is Postgres-only for v1 — no Redis.** One event table (`graft_run_id`, monotonic `graft_event_id`, `event_type`, `event_version`, `payload JSONB`, `created_at`); fan-out via `LISTEN/NOTIFY` (payload carries `graft_run_id:graft_event_id`, listener re-reads the row — avoids the 8KB NOTIFY size ceiling); replay via an indexed range query on `graft_event_id`. Chosen over the initially-proposed Redis-Streams-hot + Postgres-archive split because Postgres alone gives transactional consistency with run state (single writer, no dual-write risk) and needs no trimming/retention/hot-cold-fallback design at our expected scale. Large raw tool artifacts live in object storage, referenced by event payload, never inlined. Revisit only if real `LISTEN/NOTIFY` connection-scaling or event-rate limits are hit in production.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
