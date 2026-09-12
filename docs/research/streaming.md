# Q: How the streaming should be handled

## A: 

Streaming here has two layers: how the agent produces output as it works, and how each surface delivers that output to a person. Design those separately — one internal event model, then a thin adapter per surface — rather than building three bespoke streaming implementations.

1. Internal event stream (surface-agnostic)

Model the agent run as a stream of typed events, not just text tokens — for an SRE agent the "thinking out loud" matters as much as the final answer:

token — text delta
tool_call_start / tool_call_result — e.g. "querying Prometheus...", "found 3 matching alerts"
status — progress/state changes for long investigations
action_proposed / action_confirmed — for anything destructive, tied back to the authz step-up we talked about
error, done

Give each run a run_id and each event a monotonic event_id, and persist the stream to a durable log (Redis stream, Kafka, or even a Postgres table) as it's produced. That's what makes reconnect, replay, and multi-viewer fan-out possible — e.g. someone opens the same investigation in the web UI and in Grafana at once.

2. Per-surface adapters

Custom frontend: SSE is usually the right default — simpler than WebSockets, built-in reconnect via EventSource, and you can resume mid-stream using Last-Event-ID. Use a WebSocket only if you need the client to send things back mid-run (cancel, interrupt, follow-up).
Grafana app plugin: don't try to route tokens through the request/response cycle — use Grafana Live. Implement the backend plugin's StreamHandler (SubscribeStream / RunStream / PublishStream) and push events to a channel scoped to org + user; the frontend subscribes over Grafana's existing WebSocket infra. This also means you inherit Grafana's own auth/authz for who can subscribe to what.
Slack: this changed recently and is worth knowing — Slack shipped a native streaming API in 2026 (chat.startStream / chat.appendStream / chat.stopStream), which lets you append just the new text instead of re-sending the whole message body on every update, with much looser rate limits than the old approach. Before this, the standard pattern was: post a placeholder message, then edit it via chat.update on a timer (roughly 1 update/sec, since chat.update is rate-limited per channel and needs the full message resent each time). If your Slack SDK is recent, prefer the streaming methods and fall back to chat.update batching only if the stream expires server-side or you're on an older SDK. Either way, batch/throttle — don't try to emit every token as its own Slack API call.
Direct API consumers: expose the same run as an SSE endpoint (GET /runs/{id}/stream), mirroring the shape people already expect from LLM provider APIs. This lets the custom frontend, Grafana backend, and any third party client all consume one contract.

3. Reliability concerns specific to an ops tool

Reconnect/resume: browser refresh, Grafana panel reload, or a flaky Slack socket shouldn't lose the run — replay from the durable log using the last seen event_id.
Keep-alives: SSE/long-lived connections get killed by idle load balancers and corporate proxies; send periodic comment/ping frames.
Backpressure: don't stream raw tool output verbatim (a log dump or full metric series) — stream summarized/truncated deltas and let the client fetch full detail on demand.
Idempotency: this is the one that actually matters for an SRE agent — if a stream reconnects or retries mid-action, make sure "restart the pod" doesn't fire twice. Actions should be keyed by an idempotency token tied to the run, not re-triggered by transport-layer retries.
Authorization at the stream level: each stream/channel subscription should be checked against the canonical identity, the same way as any other request — a Grafana Live channel or Slack thread shouldn't leak another user's or tenant's investigation.

If useful, I can sketch the run lifecycle (client → run created → event log → fan-out to SSE/Grafana Live/Slack) as a diagram.
