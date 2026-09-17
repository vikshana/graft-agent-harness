# Decision index

> **Generated — do not edit by hand.** Run `python3 scripts/gen_adr_index.py` after adding or changing an ADR.
>
> Conventions: [`README.md`](./README.md). Vocabulary: [`../GLOSSARY.md`](../GLOSSARY.md), which wins on conflict.


**73 decisions · 72 accepted · 1 superseded/other**


---

## Start here — the core reading path

The decisions that constrain everything else, in dependency order. Roughly one sitting; the rest are consulted on demand.

1. [ADR-0021 — The platform owns and operates the Grafana instance](platform/0021-the-platform-owns-and-operates-the-grafana-instance.md)
2. [ADR-0051 — The scope model collapses to a single graft_tenant_id](tenancy/0051-the-scope-model-collapses-to-a-single-graft-tenant-id.md)
3. [ADR-0052 — A normative glossary owns the ubiquitous language](conventions/0052-a-normative-glossary-owns-the-ubiquitous-language.md)
4. [ADR-0059 — Every identifier is prefixed with the system that owns it](conventions/0059-every-identifier-is-prefixed-with-the-system-that-owns-it.md)
5. [ADR-0002 — Trigger surfaces for v1 are the Grafana plugin and Slack](platform/0002-trigger-surfaces-for-v1-are-the-grafana-plugin-and-slack.md)
6. [ADR-0036 — Every agent interaction is the same run primitive](agent/0036-every-agent-interaction-is-the-same-run-primitive.md)
7. [ADR-0037 — The durable-execution engine is DBOS Transact](agent/0037-the-durable-execution-engine-is-dbos-transact.md)
8. [ADR-0039 — The run is the durable workflow](agent/0039-the-run-is-the-durable-workflow.md)
9. [ADR-0007 — The Tool Gateway is a separate service](tools/0007-the-tool-gateway-is-a-separate-service.md)
10. [ADR-0068 — Every customer system is reached via the Tool Gateway and MCP](tools/0068-every-customer-system-is-reached-via-the-tool-gateway-and-mcp.md)
11. [ADR-0063 — Tool authority is a five-layer narrowing lattice](tools/0063-tool-authority-is-a-five-layer-narrowing-lattice.md)
12. [ADR-0010 — The harness mints its own run-scoped capability token](identity/0010-the-harness-mints-its-own-run-scoped-capability-token.md)
13. [ADR-0013 — system_initiated runs are structurally read-only](identity/0013-system-initiated-runs-are-structurally-read-only.md)
14. [ADR-0014 — Approval is a re-authenticated human act that happens in Grafana](identity/0014-approval-is-a-re-authenticated-human-act-that-happens-in-grafana.md)
15. [ADR-0065 — Approval authority follows the driver](identity/0065-approval-authority-follows-the-driver.md)
16. [ADR-0015 — Audit records form an insert-only hash-chained DAG](observability/0015-audit-records-form-an-insert-only-hash-chained-dag.md)
17. [ADR-0049 — Two independent regional deployments](platform/0049-two-independent-regional-deployments.md)


---

## Platform

*Surfaces, Grafana ownership, regional deployment*

Mechanism: [`../design/durable-execution.md`](../design/durable-execution.md)

Mechanism: [`../design/platform-topology.md`](../design/platform-topology.md)

| ADR | Title | Status | Date | Links |
|---|---|---|---|---|
| [ADR-0001](platform/0001-grafana-integration-via-the-plugin-backend-proxy.md) | Grafana integration via the plugin backend proxy | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0002](platform/0002-trigger-surfaces-for-v1-are-the-grafana-plugin-and-slack.md) | Trigger surfaces for v1 are the Grafana plugin and Slack | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0021](platform/0021-the-platform-owns-and-operates-the-grafana-instance.md) | The platform owns and operates the Grafana instance | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0049](platform/0049-two-independent-regional-deployments.md) | Two independent regional deployments | 🟢 accepted | 2026-09-13 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0073](platform/0073-dbos-system-database-is-separate-and-pci-scoped.md) | DBOS system database is separate and PCI-scoped | 🟢 accepted | 2026-09-17 | amends [ADR-0025](observability/0025-compliance-regime-for-v1-is-pci-dss.md), [ADR-0041](agent/0041-step-granularity-is-one-llm-call-or-one-tool-call.md), [ADR-0048](agent/0048-a-thin-runtime-seam-isolates-the-durable-execution-engine.md), [ADR-0049](platform/0049-two-independent-regional-deployments.md), [ADR-0050](tenancy/0050-isolation-is-never-thread-level.md) |

