---
id: ADR-0019
title: The MCP Authorization Server is logically distinct from the Tool Gateway
status: accepted
date: 2026-09-12
deciders: []
category: identity
tags: [identity, authn, authz]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: [ADR-0069]
design: ../../design/external-identity-mapping.md
legacy_id: D19
---

# ADR-0019 — The MCP Authorization Server is logically distinct from the Tool Gateway

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D19`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**The MCP Authorization Server (AS) is a distinct logical component from the Tool Gateway**, which is a Resource Server only — it never issues tokens, only validates them, always independently. The AS is **harness-owned** (a broker in front of the pluggable IdP, since Slack/webhook surfaces have no IdP session and the token needs harness-specific claims). Deployed **co-located with the harness API** in v1. Applies only to the **agent → Tool Gateway** hop.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
