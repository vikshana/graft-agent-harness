---
id: ADR-0022
title: Grafana service accounts are provisioned synchronously at Tenant creation
status: accepted
date: 2026-09-12
deciders: []
category: identity
tags: [identity, authn, authz]
supersedes: []
superseded_by: []
amends: [ADR-0012]
amended_by: []
relates_to: []
design: ../../design/external-identity-mapping.md
legacy_id: D22
---

# ADR-0022 — Grafana service accounts are provisioned synchronously at Tenant creation

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D22`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Both Grafana service accounts (plugin enforcement SA, `grafana-mcp` SA) are provisioned synchronously at workspace/org creation**, using a platform-level Grafana Server Admin credential. No cold-start gap exists — provisioning is a precondition of a workspace being marked ready, never lazy/first-use. Disabling the Grafana MCP server **fully deprovisions** its SA and token (delete, not downgrade); disabling one tool within an enabled server **recomputes the SA's role to the minimum required**.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
