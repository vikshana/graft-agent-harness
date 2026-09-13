# Delivery roadmap and quality gates

> ⚠️ **This predates ADR-0029–ADR-0069 and must not be handed to an implementer
> as-is.** It is preserved for its *sequencing discipline and quality gates*,
> which remain sound. Its *technology choices are substantially superseded* —
> see §3 before using any of it.
>
> *Promoted from `research/phases.md` and `research/phase-1.md` during the
> 2026-09-13 ADR migration. Rewriting this against the locked ADRs is an
> outstanding task.*

---

## 1. What is still valid

The **shape** — five phases, each ending in an automated quality gate, with
security and observability built in rather than appended — and specifically:

- A CI gate per phase, not a test phase at the end.
- Infrastructure and model routing before any agent code.
- Security testing that injects real malicious payloads
  (`Ignore previous instructions…`) rather than asserting a filter exists.
- Historical-incident replay as a **promotion gate**, not a nice-to-have.
- A lean first milestone that validates the alert → hypothesis → proposal loop
  before layering on memory and knowledge graphs.

## 2. Phase skeleton (technology claims stripped)

| Phase | Goal | Quality gate |
|---|---|---|
| **1. Foundation** | Monorepo (`/api`, `/worker`, `/infra`), local compose → K8s manifests, Postgres, model routing | Lint (Ruff), type check (MyPy), container boot health checks |
| **2. API & streaming** | Stateless API, authn middleware, run dispatch, event streaming | Integration tests: invalid-token rejection; event streaming under concurrent clients |
| **3. Agent core & tools** | Agent loop; tool access via the Tool Gateway; read-through cache on hot read tools | Unit tests with mocked tool responses verifying state transitions and **recovery across simulated worker crashes** |
| **4. Guardrails** | Injection sanitisation between tool output and model context; circuit breakers; budget caps | Security suite injecting malicious log payloads; assert stripping happens *before* the LLM |
| **5. RCA, HITL & telemetry** | Triage / evidence / hypothesis nodes; approval gate; OTel instrumentation; replay evals | E2E: alert → evidence → HITL pause → clean traces |

Read-through caching on K8s read tools (short TTL) to prevent control-plane
saturation during incident bursts remains a good idea and is now a Tool Gateway
responsibility ([`../design/tool-gateway.md`](../design/tool-gateway.md)).

## 3. Superseded technology claims — do not carry forward

| Original claim | Now |
|---|---|
| "Integrate **Temporal** or Celery" | **DBOS Transact**, an embedded MIT library on our existing Postgres. Temporal and paid orchestration services excluded by product constraint (ADR-0037) |
| "**Redis**/Valkey cache & pub/sub", "Redis Pub/Sub channels" | **Postgres only, no Redis** (ADR-0030). Fan-out via `LISTEN/NOTIFY` |
| "SSE streaming to the frontend" | **Grafana Live** for the Grafana surface (ADR-0031); SSE only for the post-v1 web frontend |
| "LangGraph workflows backed by Postgres **checkpointing**" | **No checkpointer** (ADR-0040). DBOS step checkpoints are the single source of execution truth |
| "Pause execution via **LangGraph checkpoints**" for HITL | `DBOS.recv(topic, timeout)` (ADR-0045), bounded at ≥72 h (ADR-0066) |
| Phase 4 "**MicroVM sandbox** (Daytona/E2B)" | **No arbitrary code execution in v1** (ADR-0004). Sandbox is Phase 2; only the `ToolExecutor` seam ships now |
| "**Keycloak**" as the auth system | Pluggable IdP; **the IdP authenticates, the harness authorizes** (ADR-0056). Keycloak is one interchangeable option, not the design |
| "Integrate MCP clients for K8s, GitHub, Jira" *in the worker* | The **agent never calls MCP servers directly** (ADR-0007, ADR-0068) — only the Tool Gateway does |
| "Extract user context for downstream **impersonation**" | Hybrid, **service-identity-by-default** (ADR-0011); GitHub always acts as a bot identity, never impersonating |
| Frontend is "the frontend" | v1 surfaces are the **Grafana plugin and Slack** (ADR-0002); custom web UI is post-v1 |
| "Confidence ≥ 80 % → generate PR → `hitl_required`" | Directionally right, but approval authority, re-authentication and expiry are now governed by ADR-0014 / ADR-0065 / ADR-0066 |

## 4. Phase-1 scope, restated

The lean-MVP instinct holds: validate **alert → evidence → hypothesis →
proposal** before adding knowledge graphs or memory daemons.

**Deferred, confirmed by decision:** Neo4j knowledge graph, Mem0 auto-refresh,
multi-agent swarms, dynamic multi-model routing with automatic fallbacks, shadow
A/B testing, sandboxed code execution.

**Not deferrable, contrary to the original plan:** multi-tenancy scoping. The
scoping key must exist on every row from the first migration (ADR-0051,
ADR-0050) — retrofitting a scoping column below every row is the expensive
rewrite this project explicitly avoided.

## 5. Outstanding task

Rewrite §2 as a real plan against the locked ADRs, with the two blocking spikes
from [`future-sessions.md`](./future-sessions.md) resolved first, since both can
invalidate container shapes.
