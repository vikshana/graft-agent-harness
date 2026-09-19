# DBOS Conductor commercial and capability evidence

> **Evidence date:** 2026-09-19
>
> **Scope:** public-source commercial and capability evidence only. This record
> is not a purchase recommendation, quote, trial result, or implementation
> decision.

## 1. Executive evidence summary

The official DBOS pricing page publicly lists **DBOS Pro at USD 99/month** and
**DBOS Teams at USD 499/month**. It describes **DBOS Enterprise as custom
pricing** and lists self-hosted Conductor as an Enterprise option, but gives no
public Enterprise amount. The page also advertises a free-trial call to action;
no trial was started, no trial key was obtained, and no trial terms are claimed
here.

The official self-hosting documentation states that self-hosted Conductor is
proprietary, that commercial or production use requires a paid licence key,
and that production licensing requires contact with sales. No self-hosted
production price, minimum commitment, usage schedule, or signed vendor quote
was found in the public material checked on the evidence date.

The documented capability is distributed workflow recovery and operational
management: executor health detection, recovery onto a compatible executor,
workflow and queue visibility, workflow operations, retention, version
management, autoscaling integration, and metrics. The documented mechanism is
an application connection to Conductor over a long-lived WebSocket. Conductor
is documented as out-of-band from workflow execution.

**This record makes no claim that Conductor fences external effects.** The
documentation itself describes the possibility of a live but silent or
otherwise mis-observed executor, and the DBOS execution model is at-least-once
for steps. Checkpoint or workflow-outcome convergence does not undo an external
effect that happened before the competing execution was rejected. A durable
idempotency key at the receiving boundary, or operator escalation for an
effect that cannot provide it, remains required for the Phase 1 recovery model.

## 2. Public commercial evidence

The amounts below are transcribed from the public pricing page checked on
2026-09-19. They are list-page observations, not a quote and not a promise of
availability, eligibility, tax treatment, or contractual terms.

| Public plan | Public price observed | Publicly described allowance or capability | Not established by the page |
|---|---:|---|---|
| DBOS Pro | **USD 99/month** | 2 user seats; up to 3 DBOS applications; 1 million included checkpoints per month; extra checkpoints shown as USD 50 per million; real-time workflow console; monitoring and tracing; distributed recovery; versioning and forking; bring-your-own database; unlimited throughput and concurrency; unlimited connected workers; community support | Whether the listed plan is suitable for production self-hosted Conductor; taxes; annual or committed pricing; definitions of every limit; support response commitment; self-hosted licence scope |
| DBOS Teams | **USD 499/month** | 10 user seats; 10 DBOS applications; 10 million included checkpoints per month; extra checkpoints shown as USD 40 per million; quantity discounts for extra checkpoints; everything in Pro; custom alerting; role-based access control; OpenMetrics; metadata-only mode; SOC2 and HIPAA; dedicated Slack support; priority email support; 2-day response SLAs; application architecture assistance | Whether the hosted plan includes every required production recovery feature for this use case; meaning and limits of connected workers, applications, and usage; contract, support, data-region, and retention terms |
| DBOS Enterprise | **Custom pricing** | Everything in Teams; SSO/SAML; quantity discounts for large organisations; option to self-host Conductor; air-gapped environments; custom security questionnaires; same-day response SLAs; technical onboarding; technical account management | All monetary terms; minimum spend or term; self-hosted Conductor licence limits; air-gap mechanics; support and maintenance pricing; service levels and contractual remedies |

The pricing page labels the offering as support, tooling, and hosting options
for open-source DBOS Transact applications. Its public feature list is not a
substitute for a commercial order form. In particular, the page does not
state that a listed monthly price includes self-hosted production licence
rights, Conductor infrastructure, PostgreSQL, reverse proxy, Console hosting,
or vendor-operated incident response.

### 2.1 Self-hosted and Enterprise pricing unknowns

The following remain **unknown**, not estimates:

