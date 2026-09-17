---
id: ADR-0043
title: Cancellation is effective at the next step boundary
status: accepted
date: 2026-09-12
deciders: [ ]
category: agent
tags: [ agent, orchestration, durability ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ]
relates_to: [ ]
design: ../../design/durable-execution.md
legacy_id: D43
---

# ADR-0043 — Cancellation is effective at the next step boundary

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D43`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

Run cancellation needed a defined contract: how quickly does a cancel take effect, and does it tear down only the
top-level run or its sub-agents too? DBOS offers `preemptible=True` steps as an alternative to boundary-based
cancellation, at the cost of additional complexity.

## 2. Decision

**Cancellation contract: effective at the next step boundary**, so latency is bounded by the current step's duration (a
cancel during a 40s PromQL query lands when that query returns) — accepted 2026-09-12;
`preemptible=True` steps are **not** used in v1 but remain available if a latency complaint materialises. **Propagation
is native**:
`timeout_ms`/`deadline_epoch_ms` cancel the workflow **and all its children**, so sub-agent teardown is not hand-rolled.
v1 teardown scope = child workflows + pending queue entries; in-flight tool calls complete and are discarded; Phase-2
sandboxes (ADR-0004) are out of scope.

## 3. Considered options

| Option                                                                                         | Verdict            | Why                                                                                                                                            |
|------------------------------------------------------------------------------------------------|--------------------|------------------------------------------------------------------------------------------------------------------------------------------------|
| Effective at the next step boundary, using native `timeout_ms`/`deadline_epoch_ms` propagation | ✅ Chosen          | Bounds worst-case cancel latency to one step's duration and cancels all child workflows automatically — sub-agent teardown is not hand-rolled. |
| `preemptible=True` steps (cancel mid-step)                                                     | ❌ Rejected for v1 | Not needed unless a latency complaint materialises; kept available as a future option.                                                         |

## 4. Consequences

- **Positive —** cancellation propagates natively to all child workflows; no bespoke teardown code for sub-agents.
- **Negative / accepted trade —** cancel latency is bounded by the current step's duration, not instantaneous — e.g. a
  cancel issued during a 40s PromQL query only lands when that query returns.
- **Follow-on work —** v1 teardown scope is child workflows + pending queue entries; in-flight tool calls complete and
  are discarded; Phase-2 sandboxes (ADR-0004) are explicitly out of scope for this contract.
- **Revisit trigger —** a latency complaint about cancel responsiveness would reopen the `preemptible=True` option.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/durable-execution.md`](../../design/durable-execution.md).
