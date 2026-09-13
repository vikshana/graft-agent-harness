---
id: ADR-0002
title: Trigger surfaces for v1 are the Grafana plugin and Slack
status: accepted
date: 2026-09-12
deciders: []
category: platform
tags: [platform, deployment]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
design: ../../design/platform-topology.md
legacy_id: D2
---

# ADR-0002 — Trigger surfaces for v1 are the Grafana plugin and Slack

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D2`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/platform-topology.md`](../../design/platform-topology.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

Trigger surfaces for v1: **Grafana App Plugin and Slack** with a standardised normalised event for webhooks (Grafana Alerting / Alertmanager). **Custom Web UI dropped from v1**, deferred post-v1, same API, no private capabilities.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
