# Diagrams

C4-style architecture diagrams for the Graft Agent Harness.

We work **outside-in**: the UX comes first, the architecture is derived from it.
Each level is confirmed before the next one is drawn.

| Level | Doc | Status |
|---|---|---|
| **L1 — System Context** | [`c4-l1-system-context.md`](./c4-l1-system-context.md) | 🟡 **In review — revision 4** (ADR-0001–ADR-0069) |
| **L2 — Containers** | [`c4-l2-containers.md`](./c4-l2-containers.md) | 🟡 **In review — revision 2** (ADR-0001–ADR-0069) |
| L3 — Components | _not yet drawn_ | ⛔ Blocked on L2 sign-off + the two prototype spikes in L2 §9 |
| L4 — Code | Not planned. Code is the diagram. | — |

**Normative sources.** [`../GLOSSARY.md`](../GLOSSARY.md) owns the vocabulary and
wins over any diagram. [`../adr/DECISION-INDEX.md`](../adr/DECISION-INDEX.md)
owns the decisions. A diagram that disagrees with either is a bug in the diagram.

## v1 scope at a glance

- **Surfaces:** Grafana App Plugin + Slack. **No web frontend in v1** (post-v1,
  same API, no private capabilities).
- **One primitive: the Run.** Chat, dashboard/alert authoring and RCA are the
  same thing, with the same durability, audit trail and approval gate (ADR-0036).
- **Tenant ≡ GrafanaOrg, 1:1.** `graft_tenant_id` is the **only** scoping key.
  The word *workspace* has been removed from our vocabulary (ADR-0051, ADR-0052).
- **Approval happens in Grafana, by the Run's current driver, re-authenticated.**
  Slack launches it, never performs it. **Control *is* authority**, so every
  transfer of the wheel is an audited transfer of approval rights (ADR-0014, ADR-0065, ADR-0066).
- **No direct clients on customer systems.** Tool Gateway → MCP → system, always,
  with three named non-agent exceptions (ADR-0068).
- **The Token Service, Tool Gateway and Tool Registry ship as one deployable** —
  the Authority Service — three modules, five enforced invariants, named
  decomposition triggers (ADR-0069).
- **Capability is a five-layer intersection**, and the platform has the last word
  — including a kill switch effective at the next tool call (ADR-0063).
- **Limits form a ceiling chain** `platform ≥ tenant ≥ principal ≥ run`; at-cap
  behaviour differs deliberately per scope (ADR-0057).
- **Two independent regional deployments** (GCP, AliCloud). Run data never leaves
  its home region (ADR-0049).

## Conventions

Diagrams are **Mermaid `flowchart`** using C4 colour conventions rather than
Mermaid's experimental `C4Context` renderer, which lays out poorly at this size.
Sequence diagrams are used at L2 for flows, where a box-and-arrow view would hide
ordering.

| Style | Meaning |
|---|---|
| Dark blue | **Person** — a Principal |
| Blue | **Our system / container** — inside the boundary we build |
| **Crimson** | **Authority module** — Token Service, Tool Gateway, Tool Registry. One deployable, three modules. If you review one thing for security, review these |
| Green | **State** — a datastore we own |
| Steel blue | **Platform-operated external** — we run it, we do not build it (Grafana) |
| Grey | **External system** — we integrate, we do not own |
| Dashed grey | **Deferred** — out of scope for v1, drawn to show the seam exists |

## Rules for these diagrams

1. **L1 shows one box for our system.** Any urge to decompose it belongs in L2.
2. Every external system on L1 must be justified by a **named UX journey** in the
   same document. No speculative integrations.
3. Every container on L2 must be traceable to a **locked decision**, not to an
   implementation preference. L2 §8 — *deliberately not containers* — is as
   load-bearing as the diagram itself.
4. Anything deferred is drawn dashed rather than omitted — the scope boundary is
   more useful than a clean picture.
5. Open questions live in a numbered table at the end of each document, with an
   explicit **blocking / not blocking** column. A diagram that hides what is
   unresolved is worse than no diagram.
6. **Diagrams are parse-validated before commit**, not eyeballed. Extract every
   ```` ```mermaid ```` block and run it through `mermaid.parse`. Two real
   syntax bugs in r2 were caught this way and would otherwise have shipped —
   note that **`;` is a statement separator inside sequence-diagram messages**,
   so it must never appear in message or note text.
