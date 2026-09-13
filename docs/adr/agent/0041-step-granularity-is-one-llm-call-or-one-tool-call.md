---
id: ADR-0041
title: Step granularity is one LLM call or one tool call
status: accepted
date: 2026-09-12
deciders: []
category: agent
tags: [agent, orchestration, durability]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: [ADR-0025, ADR-0034]
design: ../../design/durable-execution.md
legacy_id: D41
---

# ADR-0041 — Step granularity is one LLM call or one tool call

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D41`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

ADR-0039/ADR-0040 put the durability boundary above LangGraph, driven by DBOS
step checkpoints — but at what granularity? Too coarse (one step per graph
run) loses crash-resume precision and bounds nothing; too fine adds write
overhead for no benefit. ADR-0033 separately requires a cancellation check at
every tool-call boundary, and ADR-0034 already routes large artifacts to
object storage rather than inline payloads — both of which the granularity
rule must satisfy rather than contradict.

## 2. Decision

**Step granularity (the briefing's "crux"): one LLM call = one step; one tool call = one step; one sub-agent = one child workflow; one run = one parent workflow.** Consequences: retry waste is bounded to a single LLM call (accepted); **ADR-0033's "signal check at every tool-call boundary" is satisfied structurally** rather than by a bespoke hook, since cancel preempts at step boundaries and every tool call is a step; write amplification is one ~1–2 ms Postgres write per step (accepted, against DBOS's >40K steps/sec single-Postgres benchmark). **Steps must return pointers, never large payloads** — artifacts go to object storage, which ADR-0034 already requires independently.

**Promoted to a hard invariant by spike S2 (2026-09-13).** DBOS's serialisation of step outputs, workflow inputs/outputs and `send`/`recv` message bodies is a wire format (pickle + base64), not encryption or redaction — any value that reaches one of those fields is recoverable in plaintext by anyone with `SELECT` on the DBOS system database. A single violation of the pointer rule, in a step that happens to handle a customer log line containing a PAN, is therefore sufficient to bring PCI-DSS scope down on the system database (ADR-0025). The pointer rule accordingly moves from convention to a **CI-enforced invariant**: `scripts/check_step_pointer_rule.py` fails any `@DBOS.step()`-decorated function whose return type is not a recognised pointer type.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| **One LLM call = one step; one tool call = one step; one sub-agent = one child workflow; one run = one parent workflow** | ✅ Chosen | Bounds retry waste to a single call; satisfies ADR-0033's cancel-check-at-every-tool-call-boundary structurally, since every tool call is a step and cancel preempts at step boundaries |
| One step per graph node | ❌ Rejected | Coarser than the actual LLM/tool call boundary — a node making multiple calls would lose per-call crash isolation |
| One step per whole graph run | ❌ Rejected | No crash-resume benefit inside a run; defeats the purpose of durable execution |

## 4. Consequences

- **Positive —** retry waste is bounded to a single LLM call (accepted in session, Q6); ADR-0033's cancellation guarantee falls out of the granularity rule rather than needing a bespoke hook.
- **Negative / accepted trade —** write amplification of one ~1–2 ms Postgres write per step, accepted in session (Q3b) against DBOS's published >40K steps/sec single-Postgres benchmark.
- **Follow-on work —** steps must return pointers, never large payloads — artifacts go to object storage per ADR-0034. **`scripts/check_step_pointer_rule.py` added to CI** (spike S2 deliverable), failing any step whose return type is not a recognised pointer type.
- **Revisit trigger —** none observed; granularity was confirmed achievable in practice by spike S1 (see Verification).

## 5. Verification

- Confirmed by **spike S1** (2026-09-13, experiments E2/E6): `list_workflow_steps()` returns exactly one entry per LLM call and one per tool call — named for the call-wrapper function, not the graph node — for both an in-process fake tool and a real streamable-HTTP MCP tool call (ADR-0070). Mechanism and the full experiment log: [`../../design/durable-execution.md`](../../design/durable-execution.md) section 4.4.
- Confirmed by **spike S2** (2026-09-13, experiment E7) against a live scratch Postgres 16, `dbos==2.31.1`: a step deliberately returning a raw string containing a test PAN was found, unmodified and trivially recoverable (`base64.b64decode` + `pickle.loads`, no encryption involved), in `workflow_status.inputs`, `workflow_status.output` and `operation_outputs.output`. No PII/PAN-aware filtering exists anywhere in DBOS's serialisation path. Mechanism and full experiment log: [`../../design/durable-execution.md`](../../design/durable-execution.md) section 4.5.
