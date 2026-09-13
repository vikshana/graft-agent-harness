---
id: ADR-0001
title: Grafana integration via the plugin backend proxy
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
legacy_id: D1
---

# ADR-0001 — Grafana integration via the plugin backend proxy

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D1`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/platform-topology.md`](../../design/platform-topology.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

Grafana integration via the **plugin backend (Go) proxy**, not browser→API direct. Custom frontend calls the API directly. Two callers, one API.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
