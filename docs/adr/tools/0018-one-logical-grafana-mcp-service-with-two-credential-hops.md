---
id: ADR-0018
title: One logical grafana-mcp service with two credential hops
status: accepted
date: 2026-09-12
deciders: []
category: tools
tags: [tools, mcp, authority]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: [ADR-0068]
design: ../../design/tool-registry-and-authority.md
legacy_id: D18
---

# ADR-0018 — One logical grafana-mcp service with two credential hops

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D18`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/tool-registry-and-authority.md`](../../design/tool-registry-and-authority.md).

---

## 1. Context

`grafana-mcp` needs both to isolate customer workspaces from one another
and to scale efficiently. Running one process per workspace would give
isolation by construction but at a much higher operational cost than a
shared, horizontally-scaled service — which instead needs isolation to
come from credentials rather than from process boundaries.

## 2. Decision

**One logical, horizontally-scaled `grafana-mcp` service**, never one
process per workspace as a default. There are **two distinct hops with two
distinct credentials**: Tool Gateway → `grafana-mcp` (hop A) and
`grafana-mcp` → Grafana (hop B, the Grafana SA token,
`Authorization: Bearer glsa_...`). Hop B's SA token is resolved per call by
the Tool Gateway and forwarded verbatim via
`GRAFANA_FORWARD_HEADERS=Authorization`. **Locked 2026-09-12:** hop A does
**not** use `grafana-mcp`'s built-in caller-auth
(`MCP_GRAFANA_SERVER_TOKEN`), since that mechanism also wants the
`Authorization` header and cannot coexist with per-call SA-token
forwarding on it — hop A is instead protected by network-level isolation
(private network / mTLS / service-mesh policy). Isolation between
workspaces comes from the SA token Grafana receives per call, not from
process/instance separation. The service never reasons about *which
human* triggered a call — per-user authorisation is fully resolved before
dispatch.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| One `grafana-mcp` process per workspace | ❌ Rejected | Isolation by process boundary, but at a much higher operational cost than needed — the migrated register entry frames this as the default being explicitly avoided. |
| One logical, horizontally-scaled `grafana-mcp` service, isolation via per-call SA token forwarding | ✅ Chosen | Isolation comes from the credential presented per call (hop B), not from process separation — cheaper to operate at scale. |
| Use `grafana-mcp`'s built-in caller-auth (`MCP_GRAFANA_SERVER_TOKEN`) for hop A | ❌ Rejected | Also wants the `Authorization` header, which cannot coexist with per-call SA-token forwarding on the same header; hop A is instead protected by network-level isolation. |

## 4. Consequences

- **Positive —** a single horizontally-scaled service is cheaper to operate
  than one process per workspace, without sacrificing workspace isolation.
- **Negative / accepted trade —** hop A's protection is network-level
  (private network / mTLS / service-mesh policy) rather than an
  application-level caller-auth mechanism, because the built-in one
  conflicts with per-call SA-token forwarding.
- **Follow-on work —** the Tool Gateway must resolve the correct Grafana SA
  token per call and forward it verbatim; the service itself never
  reasons about which human triggered a call.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original
  register entry was marked "verified live" for this decision. Mechanism:
  [`../../design/tool-registry-and-authority.md`](../../design/tool-registry-and-authority.md).
