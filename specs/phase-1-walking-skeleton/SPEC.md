# Spec: Phase 1 API-first walking skeleton

> **Status:** Draft
> **Created:** 2026-09-17
> **Folder:** `specs/phase-1-walking-skeleton`
>
> **Recovery scope proposal (2026-09-19):** Proposed ADR-0078 narrows Phase 1
> automatic recovery to a returning matching executor identity and explicit
> released compatibility revision. Cross-executor automatic recovery is not
> claimed. Ambiguous or stuck Runs require operator escalation. This scope
> change is pending owner acceptance; retained Gate 0.3 and Temporal evidence
> remains historical evidence and does not mark this specification or Phase 1
> complete.

---

## User input

> Can you create a phase one implementation plan and test/verificaiton steps which can be handed over to luna for implemenation? As, the application is API first, contract test would be ideal.
>
> API contract is beetween the harness and UI/Slack, The harness should support all the models supported by the langgraph
>
> Define contract, defer adapter (Recommended)
>
> Harness is utilising LangGraph so it should handle the model support

---

## Context

Phase 1 is an internal, read-only walking skeleton for on-call engineers and
platform operators: one alert starts a durable investigation and produces an
evidence-backed narrated finding in the Grafana plugin with token-level
streaming. The implementation must establish the irreversible tenancy,
durability, authority, audit, and observability foundations defined by the
accepted ADRs.

The harness is API-first. A versioned contract between the harness and surface
adapters must describe Run creation, Run state, control outcomes, and the event
stream independently of Grafana or Slack transport details. Phase 1 implements
the Grafana adapter against that contract; the future Slack adapter must be able
to consume the same semantic contract without changing the harness API.

Model invocation uses LangGraph's model integration boundary. The harness must
not add a narrower provider-specific application API: organisation policy
selects the approved model and serving arrangement for the Run's home region,
and Phase 1 verifies the selected arrangement rather than claiming exhaustive
certification of every upstream LangGraph integration.

---

## Functional Requirements

1. Accept an authenticated, deduplicated webhook alert and create one private,
   `system_initiated`, read-only Run in its resolved Tenant scope.
2. Execute the Run as one durable DBOS workflow containing a LangGraph agent
   compiled without a checkpointer; each LLM call and Tool Gateway call is one
   independently checkpointed DBOS step.
3. Permit only `read` ToolClass capabilities for the system-initiated Run and
   route every customer-system operation through the Tool Gateway and a
   streamable-HTTP MCP server.
4. Persist Run state and a versioned, replayable event stream transactionally in
   PostgreSQL; large tool results and other artifacts are represented by
   pointers rather than embedded payloads.
5. Stream narrative tokens and lifecycle events through the shared surface
   contract to the Grafana plugin, including replay after reconnect.
6. Produce an evidence-backed terminal finding or a typed terminal error and
   make the completed step trajectory inspectable.
7. Emit OTel telemetry and expose trajectories to the internal Langfuse
   evaluation sink without making product execution depend on sink availability.
8. Derive audit attribution from verified credentials and retain Tenant scope on
   every application row, event, span, and audit record.
9. Select the model and serving arrangement through organisation policy and keep
   that selection fixed for the Run. Harness-owned code must use LangGraph's
   model abstraction rather than provider-specific types outside configuration
   and composition boundaries.

---

## Contract Scope

The Phase 1 contract must cover these transport-independent semantics:

- authenticated Run creation from a normalised webhook trigger;
- idempotent trigger handling and stable `graft_run_id` responses;
- Run status and terminal outcome retrieval;
- ordered, versioned Run events with reconnect/replay from a known
  `graft_event_id`;
- token-level narrative events and typed status, Tool-call, evidence, budget,
  error, and completion events;
- cancellation requests and their accepted/pending/terminal outcomes;
- standard authentication, authorisation, validation, conflict, throttling, and
  server-error envelopes;
- forward-compatible versioning rules that allow Grafana and future Slack
  adapters to consume the same semantic API.

