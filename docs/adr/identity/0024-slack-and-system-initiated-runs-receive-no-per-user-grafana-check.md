---
id: ADR-0024
title: Slack and system_initiated runs receive no per-user Grafana check
status: accepted
date: 2026-09-12
deciders: []
category: identity
tags: [identity, authn, authz]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
design: ../../design/external-identity-mapping.md
legacy_id: D24
---

# ADR-0024 — Slack and system_initiated runs receive no per-user Grafana check

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D24`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Slack-initiated and `system_initiated` runs never receive a per-user Grafana permission check** — both are bounded solely by the workspace service account's own role. Deliberately the simpler path for v1; revisit once PoC usage data justifies the added complexity of per-user checks for Slack. **The candidate revisit metric is accepted (2026-09-12, product decision):** track denials where a Slack-triggered action would have succeeded under the linked user's actual Grafana role but failed at the workspace SA's role; revisit this decision if that rate crosses an agreed threshold or a customer explicitly raises it.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
