# Tenancy, Scoping & Authorization

> **Status: 🟢 Resolved for v1 (2026-09-13).** Locked as **D49–D58** in
> [`../adr/DECISION-REGISTER.md`](../adr/DECISION-REGISTER.md). Resolves
> [`../adr/open-questions/03-tenancy-and-scoping.md`](../adr/open-questions/03-tenancy-and-scoping.md)
> (C1–C5) and discharges **R3**, **R4** and risk **X6**.
>
> Vocabulary is normative per [`../GLOSSARY.md`](../GLOSSARY.md) (D52).

---

## 1. Deployment topology (C1′ — D49)

```
   ┌─────────────────── GCP deployment ───────────────────┐   ┌───── AliCloud deployment ─────┐
   │  Grafana (OSS, latest, shared, multi-org)  D21       │   │  Grafana (OSS, latest, …)     │
   │  Harness API · Tool Gateway · DBOS workers           │   │  Harness API · Tool Gateway   │
   │  Postgres (runs, events, audit, DBOS system DB)      │   │  Postgres                     │
   │  Object storage (artifacts, WORM audit anchors)      │   │  Object storage               │
   └──────────────────────────────────────────────────────┘   └───────────────────────────────┘
              │                                                          │
              └──────────► Tenant Directory (globally replicated) ◄───────┘
                           graft_tenant_id → home_region
                           METADATA ONLY. No run data, no events,
                           no audit records, no artifacts.
```

- **Two independent regional deployments.** Not one logical system. Each is
  shared-multi-tenant internally.
- **`graft_tenant_id` is globally unique across both regions**, sourced from
  existing platform team metadata. We adopt the key; we do not mint it. This is
  what makes a single customer spanning both regions coherent.
- **Residency: run data, events, artifacts and audit records never leave their
  home region.** Cross-region access is a **read-path proxy** — the local API
  looks up `home_region` in the directory, forwards the request under the
  caller's identity, and returns the response **without persisting it outside
  the home region**. Audit chains (D15) are wholly in-region and anchor to
  in-region WORM storage.
- **Consequence for D48's X5** (multi-cloud worker/system-database placement):
  resolved by construction — each region has its own workers and its own DBOS
  system database. No cross-region workflow recovery, ever.

### 1.1 Isolation is not thread-level (D50)

Parallel execution for hundreds of Principals is a **scheduling** problem, not
an isolation one. Thread and async-task boundaries are **not** a security
boundary — Python threads share a heap, and the primary threat (indirect prompt
injection, D7) does not respect them.

Isolation comes from three mechanisms already locked:

| Mechanism | Decision | What it stops |
|---|---|---|
| Run-scoped capability token | D10 | A Run cannot *name* another Tenant's credentials |
| Tool Gateway resolves credentials by Tenant, never ambient | D7, D7a, D18 | A compromised agent cannot reach another Tenant's connections |
| Postgres RLS on `graft_tenant_id` | D51 | A query bug cannot return another Tenant's rows |

Two hard implementation rules:

- **No ambient or thread-local Tenant context — ever.** Scope travels as an
  explicit argument through the `runtime` seam (D48), which is the natural
  chokepoint. Thread-locals plus async task switching is *the* classic
  cross-tenant leak.
- **RLS is established per transaction with `SET LOCAL`**, never `SET`:

  ```sql
  BEGIN;
    SET LOCAL graft.tenant_id = '…';   -- transaction-scoped ⇒ pooler-safe
    -- … work …
  COMMIT;
  ```

  A transaction-mode pooler reassigns connections between Tenants; a
  session-level `SET` would leak scope across that boundary. This matters
  directly because D48 identified **Postgres connection count (the pooler)** as
  the binding scale constraint.

Concurrency itself is handled by **DBOS partitioned queues keyed by
`graft_tenant_id`** (D44) over the worker StatefulSet (D38) — a native
implementation of D17's ceiling chain.

---

## 2. The scope model (C2 — D51)

**One scoping layer.** The four-layer `Tenant → Workspace → Group → Principal`
tree proposed in the briefing collapsed, because Tenant and Workspace were
1:1 with the same external key.

