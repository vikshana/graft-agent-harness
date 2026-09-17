---
id: ADR-0007
title: The Tool Gateway is a separate service
status: accepted
date: 2026-09-12
deciders: []
category: tools
tags: [tools, mcp, authority]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: [ADR-0070, ADR-0068, ADR-0069]
design: ../../design/tool-registry-and-authority.md
legacy_id: D7
---

# ADR-0007 — The Tool Gateway is a separate service

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D7`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/tool-registry-and-authority.md`](../../design/tool-registry-and-authority.md).

---

## 1. Context

The agent needs to call tools against customer systems (Grafana,
Kubernetes, GitHub, ticketing, etc.). The primary threat model is indirect
prompt injection — malicious instructions arriving via application logs or
other tool output — which means policy enforcement has to hold even when
the agent process itself is compromised or manipulated. That rules out
enforcement that lives inside the same process as the agent.

## 2. Decision

**Tool Gateway** — the agent never calls MCP servers directly. A
**separate service**, not a library, because in-process policy enforcement
is not a security boundary (primary threat: indirect prompt injection from
application logs).

### 2.7b — folded from legacy `D7b`

The Tool Gateway **speaks MCP in both directions**: an MCP server to the
agent, an MCP client to upstreams. LangChain's `langchain-mcp-adapters`
points at exactly one endpoint.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| In-process policy enforcement (a library the agent calls into) | ❌ Rejected | Not a real security boundary against the primary threat (indirect prompt injection) — a compromised or manipulated agent process could bypass in-process checks. |
| A separate Tool Gateway service, acting as an MCP server to the agent and an MCP client to upstream MCP servers | ✅ Chosen | Enforcement happens outside the agent process, so it holds even if the agent's own reasoning is manipulated; speaking MCP in both directions avoids `langchain-mcp-adapters`' single-endpoint limitation. |

## 4. Consequences

- **Positive —** policy enforcement is a genuine security boundary,
  independent of what the agent process does or is tricked into doing.
- **Negative / accepted trade —** an extra network hop and a service to
  operate, rather than an in-process library call.
- **Follow-on work —** the gateway must implement both MCP server and MCP
  client roles, since `langchain-mcp-adapters` only points at one endpoint;
  amended by ADR-0070 (streamable-HTTP only) and generalised by ADR-0068
  (every customer system reached via gateway + MCP) and ADR-0069 (ships as
  part of the Authority Service).
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original
  register entry was marked "verified live" for this decision. Mechanism:
  [`../../design/tool-registry-and-authority.md`](../../design/tool-registry-and-authority.md).
