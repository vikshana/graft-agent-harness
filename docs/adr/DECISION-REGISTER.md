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
| **D9** | **Grafana identity forwarding: `X-Grafana-Id` (ID forwarding, feature toggle `idForwarding`) is the primary inbound authn mechanism** for the Grafana surface, running on **latest Grafana** (D21) since we operate the instance. A plugin-signed-JWT fallback is permitted, but a workspace on fallback trust **cannot approve destructive actions**. `oauthPassThru` is a downstream (D11) concern, not an inbound authn one. **Verified live 2026-09-12** against Grafana OSS `latest` (resolves to v13.0.2): `idForwarding` is enabled by default; the signing-key/JWKS-equivalent endpoint is **`/api/signing-keys/keys`**, not `/.well-known/jwks.json`. | `open-questions/01` A1; `../design/grafana-authz-delegation.md`. |
| **D10** | The harness mints its **own short-lived (~10 min), run-scoped, audience-restricted session/capability token**, independently validated by the Tool Gateway. Revocation via deny-list + short TTL. | `open-questions/01` A2; `../design/audit-and-attribution.md` §5.1. Formalised as an OAuth 2.1 / RFC 8707 audience-bound token by D19. |
| **D11** | Downstream credential strategy is **hybrid, service-identity-by-default**: a workspace service account is always the fallback (required for `system_initiated` runs, D13, and for **all Slack-initiated runs**, D25); user identity is layered on top via **check-then-act** where a live Grafana request context exists. GitHub always acts as a **bot identity** (GitHub App), never impersonating the user. | `open-questions/01` A4; `../design/grafana-authz-delegation.md`. |
| **D12** | **Grafana-side service accounts are self-provisioned imperatively**, using a platform-level Grafana Server Admin credential — **not** a customer admin's session (superseded by D21/D22), and never via `externalServiceAccounts`, confirmed broken for multi-org Grafana. One mechanism covers both the plugin's own enforcement SA and the `grafana-mcp` tool server's SA. Tokens always carry an expiry; role is recomputed to the minimum needed across enabled tools on every policy change. | `../design/grafana-mcp-provisioning.md`. |
| **D13** | **`system_initiated` runs (no human present) are structurally read-only.** Enforced by the run's capability token never containing a write tool class — not by a policy check that could be bypassed. A human approving a proposal upgrades the run to `user_initiated` from that point. | `open-questions/01` A5; `../design/audit-and-attribution.md` §2. |
| **D14** | **Approval is a distinct, human, re-authenticated act that always happens in Grafana**, never in Slack. Slack may trigger, converse, and *launch* an approval via a signed single-use deep link, but never perform it. **Confirmed to hold regardless of Slack platform evolution**: no Slack platform mechanism, including newer ones (D20), provides a per-action re-authentication primitive equivalent to a fresh signed assertion at decision time. Slack's own AI-agent governance guidance (verified live against `docs.slack.dev`, 2026-09-12) treats "approval gates" as a UX pattern, not a re-authentication mechanism — reinforcing, not weakening, this decision. | `open-questions/01` A3; `../diagrams/c4-l1-system-context.md` J4. Direct consequence of D2 (no Web UI). |
| **D15** | **Audit records form an insert-only, hash-chained DAG** (`caused_by` edges from trigger → effect), anchored periodically to WORM object storage. Every record derives its `actor` from the verified credential, never from agent/tool output. `run_id` is propagated **outward** into customer-owned logs (K8s `impersonatedBy`, GitHub commit trailers, datasource query headers). **Retention: 12 months minimum, 3 months hot**, set by the confirmed compliance regime (D26, PCI-DSS). | `../design/audit-and-attribution.md`. |
| **D16** | **Configuration is org-scoped and shared** (workspace = Grafana Org); per-user variation is an **authorisation filter at call time**, never a separate per-user configuration. Enabling a write-capable tool class requires a step-up (re-authenticated) action distinct from ordinary config edits, and is itself an audit record. Tool policy is **versioned, never overwritten**. | `../design/ux-mcp-tool-configuration.md`. Confirmed as the correct default-narrow posture per the interview (write-tool grants expected long-term, read-only-first for v1). |
| **D17** | **Limits form a ceiling chain** — `platform ≥ tenant ≥ workspace ≥ user ≥ run`, effective limit is the minimum across scopes. Platform ceilings are **not customer-raisable**. Per-connection throttles (protecting *customer* infrastructure, e.g. a shared K8s control plane) are keyed by connection, independent of workspace quota. | `../diagrams/c4-l1-system-context.md` J8 / §4. |
| **D18** | **One logical, horizontally-scaled `grafana-mcp` service**, never one process per workspace as a default. Every credential is resolved per call by the Tool Gateway and attached to that call via a forwarded header. Isolation between workspaces comes from the credential Grafana receives per call, not from process/instance separation. The service never reasons about *which human* triggered a call — per-user authorisation is fully resolved before dispatch. **Formerly blocking verification resolved 2026-09-12** by reading the actual OSS `grafana-mcp` source: it supports per-request header forwarding (`GRAFANA_FORWARD_HEADERS`) and a credential-keyed internal client cache, confirming the design is buildable as specified. **New constraint found:** `Authorization` is reserved for `grafana-mcp`'s own caller-auth (`MCP_GRAFANA_SERVER_TOKEN`) and cannot simultaneously carry the downstream Grafana credential — the per-call credential must ride on a different forwarded header (e.g. `Cookie`), or caller-auth at that hop must be dropped in favour of network isolation. | `../design/grafana-mcp-multi-tenancy.md`. |
| **D19** | **The MCP Authorization Server (AS) is a distinct logical component from the Tool Gateway**, which is a Resource Server only — it never issues tokens, only validates them, always independently. The AS is **harness-owned** (a broker in front of the pluggable IdP, since Slack/webhook surfaces have no IdP session and the token needs harness-specific claims). Deployed **co-located with the harness API** in v1. Applies only to the **agent → Tool Gateway** hop. | `../design/mcp-authorization-server.md`. |
| **D20** | **Slack account linking (A3) uses "Sign in with Slack" (OpenID Connect)** rather than a bespoke OAuth flow. Strengthens the one-time link step only; does not change D14. **Verified live against `docs.slack.dev`, 2026-09-12** — OIDC flow, scopes, and endpoints confirmed as described. | `../design/slack-identity-and-surface.md`. |
| **D21** | **The platform owns and operates the Grafana instance; customers are orgs within a single shared instance** — confirmed, not customer-hosted. Grafana runs **OSS**, at **latest release**. | Resolves the "minimum Grafana version" negotiation into a self-service verify-and-ship task; makes multi-org (not single-org) the confirmed default deployment shape, reinforcing D12's move away from `externalServiceAccounts`. |
| **D22** | **Both Grafana service accounts (plugin enforcement SA, `grafana-mcp` SA) are provisioned synchronously at workspace/org creation**, using a platform-level Grafana Server Admin credential. No cold-start gap exists — provisioning is a precondition of a workspace being marked ready, never lazy/first-use. Disabling the Grafana MCP server **fully deprovisions** its SA and token (delete, not downgrade); disabling one tool within an enabled server **recomputes the SA's role to the minimum required**. | `../design/grafana-mcp-provisioning.md`, superseding its earlier admin-session-dependent flow. **New risk to manage:** the platform Server Admin credential is now the single highest-value secret in the system — needs HSM-backed storage, tight rotation, and distinguishable audit signal. **Still open, not yet a locked policy** — see §5 row for `open-questions/01`. |
| **D23** | **Check-then-act enforcement is performed by the Tool Gateway itself**, never delegated to the Grafana plugin backend's assertion. | `../design/grafana-authz-delegation.md` §3.1. Chosen because the Tool Gateway is the actual security boundary, and Slack-triggered runs have no plugin in the request path to delegate to regardless. **Verified live 2026-09-12**: `/api/access-control/user/permissions` is reachable in OSS `latest`, but requires session-cookie auth, not Basic Auth/API key — the Tool Gateway needs a session-capable credential path for this specific call (open item, see `grafana-authz-delegation.md` §7 item 5). |
| **D24** | **Slack-initiated and `system_initiated` runs never receive a per-user Grafana permission check** — both are bounded solely by the workspace service account's own role. Deliberately the simpler path for v1; revisit once PoC usage data justifies the added complexity of per-user checks for Slack. | `../design/grafana-authz-delegation.md` §3.6/§3.7. **Open:** the concrete usage signal that would trigger a revisit is not yet defined; a candidate metric is proposed in `open-questions/01` §0.7 item 1, not yet agreed. |
| **D25** | **Compliance regime for v1 is PCI-DSS.** Drives D15's retention figure and adds a **PAN/cardholder-data scrubbing requirement** to the OTel Collector's existing PII-scrubbing layer (D8) — must detect and strip primary account numbers before they reach either the audit chain or the eval sink, not merely redact after the fact. Also reinforces (does not change) the step-up-auth (D16), least-privilege (D22), and tamper-evidence (D15) designs already in place, each of which maps to a specific PCI-DSS requirement (8.4.2, least-privilege reviews, 10.5.2 respectively). | `../design/audit-and-attribution.md` §7.1. **New engineering work:** Luhn-check-backed PAN detection, not yet designed. |
| **D26** | **Custom-role (fine-grained action/scope) RBAC evaluation is Enterprise-only in Grafana OSS.** Confirmed live 2026-09-12: `POST /api/access-control/roles` 404s against Grafana OSS `latest`. This makes D23/D11's basic-role (Viewer/Editor/Admin) fallback the **only** available enforcement granularity in OSS, not merely a fallback for a hypothetical limitation. | `../design/grafana-authz-delegation.md` §5/§6 decision 5. |
| **D27** | **The MCP client for hop 1 should use `mcp.client.auth.oauth2.OAuthClientProvider`** (from the official `mcp` Python SDK, a dependency of `langchain-mcp-adapters`) as the `auth=` value if/when RFC 9728 discovery is needed, rather than implementing discovery ourselves. `langchain-mcp-adapters` itself does not implement discovery — it only exposes a generic `httpx.Auth` hook — but the underlying SDK's `OAuthClientProvider` is spec-complete (RFC 9728 discovery, 401-triggered re-discovery, PKCE, refresh). Per D19 §5, the interactive parts of this are not needed for hop 1 day one; this decision fixes *which library* to reach for if/when they are. | `../design/mcp-authorization-server.md` §7. |
| **D28** | **Canonical Slack identity keys Grid-linked principals by `enterprise_id` (+ global user id)**, falling back to `team_id`/`slack_workspace_id` (+ user id) for non-Grid, single-workspace installs. Confirmed necessary live against `docs.slack.dev`, 2026-09-12: Enterprise Grid workspaces expose a constant `enterprise_id`, and a single human can hold **distinct per-workspace identities within the same Grid org**, reconciled by Slack via global user IDs — `slack_workspace_id` alone is not a stable enough key once Grid is in play. | `open-questions/01` §0.3; `../design/slack-identity-and-surface.md` §1.3/§5 decision 8. Feeds `open-questions/03-tenancy-and-scoping.md`. |

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

