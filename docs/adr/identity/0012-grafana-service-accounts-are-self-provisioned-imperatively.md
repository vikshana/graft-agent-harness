---
id: ADR-0012
title: Grafana service accounts are self-provisioned imperatively
status: accepted
date: 2026-09-12
deciders: []
category: identity
tags: [identity, authn, authz]
supersedes: []
superseded_by: []
amends: []
amended_by: [ADR-0022]
relates_to: []
design: ../../design/external-identity-mapping.md
legacy_id: D12
---

# ADR-0012 — Grafana service accounts are self-provisioned imperatively

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D12`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Grafana-side service accounts are self-provisioned imperatively**, using a platform-level Grafana Server Admin credential — **not** a customer admin's session (superseded by ADR-0021/ADR-0022), and never via `externalServiceAccounts`, confirmed broken for multi-org Grafana. One mechanism covers both the plugin's own enforcement SA and the `grafana-mcp` tool server's SA. Tokens always carry an expiry; role is recomputed to the minimum needed across enabled tools on every policy change.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
