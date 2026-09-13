---
id: ADR-0021
title: The platform owns and operates the Grafana instance
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
legacy_id: D21
---

# ADR-0021 — The platform owns and operates the Grafana instance

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D21`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/platform-topology.md`](../../design/platform-topology.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**The platform owns and operates the Grafana instance; customers are orgs within a single shared instance** — confirmed, not customer-hosted. Grafana runs **OSS**, at **latest release**.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
