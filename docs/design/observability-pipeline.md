# Observability pipeline

> **Status: 🟢 Resolved for v1; one open tension (§4).** Mechanism for
> **ADR-0005**, **ADR-0008**, **ADR-0071**; compliance from **ADR-0025**.
>
> Vocabulary per [`../GLOSSARY.md`](../GLOSSARY.md). Related:
> [`audit-and-attribution.md`](./audit-and-attribution.md).
>
> *Migrated from `DECISION-REGISTER.md` §3 during the 2026-09-13 ADR migration.*

---

## 1. Shape

```
OpenLIT auto-instrumentation (LiteLLM, vLLM, LangChain, vector DBs, GPU metrics)
  + hand-written spans (LangGraph nodes, Tool Gateway calls, domain events)
        │ OTel GenAI semconv
        ▼
   OTel Collector  ── PII / secret / PAN scrubbing, sampling, graft_tenant_id tagging
        ├──▶ Operational sink: Tempo / Mimir / Loki (or customer's OTLP endpoint)
        └──▶ Eval sink (internal only): Langfuse or Phoenix
                 — trajectory review, prompt version comparison,
                   annotation, eval dataset curation
```

## 2. Why two sinks

LGTM is strong for traces, metrics and logs, and weak for **trajectory review** —
comparing prompt v1.2 against v1.3 across 50 historical incidents, annotating
runs, building eval datasets. Hence a second, internal-only sink.

**The one-way rule (ADR-0071): no product feature may read from the eval sink's
API.** This is what stops an eval tool becoming a runtime dependency.

Note that the eval sink is fed by OTel spans (ADR-0008) and the event log
(ADR-0030) — never by a checkpointer, which does not exist (ADR-0040). DBOS's
`list_workflow_steps()` and `fork_workflow()` supply ordered, SQL-queryable
trajectories and historical replay respectively.

## 3. Attribution and scoping

Every span carries `graft.tenant.id` and `graft.run.id` in dotted OTel form
(ADR-0059). `graft_run_id` is additionally propagated **outward** into
customer-owned logs — K8s `impersonatedBy`, GitHub commit trailers, datasource
query headers (ADR-0015).

## 4. Open tension — prompt storage vs. PAN scrubbing

> Historically labelled **D8b** in the decision register. It is a *tension*,
> not a decision, which is why it has no ADR number — it is tracked here and
> owned by the Evals & Benchmarks session.

[`audit-and-attribution.md`](./audit-and-attribution.md) proposes storing only
prompt **hashes** in the audit chain, with raw prompts living in the eval sink.
PCI-DSS (ADR-0025) sharpens this: a raw prompt may carry a PAN quoted from an
investigated log line, so **the eval sink must pass through the same PAN-scrubbing
pipeline as the audit chain**, or it becomes an unscrubbed compliance liability
sitting next to a compliant one.

This still sits awkwardly against ADR-0071's "never a runtime dependency" framing
for forensics. **Not resolved — clarified.** The PAN-scrubbing implementation
(Luhn-check-backed detection) and this tension are both owned by the
**Evals & Benchmarks** session; see [`../backlog/future-sessions.md`](../backlog/future-sessions.md).

## 5. Open questions

- Langfuse vs. Phoenix for the eval sink.
- Sampling policy — research suggests 100% for RCA mode. **Audit records are
  never sampled** (ADR-0015).
- Whether customers get the operational sink pointed at their own OTLP endpoint
  by default.
- PCI scope now extends to the DBOS system database (ADR-0037 risk X1) — hand
  off to the Evals session alongside ADR-0025.
