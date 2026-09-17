---
id: ADR-0019
title: The MCP Authorization Server is logically distinct from the Tool Gateway
status: accepted
date: 2026-09-12
deciders: [ ]
category: identity
tags: [ identity, authn, authz ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ]
relates_to: [ ADR-0069 ]
design: ../../design/external-identity-mapping.md
legacy_id: D19
---

# ADR-0019 — The MCP Authorization Server is logically distinct from the Tool Gateway

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D19`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

The agent → Tool Gateway hop needs an OAuth token issuer. The Tool Gateway's job is to be a resource server —
authorising and routing tool calls — and mixing token issuance into the same component blurs a boundary OAuth is built
to keep separate. Slack and webhook surfaces also have no IdP session to hand the Gateway directly, so whatever issues
the token needs to sit in front of the pluggable customer IdP and mint harness-specific claims.

## 2. Decision

**The MCP Authorization Server (AS) is a distinct logical component from the Tool Gateway**, which is a Resource Server
only — it never issues tokens, only validates them, always independently. The AS is **harness-owned** (a broker in front
of the pluggable IdP, since Slack/webhook surfaces have no IdP session and the token needs harness-specific claims).
Deployed **co-located with the harness API** in v1. Applies only to the **agent → Tool Gateway** hop.

## 3. Considered options

| Option                                                                                                       | Verdict     | Why                                                                                                                                                                                    |
|--------------------------------------------------------------------------------------------------------------|-------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A logically distinct MCP Authorization Server, harness-owned, deployed co-located with the harness API in v1 | ✅ Chosen   | Keeps the Tool Gateway a pure resource server that only validates tokens, independently, every time; the AS can broker harness-specific claims for surfaces with no IdP session        |
| Fold token issuance into the Tool Gateway itself                                                             | ❌ Rejected | Mixes resource-server and authorisation-server roles in one component, which is the exact separation OAuth's RS/AS split exists to avoid, and complicates independent token validation |
| Delegate directly to the customer's IdP with no harness-owned broker                                         | ❌ Rejected | Slack and webhook-triggered runs have no IdP session at all, and the token needs harness-specific claims (run scope, capability) that a generic customer IdP does not issue            |

## 4. Consequences

- **Positive —** the Tool Gateway stays a pure resource server, validating every token independently regardless of which
  surface produced it.
- **Negative / accepted trade —** an additional component must be operated; mitigated in v1 by co-locating it with the
  harness API rather than standing up a separate deployment.
- **Follow-on work —** relates to ADR-0069, which folds the Token Service, Tool Gateway and Registry into one Authority
  Service.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

