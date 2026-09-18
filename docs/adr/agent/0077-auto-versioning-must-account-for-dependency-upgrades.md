---
id: ADR-0077
title: Auto-versioning must account for dependency upgrades
status: proposed
date: 2026-09-18
deciders: [project owner]
category: agent
tags: [agent, dbos, application-version, deployment, blue-green]
supersedes: []
superseded_by: []
amends: [ADR-0046]
amended_by: []
relates_to: [ADR-0037, ADR-0039, ADR-0040, ADR-0060]
design: ../../design/durable-execution.md
verified: 2026-09-18
phase: Phase 1
---

# ADR-0077 — Auto-versioning must account for dependency upgrades

> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism:
> [`../../design/durable-execution.md`](../../design/durable-execution.md).

---

## 1. Context

ADR-0046 chooses DBOS auto-computed application versions and rejects pinning the
version to a Git SHA or image tag. The Gate 0.3 experiment checked DBOS 3.0.0's
application-version calculation using the locked workflow source and runtime.
The observed DBOS implementation includes the DBOS package version together
with registered workflow source and application name. Consequently, a DBOS
dependency upgrade can change the application version and drain otherwise
source-compatible in-flight work.

The exact redacted evidence is
[`evidence/gate-0.3/result.json`](../../../specs/phase-1-walking-skeleton/evidence/gate-0.3/result.json),
under `G03-D`, and the command record is
[`evidence/gate-0.3/commands.json`](../../../specs/phase-1-walking-skeleton/evidence/gate-0.3/commands.json).
Both were verified on 2026-09-18.

## 2. Decision

Propose accepting that DBOS dependency upgrades may cause auto-versioning drains
when DBOS changes the computed application version, while preserving
version-compatible recovery and continuing to reject Git or image identifiers
as the application version; alternatively, a controlled dependency-aware
version policy may reduce unnecessary drains only after it proves equivalent
recovery safety.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| Accept dependency-upgrade drains under DBOS auto-versioning | ✅ Chosen conservative disposition | It preserves DBOS's version-compatible recovery rule and makes the drain visible and safe, at the cost of capacity and rollout time. |
| Pin application version to a Git SHA or image tag | ❌ Rejected | It violates ADR-0046's decision and couples recovery compatibility to release identifiers rather than executable workflow compatibility. |
| Ignore DBOS package-version input and retain the old version | ❌ Rejected | It could run incompatible DBOS runtimes under one recovery version and invalidate the safety assumption behind version matching. |
| Use a controlled dependency-aware version policy | 🟡 Requires proof before selection | It may reduce unnecessary drains, but requires an independently verified compatibility matrix, source/runtime fingerprint and rollback rule. |

## 4. Consequences

- **Positive —** dependency upgrades receive a conservative, observable drain rather than silently sharing a recovery version with a different DBOS runtime.
- **Negative / accepted trade —** safe upgrades may require blue/green overlap and temporary duplicate capacity even when application workflow source is unchanged.
- **Follow-on work —** test identical source/runtime stability, DBOS-version changes, non-DBOS dependency changes, workflow source changes, rollback, and in-flight recovery across separate processes and databases.
- **Revisit trigger —** reopen if a controlled dependency-aware policy proves equivalent version-compatible recovery without Git/image version pinning.

## 5. Verification

On 2026-09-18, Gate 0.3 ran DBOS 3.0.0 with the locked Python runtime. The
`G03-D` result records stable recomputation for identical source/runtime and a
different recomputed version after source registration. DBOS 3.0.0's source
implementation also includes the DBOS package version in the version hash;
this proposed disposition preserves ADR-0046's no-Git/no-image-pin rule while
making dependency-upgrade drains an explicit follow-up test requirement.
