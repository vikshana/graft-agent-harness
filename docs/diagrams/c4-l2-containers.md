# C4 Level 2 — Containers

> **Status: 🟡 In review — revision 2.**
>
> Derived from [`c4-l1-system-context.md`](./c4-l1-system-context.md) r4, the
> [Decision Register](../adr/DECISION-REGISTER.md) (D1–D69) and the eleven design
> documents in [`../design/`](../design/).
> [`../GLOSSARY.md`](../GLOSSARY.md) is normative — where this document conflicts
> with it, this document is a bug.
>
> **Changes in r2 (decisions taken 2026-09-13):**
>
> | # | Change | Driver |
> |---|---|---|
> | 1 | **Token Service, Tool Gateway and Tool Registry merge into one deployable — the Authority Service.** Three containers become one, with three modules and five enforced invariants. | D69 |
> | 2 | **No direct clients on customer systems.** `k8s-mcp` is now an invariant, not a preference; `pagerduty-mcp` added. | D68 |
> | 3 | **Approval follows the driver**, so §4.4 and the authority model change, and a **fifth flow** (§4.5, control liveness) is added. | D65, D66 |
> | 4 | **`run_control` added to Postgres**; the 30s control sweep added to scheduled workflows. | D66 |
>
> **Rule for this level:** every container here must be traceable to a **locked
> decision**, not to an implementation preference. §8 lists what was deliberately
> *not* made a container, and why — that list is as load-bearing as the diagram.

---

## 1. What L1 forced

L1 committed to sixteen things. Seven of them cannot be honoured by a monolith,
and those seven are what the container boundaries are actually made of.

| L1 commitment | Container it forces | Why a boundary, not a module |
|---|---|---|
| **3** — read/write architecturally separate | **Authority Service**, separate from the workers | In-process policy enforcement is not a security boundary. The primary threat is **indirect prompt injection from application logs** — text the agent reads and then acts on. A library the agent imports is inside the blast radius; a network service with its own token validation is not (D7). |
| **4** — approval by the current driver, re-authenticated in Grafana | **Grafana plugin backend** + **Token Service module** + **`run_control` state** | The identity assertion (`X-Grafana-Id`) exists only on the Grafana request path, and *who holds the wheel* is server-side state that must be evaluated even when every client is gone (D9, D66). |
| **5** — no ambient credentials, no ambient Tenant context | **Authority Service** + **Secret Store** | Credential resolution happens per call, keyed by `graft_tenant_id`, in a process the agent cannot introspect (D50, D18). |
| **10** — capability is a five-layer intersection | **Authority Service** (gateway + registry modules) | L5 must re-evaluate *per call*, which is what makes the L2 kill switch effective on in-flight Runs (D63). |
| **13** — run data never leaves its home region | **Regional deployment boundary** + **Tenant Directory** | Two independent stacks, one globally-replicated metadata-only directory. Not a config flag (D49). |
| **14** — the durable wait is the product | **Orchestrator workers** with DBOS embedded + **Postgres** | A multi-hour HITL wait cannot be a process staying alive. It is a database row and a `recv` (D37, D45, D47). |
| **15** — no direct clients on customer systems | **MCP server fleet** | The lattice, credential resolution, throttles, result reduction and audit all live at the gateway. A direct client bypasses five controls at once — and is invisible in the audit chain rather than merely undesirable (D68). |

Everything else is a consequence.

---

## 2. The diagram

