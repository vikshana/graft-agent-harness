# Open Question 03 — Tenancy, Scoping & Ownership

> **Status: 🟢 Fully resolved for v1 (2026-09-13).** The original briefing
> (§0A–§6 below) is preserved as the historical record. **§0 summarises the
> resolutions** — locked as **D49–D58** in
> [`../DECISION-REGISTER.md`](../DECISION-REGISTER.md) and written up in
> [`../../design/tenancy-and-scoping.md`](../../design/tenancy-and-scoping.md),
> with vocabulary normalised in [`../../GLOSSARY.md`](../../GLOSSARY.md).
>
> Discharges **R3**, **R4** and risk **X6**. Remaining items are
> implementation-time, not architectural.

---

## 0. Resolution summary

### 0.1 What changed the shape of this question

Three corrections during the interview reshaped the briefing's premise:

- **The four-layer scope tree collapsed to one layer.** `Tenant → Workspace
  → Group → Principal` assumed Tenant and Workspace were distinct. They are
  not: Workspace was defined as 1:1 with a GrafanaOrg, and a GrafanaOrg is
  1:1 with a customer team, which is what `tenant_id` already identified.
  **Two keys for one concept is a bug, not prudence.** `workspace_id` was
  deleted; **`graft_tenant_id` is the single scoping key** (D51). Critically
  this simplifies in the *reversible* direction — adding a billing parent
  above Tenant later is a new table and a join; adding a scoping key *below*
  every existing row is the expensive rewrite the briefing rightly feared.
- **Vocabulary was actively ambiguous, in three directions at once.**
  "tenant" is already Mimir/Loki's `X-Scope-OrgID`; "org" means both
  GrafanaOrg and Slack Enterprise Grid org; "workspace" meant both ours and
  Slack's. Resolved by a normative glossary (D52), a `graft_` prefix on our
  own keys, a rule that foreign terms are never used bare, and by deleting
  "Workspace" from our vocabulary entirely — which eliminated the Slack
  collision for free.
- **D28 was mis-framed as a scoping dimension.** `slack_enterprise_id` is not a
  scope; it is part of *which external identifier we store* for the Slack
  provider. It becomes a column on a standard identity-federation table
  (`principal_identity`), and scopes nothing. `graft_principal_id` — ours — is the
  key everything else hangs from.

Two contradictions were surfaced and resolved rather than shipped:

- **`operator`-as-approver deadlocked against initiator-only approval.** An
  Editor-mapped member could start a Run whose proposed action *nobody* was
  permitted to approve — not them (wrong role), not anyone else
  (initiator-only). Resolved by deleting the `operator` role and letting
  **check-then-act (D23) decide approval per action at call time**, which is
  what D16 already specified.
- **The briefing's C1 leaning ("model `tenant_id` anyway, the column is
  nearly free") was right, but its four-layer companion was not.** Keeping
  `workspace_id` "just in case" would have meant two columns that must always
  agree — a standing source of isolation bugs, enforced by nothing.

### 0.2 Resolutions, per original question