| Unknown requiring vendor confirmation | Why it matters |
|---|---|
| Enterprise base price, currency, billing period, minimum annual commitment, renewal, and termination terms | Establishes the commercial baseline rather than assuming that the public Teams price extends to Enterprise |
| Production self-hosted Conductor licence price and metric | Determines whether the price is per organisation, application, environment, Conductor instance, executor, user, checkpoint, or another unit |
| Whether self-hosted Conductor is available under Pro or Teams, or only as an Enterprise option | Prevents treating the public plan prices as self-hosted production prices |
| Number of applications, environments, executors, Conductor replicas, user seats, and checkpoints covered by a self-hosted licence | The documentation says a free licence permits at most one executor per application; paid limits are not public here |
| Development, test, staging, disaster-recovery, and production licence treatment | Prevents an evaluation key or non-production entitlement being treated as a production right |
| Air-gapped or offline licence validation, renewal, grace period, and emergency extension | The Kubernetes guide says Conductor validates the licence against `https://cloud.dbos.dev` at startup, while the pricing page lists air-gapped environments as an Enterprise feature; the operational and contractual resolution is unknown |
| Paid licence duration, key rotation, revocation, and version upgrade rights | Required for secret management, continuity, and release planning |
| Managed Conductor versus self-hosted Conductor feature parity | A self-hosted deployment may have different identity, organisation, audit, retention, alerting, metrics, or support behaviour |
| PostgreSQL, Console, ingress, WebSocket load-balancer, observability, and support costs | These costs are outside the public Conductor list prices unless the vendor confirms otherwise |
| Commercial support boundaries, escalation path, response measurement, and service credits | The public plan names response SLAs but does not establish all service terms needed for production reliance |

## 3. Conductor key and configuration requirements

The public documentation describes two credentials and two connection contexts:

1. A **Conductor licence key** authorises the self-hosted Conductor service
   for development/evaluation or production according to the applicable
   agreement.
2. An **application API key** lets a registered DBOS application connect to
   Conductor. The documentation says the secret is printed once when created
   and cannot subsequently be retrieved.

### 3.1 Application-side configuration

The application must have the normal DBOS settings plus Conductor connection
settings. The documented Python shape is equivalent to:

```python
config = {
    "name": "<registered-application-name>",
    "application_version": "<compatible-release-revision>",
    "system_database_url": "<DBOS-system-database-url>",
    "conductor_key": "<application-API-key>",
    "conductor_url": "<Conductor-WebSocket-URL>",
}
```

Operational requirements recorded from the official documentation:

- Register the application in the relevant DBOS Console and make its name
  exactly match the DBOS application `name`.
- Create an application API key and deliver it as a secret. Do not rely on a
  later retrieval of the key secret.
- For managed Conductor, use the managed endpoint and the application API
  key. For self-hosted Conductor, use the self-hosted Console to register the
  application and generate the key; do not mix managed and self-hosted
  Console credentials.
- The application-side `DBOS_CONDUCTOR_URL` is a full WebSocket URL, such as
  `wss://<host>/conductor-api` behind an ingress or `ws://<host>:8090/` in the
  documented local example. This is distinct from the Console container's
  `DBOS_CONDUCTOR_URL`, which is documented as a bare `host:port` value.
- The application and all executors must use a compatible application version
  for recovery. The project must not substitute a mutable image tag or Git
  SHA for its released compatibility revision.
- The application API key is not a replacement for the project capability
  token, Tool Gateway, MCP, audit, tenant-isolation, or customer-system
  authorisation controls.

### 3.2 Self-hosted service configuration

The self-hosting documentation records the following requirements:

| Component | Required or documented configuration |
|---|---|
| Conductor service | `DBOS__CONDUCTOR_DB_URL` pointing to a PostgreSQL database used for Conductor's own internal state; `DBOS_CONDUCTOR_LICENSE_KEY`; port 8090 by default |
| DBOS Console | `DBOS_CONDUCTOR_URL` pointing at the Conductor service using the Console's documented host-and-port form; port 8080 in the container, commonly published through a reverse proxy |
| DBOS applications | `DBOS_CONDUCTOR_KEY` for the application API key and `DBOS_CONDUCTOR_URL` for the full WebSocket URL |
| Multiple Conductor instances | Shared Conductor PostgreSQL state; a routable, per-instance `DBOS__ADVERTISE_ADDRESS`; peer-to-peer reachability in addition to load-balancer reachability |
| Production ingress | TLS termination, WebSocket support, suitable idle timeouts, and routing to the Conductor and Console services |
| Authentication | OAuth/OIDC is strongly required before exposing a self-hosted deployment to an untrusted network. The documentation warns that without OAuth, API requests have built-in local-admin behaviour and API keys are not verified on incoming WebSocket connections |
| Licence validation | The Kubernetes guide states that the licence is validated against `https://cloud.dbos.dev` at startup and the service exits if it cannot reach that endpoint |
| Secret handling | PostgreSQL credentials, the Conductor licence key, and the application API key should be stored as deployment secrets with least-privilege access |

