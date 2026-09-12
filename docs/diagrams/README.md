# Diagrams

C4-style architecture diagrams for the Graft Agent Harness.

We work **outside-in**: the UX comes first, the architecture is derived from it.
Each level is confirmed before the next one is drawn.

| Level | Doc | Status |
|---|---|---|
| **L1 — System Context** | [`c4-l1-system-context.md`](./c4-l1-system-context.md) | 🟡 **In review — revision 2** |
| L2 — Containers | _not yet drawn_ | ⛔ Blocked on L1 sign-off |
| L3 — Components | _not yet drawn_ | ⛔ Blocked on L2 |
| L4 — Code | Not planned. Code is the diagram. | — |

## v1 scope at a glance

- **Surfaces:** Grafana App Plugin + Slack. **No Web UI in v1** (post-v1, same API).
- **Workspace = Grafana Org.** Config is org-scoped and shared; per-user variation
  is authorisation, not configuration.
- **Approval happens in Grafana.** Slack launches it, never performs it.
- **Limits form a ceiling chain**, platform caps not customer-raisable.

## Conventions

Diagrams are **Mermaid `flowchart`** using C4 colour conventions rather than
Mermaid's experimental `C4Context` renderer, which lays out poorly at this size.

| Style | Meaning |
|---|---|
| Dark blue, rounded | **Person** — a human actor |
| Blue | **Our system** — inside the boundary we build and own |
| Grey | **External system** — we integrate, we do not own |
| Dashed grey | **Deferred** — out of scope for v1, drawn to show the seam exists |

## Rules for these diagrams

1. **L1 shows one box for our system.** Any urge to decompose it belongs in L2.
2. Every external system on L1 must be justified by a **named UX journey** in the
   same document. No speculative integrations.
3. Anything deferred is drawn dashed rather than omitted — the scope boundary is
   more useful than a clean picture.
