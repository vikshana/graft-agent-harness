---
id: ADR-NNNN
title: <Imperative, single decision. No "and".>
status: proposed          # proposed | accepted | rejected | superseded | deprecated
date: YYYY-MM-DD
deciders: []
tags: []
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
# verified: YYYY-MM-DD    # only if claims were checked against a live/primary source
---

# ADR-NNNN — <Title>

> **Status: <status> (<date>).** <One sentence: what this decides, and what it
> changes about a previous ADR, if anything.>
>
> Vocabulary per [`../GLOSSARY.md`](../GLOSSARY.md).

---

## 1. Context

What forces this? State the problem, the constraints that are not negotiable
(product constraints, compliance regime, prior accepted ADRs), and what breaks
if we do nothing. Written so someone with no memory of the session understands
why the question was even asked.

## 2. Decision

**One paragraph, bolded lead, active voice.** The decision itself, stated so it
can be checked against code in review.

Then the operative detail — the rule, the shape, the invariant — only as far as
is needed to make the decision unambiguous. Elaboration goes to `../design/`.

## 3. Considered options

Mandatory. Every serious option, including the chosen one, and **why each
rejected one was rejected**. An option rejected without a recorded reason will
be re-proposed within six months.

| Option | Verdict | Why |
|---|---|---|
| **<Chosen>** | ✅ Chosen | |
| <Alternative> | ❌ Rejected | |
| <Alternative> | ⏸ Deferred | To <which ADR/backlog item>, and on what trigger |

## 4. Consequences

Both directions. The good ones justify the decision; the bad ones are what stop
it being relitigated as a surprise.

- **Positive —**
- **Negative / accepted trade —** State it plainly. "We deliberately trade X for
  Y" is a complete and acceptable sentence.
- **Follow-on work —** What must now exist because of this.
- **Revisit trigger —** The observable condition or metric that reopens this.
  Prefer a measurable one over "if it becomes a problem".

## 5. Verification

Only for claims checked against a primary source. Cite **what** was checked,
**against what**, and **when** — undated verification decays invisibly.

- `<claim>` — verified <date> against <source: live instance, RFC, vendor doc,
  upstream source code>. Result: <what was actually observed>.
