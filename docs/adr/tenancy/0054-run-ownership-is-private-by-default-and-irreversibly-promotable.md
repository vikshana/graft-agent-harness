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

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Run ownership and visibility — ADR-0036 confirmed, superseding R4.** `user_initiated` Runs are **private to the initiating Principal**, explicitly promotable to tenant-shared; **promotion is irreversible**, because un-sharing after the fact is security theatre and complicates the audit story (archive instead). `system_initiated` Runs (webhook and Schedule) are **born tenant-shared** — nobody initiated them, so private-by-default would render them invisible to everyone. Sharing is what activates ADR-0032's soft-lock driver model; a private Run has no multi-viewer concern by construction. **Archival changes storage tier and mutability (read-only), never visibility.** **A de-provisioned Principal's private Runs become inaccessible in-product** — the end-to-end audit trail (ADR-0015, insert-only, 12 months) is the forensic path, not the product UI.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