```
Tenant  (graft_tenant_id)   ≡ GrafanaOrg, 1:1
   ├── Group (IdP claim) ──▶ Role        [authorization, not scoping]
   └── Principal                          [identity, not scoping]
```

### 2.1 Why not use the Grafana `grafana_org_id` as the key

| | `grafana_org_id` | `graft_tenant_id` |
|---|---|---|
| Uniqueness | **Region-local only** — GCP org 5 ≠ AliCloud org 5, but the integers collide | Globally unique across both regions |
| Authority | Grafana's autoincrement; changes if an org is deleted and recreated | Existing platform metadata, already reconciled |
| Coupling | Primary scoping key owned by an external system | Ours to guarantee |

`grafana_org_id` is stored as a **mapped attribute** on the Tenant row, not as the key.

### 2.2 Why collapsing is safe

The briefing's warning — "retrofitting isolation is one of the genuinely
expensive rewrites" — is about adding a scoping key *below* existing rows.
Collapsing runs the other way: if a **billing parent** above Tenant is ever
needed (one customer, several teams, one invoice), that is a new table and a
join, not a backfill of every row, event, span and audit record. We are
simplifying in the reversible direction.

### 2.3 Tenant resolution per surface

| Surface | Resolution | Notes |
|---|---|---|
| **Grafana app plugin** | **Follows the active GrafanaOrg.** Switch org in Grafana, the Tenant changes. | The Grafana surface contains *no* Tenant-resolution logic at all |
| **Slack — channel** | Admin-configured **SlackChannel → Tenant** binding | Load-bearing in v1: one SlackWorkspace serves all Tenants |
| **Slack — DM** | Per-Principal **default Tenant**, set at account-link time (D20), switchable by slash command | |
| **Slack — neither resolves** | Bot **asks** which Tenant | Fallback only |
| **Webhook / alert** | Derived from the alert's source GrafanaOrg | |
| **Schedule** | The Tenant that owns the Schedule | |

**No cross-Tenant Runs in v1.** A cross-cloud incident touching two Tenants'
connections is two Runs. There is no audited exception to build, and therefore
no exception to get wrong.

### 2.4 Slack in v1

Single **SlackEnterprise**, single **SlackWorkspace** (D52). `slack_enterprise_id`
and `slack_workspace_id` are recorded on the `PrincipalIdentity` row for provenance and
for D28's key-selection rule, and scope **nothing**.

---

## 3. Tenant lifecycle and brownfield onboarding (D53)

Hundreds of GrafanaOrgs already exist. D22 requires service-account
provisioning to be **synchronous and a precondition of readiness** — never
lazy. Both are satisfied by a lifecycle:

```
discovered ──────▶ provisioning ──────▶ ready ──────▶ suspended
     │                   │                 │
     │                   │                 └─ SAs exist · roles minimal · tokens valid
     │                   └─ synchronous, atomic, D22 semantics
     └─ shell row only. NO service accounts. NO credentials. NO cost.
        Created by the reconciler for every existing GrafanaOrg.
```

- **Every existing GrafanaOrg gets a `discovered` Tenant row.** Free and
  credential-less, so the capability is one admin action away for all teams —
  matching the expectation that most teams will want it.
- **`discovered → ready` is the explicit admin act**, and *that* is where D22's
  synchronous SA provisioning fires. We never hold hundreds of unused
  credentials, and D22 is untouched.
- **One code path.** Backfill reconciler and new-org hook call the same
  idempotent provisioner. No special-case migration script to rot.
- **`suspended`** revokes tokens and rejects new Runs without deleting history.

### 3.1 Platform-owned service accounts: naming, drift, rotation

Grafana OSS gives us no way to *prevent* a GrafanaOrgAdmin deleting or editing
a platform-owned SA. Naming is therefore a **signal**, and reconciliation is
the **control**.

- **Reserved naming:** `graft-platform-enforcement` and `graft-platform-mcp`,
  with a display name stating *"Managed by the Graft platform — do not
  modify."* Any SA under the `graft-platform-` prefix is platform-owned.