The Conductor PostgreSQL database is documented as separate internal state; it
is not the DBOS application system database and Conductor does not need direct
access to the application database. This is a documented architecture claim,
not a completed data-flow or security review for this project.

## 4. Recovery and capability scope

### 4.1 Documented capability claims

| Capability | Evidence classification and boundary |
|---|---|
| Detect interrupted or unhealthy executors in a distributed deployment | **Vendor-documented capability.** The public docs describe Conductor detecting executor failure through the application connection and directing compatible live executors to recover work. Detection is not proof that a process is dead. |
| Recover workflows onto another compatible executor | **Vendor-documented capability.** Recovery is constrained by compatible application version and DBOS checkpoint state. The public docs recommend Conductor for distributed production recovery. |
| Workflow and queue dashboards, management, retention, alerts, metrics, and observability integrations | **Vendor-documented capability.** Exact plan entitlement, limits, retention, data location, and API availability require commercial confirmation. |
| Version management, autoscaling integration, old-version draining, and compatible-worker selection | **Vendor-documented capability.** The operational drain and rollback behaviour still needs an environment-specific test for this project. |
| Data path | **Vendor-documented architecture claim.** Applications maintain outbound WebSocket connections; Conductor is described as out-of-band and not directly connected to the application database. Contractual data processing terms remain unknown. |
| Operation while the Conductor connection is interrupted | **Vendor-documented claim.** The docs say the application continues operating and failed workflows are recovered when the connection is restored. Required outage and reconnection behaviour remains to be tested against the selected version and topology. |

The DBOS FAQ states that Conductor is required for correct workflow recovery in
applications using more than one process and recommends it for production. This
is retained as the vendor's position; it does not override the repository's
evidence gates or establish that the commercial product satisfies every Phase 1
control.

### 4.2 Recovery boundary and non-claims

The official concurrent-execution material acknowledges that a zombie
executor can still be running during a mistaken recovery observation. It gives
steps at-least-once semantics and describes checkpoint and workflow-outcome
invariants, not rollback of an already completed external action.

The retained local Gate 0.3 matrix is consistent with that boundary: its
synthetic receiver observed two raw calls for one stable Run/step key in the
post-effect race while applying one keyed effect. The matrix used public DBOS
APIs and did not use Conductor, so it is **not** a Conductor test. It is retained
only to prevent an unsafe inference from vendor recovery or checkpoint
language. See [`recovery-race.json`](../gate-0.3/recovery-race.json) and the
[Gate 0.3 evidence README](../gate-0.3/README.md).

Accordingly, this record explicitly does **not** claim that Conductor:

- fences a live, silent, partitioned, or falsely declared-dead executor;
- prevents a stale executor from completing an external HTTP, MCP, database,
  queue, notification, or customer-system action;
- provides exactly-once external execution;
- makes a non-idempotent external effect automatically recoverable;
- replaces receiving-boundary idempotency, an idempotency key derived from the
  Run and durable step identity, or operator escalation; or
- satisfies the project's Tool Gateway, MCP, audit, tenant-isolation, or
  approval controls merely by being connected.

No commercial feature, licence tier, support SLA, or vendor statement may be
scored as an external-effect fence without separate evidence that proves that
property. The required default remains at-least-once execution with durable
receiving-boundary idempotency for automatically recoverable effects.

## 5. Complete vendor quote and question checklist

This is a request checklist, not evidence that any question has been answered.
No quote, order form, trial entitlement, or vendor response is held in this
repository as of the evidence date.

### 5.1 Commercial quote and entitlement

- [ ] Provide a written quote for the required shape: managed Conductor,
  self-hosted Conductor, or both; DBOS Pro, Teams, and Enterprise alternatives;
  production, staging, development, and disaster-recovery environments.
- [ ] State currency, billing period, annual versus monthly price, term,
  renewal, cancellation, payment terms, taxes, and any minimum commitment.
- [ ] State the exact unit and price for user seats, DBOS applications,
  organisations, environments, executors, connected workers, Conductor
  replicas, checkpoints, retention, and any other billable metric.
- [ ] Confirm that the public USD 99/month Pro and USD 499/month Teams prices
  are current, identify their effective date, and state whether they are
  available to this project and geography.
- [ ] Confirm the included Pro allowance of 2 seats, 3 applications, and 1
  million checkpoints per month; confirm the displayed USD 50 per million
  extra-checkpoint amount and its overage treatment.
