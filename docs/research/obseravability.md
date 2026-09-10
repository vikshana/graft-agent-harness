# Q: How do we ensure observability in this end to end system?

## A: 
Observability in an end-to-end agentic SRE system requires combining standard distributed system tracing (OpenTelemetry) with specialized **agent trajectory tracking** (prompts, reasoning steps, tool payloads, and token costs).

| Architecture Layer | What is Monitored | Key Metrics & Telemetry | Recommended OSS Tools |
| --- | --- | --- | --- |
| **Frontend & Gateway** | REST/SSE endpoints, auth validation, connection health | Request latency (p95/p99), active SSE streams, 4xx/5xx rates | FastAPI + OpenTelemetry SDK |
| **Task Queue & Workers** | Job queue depth, worker pool capacity, execution time | Queue lag, task failure rates, node execution duration | Temporal Metrics / Redis Exporter |
| **Agent & Graph State** | Reasoning trajectories, graph edge decisions, loop counts | Graph depth, retry counts, HITL pause durations | LangGraph Checkpoints, OpenLIT |
| **LLM & Model Gateway** | Prompts, completions, model latency, token costs | Tokens/sec, cost per incident, prompt cache hit rate | Langfuse, Arize Phoenix, LiteLLM OTel |
| **Sandbox & Tools** | Script execution, CPU/RAM usage, stdout/stderr, network | Execution exit codes, sandbox startup time, resource usage | Daytona/E2B Telemetry, eBPF / Vector |
| **Security & Compliance** | User identity, impersonated actions, PR approvals | Audit logs, RBAC violations, approved actions | Structured JSON Logs $\rightarrow$ S3 Glacier / OpenSearch |

---

**1. End-to-End Distributed Tracing (W3C Context Propagation)**
To trace a user's click on the UI all the way to a `kubectl` script execution in a sandbox, propagate the W3C `traceparent` header across every boundary:

1. **Frontend $\rightarrow$ Gateway:** The UI initiates a request with a generated `trace_id`.
2. **Gateway $\rightarrow$ Queue:** FastAPI creates the root span and injects the `traceparent` into the Redis/Temporal message payload metadata.
3. **Queue $\rightarrow$ LangGraph Worker:** The worker extracts the `trace_id` from the queue message, making every LangGraph node execution (`triage`, `hypothesis_engine`, `tool_execution`) a child span of the initial job.
4. **Worker $\rightarrow$ Sandbox / MCP:** The worker passes the trace context to MCP tool wrappers and sandbox scripts so container runtimes share the exact same trace ID.

**2. Agent Trajectory & LLM-Specific Observability**
Standard APMs (like Datadog or Prometheus) cannot visualize agent reasoning. Integrate an agent-native tracing tool like **Langfuse**, **Arize Phoenix**, or **OpenLIT**:

* **Trajectory Visualization:** View the full step-by-step decision tree of an RCA run, showing exact prompt templates, retrieved RAG context, LLM reasoning, tool invocation payloads, and model outputs.
* **Cost & Token Attribution:** Tag every LLM request with `user_id`, `incident_id`, and `model_name`. Set up real-time cost tracking to trigger alerts if an agent run exceeds budget thresholds.
* **Prompt Versioning & Drift Tracking:** Track exact system prompt versions (`v1.2` vs `v1.3`). If RCA accuracy drops after a prompt update, use historical trajectory traces to pinpoint where the reasoning degraded.

**3. Sandbox Runtime & Infrastructure Telemetry**
Since the agent generates and executes dynamic code, monitor the MicroVM execution layer:

* **Resource Limits:** Export container/microVM CPU and memory usage to Prometheus to detect if an agent-written script enters an infinite loop or consumes excessive memory.
* **Sanitized Logs:** Capture all `stdout` and `stderr` generated inside the sandbox, passing them through a PII and token scrubbing filter before storing them in your central logging system.

**4. Immutable Audit & Compliance Logging**
In SRE environments, auditors require non-repudiable logs of actions taken on production infrastructure.

* **Audit Payload:** Whenever the agent executes a write action or drafts a PR, generate a structured audit record containing: `timestamp`, `user_id`, `impersonated_role`, `trace_id`, `target_cluster`, `action_taken`, and `human_approver_id`.
* **WORM Storage:** Stream these events directly to write-once-read-many (WORM) storage (such as AWS S3 Glacier or an append-only Elasticsearch index) to ensure compliance with SOC2 and ISO27001 standards.
