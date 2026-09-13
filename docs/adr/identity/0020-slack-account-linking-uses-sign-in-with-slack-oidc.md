---
id: ADR-0020
title: Slack account linking uses Sign in with Slack (OIDC)
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
legacy_id: D20
---

# ADR-0020 — Slack account linking uses Sign in with Slack (OIDC)

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D20`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Slack account linking (A3) uses "Sign in with Slack" (OpenID Connect)** rather than a bespoke OAuth flow. Strengthens the one-time link step only; does not change ADR-0014. **Verified live against `docs.slack.dev`, 2026-09-12** — OIDC flow, scopes, and endpoints confirmed as described.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
