# S4 — Provisional model and serving stack for Phase 1

> **Gates: Phase 1. Timebox: 2 days.**
> Deliberately **provisional**. The full model-routing session is a Phase 2
> decision; this spike picks something defensible to build on, and says so.

---

## 1. The question

**Which model, served how, does Phase 1 run on — and does that choice survive the two-region deployment?**

## 2. Why it gates Phase 1

Phase 1 cannot run without a model, and the routing session has not happened. The risk is not picking wrongly — it is
picking in a way that **bakes in an assumption Phase 2 cannot undo**, particularly around regional availability and data
residency.

There is one constraint that makes this more than a coin-flip: **ADR-0049 puts a production region in AliCloud.**
Several commercial model providers are not available there, and ADR-0049 forbids run data leaving its home region. A
choice that works in the GCP region and is illegal or unavailable in the AliCloud one is not a provisional choice — it
is a Phase 4 landmine.

## 3. Constraints — do not relitigate

| Constraint                                                                                                                                                                                                              | ADR                                                                              |
|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| **No degrade-to-a-cheaper-model at budget cap.** Model selection is a platform decision driven by evals and availability; switching mid-Run silently changes the quality characteristics an operator is about to act on | ADR-0057                                                                         |
| **Two independent regional deployments (GCP, AliCloud).** Run data, events, artifacts and audit records **never leave their home region**                                                                               | ADR-0049                                                                         |
| Compliance regime is PCI-DSS — prompts may quote a PAN from an investigated log line, so what crosses a provider boundary is a compliance question                                                                      | ADR-0025                                                                         |
| **Token-level streaming on all surfaces** — the model and serving stack must stream tokens                                                                                                                              | ADR-0034                                                                         |
| Prompt layers are ordered static-first specifically to enable **prompt caching**                                                                                                                                        | ADR-0062, [`../../design/context-assembly.md`](../../design/context-assembly.md) |
| One LLM call = one DBOS step; retry waste is bounded to a single call                                                                                                                                                   | ADR-0041                                                                         |
| Per-run token and cost caps are reported via `budget_consumed` / `budget_warning`                                                                                                                                       | ADR-0044, ADR-0029                                                               |
| Instrumentation is OpenLIT + OTel GenAI semconv — the model client must be instrumentable                                                                                                                               | ADR-0008                                                                         |

## 4. Method

### E1 — Regional availability matrix

Before any quality testing: which candidates are actually servable in **both**
regions under ADR-0049's residency rule? This is a desk exercise, and it may eliminate most of the field in an hour. Do
it first.

### E2 — Tool-calling fidelity

The agent's core loop is tool selection, not prose. Run the same 5 investigation scenarios against each surviving
candidate and measure: correct tool chosen, correct arguments, valid schema adherence, recovery from a tool error.
**Weight this highest** — a model that writes beautifully and calls tools badly is useless here.

### E3 — Streaming

Confirm token-level streaming end to end, and measure time-to-first-token. ADR-0034 chose token-level streaming *for UX
responsiveness*, so latency is a product requirement, not a nicety.

### E4 — Context and caching

Usable context window against a realistic investigation payload, and whether the provider supports prompt caching in a
way that rewards our static-first layer ordering.

### E5 — Cost envelope

Cost per representative run, to give ADR-0057's per-run and per-Tenant ceilings a real number instead of a guess. Feeds
gate S8.

### E6 — Instrumentability

OpenLIT or equivalent OTel GenAI instrumentation available for the client.

## 5. Decision criteria

| Criterion                                           | Weight       |
|-----------------------------------------------------|--------------|
| Available in **both** regions under residency rules | **Blocking** |
| Tool-calling fidelity                               | **Highest**  |
| Token streaming + acceptable TTFT                   | **Blocking** |
| Context window sufficient for a real investigation  | High         |
| Prompt caching support                              | Medium       |
| Cost per run                                        | Medium       |
| OTel GenAI instrumentation                          | Medium       |

## 6. Outcomes

| Outcome                                                | Action                                                                                                                                                                                     |
|--------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| One model works in both regions                        | **Provisional ADR**, explicitly marked revisitable by the Phase 2 routing session                                                                                                          |
| Different models per region                            | Record it — and note the consequence: evals must then be **per region**, since ADR-0057 forbids treating models as interchangeable mid-run. This is a real finding for the routing session |
| Only self-hosted open weights are viable in one region | Likely, given ADR-0049. Serving infrastructure (GPU placement) becomes a Phase 1 dependency and must be added to the roadmap's Phase 1 scope                                               |
| Nothing meets the tool-calling bar                     | Escalate. It affects ADR-0003's agent design far more than it affects this spike                                                                                                           |

## 7. Deliverables

1. The E1 availability matrix — reusable by the Phase 2 routing session.
2. **One ADR**, titled and tagged as **provisional**, with the revisit trigger named (the Phase 2 routing session).
3. Cost-per-run figure handed to gate S8 (quota numbers).
4. If self-hosting is required: a note added to
   [`../../design/platform-topology.md`](../../design/platform-topology.md)'s open work, since GPU/serving placement is
   already tracked there.
5. Delete this file.

## 8. Out of scope

Multi-model routing, per-node model selection, fallback chains, local-vs- commercial strategy. All of that is the Phase
2 routing session. This spike answers *what do we build Phase 1 on*, with the explicit expectation of being superseded.
