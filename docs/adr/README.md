# Architecture Decision Records

This directory is the **decision log**: why the system is the way it is.
`../design/` is the **design layer**: how it actually works. The split between
them is load-bearing and is defined in section 4 — read that section before writing in
either place.

> **Conventions verified 2026-09-13** against primary sources: [MADR
> 4.0.0](https://adr.github.io/madr/), the [ADR GitHub
> organization](https://adr.github.io/), [arc42
> section 9](https://docs.arc42.org/section-9/), and [AWS Prescriptive Guidance on
> ADRs](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html).
> Where we deviate from a source, section 2 says so and why.

---

## 1. What earns an ADR

Not every decision. All four sources agree on one filter — **architectural
significance** — and it is the main defence against decision-log sprawl:

> "An Architectural Decision (AD) is a justified design choice that addresses a
> functional or non-functional requirement that is **architecturally
> significant**." — adr.github.io

> "Document only architecturally relevant decisions!" — arc42 Tip 9-1

AWS, citing Richards & Ford, scopes it to decisions affecting **structure,
non-functional requirements, dependencies, interfaces, or construction
techniques**. Applied here, project decisions sort into three kinds, and only
the first is an ADR:

| Kind | Example | Goes to |
|---|---|---|
| **Architectural decision** | "Durable-execution engine is DBOS Transact" | **An ADR** |
| **Amendment** to an existing decision | "All MCP servers are streamable-HTTP" (qualifies the Tool Gateway decision) | The parent ADR's `amended_by`, as its own ADR only if separately citable |
| **Convention / standard** | The identifier-prefix table; the glossary itself | A *living* normative doc, mandated by one ADR |

The third row matters more than it looks. A convention like the identifier-prefix
registry **grows every time a new external system is integrated** — so it cannot
live inside an immutable ADR. The ADR records *the decision to prefix and why*;
the prefix list lives in [`../GLOSSARY.md`](../GLOSSARY.md) and is edited freely.

## 2. Numbering and grouping

**Numbers are globally unique and never reused.** Our ADR numbers *are* the
historic `D`-numbers: `D1` → `0001`, `D69` → `0069`. Reference form is
**`ADR-0037`**; `D37` is an accepted legacy alias.

**Grouping is by subdirectory**, which is the community practice MADR documents
for exactly this problem:

> "Large projects may accumulate hundreds of decision records over time, and
> finding them might be hard. MADR does not enforce any repository or directory
> organization structure… MADR logs may be categorized by defining
> subdirectories and put the ADRs into these folders." — MADR

> "Ideally, the ADR categorization [uses] the same organizing principles as
> other artifacts such as the code… This comes down to a meta-decision to be
> made rather early on." — MADR

