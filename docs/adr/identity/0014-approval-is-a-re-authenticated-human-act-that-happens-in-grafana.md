---
id: ADR-0014
title: Approval is a re-authenticated human act that happens in Grafana
status: accepted
date: 2026-09-12
deciders: [ ]
category: identity
tags: [ identity, authn, authz ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ]
relates_to: [ ]
design: ../../design/external-identity-mapping.md
legacy_id: D14
---

# ADR-0014 — Approval is a re-authenticated human act that happens in Grafana

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D14`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

A `system_initiated` run's write proposal (ADR-0013) needs a way to become an authorised, attributable write, and it
must be a channel-agnostic act — Slack is a primary trigger surface (ADR-0002) but is not itself an authentication
boundary. A mechanism was needed that could not be spoofed by anyone with access to the Slack channel, and that survives
however Slack's own agent-governance features evolve.

## 2. Decision

**Approval is a distinct, human, re-authenticated act that always happens in Grafana**, never in Slack. Slack may
trigger, converse, and *launch* an approval via a signed single-use deep link, but never perform it. **Confirmed to hold
regardless of Slack platform evolution**: no Slack platform mechanism, including newer ones (ADR-0020), provides a
per-action re-authentication primitive equivalent to a fresh signed assertion at decision time. Slack's own AI-agent
governance guidance (verified live against `docs.slack.dev`, 2026-09-12) treats "approval gates" as a UX pattern, not a
re-authentication mechanism — reinforcing, not weakening, this decision.

## 3. Considered options

| Option                                                                                                                                | Verdict     | Why                                                                                                                                                                                                   |
|---------------------------------------------------------------------------------------------------------------------------------------|-------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Approval is a distinct, re-authenticated human act that always happens in Grafana; Slack may trigger and link to it, never perform it | ✅ Chosen   | Ties every approval to a fresh, strongly authenticated act in a system the platform already controls (ADR-0021); Slack's own governance guidance treats "approval gates" as UX, not re-authentication |
| Approve directly via a Slack interactive button/message action                                                                        | ❌ Rejected | No Slack platform mechanism, including newer ones such as Sign in with Slack (ADR-0020), provides a per-action re-authentication primitive equivalent to a fresh signed assertion at decision time    |

## 4. Consequences

- **Positive —** every approval is tied to a fresh, re-authenticated act, regardless of which surface originated the
  proposal; this holds even as Slack's platform evolves, since it does not depend on any Slack-specific mechanism
  improving.
- **Negative / accepted trade —** approving from a Slack conversation requires a context switch to Grafana via a signed,
  single-use deep link, adding friction compared to an in-Slack button click.
- **Follow-on work —** deep-link generation and signing is shared infrastructure with ADR-0020's linking flow.
- **Revisit trigger —** Slack ships a genuine per-action re-authentication primitive equivalent to what this decision
  requires.

## 5. Verification

- Verified live 2026-09-12 against `docs.slack.dev`: Slack's own AI-agent governance guidance treats "approval gates" as
  a UX pattern, not a re-authentication mechanism, reinforcing rather than weakening this decision. Mechanism:
  [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

