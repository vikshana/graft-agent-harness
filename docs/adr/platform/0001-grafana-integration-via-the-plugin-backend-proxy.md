---
id: ADR-0001
title: Grafana integration via the plugin backend proxy
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
legacy_id: D1
---

# ADR-0001 — Grafana integration via the plugin backend proxy

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D1`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/platform-topology.md`](../../design/platform-topology.md).

---

## 1. Context

The Grafana App Plugin frontend, and a future custom web frontend (ADR-0002), both need to reach the harness API from
the browser. The integration path for the Grafana App Plugin specifically needed deciding: call the harness API directly
from the plugin's frontend JavaScript, or route through the plugin's own backend (Go) proxy component.

## 2. Decision

Grafana integration goes through the **plugin backend (Go) proxy**, never browser→API direct. The (future, post-v1)
custom frontend calls the harness API directly. **Two callers, one API** — the plugin proxy and the custom frontend hit
the same API contract rather than each getting a bespoke one.

## 3. Considered options

| Option                                           | Verdict     | Why                                                                                                                                                  |
|--------------------------------------------------|-------------|------------------------------------------------------------------------------------------------------------------------------------------------------|
| Browser (plugin frontend) → harness API directly | ❌ Rejected | The migrated register entry did not record a rejection rationale beyond the decision itself.                                                         |
| Plugin backend (Go) proxy → harness API          | ✅ Chosen   | One API surface serves both the Grafana plugin and the future custom frontend — "two callers, one API" — instead of two divergent integration paths. |

## 4. Consequences

- **Positive —** a single API contract serves both the current caller (Grafana App Plugin) and the future one (custom
  web UI, ADR-0002); no plugin-specific API dialect to maintain.
- **Negative / accepted trade —** the plugin backend proxy is an extra hop between the browser and the harness API for
  the Grafana surface.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/platform-topology.md`](../../design/platform-topology.md) section 2.
