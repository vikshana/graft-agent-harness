---
id: ADR-0031
title: Grafana surface streaming uses Grafana Live
status: accepted
date: 2026-09-12
deciders: [ ]
category: streaming
tags: [ streaming, events ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ]
relates_to: [ ]
design: ../../design/streaming-and-events.md
legacy_id: D31
---

# ADR-0031 — Grafana surface streaming uses Grafana Live

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D31`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).

---

## 1. Context

The Grafana App Plugin (ADR-0001) needs a live-streaming transport for long-lived event streams. SSE through the
plugin's Go reverse-proxy has known buffering problems for long-lived streams; Grafana Live is Grafana's own pub/sub
transport, but its production characteristics (connection limits, message-size limits) needed checking against a live
source before committing to it as the sole transport.

## 2. Decision

**Grafana surface streaming uses Grafana Live**
(`StreamHandler`: `SubscribeStream`/`RunStream`/`PublishStream`), not SSE through the plugin's Go proxy — avoids known
Go-reverse-proxy SSE-buffering pain for long-lived streams. Frontend uses **`@grafana/ui`
directly**, no AG-UI (ADR-0029). Channel authorisation enforced inside our backend's `SubscribeStream` handler against
the caller's plugin-context identity and workspace/run ownership. **OSS self-hosted is the primary deployment target** —
verified live against Grafana's own docs (2026-09-12): Grafana Live's default in-memory pub/sub is
single-instance-scoped; its own Redis `ha_engine` is only required if a customer scales to multiple Grafana instances
behind a load balancer (an edge case for OSS self-hosted, not the default — documented as a prerequisite only for that
scenario, not assumed). The default
`max_connections = 100` per Grafana instance must be raised by the customer admin — an explicit install-doc callout,
since one WebSocket connection is consumed per browser tab. Per-message size/throughput limits are **undocumented by
Grafana** — flagged as a pre-build verification spike (prototype our largest expected event payload through a test
channel), now more important given ADR-0034 requires token-level streaming through Grafana Live too.

## 3. Considered options

| Option                                                                        | Verdict     | Why                                                                                                                                                                      |
|-------------------------------------------------------------------------------|-------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| SSE through the plugin's Go reverse-proxy                                     | ❌ Rejected | Known Go-reverse-proxy SSE-buffering pain for long-lived streams.                                                                                                        |
| Grafana Live (`StreamHandler`: `SubscribeStream`/`RunStream`/`PublishStream`) | ✅ Chosen   | Avoids the SSE-buffering problem; is Grafana's own pub/sub transport, verified against Grafana's own docs as suitable for the primary OSS self-hosted deployment target. |

## 4. Consequences

- **Positive —** avoids SSE-buffering issues; channel authorisation is enforced inside our own `SubscribeStream` handler
  against plugin-context identity and workspace/run ownership.
- **Negative / accepted trade —** Grafana Live's default
  `max_connections = 100` per instance must be raised by the customer admin — an operational requirement documented in
  the install docs, since one WebSocket connection is consumed per browser tab. Grafana's Redis
  `ha_engine` is a documented prerequisite only if a customer scales to multiple Grafana instances behind a load
  balancer.
- **Follow-on work —** per-message size/throughput limits are undocumented by Grafana and must be verified with a
  pre-build spike (prototype the largest expected event payload through a test channel) — more important given
  ADR-0034's requirement for token-level streaming through the same transport.
- **Revisit trigger —** if the verification spike finds a size/throughput limit that token-level streaming (ADR-0034)
  would exceed.

## 5. Verification

- Grafana Live's single-instance-scoped in-memory pub/sub, and the Redis `ha_engine` prerequisite only for
  multi-instance-behind-a-load-balancer deployments — verified live against Grafana's own documentation, 2026-09-12.