```mermaid
flowchart TB

  %% ================= PEOPLE =================
  subgraph PEOPLE["Principals"]
    direction LR
    HUMAN["<b>On-call / SRE / Tenant Admin</b><br/><i>[Person]</i>"]
    PLATOP["<b>Platform Operator</b><br/><i>[Person]</i><br/>Never drives, never approves"]
  end

  %% ================= EDGE SURFACES =================
  subgraph EDGE["Surfaces — thin adapters, no private capability"]
    direction LR

    subgraph PLUGIN["Grafana App Plugin"]
      direction TB
      PFE["<b>Plugin Frontend</b><br/><i>[Container: TypeScript, React, @grafana/ui]</i><br/>Panels, full-page routes, config pages.<br/>Subscribes to Grafana Live for<br/>token-level streaming.<br/>Diff view for proposed changes.<br/><b>Driver badge, T−60s keep-control prompt.</b><br/>D1, D29, D31, D34, D66"]
      PBE["<b>Plugin Backend</b><br/><i>[Container: Go, Grafana plugin SDK]</i><br/>Proxies browser → Harness API.<br/>Grafana Live StreamHandler:<br/>SubscribeStream / RunStream / PublishStream.<br/><b>Subscribe/teardown is the disconnect-clock signal.</b><br/>Channel authz against plugin-context identity<br/>and Run ownership. Forwards X-Grafana-Id verbatim.<br/><b>Never asserts authorization itself</b> — D23, D66"]
      PFE -->|"REST + Live<br/>WebSocket"| PBE
    end

    SLACKAD["<b>Slack Adapter</b><br/><i>[Container: Python]</i><br/>Socket Mode outbound WebSocket.<br/>Resolves Tenant via SlackChannel binding<br/>or per-Principal default.<br/>Issues link prompts to unverified users.<br/><b>Batched / throttled output only.</b><br/>Signed single-use approval deep links.<br/><b>No transport liveness → idle clock only.</b><br/>D20, D34, D51, D52, D61, D66"]

    HOOK["<b>Webhook Ingress</b><br/><i>[Container: Python]</i><br/>Grafana Alerting / Alertmanager →<br/>normalised event. Verifies shared secret.<br/>Tenant from source GrafanaOrg.<br/>deduplication_id on the queue.<br/>D2, D42, D51"]

    WEBFE["<b>Web Frontend</b><br/><i>[DEFERRED — post-v1]</i><br/>Same API. OIDC + explicit<br/>Tenant switcher. D2, D64"]
  end

  %% ================= CORE =================
  subgraph CORE["Harness core — one regional deployment"]
    direction TB

    API["<b>Harness API</b><br/><i>[Container: Python, FastAPI]</i><br/>The single API. Forwards <b>every</b> inbound surface<br/>credential verbatim to the AS — never asserts identity<br/>on a caller's behalf.<br/>REST back-channel: cancel · signal · approve ·<br/><b>request/grant/release/force-release control</b> —<br/>idempotency-keyed, identical across all surfaces.<br/>Run list (Mine / Tenant). Artifact fetch.<br/>Cross-region read proxy.<br/>D1, D33, D34, D49, D64, D66, D69"]

    ORCH["<b>Orchestrator Workers</b><br/><i>[Container: Python StatefulSet, DBOS Transact embedded]</i><br/>The Run <b>is</b> the durable workflow (Pattern B).<br/>Parent = Run · child = sub-agent · step = 1 LLM or 1 tool call.<br/>Partitioned durable queues keyed by graft_tenant_id.<br/>send/recv for HITL waits and steering signals.<br/>Blue/green executor IDs, auto-hashed app version.<br/><b>All Runs enqueued, never started in-process.</b><br/>D37–D48"]

    AGENT["<b>Agent Graph</b><br/><i>[Component inside the worker: LangGraph + DeepAgents]</i><br/>Compiled with <b>no checkpointer</b> — DBOS steps are the<br/>single source of execution truth.<br/>Planner, sub-agents, hypothesis, evidence.<br/>Max depth ~15, loop breakers, per-Run token caps.<br/>Prompt layers: platform → Tenant → Principal.<br/>D3, D39, D40, D44, D62"]

    RUNTIME["<b>runtime seam</b><br/><i>[Component: the sole importer of dbos]</i><br/>enqueue_run · await_human · signal · sleep_until ·<br/>cancel · resume · fork · list_*<br/>The natural chokepoint for audit emission, event<br/>publication, Tenant scoping and ceiling checks.<br/><b>Not a swappable engine port.</b> D48"]

    REAPER["<b>Scheduled Workflows</b><br/><i>[Container: DBOS scheduled workflows]</i><br/>Version-aware <b>reaper</b> (resumes stale executors'<br/>PENDING work onto a live matching-version worker).<br/><b>Control sweep every 30s</b> — idle and disconnect clocks.<br/>Tenant backfill + SA <b>drift reconciler</b>, token rotation,<br/>infra-memory refresh */15, stale-Run auto-close,<br/>approval expiry. D38, D47, D53, D58, D66"]

    ORCH --- AGENT
    ORCH --- RUNTIME
  end

  %% ================= AUTHORITY =================
  subgraph AUTH["Authority Service — one deployable, three modules, separate ports. D69"]
    direction TB
    TOKEN["<b>Token Service / MCP AS</b> <i>[module]</i><br/>Verifies <b>raw</b> surface credentials itself:<br/>X-Grafana-Id against <code>/api/signing-keys/keys</code>,<br/>Slack linked Principal, webhook secret.<br/>Resolves Principal → Role → Tenant. Decides initiation_mode.<br/>Mints the <b>run capability token</b>: ~10 min,<br/>aud=tool-gateway, allowed_tool_classes[].<br/>Publishes OIDC discovery + JWKS.<br/><b>Sole holder of the signing key. Issues only.</b><br/>D9, D10, D19, D27, D56, D63-L4"]
    GW["<b>Tool Gateway</b> <i>[module]</i><br/><b>The security boundary — separate process from the agent.</b><br/>Resource Server only. Validates tokens <b>independently</b><br/>over the published JWKS, <b>including on loopback</b>.<br/><b>Holds the public JWKS and nothing else.</b><br/>Publishes RFC 9728 protected-resource metadata.<br/>Enforces the five-layer lattice at <b>L5, per call</b>.<br/>Check-then-act against the Principal's own Grafana permission.<br/>Resolves Tenant credentials per call. Per-connection throttles.<br/>Result reduction + artifact offload. Audit emission. HITL gate.<br/><b>ToolExecutor seam for the Phase-2 sandbox.</b><br/>D4a, D7, D7a, D7b, D18, D23, D34, D44, D63, D68"]
    REG["<b>Tool Registry</b> <i>[module]</i><br/>Tool definitions <b>pinned by hash</b> — a changed upstream<br/>name/description/schema is <b>not enabled</b> until re-approved.<br/>ToolClass, required Role, <b>our curated description</b>.<br/>Upstream descriptions stored for diffing only,<br/><b>never forwarded to the model</b>.<br/>Discovery yields review candidates, never capability. D63"]
    GW --- REG
  end

  %% ================= MCP SERVERS =================
  subgraph MCPS["Upstream MCP servers — streamable HTTP only, never stdio. The ONLY path to a customer system. D7a, D68"]
    direction LR
    GMCP["<b>grafana-mcp</b><br/><i>[Container: Go — one logical service,<br/>stateless, horizontally scaled]</i><br/>GRAFANA_FORWARD_HEADERS=Authorization.<br/>Client cache keyed by credential.<br/>Isolation comes from the SA token per call,<br/><b>not</b> from process separation.<br/>Built-in caller-auth <b>not used</b>. D18"]
    KMCP["<b>k8s-mcp</b><br/><i>[Container]</i><br/>Impersonation headers carry<br/>graft_run_id outward.<br/><b>Design pending</b> — §9. D11, D15, D68"]
    GHMCP["<b>github-mcp</b><br/><i>[Container]</i><br/>GitHub App <b>bot identity</b>,<br/>never user impersonation. D11"]
    ITMCP["<b>jira / servicenow-mcp</b><br/><i>[Container]</i>"]
    PDMCP["<b>pagerduty / ilert-mcp</b><br/><i>[Container]</i><br/><b>read class only in v1.</b><br/>Suppression and maintenance<br/>windows <b>hard-denied at L2,<br/>permanently</b>. D67"]
    SBX["<b>Sandbox Executor</b><br/><i>[DEFERRED — Phase 2]</i><br/>Micro-VM. Seam exists now. D4"]
  end

  %% ================= DATA =================
  subgraph DATA["State — per region, never leaves it (D49)"]
    direction LR
    PG[("<b>Postgres</b><br/><i>[Container]</i><br/>Run state · <b>run_control</b> (driver, clocks) ·<br/><b>event log</b> (monotonic graft_event_id,<br/>LISTEN/NOTIFY fan-out, indexed replay) ·<br/><b>audit chain</b> (insert-only, hash-chained causal DAG) ·<br/>DBOS system DB · tool policy versions ·<br/>graft_ref_kind / graft_external_ref · heartbeats.<br/><b>FORCE ROW LEVEL SECURITY</b> on graft_tenant_id,<br/>established with <b>SET LOCAL</b>, never SET.<br/>D15, D30, D37, D50, D60, D66")]
    OBJ[("<b>Object Storage</b><br/><i>[Container]</i><br/>Tool artifacts (steps return pointers,<br/>never payloads) + <b>object-lock WORM</b><br/>anchors for audit chain heads.<br/>D15, D34, D41")]
    VAULT[("<b>Secret Store</b><br/><i>[Container]</i><br/>Tenant-scoped downstream credentials,<br/>namespaced by graft_tenant_id.<br/>Holds the HSM-backed platform<br/>Grafana Server Admin credential.<br/>D11, D22, D50")]
  end

  TDIR[("<b>Tenant Directory</b><br/><i>[Container — global, replicated, metadata only]</i><br/>graft_tenant_id → home_region.<br/><b>No run data, ever.</b> D49")]

  %% ================= OBSERVABILITY =================
  subgraph OBS["Observability pipeline (D8)"]
    direction LR
    COLL["<b>OTel Collector</b><br/><i>[Container]</i><br/>PII / secret / <b>PAN</b> scrubbing,<br/>sampling, graft.tenant.id tagging.<br/>Audit records are <b>never sampled</b>.<br/>D8, D15, D25"]
    OPSINK["<b>Operational sink</b><br/><i>[External]</i><br/>Tempo / Mimir / Loki"]
    EVAL["<b>Eval sink</b><br/><i>[External — internal use only]</i><br/>Langfuse or Phoenix.<br/>Trajectories, prompt-version<br/>comparison, eval datasets.<br/><b>No product feature may read it.</b> D8a"]
    COLL --> OPSINK
    COLL --> EVAL
  end

  %% ================= EXTERNAL =================
  subgraph EXT["External systems"]
    direction LR
    GRAF["<b>Grafana</b><br/><i>[External — platform-operated]</i><br/>OSS latest, shared multi-org.<br/>Surface · identity asserter ·<br/>authorization oracle · datasource proxy.<br/>D21"]
    SLACKX["<b>Slack</b><br/><i>[External]</i><br/>Events API + OIDC"]
    IDPX["<b>IdP</b><br/><i>[External]</i><br/>Entra / Keycloak / Okta / Auth0"]
    LLMX["<b>LLM Providers</b><br/><i>[External]</i><br/>Commercial + self-hosted"]
    CUST["<b>Customer systems</b><br/><i>[External]</i><br/>Prometheus/Mimir · Loki · Tempo ·<br/>Kubernetes · GitHub · Jira/ServiceNow ·<br/>PagerDuty/iLert"]
  end

  %% ================= EDGES =================
  HUMAN --> PFE
  HUMAN --> SLACKX
  PLATOP --> API
  PLATOP --> OPSINK

  GRAF -->|"hosts, signs<br/>X-Grafana-Id"| PFE
  SLACKX <-->|"Socket Mode"| SLACKAD
  GRAF -->|"alert webhook"| HOOK

  PBE -->|"REST, forwards<br/>X-Grafana-Id"| API
  SLACKAD --> API
  HOOK --> API
  WEBFE -.-> API

  API -->|"forwards raw credential<br/><b>over mTLS</b>, AS port"| TOKEN
  TOKEN -->|"verify signing keys"| GRAF
  TOKEN -->|"verify OIDC"| IDPX
  TOKEN -->|"verify Sign in<br/>with Slack"| SLACKX

  API -->|"enqueue_run · signal ·<br/>cancel · control ops"| ORCH
  API -->|"resolve home_region"| TDIR
  API -->|"events, replay, artifacts,<br/>run_control"| PG
  API --> OBJ

  ORCH -->|"MCP, bearing the run capability<br/>token — <b>MCP port</b>"| GW
  ORCH -->|"inference"| LLMX
  ORCH -->|"steps, events,<br/>run state"| PG
  REAPER --> PG
  REAPER -->|"reconcile SAs,<br/>rotate tokens"| GRAF

  GW -->|"JWKS over the published<br/>endpoint, <b>even on loopback</b>"| TOKEN
  GW -->|"check-then-act:<br/>may this Principal?"| GRAF
  GW -->|"resolve Tenant<br/>credential per call"| VAULT
  GW -->|"Authorization: Bearer glsa_…<br/><i>hop A: network-isolated / mTLS</i>"| GMCP
  GW --> KMCP
  GW --> GHMCP
  GW --> ITMCP
  GW --> PDMCP
  GW -.->|"Phase 2"| SBX
  GW -->|"audit records"| PG
  GW -->|"large results"| OBJ

  GMCP -->|"hop B: same SA token,<br/>forwarded verbatim"| GRAF
  KMCP --> CUST
  GHMCP --> CUST
  ITMCP --> CUST
  PDMCP --> CUST
  GRAF -->|"datasource proxy"| CUST

  PG -->|"LISTEN/NOTIFY<br/>graft_run_id:graft_event_id"| API
  API -->|"publish to<br/>Live channel"| PBE
  API -->|"batched digest"| SLACKAD

  ORCH -.->|"OTLP"| COLL
  GW -.->|"OTLP"| COLL
  API -.->|"OTLP"| COLL

  %% ================= STYLE =================
  classDef person fill:#08427b,stroke:#052e56,color:#ffffff
  classDef container fill:#1168bd,stroke:#0b4884,color:#ffffff
  classDef security fill:#a6304a,stroke:#752034,color:#ffffff
  classDef store fill:#2d7d5a,stroke:#1d5139,color:#ffffff
  classDef external fill:#999999,stroke:#6b6b6b,color:#ffffff
  classDef operated fill:#6a8fb5,stroke:#3d5a75,color:#ffffff
  classDef deferred fill:#cccccc,stroke:#8a8a8a,color:#333333,stroke-dasharray: 6 4
  classDef groupbox fill:#f7f7f7,stroke:#d0d0d0,color:#333333
  classDef authbox fill:#f7e9ec,stroke:#a6304a,color:#333333

  class HUMAN,PLATOP person
  class PFE,PBE,SLACKAD,HOOK,API,ORCH,AGENT,RUNTIME,REAPER,GMCP,KMCP,GHMCP,ITMCP,PDMCP,COLL container
  class GW,TOKEN,REG security
  class PG,OBJ,VAULT,TDIR store
  class GRAF operated
  class SLACKX,IDPX,LLMX,CUST,OPSINK,EVAL external
  class WEBFE,SBX deferred
  class PEOPLE,EDGE,CORE,MCPS,DATA,OBS,EXT,PLUGIN groupbox
  class AUTH authbox
```

