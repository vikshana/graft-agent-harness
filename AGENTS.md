# AGENTS.md

Instructions for AI coding agents working in this repository.

---

## 1. Read this first: there is no application code yet

This repository currently contains **documentation and two Python scripts**. There is no `/api`, no `/worker`, no
`src/`. That is not an omission — Phase 1 has not started, and is deliberately gated on two spikes
(`docs/backlog/spikes/`).

**If you are asked to implement a feature, stop and check
[`docs/backlog/roadmap.md`](docs/backlog/roadmap.md) first.** Building ahead of the roadmap here is expensive: the
architecture is fully decided across 72 ADRs, and code that violates a locked decision is not a bug to be fixed later —
it is rework.

```
docs/adr/         72 ADRs — why the system is the way it is (IMMUTABLE)
docs/design/      how the decided things work (living)
docs/diagrams/    C4 L1 and L2
docs/GLOSSARY.md  normative vocabulary — wins over every other document
docs/backlog/     what is still undecided, the roadmap, and spike briefs
scripts/          documentation hygiene tooling
```

## 2. Commands

```sh
python3 scripts/check_docs.py      # MUST pass before any commit touching docs/
python3 scripts/gen_adr_index.py   # regenerate the ADR index after ADR changes
```

Both run in CI (`.github/workflows/docs.yml`). `check_docs.py` currently reports **0 errors, 0 warnings** — keep it that
way.

There is no test suite, linter or build yet. When Phase 1 starts, the quality gates are specified in the roadmap, not
invented ad hoc.

## 3. Hard rules — violating these fails review

### Documentation

| Rule                                                                                                                                                     | Source                         |
|----------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------|
| **An accepted ADR is immutable.** Never edit its Decision text. To change a decision, write a **new** ADR and set `superseded_by` on the old one         | `docs/adr/README.md`           |
| **Never strike through or annotate a superseded ADR in place.** Supersession is a link                                                                   | ADR-0055 is the worked example |
| **Never renumber an ADR.** Numbers are permanent; hundreds of cross-references depend on them                                                            | `docs/adr/README.md` section 2 |
| **Never hand-edit `DECISION-INDEX.md`.** It is generated; run the script                                                                                 |                                |
| **Never create a `research/` directory.** Surveys are inputs to a decision, not living documents. Their residue belongs in an ADR's *Considered options* | `docs/adr/README.md` section 1 |
| **Never use the section glyph.** Write `section 4`. A bare `section N` means *this* document; a cross-file reference must link the file first            | CI-enforced                    |
| **Every ADR must be placed in a roadmap phase**                                                                                                          | CI-enforced                    |
| Use `ADR-0037`, not `D37`. `D`-numbers are legacy aliases only                                                                                           |                                |

### Vocabulary — `docs/GLOSSARY.md` wins over every other document

- **"Workspace" is banned.** It names nothing of ours. In older text, read it as **Tenant**.
- **Foreign terms are never used bare:** write `GrafanaOrg`, `SlackWorkspace`,
  `SlackEnterprise`, `LGTMTenant` — never "org", "workspace" or "tenant" alone when referring to another system.
- **Every identifier is prefixed with the system that owns it** (ADR-0059).
  `graft_*` means we mint it; `grafana_*`, `slack_*`, `dbos_*`, `lgtm_*` mean someone else does. **An unprefixed
  identifier is a review defect.**
  Separator follows the medium: `snake_case` in SQL/JSON/claims, dotted in OTel (`graft.tenant.id`), `X-Graft-*` in HTTP
  headers.

## 4. Architectural invariants for when code exists

These are the decisions most likely to be violated by plausible-looking code. Each is locked; none is a preference.

