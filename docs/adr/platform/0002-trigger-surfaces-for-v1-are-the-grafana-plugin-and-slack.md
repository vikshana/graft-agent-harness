---
id: ADR-0002
title: Trigger surfaces for v1 are the Grafana plugin and Slack
status: accepted
date: 2026-09-12
deciders: [ ]
category: platform
tags: [ platform, deployment ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ]
relates_to: [ ]
design: ../../design/platform-topology.md
legacy_id: D2
---

# ADR-0002 — Trigger surfaces for v1 are the Grafana plugin and Slack

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D2`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/platform-topology.md`](../../design/platform-topology.md).

---

## 1. Context

v1 needed to fix which surfaces can originate a run (trigger surfaces) versus which are deferred. The Grafana App Plugin
(ADR-0001) and Slack were the surfaces being built for v1; Grafana Alerting / Alertmanager webhooks are a common trigger
source but arrive in provider-specific shapes; a custom web UI was also on the table for v1.

## 2. Decision

Trigger surfaces for v1: the **Grafana App Plugin and Slack**, plus a **standardised normalised event** for webhooks
(Grafana Alerting / Alertmanager) so alert sources are interchangeable. **Custom Web UI is dropped from v1**, deferred
post-v1; when it ships it uses the same API and gets no private capabilities.

## 3. Considered options

| Option                                                | Verdict                | Why                                                                                                                              |
|-------------------------------------------------------|------------------------|----------------------------------------------------------------------------------------------------------------------------------|
| Grafana App Plugin + Slack + normalised webhook event | ✅ Chosen              | These are the surfaces needed and available for v1; one standard event shape makes webhook alert sources interchangeable.        |
| Custom Web UI in v1                                   | ❌ Rejected (deferred) | Dropped from v1; when built post-v1 it must reuse the existing API rather than get bespoke endpoints or privileged capabilities. |

## 4. Consequences

- **Positive —** one normalised event model for webhook triggers regardless of alert source.
- **Negative / accepted trade —** no custom web UI at v1 launch; users are limited to the Grafana plugin and Slack.
- **Follow-on work —** when the custom Web UI ships, it must reuse the existing API rather than get bespoke endpoints or
  private capabilities (see [`../../design/platform-topology.md`](../../design/platform-topology.md)
  section 2).
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/platform-topology.md`](../../design/platform-topology.md) section 2.
