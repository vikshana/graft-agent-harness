---
id: ADR-0077
title: Auto-versioning must account for dependency upgrades
status: accepted
date: 2026-09-19
deciders: [project owner]
category: agent
tags: [agent, dbos, application-version, deployment, blue-green]
supersedes: [ADR-0046]
superseded_by: []
amends: []
amended_by: []
relates_to: [ADR-0037, ADR-0039, ADR-0040, ADR-0060]
design: ../../design/durable-execution.md
verified: 2026-09-19
phase: Phase 1
---

# ADR-0077 — Auto-versioning must account for dependency upgrades

> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism:
> [`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

ADR-0046 currently chooses DBOS auto-computed application versions and rejects
pinning the version to a Git SHA or image tag. Gate 0.3 found that this does not
give a sufficient compatibility boundary: a helper-only change altered runtime
output while DBOS reported the same automatic application version. The direct
DBOS-version comparison also showed that changing the DBOS runtime can change
the automatic application version even when the registered workflow source and
application name are unchanged.

The exact redacted evidence is
[`evidence/gate-0.3/result.json`](../../../specs/phase-1-walking-skeleton/evidence/gate-0.3/result.json),
under `G03-D`, and the command record is
[`evidence/gate-0.3/commands.json`](../../../specs/phase-1-walking-skeleton/evidence/gate-0.3/commands.json).
The direct DBOS-version and helper-only comparison is retained in
[`dbos-version-comparison-result.json`](../../../specs/phase-1-walking-skeleton/evidence/gate-0.3/dbos-version-comparison-result.json),
with commands in
[`dbos-version-comparison-commands.json`](../../../specs/phase-1-walking-skeleton/evidence/gate-0.3/dbos-version-comparison-commands.json).
These comparison artefacts were verified on 2026-09-19.

## 2. Decision

**Supersede ADR-0046**, rather than amend it, with an
all-release-drain policy:

1. Every mutually versioned release receives an explicit application
   compatibility revision. The value must be a released compatibility/revision
   identifier. It must not be a Git commit SHA or image tag, because release
   provenance is not a semantic compatibility contract.
2. Every new release drains all prior release cohorts, including when the
   workflow source appears unchanged. Recovery remains matching-version only:
   an executor may recover a workflow only when its explicit application
   compatibility revision matches the revision recorded for that workflow.
3. The old-version capacity remains available until the drain check finds zero
   `PENDING`, `ENQUEUED`, and `DELAYED` work for every prior cohort. The drain
   controller alerts on orphaned cohorts or revisions with work but no live
   executor. A rollback from B to A is a reverse drain: it restores A capacity,
   routes new work to A, and applies the same checks before retiring B.

The owner selected this direction and formally accepted ADR-0077 on
2026-09-19. ADR-0046 is superseded by this decision. The operational evidence
listed in Verification remains outstanding; acceptance records the decision
and does not claim implementation or gate completion.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| Give every mutually versioned release an explicit released compatibility revision and drain all prior cohorts | ✅ Owner-selected proposal | It prevents false compatibility when helper or runtime changes are not represented by DBOS's automatic hash, while preserving matching-version recovery and making the drain observable. |
| Keep DBOS auto-computed application versions as the release boundary | ❌ Rejected by the proposal | The helper-only experiment changed runtime output while the automatic version remained `6291bf83d0ad38ca22f83e659454e749`; relying on that value can falsely group incompatible recovery work. |
| Use a Git commit SHA or image tag as the explicit application version | ❌ Rejected | The compatibility value must be a released compatibility/revision identifier, not deployment provenance. |
| Use a dependency-aware exception policy that avoids some drains | 🟡 Not selected | It would need independently verified coverage for helper/runtime changes, matching-version recovery, orphan handling, and reverse-drain rollback; the owner selected the safer all-release drain instead. |

## 4. Consequences

- **Positive —** every mutually versioned release has an explicit compatibility boundary, preventing false compatibility from helper or runtime changes that DBOS's automatic version can miss.
- **Positive —** matching-version recovery remains explicit and operationally visible: old-version capacity, drain checks, orphan alerts, and reverse-drain rollback are all required.
- **Negative / accepted trade —** every release drains all prior cohorts, requiring blue/green overlap, retained old-version capacity, and potentially substantial capacity and rollout-time cost even when application workflow source is unchanged.
- **Follow-on work —** test the release-revision contract, `PENDING`/`ENQUEUED`/`DELAYED` drain checks, orphan alerts, matching-version recovery, rollback, and in-flight recovery across separate processes and databases.
- **Revisit trigger —** a new proposed ADR is required to change this all-release-drain policy; evidence that a narrower policy is safe is not an amendment to this proposal.

## 5. Verification

### Verified by experiment — 2026-09-19

The isolated comparison lane ran the same minimal registered workflow and
application name with DBOS 2.31.1 and DBOS 3.0.0, across Python 3.11, 3.12,
and 3.13, using separate disposable PostgreSQL system databases and schemas.
The actual automatic application versions were `c794758e9a435661e8952586635ba345`
for DBOS 2.31.1 and `469124d570d40494405ef8ad74749acb` for DBOS 3.0.0; both
workflows completed `SUCCESS`. The DBOS 2.31.1 system schema recorded migration
108, and the DBOS 3.0.0 system schema recorded migration 114. These are
observations from separate launches, not a drain or cross-version recovery
test.

The same lane launched DBOS 3.0.0 with baseline and changed helper modules in
separate processes. The output changed from
`helper-v1:gate-0-3-version-fingerprint` to
`helper-v2:gate-0-3-version-fingerprint`, while both launches reported
automatic version `6291bf83d0ad38ca22f83e659454e749`. This is an observed
false-compatible result, not evidence that the helper change was safe. No
LangGraph upgrade test was claimed.

### Not yet tested

The retained comparison did not exercise operational draining, orphan alerts,
matching-version recovery, or reverse-drain rollback. It therefore supports the
owner-selected decision but does not prove those controls. The required
operational evidence remains outstanding and does not change the formal
acceptance recorded below.

### Owner acceptance — 2026-09-19

The project owner formally accepted ADR-0077 on 2026-09-19. This acceptance
records the all-release-drain decision and supersedes ADR-0046; it does not
claim completion of the outstanding operational evidence for drain checks,
orphan alerts, matching-version recovery, or reverse-drain rollback.