- **Drift reconciler** (a scheduled DBOS workflow, D47) asserts, per Tenant:
  SA exists · role == minimum required across enabled tools (D22) · token
  present and unexpired. Divergence triggers re-provision, and always an audit
  record.
- **Rotation** is a scheduled workflow, not a calendar reminder. Tokens always
  carry an expiry (D12); rotation runs well inside it.
- **Metrics, per SA:** token age, time-to-expiry, last successful use, drift
  events detected, re-provisions performed, reconciler lag. These are the
  monitoring surface for the platform team.

---

## 4. Run ownership, visibility and approval (C3 — D54, D55)

### 4.1 Ownership and visibility

**D36 supersedes R4.** Ownership is a per-Run property, not a blanket rule for
a run-type.

| Case | Ownership at birth | Notes |
|---|---|---|
| `user_initiated` | **Private to the initiating Principal** | Promotable to tenant-shared |
| `system_initiated` (webhook, Schedule) | **Tenant-shared** | Nobody initiated it; private-by-default would make it invisible to everyone |

- **Sharing is irreversible.** A tenant-shared Run cannot be made private
  again — un-sharing after the fact is security theatre and complicates the
  audit story. It can be **archived**, not un-shared.
- **Sharing activates D32's soft-lock driver model.** A private Run has no
  multi-viewer concern by construction.
- **Archival does not change visibility** — it is a storage-tier and
  mutability change (read-only), not an access-control change.
- **De-provisioned Principals:** their private Runs become **inaccessible
  in-product**. Audit records are unaffected and retained for the full 12
  months (D15, insert-only) — the end-to-end audit trail, not the product UI,
  is the forensic path.

### 4.2 Approval authority

**Approval is initiator-only in v1**, on top of the existing constraints:
approval is a distinct, re-authenticated act that always happens in Grafana
(D14), and the action must independently pass **check-then-act** against the
initiator's own Grafana permission (D23).

```
may_approve(principal, run, action) =
        principal == run.initiator                      (D55)
    AND re-authenticated in Grafana                     (D14)
    AND check-then-act passes for this action           (D23, D26 basic roles)
    AND run.origin == user_initiated                    (D13)
```

**Accepted consequence — stated plainly:** if the initiator goes offline, the
approval is **not** transferable, and the Run expires (D47, ≥72h). This
deliberately trades R4's original "Bob approves when Alice is offline"
rationale for a simpler, unambiguous attribution story in v1.

**Revisit metric** (same pattern as D24): track the **expired-approval rate** —
Runs closed `expired` with a pending `hitl_required`. If it becomes material,
promote to a delegated-approval or tenant-approver model.

### 4.3 Platform admin break-glass

`platform_admin` (the GrafanaServerAdmin) may enter **any** Tenant to
**read, cancel and suspend** Runs.

**They may not approve.** Separation of duties: the actor who can reach every
Tenant must not also be able to authorise writes in every Tenant. Break-glass
covers incident containment, not action authorisation.

Every break-glass access emits an audit record naming the `platform_admin`, the
Tenant entered, and the action taken — non-sampled (D15).

### 4.4 Two-person rule

**Not in v1.** Initiator-only approval and a two-person rule are mutually
exclusive by definition. Deferred to the HITL & write-action session.

---

## 5. Roles and authorization (C4 — D56)

**The IdP authenticates; the harness authorizes.** The IdP establishes *who the
Principal is* and nothing more. Role assignment, permission verbs and their
evaluation are entirely ours, in our own tables. This satisfies the
IdP-independence requirement (Entra / Keycloak / Auth0 / AD interchangeable
with zero code change) and is unaffected by D26's finding that fine-grained
RBAC is Grafana-Enterprise-only.

### 5.1 Roles

| Role | Scope | Default source (D56/Q16) | Capabilities |
|---|---|---|---|
| `platform_admin` | Platform | **GrafanaServerAdmin** | Tenant lifecycle, platform ceilings, quota overrides, break-glass read/cancel/suspend (§4.3). **Cannot approve.** |
| `tenant_admin` | Tenant | **GrafanaOrgAdmin** | Connections, tool policy (D16), budgets, Schedules, Group→Role mapping, quota-increase requests. Plus everything `responder` can do. |
| `responder` | Tenant | **Grafana Editor** | Create / steer / cancel / share own Runs; propose actions; **approve their own Run's actions** subject to §4.2 |
| `viewer` | Tenant | **Grafana Viewer** | Read tenant-shared Runs. No Run creation. |