---

## Agent

*Framework, run model, durable execution*

Mechanism: [`../design/durable-execution.md`](../design/durable-execution.md)

| ADR | Title | Status | Date | Links |
|---|---|---|---|---|
| [ADR-0003](agent/0003-agent-framework-is-langgraph-plus-deepagents.md) | Agent framework is LangGraph plus DeepAgents | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0036](agent/0036-every-agent-interaction-is-the-same-run-primitive.md) | Every agent interaction is the same run primitive | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0037](agent/0037-the-durable-execution-engine-is-dbos-transact.md) | The durable-execution engine is DBOS Transact | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0038](agent/0038-work-rediscovery-is-ours-to-build.md) | Work rediscovery is ours to build | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0039](agent/0039-the-run-is-the-durable-workflow.md) | The run is the durable workflow | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0040](agent/0040-langgraph-is-compiled-with-no-checkpointer.md) | LangGraph is compiled with no checkpointer | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0041](agent/0041-step-granularity-is-one-llm-call-or-one-tool-call.md) | Step granularity is one LLM call or one tool call | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0042](agent/0042-idempotency-is-three-layered.md) | Idempotency is three-layered | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0043](agent/0043-cancellation-is-effective-at-the-next-step-boundary.md) | Cancellation is effective at the next step boundary | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0045](agent/0045-signal-delivery-is-dbos-send-and-recv.md) | Signal delivery is DBOS send and recv | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends [ADR-0033](streaming/0033-the-back-channel-is-plain-rest.md); amended by  |
| [ADR-0046](agent/0046-deploy-strategy-is-blue-green-on-dbos-application-version.md) | Deploy strategy is blue/green on DBOS application version | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0047](agent/0047-all-five-durable-timer-use-cases-ship-in-v1.md) | All five durable-timer use cases ship in v1 | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends [ADR-0035](streaming/0035-unattended-run-notification-via-slack-summary-and-in-app-inbox.md); amended by  |
| [ADR-0048](agent/0048-a-thin-runtime-seam-isolates-the-durable-execution-engine.md) | A thin runtime seam isolates the durable-execution engine | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0062](agent/0062-custom-instructions-exist-at-tenant-and-principal-level.md) | Custom instructions exist at Tenant and Principal level | 🟢 accepted | 2026-09-13 | supersedes ; **superseded by** ; amends [ADR-0016](tenancy/0016-configuration-is-tenant-scoped-and-shared.md); amended by  |

---

## Tools

*Tool Gateway, MCP invariants, authority lattice*

Mechanism: [`../design/tool-registry-and-authority.md`](../design/tool-registry-and-authority.md)

