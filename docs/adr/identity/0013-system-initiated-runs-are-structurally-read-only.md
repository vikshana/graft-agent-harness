---
id: ADR-0013
title: system_initiated runs are structurally read-only
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
legacy_id: D13
---

# ADR-0013 — system_initiated runs are structurally read-only

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D13`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**`system_initiated` runs (no human present) are structurally read-only.** Enforced by the run's capability token never containing a write tool class — not by a policy check that could be bypassed. A human approving a proposal upgrades the run to `user_initiated` from that point.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
