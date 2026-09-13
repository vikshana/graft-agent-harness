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

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Tool Gateway** — the agent never calls MCP servers directly. A **separate service**, not a library, because in-process policy enforcement is not a security boundary (primary threat: indirect prompt injection from application logs).

### 2.7b — folded from legacy `D7b`

The Tool Gateway **speaks MCP in both directions**: an MCP server to the agent, an MCP client to upstreams. LangChain's `langchain-mcp-adapters` points at exactly one endpoint.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
