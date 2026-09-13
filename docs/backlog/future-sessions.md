# Remaining architecture sessions

> *Migrated from `DECISION-REGISTER.md` §7 during the 2026-09-13 ADR migration.*

Each becomes one or more ADRs in [`../adr/`](../adr/README.md). The **Gate**
marker on each shows which roadmap phase it blocks — see
[`roadmap.md`](./roadmap.md) §6. Sessions with no gate marker are not on the
critical path. The four earlier
deep-dives (identity, streaming, tenancy, durable execution) are **all closed** —
their `open-questions/` files were deleted in commit `b78cdcc` and their outcomes
are ADR-0009–ADR-0069.

---

## 1. Context assembly & compaction

**Gate S5 — blocks Phase 2.**
Layered prompt hierarchy, summariser node, tool-result offloading, prompt-caching
strategy.

**Inherits:** [`../design/context-assembly.md`](../design/context-assembly.md) —
the hierarchy is locked (ADR-0062), the compaction mechanics are not.
**Does not inherit** the authority question: ADR-0062 already settled that
custom instructions govern behaviour, never capability.

## 2. Memory & knowledge

*Not on the critical path — Phase 5.*
Neo4j / Mem0 deferral, RAG over runbooks, auto-refreshing infrastructure memory.

**Inherits:** the `*/15` infra-memory refresh schedule is already committed as a
platform-internal timer (ADR-0047), consuming no Tenant Schedule ceiling
(ADR-0058).

## 3. HITL & write-action model

**Gate S7 — blocks Phase 3.**
Proposal → approval → execution, confidence thresholds, two-person rules.

**Inherits:** approval follows the driver (ADR-0065), binds to `proposal_hash`,
is re-authenticated in Grafana (ADR-0014), and expires after ≥72 h (ADR-0066).
**Two-person rule is explicitly deferred here** — it was mutually exclusive with
the superseded initiator-only rule (ADR-0055) and is now re-openable.

## 4. Model routing & provider strategy

**Gate S4 — a *provisional* choice blocks Phase 1; the full session is Phase 2.**
LiteLLM, local (vLLM/Qwen) vs commercial, per-node model selection, fallbacks.

**Inherits a hard constraint:** **no degrade-to-a-cheaper-model at budget cap**
(ADR-0057) — switching mid-Run silently changes the quality characteristics an
operator is about to act on.

## 5. Evals & benchmarks

**Gate S3 (sink choice) blocks Phase 1; Gate S6 (methodology) blocks Phase 2.**
Incident replay suite, trajectory evals, DeepEval, O11y-Bench, shadow deployments.

**Also owns two handed-off items:**
- **PAN-scrubbing implementation** (Luhn-check-backed detector for the OTel
  Collector) — requirement locked by ADR-0025, implementation deferred here.
- **The eval-sink scrubbing tension** — see
  [`../design/observability-pipeline.md`](../design/observability-pipeline.md) §4.
- **PCI scope extending to the DBOS system database** (ADR-0037 risk X1).

**Inherits:** `fork_workflow(id, from_step=N)` is the replay primitive
(ADR-0040); forked runs are structurally read-only (ADR-0042).

## 6. Config-driven design

*Not on the critical path.*
What is config vs code; config schema, validation, versioning, hot reload.

**Inherits:** tool policy is versioned, never overwritten (ADR-0016); roles and
verbs are rows, not code (ADR-0056).

## 7. Deployment topology — *mostly closed*
**Resolved:** ADR-0021 (Grafana layer), ADR-0049 (two regions, residency,
Tenant Directory), ADR-0046 (blue/green). See
[`../design/platform-topology.md`](../design/platform-topology.md).

**Remaining:** packaging (Helm/Terraform) and GPU/serving placement. Not tenancy.

## 8. Cost & safety guardrails — *mostly closed*

**Gate S8 — blocks Phase 2 (per-run caps) and Phase 4 (quota request flow).**
**Resolved:** ADR-0044, ADR-0057, ADR-0058.
**Remaining:** concrete quota numbers, Schedule defaults (proposed 10 per Tenant,
1 h minimum interval), ITSM-vs-deep-link for quota requests.

## 9. Security

*PAN scrubbing blocks Phase 4; injection sanitisation is continuous.*
Indirect prompt-injection sanitisation, PII/secret scrubbing, WORM audit trail.

**Out of scope for this project:** the platform Grafana Server Admin credential's
blast radius and rotation policy (ADR-0022) is owned by the platform team.

---

## Implementation-time verification items

Not architectural questions — things to check before or during build.

| Item | Source |
|---|---|
| Grafana Live per-message size/throughput limits (undocumented) — prototype largest expected payload | ADR-0031 |
| Exact `SubscribeStream` request/context shape against the plugin SDK | ADR-0031 |
| DBOS × async LangGraph × `langchain-mcp-adapters` ergonomics — **Gate S1: blocks C4 L3 *and* Phase 1** | ADR-0037 |
| DBOS system-DB migrations vs `FORCE ROW LEVEL SECURITY` / PCI scope — **Gate S2: blocks C4 L3 *and* Phase 1** | ADR-0050 |
| Reaper safety envelope | ADR-0038 |
| LangGraph-under-Pattern-B prototype | ADR-0039 |
| Doubled worker capacity during blue/green drains | ADR-0046 |
| Expired-approval rate instrumentation | ADR-0065 |
| Tenant Directory substrate; brownfield backfill run-book | ADR-0049, ADR-0053 |
