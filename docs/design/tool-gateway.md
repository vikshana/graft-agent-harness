# Tool Gateway

> **Status: 🟢 Resolved for v1.** Mechanism for **ADR-0007**; invariants from
> **ADR-0068**, **ADR-0070**, **ADR-0018**, **ADR-0023**, **ADR-0069**.
>
> Vocabulary per [`../GLOSSARY.md`](../GLOSSARY.md). Related:
> [`tool-registry-and-authority.md`](./tool-registry-and-authority.md),
> [`grafana-mcp-multi-tenancy.md`](./grafana-mcp-multi-tenancy.md),
> [`mcp-authorization-server.md`](./mcp-authorization-server.md).
>
> *Migrated from `DECISION-REGISTER.md` §2 during the 2026-09-13 ADR migration.*

---

## 1. Shape

```
LangGraph / DeepAgents ──MCP──▶ Tool Gateway ──MCP──▶ k8s-mcp, grafana-mcp,
  (MultiServerMCPClient,        (MCP server to agent,      github-mcp, jira-mcp,
   one endpoint)                 MCP client to upstreams)  pagerduty-mcp, …
                                        │
                       identity binding · authz / tool allow-listing
                       Tenant credential resolution (vault)
                       read-through cache · rate limiting
                       result reduction · audit emission
                       destructive-action HITL gate
                       Phase 2: sandboxed execution
```

The agent points `langchain-mcp-adapters` at **exactly one endpoint**
(ADR-0007). Upstreams are always streamable-HTTP, never stdio (ADR-0070).

## 2. Division of labour with LangChain

| Concern | Owner |
|---|---|
| Tool discovery, schema binding, tool selection | LangChain (`langchain-mcp-adapters`) |
| Retry / telemetry wrapping in-process | LangChain middleware |
| Identity binding, authz, credentials, cache, rate limit, audit, HITL gate, result reduction | **Tool Gateway** |

Two further benefits: non-LangGraph consumers (Slack quick-actions, single-tool
calls) can use the gateway directly, and the agent framework stays swappable.

## 3. What happens on every call

1. **Validate the run capability token** as a Resource Server (ADR-0010,
   ADR-0019, ADR-0027). The gateway never mints — that is the AS module's job,
   and it validates independently even when co-deployed (ADR-0069).
2. **Evaluate L5 of the authority lattice** — may *this* Principal, *now*
   (ADR-0063). L1–L4 have already narrowed what is reachable.
3. **Check-then-act** for Grafana-scoped resources, performed by the gateway
   itself and never delegated to the plugin backend's assertion (ADR-0023), at
   basic-role granularity (ADR-0026).
4. **Resolve the Tenant credential** and attach it per call. For `grafana-mcp`
   this is hop B's `Authorization: Bearer glsa_...`, forwarded verbatim via
   `GRAFANA_FORWARD_HEADERS` (ADR-0018). Hop A is protected by network isolation,
   not by `grafana-mcp`'s own caller-auth, because both want the same header.
5. **Throttle per connection**, protecting *customer* infrastructure,
   independent of Tenant quota (ADR-0044, ADR-0057).
6. **Reduce the result** — raw tool output is never returned verbatim; artifacts
   go to object storage and are referenced by pointer (ADR-0034, ADR-0041).
7. **Emit the audit record** (ADR-0015), with the actor derived from the
   verified credential, never from tool output.

## 4. The invariant

**No component reaches a customer system except through this gateway**
(ADR-0068). Three named exceptions, all non-agent-driven: platform-internal
service-account provisioning and drift reconciliation (ADR-0022, ADR-0053); the
gateway's own call to Grafana's access-control API for check-then-act
(ADR-0023); and surface adapters posting narration to Slack and Grafana
(ADR-0067). Anything else opening a direct client is a review defect.

## 5. Open work

- **Spike existing OSS MCP gateways** — IBM ContextForge, Docker MCP Gateway,
  Lasso mcp-gateway, Obot — as reference or adopt candidates. **Verify maturity,
  do not assume.** Expect none to cover Tenant-scoped credential binding, K8s
  impersonation and our HITL model together.
- **Blocking spike (L3):** DBOS × async LangGraph × `langchain-mcp-adapters`
  ergonomics — see [`../diagrams/c4-l2-containers.md`](../diagrams/c4-l2-containers.md) §9.