**Colour key:** **crimson** marks the three modules that carry *authority*. They
now ship as one deployable but remain three modules with three sets of rules. If
you are reviewing this diagram for security, those three plus Postgres RLS are
the whole story. **Green** marks state.

---

## 3. The Authority Service — why merging is safe (D69)

r1 drew the Token Service, Tool Gateway and Tool Registry as three deployables.
They are now **one deployable with three modules**. This is an operability
decision, and it is only defensible because of what it does *not* change.

**The boundary that matters is untouched.** D7 requires separation from the
**agent/worker process** — because in-process policy enforcement is not a
boundary when the primary threat is a model acting on injected text it just read.
It does **not** require separation of the Authorization Server from the Resource
Server; D19 explicitly anticipated co-location and demanded only that the RS
validate independently.

Five invariants, each a build-time or config-time fact rather than a convention:

| # | Invariant | How it is enforced |
|---|---|---|
| 1 | **The signing key is reachable only by the Token Service module.** | The gateway module holds the public JWKS and nothing else, so it *cannot* shortcut validation even if someone wants it to. |
| 2 | **The gateway validates independently** — signature, `aud`, `exp` — over the published JWKS endpoint, **including on loopback**. | No shared in-memory token state between modules. |
| 3 | **Separate listeners, separate network policy.** | AS discovery/JWKS/mint on one port, MCP on another, with distinct ingress rules. Preserves D18's hop-A isolation and makes a future split a DNS change, not a refactor. |
| 4 | **No shared mutable request context.** | Module interface is a call, not a context object. |
| 5 | **Independent rate limits.** | Token minting and tool brokering throttle separately. |