- [ ] Confirm the included Teams allowance of 10 seats, 10 applications, and
  10 million checkpoints per month; confirm the displayed USD 40 per million
  extra-checkpoint amount, quantity discounts, and overage treatment.
- [ ] Define a checkpoint precisely: workflow, step, transaction, retry,
  replay, fork, queue, schedule, and failed execution counting rules.
- [ ] State whether over-limit use is throttled, suspended, billed, or merely
  reported, and provide notification and grace behaviour.
- [ ] State whether “unlimited throughput and concurrency” and “unlimited
  connected workers” have technical, fair-use, application, or support limits.
- [ ] List every Enterprise feature and entitlement included in the quote,
  including self-hosted Conductor, air-gapped operation, SSO/SAML, security
  questionnaires, support, onboarding, and account management.
- [ ] State whether the quote includes the Console, Conductor images, updates,
  maintenance, security fixes, support, training, and incident assistance.
- [ ] Supply the MSA, order form, DPA, subprocessor list, SLA, support policy,
  licence agreement, acceptable-use terms, and data-deletion/termination
  terms for review.
- [ ] State service credits, liability, indemnity, audit rights, breach
  notice, export controls, governing law, and termination assistance.

### 5.2 Self-hosted Conductor licence

- [ ] State the production licence price and all pricing dimensions.
- [ ] State whether one licence covers multiple Conductor replicas, DBOS
  applications, environments, regions, and disaster-recovery installations.
- [ ] State the permitted executor count per application and whether the limit
  is simultaneous, registered, or active over a billing period.
- [ ] State whether a development key, trial key, or free key is limited to one
  executor per application, its duration, and its permitted environments.
- [ ] State the exact difference between a development/evaluation key and a
  production key. Do not substitute an evaluation key for a production quote.
- [ ] Explain licence issuance, activation, expiry, rotation, revocation,
  emergency replacement, grace periods, clock skew, and renewal failure.
- [ ] Resolve whether production self-hosted Conductor can operate in an
  air-gapped environment when the public Kubernetes guide says the service
  validates the licence against `cloud.dbos.dev` at startup.
- [ ] If offline or proxy validation is supported, document the protocol,
  endpoints, cached entitlement, renewal cadence, and failure mode.
- [ ] State whether the licence is bound to a Conductor version, container
  image, cluster, hostname, organisation, or another identity.
- [ ] State image registry access, image retention, release cadence, support
  lifetime, upgrade path, rollback support, SBOM, provenance, and CVE response.
- [ ] Confirm whether Conductor and Console may be run without DBOS-managed
  cloud accounts and what telemetry or outbound connections remain mandatory.

### 5.3 Configuration, identity, and security

- [ ] Confirm the supported Python DBOS version and exact configuration field
  names for `conductor_key`, `conductor_url`, `name`, and
  `application_version`.
- [ ] Confirm WebSocket URL formats, TLS requirements, certificate validation,
  proxy requirements, keepalive behaviour, idle timeout guidance, and retry
  behaviour.
- [ ] Confirm API-key scopes, application binding, creation, one-time secret
  display, rotation, revocation, audit, and least-privilege roles.
- [ ] Confirm whether OIDC is required for self-hosted production and list
  supported claims, audiences, scopes, groups, logout, and key rotation.
- [ ] Explain the security consequences and supported use of self-hosted
  no-auth mode; confirm that it is not an acceptable production configuration
  for an exposed service.
- [ ] Confirm Conductor's required PostgreSQL version, extensions, sizing,
  migration process, connection pool, backup, restore, encryption, RLS
  interaction, and HA topology.
- [ ] Confirm the separation between the Conductor database and each DBOS
  application system database, including all data written to each.
- [ ] List all outbound endpoints, DNS requirements, proxy support, and
  required egress from a private cluster.
- [ ] Provide retention, deletion, export, residency, encryption, access-log,
  audit-log, and incident-response details for managed and self-hosted modes.
- [ ] Provide current SOC 2, HIPAA, GDPR, DPA, subprocessor, and penetration
  testing evidence applicable to the selected mode; distinguish public
  marketing statements from contractual commitments.

### 5.4 Recovery and safety questions

- [ ] Specify executor health signals, heartbeat or WebSocket timeouts, grace
  periods, detection states, and all configurable thresholds.
- [ ] Describe behaviour for crash, SIGSTOP, process hang, alive-but-silent
  executor, one-way network partition, system-database partition, Conductor
  outage, and reconnect races.