**`operator` was considered and removed.** A separate approve-granting role
deadlocked against initiator-only approval: an Editor-mapped `responder` could
start a Run whose proposed action nobody was permitted to approve. Approval
authority is instead resolved **per action, at call time, by D23** — which is
exactly D16's "per-user variation is an authorisation filter at call time,
never a separate configuration". An Editor may approve a dashboard change
because Grafana says they may edit dashboards.

**Non-Grafana write classes** (K8s restart, GitHub PR, Jira) have no Grafana
permission to check against. For these, the **required Role is declared
explicitly in the tool policy** (D16), defaulting to `tenant_admin`.

**Extensibility:** Roles and permission verbs are **rows, not code**. Adding a
role, or splitting `responder`, is a data change plus a policy version bump
(D16) — no deploy, no Grafana Enterprise licence.

### 5.2 Permission verbs

```
run:create   run:read    run:steer    run:cancel   run:share
action:propose           action:approve
connection:manage        policy:manage
budget:manage            schedule:manage
member:manage            tenant:provision         tenant:breakglass
```

### 5.3 Resolution order

```
1. Explicit Group→Role mapping for this Tenant   ─┐  first match wins
2. Explicit per-Principal Role grant              │
3. Default mapping from Grafana basic role        ─┘  (§5.1, zero-config)
⇒ harness Role
⇒ AND, at call time, check-then-act against the Principal's Grafana
   permission for Grafana-scoped actions (D23)
```

Layer 3 is what makes brownfield onboarding viable: a newly-`ready` Tenant is
immediately usable with sane permissions and **zero configuration**, and an
admin overrides with Group mappings only when they want something different.

The call-time Grafana check is **not** a role source — it is an independent
ceiling and a safety net. Our Role can never cause an action Grafana itself
would refuse. (D24 remains the stated exception: Slack-initiated and
`system_initiated` Runs are bounded solely by the Tenant's service-account
role.)

### 5.4 De-provisioning

**TTL-only.** A Principal removed at the IdP loses access when their harness
token expires (~10 min, D10). The D10 deny-list remains available for
immediate revocation in an incident. No SCIM and no polling in v1.

---

## 6. Budgets, quotas and schedule ceilings (C5, X6 — D57, D58)

### 6.1 The ceiling chain

D17's chain loses a layer with the scope collapse:

```
platform  ≥  tenant  ≥  principal  ≥  run
```

Effective limit is the **minimum across scopes**. Platform ceilings are **not
customer-raisable**. Per-connection throttles (protecting *customer*
infrastructure, e.g. a shared K8s control plane) are keyed by connection and
remain **independent** of Tenant quota (D44).

### 6.2 At-cap behaviour

| Cap | Behaviour at cap |
|---|---|
| **Per-run** — tokens, cost, graph depth, wall clock | **Graceful terminate.** Emit the best hypothesis formed so far plus `budget_consumed` (D29). Never a bare failure. |
| **Per-principal** — monthly | **Hard stop.** New Runs rejected; in-flight Runs finish. Surfaced in the UI *before* it is reached (§6.4). |
| **Per-tenant** — monthly | **Hard stop.** New Runs rejected; in-flight Runs finish. The billing boundary. |
| **Per-connection** | **Throttle / queue.** Protects customer infrastructure; never fails the Run outright. |

**No degrade-to-a-cheaper-model.** Model selection is a platform decision
driven by evals and availability, not a runtime budget lever. A cheaper model
mid-Run would also silently change the quality characteristics an operator is
about to act on.

### 6.3 Reset cadence and raising caps

- **Monthly reset** for both per-Principal and per-Tenant quotas.
- **Platform team sets and customises quotas** per Principal and per Tenant.
  Not self-service.