**The AS verifies raw surface credentials itself.** The Harness API forwards
`X-Grafana-Id`, the Slack assertion or the webhook secret **verbatim over mTLS**
rather than asserting a verified identity on the caller's behalf. This is the
same confused-deputy property D23 exists to protect — it would have been easy to
let the API do the verifying and pass a claim, and it would have quietly
reintroduced exactly the trust relationship we removed from the plugin backend.

**Named decomposition triggers**, so a future split is a decision rather than a
drift:

1. **Exposing the Tool Gateway to external MCP clients.** That would require
   Dynamic Client Registration and change the AS threat model — already flagged
   in `mcp-authorization-server.md` §7.
2. **Materially divergent scaling profiles** between token minting (cheap, bursty,
   per-run) and tool brokering (expensive, sustained, per-call).

---

## 4. Container register

| Container | Tech | Responsibility | Must **not** | Decisions |
|---|---|---|---|---|
| **Plugin Frontend** | TypeScript, React, `@grafana/ui` | Panels, full-page routes, config pages, diff view, Live subscription, driver badge and keep-control prompt | Call the Harness API directly; hold capability | D1, D31, D34, D66 |
| **Plugin Backend** | Go, Grafana plugin SDK | Proxy to API; Grafana Live `StreamHandler`; channel authz; forward `X-Grafana-Id`; **emit connect/teardown as the disconnect-clock signal** | Assert authorization on the gateway's behalf (D23); stream SSE through the Go proxy (D31) | D1, D23, D31, D66 |
| **Slack Adapter** | Python, Socket Mode | Tenant resolution by channel binding; link prompts; batched output; approval deep links | Perform approval; stream token-level; report transport liveness it does not have | D14, D20, D34, D61, D66 |
| **Webhook Ingress** | Python | Normalise + deduplicate alert events; derive Tenant from source GrafanaOrg | Produce a `user_initiated` Run | D2, D13, D42, D51 |
| **Harness API** | Python, FastAPI | The single API. Forward surface credentials verbatim. REST back-channel incl. control ops. Run list. Artifact fetch. Cross-region read proxy | Execute tools; mint or verify tokens; **assert a verified identity on a caller's behalf**; persist outside home region | D1, D33, D49, D64, D69 |
| **Authority Service · Token Service module** | Python; OIDC, RFC 8707, RFC 9728 | Verify raw surface credentials; resolve Principal→Role→Tenant; mint run capability tokens; publish JWKS | Validate its own tokens; grant a class L3 has not enabled; share the signing key | D9, D10, D19, D56, D69 |
| **Authority Service · Tool Gateway module** | MCP both directions | L5 enforcement; check-then-act; credential resolution; throttles; result reduction; audit emission; HITL gate; ToolExecutor seam | Mint tokens; hold the signing key; trust the plugin backend's assertion; forward upstream descriptions to the model | D7, D18, D23, D44, D63, D68, D69 |
| **Authority Service · Tool Registry module** | Postgres-backed | Hash-pinned definitions, ToolClass, required Role, curated descriptions | Auto-enable discovered tools | D63 |
| **Orchestrator Workers** | Python StatefulSet; DBOS Transact (MIT, embedded) | Durable Run workflows; partitioned queues; durable timers; signals; blue/green versioning | Call MCP servers or customer systems directly; hold ambient Tenant context | D37–D48, D50, D68 |
| **Agent Graph** | LangGraph + DeepAgents, no checkpointer | Planning, sub-agents, hypothesis formation, evidence assembly | Be the durability boundary; hold a second checkpointer | D3, D39, D40 |
| **`runtime` seam** | Python module | Sole importer of `dbos`; chokepoint for audit, events, scoping, ceilings | Become a config-swappable engine port | D48 |
| **Scheduled Workflows** | DBOS cron | Reaper, **30s control sweep**, drift reconciler, rotation, infra-memory refresh, auto-close, approval expiry | Consume Tenant Schedule ceilings (platform timers are not user Schedules) | D38, D47, D53, D58, D66 |
| **grafana-mcp** | Go, shared, stateless | Grafana tool surface; forwards `Authorization` verbatim | Use its own caller-auth on hop A; cache across Tenants | D18 |
| **k8s-mcp** | TBD — **design pending** | The **only** path to customer Kubernetes; impersonation carries `graft_run_id` | Exist as a library inside the worker | D68, §9 |
| **pagerduty / ilert-mcp** | TBD | Schedules, rotation, incident detail — `read` only in v1 | Ever expose suppression or maintenance windows | D67 |
| **Postgres** | PostgreSQL, RLS | Run state, `run_control`, event log, audit chain, DBOS system DB, policy versions, identity mapping | Be reachable without `SET LOCAL graft.tenant_id`; hold large artifacts | D15, D30, D50, D66 |
| **Object Storage** | Object-lock capable | Artifacts + WORM audit anchors | Hold anything mutable | D15, D34, D41 |
| **Secret Store** | Vault-class, HSM-backed for platform creds | Tenant-scoped credentials | Be read by anything except the Authority Service and provisioning workflows | D11, D22, D50 |
| **Tenant Directory** | Globally replicated, metadata only | `graft_tenant_id → home_region` | Contain Run data of any kind | D49 |
| **OTel Collector** | OpenTelemetry | Scrub PII/secret/PAN, sample, tag, fan out | Sample audit records | D8, D25 |