- [ ] State whether Conductor can ever direct recovery while the original
  executor remains live, and what guarantee exists in that case.
- [ ] State explicitly whether any product component fences external
  execution, and define “fence” as preventing a stale executor from reaching
  the external receiving boundary. A checkpoint conflict is not an answer to
  this question.
- [ ] State the documented and observed semantics for duplicate LLM calls,
  tool calls, HTTP calls, MCP calls, database writes, queue messages,
  notifications, and customer-system mutations.
- [ ] State whether Conductor supplies, propagates, or enforces an idempotency
  key for every step and external effect. If not, state the required receiving
  boundary contract and operator procedure.
- [ ] State how `PENDING`, `ENQUEUED`, and `DELAYED` work is found, alerted,
  drained, retried, and recovered across application-version changes.
- [ ] State how version-compatible recovery is selected, what happens when no
  matching executor is live, and how an orphaned release cohort is surfaced.
- [ ] State the rollback procedure and whether rollback is a reverse drain
  with measurable completion criteria.
- [ ] State how concurrent recovery attempts, reaper crashes, repeated resume
  requests, and both-handle result convergence behave.
- [ ] State dead-letter, retry-exhaustion, cancellation, operator override,
  audit, and incident escalation behaviour.
- [ ] Provide a supported-API, version-pinned reproduction of the full
  recovery barrier matrix, including pre-effect, post-effect/pre-checkpoint,
  post-final-step/pre-outcome, and system-database network-cut cases.
- [ ] Provide results for duplicate external-effect tests at the receiving
  boundary. Do not provide only a workflow checkpoint or terminal-status test.

### 5.5 Evaluation or trial, if separately offered

- [ ] If DBOS offers an evaluation key, state its issuer, duration, limits,
  executor cap, feature scope, data handling, and expiry behaviour.
- [ ] Confirm whether a trial requires a payment method, sales approval, or a
  licence agreement.
- [ ] Confirm whether a trial may be used in a disposable non-production
  environment only and whether it can test multiple executors, failover,
  version drains, and the required safety matrix.
- [ ] Record the trial only after the key is actually issued and the exact
  terms are retained. This evidence record does not claim that any trial was
  requested, issued, or run.

## 6. Required comparison decision criteria

No option is selected by this record. Before comparing a Conductor quote with
open-source DBOS plus the project-owned recovery controls, or with a Temporal
fallback, score every option against the same criteria and retain the evidence
for each score.

| Criterion | Required decision evidence | Minimum decision rule |
|---|---|---|
| External-effect safety | Reproduced duplicate-effect tests at the receiving boundary, stable key derivation, receiver durability, and classification of every non-idempotent effect | No option passes by claiming checkpoint convergence or executor detection alone. Effects without durable idempotency remain operator-escalation-only. |
| Recovery correctness | Crash, SIGSTOP, alive-but-silent, one-way partition, system-database partition, concurrent recovery, reaper crash, and both-handle outcomes | Must show no unsafe terminal overwrite, matching outcome convergence, and an explicit residual duplicate boundary. |
| Version and drain safety | Explicit released compatibility revision; matching-version recovery; `PENDING`, `ENQUEUED`, and `DELAYED` drain; orphan alert; forward and reverse rollback drain | No release cohort is retired until measurable drain completion. An automatic hash or image tag alone is insufficient. |
| Supported API and evidence quality | Current pinned DBOS/Python versions, public APIs, reproducible commands, raw redacted output, and no private system-table mutation | Private or undocumented behaviour is a risk requiring explicit approval and version pinning, not a pass. |
| Architecture and trust boundary | Data flow, outbound-only or inbound connections, key isolation, OIDC, audit, least privilege, customer-system path, and compatibility with Tool Gateway/MCP controls | Conductor cannot bypass the project authority boundary and cannot be credited for controls it does not enforce. |
| Availability and failure mode | Conductor outage, licence validation outage, PostgreSQL outage, network recovery, multi-replica behaviour, RTO/RPO, and operational alerts | Out-of-band management must not introduce an unrecognised customer-system or workflow safety dependency. |
| Operational burden | Deployment components, database, ingress, WebSockets, egress, secrets, upgrades, backups, monitoring, on-call, and recovery runbooks | Compare the complete operating surface, not only the subscription price or reaper line count. |
| Commercial total cost | Bound quote, licence metric, seats, checkpoints, overages, environments, infrastructure, support, renewal, and exit costs | Unknown commercial fields remain open risks; do not fill them with assumptions or list-price extrapolation. |
| Security and compliance | Contractual DPA, residency, retention, deletion, SSO, audit, SOC 2/HIPAA evidence, air-gap operation, and vulnerability response | Required controls must be contractually or technically evidenced for the selected deployment mode. |
| Performance and scale | Measured checkpoint rate, queue latency, executor count, Conductor capacity, PostgreSQL load, blue/green double peak, and rate limits | Use this project's measured workload and recovery matrix rather than vendor benchmark claims alone. |
| Supportability and lifecycle | SLA definitions, escalation, version support, release cadence, image provenance, CVE response, and licence renewal process | The selected option must have an operable support and upgrade path for the required lifetime. |
| Reversibility and lock-in | Export/API coverage, retained application state, replacement of Conductor functions, migration effort, and termination assistance | A future exit must not require unsafe replay or loss of audit and recovery history. |