The contract is authoritative for consumer/provider contract tests. The
implementation plan will choose the machine-readable HTTP and event-schema
formats consistent with the accepted ADRs.

---

## Observability Requirements

1. Every Phase 1 component emits OTLP to the self-owned OTel Collector; product
   code does not export directly to an operational or evaluation vendor.
2. OpenLIT instruments model and Tool calls, supplemented by hand-written spans
   for Run lifecycle, graph nodes, Tool Gateway policy decisions, event
   publication, and recovery operations.
3. Every span carries `graft.tenant.id` and `graft.run.id`; model and Tool spans
   also expose the applicable GenAI semantic-convention attributes, token usage,
   duration, outcome, and error classification.
4. The operational telemetry path exposes enough information to diagnose API
   request failures, workflow/step failures, recovery attempts, Tool denials,
   event-stream lag, database-pool wait, and model token/cost consumption.
5. The Collector independently exports operational telemetry and scrubbed
   trajectories to the internal Langfuse sink. Langfuse is never called by the
   product runtime and its outage cannot fail or delay a Run.
6. Audit records are not telemetry: they are complete and unsampled even when
   operational or evaluation telemetry is sampled.
7. Phase 1 verification uses synthetic, non-sensitive investigation data until
   the deferred production PAN-scrubbing acceptance work is complete.

---

## Security and Audit Requirements

1. The harness mints a short-lived, Run-scoped capability token whose audience
   is the Tool Gateway. The Tool Gateway independently validates signature,
   audience, expiry, Run binding, Tenant binding, and allowed ToolClasses.
2. A `system_initiated` capability token can contain `read` only. Effective Tool
   authority is the intersection of the five narrowing layers in ADR-0063; no
   prompt, model output, or custom instruction can widen it.
3. Every customer-system operation uses Tool Gateway → streamable-HTTP MCP.
   Direct customer-system clients and stdio MCP configurations are prohibited
   by automated architecture checks.
4. Tool arguments are schema-validated. Upstream Tool descriptions are treated
   as untrusted data; only curated, hash-pinned registry descriptions enter model
   context.
5. Tenant scope is explicit at every boundary. Application tables use
   `FORCE ROW LEVEL SECURITY` with transaction-scoped `SET LOCAL`; no ambient,
   thread-local, or model-derived Tenant identity is permitted.
6. Every Run lifecycle transition, authentication/authorisation outcome, Tool
   request, Tool result, denial, cancellation, and terminal outcome creates an
   insert-only audit record. The actor is derived from the verified credential,
   never from agent or Tool content.
7. Audit records form a hash-chained DAG with causal links and carry
   `graft_tenant_id`, `graft_run_id`, actor, action, outcome, policy/configuration
   version references, timestamp, and relevant external-reference pointers.
   Phase 1 validates chain integrity and append-only behaviour; WORM anchoring
   and production retention acceptance remain Phase 4.
8. DBOS's separate system database is treated as PCI-DSS in scope. DBOS steps
   return approved pointers rather than raw Tool payloads, secrets, or PANs.
9. Logs, API errors, events, spans, and contract-test fixtures must not expose
   credentials, capability tokens, downstream secrets, or raw sensitive Tool
   payloads.

---

## Review and Acceptance Evidence

- **API review:** the HTTP and event contracts, versioning rules, standard error
  model, idempotency semantics, and compatibility report are reviewed before
  provider implementation is considered complete.
- **Security review:** threat modelling covers authentication, capability-token
  misuse, Tenant-boundary failures, prompt/tool-description injection, replay,
  SSRF through MCP endpoints, secret handling, and event-stream authorisation.
- **Data review:** migrations, RLS policies, privileged migration role, runtime
  role, DBOS system-database separation, and destructive/rollback procedures are
  reviewed together.
