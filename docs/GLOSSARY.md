# Glossary — Ubiquitous Language

> **Status: normative.** Locked as **D52** (2026-09-13). This document is the
> single source of truth for domain vocabulary. Where any other document in this
> repository conflicts with it, this one wins and the other is a bug.
>
> Related: [`adr/DECISION-REGISTER.md`](./adr/DECISION-REGISTER.md),
> [`design/tenancy-and-scoping.md`](./design/tenancy-and-scoping.md).

---

## 0. Why this exists

Three separate systems in this architecture use the same words for different
things:

| Word | Means, to… | …something completely different from |
|---|---|---|
| **tenant** | Mimir / Loki (`X-Scope-OrgID`) | our isolation boundary |
| **org** | Grafana (`grafana_org_id`) | Slack Enterprise Grid ("the Grid org") |
| **workspace** | Slack (`slack_workspace_id`) | what we previously called our own scope |

Two rules resolve all of it:

1. **Our own scoping key is prefixed `graft_`.** Never a bare `tenant_id`.
2. **Foreign terms are never used bare.** It is always `GrafanaOrg`,
   `SlackWorkspace`, `SlackEnterprise`, `LGTMTenant` — never "org",
   "workspace", "tenant" on its own when referring to another system.

The word **Workspace** has been **removed from our vocabulary entirely**
(D51). It no longer names anything of ours. If you see it in an older
document, read it as **Tenant**.

---

## 1. Our concepts

| Term | Definition | Key | Cardinality |
|---|---|---|---|
| **Tenant** | The isolation, billing, ownership and configuration boundary. Owns connections (datasources, clusters, repos, ticketing), tool policy, budgets, schedules, custom instructions, and all Runs. **The only scoping layer.** | `graft_tenant_id` — externally sourced from existing platform team metadata; globally unique **across both regional deployments** | 1:1 with a **GrafanaOrg** |
| **Principal** | Any actor: a human, a bot, a webhook, or a schedule. The identity every surface resolves to and every audit record attributes to. | `graft_principal_id` — **ours**, minted by us | — |
| **PrincipalIdentity** | An external identity claim that maps to a Principal. One Principal may have several (Grafana, Slack, IdP). | `(provider, external_id)` | N:1 to Principal |
| **Group** | An IdP-supplied group used to grant Roles within a Tenant. An *abstraction* — never "AD group". | abstract `groups` claim value | N:M with Role |
| **Role** | A named bundle of permission verbs, scoped to Platform or Tenant. Ours, stored as data, extensible without code changes. | `graft_role_id` | — |
| **Run** | **Every** agent interaction — chat, dashboard/alert building, and RCA investigation alike (D36). One durable DBOS workflow (D39), one event stream (D30), one audit chain (D15). | `graft_run_id` | N:1 to Tenant |
| **Connection** | A Tenant-owned credentialed link to an external system (datasource, K8s cluster, repo, ticketing). | `graft_connection_id` | N:1 to Tenant |
| **Schedule** | A Tenant-owned recurring trigger for a Run (D47). Always produces `system_initiated`, structurally read-only Runs (D13). | `graft_schedule_id` | N:1 to Tenant |

### 1.1 Run origin — an attribute, not a type

| Value | Meaning | Consequence |
|---|---|---|
| `user_initiated` | A human started it, or a human approved a proposal within it | May hold write tool classes |
| `system_initiated` | Webhook/alert or Schedule started it; no human present | **Structurally read-only** (D13) — the capability token never contains a write tool class |

---

## 2. Foreign concepts, and how they map

