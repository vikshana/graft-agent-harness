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

ADR-0019 placed the MCP Authorization Server (Token Service) as logically
distinct from the Tool Gateway, but did not settle whether they must be
separately *deployed* services or could ship as one deployable with a
module boundary instead. The security requirement that actually matters
(ADR-0007: separation from the agent/worker process) needed distinguishing
from operational overhead that a network-level split would add without
buying additional security.

## 2. Decision

**The Token Service/AS, the Tool Gateway and the Tool Registry ship as one
deployable — the Authority Service — composed of independent modules,
decomposable later without redesign.** Supersedes ADR-0019's *placement*
(AS co-located with the harness API); ADR-0019's **logical** distinctness
is untouched and is now enforced by module boundary instead of by network
boundary. **The security boundary that matters is unchanged:** ADR-0007's
requirement is separation from the **agent/worker process**, because
in-process policy enforcement is not a boundary when the primary threat is
indirect prompt injection — not separation of the AS from the RS, which
ADR-0019 already anticipated could be co-located. **Five invariants make
the merge safe, and each is a build-time or config-time fact rather than a
convention:** (1) the **signing key is reachable only by the AS module**;
the gateway module holds the public JWKS and nothing else, so it
**cannot** shortcut validation even if someone wants to; (2) the gateway
**validates tokens independently** — signature, `aud`, `exp` — over the
published JWKS endpoint, including on loopback, with no shared in-memory
token state; (3) **separate listeners and separate network policy** — AS
discovery/JWKS/mint endpoints and the MCP endpoint are distinct ports with
distinct ingress rules, preserving ADR-0018's hop-A network isolation and
making a future split a DNS change rather than a refactor; (4) **no shared
mutable request context** between modules; (5) **independent rate
limits**. **The AS verifies raw surface credentials itself** — the harness
API forwards `X-Grafana-Id`, the Slack assertion or the webhook secret
verbatim over mTLS rather than asserting a verified identity on the
caller's behalf, preserving the confused-deputy property ADR-0023 exists
to protect. **Named decomposition triggers, so the split is a decision and
not a drift:** exposing the Tool Gateway to external MCP clients (which
would require Dynamic Client Registration and change the AS threat
model — already flagged in `mcp-authorization-server.md` section 7), or
materially divergent scaling profiles between token minting and tool
brokering.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| Keep the AS and Tool Gateway as separately deployed network services (ADR-0019's original placement) | ❌ Rejected (superseded) | Adds operational overhead (two deployables, two network hops) without buying additional security beyond what module-boundary separation already provides, given ADR-0007's actual requirement is separation from the agent/worker process. |
| Ship the Token Service, Tool Gateway and Registry as one deployable ("Authority Service") composed of independent modules | ✅ Chosen | Preserves the security-relevant separation (from the agent/worker process) and ADR-0019's logical distinctness, enforced by module boundary plus five build/config-time invariants, while reducing deployment overhead. |

## 4. Consequences

- **Positive —** one deployable to operate instead of two, with a clean,
  named path to split again later (DNS change, not a refactor) if a
  decomposition trigger fires.
- **Negative / accepted trade —** the five invariants (signing-key
  isolation, independent token validation, separate listeners/network
  policy, no shared mutable request context, independent rate limits)
  must all hold and be enforced at build/config time — a merge that
  violated any of them would reintroduce the confused-deputy risk
  ADR-0023 and ADR-0007 exist to prevent.
- **Follow-on work —** the AS must verify raw surface credentials itself
  (not trust an asserted identity from the harness API), preserving the
  confused-deputy property.
- **Revisit trigger —** exposing the Tool Gateway to external MCP clients
  (requiring Dynamic Client Registration and changing the AS threat
  model), or materially divergent scaling profiles between token minting
  and tool brokering.

## 5. Verification

- Not separately verified against a live source; no claim in the original
  register entry was marked "verified live" for this decision. Mechanism:
  [`../../design/tool-registry-and-authority.md`](../../design/tool-registry-and-authority.md).