| # | Question | Resolution | Decision |
|---|---|---|---|
| **C1** | Deployment model | **Grafana layer already resolved by D21.** Rest of stack: **two independent regional deployments** (GCP, AliCloud), shared-multi-tenant within each. `graft_tenant_id` globally unique across both, externally sourced from existing platform team metadata. **Run data, events, artifacts and audit records never leave their home region**; cross-region access is a read-path proxy via a globally-replicated, metadata-only Tenant Directory. Resolves D48's **X5**. | **D49** |
| **C1′** | Isolation under hundreds of concurrent users | **Thread/async-task isolation is explicitly *not* a security boundary.** Isolation is the run-scoped capability token (D10) + Tool Gateway credential resolution by Tenant (D7/D18) + Postgres RLS. Two hard rules: **no ambient or thread-local Tenant context** (scope travels explicitly through D48's `runtime` seam), and **RLS via `SET LOCAL` per transaction**, never `SET` — pooler-safe, which matters because D48 named the pooler as the binding scale constraint. Concurrency is a *scheduling* problem, already solved by D44's partitioned queues. | **D50** |
| **C2** | Grafana Org ↔ scope mapping | **Tenant ≡ GrafanaOrg, 1:1, single scoping layer.** `grafana_org_id` is a **mapped attribute**, not the key — it is a region-local integer assigned by Grafana and collides across the two deployments. Tenant resolution per surface: Grafana **follows the active GrafanaOrg** (no resolution logic at all in that surface); Slack uses **SlackChannel→Tenant binding** for channels and a per-Principal default for DMs, asking only as fallback. **No cross-Tenant Runs in v1** — no audited exception to build, and none to get wrong. | **D51**, **D52** |
| **C2a** | Brownfield: hundreds of existing GrafanaOrgs | **Tenant lifecycle `discovered → provisioning → ready → suspended`.** A reconciler creates a **credential-less `discovered` row for every existing GrafanaOrg** — free, so the capability is one click away for all teams. **`discovered → ready` is the explicit admin act that fires D22's synchronous SA provisioning**, so D22 is untouched and we never hold hundreds of unused credentials. One idempotent code path for both backfill and new orgs. Platform SAs use a reserved `graft-platform-` prefix with a do-not-modify display name (a *signal*), backed by a **drift reconciler** (the *control*, since Grafana OSS cannot prevent an OrgAdmin editing them), scheduled rotation, and per-SA metrics: token age, time-to-expiry, last use, drift events. | **D53** |
| **C3** | Run ownership & visibility | **D36 confirmed and supersedes R4.** `user_initiated` Runs are **private to the initiator**, promotable to tenant-shared; **promotion is irreversible** (un-sharing is security theatre). `system_initiated` Runs are **born tenant-shared** — nobody initiated them, so private-by-default would make them invisible to everyone. Archival changes storage tier and mutability, **not** visibility. A de-provisioned Principal's private Runs become **inaccessible in-product**; the end-to-end audit trail (D15, 12 months) is the forensic path, not the UI. | **D54** |
| **C3a** | Approval authority | **Initiator-only in v1**, on top of D14 (re-authenticated, in Grafana) and D23 (check-then-act against the initiator's own Grafana permission). **Accepted consequence, stated plainly:** an offline initiator means the approval is not transferable and the Run expires (D47, ≥72h) — deliberately trading R4's "Bob approves when Alice is offline" rationale for unambiguous attribution. **Revisit metric: expired-approval rate** (same pattern as D24). **`platform_admin` break-glass = read/cancel/suspend in any Tenant, explicitly *not* approve** — separation of duties; the actor who can reach every Tenant must not authorise writes in every Tenant. Every break-glass act is a non-sampled audit record. **Two-person rule deferred** — mutually exclusive with initiator-only by definition. | **D55** |
| **C4** | Role vocabulary & where mappings live | **The IdP authenticates; the harness authorizes.** Roles, verbs and evaluation are entirely ours, in our own tables — satisfying IdP-independence and sidestepping D26's Enterprise-only RBAC finding. **Four roles**: `platform_admin`, `tenant_admin`, `responder`, `viewer`. **`operator` deleted** (see §0.1). **Zero-config default mapping from the Grafana basic role** — essential for brownfield, since hundreds of Tenants cannot each need manual mapping before first use — overridden by explicit Group→Role mapping where an admin wants something different. Roles and verbs are **rows, not code**, so the model is extensible by data change plus a D16 policy version bump. **De-provisioning is TTL-only** (~10 min, D10), with the existing deny-list for incidents; no SCIM, no polling. | **D56** |
| **C5** | Budget & quota scopes | Ceiling chain loses a layer: **`platform ≥ tenant ≥ principal ≥ run`**. At-cap behaviour is **per-scope, not uniform**: per-run → **graceful terminate** emitting the best hypothesis so far; per-principal and per-tenant → **hard stop** (new Runs rejected, in-flight finish); per-connection → **throttle/queue**, never failing the Run, because it protects *customer* infrastructure. **No degrade-to-a-cheaper-model** — model choice is a platform decision driven by evals and availability, and switching mid-Run would silently change the quality characteristics an operator is about to act on. **Monthly reset.** Quotas are platform-set and platform-customisable per Principal and per Tenant; increases are **requested from the UI**, creating a pre-filled, idempotency-keyed service-desk ticket. In-product quota indicator, threshold notification, and platform-side monitoring of consumption, at-cap rejections and request fulfilment. | **D57** |
| **X6** | Schedules as a tenant-scoped resource | **Ceiling on Schedule count per Tenant + minimum interval** (proposed 10 and 1h, pending cost data), platform-customisable. **Versioned policy, never overwritten** (D16). Schedule consumption **counts against the Tenant's monthly quota** — a Schedule is not a budget bypass. **All scheduled Runs are `system_initiated` and therefore structurally read-only (D13)**, which bounds Schedule risk to *cost*, not *blast radius*. Platform-internal timers (infra-memory refresh, SA drift reconciliation) use the same substrate but are not user-facing Schedules and consume no ceiling. | **D58** |

### 0.3 The vocabulary fix (D52)

Full table in [`../../GLOSSARY.md`](../../GLOSSARY.md). The essentials:

| Ours | Key | Maps to | Not to be confused with |
|---|---|---|---|
| **Tenant** | `graft_tenant_id` | **GrafanaOrg**, 1:1 | Mimir/Loki `LGTMTenant` (`X-Scope-OrgID`) |
| **Principal** | `graft_principal_id` | Grafana user / **SlackUser** / bot / schedule | — |
| **Group** | IdP `groups` claim | AD / Keycloak / Auth0 / Entra group | — |
| **Run** | `graft_run_id` | — | "session", "investigation" (one primitive, D36) |
| *(deleted)* | ~~`workspace_id`~~ | — | **SlackWorkspace** (`slack_workspace_id`) |

`slack_enterprise_id`, `slack_workspace_id` and `slack_channel_id` are **attributes and locators, not
scoping columns**. v1 supports a single SlackEnterprise and a single
SlackWorkspace, which is precisely why SlackChannel→Tenant binding carries the
weight: one Slack install serves every Tenant.

### 0.4 Remaining action items (implementation-time, not open questions)

- **Quota numbers** — per-Principal and per-Tenant monthly ceilings need real
  cost data. Same status as D47's expiry duration: mechanism locked, number
  untaken.
- **Schedule defaults** (10/Tenant, 1h minimum) to confirm against expected
  Run cost.
- **Quota-increase path** — ITSM API integration in v1, or pre-filled
  deep-link fallback first.
- **Tenant Directory** replication substrate and staleness budget for the
  cross-region read proxy.
- **Backfill reconciler run-book** — idempotent by design, but the first run
  against hundreds of existing GrafanaOrgs is the one that proves it.
- **Expired-approval rate** instrumentation, as D55's revisit trigger.

---

### 0.5 Audit of the original doc — what was *not* covered by C1–C5

Every explicit "To resolve" bullet under C1–C5 is answered by D49–D58. This
section records what the original briefing raised **outside** those bullets, so
none of it evaporates.

#### One genuine contradiction — **resolved 2026-09-13 as D62**

§5 proposes **"custom instructions exist at two levels — workspace and user,
workspace wins on conflict."** **D16 says the opposite:** configuration is
org-scoped and shared, and per-user variation is an authorisation filter at call
time, *"never a separate per-user configuration."* Per-user custom instructions
are unambiguously per-user configuration.

**D16's absolute is already strained by decisions taken in this session**, which
makes this a narrowing exercise rather than a straight choice:

| Per-Principal setting | Introduced by | Is it really "configuration"? |
|---|---|---|
| `default_graft_tenant_id` (Slack DM resolution) | D51 / D54 | A preference |
| Per-Principal monthly quota | D57 | A limit, not a grant |
| Per-Principal custom instructions | *proposed, undecided* | A preference |

**Proposed resolution (untaken):** narrow D16 to mean *per-user variation of
**tool and authorization** configuration is never separate configuration* —
which was its actual intent, stopping a Principal from holding a private tool
allow-list. Per-Principal **preferences and limits** are a different kind of
thing and are legitimate. Custom instructions then work as §5 proposed: two
levels, **Tenant wins on conflict**, consistent with the Layer-2-over-Layer-3
prompt hierarchy in `../../research/context-management.md`.

**Resolved as D62 (2026-09-13):** the narrowing was taken as proposed.
Custom instructions exist at **both** levels, Tenant winning on conflict. The
distinction that settles it: D16 governs **capability** (what a Principal may
*do*), custom instructions govern **behaviour** (how the agent *replies*) —
different kinds of thing that were sharing one word. The hard rule that keeps
them separable is that **custom instructions are prompt text and can never
grant capability** (D63's layer 4). The two unwritten consequences below are
also now closed: steer/watch as **D64**, web-frontend resolution as **D64**.

#### Two unwritten consequences — now stated

- **Steer vs. watch on a tenant-shared Run** (C3, bullet 2). Resolved by
  composition but never written down: **`viewer` holds no `run:steer` verb**
  (D56) and so can only watch; **`responder` and `tenant_admin` may request
  control** under D32's soft-lock driver model. Approval remains
  initiator-only regardless of who is driving (D55) — **driving is not
  approving.**
- **Tenant resolution for the custom web frontend** (C2, bullet 3). **Moot for
  v1** — D2 dropped the Web UI. When it returns post-v1 it inherits the Slack
  rule shape rather than inventing one: an **explicit Tenant switcher**, with
  the Principal's `default_graft_tenant_id` as the initial selection, and the
  active Tenant carried in the harness token exactly as for every other
  surface.

#### Numbers whose mechanism is locked but whose value is not

| Value | Decision | Proposed |
|---|---|---|
| Per-Principal / per-Tenant monthly quota ceiling | D57 | — needs cost data |
| Schedule count per Tenant | D58 | 10 |
| Minimum Schedule interval | D58 | 1 hour |
| Budget warning threshold | D57 | 80% |
| Approval expiry | D47 (pre-existing) | ≥72h |

#### UX items raised in §5, deferred to a UX session

- Run list scoped to Tenant, filterable "mine / my team / all".
- **Sharing is a link to the live Run, not an export** — consistent with D54's
  irreversible promotion and D32's multi-viewer model, but never decided as
  such.

*(§5's remaining items **are** decided: connection setup is a `tenant_admin`
action distinct from `platform_admin` — D56's `connection:manage`; and
budget/quota indicators are Tenant-scoped and visible — D57.)*

---

## 0A. Inputs carried in from `01-identity-and-access.md`

- **C1 (deployment model) is resolved: option (a)/(c) shape.** D21 confirms
  **the platform owns and operates a single, shared Grafana instance;
  customers are orgs within it.** This is much closer to "internal platform,
  many teams" (option (c) below) than a per-customer-deployment or classic
  multi-tenant-SaaS-with-full-isolation shape — `Tenant` is real but the
  Grafana layer specifically is not siloed per customer. Model `tenant_id` in
  the schema regardless (per the original leaning below), but the "which of
  (a)/(b)/(c) is true" question no longer needs arguing from scratch in that
  session.
- **New input for C2 (Grafana Org ↔ Workspace mapping): Slack Enterprise Grid
  needs a second scoping dimension.** Confirmed live against `docs.slack.dev`
  (2026-09-12, D28): Enterprise Grid workspaces expose a constant
  `slack_enterprise_id`, and **a single human can hold distinct per-workspace
  identities within the same Grid org**, reconciled by Slack via "global user
  IDs." This means `slack_workspace_id` (`slack_workspace_id`) alone is not a stable
  enough key for a Slack-linked principal once a customer's Slack is on Grid.
  **When this session runs, R3's scope model (`Tenant → Workspace → Group →
  Principal`) needs `slack_enterprise_id` recognised as a first-class scoping
  dimension for Slack-linked principals** — keyed by `slack_enterprise_id` (+
  global user id) where present, falling back to `slack_workspace_id` (+ user id) for
  non-Grid, single-workspace installs. This is additive to the existing model
  (an extra identity key, not a new tree layer) but should be designed in from
  the start of this session rather than retrofitted.

Everything else below is unchanged and still open.

---

## 1. Where this came from

The question "what does multi-tenant mean here — is a tenant a user or an org?"
turned out to be four distinct scopes compressed into one word. The stated
reality:

- **Datasource access is tied to the org.**
- **Org access is tied to the user via Azure AD groups.**
- This must be **generic** — not restricted to AD groups; Keycloak, Auth0,
  Entra ID and others must work without code changes.

---

## 2. Proposed scope model (for critique)

```
Tenant            — isolation & billing boundary. Separate data, possibly
                    separate keys, possibly a separate deployment.
  └─ Workspace    — ≈ Grafana Org. Owns CONNECTIONS (datasources, clusters,
                    repos, ticketing), tool configs, policies/rules, workspace
                    custom instructions, budgets. Investigations live here.
       └─ Group   — supplied by the IdP (AD group / Keycloak group / Auth0 org /
                    Entra group). Grants roles within a workspace.
            └─ Principal — the human. Also service principals (webhooks, Slack bot,
                    scheduled runs). **For Slack-linked principals on Enterprise
                    Grid, keyed by `slack_enterprise_id` + global user id, not
                    `slack_workspace_id` + user id — see §0.**
```

Why each layer earns its place:

- **Tenant** — only meaningful if one deployment serves parties who must never
  see each other's data. Determines whether row-level security, per-tenant
  encryption keys, and noisy-neighbour quotas are real requirements or theatre.
  **Per §0, the Grafana layer itself is a single shared instance (D21) — so
  `Tenant` isolation, where it matters, is enforced in our own data layer
  (RLS), not by separate Grafana deployments.**
- **Workspace** — almost certainly needed. It is the unit that **owns
  credentials**, and it maps naturally onto a Grafana Org. It is also the unit of
  cost attribution.
- **Group** — must be an *abstraction*, never "AD group". The mapping
  `IdP claim → harness role` is configuration.
- **Principal** — the canonical identity all surfaces resolve to.

---

## 3. Open questions

### C1 — What is the actual deployment model for v1? — **resolved, see §0**

| Option | Consequence |
|---|---|
| **(a) One deployment per customer**, many workspaces inside | `Tenant` becomes a near-vestigial column; isolation is achieved by deployment. Simplest. |
| **(b) One shared deployment, many customers** (SaaS) | `Tenant` is a live runtime concept: RLS, per-tenant keys, quota isolation, noisy-neighbour protection, tenant-aware rate limiting, per-tenant data-residency. Much more work. |
| **(c) Internal platform, one company, many teams** | `Tenant` is a single row; `Workspace` does all the real work. |

*This is the question that determines how much of the rest is real.* Note the
multi-cloud context (GCP + AliCloud, active-active per cloud to avoid log egress
costs) interacts strongly with (b) — data residency may force per-region tenancy
regardless.

**Resolved (§0): the Grafana layer is (a)/(c)-shaped — one shared, platform-owned
instance, multi-org (D21).** Still model `tenant_id` in the schema from day
one and enforce it via RLS (the cost of the column is near zero; the cost of
adding it later is not) — but the "which deployment model is real" argument
for the Grafana-facing part of the system is settled. Whether the **rest** of
the stack (harness API, Tool Gateway, Postgres, secret store) is deployed
single-tenant-per-customer or shared-SaaS is a separate, still-open
deployment-topology question (tracked in the Decision Register §7).

---

### C2 — Grafana Org ↔ Workspace mapping *(resolved — D51/D52, §0.2)*

Proposed: a Grafana Org maps to a harness Workspace.

**To resolve:**
- What happens when a user belongs to 3 Grafana orgs — 3 workspaces, with an
  explicit switcher? *(Leaning: yes; active workspace is in the harness token;
  no implicit cross-workspace queries, ever.)*
- Is workspace creation automatic on first sight of a Grafana org, or an explicit
  admin action? (Auto-provisioning is convenient but silently creates
  credential-owning entities.)
- How do the **custom frontend** and **Slack** select a workspace, given neither
  has a Grafana org context? Slack channel → workspace mapping? User default?
  **Now sharper per §0: if the Slack workspace is on Enterprise Grid, this
  mapping needs to consider `slack_enterprise_id`, not just `slack_workspace_id`/channel, since
  the same human may have different identities per Grid workspace.**
- Can an investigation ever legitimately span workspaces (e.g. a cross-cloud
  incident touching two orgs' datasources)? If yes, the "never cross workspaces"
  rule needs a deliberate, audited exception.

---

### C3 — Investigation ownership and visibility *(resolved — D54/D55, §0.2)*

*Current leaning:* investigations are **workspace-owned**, not user-owned, with
visibility `private | workspace | link-shared`, defaulting to `workspace`.

Rationale: incident response is a team activity. If Alice starts an RCA and goes
offline, Bob must be able to open it, follow up, and approve the PR. Note this
**contradicts** `docs/research/session.md`, which proposes a `Sessions` table
keyed by `user_id` — that design produces a single-player tool for a
multi-player activity.

**To resolve:**
- Confirm the default visibility.
- Who may *steer* a workspace-visible investigation vs merely watch it? (Couples
  to `02-streaming-and-events.md` B4.)
- Who may *approve* an action — anyone in the workspace with the role, or only
  the initiator? (Two-person rule for high-risk actions?)
- Retention/archival: `session.md` suggests archiving closed investigations to a
  read-only trajectory store. Does archival change ownership or visibility?

---

### C4 — Where do IdP-group → role mappings live? *(resolved — D56, §0.2)*

| Option | Pros | Cons |
|---|---|---|
| **Harness-side config per workspace** — map an abstract `groups` claim to roles, e.g. `roles: { sre-oncall: [investigate, approve_writes] }` | Keeps AD / Keycloak / Auth0 / Entra fully interchangeable (the stated requirement); auditable in Git; no IdP write access needed | Config drift vs IdP reality; another thing to manage |
| **Read roles from the IdP** (custom claims / app roles) | Single source of truth; central governance | Requires IdP-specific configuration per customer; couples us to each IdP's model; the exact thing we're trying to avoid |
| **SCIM sync** | Proper lifecycle incl. de-provisioning | Heaviest to build; not all IdPs configured for it |

*Current leaning:* harness-side config mapping from an abstract `groups` claim,
because IdP-independence is an explicit requirement.

**To resolve:** the canonical role set and permission verbs; whether roles are
purely workspace-scoped or some are platform-scoped (platform-admin vs
workspace-admin); how de-provisioning propagates (token TTL only, or active
revocation).

---

### C5 — Budget and quota enforcement scopes *(resolved — D57/D58, §0.2)*

Token/cost budgets, tool-call limits, and rate limits could be enforced per
**workspace**, per **user**, per **run**, or all three.

*Current leaning:* all three — **workspace is the hard cap and the
billing-attribution unit**; per-run caps prevent a single runaway investigation
(cf. `oversight.md`: max graph depth, per-job cost cap, loop breakers); per-user
caps are mostly a fairness mechanism.

Directly connected: the "control-plane DDoS during incident cascades" risk from
`critique.md` — when 20 alerts fire at once, rate-limit buckets keyed by
workspace stop one team's incident storm from starving another *and* from
saturating the shared Kubernetes control plane. The Tool Gateway is the
enforcement point.

**To resolve:** what happens at cap — hard stop, graceful degrade to a cheaper
model, or queue? (`oversight.md` suggests terminating gracefully and emitting
whatever hypothesis exists so far.) Who can raise a cap, and is it self-service?
Do budgets reset periodically or per-incident?

---

## 4. Cross-cutting consequences to design for *(superseded by `../../design/tenancy-and-scoping.md` §7)*

- **Data model:** `tenant_id` + `workspace_id` on every row, event, span, and
  audit record. Enforced with **Postgres row-level security**, not application
  code alone. **Slack-linked principal rows additionally carry `slack_enterprise_id`
  where the source workspace is on Grid (§0).**
- **Secrets:** namespaced per workspace. A workspace's datasource/cluster/repo
  credentials must be unreachable from another workspace's run, including via a
  compromised agent.
- **Observability:** traces and LLM spans tagged with tenant/workspace so cost
  attribution and per-tenant dashboards work without re-processing.
- **Streaming:** channel/stream names scoped by workspace; subscription authz
  checked per connection (see `02-streaming-and-events.md` §5).
- **Tool Gateway:** resolves credentials *by workspace*, never from ambient
  process config. This is a direct consequence of the no-stdio-MCP rule.

---

## 5. UX implications worth deciding deliberately

- Investigation list scoped to workspace, filterable "mine / my team / all".
- Sharing is a link to the live run, not an export.
- **Custom instructions exist at two levels** — workspace and user. Workspace
  wins on conflict, consistent with the prompt-layer hierarchy in
  `docs/research/context-management.md` (Layer 2 org policy above Layer 3 user
  preferences).
- Connection setup (datasources, clusters, repos) is a **workspace-admin**
  action, distinct from platform-admin.
- Budget/quota indicators are workspace-scoped and visible in the UI (the
  braindump lists "Limits/Quota Indicator" and "Show Token Usage/Budget").

---

## 6. What a good outcome looks like *(all met — see §0)*

1. ~~A definitive answer on the deployment model (C1) and therefore how real
   `Tenant` is.~~ **Resolved for the Grafana layer by D21 — see §0.** Still
   need the equivalent answer for the rest of the stack (harness API, Tool
   Gateway, secret store deployment topology).
2. A workspace-resolution rule for all four surfaces (C2), **now including the
   Grid `slack_enterprise_id` dimension (§0).**
3. An ownership + visibility + approval-authority model for investigations (C3).
4. A role/permission vocabulary and where mappings live (C4).
5. A budget enforcement matrix with defined at-cap behaviour (C5).
6. A one-page data-model sketch showing scoping columns and the RLS strategy.
