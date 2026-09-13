1](./S1-dbos-langgraph-mcp.md) | Does LangGraph run beneath a DBOS workflow boundary with per-call step granularity? | **Phase 1** + C4 L3 | 5 days |
| [S2](./S2-dbos-system-db-rls-pci.md) | Does the DBOS system database coexist with `FORCE ROW LEVEL SECURITY`, and is it in PCI scope? | **Phase 1** + C4 L3 | 4 days |
| [S3](./S3-eval-sink.md) | Langfuse or Phoenix for the internal eval sink? | **Phase 1** | 2 days |
| [S4](./S4-provisional-model.md) | Which model and serving stack for Phase 1? | **Phase 1** | 2 days |

S1 and S2 are the real blockers — they can invalidate locked decisions. S3 and
S4 are selections between known options and can run in parallel with them**S1 is closed** — it confirmed ADR-0039/0040/0041 as designed; see
[`../../design/durable-execution.md`](../../design/durable-execution.md)
section 4.4 for the experiment log.
**S2 is the remaining real blocker** — it can still invalidate locked
decisions. S3 and S4 are selections between known options and can run in
parallel with it.

