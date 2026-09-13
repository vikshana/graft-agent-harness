---
id: ADR-0066
title: Control liveness is three independent server-side clocks
status: accepted
date: 2026-09-13
deciders: []
category: streaming
tags: [streaming, events]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
design: ../../design/streaming-and-events.md
legacy_id: D66
---

# ADR-0066 — Control liveness is three independent server-side clocks

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D66`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Control liveness is three independent server-side clocks, and “10 minutes” is now a security parameter rather than a UX nicety** — because ADR-0065 makes control equal authority. State lives in `run_control(graft_run_id, driver_graft_principal_id NULL, driver_since, last_interaction_at, transport_state, disconnected_at, control_version)`; **`NULL` driver means unowned**. **Idle clock** — anchored on `last_interaction_at`, default **10 min**, reset by an *interactive act* (send a prompt, steer, cancel, request/grant/release control, approve or reject, or click “keep control”) and **not** by receiving events, scrolling, replaying history, expanding an artifact or tab focus: the idle clock asks *“is a human still deciding?”*, which is a different question from *“is a browser still open?”*. **Disconnect clock** — anchored on `disconnected_at`, default **2 min**, reset by reconnect; the signal is Grafana Live `SubscribeStream` teardown for the plugin surface and the equivalent for the post-v1 web frontend. **Approval clock** — anchored on the `action_proposed` event, **≥72h**, never reset, expiry closes the Run as `expired` (ADR-0047), and runs **independently** of the other two. **Slack has no transport liveness, so a Slack driver has only the idle clock** — a deliberate, documented asymmetry, not an oversight. **Evaluation is a 30-second scheduled sweep (DBOS scheduled workflow, ADR-0047 substrate), not a durable timer per Run reset on every interaction** — resetting a durable timer on every keystroke is write amplification against the exact Postgres ADR-0048 named as the binding scale constraint; the reset is a cheap `UPDATE`, the evaluation is periodic, and release therefore fires within 30s of nominal (accepted and stated, because the number is now security-relevant). Driver is warned in-product at **T−60s** with a one-click “keep control”; best-effort in Slack. **On expiry, control goes to nobody, never to a specific viewer** — auto-handing control now means auto-handing approval authority, and silently promoting whoever happens to be watching is precisely the failure mode to avoid; any `responder` or `tenant_admin` viewer may then claim it. **Force-release is `tenant_admin`-only** (never `platform_admin`, ADR-0065) and emits a **non-sampled audit record** naming forcer, displaced driver and any pending `proposal_hash`. **We chose detection over friction:** a cool-down before the forcer may claim was considered and **rejected** — during an incident a deliberate delay is itself a harm — so the forcer may claim immediately, and a force-release followed by the forcer approving within the same Run is **flagged in the audit chain as a self-escalation pattern and tracked as a platform metric**. **Claiming control on a `system_initiated` Run is the moment a human attaches, and is therefore the upgrade point to `user_initiated`** — refining ADR-0013, which located the upgrade at approval; the capability token is re-minted at claim time with write classes subject to L3 and L5. Until someone claims, a `system_initiated` Run has no driver and nobody can approve, which is correct because it is structurally read-only anyway.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
