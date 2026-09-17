---
id: ADR-0066
title: Control liveness is three independent server-side clocks
status: accepted
date: 2026-09-13
deciders: [ ]
category: streaming
tags: [ streaming, events ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ]
relates_to: [ ]
design: ../../design/streaming-and-events.md
legacy_id: D66
---

# ADR-0066 — Control liveness is three independent server-side clocks

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D66`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).

---

## 1. Context

ADR-0065 makes control of a shared run equal to approval authority, which raises the stakes of ADR-0064's "10 minutes"
disconnect/idle figure from a UX nicety to a security parameter. A single bare timeout cannot correctly distinguish "is
a human still deciding?" from "is a browser still open?"
from "has an approval been waiting too long?" — three different questions that were being conflated, and Slack's lack of
transport liveness signal needed accounting for separately.

## 2. Decision

**Control liveness is three independent server-side clocks, and "10 minutes" is now a security parameter rather than a
UX nicety** — because ADR-0065 makes control equal authority. State lives in
`run_control(graft_run_id, driver_graft_principal_id NULL, driver_since,
last_interaction_at, transport_state, disconnected_at, control_version)`; **`NULL` driver means unowned**. **Idle
clock** — anchored on
`last_interaction_at`, default **10 min**, reset by an *interactive act*
(send a prompt, steer, cancel, request/grant/release control, approve or reject, or click "keep control") and **not** by
receiving events, scrolling, replaying history, expanding an artifact or tab focus: the idle clock asks *"is a human
still deciding?"*, which is a different question from *"is a browser still open?"*. **Disconnect clock** — anchored on
`disconnected_at`, default **2 min**, reset by reconnect; the signal is Grafana Live `SubscribeStream` teardown for the
plugin surface and the equivalent for the post-v1 web frontend. **Approval clock** — anchored on the `action_proposed`
event, **≥72h**, never reset, expiry closes the Run as `expired` (ADR-0047), and runs **independently** of the other
two. **Slack has no transport liveness, so a Slack driver has only the idle clock** — a deliberate, documented
asymmetry, not an oversight. **Evaluation is a 30-second scheduled sweep (DBOS scheduled workflow, ADR-0047 substrate),
not a durable timer per Run reset on every interaction** — resetting a durable timer on every keystroke is write
amplification against the exact Postgres ADR-0048 named as the binding scale constraint; the reset is a cheap `UPDATE`,
the evaluation is periodic, and release therefore fires within 30s of nominal (accepted and stated, because the number
is now security-relevant). Driver is warned in-product at **T−60s** with a one-click "keep control"; best-effort in
Slack. **On expiry, control goes to nobody, never to a specific viewer** — auto-handing control now means auto-handing
approval authority, and silently promoting whoever happens to be watching is precisely the failure mode to avoid; any
`responder` or `tenant_admin` viewer may then claim it. **Force-release is `tenant_admin`-only** (never
`platform_admin`, ADR-0065) and emits a **non-sampled audit record** naming forcer, displaced driver and any pending
`proposal_hash`. **We chose detection over friction:** a cool-down before the forcer may claim was considered and
**rejected** — during an incident a deliberate delay is itself a harm — so the forcer may claim immediately, and a
force-release followed by the forcer approving within the same Run is **flagged in the audit chain as a self-escalation
pattern and tracked as a platform metric**. **Claiming control on a `system_initiated` Run is the moment a human
attaches, and is therefore the upgrade point to `user_initiated`** — refining ADR-0013, which located the upgrade at
approval; the capability token is re-minted at claim time with write classes subject to L3 and L5. Until someone claims,
a `system_initiated` Run has no driver and nobody can approve, which is correct because it is structurally read-only
anyway.

## 3. Considered options

| Option                                                                                                     | Verdict     | Why                                                                                                                                                                                                         |
|------------------------------------------------------------------------------------------------------------|-------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A single bare timeout ("10 minutes") governing driver liveness                                             | ❌ Rejected | Conflates three different questions — is a human still deciding, is a browser still connected, has an approval waited too long — that need independent answers now that control equals approval authority.  |
| Three independent server-side clocks (idle, disconnect, approval), each with its own anchor and reset rule | ✅ Chosen   | Each clock answers exactly one question; the approval clock in particular must never reset on activity elsewhere, since it governs a bounded wait independent of driver presence.                           |
| A durable timer per Run, reset on every interaction                                                        | ❌ Rejected | Write amplification against Postgres, the exact binding scale constraint named by ADR-0048; a 30-second scheduled sweep with a cheap `UPDATE` reset achieves the same outcome within an accepted 30s slack. |
| A cool-down before a force-release forcer may claim control                                                | ❌ Rejected | During an incident a deliberate delay is itself a harm; the forcer may claim immediately, with self-escalation flagged and tracked as a platform metric instead.                                            |
| On expiry, hand control to whoever happens to be watching                                                  | ❌ Rejected | Auto-handing control now means auto-handing approval authority; silently promoting a bystander viewer is precisely the failure mode to avoid — control instead goes to nobody until explicitly claimed.     |

## 4. Consequences

- **Positive —** the three clocks correctly separate "human still deciding" from "browser still connected" from
  "approval waited too long", each independently tuned and auditable.
- **Negative / accepted trade —** evaluation is a 30-second scheduled sweep rather than an instantaneous durable timer,
  so release fires within 30s of nominal rather than exactly on time — accepted because the alternative (a durable timer
  reset on every keystroke) is write amplification against Postgres.
- **Follow-on work —** claiming control on a `system_initiated` run is now the upgrade point to `user_initiated`
  (refining ADR-0013, which had located the upgrade at approval); the capability token is re-minted at claim time.
- **Revisit trigger —** none observed; self-escalation (force-release followed by the forcer approving within the same
  run) is tracked as an ongoing platform metric rather than a one-time check.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/streaming-and-events.md`](../../design/streaming-and-events.md).
