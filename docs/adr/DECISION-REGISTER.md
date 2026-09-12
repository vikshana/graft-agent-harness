# Decision Register (WIP — not ADRs)

Working scratchpad for the design interview. ADRs are written only once the
architecture is locked and demonstrably composable. Nothing here is final unless
marked **LOCKED**.

**Deep-dive briefings** for the four deferred decisions live in
[`open-questions/`](./open-questions/). Each is self-contained and intended to be
taken into its own session.

**UX-first architecture work** (system context, identity flows, admin config
UX) lives in [`../diagrams/`](../diagrams/) and [`../design/`](../design/).

---

## 1. Locked decisions

| # | Decision | Notes |
|---|---|---|
| **D1** | Grafana integration via the **plugin backend (Go) proxy**, not browser→API direct. Custom frontend calls the API directly. Two callers, one API. | Avoids CORS/token leakage; uses Grafana secret storage. |
| **D2** | Trigger surfaces for v1: **Grafana App Plugin and Slack** with a standardised normalised event for webhooks (Grafana Alerting / Alertmanager). **Custom Web UI dropped from v1**, deferred post-v1, same API, no private capabilities. | Superseded from "custom UI, Slack, webhook" — see `open-questions/01` §0.1. Auto-triggered RCA off by default per workspace. |
| **D3** | Agent framework: **LangGraph + DeepAgents**. | Graph nodes written as plain functions; no framework types in node signatures. |
| **D4** | **No arbitrary code execution in v1.** Read-only tools + server-side result reduction. Sandbox deferred to Phase 2. | |
| **D4a** | A `ToolExecutor` / sandbox seam must exist in v1 so Phase 2 adds micro-VM execution without a rewrite. | The Tool Gateway (D7) is that seam. |
| **D5** | Observability is **OTel-native**. OTLP to a self-owned Collector; the Collector fans out. | |
| **D6** | Streaming is **decoupled from orchestration** via a durable event log. One internal event model; surfaces are thin adapters. | Consequence: the orchestrator choice does not affect streaming. |
| **D7** | **Tool Gateway** — the agent never calls MCP servers directly. A **separate service**, not a library, because in-process policy enforcement is not a security boundary (primary threat: indirect prompt injection from application logs). | See §2 for its shape and responsibilities. |
| **D7a** | **All MCP servers are streamable-HTTP, never stdio.** | stdio MCP is single-identity by construction — no per-user RBAC, no central throttling point. |
| **D7b** | The Tool Gateway **speaks MCP in both directions**: an MCP server to the agent, an MCP client to upstreams. LangChain's `langchain-mcp-adapters` points at exactly one endpoint. | Keeps the agent framework trivial and the gateway framework-agnostic. |
| **D8** | Instrumentation: **OpenLIT + hand-written spans** for graph nodes and domain semantics → **OTLP → Collector → multi-sink**. | See §3. |
| **D8a** | **Two sinks, two jobs:** operational observability (traces/metrics/logs) and an **internal-only** trajectory/eval sink. **No product feature may read from the eval sink's API.** | Keeps Langfuse/Phoenix a dev-loop tool, never a runtime dependency. Tension flagged: see D8b. |
| **D9** | **Grafana identity forwarding: `X-Grafana-Id` (ID forwarding, feature toggle `idForwarding`) is the primary inbound authn mechanism** for the Grafana surface. A plugin-signed-JWT fallback is permitted per-workspace, but a workspace on fallback trust **cannot approve destructive actions**. `oauthPassThru` is a downstream (D11) concern, not an inbound authn one. | `open-questions/01` A1; detail in `../design/grafana-authz-delegation.md`. **Blocking verification:** minimum Grafana version for `idForwarding` — see §5. |
| **D10** | The harness mints its **own short-lived (~10 min), run-scoped, audience-restricted session/capability token**, independently validated by the Tool Gateway. Revocation via deny-list + short TTL. | `open-questions/01` A2; `../design/audit-and-attribution.md` §5.1. |
| **D11** | Downstream credential strategy is **hybrid, service-identity-by-default**: a workspace service account is always the fallback (required for `system_initiated` runs, D13); user identity is layered on top via **check-then-act** (authorise against the user's own Grafana permissions, execute via the service account) where available. GitHub always acts as a **bot identity** (GitHub App), never impersonating the user. | `open-questions/01` A4; `../design/grafana-authz-delegation.md`. |
| **D12** | **Grafana-side service accounts are self-provisioned imperatively, per org**, by the harness calling Grafana's own API (`POST /api/serviceaccounts`) using the acting admin's org-scoped session — **never** via `externalServiceAccounts`, which is confirmed broken for multi-org Grafana. One mechanism covers both the plugin's own enforcement SA and the `grafana-mcp` tool server's SA. Tokens always carry an expiry; role is recomputed to the minimum needed across enabled tools on every policy change. | `../design/grafana-mcp-provisioning.md`. Manual paste is a constrained fallback only. |
| **D13** | **`system_initiated` runs (no human present) are structurally read-only.** Enforced by the run's capability token never containing a write tool class — not by a policy check that could be bypassed. A human approving a proposal upgrades the run to `user_initiated` from that point. | `open-questions/01` A5; `../design/audit-and-attribution.md` §2. |
| **D14** | **Approval is a distinct, human, re-authenticated act that always happens in Grafana**, never in Slack. Slack may trigger, converse, and *launch* an approval via a signed single-use deep link, but never perform it. | `open-questions/01` A3; `../diagrams/c4-l1-system-context.md` J4. Direct consequence of D2 (no Web UI). |
| **D15** | **Audit records form an insert-only, hash-chained DAG** (`caused_by` edges from trigger → effect), anchored periodically to WORM object storage. Every record derives its `actor` from the verified credential, never from agent/tool output. `run_id` is propagated **outward** into customer-owned logs (K8s `impersonatedBy`, GitHub commit trailers, datasource query headers) so customers can verify independently of trusting our logs. | `../design/audit-and-attribution.md`. |
| **D16** | **Configuration is org-scoped and shared** (workspace = Grafana Org); per-user variation is an **authorisation filter at call time**, never a separate per-user configuration. Enabling a write-capable tool class requires a step-up (re-authenticated) action distinct from ordinary config edits, and is itself an audit record. Tool policy is **versioned, never overwritten** — a run keeps the policy live at its start for its whole lifetime. | `../design/ux-mcp-tool-configuration.md`. |
| **D17** | **Limits form a ceiling chain** — `platform ≥ tenant ≥ workspace ≥ user ≥ run`, effective limit is the minimum across scopes. Platform ceilings are **not customer-raisable**. Per-connection throttles (protecting *customer* infrastructure, e.g. a shared K8s control plane) are keyed by connection, independent of workspace quota. | `../diagrams/c4-l1-system-context.md` J8 / §4. |
| **D18** | **One logical, horizontally-scaled `grafana-mcp` service**, never one process per workspace as a default. No credential is ever baked in at startup — every credential is resolved per call by the Tool Gateway and attached to that call. Isolation between workspaces comes from the token Grafana receives per call, not from process/instance separation. The service never reasons about *which human* triggered a call — per-user authorisation is fully resolved before dispatch. | `../design/grafana-mcp-multi-tenancy.md`. **Blocking verification:** does upstream OSS `grafana-mcp` support per-call credential override, or only a startup-time token (§4)? |

---

## 2. Tool Gateway (D7) — responsibilities

```
LangGraph / DeepAgents ──MCP──▶ Tool Gateway ──MCP──▶ k8s-mcp, grafana-mcp,
  (MultiServerMCPClient,        (MCP server to agent,      github-mcp, jira-mcp, …
   one endpoint)                 MCP client to upstreams)
                                        │
                       identity binding · authz / tool allow-listing
                       workspace credential resolution (vault)
                       read-through cache · rate limiting
                       result reduction · audit emission
                       destructive-action HITL gate
                       Phase 2: sandboxed execution
```

Division of labour with LangChain:

| Concern | Owner |
|---|---|
| Tool discovery, schema binding, tool selection | LangChain (`langchain-mcp-adapters`) |
| Retry / telemetry wrapping in-process | LangChain middleware |
| Identity binding, authz, credentials, cache, rate limit, audit, HITL gate, result reduction | **Tool Gateway (separate service)** |

Additional benefits: non-LangGraph consumers (Slack quick-actions, the braindump's
*"single call for specific task/tool"*) can use it directly; the agent framework
stays swappable.

**Per D9–D18:** the Tool Gateway is now the confirmed single place where: the
run-scoped capability token (D10) is validated; check-then-act (D11) is
performed for Grafana-scoped resources; per-call credential attachment (D18)
happens for `grafana-mcp`; and every audit record (D15) is emitted.

**To do:** spike existing OSS MCP gateways (IBM ContextForge, Docker MCP Gateway,
Lasso mcp-gateway, Obot) as reference/adopt candidates — **verify maturity, do not
assume**. Expect none to cover workspace-scoped credential binding + K8s
impersonation + our HITL model.

---

## 3. Observability pipeline (D8)

```
OpenLIT auto-instrumentation (LiteLLM, vLLM, LangChain, vector DBs, GPU metrics)
  + hand-written spans (LangGraph nodes, Tool Gateway calls, domain events)
        │ OTel GenAI semconv
        ▼
   OTel Collector  ── PII / secret scrubbing, sampling, tenant+workspace tagging
        ├──▶ Operational sink: Tempo / Mimir / Loki (or customer's OTLP endpoint)
        └──▶ Eval sink (internal only): Langfuse or Phoenix
                 — trajectory review, prompt version comparison,
                   annotation, eval dataset curation
```

Rationale: LGTM is strong for traces/metrics/logs and weak for *trajectory
review* — comparing prompt v1.2 vs v1.3 across 50 historical incidents,
annotating runs, building eval datasets. Hence two sinks. The one-way rule (D8a)
prevents the eval tool becoming a runtime dependency.

**D8b — open tension, not yet resolved:** `audit-and-attribution.md` proposes
storing only prompt **hashes** in the audit chain (for PII safety), with raw
prompts living in the eval sink. That makes the eval sink load-bearing for
post-incident forensics, which contradicts D8a's "never a runtime dependency"
framing. Needs an explicit decision, not a default.

**Open:** Langfuse vs Phoenix for the eval sink; sampling policy (research
suggests 100% for RCA mode; **note audit records themselves are never sampled**,
per D15 — this is a distinct store from telemetry); whether customers get the
operational sink pointed at their own OTLP endpoint by default.

---

## 4. Strong recommendations pending confirmation

| # | Recommendation | Rationale | Tracked in |
|---|---|---|---|
| R3 | Scope model `Tenant → Workspace (≈ Grafana Org) → Group (IdP) → Principal`; `tenant_id` + `workspace_id` on every row/event/span/audit record, enforced by Postgres RLS from day one | Retrofitting tenancy is the classic expensive rewrite | `open-questions/03` |
| R4 | **Investigations are workspace-owned, not user-owned** | Incident response is a team activity; contradicts `research/session.md` deliberately | `open-questions/03` |
| R7 | Back-channel (cancel / signal / steer / approve) is **plain REST**, not WebSocket | Idempotency keys for free; identical from all surfaces | `open-questions/02` |
| R8 | Graph decomposed into **bounded, individually retryable, side-effect-idempotent steps** from day one, behind a `RunController` port | Makes a later Temporal migration a driver swap, not a graph redesign | `open-questions/04` |

*(R5, R6 — the harness session token and hybrid downstream credential
recommendations — are now **locked** as D10 and D11 respectively.)*

---

## 5. Deferred for dedicated deep-dive sessions

| Doc | Decision | Stakes | Status |
|---|---|---|---|
| [`01-identity-and-access.md`](./open-questions/01-identity-and-access.md) | Per-surface authn, canonical identity federation, downstream credential strategy, audit actor model | High — touches every surface and every tool call | 🟢 **Mostly resolved** — D9–D18. Open: min Grafana version for `idForwarding`, compliance regime, cold-start provisioning, `grafana-mcp` credential-override support |
| [`02-streaming-and-events.md`](./open-questions/02-streaming-and-events.md) | Event schema (AG-UI vs own), durable log substrate, Grafana Live vs SSE, multi-viewer, back-channel, notifications | Medium — contained by D6 | 🔴 Not started |
| [`03-tenancy-and-scoping.md`](./open-questions/03-tenancy-and-scoping.md) | Deployment model, workspace mapping, investigation ownership, role mapping, budget scopes | **High and urgent** — scoping columns must exist before anything writes rows | 🟡 Partially informed by D16/D17; deployment model (C1) still open |
| [`04-durable-execution.md`](./open-questions/04-durable-execution.md) | Temporal vs Postgres job runner vs bare worker; step granularity; idempotency; cancellation | **Highest — least reversible.** Shapes how the graph itself is decomposed | 🔴 Not started |

---

## 6. UX-first architecture track (new)

Started outside-in per the UX-first working method: journeys first, diagram
derived from journeys, architecture derived from the diagram.

| Doc | Covers | Status |
|---|---|---|
| [`../diagrams/c4-l1-system-context.md`](../diagrams/c4-l1-system-context.md) | System context: actors, surfaces, external systems, v1 scope boundary | 🟡 In review — revision 2 |
| [`../design/audit-and-attribution.md`](../design/audit-and-attribution.md) | Audit chain schema, causal DAG, hash-chain tamper evidence, outward propagation | 🟡 In review |
| [`../design/grafana-authz-delegation.md`](../design/grafana-authz-delegation.md) | Check-then-act permission enforcement pattern | 🟡 In review |
| [`../design/grafana-mcp-provisioning.md`](../design/grafana-mcp-provisioning.md) | Imperative, per-org service-account provisioning (supersedes `externalServiceAccounts`) | 🟡 In review |
| [`../design/grafana-mcp-multi-tenancy.md`](../design/grafana-mcp-multi-tenancy.md) | Shared `grafana-mcp` service, per-call credential attachment, multi-user handling | 🟡 In review |
| [`../design/ux-mcp-tool-configuration.md`](../design/ux-mcp-tool-configuration.md) | Admin UX for enabling/scoping MCP tools, step-up flow for write-capable tools | 🟡 In review |

**Next:** L2 Containers, once `open-questions/01` §0.4's blocking items
(Grafana version, `grafana-mcp` credential-override support) are verified.

---

## 7. Not yet discussed (future rounds)

- **Context assembly & compaction** — layered prompt hierarchy, summariser node, tool-result offloading, prompt caching strategy.
- **Memory & knowledge** — Neo4j/Mem0 deferral, RAG over runbooks, auto-refreshing infrastructure memory.
- **HITL & write-action model** — proposal → approval → execution, confidence thresholds, two-person rules.
- **Model routing & provider strategy** — LiteLLM, local (vLLM/Qwen) vs commercial, per-node model selection, fallbacks.
- **Evals & benchmarks** — incident replay suite, trajectory evals, DeepEval, O11y-Bench, shadow deployments.
- **Config-driven design** — what is config vs code; config schema, validation, versioning, hot reload.
- **Deployment topology** — GCP + AliCloud active-active, GPU serving, self-host vs SaaS, Helm/Terraform.
- **Cost & safety guardrails** — control-plane throttling, token budgets, circuit breakers, loop breakers.
- **Security** — indirect prompt-injection sanitisation, PII/secret scrubbing, WORM audit trail.

---

## 8. Capability inventory (from `research/Agent Harness.csv`)

Braindump triaged into domains. Each item still needs **keep / defer / drop** and a
concrete tool choice.

**Orchestration & agent loop** — agent loop, planner, workers, validator, router, sub-agents, specialised agents, intent, hypothesis, RCA, chat, shallow vs deep research, split conversation, framework (LangGraph / LangChain / DeepAgents).

**Context management** — context compaction, context offloading, state, memory, knowledge graph, custom user instructions, rules, agent steering, caching, "store result in memory, pass schema only, let the agent query it via jq/yq".

**Interfaces** — Grafana App, custom UI, API-first, Slack agent, AG-UI, React, MCP Apps, interactive, artifacts, mermaid graphs, follow-up questions, `@context` (datasource/dashboard/panel/alert), jump-to Explore/Dashboard/Alert, data visualisation, per-message feedback icon, per-conversation feedback modal, token usage/budget display, quota indicator, tool-call input/output display, scroll-to-last, usage tips, custom doc links.

**Observability (of the agent)** — tracing, logs, metrics, trajectories, feedback, token count, LangFuse, LGTM.

**Observability (as the problem domain)** — dashboards, alerts, investigations, dashboard queries, recording rules, search (SearXNG, qsearch, Camoufox), K8s, GCP.

**Tools & integrations** — MCP client, tool registry, tool use, single call for a specific task/tool, GitHub, Jira, Slack, ServiceNow, ITSI, iLert, Harbor, K8s, GCP, build, deploy.

**Security & governance** — guardrails, sandbox, governance, authn, authz, HITL, rate limiting, max tool calls, token budget, NeMo, OpenShell, Arrakis, Kata Containers, Firecracker, Cloud Hypervisor.

**Models** — multi-model, cross-provider models, Python/TypeScript runtime split.

**Evals** — evals, benchmark, DeepEval, O11y-Bench.
