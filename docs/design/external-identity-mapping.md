# External Identity & Reference Mapping

> **Status: 🟢 Resolved for v1 (2026-09-13).** Locked as **ADR-0060** (mapping model)
> and **ADR-0061** (mandatory verified linking). Extends **ADR-0052** (glossary) and
> **ADR-0059** (identifier prefixes).
>
> Vocabulary per [`../GLOSSARY.md`](../GLOSSARY.md). Related:
> [`slack-identity-and-surface.md`](./slack-identity-and-surface.md),
> [`tenancy-and-scoping.md`](./tenancy-and-scoping.md),
> [`audit-and-attribution.md`](./audit-and-attribution.md).

---

## 1. The problem: there are three layers, not two

ADR-0059 fixed *prefixes*, but a prefix alone still conflates two different things:
**our name for a slot** and **the external system's name for the thing in it**.

```
   Layer 1              Layer 2                    Layer 3
   OUR KEY              OUR REFERENCE SLOT         THEIR NATIVE FIELD
   (we mint it)         (our column name)          (their vocabulary)
   ─────────────────────────────────────────────────────────────────────
   graft_tenant_id  ──▶ grafana_org_id        ──▶  Grafana  `id` / `orgId`
   graft_tenant_id  ──▶ slack_channel_id      ──▶  Slack    `channel_id`
   graft_principal_id ▶ slack_user_id         ──▶  Slack    `user_id` / `sub`
   graft_principal_id ▶ grafana_user_id       ──▶  Grafana  `sub` (ID token)
   graft_principal_id ▶ idp_subject           ──▶  OIDC     `sub` + `iss`
```

Layer 2 is **ours** — we choose it for readability and it never changes.
Layer 3 is **theirs** — it changes when they rename things, and it is the name
you must use when reading their API docs or debugging a payload.

Conflating 2 and 3 is what produces the bug where someone greps an API response
for `slack_workspace_id`, finds nothing, and concludes the integration is
broken.

---

## 2. How other systems solve this (verified against primary sources)

### 2.1 SCIM — RFC 7643 section 3.1 *(read directly, 2026-09-13)*

SCIM formalises exactly this two-party problem:

- **`id`** — "assigned by the service provider… MUST be a **stable,
  non-reassignable** identifier that does not change when the same resource is
  returned in subsequent requests… MUST NOT be specified by the client."
- **`externalId`** — "an identifier for the resource **as defined by the
  provisioning client**… The service provider MUST always interpret the
  externalId as **scoped to the provisioning domain**."

Two things worth taking:

1. **The RFC's stated motivation for `externalId` is literally to avoid our
   problem** — "obviating the need to store a local mapping between the
   provisioning domain's identifier of the resource and the identifier used by
   the service provider." We cannot use that escape hatch (Grafana and Slack
   do not accept a `graft_tenant_id` we hand them), so **we must store the
   local mapping** — which makes doing it deliberately, once, the right call.
2. **"Stable, non-reassignable" is called out as a requirement, not an
   assumption.** Most of the ids we consume do *not* meet it. See section 4.

### 2.2 Backstage — well-known annotations *(read directly, 2026-09-13)*

Backstage's catalog is the closest analogue to our Tenant registry, and its
convention is unambiguous:

- Its own key is an **`entityRef`** (`kind:namespace/name`). External ids are
  **never** the entity key.
- Foreign ids live in **annotations namespaced by the external system's DNS
  domain**: `github.com/project-slug`, `github.com/team-slug`,
  `github.com/user-login`, `jenkins.io/job-full-name`, with `backstage.io/*`
  reserved for their own.
- **The annotation is named in the foreign system's own vocabulary.** The docs
  for `github.com/project-slug` say it is "the so-called slug that identifies a
  repository on GitHub… the same as can be seen in the URL location bar."

