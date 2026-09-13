---
id: ADR-0064
title: Shared-run control is one driver with explicit handover
status: accepted
date: 2026-09-13
deciders: []
category: streaming
tags: [streaming, events]
supersedes: []
superseded_by: []
amends: []
amended_by: [ADR-0065]
relates_to: [ADR-0072, ADR-0032, ADR-0066]
design: ../../design/streaming-and-events.md
legacy_id: D64
---

# ADR-0064 — Shared-run control is one driver with explicit handover

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D64`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**The "driving is not approving" clause is superseded 2026-09-13 by ADR-0065** — control now *is* approval authority, and the two escape hatches are re-justified on new grounds in ADR-0066, which also replaces the bare "10 minutes" with three named clocks. Run-list filters and web-frontend Tenant resolution stand unchanged. Original: **Shared-Run interaction, Run list, and web-frontend Tenant resolution.** **One driver, everyone else watches, handover is explicit** — confirming and completing ADR-0032's soft-lock. `viewer` can never drive (no `run:steer` verb, ADR-0056); `responder` and `tenant_admin` may request control. **Two escape hatches stop a disconnected driver deadlocking a Run: auto-release after 10 minutes of disconnect/idle, and `tenant_admin` force-release**, both audited — this **closes the driver-disconnect item left open in the streaming deep-dive**. **Driving is not approving:** approval stays initiator-only (ADR-0055), so neither handover nor force-release ever transfers approval authority — which is precisely what makes the escape hatches safe. **Run list filters are “Mine” and “Tenant”** — deliberately *not* the originally proposed “mine / my team / all”, because there is no “my team” (Group is not a scoping layer, ADR-0051) and no “all” (cross-Tenant listing does not exist, ADR-0051). **Sharing remains irreversible** (ADR-0054, confirmed). **Web frontend (post-v1, ADR-0002): Tenant resolution is OIDC/SSO against the existing `graft_external_ref` mapping** (ADR-0060) — an explicit Tenant switcher seeded from the Principal's `default_graft_tenant_id`, active Tenant carried in the harness token exactly as every other surface. No new resolution mechanism is invented for it.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