- **Durability review:** repeatable evidence covers the three worker-kill points,
  alive-but-silent handling, cancellation boundaries, matching executor and
  application-revision restart recovery, operator escalation, and duplicate-
  call prevention within the permitted recovery boundary. It does not claim
  automatic recovery onto a different executor.
- **Observability review:** representative traces, metrics, logs, audit records,
  Collector routing, and sink-outage behaviour are demonstrated using a single
  correlated `graft_run_id`.
- **Acceptance evidence:** each acceptance criterion has an automated test or a
  named, repeatable verification procedure with command, environment, versions,
  expected result, actual result, and retained CI artefact.

---

## Non-Goals

- Implementing the Slack adapter; Phase 1 defines reusable contract semantics
  only, and Slack remains Phase 3.
- Write or destructive ToolClasses, proposals, approvals, or action execution.
- Shared Runs, driver handover, control-liveness clocks, or collaboration.
- Schedules, second-region deployment, blue/green rollout, quota request flow,
  or production PAN-scrubbing acceptance.
- Multi-model routing, fallback chains, per-node model selection, or exhaustive
  certification of every model integration published by LangGraph.
- Context-compaction mechanics, quantitative eval methodology, or production
  benchmark targets.
- Direct product-runtime dependency on Langfuse or any evaluation sink.

---

## Acceptance Criteria

1. **AC 1 — Contract authority:** A versioned, machine-readable harness contract
   defines Run creation, Run retrieval, cancellation, event replay/streaming,
   event payloads, and standard errors; CI fails on an unreviewed breaking
   contract change.
2. **AC 2 — Consumer/provider compatibility:** Automated contract tests prove
   that the harness provider and Grafana consumer conform to the same contract;
   a transport-independent consumer fixture proves the contract can be consumed
   without Grafana-specific fields, preserving the future Slack boundary.
3. **AC 3 — Alert-to-finding path:** A valid webhook produces exactly one private
   read-only Run and an ordered event sequence ending in a narrated finding
   visible through the Grafana adapter.
4. **AC 4 — Trigger idempotency:** Replaying the same webhook idempotency key does
   not create or execute a second Run and returns the original `graft_run_id`.
5. **AC 5 — Token streaming and replay:** Narrative output is observable as token
   events before Run completion; reconnecting from a recorded
   `graft_event_id` replays every later event exactly once and in order.
6. **AC 6 — Scoped durable recovery (proposed, pending ADR-0078 owner
   acceptance):** Killing the owning worker during an LLM call, during a Tool
   call, and between steps permits the Run to resume and complete only when the
   same executor identity returns and the explicit released application
   compatibility revision matches the Run. Phase 1 must not automatically
   resume a Run on a different executor. An alive-but-silent, ambiguous, or
   stuck Run is durably recorded and escalated to an operator. Within the
   permitted matching-identity restart boundary, an at-least-once retry may
   repeat an in-flight step; receiving-boundary idempotency is required where
   automatic retry is allowed, and completed Tool-side effects or events must
   not be duplicated by the implementation. This criterion is not complete
   until ADR-0078 is accepted and its negative cross-executor and escalation
   evidence is retained.
7. **AC 7 — Step granularity and pointers:** `list_workflow_steps()` shows each
   LLM call and Tool Gateway call as a distinct DBOS step, and automated checks
   reject DBOS steps that return a large or sensitive payload instead of an
   approved pointer type.
8. **AC 8 — Tenant isolation:** Automated tests with at least two Tenants prove
   that application rows, Runs, events, artifacts, and audit records cannot be
   read or written across Tenant scope, including through a transaction-mode
   pooler using `SET LOCAL` and `FORCE ROW LEVEL SECURITY`.
9. **AC 9 — Authority boundary:** A system-initiated Run cannot obtain `write` or
   `destructive` ToolClass capability, and an automated dependency test fails if
   harness code introduces a direct customer-system client outside the Tool
   Gateway/MCP path.
