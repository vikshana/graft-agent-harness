---
id: ADR-0069
title: Token Service, Tool Gateway and Registry ship as one Authority Service
status: accepted
date: 2026-09-13
deciders: []
category: tools
tags: [tools, mcp, authority]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: [ADR-0019, ADR-0007]
design: ../../design/tool-registry-and-authority.md
legacy_id: D69
---

# ADR-0069 — Token Service, Tool Gateway and Registry ship as one Authority Service

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D69`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/tool-registry-and-authority.md`](../../design/tool-registry-and-authority.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**The Token Service/AS, the Tool Gateway and the Tool Registry ship as one deployable — the Authority Service — composed of independent modules, decomposable later without redesign.** Supersedes ADR-0019's *placement* (AS co-located with the harness API); ADR-0019's **logical** distinctness is untouched and is now enforced by module boundary instead of by network boundary. **The security boundary that matters is unchanged:** ADR-0007's requirement is separation from the **agent/worker process**, because in-process policy enforcement is not a boundary when the primary threat is indirect prompt injection — not separation of the AS from the RS, which ADR-0019 already anticipated could be co-located. **Five invariants make the merge safe, and each is a build-time or config-time fact rather than a convention:** (1) the **signing key is reachable only by the AS module**; the gateway module holds the public JWKS and nothing else, so it **cannot** shortcut validation even if someone wants to; (2) the gateway **validates tokens independently** — signature, `aud`, `exp` — over the published JWKS endpoint, including on loopback, with no shared in-memory token state; (3) **separate listeners and separate network policy** — AS discovery/JWKS/mint endpoints and the MCP endpoint are distinct ports with distinct ingress rules, preserving ADR-0018's hop-A network isolation and making a future split a DNS change rather than a refactor; (4) **no shared mutable request context** between modules; (5) **independent rate limits**. **The AS verifies raw surface credentials itself** — the harness API forwards `X-Grafana-Id`, the Slack assertion or the webhook secret verbatim over mTLS rather than asserting a verified identity on the caller's behalf, preserving the confused-deputy property ADR-0023 exists to protect. **Named decomposition triggers, so the split is a decision and not a drift:** exposing the Tool Gateway to external MCP clients (which would require Dynamic Client Registration and change the AS threat model — already flagged in `mcp-authorization-server.md` §7), or materially divergent scaling profiles between token minting and tool brokering.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
