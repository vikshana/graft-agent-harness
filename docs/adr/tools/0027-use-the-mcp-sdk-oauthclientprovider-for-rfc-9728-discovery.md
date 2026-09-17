---
id: ADR-0027
title: Use the MCP SDK OAuthClientProvider for RFC 9728 discovery
status: accepted
date: 2026-09-12
deciders: []
category: tools
tags: [tools, mcp, authority]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
design: ../../design/tool-registry-and-authority.md
legacy_id: D27
---

# ADR-0027 — Use the MCP SDK OAuthClientProvider for RFC 9728 discovery

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D27`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/tool-registry-and-authority.md`](../../design/tool-registry-and-authority.md).

---

## 1. Context

Hop 1 (Tool Gateway → upstream MCP server) may eventually need RFC 9728
protected-resource-metadata discovery for OAuth. `langchain-mcp-adapters`
itself does not implement discovery — it only exposes a generic `httpx.Auth`
hook — so a library needed choosing for whichever component fills that
hook, rather than implementing discovery from scratch.

## 2. Decision

**The MCP client for hop 1 should use
`mcp.client.auth.oauth2.OAuthClientProvider`** (from the official `mcp`
Python SDK, a dependency of `langchain-mcp-adapters`) as the `auth=` value
if/when RFC 9728 discovery is needed, rather than implementing discovery
ourselves. `langchain-mcp-adapters` itself does not implement discovery —
it only exposes a generic `httpx.Auth` hook — but the underlying SDK's
`OAuthClientProvider` is spec-complete (RFC 9728 discovery, 401-triggered
re-discovery, PKCE, refresh). Per ADR-0019 section 5, the interactive
parts of this are not needed for hop 1 day one; this decision fixes
*which library* to reach for if/when they are.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| Implement RFC 9728 discovery ourselves against the generic `httpx.Auth` hook | ❌ Rejected | Reinvents a spec-complete implementation that already exists in the official MCP SDK, which `langchain-mcp-adapters` already depends on. |
| Use `mcp.client.auth.oauth2.OAuthClientProvider` from the official `mcp` Python SDK | ✅ Chosen | Spec-complete (RFC 9728 discovery, 401-triggered re-discovery, PKCE, refresh) and already a transitive dependency — no new library to adopt. |

## 4. Consequences

- **Positive —** no bespoke discovery/OAuth implementation to build or
  maintain; the choice is made in advance so there's no ambiguity when the
  need arises.
- **Negative / accepted trade —** none recorded; this decision fixes a
  future choice rather than committing to work now.
- **Follow-on work —** per ADR-0019 section 5, the interactive parts are
  not needed for hop 1 on day one — this decision only fixes which library
  to reach for when they are.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original
  register entry was marked "verified live" for this decision. Mechanism:
  [`../../design/tool-registry-and-authority.md`](../../design/tool-registry-and-authority.md).
