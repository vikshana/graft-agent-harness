# Open Question 03 — Tenancy, Scoping & Ownership

> **Purpose of this document.** Self-contained briefing for a dedicated deep-dive
> session. Nothing here is decided.
>
> Related: `01-identity-and-access.md` (who the principal is),
> `02-streaming-and-events.md` (who may subscribe to a run).
>
> **Why this one is urgent:** every other decision writes rows, events, spans and
> audit records. If the scoping columns and the enforcement mechanism aren't
> settled early, retrofitting isolation is one of the genuinely expensive
> rewrites. It is cheap now and brutal later.

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
                    scheduled runs).
```

Why each layer earns its place:

- **Tenant** — only meaningful if one deployment serves parties who must never
  see each other's data. Determines whether row-level security, per-tenant
  encryption keys, and noisy-neighbour quotas are real requirements or theatre.
- **Workspace** — almost certainly needed. It is the unit that **owns
  credentials**, and it maps naturally onto a Grafana Org. It is also the unit of
  cost attribution.
- **Group** — must be an *abstraction*, never "AD group". The mapping
  `IdP claim → harness role` is configuration.
- **Principal** — the canonical identity all surfaces resolve to.

---

## 3. Open questions

### C1 — What is the actual deployment model for v1?

| Option | Consequence |
|---|---|
| **(a) One deployment per customer**, many workspaces inside | `Tenant` becomes a near-vestigial column; isolation is achieved by deployment. Simplest. |
| **(b) One shared deployment, many customers** (SaaS) | `Tenant` is a live runtime concept: RLS, per-tenant keys, quota isolation, noisy-neighbour protection, tenant-aware rate limiting, per-tenant data-residency. Much more work. |
| **(c) Internal platform, one company, many teams** | `Tenant` is a single row; `Workspace` does all the real work. |

*This is the question that determines how much of the rest is real.* Note the
multi-cloud context (GCP + AliCloud, active-active per cloud to avoid log egress
costs) interacts strongly with (b) — data residency may force per-region tenancy
regardless.

*Current leaning:* model `tenant_id` in the schema from day one and enforce it,
but ship v1 in whichever of (a)/(c) is true, with exactly one auto-provisioned
tenant. The cost of the column is near zero; the cost of adding it later is not.

---

### C2 — Grafana Org ↔ Workspace mapping

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
- Can an investigation ever legitimately span workspaces (e.g. a cross-cloud
  incident touching two orgs' datasources)? If yes, the "never cross workspaces"
  rule needs a deliberate, audited exception.

---

### C3 — Investigation ownership and visibility

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

### C4 — Where do IdP-group → role mappings live?

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

### C5 — Budget and quota enforcement scopes

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

## 4. Cross-cutting consequences to design for

- **Data model:** `tenant_id` + `workspace_id` on every row, event, span, and
  audit record. Enforced with **Postgres row-level security**, not application
  code alone.
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

## 6. What a good outcome looks like

1. A definitive answer on the deployment model (C1) and therefore how real
   `Tenant` is.
2. A workspace-resolution rule for all four surfaces (C2).
3. An ownership + visibility + approval-authority model for investigations (C3).
4. A role/permission vocabulary and where mappings live (C4).
5. A budget enforcement matrix with defined at-cap behaviour (C5).
6. A one-page data-model sketch showing scoping columns and the RLS strategy.