| ADR | Title | Status | Date | Links |
|---|---|---|---|---|
| [ADR-0004](tools/0004-no-arbitrary-code-execution-in-v1.md) | No arbitrary code execution in v1 | 🟢 accepted | 2026-09-12 |  |
| [ADR-0007](tools/0007-the-tool-gateway-is-a-separate-service.md) | The Tool Gateway is a separate service | 🟢 accepted | 2026-09-12 |  |
| [ADR-0018](tools/0018-one-logical-grafana-mcp-service-with-two-credential-hops.md) | One logical grafana-mcp service with two credential hops | 🟢 accepted | 2026-09-12 |  |
| [ADR-0023](tools/0023-check-then-act-enforcement-is-performed-by-the-tool-gateway.md) | Check-then-act enforcement is performed by the Tool Gateway | 🟢 accepted | 2026-09-12 |  |
| [ADR-0027](tools/0027-use-the-mcp-sdk-oauthclientprovider-for-rfc-9728-discovery.md) | Use the MCP SDK OAuthClientProvider for RFC 9728 discovery | 🟢 accepted | 2026-09-12 |  |
| [ADR-0063](tools/0063-tool-authority-is-a-five-layer-narrowing-lattice.md) | Tool authority is a five-layer narrowing lattice | 🟢 accepted | 2026-09-13 |  |
| [ADR-0067](tools/0067-paging-and-on-call-writes-are-classified-v1-ships-read-only.md) | Paging and on-call writes are classified, v1 ships read only | 🟢 accepted | 2026-09-13 |  |
| [ADR-0068](tools/0068-every-customer-system-is-reached-via-the-tool-gateway-and-mcp.md) | Every customer system is reached via the Tool Gateway and MCP | 🟢 accepted | 2026-09-13 |  |
| [ADR-0069](tools/0069-token-service-tool-gateway-and-registry-ship-as-one-authority-service.md) | Token Service, Tool Gateway and Registry ship as one Authority Service | 🟢 accepted | 2026-09-13 |  |
| [ADR-0070](tools/0070-all-mcp-servers-are-streamable-http-never-stdio.md) | All MCP servers are streamable-HTTP, never stdio | 🟢 accepted | 2026-09-12 | amends [ADR-0007](tools/0007-the-tool-gateway-is-a-separate-service.md) |

---

## Identity

*Authn, federation, approval authority*

Mechanism: [`../design/external-identity-mapping.md`](../design/external-identity-mapping.md)

| ADR | Title | Status | Date | Links |
|---|---|---|---|---|
| [ADR-0009](identity/0009-grafana-identity-forwarding-via-x-grafana-id-is-the-primary-inbound-au.md) | Grafana identity forwarding via X-Grafana-Id is the primary inbound authn | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0010](identity/0010-the-harness-mints-its-own-run-scoped-capability-token.md) | The harness mints its own run-scoped capability token | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0011](identity/0011-downstream-credentials-are-hybrid-service-identity-by-default.md) | Downstream credentials are hybrid, service-identity by default | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0012](identity/0012-grafana-service-accounts-are-self-provisioned-imperatively.md) | Grafana service accounts are self-provisioned imperatively | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by [ADR-0022](identity/0022-grafana-service-accounts-are-provisioned-synchronously-at-tenant-creat.md) |
| [ADR-0013](identity/0013-system-initiated-runs-are-structurally-read-only.md) | system_initiated runs are structurally read-only | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0014](identity/0014-approval-is-a-re-authenticated-human-act-that-happens-in-grafana.md) | Approval is a re-authenticated human act that happens in Grafana | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0019](identity/0019-the-mcp-authorization-server-is-logically-distinct-from-the-tool-gatew.md) | The MCP Authorization Server is logically distinct from the Tool Gateway | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0020](identity/0020-slack-account-linking-uses-sign-in-with-slack-oidc.md) | Slack account linking uses Sign in with Slack (OIDC) | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0022](identity/0022-grafana-service-accounts-are-provisioned-synchronously-at-tenant-creat.md) | Grafana service accounts are provisioned synchronously at Tenant creation | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends [ADR-0012](identity/0012-grafana-service-accounts-are-self-provisioned-imperatively.md); amended by  |
| [ADR-0024](identity/0024-slack-and-system-initiated-runs-receive-no-per-user-grafana-check.md) | Slack and system_initiated runs receive no per-user Grafana check | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0026](identity/0026-enforcement-granularity-is-grafana-basic-roles.md) | Enforcement granularity is Grafana basic roles | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0028](identity/0028-canonical-slack-identity-is-keyed-by-slack-enterprise-id.md) | Canonical Slack identity is keyed by slack_enterprise_id | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by [ADR-0052](conventions/0052-a-normative-glossary-owns-the-ubiquitous-language.md) |
| [ADR-0060](identity/0060-external-references-are-modelled-in-three-layers.md) | External references are modelled in three layers | 🟢 accepted | 2026-09-13 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0061](identity/0061-identity-linking-is-mandatory-and-verified.md) | Identity linking is mandatory and verified | 🟢 accepted | 2026-09-13 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0065](identity/0065-approval-authority-follows-the-driver.md) | Approval authority follows the driver | 🟢 accepted | 2026-09-13 | supersedes [ADR-0055](tenancy/0055-approval-authority-is-initiator-only.md); **superseded by** ; amends ; amended by  |

