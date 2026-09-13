---
id: ADR-0014
title: Approval is a re-authenticated human act that happens in Grafana
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
legacy_id: D14
---

# ADR-0014 — Approval is a re-authenticated human act that happens in Grafana

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D14`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Approval is a distinct, human, re-authenticated act that always happens in Grafana**, never in Slack. Slack may trigger, converse, and *launch* an approval via a signed single-use deep link, but never perform it. **Confirmed to hold regardless of Slack platform evolution**: no Slack platform mechanism, including newer ones (ADR-0020), provides a per-action re-authentication primitive equivalent to a fresh signed assertion at decision time. Slack's own AI-agent governance guidance (verified live against `docs.slack.dev`, 2026-09-12) treats "approval gates" as a UX pattern, not a re-authentication mechanism — reinforcing, not weakening, this decision.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