### 6.1 Decision gates

1. **Commercial gate:** do not compare a public list price with a self-hosted
   production option until the missing licence metric, entitlement, support,
   and infrastructure terms are answered in a written quote.
2. **Safety gate:** do not treat Conductor as a fix for zombie risk. The
   selected architecture must still pass the project's at-least-once,
   receiving-boundary-idempotency and operator-escalation rules.
3. **Recovery gate:** require the full supported-API recovery and version-drain
   matrix, not a dashboard demonstration or a single crash test.
4. **Security gate:** require the self-hosted authentication, key, licence
   validation, egress, PostgreSQL, data-flow, and audit answers before any
   production claim.
5. **Evidence gate:** label every result as vendor-documented, locally
   observed, independently reproduced, or unknown. Unknowns remain unknown.

## 7. Official sources checked

All URLs in this table are official DBOS sources checked on **2026-09-19**.
The date records when this evidence was checked; it is not a guarantee that
the pages or prices remain unchanged.

| Source | Evidence used |
|---|---|
| [DBOS Pricing](https://www.dbos.dev/dbos-pricing) | Public Pro and Teams monthly prices, allowances, Enterprise custom-pricing wording, self-hosted option, public feature and support lists, and the public free-trial call to action |
| [Self-hosting Conductor](https://docs.dbos.dev/production/hosting-conductor) | Proprietary licence, development/evaluation key, production licence agreement and sales contact, licence environment variable, separate Conductor PostgreSQL database, application URL/key configuration, Console, WebSocket connection, high availability, security, and licence validation requirements |
| [Self-hosting Conductor with Kubernetes](https://docs.dbos.dev/production/hosting-conductor-with-kubernetes) | Required service variables, PostgreSQL, licence and API secrets, ingress/WebSocket requirements, OAuth warning, `DBOS__ADVERTISE_ADDRESS`, and startup validation against `cloud.dbos.dev` |
| [DBOS Workflow Recovery](https://docs.dbos.dev/production/workflow-recovery) | Recovery sequence, executor coordination, compatible application versions, manual versus Conductor recovery, and receiving-step idempotency requirement |
| [DBOS Concurrent Executions](https://docs.dbos.dev/explanations/concurrent-executions) | Zombie-executor possibility, at-least-once step execution, and workflow/checkpoint convergence boundary |
| [DBOS Production Conductor](https://docs.dbos.dev/production/conductor) | Conductor management, registration, connection, workflow and queue operations, and operational scope |
| [DBOS Conductor licence](https://www.dbos.dev/conductor-license) | Official licence reference linked by the self-hosting documentation; terms were not reproduced or interpreted here beyond the documented proprietary/licence-keyed status |
| [DBOS contact](https://www.dbos.dev/contact) | Official sales route named by the self-hosting documentation; no contact, quote, or response is claimed |

## 8. Evidence status

- **Known:** public Pro and Teams list prices and the public Enterprise
  custom-pricing description as displayed on 2026-09-19.
- **Known:** official documentation requires a paid production self-hosted
  Conductor licence and documents the key/configuration shape.
- **Known:** official documentation describes distributed recovery,
  compatible-version recovery, operational management, and an out-of-band
  Conductor connection.
- **Not claimed:** any quote, purchase, trial, trial key, vendor response,
  production entitlement, external-effect fence, exactly-once external
  execution, or completed Conductor deployment.
- **Open:** every item in the commercial, self-hosting, security, recovery,
  and comparison checklists that has not been answered by a dated vendor
  response or independent reproduction.
