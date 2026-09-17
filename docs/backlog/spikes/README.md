1](./S1-dbos-langgraph-mcp.md) | Does LangGraph run beneath a DBOS workflow boundary with per-call step granularity? | **Phase 1** + C4 L3 | 5 days |
| S3 | Langfuse is the internal eval sink; see [ADR-0074](../../adr/observability/0074-langfuse-is-the-internal-evaluation-sink.md) | **Phase 1** | closed |
| S4 | Model and serving arrangement follows organisation policy; see [ADR-0075](../../adr/platform/0075-organisation-policy-governs-model-and-serving-selection.md) | **Phase 1** | closed |

S1 and S2 were the real blockers and are now closed. S2 is recorded in
[`ADR-0073`](../../adr/platform/0073-dbos-system-database-is-separate-and-pci-scoped.md).
S3 and S4 are closed by ADR-0074 and ADR-0075. **S1 is closed** — it confirmed
ADR-0039/0040/0041 as designed; see
[`../../design/durable-execution.md`](../../design/durable-execution.md)
section 4.4 for the experiment log.