- **`tenant_admin` and `responder` can request an increase from the UI.** The
  in-product action creates a service-desk ticket via the existing ITSM
  integration, **pre-filled** with `graft_tenant_id`, current ceiling, observed
  consumption, and the triggering `graft_run_id`, under an idempotency key so a
  double-click does not open two tickets. A `platform_admin` applies the new
  ceiling in the admin UI; the change is an audit record and a policy version
  bump (D16).
  - *Fallback if ITSM integration slips:* a deep link to the service desk with
    the same context in the URL. Same UX, no API dependency.

### 6.4 Visibility and monitoring

- **In-product quota indicator** — per-Principal and per-Tenant consumption
  against ceiling, always visible (the braindump's "Limits/Quota Indicator" and
  "Show Token Usage/Budget").
- **Notification at threshold** (proposed: 80%) and at cap, via the D35
  notification path.
- **Platform monitoring:** consumption vs ceiling per Tenant and per Principal,
  at-cap rejection rate, quota-increase request rate, and time-to-fulfil. These
  are the signals that tell the platform team the defaults are wrong.

### 6.5 Schedules as a governed resource (X6 — D58)

Schedules (D47) are Tenant-owned, runtime-mutable and cost money, so they get
the same treatment as any other tenant-scoped resource:

- **Ceiling on Schedule count per Tenant** and a **minimum interval**.
  *Proposed defaults, to confirm with cost data:* **10 Schedules per Tenant**,
  **minimum interval 1 hour**. Both are `platform_admin`-customisable per
  Tenant per §6.3.
- **Versioned policy, never overwritten** (D16). Every create/modify/delete is
  an audit record naming the Principal.
- **Schedule consumption counts against the Tenant's monthly quota** — a
  Schedule is not a budget bypass.
- **All scheduled Runs are `system_initiated` and therefore structurally
  read-only** (D13, D47). A Schedule can investigate and report; it can never
  act. This bounds the risk of Schedules to *cost*, not *blast radius*.

#### What Schedules are for

| Use | Origin | Owner |
|---|---|---|
| Recurring proactive health / SLO sweeps ("any degradation in payments overnight?") | `system_initiated` | Tenant |
| **Post-incident follow-up verification** — re-check in 24h that a fix held | `system_initiated` | Tenant |
| Recurring configuration- or cost-drift reports | `system_initiated` | Tenant |
| Pre-emptive checks ahead of a known high-traffic event | `system_initiated` | Tenant |
| **Infrastructure-memory refresh** (`*/15`, D47) | internal | **Platform** — not tenant-configurable, not quota-counted |
| **SA drift reconciliation and rotation** (§3.1) | internal | **Platform** |

The last two are platform-internal machinery that happens to use the same timer
substrate. They are not user-facing Schedules and do not consume a Tenant's
Schedule ceiling.

---

## 7. Data model sketch

### 7.1 Tenancy and identity

```sql
CREATE TABLE tenant (
    graft_tenant_id   text PRIMARY KEY,        -- external, globally unique
    display_name      text NOT NULL,
    home_region       text NOT NULL,           -- 'gcp' | 'alicloud'
    grafana_org_id    integer NOT NULL,        -- MAPPED ATTRIBUTE, not a key
    lifecycle_state   text NOT NULL,           -- discovered|provisioning|ready|suspended
    created_at        timestamptz NOT NULL DEFAULT now(),
    UNIQUE (home_region, grafana_org_id)       -- grafana_org_id unique only within a region
);

CREATE TABLE principal (
    graft_principal_id      uuid PRIMARY KEY,
    kind              text NOT NULL,           -- human|bot|webhook|schedule
    status            text NOT NULL,           -- active|deprovisioned
    default_graft_tenant_id text REFERENCES tenant   -- Slack DM resolution
);

CREATE TABLE principal_identity (              -- the federation table
    graft_principal_id      uuid NOT NULL REFERENCES principal,
    provider          text NOT NULL,           -- grafana|slack|idp
    external_id       text NOT NULL,           -- D28 decides this for slack
    slack_enterprise_id     text,                    -- provenance only, scopes nothing
    slack_workspace_id           text,                    -- provenance only, scopes nothing
    PRIMARY KEY (provider, external_id)
);
```