---

## Tenancy

*Scoping, roles, budgets, lifecycle*

Mechanism: [`../design/tenancy-and-scoping.md`](../design/tenancy-and-scoping.md)

| ADR | Title | Status | Date | Links |
|---|---|---|---|---|
| [ADR-0016](tenancy/0016-configuration-is-tenant-scoped-and-shared.md) | Configuration is Tenant-scoped and shared | 🟢 accepted | 2026-09-12 | amended by [ADR-0062](agent/0062-custom-instructions-exist-at-tenant-and-principal-level.md) |
| [ADR-0017](tenancy/0017-limits-form-a-ceiling-chain.md) | Limits form a ceiling chain | 🟢 accepted | 2026-09-12 | amended by [ADR-0057](tenancy/0057-budget-ceilings-are-per-scope-with-distinct-at-cap-behaviour.md) |
| [ADR-0044](tenancy/0044-budget-enforcement-is-split-across-three-layers.md) | Budget enforcement is split across three layers | 🟢 accepted | 2026-09-12 |  |
| [ADR-0050](tenancy/0050-isolation-is-never-thread-level.md) | Isolation is never thread-level | 🟢 accepted | 2026-09-13 |  |
| [ADR-0051](tenancy/0051-the-scope-model-collapses-to-a-single-graft-tenant-id.md) | The scope model collapses to a single graft_tenant_id | 🟢 accepted | 2026-09-13 |  |
| [ADR-0053](tenancy/0053-tenant-lifecycle-is-discovered-provisioning-ready-suspended.md) | Tenant lifecycle is discovered, provisioning, ready, suspended | 🟢 accepted | 2026-09-13 |  |
| [ADR-0054](tenancy/0054-run-ownership-is-private-by-default-and-irreversibly-promotable.md) | Run ownership is private by default and irreversibly promotable | 🟢 accepted | 2026-09-13 |  |
| [ADR-0055](tenancy/0055-approval-authority-is-initiator-only.md) | ~~Approval authority is initiator-only~~ | ⚪ superseded | 2026-09-13 | **superseded by** [ADR-0065](identity/0065-approval-authority-follows-the-driver.md), [ADR-0066](streaming/0066-control-liveness-is-three-independent-server-side-clocks.md) |
| [ADR-0056](tenancy/0056-the-idp-authenticates-and-the-harness-authorizes.md) | The IdP authenticates and the harness authorises | 🟢 accepted | 2026-09-13 |  |
| [ADR-0057](tenancy/0057-budget-ceilings-are-per-scope-with-distinct-at-cap-behaviour.md) | Budget ceilings are per-scope with distinct at-cap behaviour | 🟢 accepted | 2026-09-13 | amends [ADR-0017](tenancy/0017-limits-form-a-ceiling-chain.md) |
| [ADR-0058](tenancy/0058-schedules-are-a-governed-tenant-scoped-resource.md) | Schedules are a governed Tenant-scoped resource | 🟢 accepted | 2026-09-13 |  |

---

## Streaming

*Event model, transport, control liveness*

Mechanism: [`../design/streaming-and-events.md`](../design/streaming-and-events.md)

