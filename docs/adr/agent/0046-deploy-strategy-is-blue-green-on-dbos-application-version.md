---
id: ADR-0046
title: Deploy strategy is blue/green on DBOS application version
status: accepted
date: 2026-09-12
deciders: [ ]
category: agent
tags: [ agent, orchestration, durability ]
supersedes: [ ]
superseded_by: [ADR-0077]
amends: [ ]
amended_by: [ ]
relates_to: [ ]
design: ../../design/durable-execution.md
legacy_id: D46
---

# ADR-0046 — Deploy strategy is blue/green on DBOS application version

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D46`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

Deploys need a strategy that does not force a full drain on every change — including prompt-only edits that don't affect
workflow structure — but does drain when workflow structure genuinely changes. DBOS ties workflow recovery to an
"application version," which can either be auto-computed or pinned explicitly by the deploy pipeline.

## 2. Decision

**Deploy strategy is blue/green with DBOS's auto-computed application version.** A DBOS application version defaults to
a **hash of workflow source code**; every workflow is tagged with the version it started on, and **recovery only matches
like versions**. We deliberately **do not** pin
`application_version` to a git SHA or image tag — that would force a full drain on every deploy, including prompt-only
changes; the auto-hash changes only when *what steps run, or in what order* changes, which is exactly when draining is
required. In-flight runs finish on their original version (confirmed as the desired behaviour, 2026-09-12). New work is
enqueued pinned to the latest version via `get_latest_application_version()`; scheduled workflows target the latest
version automatically. **Colour retirement is gated in the deploy pipeline on
`list_workflows(app_version=…, status=["ENQUEUED","PENDING"])` returning empty** — a machine check, not a human eyeball.
`DBOS.patch()`/
`deprecate_patch()` is the documented escape hatch for urgent fixes that must reach already-running investigations, not
the default.

## 3. Considered options

| Option                                                                      | Verdict     | Why                                                                                                           |
|-----------------------------------------------------------------------------|-------------|---------------------------------------------------------------------------------------------------------------|
| Pin `application_version` to a git SHA or image tag                         | ❌ Rejected | Would force a full drain on every deploy, including prompt-only changes that don't affect workflow structure. |
| Use DBOS's auto-computed application version (hash of workflow source code) | ✅ Chosen   | Version changes only when what steps run, or in what order, changes — exactly when draining is required.      |

## 4. Consequences

- **Positive —** in-flight runs finish on their original version; new work and scheduled workflows automatically target
  the latest version via
  `get_latest_application_version()`.
- **Negative / accepted trade —** colour retirement requires a machine check
  (`list_workflows(app_version=…, status=["ENQUEUED","PENDING"])`
  returning empty) gated in the deploy pipeline, rather than a simpler human eyeball on traffic.
- **Follow-on work —** `DBOS.patch()`/`deprecate_patch()` is the documented escape hatch for urgent fixes reaching
  already-running investigations, not the default deploy path.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original register entry was marked "verified live" for
  this decision. Mechanism:
  [`../../design/durable-execution.md`](../../design/durable-execution.md).
