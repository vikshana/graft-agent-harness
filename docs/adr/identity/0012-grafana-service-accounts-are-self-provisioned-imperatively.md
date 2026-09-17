---
id: ADR-0012
title: Grafana service accounts are self-provisioned imperatively
status: accepted
date: 2026-09-12
deciders: [ ]
category: identity
tags: [ identity, authn, authz ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ADR-0022 ]
relates_to: [ ]
design: ../../design/external-identity-mapping.md
legacy_id: D12
---

# ADR-0012 — Grafana service accounts are self-provisioned imperatively

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D12`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

Two Grafana-side service accounts need to exist — the plugin's own enforcement SA and the `grafana-mcp` tool server's
SA — and something has to create them. Grafana's declarative `externalServiceAccounts` mechanism was a candidate, as was
provisioning through whichever customer admin happened to be present at setup time; both had to be weighed against a
mechanism the platform itself controls end to end.

## 2. Decision

**Grafana-side service accounts are self-provisioned imperatively**, using a platform-level Grafana Server Admin
credential — **not** a customer admin's session (superseded by ADR-0021/ADR-0022), and never via
`externalServiceAccounts`, confirmed broken for multi-org Grafana. One mechanism covers both the plugin's own
enforcement SA and the `grafana-mcp` tool server's SA. Tokens always carry an expiry; role is recomputed to the minimum
needed across enabled tools on every policy change.

## 3. Considered options

| Option                                                                             | Verdict     | Why                                                                                                                                                                    |
|------------------------------------------------------------------------------------|-------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Self-provision imperatively using a platform-level Grafana Server Admin credential | ✅ Chosen   | One mechanism for both SAs, controlled entirely by the platform; not dependent on any customer's session or standing rights                                            |
| Provision using a customer admin's own session/credential at setup time            | ❌ Rejected | Ephemeral and dependent on a specific admin being present and willing; superseded in timing by ADR-0022 once the platform was confirmed to own the instance (ADR-0021) |
| Grafana's declarative `externalServiceAccounts` feature                            | ❌ Rejected | Confirmed broken in multi-org Grafana deployments (per a Grafana maintainer), which is exactly the platform's topology                                                 |

## 4. Consequences

- **Positive —** one mechanism covers both SAs; token role is recomputed to the minimum needed across enabled tools on
  every policy change, rather than drifting to the broadest role ever granted.
- **Negative / accepted trade —** the platform must hold and protect a powerful Server Admin credential per Grafana
  instance, since that credential can provision an SA of any privilege.
- **Follow-on work —** the *timing* of provisioning (synchronous at Tenant creation vs. lazy) is specified separately in
  ADR-0022.
- **Revisit trigger —** Grafana's declarative service-account mechanism becoming multi-org-safe.

## 5. Verification

- Not separately verified against a live source beyond confirming
  `externalServiceAccounts`'s multi-org breakage (see ADR-0026's verification for the related OSS/Enterprise RBAC
  finding). Mechanism:
  [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

