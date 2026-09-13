---
id: ADR-0039
title: The run is the durable workflow
status: accepted
date: 2026-09-12
deciders: []
category: agent
tags: [agent, orchestration, durability]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
design: ../../design/durable-execution.md
legacy_id: D39
---

# ADR-0039 — The run is the durable workflow

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D39`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**The run *is* the durable workflow ("Pattern B").** Parent workflow = run; child workflow = sub-agent/DeepAgents worker; step = one LLM call or one tool call. **"Pattern A" (durable-workflow-as-LangChain-`@tool`) — which is what DBOS's own LangGraph blog and maintained LangGraph example demonstrate — is retained only for write actions** (PR, Jira, alert silence), where a self-contained workflow with its own idempotency key is the right unit and ADR-0014's approval gate already forces a boundary. Pattern A alone was **rejected as primary**: it makes individual tools crash-proof but leaves the *run* with no work rediscovery, and runs two checkpointers side by side. **Accepted tension:** DBOS's Pattern B references are framework-free Python loops, not LangGraph, so LangGraph is demoted from "the orchestrator" to "graph structure invoked beneath the durability boundary." Does not contradict ADR-0003; does make R8 mandatory.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
