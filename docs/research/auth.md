# Q: 
How does front end authentication with backend ang backend with execution and how does front end get the streaming response?

## A: 
Here is the end-to-end architecture for handling user authentication, secure credential propagation down to the execution sandbox, and real-time response streaming.

---

```
                       AUTHENTICATION & STREAMING PIPELINE

[ Frontend (UI) ]
       │
       │  1. Authenticate (OIDC PKCE)
       ▼
[ Keycloak / IDP ] ────(Returns JWT)────► [ Frontend ]
                                              │
    2. HTTP/SSE + JWT Bearer Header           │ 3. WebSocket / SSE Session
                                              ▼
                                     [ FastAPI Gateway ]
                                              │
                                              │ 4. Publish Event Jobs
                                              ▼
                                     [ Redis Pub/Sub ]
                                         ▲       │
                         5. Read Events  │       │ 6. Run Execution
                                         │       ▼
                                     [ LangGraph Worker ]
                                         │       │
                7. User Impersonation    │       │ 8. Ephemeral mTLS
                (K8s Impersonate-User)   │       │    SSH / gRPC
                                         ▼       ▼
                                     [ K8s / GitHub ]  [ Sandbox MicroVM ]

```

---

## 1. Front-End to Back-End Authentication

The frontend authenticates using the **OAuth 2.0 / OIDC Authorization Code Flow with PKCE** via Keycloak or your identity provider.

### The Token Lifecycle

1. **Login:** The user logs in on the frontend and receives a short-lived JWT **Access Token** (e.g., 15-minute expiry) and a secure `HttpOnly`, `SameSite=Strict` **Refresh Token cookie**.
2. **REST API Requests:** The frontend attaches the access token in the `Authorization: Bearer <JWT>` header for standard API calls.
3. **Gateway Verification:** The FastAPI Gateway validates the JWT's signature against the IDP’s Public Key (JWKS) and extracts user metadata (`user_id`, `email`, `roles`, `groups`).

### Authenticating Streaming Endpoints (SSE / WebSockets)

Browser-native APIs like `new EventSource(url)` **do not allow custom HTTP headers** (such as `Authorization: Bearer <JWT>`). You handle this using one of two patterns:

* **Pattern A: Fetch-based SSE (Recommended):** Use a client library like `@microsoft/fetch-event-source` instead of standard `EventSource`. This wraps the Stream using standard `fetch()`, allowing custom headers:
```typescript
fetchEventSource('/api/v1/incidents/rca/stream', {
  method: 'POST',
  headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
  body: JSON.stringify({ incident_id: 'INC-1042' }),
  onmessage(ev) { /* update UI */ }
});

```


* **Pattern B: Single-Use Ticket Exchange (WebSockets):** The frontend requests a short-lived ticket via a POST request (`POST /api/v1/auth/ws-ticket`), receiving a UUID that expires in 10 seconds. The frontend then connects via `wss://[api.example.com/ws?ticket=UUID](https://api.example.com/ws?ticket=UUID)`.

---

## 2. Back-End to Execution Environment Authentication

The agent must not run with blanket cluster-admin rights. It must use **User Impersonation** and **Isolated Session Credentials**.

```
[LangGraph Agent] ──(Payload + User Claims)──> [MCP Server] ──(Impersonate-User: alice)──> [K8s API]

```

### A. Target API Integration (K8s, GitHub, Jira)

When the agent invokes a tool (e.g., querying Kubernetes or opening a GitHub PR), it propagates the user’s identity:

* **Kubernetes (Native Impersonation):** The agent service account holds `impersonate` permissions on the API server. When executing `kubectl` or K8s API calls, it appends headers:
* `Impersonate-User: alice@company.com`
* `Impersonate-Group: sre-team`
* *Result:* Kubernetes evaluates RBAC rules against **Alice's permissions**, not the agent's. If Alice cannot delete pods in `prod`, the agent's tool call fails with `403 Forbidden`.