---

## 5. The five flows that define the system

### 5.1 Run creation and the capability token

```mermaid
sequenceDiagram
    autonumber
    participant S as Surface
    participant API as Harness API
    participant TS as Token Service · AS
    participant Q as DBOS queue (Postgres)
    participant W as Worker

    S->>API: Start Run (X-Grafana-Id / linked Slack principal / webhook secret)
    API->>TS: Forward credential VERBATIM over mTLS
    Note over API,TS: The API never asserts identity on a caller's behalf (D69)
    TS->>TS: Verify credential, then resolve Principal → Role → Tenant<br/>Group map → per-Principal grant → live Grafana basic role
    Note over TS: Unverified identity → link prompt, not a Run (D61)
    TS->>TS: Decide initiation_mode
    Note over TS: system_initiated ⇒ allowed_tool_classes excludes write/destructive (D13)<br/>forked/eval runs likewise (D42)
    TS-->>API: Run capability token (~10 min, aud=tool-gateway, L4)
    API->>Q: enqueue_run(workflow_id=graft_run_id, deduplication_id)
    Note over Q: Partition key = graft_tenant_id (D44)<br/>Never started in-process (D38)
    Q-->>W: Dispatch, pinned to app_version
    W->>W: Parent workflow = the Run
```

**Why `dbos_workflow_id = graft_run_id`:** D42 makes the workflow id
caller-supplied, so the value is ours anyway. Setting them equal stops drift and
makes the idempotency key self-evident (D60).

### 5.2 A tool call — the five-layer lattice in motion

```mermaid
sequenceDiagram
    autonumber
    participant W as Worker · agent step
    participant GW as Tool Gateway
    participant TS as Token Service
    participant REG as Tool Registry
    participant V as Secret Store
    participant M as grafana-mcp
    participant G as Grafana
    participant PG as Audit chain

    W->>GW: MCP tools/call + capability token
    GW->>TS: Fetch JWKS over the published endpoint (cached)
    Note over GW,TS: Same deployable, still the published endpoint.<br/>The gateway module never holds the signing key (D69)
    GW->>GW: Validate signature, aud, exp — independently
    GW->>REG: L1 in catalogue? definition hash unchanged?
    GW->>GW: L2 platform policy — hard deny / kill switch
    GW->>GW: L3 Tenant policy version pinned to this Run
    GW->>GW: L4 class present in capability token?
    GW->>G: L5 check-then-act — may this Principal, now?
    Note over GW,G: Basic-role granularity only —<br/>custom roles are Enterprise-only (D26)
    GW->>GW: L5 per-connection throttle (protects customer infra)
    GW->>V: Resolve Tenant SA token
    GW->>M: MCP call, Authorization: Bearer glsa_… (hop A, network-isolated)
    M->>G: Same token forwarded verbatim (hop B)
    G-->>M: Result
    M-->>GW: Result
    GW->>GW: Reduce result — offload full artifact to object storage
    GW->>PG: Audit record (actor from verified credential, caused_by edge)
    GW-->>W: Reduced result + artifact pointer
```

**The two-hop credential split is the whole multi-tenancy story.** Hop A cannot
use `grafana-mcp`'s built-in caller-auth because that mechanism also wants the
`Authorization` header and cannot coexist with per-call SA-token forwarding on
it. So hop A is protected by network isolation, and `Authorization` is reserved
for hop B (D18). Isolation between Tenants comes from *the token Grafana receives
per call* — not from running a process per Tenant.

**Every customer system is reached this way** (D68). The diagram shows Grafana
because it has the most interesting credential story; Kubernetes, GitHub,
ticketing and paging follow the identical path through their own MCP servers.

### 5.3 Streaming — decoupled from orchestration by construction

