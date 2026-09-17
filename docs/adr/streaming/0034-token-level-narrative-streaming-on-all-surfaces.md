---
id: ADR-0034
title: Token-level narrative streaming on all surfaces
status: accepted
date: 2026-09-12
deciders: [ ]
category: streaming
tags: [ streaming, events ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ]
relates_to: [ ]
design: ../../design/streaming-and-events.md
legacy_id: D34
---

# ADR-0034 — Token-level narrative streaming on all surfaces

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D34`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).

---

## 1. Context

An initial caution suggested using a coarser event granularity for Grafana specifically (e.g. whole-message rather than
token-by-token), on the assumption that chat would be an occasional, RCA-only interaction. ADR-0036 made every
interaction — including frequent, conversational chat — the same run primitive, which changes the UX bar for
responsiveness. Separately, raw tool output needed a policy: stream it verbatim, or reduce/truncate it before it reaches
any surface.

## 2. Decision

**Token-level narrative streaming on all surfaces, including Grafana Live** (deliberately overriding an
initially-proposed "coarser granularity for Grafana" caution — chosen for UX responsiveness now that chat is a frequent
interaction, not an occasional RCA-only one, per ADR-0036). Step/event-level for everything else (tool calls,
hypotheses, evidence, plans) on all surfaces except Slack, which is always batched/throttled regardless. **Raw tool
output is never streamed verbatim** — always truncated/summarised inline (Tool Gateway result-reduction, ties to
`context-management`), with the untruncated artifact fetched on demand via
`GET /runs/{id}/events/{graft_event_id}/artifact` (object storage per ADR-0030), rendered per content type: log viewer,
JSON viewer, and specifically a **diff view** for proposed dashboard/alert-rule changes so an approving user can
evaluate an `action_proposed` event properly before confirming.

## 3. Considered options

| Option                                                                                                                                    | Verdict     | Why                                                                                                                                                                                                |
|-------------------------------------------------------------------------------------------------------------------------------------------|-------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Coarser (whole-message) streaming granularity for Grafana specifically                                                                    | ❌ Rejected | Chat is now a frequent, conversational interaction (ADR-0036), not an occasional RCA-only one — coarser granularity would hurt UX responsiveness for the common case.                              |
| Stream raw tool output verbatim to all surfaces                                                                                           | ❌ Rejected | Large or noisy tool output would overwhelm the narrative stream; truncated/summarised inline text with an on-demand artifact fetch serves the common case while keeping the full detail available. |
| Token-level streaming on all surfaces (Slack batched/throttled), with truncated/summarised tool output and an on-demand artifact endpoint | ✅ Chosen   | Matches the UX bar for frequent chat interactions; keeps the stream readable while preserving full detail via `GET /runs/{id}/events/{graft_event_id}/artifact`.                                   |

## 4. Consequences

- **Positive —** consistent, responsive token-level narrative UX across surfaces; approving users get a proper diff view
  for proposed dashboard/alert-rule changes before confirming.
- **Negative / accepted trade —** Slack, lacking a native token-streaming UX, is always batched/throttled regardless of
  what other surfaces get.
- **Follow-on work —** the artifact-fetch endpoint must render per content type (log viewer, JSON viewer, diff view),
  and ties into the Tool Gateway's result-reduction / context-management design.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).