| Foreign term                          | Belongs to                    | Key                                                               | Maps to ours                                                          | Is it a scoping layer?                                           |
|---------------------------------------|-------------------------------|-------------------------------------------------------------------|-----------------------------------------------------------------------|------------------------------------------------------------------|
| **GrafanaOrg**                        | Grafana                       | `grafana_org_id` (integer, **region-local**, assigned by Grafana) | **Tenant**, 1:1                                                       | No — it is a *mapped attribute* of a Tenant, not the scoping key |
| **GrafanaServerAdmin**                | Grafana                       | —                                                                 | **`platform_admin`** Role                                             | —                                                                |
| **GrafanaOrgAdmin / Editor / Viewer** | Grafana                       | basic roles (D26 — the only granularity in OSS)                   | Default Role mapping (D56) and an independent call-time ceiling (D23) | No                                                               |
| **SlackEnterprise**                   | Slack                         | `slack_enterprise_id` (constant across a Grid)                    | Recorded on the PrincipalIdentity                                     | **No**                                                           |
| **SlackWorkspace**                    | Slack                         | `slack_workspace_id`                                              | A **locator only**                                                    | **No**                                                           |
| **SlackChannel**                      | Slack                         | `slack_channel_id`                                                | **Bound to exactly one Tenant** by an admin                           | It is a *resolution* mechanism, not a scope                      |
| **SlackUser**                         | Slack                         | global user id (Grid) or `slack_workspace_id`+user id (D28)       | A **PrincipalIdentity** row → **Principal**                           | No                                                               |
| **LGTMTenant**                        | Mimir / Loki                  | `X-Scope-OrgID`                                                   | Nothing of ours. Coincidental name collision.                         | No                                                               |
| **IdP Group**                         | Entra / Keycloak / Auth0 / AD | `groups` claim                                                    | **Group**                                                             | No                                                               |

### 2.1 The mapping, drawn

```
Existing platform team metadata
        │  (globally unique, spans both regions)
        ▼
   graft_tenant_id ──1:1──▶ GrafanaOrg (grafana_org_id, region-local attribute)
        │
        ├── Connections, Tool policy, Budgets, Schedules, Custom instructions
        └── Runs
                └── Principal (graft_principal_id)
                        ▲
                        │  PrincipalIdentity (provider, external_id)
                        ├── grafana   : Grafana user id
                        ├── slack     : global user id  (Grid)      ── D28
                        │               slack_workspace_id + user id (non-Grid)
                        └── idp       : subject claim  → Groups → Roles
```

**Slack, v1 (single SlackEnterprise, single SlackWorkspace):** one Slack
install serves *all* Tenants. Therefore `slack_workspace_id` scopes nothing, and
**SlackChannel → Tenant binding is the load-bearing resolution mechanism**,
with a per-Principal default Tenant for DMs.

---

### 2.2 Three layers, not two

A prefix alone still conflates **our name for a slot** with **the external
system's name for the thing in it**. Always distinguish:

| Layer 1 — our key | Layer 2 — our reference slot | Layer 3 — their native field |
|---|---|---|
| `graft_tenant_id` | `grafana_org_id` | Grafana `id` / `orgId` |
| `graft_tenant_id` | `slack_channel_id` | Slack `channel_id` |
| `graft_principal_id` | `slack_user_id` | Slack `user_id`, OIDC `sub` |
| `graft_principal_id` | `grafana_user_id` | Grafana `sub` (`X-Grafana-Id` token) |
| `graft_principal_id` | `idp_subject` | OIDC `sub` (+ `iss`) |
| `graft_run_id` | `dbos_workflow_id` | DBOS `workflow_id` |
| — | `slack_workspace_id` | **Slack `team_id`** |

**Layer 2 is ours** — we choose it for readability and it never changes.
**Layer 3 is theirs** — it is the name you must use when reading their API docs
or grepping a payload. The last row is why this matters: searching a Slack
payload for `slack_workspace_id` finds nothing, because Slack calls it
`team_id`.

Layer 3 is recorded **in data**, in `graft_ref_kind.native_field`, together with
the two properties that cause outages when assumed wrong — `is_stable` and
`is_global`. See
[`design/external-identity-mapping.md`](./design/external-identity-mapping.md)
(D60).

**Foreign ids are never a primary key of ours.** They live only in
`graft_external_ref`. And **email is never a join key** — it is mutable and
reassignable, so matching on it turns an address being reissued to a new hire
into a silent identity takeover.

---

## 3. Scoping columns — the canonical set

Every row, event, span, audit record and token carries:

| Column | Always present? | Notes |
|---|---|---|
| `graft_tenant_id` | **Yes** | The RLS predicate. The only scoping key. |
| `graft_principal_id` | Yes, where an actor exists | Derived from a verified credential, never from agent or tool output (D15) |
| `graft_run_id` | Yes, within a Run | Propagated **outward** into customer-owned logs (D15) |

Deliberately **not** scoping columns: `grafana_org_id`, `slack_workspace_id`, `slack_enterprise_id`,
`slack_channel_id`. All are attributes or locators.

---

## 4. Identifier naming convention

**The rule: every identifier is prefixed with the system that owns it.** The
prefix answers "who mints this, who guarantees its uniqueness, and who may
change it" — before you read the rest of the name.

