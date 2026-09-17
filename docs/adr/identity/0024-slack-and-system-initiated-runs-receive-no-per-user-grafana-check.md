---
id: ADR-0024
title: Slack and system_initiated runs receive no per-user Grafana check
status: accepted
date: 2026-09-12
deciders: [ ]
category: identity
tags: [ identity, authn, authz ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ]
relates_to: [ ]
design: ../../design/external-identity-mapping.md
legacy_id: D24
---

# ADR-0024 — Slack and system_initiated runs receive no per-user Grafana check

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D24`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

Slack-initiated and `system_initiated` runs have no live Grafana request context to check a per-user permission against,
unlike `user_initiated` runs from the Grafana plugin (ADR-0011). Building the more accurate alternative — resolving the
linked user and checking their permission out of band — is real engineering work, and a call was needed on whether to
build it for v1 or accept the coarser workspace-service-account ceiling.

## 2. Decision

**Slack-initiated and `system_initiated` runs never receive a per-user Grafana permission check** — both are bounded
solely by the workspace service account's own role. Deliberately the simpler path for v1; revisit once PoC usage data
justifies the added complexity of per-user checks for Slack. **The candidate revisit metric is accepted (2026-09-12,
product decision):** track denials where a Slack-triggered action would have succeeded under the linked user's actual
Grafana role but failed at the workspace SA's role; revisit this decision if that rate crosses an agreed threshold or a
customer explicitly raises it.

## 3. Considered options

| Option                                                                                                         | Verdict              | Why                                                                                                                                |
|----------------------------------------------------------------------------------------------------------------|----------------------|------------------------------------------------------------------------------------------------------------------------------------|
| No per-user check for Slack/`system_initiated`; always evaluate at the workspace service account's ceiling     | ✅ Chosen            | Simpler for v1, one enforcement path for surfaces with no live request context; explicitly deferred rather than declared permanent |
| Resolve the linked Principal and check their actual Grafana permission out of band for Slack-initiated actions | ❌ Rejected (for v1) | Real additional complexity — no live request context to check against — not justified before usage data shows it matters           |

## 4. Consequences

- **Positive —** one simple enforcement path for every surface with no live Grafana request context, instead of a
  bespoke out-of-band resolution mechanism built ahead of need.
- **Negative / accepted trade —** a Slack-triggered action is authorised only by the workspace SA's role, which is
  coarser than the linked user's real Grafana permissions could allow — the SA's role effectively **is**
  the access-control boundary for the Slack surface.
- **Follow-on work —** instrument the accepted revisit metric (see Verification).
- **Revisit trigger —** the tracked denial rate (see Verification) crosses an agreed threshold, or a customer explicitly
  raises it.

## 5. Verification

- The revisit metric itself was accepted 2026-09-12 as a product decision, not a live-source verification: track denials
  where a Slack-triggered action would have succeeded under the linked user's actual Grafana role but failed at the
  workspace SA's role. Mechanism:
  [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md)
  and
  [`../../design/grafana-authz-delegation.md`](../../design/grafana-authz-delegation.md)
  section 3.6.