```mermaid
sequenceDiagram
    autonumber
    participant W as Worker
    participant PG as Postgres event log
    participant API as Harness API
    participant PBE as Plugin Backend
    participant B as Browser
    participant SL as Slack Adapter

    W->>PG: INSERT event (graft_run_id, graft_event_id, type, version, payload)
    PG-->>API: NOTIFY "graft_run_id:graft_event_id"
    API->>PG: SELECT the row (avoids the 8KB NOTIFY ceiling)
    API->>PBE: Publish to Live channel plugin/<id>/run/<graft_run_id>
    PBE-->>B: Token-level stream
    API->>SL: Batched / throttled digest
    Note over B: Late joiner sees the live tail by default —<br/>full replay is an explicit action,<br/>an indexed range query on graft_event_id (D30, D32)
```

Three properties fall out of this shape, and all three were design goals:

- **One writer.** Run state and events commit in the same transaction, so there
  is no dual-write risk and no hot/cold fallback to design (D30 — chosen over a
  Redis-Streams split).
- **The orchestrator choice is not visible here.** We deliberately do not use
  DBOS's `set_event`/streaming. Swapping the engine would not touch this flow
  (D45).
- **Narration lives entirely on this path.** Posting to Slack and annotating
  Grafana never touch the Tool Gateway and carry no ToolClass, which is precisely
  why a structurally read-only 03:00 Run can still tell you what it found (D67).

### 5.4 The durable approval wait

```mermaid
sequenceDiagram
    autonumber
    participant W as Worker
    participant PG as Postgres
    participant SL as Slack
    participant B as Grafana Plugin
    participant API as Harness API
    participant GW as Tool Gateway

    W->>PG: Emit action_proposed (diff, blast radius, confidence, proposal_hash)
    W->>W: DBOS.recv("approval", timeout ≥72h)
    Note over W: The process may die here. The wait is a row.
    PG-->>SL: Notification + signed single-use deep link
    SL-->>B: Human lands in Grafana
    B->>API: Claim control (if not already driver)
    API->>PG: run_control: driver = P, driver_since = now
    Note over API,PG: On a system_initiated Run, this claim is the<br/>upgrade to user_initiated — a human has attached (D66)
    B->>API: POST approve — re-authenticated, idempotency-keyed
    API->>API: may_approve = <b>driver</b> AND re-authed AND check-then-act<br/>AND origin=user_initiated AND role holds action:approve (D65)
    API->>PG: Bind approval to proposal_hash, not intent
    Note over API,PG: TOCTOU-resistant: approving a *hash*<br/>means the executed change is the reviewed change —<br/>which is what makes inheriting a proposal safe
    API->>W: DBOS.send(graft_run_id, "approval")
    W->>W: Write class now in token (D13)
    W->>GW: Execute as a Pattern-A child workflow<br/>(graft_run_id, step_id, idempotency_key)
    Note over W: On timeout: Run closes as expired (D47).<br/>Bounds the blue/green colour-retention window.
```

### 5.5 Control liveness — the flow that only exists because control is authority

```mermaid
sequenceDiagram
    autonumber
    participant B as Driver's surface
    participant API as Harness API
    participant PG as Postgres · run_control
    participant SW as Control sweep · 30s
    participant V as Other viewers

    B->>API: Interactive act (prompt / steer / approve / keep-control)
    API->>PG: UPDATE last_interaction_at = now()
    Note over API,PG: A cheap UPDATE, not a durable-timer reset.<br/>Resetting a timer per keystroke is write amplification<br/>against the binding scale constraint (D48)

    B--xAPI: Grafana Live teardown
    API->>PG: transport_state = disconnected, disconnected_at = now()

    loop every 30s
        SW->>PG: Scan runs WHERE driver IS NOT NULL
        alt idle ≥ 9 min
            SW->>B: Warn — "keep control?" (T−60s)
        else idle ≥ 10 min OR disconnected ≥ 2 min
            SW->>PG: driver = NULL (unowned)
            SW->>PG: Audit record — control released, reason, clock
            SW->>V: Notify — wheel is free
        end
    end

    V->>API: Claim control
    Note over V,API: Released to NOBODY, never auto-handed.<br/>Auto-handing control = auto-handing approval rights (D66)
    API->>PG: driver = V, audited as an authority transfer
```

**Slack drivers have no disconnect clock** — Socket Mode gives us no per-Principal
liveness signal — so they run on the idle clock alone. A documented asymmetry,
and a mild one, since a Slack driver must land in Grafana to approve anyway.

**Force-release** is a separate, `tenant_admin`-only path into the same state
transition, emitting a non-sampled audit record naming forcer, displaced driver
and any pending `proposal_hash`. We chose **detection over friction**: no
cool-down, because during an incident a deliberate delay is itself a harm — but a
force-release followed by the forcer approving in the same Run is flagged as a
self-escalation pattern and tracked as a platform metric.

---

## 6. Deployment topology

```mermaid
flowchart TB
    subgraph GLOBAL["Global"]
        TD[("<b>Tenant Directory</b><br/>graft_tenant_id → home_region<br/><b>metadata only</b>")]
        GRAFG["<b>Grafana</b><br/>platform-operated, OSS latest,<br/>shared multi-org"]
        SLACKG["<b>Slack</b><br/>single install, all Tenants"]
    end

    subgraph R1["Region: GCP"]
        direction LR
        S1["Full harness stack<br/>API · <b>Authority Service</b> · Workers · MCP fleet"]
        DB1[("Postgres · Object storage<br/>Secret store · WORM anchors")]
        S1 --- DB1
    end

    subgraph R2["Region: AliCloud"]
        direction LR
        S2["Full harness stack<br/>API · <b>Authority Service</b> · Workers · MCP fleet"]
        DB2[("Postgres · Object storage<br/>Secret store · WORM anchors")]
        S2 --- DB2
    end

    TD -.->|"resolve home_region"| S1
    TD -.->|"resolve home_region"| S2
    S1 -.->|"<b>read-path proxy only</b><br/>under caller's identity,<br/>never persisted locally"| S2
    GRAFG --- S1
    GRAFG --- S2
    SLACKG --- S1
    SLACKG --- S2

    classDef store fill:#2d7d5a,stroke:#1d5139,color:#ffffff
    classDef container fill:#1168bd,stroke:#0b4884,color:#ffffff
    classDef operated fill:#6a8fb5,stroke:#3d5a75,color:#ffffff
    classDef groupbox fill:#f7f7f7,stroke:#d0d0d0,color:#333333
    class TD,DB1,DB2 store
    class S1,S2 container
    class GRAFG,SLACKG operated
    class GLOBAL,R1,R2 groupbox
```

