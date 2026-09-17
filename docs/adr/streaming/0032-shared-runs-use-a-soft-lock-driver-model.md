---
id: ADR-0032
title: Shared runs use a soft-lock driver model
status: accepted
date: 2026-09-12
deciders: [ ]
category: streaming
tags: [ streaming, events ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ]
relates_to: [ ]
design: ../../design/streaming-and-events.md
legacy_id: D32
---

# ADR-0032 — Shared runs use a soft-lock driver model

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D32`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).

---

## 1. Context

ADR-0036 makes runs promotable to workspace-shared, which means multiple viewers can watch — and potentially want to
interact with — the same live run. A concurrency model was needed for who can steer/approve/cancel when several viewers
are present, and for what a new viewer sees when they join a run already in progress.

## 2. Decision

**Multi-viewer/shared live runs, v1 — soft-lock "driver" model**
(screen-share analogy): one viewer holds interactive control (steer/approve/cancel) at a time; other viewers are
read-only until they request control or the driver hands it off; a driver-disconnect fallback (auto-release or explicit
hand-off) is an implementation detail still to design. New viewers joining a shared run see the **live tail by
default**, with an explicit scroll-back/full-replay action backed by ADR-0030's Postgres log (replay is not the default
view). **Only activates once a run is explicitly promoted to workspace-shared** — see ADR-0036; a private (user-owned)
run has no multi-viewer concern.

## 3. Considered options

| Option                                                                                                                 | Verdict     | Why                                                                                                                                                                                      |
|------------------------------------------------------------------------------------------------------------------------|-------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Allow any viewer of a shared run to steer/approve/cancel concurrently                                                  | ❌ Rejected | The migrated register entry did not record a rejection rationale beyond the decision itself; concurrent uncoordinated control is an obvious source of conflicting actions on a live run. |
| Soft-lock "driver" model — one viewer holds interactive control at a time, others read-only until requested/handed off | ✅ Chosen   | Screen-share analogy familiar to users; only activates for workspace-shared runs, so private runs have no added complexity.                                                              |

## 4. Consequences

- **Positive —** only one viewer can act on a live run at a time, preventing conflicting concurrent actions; new viewers
  land on the live tail by default rather than an overwhelming full replay.
- **Negative / accepted trade —** a driver-disconnect fallback (auto-release vs. explicit hand-off) was left as an
  implementation detail still to design at the time of this decision — later resolved by ADR-0064 and ADR-0066.
- **Follow-on work —** full replay remains available as an explicit scroll-back action, backed by ADR-0030's Postgres
  event log.
- **Revisit trigger —** none observed; driver-disconnect handling was subsequently completed by ADR-0064/ADR-0066.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).
