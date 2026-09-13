# Spikes

Time-boxed investigations that gate a roadmap phase. Each file is
**self-contained** and can be taken into its own session by someone who was not
in the decision sessions.

| Spike | Question | Gates | Timebox |
|---|---|---|---|
| [S1](./S1-dbos-langgraph-mcp.md) | Does LangGraph run beneath a DBOS workflow boundary with per-call step granularity? | **Phase 1** + C4 L3 | 5 days |
| [S2](./S2-dbos-system-db-rls-pci.md) | Does the DBOS system database coexist with `FORCE ROW LEVEL SECURITY`, and is it in PCI scope? | **Phase 1** + C4 L3 | 4 days |
| [S3](./S3-eval-sink.md) | Langfuse or Phoenix for the internal eval sink? | **Phase 1** | 2 days |
| [S4](./S4-provisional-model.md) | Which model and serving stack for Phase 1? | **Phase 1** | 2 days |

S1 and S2 are the real blockers — they can invalidate locked decisions. S3 and
S4 are selections between known options and can run in parallel with them.

## How to run one

1. Read the spike's **Constraints** section first. Those are locked decisions;
   the spike does not get to relitigate them. If the spike concludes a
   constraint is *wrong*, that is a finding — raise it as a superseding ADR
   rather than quietly working around it.
2. Work to the **Method**. Stop at the timebox.
3. Record the outcome as an **ADR** (use [`../../adr/0000-template.md`](../../adr/0000-template.md)),
   update the named design document, and delete the spike file.

Spikes are ephemeral. A completed spike leaves an ADR behind, not a document
here.

## Conventions

- Numbers `S1`–`S4` match the gate IDs in [`../roadmap.md`](../roadmap.md)
  section 6 and the markers in [`../future-sessions.md`](../future-sessions.md).
- New spikes continue the sequence and are added to the table above and to the
  roadmap's gate table.
