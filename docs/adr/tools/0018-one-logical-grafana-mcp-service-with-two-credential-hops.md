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

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**One logical, horizontally-scaled `grafana-mcp` service**, never one process per workspace as a default. There are **two distinct hops with two distinct credentials**: Tool Gateway → `grafana-mcp` (hop A) and `grafana-mcp` → Grafana (hop B, the Grafana SA token, `Authorization: Bearer glsa_...`). Hop B's SA token is resolved per call by the Tool Gateway and forwarded verbatim via `GRAFANA_FORWARD_HEADERS=Authorization`. **Locked 2026-09-12:** hop A does **not** use `grafana-mcp`'s built-in caller-auth (`MCP_GRAFANA_SERVER_TOKEN`), since that mechanism also wants the `Authorization` header and cannot coexist with per-call SA-token forwarding on it — hop A is instead protected by network-level isolation (private network / mTLS / service-mesh policy). Isolation between workspaces comes from the SA token Grafana receives per call, not from process/instance separation. The service never reasons about *which human* triggered a call — per-user authorisation is fully resolved before dispatch.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