* **GitHub / Jira (On-Behalf-Of Tokens):** User OAuth tokens are stored in a secret manager (e.g., HashiCorp Vault) keyed by `user_id`. When the agent executes a GitHub action, it fetches Alice's short-lived GitHub User Access Token from Vault to create the PR under her name.

### B. Agent Worker to MicroVM Sandbox Communication

When the agent needs to execute Python scripts or complex Bash pipelines, it communicates with an isolated MicroVM (e.g., Daytona or E2B):

* **Ephemeral Credentials:** When a session starts, the API Gateway provisions a dedicated sandbox container/microVM for `thread_id`.
* **mTLS / Short-Lived SSH:** The worker generates a unique, in-memory SSH key pair or mTLS certificate for that specific sandbox.
* **Sandbox Isolation:** The sandbox runs as a non-root user (`sandboxuser`), has a read-only root filesystem except for `/tmp`, and has no external egress except to whitelist IP addresses for internal telemetry.

---

## 3. Real-Time Response Streaming to the Front-End

Because an RCA run takes 30–90 seconds and involves multiple agent steps, the system uses an **Event-Driven Pub/Sub architecture** to stream steps, thoughts, tool execution logs, and final responses back to the user.

```
[ LangGraph Node ] ──(Pushes Step Event)──► [ Redis Pub/Sub ]
                                                   │
[ Frontend UI ]    ◄──(Streams SSE Events)── [ FastAPI SSE Endpoint ]

```

### Step-by-Step Flow

1. **Task Execution:** The user triggers an RCA run. FastAPI creates a `thread_id` and dispatches the task to the LangGraph worker pool via a task queue (Temporal / Celery).
2. **Event Generation:** As the LangGraph agent executes nodes, it publishes granular JSON events to a **Redis Pub/Sub channel** (`channel:rca:{thread_id}`):
* `agent_thought`: Internal LLM reasoning step.
* `tool_start`: "Executing script `check_oom_events.py` in sandbox..."
* `tool_output`: Streamed output logs from the sandbox execution.
* `token_delta`: Streamed raw text tokens for the final user report.
* `hitl_required`: Execution paused; waiting for user PR approval.


3. **Gateway Forwarding:** The FastAPI SSE endpoint subscribes to `channel:rca:{thread_id}` in Redis and immediately forwards these chunks over the open HTTP connection as a Server-Sent Events stream.
4. **Frontend Rendering:** The React/Vue frontend parses event types to update UI components dynamically (e.g., showing a live terminal for `tool_output` and an interactive approval modal when receiving `hitl_required`).

### Standard SSE Event Format

```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

event: agent_thought
data: {"step": "topology_lookup", "message": "Querying Neo4j to check upstream dependencies of payment-service..."}

event: tool_start
data: {"tool": "k8s_get_logs", "params": {"pod": "payment-service-84f9", "namespace": "prod"}}

event: hitl_required
data: {"confidence": 0.92, "action": "create_github_pr", "payload": {"repo": "infra-live", "file": "helm/values.yaml"}}

```

---

## Summary of Responsibilities

| Boundary | Auth / Comm Mechanism | Security / Operational Focus |
| --- | --- | --- |
| **Frontend $\rightarrow$ Gateway** | OIDC JWT (Authorization Code + PKCE) over HTTPS/SSE | JWT signature validation, Role-Based Access Control (RBAC). |
| **Gateway $\rightarrow$ Redis / Queue** | Internal TLS / Auth Token | Asynchronous job dispatch, decoupling long-running agent tasks. |
| **Worker $\rightarrow$ Target Tools** | User Impersonation (`Impersonate-User` / Vault OAuth) | Enforces user-level permissions so agents cannot exceed user access. |
| **Worker $\rightarrow$ Sandbox** | Ephemeral mTLS / SSH Keys | Total execution isolation; prevents host system compromise. |
| **Worker $\rightarrow$ Frontend Stream** | Redis Pub/Sub $\rightarrow$ SSE (Server-Sent Events) | Non-blocking, low-latency live streaming of reasoning, logs, and tokens. |
