---
id: ADR-0032
title: Shared runs use a soft-lock driver model
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
legacy_id: D32
---

# ADR-0032 — Shared runs use a soft-lock driver model

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D32`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Multi-viewer/shared live runs, v1 — soft-lock "driver" model** (screen-share analogy): one viewer holds interactive control (steer/approve/cancel) at a time; other viewers are read-only until they request control or the driver hands it off; a driver-disconnect fallback (auto-release or explicit hand-off) is an implementation detail still to design. New viewers joining a shared run see the **live tail by default**, with an explicit scroll-back/full-replay action backed by ADR-0030's Postgres log (replay is not the default view). **Only activates once a run is explicitly promoted to workspace-shared** — see ADR-0036; a private (user-owned) run has no multi-viewer concern.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