| Invariant                                                                                                                                                      | ADR                |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------|
| **Nothing reaches a customer system directly.** Every call goes agent → Tool Gateway → MCP server → system. A direct client is a hole in five controls at once | ADR-0068, ADR-0007 |
| **MCP servers are streamable-HTTP, never stdio**                                                                                                               | ADR-0070           |
| **`graft_tenant_id` on every row, event, span and audit record**                                                                                               | ADR-0051           |
| **`FORCE ROW LEVEL SECURITY`; establish scope with `SET LOCAL`, never `SET`** (a transaction-mode pooler reassigns connections between Tenants)                | ADR-0050           |
| **No ambient or thread-local Tenant context, ever.** Scope travels as an explicit argument                                                                     | ADR-0050           |
| **Isolation is never thread-level.** Parallelism is a scheduling problem, not an isolation one                                                                 | ADR-0050           |
| **Only the internal `runtime` module imports `dbos`**                                                                                                          | ADR-0048           |
| **LangGraph is compiled with no checkpointer.** DBOS step checkpoints are the single source of execution truth                                                 | ADR-0040           |
| **One LLM call = one step; one tool call = one step.** Steps return **pointers, never large payloads**                                                         | ADR-0041           |
| **No Redis.** The durable event log is Postgres only, fan-out via `LISTEN/NOTIFY`                                                                              | ADR-0030           |
| **No arbitrary code execution.** Read-only tools plus server-side result reduction; the sandbox is post-v1 behind the `ToolExecutor` seam                      | ADR-0004           |
| **Upstream MCP tool descriptions are untrusted and are never forwarded to the model.** Serve our own curated description                                       | ADR-0063           |
| **Custom instructions are prompt text, never policy.** They cannot enable a tool, widen a Role, alter a budget or bypass an approval                           | ADR-0062           |
| **The audit actor derives from the verified credential**, never from agent or tool output                                                                      | ADR-0015           |
| **Approval happens in Grafana, never in Slack**, and is a re-authenticated act                                                                                 | ADR-0014, ADR-0065 |
| **Read-only until Phase 3.** Write classes are denied at lattice layer L2 — a policy row, not developer discipline                                             | ADR-0063, ADR-0013 |
| `dbos_workflow_id = graft_run_id`                                                                                                                              | ADR-0060           |

**If a task seems to require breaking one of these, that is a finding.** Raise it as a proposed superseding ADR — do not
work around it silently.

## 5. Where a change goes

| The change is…                                              | Put it in                                                                       |
|-------------------------------------------------------------|---------------------------------------------------------------------------------|
| A new decision, with alternatives considered                | A new ADR in the right `docs/adr/<category>/`, from `docs/adr/0000-template.md` |
| How a decided thing works — schema, sequence, failure modes | The relevant `docs/design/*.md`                                                 |
| A word's meaning                                            | `docs/GLOSSARY.md` (and an ADR if it changes a locked term)                     |
| Something not yet decided                                   | `docs/backlog/`                                                                 |
| A time-boxed investigation                                  | `docs/backlog/spikes/`                                                          |

**Do not duplicate between ADR and design.** The ADR owns *why* (immutable); the design doc owns *how* (living). Test:
if one fact changes, exactly one file should need editing.

## 6. Conventions

- **Commits:** Conventional Commits — `docs:`, `feat(docs):`, `chore:`. Explain *why*, not just what; this repo's
  history is used as evidence.
- **Prose: British English throughout — CI-enforced.** `behaviour`, `licence`
  (noun), `catalogue`, `normalised`, `standardised`, `authorisation`.
  Note `licensed`/`licensing` are correct British (licence = noun, license =
  verb), so they are not flagged.
  **Three exempt contexts**, and the way to use them is to mark the text as what
  it is:
  1. **Protocol tokens and proper nouns** — the `Authorization` HTTP header, the
     **MCP Authorization Server**, OAuth's `authorization-code` grant. Backtick
     them, or keep the capital.
  2. **Verbatim quotations** — blockquote or quote them. Never "correct" a
     source's spelling; that misquotes it. The MADR and OWASP quotes in this
     repo keep `categorized`, `organizing`, `recognize`, `Minimize`.
  3. **Filenames, URLs and code** — never rewritten. ADR-0056's file is still
     `...-the-harness-authorizes.md` while its title reads *authorises*;
     filenames are identifiers, and renaming would break every inbound link.
  `color` appears only inside Mermaid and CSS; `colour` is ADR-0046's blue/green
  deploy colour. Neither is a prose signal — do not "fix" either.
- Direct and specific. State trade-offs plainly — "we deliberately trade X for Y" is a complete and acceptable sentence.
- **Verification:** if you check a claim against a live or primary source, cite **what, against what, and when**.
  Undated verification decays invisibly.
- **Tables over prose** for anything enumerable.

## 7. Common traps in this repository

1. **Assuming `v1` means Phase 1.** It does not. `v1` is a scope boundary covering Phases 1–4; the ADRs' "Phase 2 /
   post-v1" means Phase 5.
2. **Treating a design doc as authoritative over an ADR.** It is not. If they conflict, the document is wrong.
3. **Reading older documents literally.** Text predating ADR-0051 says
   "workspace"; text predating ADR-0059 uses unprefixed identifiers. Both read as their current forms.
4. **Citing a superseded ADR.** Check `status` in the front matter. ADR-0055 is superseded by ADR-0065 — approval
   follows the *driver*, not the initiator.
5. **Deleting a directory without fixing inbound links.** This has already happened once (`open-questions/`, leaving ten
   dead links). Run
   `check_docs.py`.