| ADR | Title | Status | Date | Links |
|---|---|---|---|---|
| [ADR-0006](streaming/0006-streaming-is-decoupled-from-orchestration-via-a-durable-event-log.md) | Streaming is decoupled from orchestration via a durable event log | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0029](streaming/0029-the-event-model-is-our-own-internally-versioned.md) | The event model is our own, internally versioned | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0030](streaming/0030-the-durable-event-log-is-postgres-only-for-v1.md) | The durable event log is Postgres-only for v1 | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0031](streaming/0031-grafana-surface-streaming-uses-grafana-live.md) | Grafana surface streaming uses Grafana Live | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0032](streaming/0032-shared-runs-use-a-soft-lock-driver-model.md) | Shared runs use a soft-lock driver model | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0033](streaming/0033-the-back-channel-is-plain-rest.md) | The back-channel is plain REST | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by [ADR-0045](agent/0045-signal-delivery-is-dbos-send-and-recv.md) |
| [ADR-0034](streaming/0034-token-level-narrative-streaming-on-all-surfaces.md) | Token-level narrative streaming on all surfaces | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0035](streaming/0035-unattended-run-notification-via-slack-summary-and-in-app-inbox.md) | Unattended-run notification via Slack summary and in-app inbox | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by [ADR-0047](agent/0047-all-five-durable-timer-use-cases-ship-in-v1.md) |
| [ADR-0064](streaming/0064-shared-run-control-is-one-driver-with-explicit-handover.md) | Shared-run control is one driver with explicit handover | 🟢 accepted | 2026-09-13 | supersedes ; **superseded by** ; amends ; amended by [ADR-0065](identity/0065-approval-authority-follows-the-driver.md) |
| [ADR-0066](streaming/0066-control-liveness-is-three-independent-server-side-clocks.md) | Control liveness is three independent server-side clocks | 🟢 accepted | 2026-09-13 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0072](streaming/0072-run-list-filters-and-web-frontend-tenant-resolution.md) | Run list filters and web-frontend Tenant resolution | 🟢 accepted | 2026-09-13 | supersedes ; **superseded by** ; amends ; amended by  |

---

## Observability

*Telemetry, audit, compliance*

Mechanism: [`../design/audit-and-attribution.md`](../design/audit-and-attribution.md)

| ADR | Title | Status | Date | Links |
|---|---|---|---|---|
| [ADR-0005](observability/0005-observability-is-otel-native.md) | Observability is OTel-native | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0008](observability/0008-instrumentation-is-openlit-plus-hand-written-spans-over-otlp.md) | Instrumentation is OpenLIT plus hand-written spans over OTLP | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by [ADR-0071](observability/0071-two-telemetry-sinks-with-an-internal-only-eval-sink.md) |
| [ADR-0015](observability/0015-audit-records-form-an-insert-only-hash-chained-dag.md) | Audit records form an insert-only hash-chained DAG | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0025](observability/0025-compliance-regime-for-v1-is-pci-dss.md) | Compliance regime for v1 is PCI-DSS | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0071](observability/0071-two-telemetry-sinks-with-an-internal-only-eval-sink.md) | Two telemetry sinks with an internal-only eval sink | 🟢 accepted | 2026-09-12 | supersedes ; **superseded by** ; amends [ADR-0008](observability/0008-instrumentation-is-openlit-plus-hand-written-spans-over-otlp.md); amended by  |

---

## Conventions

*Cross-cutting normative rules*

Mechanism: [`../GLOSSARY.md`](../GLOSSARY.md)

| ADR | Title | Status | Date | Links |
|---|---|---|---|---|
| [ADR-0052](conventions/0052-a-normative-glossary-owns-the-ubiquitous-language.md) | A normative glossary owns the ubiquitous language | 🟢 accepted | 2026-09-13 | supersedes ; **superseded by** ; amends ; amended by  |
| [ADR-0059](conventions/0059-every-identifier-is-prefixed-with-the-system-that-owns-it.md) | Every identifier is prefixed with the system that owns it | 🟢 accepted | 2026-09-13 | supersedes ; **superseded by** ; amends ; amended by  |