| Prefix | Meaning | We may… |
|---|---|---|
| `graft_` | **We mint it.** We own the format, guarantee uniqueness, and control its lifetime. | …rely on it as a key, index it, enforce RLS on it |
| `grafana_`, `slack_`, `idp_`, `dbos_`, `lgtm_`, `github_`, `jira_`, `k8s_` | **Somebody else mints it.** We store it, we may match on it, we guarantee **nothing** about it. | …never use it as *our* primary key, never assume global uniqueness |

An unprefixed identifier in any new code or document is a **review defect**.

### 4.1 Registry — graft-owned

| Identifier | Names | Notes |
|---|---|---|
| `graft_tenant_id` | Tenant | The **only** scoping key (D51). Externally *sourced* from platform team metadata but **graft-owned** thereafter — we guarantee it |
| `graft_principal_id` | Principal | |
| `graft_run_id` | Run | Propagated **outward** into customer-owned logs (D15) — the prefix is what makes it unambiguous in a customer's own log stream |
| `graft_event_id` | Event, monotonic per Run | D30 |
| `graft_role_id` | Role | |
| `graft_connection_id` | Connection | |
| `graft_schedule_id` | Schedule | D47 |

### 4.2 Registry — foreign

| Identifier | Owner | Notes |
|---|---|---|
| `grafana_org_id` | Grafana | Integer, **region-local**. Mapped attribute of a Tenant, never a key (D51) |
| `grafana_user_id` | Grafana | |
| `slack_enterprise_id` | Slack | Constant across a Grid. Scopes nothing (D52) |
| `slack_workspace_id` | Slack | Slack's `team_id`. **A locator only** — the name is deliberately *not* `slack_team_id`, because Slack's own UI calls it a workspace |
| `slack_channel_id` | Slack | Bound to one Tenant; a resolution mechanism, not a scope |
| `slack_user_id` | Slack | Global user id on Grid; `slack_workspace_id` + user id otherwise (D28) |
| `idp_subject`, `idp_group_claim` | IdP | Entra / Keycloak / Auth0 / AD |
| `dbos_workflow_id` | DBOS | D39 |
| `lgtm_tenant_id` | Mimir / Loki | Their `X-Scope-OrgID`. **Nothing to do with `graft_tenant_id`** |

### 4.3 Separator follows the medium, the prefix never changes

| Medium | Form | Example |
|---|---|---|
| SQL column, JSON field, token claim | `snake_case` | `graft_tenant_id` |
| OTel attribute | dotted, per semconv | `graft.tenant.id`, `graft.run.id` |
| HTTP header | `X-Graft-*` | `X-Graft-Run-Id` |
| Postgres RLS setting (GUC) | `graft.` namespace | `SET LOCAL graft.tenant_id = …` |
| Grafana Live channel path | path segment | `plugin/<id>/run/<graft_run_id>` |

### 4.4 Deliberate exceptions

- **URL path parameters** are positional and already unambiguous:
  `GET /runs/{id}/events/{event_id}/artifact` keeps its short form. The rule
  governs **field, column, claim and attribute names**, not URL templates.
- **Role-named foreign keys** keep their role name where the referent is
  obvious: `run.initiator_id` references a Principal. The type is clear from
  the constraint; the role is what the reader needs.
- **`principal_identity.external_id`** is deliberately unprefixed: it is
  polymorphic, and its owner is given by the sibling `provider` column. It is
  the one place where the prefix genuinely cannot be static.
- **Quoting an external API keeps its native spelling.** A sentence describing
  what Slack's API *returns* says `team_id`, because that is the field's real
  name and renaming it in that context would be a lie. The prefixed form
  (`slack_workspace_id`) is for **our** schema, claims and attributes — the
  place where we store it.

---

## 5. Words to never use

| Don't say | Say | Because |
|---|---|---|
| "workspace" | **Tenant** (ours) / **SlackWorkspace** (Slack's) | Removed from our vocabulary (D51) |
| "tenant_id" | `graft_tenant_id` / **LGTMTenant** | Collides with Mimir/Loki |
| "org" | **Tenant** / **GrafanaOrg** / **SlackEnterprise** | Three meanings |
| "user" | **Principal** | Excludes bots, webhooks and schedules, which are also actors |
| "session" | **Run** | There is exactly one primitive (D36) |
| "AD group" | **Group** | IdP-independence is an explicit requirement (D56) |
| "investigation" (as a type) | **Run** with RCA intent | Not a distinct primitive (D36) |
