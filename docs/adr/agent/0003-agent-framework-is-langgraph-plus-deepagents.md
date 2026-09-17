---
id: ADR-0003
title: Agent framework is LangGraph plus DeepAgents
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
legacy_id: D3
---

# ADR-0003 — Agent framework is LangGraph plus DeepAgents

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D3`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

v1 needed an agent orchestration framework. Whatever is chosen has to compose with a durable-execution engine (ADR-0037)
that requires deterministic, replayable workflow functions — all non-deterministic work (LLM calls, tool calls, clock
reads, randomness) must live inside steps, not in the graph structure itself.

## 2. Decision

Agent framework: **LangGraph + DeepAgents**. Graph nodes are written as **plain functions with no framework types in
node signatures**, so business logic is not coupled to LangGraph's own types and the determinism constraint above is
satisfied by construction rather than by discipline alone.

## 3. Considered options

| Option                                                                                         | Verdict   | Why                                                                                                                                                                           |
|------------------------------------------------------------------------------------------------|-----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| LangGraph + DeepAgents, with graph nodes as plain functions (no framework types in signatures) | ✅ Chosen | Satisfies the durable-execution engine's determinism/replay requirement (ADR-0037) largely by construction; no alternative framework is named in the migrated register entry. |

## 4. Consequences

- **Positive —** graph nodes stay portable and testable outside LangGraph; framework-free node signatures reduce the
  migration cost if the agent framework or durable-execution engine ever changes.
- **Follow-on work —** enables ADR-0037/ADR-0039/ADR-0040's requirement that node functions be deterministic and
  resumable at step boundaries, and ADR-0040's requirement that conversational state be passed explicitly into the graph
  rather than relying on framework-native persistence.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. The framework-free node discipline is referenced as satisfied in
  [`../../design/durable-execution.md`](../../design/durable-execution.md) section 2.4.
