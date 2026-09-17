---
id: ADR-0070
title: All MCP servers are streamable-HTTP, never stdio
status: accepted
date: 2026-09-12
deciders: []
category: tools
tags: [tools, mcp, authority]
supersedes: []
superseded_by: []
amends: [ADR-0007]
amended_by: []
relates_to: []
design: ../../design/tool-registry-and-authority.md
legacy_id: null
---

# ADR-0070 — All MCP servers are streamable-HTTP, never stdio

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D70`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/tool-registry-and-authority.md`](../../design/tool-registry-and-authority.md).

---

## 1. Context

MCP servers can be exposed either over `stdio` (spawned as a local
subprocess of the caller) or over streamable-HTTP (a network service). The
Tool Gateway (ADR-0007) needs a transport for both its server role (facing
the agent) and its client role (facing upstream MCP servers), and `stdio`
carries known security implications for a service architecture — it is
named in the MCP Security Best Practices document as the "stdio-in-proxy"
risk.

## 2. Decision

**All MCP servers are streamable-HTTP, never stdio.**

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| `stdio`-based MCP servers, spawned as local subprocesses | ❌ Rejected | Carries the "stdio-in-proxy" risk named in the MCP Security Best Practices document; does not fit a horizontally-scaled, network-isolated service architecture (ADR-0007, ADR-0018). |
| Streamable-HTTP MCP servers exclusively | ✅ Chosen | Fits the Tool Gateway's network-service architecture and avoids the stdio-in-proxy risk class entirely. |

## 4. Consequences

- **Positive —** avoids the stdio-in-proxy risk class named in the MCP
  Security Best Practices document; MCP servers can be deployed,
  scaled and network-isolated like any other service.
- **Negative / accepted trade —** any upstream MCP server or library that
  only supports `stdio` cannot be used without an HTTP-facing wrapper.
- **Follow-on work —** amends ADR-0007, which now specifies the transport
  for the gateway's dual MCP server/client role.
- **Revisit trigger —** none observed.

## 5. Verification

- Confirmed by **spike S1** (2026-09-13, experiments E2/E6, per ADR-0041's Verification): step granularity was confirmed for a real streamable-HTTP MCP tool call, exercising this transport choice end to end.