**Two deployments, not one logical system** (D49). Each region has its own
workers and its own DBOS system database; **there is no cross-region workflow
recovery**, which is what makes multi-region tractable rather than a distributed
consensus problem. Run data, events, artifacts and audit records never leave
their home region; audit chains are wholly in-region and anchor to in-region WORM
storage.

> **The trap this design makes structurally impossible:** `grafana_org_id` is a
> region-local integer, so org `5` exists in *both* deployments meaning different
> Tenants. `graft_external_ref`'s primary key includes `ref_scope` for exactly
> this reason (D60). `graft_tenant_id` is globally unique and externally sourced
> — we adopt the key, we do not mint it — which is what makes a customer spanning
> both regions coherent.

**D69 helps here in a way worth naming:** the Authority Service is a *per-region*
deployable, and merging three into one cuts the per-region operational surface by
two services across two clouds — which is most of the reason the merge is worth
doing at all.

### 6.1 Deploy and recovery

| Mechanism | Behaviour | Decision |
|---|---|---|
| **Versioning** | DBOS app version = **auto-hash of workflow source**, deliberately *not* a git SHA or image tag — a prompt-only change must not force a full drain | D46 |
| **In-flight Runs** | Finish on their original version. New work enqueues pinned to the latest | D46 |
| **Colour retirement** | Gated in the pipeline on `list_workflows(app_version, status=[ENQUEUED,PENDING])` returning empty — **a machine check, not a human eyeball** | D46 |
| **Recovery** | Workers are a StatefulSet; executor IDs carry ordinal **and** colour (`blue-0`, `green-0`). A version-aware reaper resumes stale executors' work onto a live matching-version worker | D38 |
| **Capacity** | Two colours run concurrently during structural deploys — **plan for double peak workers and Postgres connections** | D48 risk X7 |
| **Binding constraint** | **Postgres connection count (pooler), not engine throughput.** Our workload sits 2–3 orders of magnitude below DBOS's >40K steps/sec single-Postgres benchmark | D48 |

---

## 7. Where authority lives — the one-page security read

```mermaid
flowchart LR
    subgraph UNTRUSTED["Untrusted by construction"]
        direction TB
        LOGS["Application logs, tool output,<br/>upstream tool descriptions,<br/>custom instructions"]
        MODEL["LLM output"]
    end

    subgraph TRUSTBOUNDARY["Trust boundary — the agent cannot cross this in-process"]
        direction TB
        GW2["<b>Authority Service</b><br/>separate process from the worker ·<br/>independent token validation ·<br/>signing key isolated to the AS module"]
    end

    subgraph AUTHORITY["Authority, in order"]
        direction TB
        A1["L1/L2 Platform — kill switch"]
        A2["L3 Tenant policy — versioned, step-up"]
        A3["L4 Capability token — minted before any instruction is read"]
        A4["L5 Call-time — Grafana permission, Role, throttle"]
        A5["<b>Human gate — the current driver,<br/>re-authenticated, bound to proposal_hash</b>"]
    end

    LOGS --> MODEL --> GW2
    GW2 --> A1 --> A2 --> A3 --> A4 --> A5
    A5 --> EFFECT["Effect on a customer system<br/><i>reached only via MCP</i>"]

    classDef bad fill:#a6304a,stroke:#752034,color:#ffffff
    classDef gate fill:#08427b,stroke:#052e56,color:#ffffff
    classDef ok fill:#2d7d5a,stroke:#1d5139,color:#ffffff
    class LOGS,MODEL bad
    class GW2,A1,A2,A3,A4,A5 gate
    class EFFECT ok
```

Six invariants, each a container boundary or a data binding rather than a check:

1. **The capability token is minted before any untrusted text is read.** An
   instruction saying *"you may restart pods without asking"* has literally no
   effect (D62). The mitigation is structural, not a filter.
2. **`system_initiated` cannot write** because the token never names a write
   class — not because a check said no (D13). Forked/eval Runs inherit this,
   since `fork_workflow` deliberately re-executes and would otherwise re-file a
   Jira ticket (D42).
3. **Upstream tool descriptions never reach the model.** A third party's
   description in model context is a direct prompt-injection channel (D63).
4. **No ambient Tenant context, ever.** Scope travels as an explicit argument
   through the `runtime` seam; thread-locals plus async task switching is the
   classic cross-tenant leak (D50).
5. **No direct clients on customer systems.** A direct client bypasses the
   lattice, credential resolution, throttles, reduction and audit in one move
   (D68).
6. **Approval binds to `proposal_hash`, not to intent.** This is what makes
   driver-based approval safe: whoever holds the wheel approves *exactly* the
   artefact that was reviewed, so inheriting a pending proposal cannot inherit a
   different one (D65).

---

## 8. Compliance surface (PCI-DSS, D25)

| Requirement | Container that satisfies it | Mechanism |
|---|---|---|
| Tamper evidence (10.5.2) | Postgres audit chain + Object Storage | Insert-only hash-chained causal DAG, periodically anchored to object-lock WORM |
| Retention | Postgres + Object Storage | 12 months minimum, 3 months hot |
| Step-up auth (8.4.2) | Harness API + Grafana | Re-authentication to enable a write/destructive ToolClass, and again at approval |
| Least privilege | Scheduled Workflows + Grafana | SA role recomputed to the minimum across enabled Tools on every policy change; drift reconciler asserts it |
| Cardholder data | OTel Collector | PAN detection and scrubbing **before** data reaches either the audit chain or the eval sink |
| Attribution | Authority Service | Actor derives from a **verified credential**, never from agent or tool output — and **control transfers are audit records**, so the chain shows how an approver came to hold authority (D65) |