10. **AC 10 — MCP and Tool failure behaviour:** Contract and integration tests
    prove streamable-HTTP MCP invocation, argument validation, typed Tool errors,
    retry/idempotency behaviour, and terminal error propagation without leaking
    uncurated upstream Tool descriptions to the model.
11. **AC 11 — Cancellation:** A cancellation request becomes effective at the
    next DBOS step boundary, emits the contracted events, and does not interrupt
    a step in a way that permits duplicate Tool execution.
12. **AC 12 — Audit and telemetry:** Every Run and Tool call emits Tenant-scoped
    OTel data and an audit record whose actor comes from the verified credential;
    trajectories reach Langfuse through the Collector while the same Run still
    completes when Langfuse is unavailable.
13. **AC 13 — Model portability:** The agent can be composed with a LangGraph
    compatible chat-model test double and with the organisation-approved Phase 1
    model without provider-specific types in graph node signatures; the selected
    model cannot change during a Run.
14. **AC 14 — Phase 1 verification:** Linting, type checking, unit tests, contract
    tests, integration tests, cross-Tenant isolation tests, crash-recovery tests,
    and the end-to-end webhook-to-Grafana test all pass in CI with documented
    local equivalents.
15. **AC 15 — Outstanding DBOS checks:** Phase 1 records repeatable test results
    for async LangGraph/MCP operation, alive-but-silent executor handling,
    executor-filtered workflow listing, matching-executor restart recovery,
    executor/revision rejection, and application-version stability; any failed
    architectural assumption is raised for decision review rather than bypassed.
    No cross-executor automatic recovery is an accepted Phase 1 expectation
    unless a later accepted ADR changes this boundary.
16. **AC 16 — Correlated observability:** A completed Run can be followed from
    inbound API request through workflow, LLM steps, Tool Gateway policy checks,
    MCP calls, event publication, and terminal result using
    `graft.tenant.id` and `graft.run.id`; required operational metrics and typed
    errors are emitted without secrets or raw sensitive Tool payloads.
17. **AC 17 — Telemetry failure isolation:** Integration tests prove the Run
    completes when Langfuse is unavailable and when the Collector export path is
    temporarily unavailable; telemetry recovery does not duplicate audit
    records or product events.
18. **AC 18 — Capability-token security:** Automated negative tests reject bad
    signatures, wrong audiences, expired tokens, mismatched Run/Tenant bindings,
    replay outside the bound Run, and `write`/`destructive` requests from a
    system-initiated Run; each denial is audited.
19. **AC 19 — Audit integrity:** Automated tests prove required actions produce
    unsampled, append-only audit records, verify actor derivation from the
    credential, reject mutation/deletion by the runtime role, and detect a
    broken hash or causal link.
20. **AC 20 — Security and review gates:** The API, security, data/RLS,
    durability, and observability reviews defined in this spec are complete;
    no unresolved critical or high-severity finding remains, and the retained
    acceptance report links every AC to passing evidence.

---

## Definition of Done

Phase 1 is done only when all of the following are true:

- AC 1–AC 20 pass with no skipped mandatory test and with evidence retained by
  CI or the repeatable verification report.
- The versioned API/event contract and generated artefacts are current;
  provider, Grafana consumer, transport-independent consumer, compatibility, and
  breaking-change checks pass.
- The webhook-to-Grafana acceptance path passes in a production-like local or CI
  environment with PostgreSQL, transaction-mode pooling, DBOS, Tool Gateway, a
  streamable-HTTP MCP test server, OTel Collector, and Langfuse.
- Unit, schema, contract, integration, cross-Tenant isolation, architecture,
  security-negative, audit-integrity, crash-recovery, cancellation, telemetry,
  and end-to-end suites pass alongside linting and type checking.
- Database migrations apply from an empty database and from the previous
  supported schema, establish the expected runtime privileges and RLS policies,
  and have a documented recovery procedure.
- The four outstanding DBOS verification results are recorded. A failed locked
  assumption has either been resolved by a reviewed fix consistent with the
  ADRs or escalated through a new ADR; it is not waived silently.
