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

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**The MCP client for hop 1 should use `mcp.client.auth.oauth2.OAuthClientProvider`** (from the official `mcp` Python SDK, a dependency of `langchain-mcp-adapters`) as the `auth=` value if/when RFC 9728 discovery is needed, rather than implementing discovery ourselves. `langchain-mcp-adapters` itself does not implement discovery — it only exposes a generic `httpx.Auth` hook — but the underlying SDK's `OAuthClientProvider` is spec-complete (RFC 9728 discovery, 401-triggered re-discovery, PKCE, refresh). Per ADR-0019 section 5, the interactive parts of this are not needed for hop 1 day one; this decision fixes *which library* to reach for if/when they are.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
