---
id: ADR-0067
title: Paging and on-call writes are classified, v1 ships read only
status: accepted
date: 2026-09-13
deciders: []
category: tools
tags: [tools, mcp, authority]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
design: ../../design/tool-registry-and-authority.md
legacy_id: D67
---

# ADR-0067 — Paging and on-call writes are classified, v1 ships read only

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D67`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/tool-registry-and-authority.md`](../../design/tool-registry-and-authority.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Paging/on-call writes are classified, not deferred wholesale — and the useful case turns out not to need them.** Against ADR-0063's ToolClass taxonomy: reading schedules, on-call rotation and incident detail is **`read`** (v1); adding a note to an existing incident is **`write`**; creating an incident, escalating, or adding responders is **`write`** and wakes humans at 03:00; acknowledging or resolving an incident is **`destructive`**, because it closes something a human may still need; and **maintenance windows, notification suppression and schedule overrides are `destructive` and hard-denied at L2 permanently** — **an agent that can suppress paging can hide an outage**, which is the single worst capability in this integration and is not worth having at any maturity level without an explicit, separate decision. **v1 ships `read` only.** `write` and `destructive` classes exist in the catalogue (L1) but are denied at L2. **The apparent loss is illusory, and resolving why fixes a latent inconsistency in J1:** the flagship journey has a `system_initiated`, structurally read-only Run posting to Slack and annotating a Grafana alert — which looked like writes. They are not. **Surface output is not a ToolClass.** The agent narrating its own findings on its own surfaces flows from the event log through the Slack Adapter and plugin backend, and never through the Tool Gateway; it acts on *us*, not on a customer system. A PagerDuty note, by contrast, is a tool call against a customer system and is correctly a `write`. So the thing on-call actually wants — the agent's finding appearing where they are looking — is served by narration, at 03:00, with no write capability at all.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
