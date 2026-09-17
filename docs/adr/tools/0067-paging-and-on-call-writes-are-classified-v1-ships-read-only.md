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

Paging/on-call tooling (e.g. PagerDuty-style incident and schedule
management) mixes read operations with writes of very different severity,
up to and including suppressing notifications — an agent that can suppress
paging could hide a real outage. A journey in the flagship design (J1) also
appeared to require the agent to "post to Slack" and "annotate a Grafana
alert" during a `system_initiated`, structurally read-only run, which
looked like a contradiction that needed resolving.

## 2. Decision

**Paging/on-call writes are classified, not deferred wholesale — and the
useful case turns out not to need them.** Against ADR-0063's ToolClass
taxonomy: reading schedules, on-call rotation and incident detail is
**`read`** (v1); adding a note to an existing incident is **`write`**;
creating an incident, escalating, or adding responders is **`write`** and
wakes humans at 03:00; acknowledging or resolving an incident is
**`destructive`**, because it closes something a human may still need;
and **maintenance windows, notification suppression and schedule
overrides are `destructive` and hard-denied at L2 permanently** — **an
agent that can suppress paging can hide an outage**, which is the single
worst capability in this integration and is not worth having at any
maturity level without an explicit, separate decision. **v1 ships `read`
only.** `write` and `destructive` classes exist in the catalogue (L1) but
are denied at L2. **The apparent loss is illusory, and resolving why fixes
a latent inconsistency in J1:** the flagship journey has a
`system_initiated`, structurally read-only Run posting to Slack and
annotating a Grafana alert — which looked like writes. They are not.
**Surface output is not a ToolClass.** The agent narrating its own
findings on its own surfaces flows from the event log through the Slack
Adapter and plugin backend, and never through the Tool Gateway; it acts on
*us*, not on a customer system. A PagerDuty note, by contrast, is a tool
call against a customer system and is correctly a `write`. So the thing
on-call actually wants — the agent's finding appearing where they are
looking — is served by narration, at 03:00, with no write capability at
all.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| Defer all paging/on-call tooling wholesale (no read either) until write semantics are resolved | ❌ Rejected | Unnecessarily conservative — reads (schedules, rotation, incident detail) carry none of the risk that writes do and are useful on their own. |
| Ship reads and writes together, classifying writes by severity | ❌ Rejected | Notification suppression and maintenance-window writes let an agent hide a real outage — the single worst capability in this integration, not worth having without an explicit, separate decision. |
| Classify all paging/on-call operations by ToolClass; ship only `read` in v1, hard-deny `write`/`destructive` at L2 | ✅ Chosen | Reads are useful and safe now; the apparent gap for "the agent needs to notify on-call" is actually served by narration (Slack/Grafana annotation via the event log), which is not a ToolClass tool call at all. |

## 4. Consequences

- **Positive —** v1 ships useful read-only paging/on-call tooling without
  ever exposing the ability to suppress notifications or acknowledge/
  resolve incidents.
- **Negative / accepted trade —** `write` and `destructive` classes exist in
  the catalogue but are permanently hard-denied at L2 for suppression/
  maintenance-window operations — not merely deferred, a deliberate
  standing denial.
- **Follow-on work —** fixes a latent inconsistency in journey J1: the
  agent's Slack post and Grafana annotation during a `system_initiated`
  run are narration (event log → Slack Adapter/plugin backend), never a
  Tool Gateway call, so they remain compatible with ADR-0013's structural
  read-only guarantee.
- **Revisit trigger —** re-enabling suppression/maintenance-window writes
  would require an explicit, separate decision — not a routine
  L3 policy change.

## 5. Verification

- Not separately verified against a live source; no claim in the original
  register entry was marked "verified live" for this decision. Mechanism:
  [`../../design/tool-registry-and-authority.md`](../../design/tool-registry-and-authority.md).