### 7.2 Authorization

```sql
CREATE TABLE role        (graft_role_id text PRIMARY KEY, scope_level text NOT NULL);
CREATE TABLE role_permission (graft_role_id text REFERENCES role, verb text,
                              PRIMARY KEY (graft_role_id, verb));

CREATE TABLE group_role_mapping (              -- §5.3 layer 1 — admin config
    graft_tenant_id   text NOT NULL REFERENCES tenant,
    idp_group_claim   text NOT NULL,
    graft_role_id           text NOT NULL REFERENCES role,
    policy_version    integer NOT NULL,        -- versioned, never overwritten (D16)
    PRIMARY KEY (graft_tenant_id, idp_group_claim, policy_version)
);

CREATE TABLE principal_role (                  -- §5.3 layer 2 — explicit grant
    graft_tenant_id   text NOT NULL REFERENCES tenant,
    graft_principal_id      uuid NOT NULL REFERENCES principal,
    graft_role_id           text NOT NULL REFERENCES role,
    PRIMARY KEY (graft_tenant_id, graft_principal_id)
);
```

Layer 3 (default from Grafana basic role) is **computed at token-mint time**,
not stored — it must track the live Grafana role, not a stale copy.

### 7.3 Runs, and the RLS pattern

```sql
CREATE TABLE run (
    graft_run_id            uuid PRIMARY KEY,
    graft_tenant_id   text NOT NULL REFERENCES tenant,
    initiator_id      uuid REFERENCES principal,   -- NULL ⇒ system_initiated
    origin            text NOT NULL,               -- user_initiated|system_initiated
    visibility        text NOT NULL,               -- private|tenant_shared
    status            text NOT NULL,
    dbos_workflow_id  text NOT NULL,               -- D39
    created_at        timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE run ENABLE ROW LEVEL SECURITY;
ALTER TABLE run FORCE ROW LEVEL SECURITY;        -- applies to the table owner too

CREATE POLICY tenant_isolation ON run
    USING (graft_tenant_id = current_setting('graft.tenant_id', true));
```

`FORCE ROW LEVEL SECURITY` matters: without it the table owner — which the
application role often is — silently bypasses every policy.

The identical pattern applies to `run_event` (D30), `audit_record` (D15),
`connection`, `schedule`, `tool_policy` and every other tenant-scoped table.

### 7.4 Scoping beyond the database

| Carrier | Must carry | Decision |
|---|---|---|
| Capability token | `graft_tenant_id`, `graft_run_id`, `graft_principal_id`, tool classes | D10, D19 |
| Event log rows | `graft_tenant_id`, `graft_run_id`, monotonic `graft_event_id` | D30 |
| Grafana Live channel | `graft_tenant_id` + `graft_run_id` in the channel path; authorized in `SubscribeStream` | D31 |
| OTel spans | `graft_tenant_id` resource attribute, tagged at the Collector | D5, D8 |
| Audit records | `graft_tenant_id`, `graft_principal_id`, `graft_run_id`, `caused_by` | D15 |
| DBOS queue partition key | `graft_tenant_id` | D44 |
| Secret store paths | namespaced by `graft_tenant_id` | D7 |

---

## 8. Open items (implementation-time, not architectural)

1. **Quota numbers.** Per-Principal and per-Tenant monthly token/cost ceilings
   need real cost data before defaults are set. Same status as D47's expiry
   duration: the mechanism is locked, the number is an untaken product
   decision.
2. **Schedule defaults** (10/Tenant, 1h minimum) to confirm against expected
   Run cost.
3. **Quota-increase request path** — confirm whether the ITSM API integration
   lands in v1 or whether the pre-filled deep-link fallback ships first.
4. **Tenant Directory replication mechanism** for the cross-region read proxy —
   metadata-only, but needs a chosen substrate and a staleness budget.
5. **Backfill reconciler run-book** — first execution against hundreds of
   existing GrafanaOrgs should be rehearsed; it is idempotent by design, but
   the first run is the one that proves it.
6. **Expired-approval rate** instrumentation, as the D55 revisit trigger.