- The proposed ADR-0078 recovery scope change is formally accepted before Phase
  1 completion. Until then, no cross-executor recovery evidence or completion
  claim is permitted; ambiguous and stuck Runs remain an operator-escalation
  case.
- The API, security, data/RLS, durability, and observability reviews are approved
  with no unresolved critical or high-severity finding.
- Operational documentation covers local setup, contract generation/checking,
  test commands, migration, deployment, matching-executor restart recovery,
  operator escalation, Run correlation, common failure diagnosis, and known
  Phase 1 limitations.
- The implementation contains no direct customer-system client, no stdio MCP,
  no Redis event path, no LangGraph checkpointer, no provider-specific model
  type in graph node signatures, and no DBOS import outside the runtime seam.
- Repository documentation checks and the DBOS step-pointer rule pass, and any
  implementation-discovered design change is reflected in the correct living
  design document without modifying accepted ADR decision text.

---

## Constraints

- `docs/GLOSSARY.md` is the normative vocabulary source; all identifiers use the
  owning-system prefixes required by ADR-0059.
- The only module permitted to import DBOS is the internal `runtime` seam.
- LangGraph is compiled without a checkpointer; DBOS is the sole execution
  checkpoint authority.
- PostgreSQL is the only durable event-log substrate; no Redis is introduced.
- Tenant scope is explicit data passed through call boundaries, never ambient or
  thread-local state.
- Application tables use `FORCE ROW LEVEL SECURITY` and transaction-scoped
  `SET LOCAL`; DBOS-owned system tables remain in a separate, PCI-scoped regional
  database and are accessed only through the runtime seam.
- All MCP servers use streamable HTTP; upstream Tool descriptions are untrusted
  and never forwarded directly to the model.
- Phase 1 remains structurally read-only.
- Model selection follows organisation policy and applicable regional,
  residency, compliance, streaming, instrumentation, and context requirements.
- Accepted ADRs are immutable; a discovered contradiction requires a new ADR,
  not an implementation workaround.

---

## Technical Notes

- The repository currently contains architecture documentation, deployment
  configuration, and documentation/static-analysis scripts; there is no
  application package or established application test framework yet.
- `docs/backlog/roadmap.md` sections 3, 4, and 6 define the Phase 1 foundations,
  exit criteria, and closed decision gates.
- `docs/diagrams/c4-l2-containers.md` is the current container-level allocation
  of the Python API, workers, authority service, Grafana frontend/backend,
  PostgreSQL, object storage, secret store, and OTel Collector.
- `docs/design/streaming-and-events.md` owns the event taxonomy and replay model.
- `docs/design/durable-execution.md` owns DBOS/LangGraph composition and lists
  four implementation-time verification items.
- `docs/design/tool-gateway.md` owns the Tool Gateway/MCP authority path.
- `scripts/check_step_pointer_rule.py` is the initial CI invariant for DBOS step
  return types and must be integrated once Python source exists.

---

## Decision Log

| Decision | Rationale |
|----------|-----------|
| Define shared harness contract semantics in Phase 1 but defer the Slack adapter | Preserves the API boundary now without pulling a Phase 3 surface into Phase 1. |
| Treat outstanding DBOS verification as normal Phase 1 tasks | Requested hand-off scope; failures still require decision review rather than silent workarounds. |
| Scope automatic recovery to matching executor identity and released application revision, with operator escalation for ambiguous or stuck Runs | Proposed ADR-0078 records the Gate 0.3 scope change; owner acceptance and its negative evidence remain pending, and no cross-executor recovery completion claim is made. |
| Use contract tests as the primary API integration gate | The harness is API-first and has independently implemented consumers/providers. |
| Rely on LangGraph's model integration boundary | Avoids a redundant harness-specific provider matrix while organisation policy remains authoritative for permitted models. |
| Verify the organisation-approved model plus a model test double | Demonstrates the harness seam without claiming exhaustive compatibility with every changing upstream integration. |
