---
id: ADR-0031
title: Grafana surface streaming uses Grafana Live
status: accepted
date: 2026-09-12
deciders: []
category: streaming
tags: [streaming, events]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
design: ../../design/streaming-and-events.md
legacy_id: D31
---

# ADR-0031 — Grafana surface streaming uses Grafana Live

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D31`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Grafana surface streaming uses Grafana Live** (`StreamHandler`: `SubscribeStream`/`RunStream`/`PublishStream`), not SSE through the plugin's Go proxy — avoids known Go-reverse-proxy SSE-buffering pain for long-lived streams. Frontend uses **`@grafana/ui` directly**, no AG-UI (ADR-0029). Channel authorization enforced inside our backend's `SubscribeStream` handler against the caller's plugin-context identity and workspace/run ownership. **OSS self-hosted is the primary deployment target** — verified live against Grafana's own docs (2026-09-12): Grafana Live's default in-memory pub/sub is single-instance-scoped; its own Redis `ha_engine` is only required if a customer scales to multiple Grafana instances behind a load balancer (an edge case for OSS self-hosted, not the default — documented as a prerequisite only for that scenario, not assumed). The default `max_connections = 100` per Grafana instance must be raised by the customer admin — an explicit install-doc callout, since one WebSocket connection is consumed per browser tab. Per-message size/throughput limits are **undocumented by Grafana** — flagged as a pre-build verification spike (prototype our largest expected event payload through a test channel), now more important given ADR-0034 requires token-level streaming through Grafana Live too.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
