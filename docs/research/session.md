# Q:
Where the session history should be persisteted so users can come back it at a later time

## A:
For an agentic system built on LangGraph, session history should be persisted in a **PostgreSQL** database using LangGraph's native checkpointer architecture.

Postgres acts as the unified storage layer for both the exact state of the AI agent and the human-readable chat history. When a user returns to a session days later, the system reloads this state, allowing the agent to pick up exactly where it left off—even if it was paused waiting for a human PR approval.

Here is how the session persistence layer breaks down:

### 1. LangGraph State Checkpointer (Postgres)

Instead of manually saving chat messages, you configure LangGraph to use its native `AsyncPostgresSaver`.

* **How it works:** At every step of the RCA (after a user message, a tool execution, or an LLM thought), LangGraph automatically serializes the entire graph state—including the full array of conversation `messages`, current variables, and active hypotheses—and saves it to Postgres.
* **The Key:** Every session is assigned a unique UUID called a `thread_id`. When the user clicks an old chat in the UI, the FastAPI backend passes that `thread_id` back to LangGraph, which hydrates the state from Postgres instantly.

### 2. Session Metadata (Relational Tables)

Alongside the LangGraph checkpointer tables, you need standard relational tables in the same Postgres instance to populate the frontend's "Chat History" sidebar.

* **`Sessions` Table:** Maps `user_id` (from Keycloak) to `thread_id`, `incident_id`, `created_at`, and an LLM-generated `session_title` (e.g., *"RCA: Payment Gateway 502s"*).
* **Access Control:** When a user logs in, FastAPI queries this table to fetch their historical sessions, ensuring engineers can only resume sessions they own (or sessions shared explicitly within their RBAC group).

### 3. Read-Only Trajectories (Langfuse / ClickHouse)

If an incident is resolved and closed, the user doesn't need an *active* agent state—they just need to read what happened.

* Instead of keeping massive active states in Postgres forever, you can archive closed sessions.
* The frontend can fetch historical, read-only views directly from **Langfuse** (backed by ClickHouse or S3), displaying the exact chat transcript, the tool outputs, and the generated PR without tying up the LangGraph execution engine.

### Cloud & OSS Mapping

Since you are targeting GCP and AliCloud using OSS primitives:

* **Self-Hosted:** Deploy **CloudNativePG** (an open-source Kubernetes operator for Postgres) to run highly available Postgres clusters natively on GKE (GCP) and ACK (AliCloud).
* **Managed Options:** Use **Cloud SQL for PostgreSQL** (GCP) and **ApsaraDB RDS for PostgreSQL** (AliCloud). Both integrate natively with LangGraph's checkpointer libraries out of the box.