So Backstage does exactly the three-layer split: `entityRef` (theirs) →
`github.com/project-slug` (their slot, namespaced by owner) → the slug itself
(GitHub's vocabulary, unrenamed).

**This is a mild challenge to our own `slack_workspace_id`**, which is named
for Slack's *UI* term rather than its *API* term (`team_id`). We are keeping
it — Slack's own UI calls it a workspace, and the API name is genuinely
confusing — but the three-layer model is precisely what makes that safe:
Layer 3 records `team_id` explicitly, so the ambiguity is documented rather
than hidden.

### 2.3 incident.io catalog-importer *(config reference read directly, 2026-09-13)*

Their sync model carries **two** foreign-facing fields, not one:

- **`external_id`** — the source system's stable identity for the entry.
- **`sync_id`** — "how the importer knows which catalog types it should remove
  when they've been removed from the configuration"; recommended value is "the
  repo name that the importer runs from, or the ID of the CI pipeline."

The second is the interesting one: it is a **provenance and lifecycle marker**,
separate from the identity itself. It answers *"who owns this mapping, and
therefore who is allowed to delete it."* We adopt the same idea — it is what
makes a reconciler safe to run (section 5.3), and it is the same instinct as ADR-0053's
drift reconciler.

### 2.4 Not verified

PagerDuty's and incident.io's *user*-identity mapping specifics could not be
retrieved (docs are JS-rendered and several URLs 404'd). The widely-used
industry shortcut in this space is **joining on email address**. We are
explicitly rejecting that — see section 4.1 — on first principles rather than on
their authority, so nothing here depends on that unverified claim.

---

## 3. The model

Two tables: a **static registry** describing each kind of reference, and a
**mapping table** holding the values.

### 3.1 Reference-kind registry

```sql
CREATE TABLE graft_ref_kind (
    ref_kind      text PRIMARY KEY,   -- Layer 2: OUR slot name
    provider      text NOT NULL,      -- 'grafana' | 'slack' | 'idp' | 'dbos' | …
    native_field  text NOT NULL,      -- Layer 3: THEIR field name
    native_api    text NOT NULL,      -- where to see it, for the debugger
    is_stable     boolean NOT NULL,   -- never reassigned to a different thing?
    is_global     boolean NOT NULL    -- globally unique, or scoped/local?
);
```

`is_stable` and `is_global` earn their place: **they are the two assumptions
that cause outages when they are wrong**, and today they live only in people's
heads.

| `ref_kind` (ours) | provider | `native_field` (theirs) | native_api | stable | global |
|---|---|---|---|---|---|
| `grafana_org_id` | grafana | `id`, `orgId` | `GET /api/orgs`; plugin context; `X-Grafana-Org-Id` | yes | **no — region-local** |
| `grafana_user_id` | grafana | `sub` | `X-Grafana-Id` ID token (ADR-0009) | yes | no — per instance |
| `slack_workspace_id` | slack | **`team_id`** | event envelope; `team.info` | yes | yes |
| `slack_enterprise_id` | slack | `enterprise_id` | event envelope | yes | yes |
| `slack_channel_id` | slack | `channel_id` | event envelope | yes | yes |
| `slack_user_id` | slack | `user_id` / OIDC `sub` | Sign in with Slack (ADR-0020) | yes | yes |
| `idp_subject` | idp | `sub` (+ `iss`) | OIDC ID token | yes | **only with `iss`** |
| `dbos_workflow_id` | dbos | `workflow_id` | DBOS (ADR-0042) | yes | yes — **but we mint the value**, section 3.4 |
| `lgtm_tenant_id` | mimir/loki | `X-Scope-OrgID` | query headers | — | no |

Rows marked **`is_global = false`** are the trap: a `grafana_org_id` of `5`
exists in *both* ADR-0049 regions and means different Tenants. Any lookup by a
non-global ref **must** be qualified by region (or instance), and the schema
enforces it (section 3.2).

### 3.2 Mapping table

```sql
CREATE TABLE graft_external_ref (
    graft_entity_type text NOT NULL,      -- 'tenant' | 'principal' | 'connection'
    graft_entity_id   text NOT NULL,      -- graft_tenant_id / graft_principal_id / …
    ref_kind          text NOT NULL REFERENCES graft_ref_kind,
    external_value    text NOT NULL,      -- the raw value, verbatim, never normalised
    ref_scope         text NOT NULL,      -- region/instance for non-global kinds; '' if global
    verified_at       timestamptz,        -- NULL ⇒ claimed, not proven (section 4.2)
    sync_source       text NOT NULL,      -- incident.io's sync_id idea (section 5.3)
    graft_tenant_id   text NOT NULL REFERENCES tenant,   -- RLS predicate (ADR-0050)
    PRIMARY KEY (ref_kind, ref_scope, external_value)    -- inbound lookup direction
);

CREATE INDEX ON graft_external_ref (graft_entity_type, graft_entity_id);  -- outbound
```

The primary key is deliberately on the **inbound** direction
(`their id → our id`), because that is the hot path: every Slack event, every
Grafana request and every webhook arrives carrying a foreign id and must
resolve to a `graft_*` key before anything else happens. Including `ref_scope`
in the key makes the region-local trap **structurally impossible** rather than
a thing to remember.

`external_value` is stored **verbatim** — never lower-cased, trimmed or
otherwise "helpfully" normalised. Normalisation is how you silently merge two
distinct principals.

### 3.3 What this replaces

The `principal_identity` table sketched in
[`tenancy-and-scoping.md`](./tenancy-and-scoping.md) section 7.1 is a **special case
of this table** (`graft_entity_type = 'principal'`). Keep one mechanism, not
two: `principal_identity` becomes a view over `graft_external_ref`.

### 3.4 The `dbos_workflow_id` edge case

ADR-0042 makes the DBOS workflow id **caller-supplied**. So it carries a foreign
prefix (it lives in DBOS's namespace) while the *value* is minted by us — the
one row in section 3.1 where those differ.

**Set `dbos_workflow_id = graft_run_id`.** They then cannot drift, ADR-0042's
run-creation idempotency key becomes self-evident, and correlating a DBOS
workflow to a Run in an incident needs no lookup at all.

---

## 4. Rules

### 4.1 Email is never a join key

Email addresses are **mutable and reassignable** — a departing employee's
address is routinely reissued to a new hire. Joining identities on email means
that reassignment is an **identity takeover** that grants the new hire the old
one's Runs and approvals, silently.

This is directly disqualifying under ADR-0015 (the actor must derive from a verified
credential) and ADR-0025 (PCI-DSS). Email may be *displayed*; it may never be
*matched on*.

The correct federated key is the **`(iss, sub)` pair**, per OIDC — `sub` alone
is only unique within its issuer.

### 4.2 Links are verified, never inferred

`verified_at IS NULL` means *claimed*. A mapping becomes verified only by an
authenticated round trip that proves control of the external identity — for
Slack, the "Sign in with Slack" OIDC flow (ADR-0020).

**An unverified link grants nothing.** This is what makes ADR-0061 enforceable.

### 4.3 Foreign ids are never our primary key

Per Backstage and SCIM both: our tables key on `graft_*`. A foreign id appears
only in `graft_external_ref`. This is what let ADR-0051 delete `workspace_id`
without touching every table, and it is what keeps a Grafana org deletion and
recreation from orphaning a Tenant's entire history.

### 4.4 One entity may hold several refs of the same kind; none may be shared

A Principal can legitimately hold several `slack_user_id` values (Grid, ADR-0028).
Two Principals may never hold the **same** one — enforced by the primary key in
Section 3.2.

---

## 5. Mandatory identity linking (ADR-0061)

> **Correction adopted 2026-09-13.** A single Slack install (ADR-0052) does **not**
> mean a single identity. Every Tenant and every human must authenticate to
> Graft so their identity is mapped across systems.

### 5.1 The rule

**Graft never acts on behalf of a human whose identity is not verifiably
linked for the surface they are acting from.**

| Actor state | What happens |
|---|---|
| Verified link exists for this provider | Proceed |
| No link, or `verified_at IS NULL` | **Link prompt, not a Run.** Ephemeral Slack message with a signed, single-use "Sign in with Slack" link (ADR-0020) |
| Link exists, Principal has no Role in the resolved Tenant | Refuse with an explicit "ask your `tenant_admin`" message — *not* a generic error |
| `system_initiated` (webhook, Schedule) | No human to link. Bounded by the Tenant service account and structurally read-only (ADR-0013/ADR-0024) |

### 5.2 Why it is mandatory, not a nicety

- **ADR-0015 requires the audit actor to derive from a verified credential**, never
  from agent or tool output. An unlinked SlackUser cannot produce a compliant
  audit record — there is no `graft_principal_id` to attribute to.
- **ADR-0065 makes approval driver-based** (superseding ADR-0055's initiator-only rule,
  withdrawn 2026-09-13). The argument below is unchanged and in fact
  strengthened: *driver* is as meaningless as *initiator* without a
  resolved Principal.
- **ADR-0024 remains true and is not weakened:** Slack-initiated Runs are still
  *authorised* by the Tenant service account's ceiling. Linking is about
  **attribution**, not authorisation. We must know *who asked* even when the
  permission check does not use their identity — and ADR-0024's revisit metric
  (denials that would have succeeded under the user's own role) is only
  computable if we know who they are.

### 5.3 Tenant-level linking, and reconciler safety

Tenant linking is the `discovered → ready` transition (ADR-0053): binding
`graft_tenant_id ↔ grafana_org_id` and the SlackChannel bindings is precisely
what a `tenant_admin` does at that step.

`sync_source` (section 3.2, after incident.io's `sync_id`) records **which process
created each mapping** — `backfill-reconciler`, `admin-ui`, `slack-oidc`. A
reconciler may only delete mappings it owns. Without this, the ADR-0053 backfill
reconciler could plausibly remove an admin's hand-made binding, which is the
classic destructive-sync incident.

---

## 6. Consequences for existing decisions

| Decision | Effect |
|---|---|
| **ADR-0052** | `principal_identity` generalises into `graft_external_ref`; one mechanism |
| **ADR-0059** | Extended: the prefix names the **owner of the namespace**; `graft_ref_kind.native_field` records the owner's **own** name for it |
| **ADR-0020** | "Sign in with Slack" is promoted from a one-time convenience to a **precondition** for any human-attributed Slack action |
| **ADR-0024** | Unchanged and clarified: SA ceiling governs *authorisation*; linking governs *attribution* |
| **ADR-0049** | `ref_scope` makes region-local foreign ids safe by construction |
| **ADR-0053** | `sync_source` is what makes the backfill reconciler non-destructive |
| **ADR-0042** | `dbos_workflow_id = graft_run_id` (section 3.4) |

---

## 7. Open items

1. **Verify Layer-3 field names at implementation time** against live payloads
   for: Grafana `X-Grafana-Id` token `sub` format, Slack event-envelope field
   names, and Slack OIDC `sub`. The section 3.1 table is populated from
   documentation and prior sessions (ADR-0009, ADR-0020, ADR-0028), not from captured traffic.
2. **Re-link on Slack Grid migration** — if a customer migrates a standalone
   workspace into a Grid, `slack_user_id` changes shape (ADR-0028). Needs a
   migration path, or an accepted re-link event.
3. **Unlinked-user friction metric** — track link-prompt-to-completion rate;
   if it is poor, the Slack surface silently under-delivers.
