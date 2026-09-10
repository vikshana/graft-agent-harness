# Q:
Can you create a detail plan broken down in phases which I can hand over to the Coding agent to start implementing while insuring that the architecture doesn't diverge too much from the production grade design we discussed. And all the quality checks are in place.

## A:
## Phase 1: Foundation & Core Infrastructure

Establish the repository baseline, containerization, and foundational services.

* **Repository Structure:** Monorepo structure containing `/api` (FastAPI), `/worker` (LangGraph agents), `/sandbox` (execution templates), and `/infra` (Helm/Terraform).
* **Core Services Setup:** Docker Compose configuration for local dev mapping to Kubernetes (GKE/ACK) manifests. Include Postgres (state/checkpoints), Valkey/Redis (cache & pub/sub), and Keycloak (OIDC auth).
* **Model Routing:** Configure **LiteLLM** proxy container with fallback routing between local open-weights models (`vLLM` hosting Qwen 2.5 Coder) and commercial providers.
* **Quality Gate:** Automated CI pipeline verifying linting (Ruff), type checking (MyPy), and successful container boot health checks.

## Phase 2: FastAPI Gateway & Streaming Pipeline

Implement the stateless API layer, security boundary, and real-time event distribution.

* **Authentication Middleware:** FastAPI dependency verifying JWT access tokens against Keycloak JWKS. Extract user context (`user_id`, `groups`) for downstream impersonation.
* **Job Queue Integration:** Integrate **Temporal** or Celery to dispatch asynchronous tasks (Chat and RCA requests) from the API gateway to worker pods.
* **Real-Time SSE Endpoint:** Implement fetch-based Server-Sent Events (SSE) streaming connected to Redis Pub/Sub channels (`channel:rca:{thread_id}`) to push live status updates to the frontend.
* **Quality Gate:** Integration tests validating token rejection for invalid JWTs and successful SSE event streaming under concurrent client loads.

## Phase 3: LangGraph Core & MCP Tool Integration

Build the core agent reasoning loop and standardize external tool access.

* **State Machine Setup:** Initialize **LangGraph** workflows backed by Postgres checkpointing for state persistence and thread recovery.
* **MCP Server Clients:** Integrate official Model Context Protocol clients for Kubernetes (`mcp-server-kubernetes`), GitHub, and Jira.
* **Read-Through Cache:** Wrap K8s read tools (`get pods`, `describe`) in a Redis caching layer with a 5-second TTL to prevent control plane saturation during incident bursts.
* **Quality Gate:** Unit tests mocking MCP tool responses to verify LangGraph state transitions and checkpoint persistence across simulated worker crashes.

## Phase 4: Secure Sandboxing & Guardrails

Isolate code execution and implement defense-in-depth against prompt injection and runaway loops.

* **MicroVM Integration:** Implement the sandbox execution driver (Daytona or E2B interface) to spin up ephemeral, network-restricted containers for script execution.
* **Log Sanitization Pipeline:** Insert an intermediate guardrail model (e.g., Llama Guard or regex token scrubber) between sandbox outputs and the agent context window to block indirect prompt injection.
* **Circuit Breakers & Budgets:** Hard-code a maximum graph depth (e.g., 15 steps) and LiteLLM cost caps per job to terminate runaway agent loops automatically.
* **Quality Gate:** Security test suite injecting malicious log payloads (`Ignore previous instructions...`) to ensure the sanitization layer strips malicious instructions before reaching the LLM.

## Phase 5: RCA Loop, HITL & Observability

Deliver the automated root cause analysis engine, human-in-the-loop approvals, and full telemetry.

* **RCA Workflow Nodes:** Build the Triage, Evidence Gather, Topology check, and Hypothesis Engine nodes.
* **Confidence Threshold & Gatekeeper:** Implement the conditional edge: if hypothesis confidence is $\ge 80\%$, pause execution, generate a GitHub PR via Git MCP, and trigger a `hitl_required` event waiting for user approval.
* **OpenTelemetry & Langfuse:** Instrument all FastAPI routes, LangGraph steps, and LiteLLM calls with OpenTelemetry, exporting full agent trajectories to **Langfuse**.
* **Historical Replay Evals:** Deploy an evaluation harness running 10 historical incident scenarios to measure RCA accuracy against post-mortem ground truth before production promotion.
* **Quality Gate:** End-to-end integration test simulating an alert, verifying automated evidence gathering, successful HITL pause on PR generation, and clean telemetry traces in Langfuse.
