# S3 — Eval sink: Langfuse or Phoenix

> **Gates: Phase 1. Timebox: 2 days.**
> A selection between two known options, not an open investigation. It gates
> Phase 1 only because "start testing and evaluating" requires somewhere to
> *look at* trajectories from day one.

---

## 1. The question

**Which self-hosted, open-source tool is the internal-only trajectory and
evaluation sink: Langfuse or Arize Phoenix?**

## 2. Why it gates Phase 1

ADR-0008 commits to two sinks and ADR-0071 defines the second one's job, but
neither picks the product. Phase 1's exit criteria include *"trajectories visible
in the eval sink"* — because a walking skeleton you cannot inspect is not
evaluable, and evaluating RCA quality is the reason Phase 1 exists.

It is cheap: both are OSS and self-hostable, and the decision is reversible if
the sink is fed by OTLP rather than a vendor SDK — which ADR-0071 already
requires.

## 3. Constraints — do not relitigate

| Constraint | ADR |
|---|---|
| **Internal only. No product feature may read from the eval sink's API.** This is what stops it becoming a runtime dependency | ADR-0071 |
| Fed by **OTel spans through our Collector** (OTLP), not by a bespoke in-process SDK | ADR-0005, ADR-0008 |
| Must sit behind the **same PAN/PII scrubbing** as the audit chain — an unscrubbed sink next to a compliant one is a liability | ADR-0025 |
| Trajectories come from OTel spans and the event log — **never from a checkpointer**, which does not exist | ADR-0040 |
| The replay primitive is `fork_workflow(id, from_step=N)`, producing a **new workflow id** with history copied | ADR-0040 |
| Audit records are never sampled; the eval sink is a separate concern | ADR-0015 |
| OSS, self-hostable, deployable per region | ADR-0049 |

**The load-bearing constraint is OTLP ingestion.** A tool that only works via its
own SDK would put a vendor library in the agent process and quietly violate
ADR-0071's one-way rule.

## 4. Method

Stand both up locally. Feed both the *same* synthetic corpus.

### E1 — OTLP ingestion fidelity
Emit ~20 synthetic trajectories as OTel spans using GenAI semantic conventions,
through a Collector, to each tool. Assess: are nested spans (run → sub-agent →
LLM call → tool call) preserved as a readable tree? Are GenAI attributes
(model, tokens, cost) parsed or dropped?

### E2 — The actual job: prompt-version comparison
The reason we have a second sink at all is *"compare prompt v1.2 vs v1.3 across
50 historical incidents"*. Simulate it: two versions, N runs each, and try to
answer "which is better" in the UI. **This is the discriminating test** — both
tools trace well; they differ in whether this comparison is a first-class
workflow or a manual slog.

### E3 — Annotation and dataset curation
Annotate a trajectory, build a dataset from annotated runs, export it.

### E4 — Retention and scrubbing posture
Configurable retention? Can it sit entirely behind our Collector so scrubbing is
guaranteed upstream? Any phone-home or telemetry to disable?

### E5 — Operational cost
Storage growth for a realistic run volume; deployment complexity per region;
upgrade story.

## 5. Decision criteria, weighted

| Criterion | Weight | Why |
|---|---|---|
| OTLP/GenAI-semconv ingestion without a vendor SDK in our process | **Blocking** | ADR-0071's one-way rule |
| Prompt-version comparison across many runs | **High** | The reason the sink exists |
| Annotation + dataset curation | High | Feeds the Phase 2 eval suite |
| Self-host licence suitable for commercial use | **Blocking** | |
| Retention controls | Medium | ADR-0025 |
| Operational cost per region | Medium | ADR-0049 |

## 6. Outcomes

| Outcome | Action |
|---|---|
| One clearly wins | ADR recording the choice **and the criterion that decided it** |
| Both adequate | Choose on operational cost; record the other as a viable alternative with the switching cost noted — it is genuinely low while ingestion stays OTLP |
| **Neither ingests OTLP cleanly** | Significant: ADR-0008's "Collector fans out" assumption weakens. Do **not** solve it by embedding a vendor SDK — that breaks ADR-0071. Escalate |

## 7. Deliverables

1. **One ADR** — the eval sink choice, with the deciding criterion stated.
2. Update [`../../design/observability-pipeline.md`](../../design/observability-pipeline.md),
   closing its open question and naming the tool.
3. Collector configuration for the chosen sink, checked in.
4. Delete this file.

## 8. Out of scope

Eval *methodology* — ground truth, metrics, corpus size, what "good" means. That
is gate S6 and blocks Phase 2, not Phase 1. This spike picks the place to look,
not what to look for.
