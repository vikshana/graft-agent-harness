---
id: ADR-0011
title: Downstream credentials are hybrid, service-identity by default
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
legacy_id: D11
---

# ADR-0011 — Downstream credentials are hybrid, service-identity by default

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D11`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

Downstream credential strategy is **hybrid, service-identity-by-default**: a workspace service account is always the fallback (required for `system_initiated` runs, ADR-0013, and for **all Slack-initiated runs**, ADR-0025); user identity is layered on top via **check-then-act** where a live Grafana request context exists. GitHub always acts as a **bot identity** (GitHub App), never impersonating the user. **The Grafana workspace service account authenticates via `Authorization: Bearer glsa_...`, confirmed against Grafana's own docs** — see ADR-0018's expanded note for how this credential moves through the Tool Gateway → `grafana-mcp` → Grafana hop chain.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
