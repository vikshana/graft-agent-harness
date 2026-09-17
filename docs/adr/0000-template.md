---
id: ADR-NNNN
title: <imperative, present-tense summary of the decision>
status: proposed          # proposed | accepted | rejected | superseded | deprecated
date: YYYY-MM-DD
deciders: [<name>]
category: <platform|agent|tools|identity|tenancy|streaming|observability|conventions>
tags: [<free-form>]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
design: ../../design/<doc>.md   # or `none` if this decision has no living mechanism doc
verified: YYYY-MM-DD       # omit unless checked against a live/primary source
---

# ADR-NNNN — <title>

> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism:
> [`../../design/<doc>.md`](../../design/<doc>.md).

---

## 1. Context

What forces make this decision necessary right now? State the problem and the
constraints, not the answer. No solution language here.

## 2. Decision

One short paragraph: what was decided, stated as a direct, quotable claim.
If this needs a design write-up longer than that, the surplus belongs in
`design/`, not here (see [`README.md`](./README.md) section 4, rule 1).

## 3. Considered options

Mandatory. Name every option that was seriously considered, including the one
rejected, and say *why* it lost — not just that it did.

| Option | Verdict | Why |
|---|---|---|
| <chosen option> | ✅ Chosen | <reason> |
| <rejected option> | ❌ Rejected | <reason> |

## 4. Consequences

Include the negative ones.

- **Positive —** …
- **Negative / accepted trade —** …
- **Follow-on work —** …
- **Revisit trigger —** what would make this worth reopening, or "none observed".

## 5. Verification

How and when this was checked against a live/primary source (a spike, a
running system, an upstream doc). Cite the source and the date. Omit only if
truly nothing has been verified yet — say so explicitly rather than leaving
this section silently empty.