**Deliberate deviation from MADR:** MADR's own
[ADR-0010](https://adr.github.io/madr/decisions/0010-support-categories.html)
chose *subfolders with **local** IDs*. We use *subfolders with **global** IDs* —
an option MADR explicitly considered and did not forbid. Reason: several hundred
hand-written `D`-number citations already exist across `../design/` and
`../diagrams/`. Local renumbering would invalidate all of them silently, which
is a far worse failure than a slightly less tidy `ls`.

Categories mirror `../design/` one-for-one, so that **each category has exactly
one design document** (see section 4):

```
adr/
├── README.md                  ← this file: the conventions
├── 0000-template.md
├── DECISION-INDEX.md          ← generated; start here
├── platform/       surfaces, deployment topology, Grafana ownership
├── agent/          framework, durable execution, run model
├── tools/          Tool Gateway, MCP invariants, authority lattice
├── identity/       authn, federation, approval authority
├── tenancy/        scoping, roles, budgets, lifecycle
├── streaming/      event model, transport, control liveness
├── observability/  telemetry, audit, compliance
└── conventions/    cross-cutting normative rules (vocabulary, identifiers)
```

`conventions/` is the exception to the one-category-one-design-doc rule: its
ADRs mandate rules that apply everywhere, and their living content is
[`../GLOSSARY.md`](../GLOSSARY.md).

## 3. Status lifecycle

```
proposed ──▶ accepted ──▶ superseded   (by one or more later ADRs)
    │            │
    └──▶ rejected└──▶ deprecated       (no longer applies; nothing replaced it)
```

**Accepted means immutable.** This is universal across the sources:

> "When the team accepts an ADR, it becomes immutable. If new insights require a
> different decision, the team proposes a new ADR." — AWS

Only front matter (`superseded_by`, `amended_by`) and the *Verification* log may
change after acceptance. **Supersession is a link, never an edit** — the
striking-through of `D55` in place, and the "*(partially superseded)*"
annotation on `D64`, are exactly what this rule removes. "Partially superseded"
is not a status: split the ADR into the clause that survived and the clause that
did not, and supersede only the latter.

`rejected` ADRs are kept. AWS: "the ADR owner adds a reason for the rejection to
prevent future discussions on the same topic."

## 4. ADR vs. design — the single-source-of-truth rule

The duplication risk is real and arc42 names it directly:

> "Please use your judgement to decide whether an architectural decision should
> be documented here in this central section or whether you better document it
> locally… **Avoid redundant texts.**" — arc42 section 9

AWS gives the cut line:

> "One of the most powerful aspects of the ADR structure is that it focuses on
> **the reason for the decision rather than how the team implemented it**." — AWS

So:

| Owns | ADR (`adr/`) | Design (`design/`) |
|---|---|---|
| Content | **Why.** Forces, options considered, option chosen, trade accepted | **How.** Mechanism, schema, sequence, failure modes, monitoring |
| Mutability | Immutable once accepted | Living |
| Shape | Point-in-time record | Current state |
| On change | New ADR supersedes | Edit in place |

Three rules make this enforceable:

1. **The three-sentence rule.** An ADR's *Decision* section is at most a short
   paragraph plus a link to its design document. If it needs more, the surplus is
   design, not decision. (Today's register violates this badly — several cells
   run to 3,000 characters of design detail, which is why it is 261 KB.)
2. **Design cites, never re-argues.** A design document may restate a decision in
   one sentence for readability, and must cite `ADR-NNNN` as the authority. It may
   never *qualify, extend or except* a decision — that is a new ADR.
3. **The edit test.** If a single fact changes, exactly one file should need
   editing. If two do, the fact is duplicated and one of them is a copy.

Conflict resolution, in strict order: **[`../GLOSSARY.md`](../GLOSSARY.md)
(vocabulary) → accepted ADR (decision) → design doc (mechanism).** A design
document that contradicts an accepted ADR is a bug in the document, never a
competing opinion.

## 5. You are not meant to read all of them

A decision log is a **queried** artefact, not a syllabus:

> "Project members **skim the headlines** of each ADR to get an overview of the
> project context. They **read the ADRs to dive deep** into project
> implementations and design choices." — AWS

Onboarding reads `../diagrams/` (shape), `../GLOSSARY.md` (vocabulary) and
`../design/` (mechanism) — roughly five documents. The ADRs are consulted when
someone asks "why is it like this?" or proposes changing it, and in review to
check a change against an accepted decision. If you feel you must read all of
them to get work done, the **design layer** has failed, not the ADR layer.

## 6. Front matter (required, machine-readable)

```yaml
---
id: ADR-0037
title: Durable-execution engine is DBOS Transact
status: accepted          # proposed | accepted | rejected | superseded | deprecated
date: 2026-09-12
deciders: [<name>]
category: agent           # must match the containing subdirectory
tags: [orchestration, durability, v1]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: [ADR-0003, ADR-0030, ADR-0033]
design: ../../design/durable-execution.md
verified: 2026-09-12      # omit unless checked against a live/primary source
---
```

`relates_to` and `design` replace the prose habit of "see D3, D30, D33" — they
are fields a link-checker and the index generator can read.

## 7. Body

Use [`0000-template.md`](./0000-template.md): **Context → Decision → Considered
options → Consequences → Verification.**

- **One decision per ADR.** If the title needs an "and", it is two ADRs.
- **`Considered options` is mandatory and names the rejected option with its
  reason.** This is where the value of the old `research/` folder survives; an
  option rejected without a recorded reason gets re-proposed within six months.
- **Consequences include the negative ones.** The register does this well —
  "accepted tension", "the trade, stated plainly" — keep it.
- **Identifiers are prefixed** per ADR-0059. An unprefixed identifier is a review
  defect.
- **Verification cites source and date.** Undated verification decays invisibly.
- **Cross-references name the document.** Write `section 4`, never the section
  glyph — the glyph reads as "somewhere, in some document". A reference to another
  file must link that file first: *"see [`tool-gateway.md`](../design/tool-gateway.md)
  section 3"*. A bare `section 3` always means *this* document. Enforced in CI.

## 8. The index

[`DECISION-INDEX.md`](./DECISION-INDEX.md) is **generated** from front matter —
number, title, status, date, category, supersession links, plus the legacy
`D`/`R` alias map. Being generated it cannot drift from the ADRs it summarises,
which was the old register's main failure mode.

Regenerate after any ADR change:

```sh
python3 scripts/gen_adr_index.py
```

CI fails if the committed index differs from the generated one.

`DECISION-REGISTER.md` was replaced by the index on 2026-09-13. Its non-index
content was relocated as follows:

| Old register section | Now |
|---|---|
| section 1 Locked decisions (D1–D69) | One ADR per decision, across the eight categories |
| section 2 Tool Gateway responsibilities | [`../design/tool-gateway.md`](../design/tool-gateway.md) |
| section 3 Observability pipeline | [`../design/observability-pipeline.md`](../design/observability-pipeline.md) |
| section 4 Recommendations (R3–R8) | Resolved; alias map in the index |
| section 5 Deferred deep-dives | All four closed |
| section 6 UX-first track status | [`../diagrams/README.md`](../diagrams/README.md) |
| section 7 Not yet discussed | [`../backlog/future-sessions.md`](../backlog/future-sessions.md) |
| section 8 Capability inventory | [`../backlog/capability-inventory.md`](../backlog/capability-inventory.md) |

## 9. Hygiene, enforced in CI

Enforced by `scripts/check_docs.py`, run in CI (`.github/workflows/docs.yml`):

1. **Every relative link resolves.** The dead `open-questions/` references proved
   the need — a directory was deleted and ten citations were left pointing at it.
2. **Every `ADR-NNNN` reference resolves** to a real ADR.
3. **Front matter is complete** and `category` matches the containing directory.
4. **Every accepted ADR names a design document that exists**, or `design: none`.
5. **`status: superseded` requires a non-empty `superseded_by`.**
6. **No references to removed paths** (`research/`, `open-questions/`), except in
   explicitly marked provenance notes.

Run locally before pushing:

```sh
python3 scripts/check_docs.py && python3 scripts/gen_adr_index.py
```