> **Open tension (D8b).** The eval sink must pass through the *same* scrubbing
> pipeline as the audit chain, or it becomes an unscrubbed liability sitting next
> to a compliant one. This still rubs against D8a's "never a runtime dependency"
> framing for forensics. Deferred to the Evals & Benchmarks session alongside the
> PAN detector — same piece of work.

---

## 9. Deliberately **not** containers

This list is where most of the design work actually went.

| Not a container | Why | Decision |
|---|---|---|
| **A separate Token Service deployment** | Logically distinct, physically merged. D19 only ever required independent validation, which is preserved by module boundary plus key isolation. Split triggers are named, so it is a decision and not a drift | D69 |
| **A separate Tool Registry service** | It is a Postgres-backed lookup on the gateway's hot path. A network hop per tool call to read our own table buys nothing | D69 |
| **A separate LangGraph service** | LangGraph is demoted from "the orchestrator" to "graph structure invoked beneath the durability boundary". A separate service would reintroduce the checkpointing it was demoted to remove | D39, D40 |
| **DBOS Conductor / Temporal** | Explicit product constraint: no paid plans, no separate orchestration service. Work rediscovery is ~150 lines we own, not a durable engine we build | D37, D38 |
| **Redis** | Postgres alone gives transactional consistency with Run state — one writer, no dual-write risk — and needs no trimming, retention or hot/cold fallback design at our scale | D30 |
| **A K8s client inside the worker** | Convenient and forbidden. It would bypass the lattice, credential resolution, throttles, reduction and audit simultaneously, and be invisible in the audit chain | D68 |
| **Per-Tenant `grafana-mcp` process** | Isolation comes from the SA token Grafana receives per call. Process-per-Tenant is cost without a security gain | D18 |
| **A `RunController` driver port** | DBOS's value comes from decorators on *our* functions, and determinism constraints cannot be hidden behind an interface. Replaced by the thin `runtime` seam, which earns its keep as an audit/event/scoping chokepoint | D48 |
| **A per-surface API** | One API, thin surfaces. The REST back-channel is byte-identical across Grafana, Slack and the post-v1 web frontend | D1, D33 |
| **A "chat service" beside a "run service"** | Considered and rejected. Even routine chat needs resumable persistence, end-to-end audit and approved tool calls | D36 |
| **Thread-level isolation** | Parallel execution for hundreds of Principals is a **scheduling** problem, not an isolation one. Python threads share a heap and prompt injection does not respect task boundaries | D50 |
| **A durable timer per Run for control liveness** | A 30s sweep over a cheap `UPDATE` column beats resetting a durable timer on every keystroke, against the exact Postgres named as the binding scale constraint | D66, D48 |
| **AG-UI as the event protocol** | Our event model is ours, versioned, additive-only. AG-UI is at most a future output adapter for the web frontend — never Grafana, never Slack | D29 |

---

## 10. Still open at this level

| # | Question | Blocking? | Owner |
|---|---|---|---|
| 1 | **DBOS + async LangGraph + `langchain-mcp-adapters` ergonomics unverified.** Pattern B is DBOS's own pattern but their references are framework-free Python loops, not LangGraph | **Yes — needs an early prototype before L3** | Orchestrator |
| 2 | **DBOS system-database migrations vs `FORCE ROW LEVEL SECURITY`.** DBOS tables are not RLS-aware, and step inputs/outputs checkpointed there may pull the system DB into PCI-DSS scope | **Yes** | Data / compliance |
| 3 | **`k8s-mcp` design.** D68 settled the *shape* — MCP only, never a direct client — but not the plumbing: which server, how impersonation headers are threaded, how cluster Connections map to credentials, how per-connection QPS throttles bind | **Yes for J1** | Tool track |
| 4 | **Control-clock defaults are guesses.** 10 min idle, 2 min disconnect, 30s sweep. These are now security parameters, and nothing has measured them | **No — but instrument from day one** | Surface / product |
| 5 | **Grafana `authlib` `EnforcementClient` maturity** — supported public API or internal package? And **enforcement-check latency/caching** at alert-storm concurrency | No — fallback is direct API calls | Authority Service |
| 6 | **Grafana Live per-message size/throughput limits are undocumented.** D34 pushes token-level streaming through it. `max_connections` defaults to 100 per instance and one WebSocket is consumed per browser tab | No — needs a spike | Surface |
| 7 | **Reaper behaviour on routine scale-down**, not just crashes: scaling 8→4 orphans ordinals 4–7. Needs an explicit test, not an argument | No — test gap | Orchestrator |
| 8 | **Langfuse vs Phoenix** for the eval sink; sampling policy (100% for RCA proposed; audit records never sampled) | No | Observability |
| 9 | **OSS MCP gateway spike** — IBM ContextForge, Docker MCP Gateway, Lasso mcp-gateway, Obot as adopt candidates. **Verify maturity, do not assume.** Expect none to cover Tenant-scoped credential binding + K8s impersonation + our HITL model | No | Authority Service |
| 10 | **Tenant Directory replication substrate and staleness budget** — metadata-only, but a stale `home_region` misroutes a read proxy | No | Platform |

---

## 11. Next

1. **L3 — Authority Service.** It now carries three modules and the most
   authority in the system. Components: credential verifier, token minter, JWKS
   publisher, token validator, lattice evaluator, check-then-act client,
   credential resolver, throttle, result reducer, audit emitter, ToolExecutor
   seam, registry.
2. **L3 — Orchestrator.** Components: `runtime` seam, workflow/step decomposition,
   queue partitioning, reaper, control sweep, signal handling, the LangGraph
   invocation boundary.
3. **`k8s-mcp` design pass** (§10 item 3) — the last customer system without a
   decided path.
4. **Prototype spike** answering §10 items 1 and 2 — these two can invalidate
   container shapes, and nothing below L2 should be drawn until they are
   answered.
