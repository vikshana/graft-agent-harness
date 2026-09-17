---
id: ADR-0064
title: Shared-run control is one driver with explicit handover
status: accepted
date: 2026-09-13
deciders: [ ]
category: streaming
tags: [ streaming, events ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ADR-0065 ]
relates_to: [ ADR-0072, ADR-0032, ADR-0066 ]
design: ../../design/streaming-and-events.md
legacy_id: D64
---

# ADR-0064 — Shared-run control is one driver with explicit handover

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D64`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).

---

## 1. Context

ADR-0032 left the driver-disconnect fallback for shared runs as an implementation detail still to design, and left
run-list filtering and web-frontend Tenant resolution unspecified. Those gaps needed closing with a concrete, auditable
mechanism — while keeping control (who can steer/cancel a live run) and approval authority (who can confirm a write
action) as two conceptually separate questions.

## 2. Decision

**The "driving is not approving" clause is superseded 2026-09-13 by ADR-0065** — control now *is* approval authority,
and the two escape hatches are re-justified on new grounds in ADR-0066, which also replaces the bare "10 minutes" with
three named clocks. Run-list filters and web-frontend Tenant resolution stand unchanged. Original: **Shared-Run
interaction, Run list, and web-frontend Tenant resolution.** **One driver, everyone else watches, handover is
explicit** — confirming and completing ADR-0032's soft-lock. `viewer` can never drive (no `run:steer` verb, ADR-0056);
`responder` and `tenant_admin` may request control. **Two escape hatches stop a disconnected driver deadlocking a Run:
auto-release after 10 minutes of disconnect/idle, and `tenant_admin` force-release**, both audited — this **closes the
driver-disconnect item left open in the streaming deep-dive**. **Driving is not approving:** approval stays
initiator-only (ADR-0055), so neither handover nor force-release ever transfers approval authority — which is precisely
what makes the escape hatches safe. **Run list filters are "Mine" and "Tenant"** — deliberately *not* the originally
proposed "mine / my team / all", because there is no
"my team" (Group is not a scoping layer, ADR-0051) and no "all"
(cross-Tenant listing does not exist, ADR-0051). **Sharing remains irreversible** (ADR-0054, confirmed). **Web
frontend (post-v1, ADR-0002):
Tenant resolution is OIDC/SSO against the existing `graft_external_ref`
mapping** (ADR-0060) — an explicit Tenant switcher seeded from the Principal's `default_graft_tenant_id`, active Tenant
carried in the harness token exactly as every other surface. No new resolution mechanism is invented for it.

## 3. Considered options

| Option                                                                                                             | Verdict     | Why                                                                                                                                                                                             |
|--------------------------------------------------------------------------------------------------------------------|-------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Leave the driver-disconnect fallback undesigned (as ADR-0032 left it)                                              | ❌ Rejected | Deadlocks a shared run if the driver disconnects and never returns; needed a concrete, audited resolution.                                                                                      |
| Two escape hatches — auto-release after 10 minutes disconnect/idle, and `tenant_admin` force-release, both audited | ✅ Chosen   | Closes the driver-disconnect gap without ever transferring approval authority, since driving and approving are kept separate (at the time of this decision; later superseded by ADR-0065).      |
| Originally proposed "mine / my team / all" run-list filters                                                        | ❌ Rejected | There is no "my team" (Group is not a scoping layer, ADR-0051) and no "all" (cross-Tenant listing does not exist, ADR-0051) — both options describe scopes that don't exist in the scope model. |
| "Mine" and "Tenant" run-list filters                                                                               | ✅ Chosen   | The only two scopes that actually exist under ADR-0051's collapsed scope model.                                                                                                                 |

## 4. Consequences

- **Positive —** the driver-disconnect gap left open by ADR-0032 is closed with two audited escape hatches; run-list
  filters match the scopes that actually exist.
- **Negative / accepted trade —** this ADR's central "driving is not approving" clause was subsequently superseded by
  ADR-0065 — control now *is* approval authority, re-justifying the same two escape hatches on new grounds via ADR-0066.
- **Follow-on work —** web-frontend Tenant resolution reuses the existing
  `graft_external_ref` mapping (ADR-0060) rather than inventing a new resolution mechanism; split out into ADR-0072
  during the 2026-09-13 ADR migration since the run-list/Tenant-resolution clauses were never about run control.
- **Revisit trigger —** none observed beyond the already-completed ADR-0065 supersession.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).
