---
id: ADR-0022
title: Grafana service accounts are provisioned synchronously at Tenant creation
status: accepted
date: 2026-09-12
deciders: [ ]
category: identity
tags: [ identity, authn, authz ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ADR-0012 ]
amended_by: [ ]
relates_to: [ ]
design: ../../design/external-identity-mapping.md
legacy_id: D22
---

# ADR-0022 — Grafana service accounts are provisioned synchronously at Tenant creation

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D22`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

ADR-0012 fixed *how* the two Grafana service accounts are created (platform Server Admin credential, one mechanism for
both), but not *when*. Provisioning could happen lazily on first use, as a background step some time after a workspace
is created, or synchronously as part of creation itself — and the choice determines whether a cold-start gap can exist
where a workspace looks ready but its SAs do not yet.

## 2. Decision

**Both Grafana service accounts (plugin enforcement SA, `grafana-mcp` SA) are provisioned synchronously at workspace/org
creation**, using a platform-level Grafana Server Admin credential. No cold-start gap exists — provisioning is a
precondition of a workspace being marked ready, never lazy/first-use. Disabling the Grafana MCP server **fully
deprovisions** its SA and token (delete, not downgrade); disabling one tool within an enabled server **recomputes the
SA's role to the minimum required**.

## 3. Considered options

| Option                                                                                   | Verdict     | Why                                                                                                                                                         |
|------------------------------------------------------------------------------------------|-------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Provision both SAs synchronously at workspace/org creation, as a precondition of "ready" | ✅ Chosen   | No cold-start gap: a workspace is never marked ready while its SAs are still pending                                                                        |
| Lazy, first-use provisioning                                                             | ❌ Rejected | Creates a race between "workspace looks usable" and "SA actually exists", and pushes provisioning failures into the first real user action instead of setup |
| Asynchronous provisioning as a separate step after creation completes                    | ❌ Rejected | A workspace could still be marked ready before its SAs exist, reopening the same gap by a different route                                                   |

## 4. Consequences

- **Positive —** provisioning is a precondition of the `ready` lifecycle state (ADR-0053), so the race this decision
  closes cannot reopen through a lifecycle bug.
- **Negative / accepted trade —** Tenant creation is slower and has more failure modes that must be handled atomically
  (a partially provisioned Tenant must not become `ready`).
- **Follow-on work —** disabling the Grafana MCP server fully deprovisions its SA and token (delete, not downgrade);
  disabling one tool within an enabled server recomputes the SA's role to the minimum still required.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

