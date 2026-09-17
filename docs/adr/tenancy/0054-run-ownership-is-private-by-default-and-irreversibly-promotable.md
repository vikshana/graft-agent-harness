---
id: ADR-0054
title: Run ownership is private by default and irreversibly promotable
status: accepted
date: 2026-09-13
deciders: []
category: tenancy
tags: [tenancy, scoping, rbac]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
design: ../../design/tenancy-and-scoping.md
legacy_id: D54
---

# ADR-0054 — Run ownership is private by default and irreversibly promotable

> **Status: accepted (2026-09-13).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D54`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/tenancy-and-scoping.md`](../../design/tenancy-and-scoping.md).

---

## 1. Context

An earlier recommendation (R4) held that investigations are
workspace-owned, not user-owned, by default. ADR-0036 established that
every interaction — chat included — is the same run primitive, which
raises the question of default visibility more sharply: a blanket
workspace-owned default would make every private chat visible to the
whole Tenant. `system_initiated` runs (webhook/Schedule) additionally have
no natural "initiator" to default ownership to.

## 2. Decision

**Run ownership and visibility — ADR-0036 confirmed, superseding R4.**
`user_initiated` Runs are **private to the initiating Principal**,
explicitly promotable to tenant-shared; **promotion is irreversible**,
because un-sharing after the fact is security theatre and complicates the
audit story (archive instead). `system_initiated` Runs (webhook and
Schedule) are **born tenant-shared** — nobody initiated them, so
private-by-default would render them invisible to everyone. Sharing is
what activates ADR-0032's soft-lock driver model; a private Run has no
multi-viewer concern by construction. **Archival changes storage tier and
mutability (read-only), never visibility.** **A de-provisioned Principal's
private Runs become inaccessible in-product** — the end-to-end audit trail
(ADR-0015, insert-only, 12 months) is the forensic path, not the product
UI.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| Keep R4's workspace-owned-by-default model for every run | ❌ Rejected | Would make every private chat interaction visible to the whole Tenant by default, once ADR-0036 made chat the same run primitive as investigations. |
| Allow un-sharing a promoted Run back to private | ❌ Rejected | Security theatre — anyone who already saw it while shared still saw it — and complicates the audit story; archival (read-only, different storage tier) serves the "wind this down" need instead. |
| Private-by-default for `system_initiated` runs too | ❌ Rejected | Nobody initiated them, so a private-by-default rule would render them invisible to everyone; they are instead born tenant-shared. |
| `user_initiated` private-by-default, irreversibly promotable; `system_initiated` born tenant-shared | ✅ Chosen | Matches each run type's actual ownership semantics: a human owns their own private work by default, while a run nobody initiated must be visible to someone from the start. |

## 4. Consequences

- **Positive —** private runs have no multi-viewer concern by
  construction; sharing is exactly the event that activates ADR-0032's
  soft-lock driver model, not a separate concept.
- **Negative / accepted trade —** promotion to tenant-shared is
  irreversible — there is no way to make a shared run private again, only
  to archive it (changing storage tier and mutability, never visibility).
- **Follow-on work —** a de-provisioned Principal's private runs become
  inaccessible in-product; the audit trail (ADR-0015) remains the
  forensic path, not the product UI.
- **Revisit trigger —** none observed.

## 5. Verification

- Not separately verified against a live source; no claim in the original
  register entry was marked "verified live" for this decision. Mechanism:
  [`../../design/tenancy-and-scoping.md`](../../design/tenancy-and-scoping.md).