**Per D9–D28:** the Tool Gateway is now the confirmed single place where: the
run-scoped capability token (D10) is validated as an RS per the MCP
Authorization spec (D19, D27); check-then-act (D23) is performed for Grafana-scoped
resources, by the gateway itself; per-call credential attachment (D18) happens
for `grafana-mcp`, on a header other than `Authorization` if `grafana-mcp`'s own
caller-auth is also in use; and every audit record (D15) is emitted. It never mints
tokens — that is the Token Service / AS's job (D19), kept logically separate
even when co-deployed.

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
   OTel Collector  ── PII / secret / PAN scrubbing, sampling, tenant+workspace tagging
        ├──▶ Operational sink: Tempo / Mimir / Loki (or customer's OTLP endpoint)
        └──▶ Eval sink (internal only): Langfuse or Phoenix
                 — trajectory review, prompt version comparison,
                   annotation, eval dataset curation
```

Rationale: LGTM is strong for traces/metrics/logs and weak for *trajectory
review* — comparing prompt v1.2 vs v1.3 across 50 historical incidents,
annotating runs, building eval datasets. Hence two sinks. The one-way rule (D8a)
prevents the eval tool becoming a runtime dependency.

**D8b — open tension, sharper now that compliance is confirmed (D25):**
`audit-and-attribution.md` proposes storing only prompt **hashes** in the audit
chain, with raw prompts living in the eval sink. PCI-DSS makes this more
urgent: a raw prompt could carry a PAN quoted from an investigated log line,
so the eval sink must go through the **same** PAN-scrubbing pipeline as the
audit chain, or it becomes an unscrubbed compliance liability sitting next to
a compliant one. Still contradicts D8a's "never a runtime dependency" framing
for forensics; not resolved, just clarified.

**Open:** Langfuse vs Phoenix for the eval sink; sampling policy (research
suggests 100% for RCA mode; **note audit records themselves are never sampled**,
per D15); whether customers get the operational sink pointed at their own OTLP
endpoint by default.

---

## 4. Strong recommendations pending confirmation

| # | Recommendation | Rationale | Tracked in |
|---|---|---|---|
| R3 | Scope model `Tenant → Workspace (≈ Grafana Org) → Group (IdP) → Principal`; `tenant_id` + `workspace_id` on every row/event/span/audit record, enforced by Postgres RLS from day one | Retrofitting tenancy is the classic expensive rewrite. **Needs a Grid-aware amendment** — see D28: `enterprise_id` may need to be a first-class scoping dimension alongside `workspace_id` for Slack-linked, Grid-hosted principals. | `open-questions/03` |
| R4 | **Investigations are workspace-owned, not user-owned** | Incident response is a team activity; contradicts `research/session.md` deliberately | `open-questions/03` |
| R7 | Back-channel (cancel / signal / steer / approve) is **plain REST**, not WebSocket | Idempotency keys for free; identical from all surfaces | `open-questions/02` |
| R8 | Graph decomposed into **bounded, individually retryable, side-effect-idempotent steps** from day one, behind a `RunController` port | Makes a later Temporal migration a driver swap, not a graph redesign | `open-questions/04` |

*(R5, R6 — the harness session token and hybrid downstream credential
recommendations — are now **locked** as D10 and D11 respectively.)*

---

## 5. Deferred for dedicated deep-dive sessions

| Doc | Decision | Stakes | Status |
|---|---|---|---|
| [`01-identity-and-access.md`](./open-questions/01-identity-and-access.md) | Per-surface authn, canonical identity federation, downstream credential strategy, audit actor model | High — touches every surface and every tool call | 🟢 **Mostly resolved** — D9–D28. **Live-verified 2026-09-12** (ran Grafana OSS, read `mcp-grafana`/`langchain-mcp-adapters` source, fetched current Slack docs) — see its §0.6. Still open: PoC feedback trigger for Slack workspace-SA-ceiling (D24), blast-radius/rotation policy for the platform Grafana Server Admin credential (D22), PAN-scrubbing implementation (D25) |
| [`02-streaming-and-events.md`](./open-questions/02-streaming-and-events.md) | Event schema (AG-UI vs own), durable log substrate, Grafana Live vs SSE, multi-viewer, back-channel, notifications | Medium — contained by D6 | 🔴 Not started |
| [`03-tenancy-and-scoping.md`](./open-questions/03-tenancy-and-scoping.md) | Deployment model, workspace mapping, investigation ownership, role mapping, budget scopes | **High and urgent** — scoping columns must exist before anything writes rows | 🟢 **Deployment model (C1) resolved by D21** — platform-owned, single shared Grafana instance, multi-org. **New input from D28:** the scope model (R3) needs an `enterprise_id` dimension for Grid-linked Slack principals. Workspace-mapping and role-mapping still open |
| [`04-durable-execution.md`](./open-questions/04-durable-execution.md) | Temporal vs Postgres job runner vs bare worker; step granularity; idempotency; cancellation | **Highest — least reversible.** Shapes how the graph itself is decomposed | 🔴 Not started |

---

## 6. UX-first architecture track

Started outside-in per the UX-first working method: journeys first, diagram
derived from journeys, architecture derived from the diagram.

| Doc | Covers | Status |
|---|---|---|
| [`../diagrams/c4-l1-system-context.md`](../diagrams/c4-l1-system-context.md) | System context: actors, surfaces, external systems, v1 scope boundary | 🟡 In review — revision 2 |
| [`../design/audit-and-attribution.md`](../design/audit-and-attribution.md) | Audit chain schema, causal DAG, hash-chain tamper evidence, outward propagation, PCI-DSS retention | 🟢 Retention/compliance resolved; D8b tension open |
| [`../design/grafana-authz-delegation.md`](../design/grafana-authz-delegation.md) | Check-then-act permission enforcement pattern | 🟢 Resolved for v1, **live-verified 2026-09-12** against Grafana OSS `latest` (D26) |
| [`../design/grafana-mcp-provisioning.md`](../design/grafana-mcp-provisioning.md) | Platform-internal, synchronous service-account provisioning | 🟢 Resolved for v1 |
| [`../design/grafana-mcp-multi-tenancy.md`](../design/grafana-mcp-multi-tenancy.md) | Shared `grafana-mcp` service, per-call credential attachment, multi-user handling | 🟢 **Blocking verification resolved 2026-09-12** — real `mcp-grafana` source confirms per-call credential forwarding; one new constraint found (D18) and one implementation choice still open (§6 item 2 in the doc) |
| [`../design/ux-mcp-tool-configuration.md`](../design/ux-mcp-tool-configuration.md) | Admin UX for enabling/scoping MCP tools, step-up flow for write-capable tools | 🟡 In review |
| [`../design/mcp-authorization-server.md`](../design/mcp-authorization-server.md) | MCP Authorization spec (OAuth 2.1 / RFC 9728) applied to our two MCP hops; where the AS lives | 🟡 In review — open question on client-library discovery support **resolved 2026-09-12** (D27); AS placement itself still 🟡 |
| [`../design/slack-identity-and-surface.md`](../design/slack-identity-and-surface.md) | Newer Slack platform mechanisms; confirms D14 holds regardless | 🟢 **Fully verified against live `docs.slack.dev`, 2026-09-12** (previously partially recollection-based) — surfaced a new Grid identity-granularity fact (D28) |

**Next:** L2 Containers. The self-service verification items that were
blocking this (§5's `01-identity-and-access.md` row) were checked against a
live Grafana OSS instance and the real `mcp-grafana`/`langchain-mcp-adapters`
source on 2026-09-12; nothing remaining in that row blocks starting L2. The
three genuinely open items (PoC trigger, credential rotation policy,
PAN-scrubbing implementation) are product/engineering work, not research
gaps, and can proceed in parallel.

---

## 7. Not yet discussed (future rounds)

- **Context assembly & compaction** — layered prompt hierarchy, summariser node, tool-result offloading, prompt caching strategy.
- **Memory & knowledge** — Neo4j/Mem0 deferral, RAG over runbooks, auto-refreshing infrastructure memory.
- **HITL & write-action model** — proposal → approval → execution, confidence thresholds, two-person rules.
- **Model routing & provider strategy** — LiteLLM, local (vLLM/Qwen) vs commercial, per-node model selection, fallbacks.
- **Evals & benchmarks** — incident replay suite, trajectory evals, DeepEval, O11y-Bench, shadow deployments.
- **Config-driven design** — what is config vs code; config schema, validation, versioning, hot reload.
- **Deployment topology** — GCP + AliCloud active-active, GPU serving, self-host vs SaaS, Helm/Terraform. **Note:** D21 resolves this for the Grafana layer specifically (platform-owned, shared, multi-org); the rest of the stack's topology is still open.
- **Cost & safety guardrails** — control-plane throttling, token budgets, circuit breakers, loop breakers.
- **Security** — indirect prompt-injection sanitisation, PII/secret/PAN scrubbing, WORM audit trail. PAN scrubbing now has an owner decision (D25) but no implementation yet. **New:** the platform Grafana Server Admin credential's blast-radius/rotation policy (flagged by D22) is also unimplemented.

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
