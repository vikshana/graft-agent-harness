# Documentation

| Read this | When |
|---|---|
| [`GLOSSARY.md`](./GLOSSARY.md) | **First.** Normative vocabulary — wins over every other document |
| [`diagrams/`](./diagrams/README.md) | To see the shape: C4 L1 context, L2 containers |
| [`design/`](./design/) | To understand how something works |
| [`adr/DECISION-INDEX.md`](./adr/DECISION-INDEX.md) | To find out *why* it is that way |
| [`backlog/`](./backlog/README.md) | To see what is still undecided |

## The five kinds of document

| Directory | Kind | Mutability |
|---|---|---|
| `adr/` | Decision — why, options, trade accepted | **Immutable** once accepted |
| `design/` | Design — mechanism, schema, failure modes | Living |
| `diagrams/` | Model — boxes and arrows | Living, revision-stamped |
| `GLOSSARY.md` | Normative vocabulary | Living; changes are themselves ADRs |
| `backlog/` | Open question | Ephemeral — deleted when its ADR lands |

There is deliberately **no `research/` directory**. Surveys and comparisons are
inputs to a decision, not artefacts of one; their durable residue is an ADR's
*Considered options*. See [`adr/README.md`](./adr/README.md) §1.

## Conventions

Decisions follow [`adr/README.md`](./adr/README.md). New ADRs start from
[`adr/0000-template.md`](./adr/0000-template.md).

```sh
python3 scripts/check_docs.py      # hygiene: links, references, front matter
python3 scripts/gen_adr_index.py   # regenerate the decision index
```

Both run in CI on any change under `docs/`.
