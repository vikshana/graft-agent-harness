# Open Question 01 — Identity, Authentication & Downstream Access

> **Status: 🟢 Mostly resolved as of the UX-first design pass.** The original
> briefing (§1–§7 below) is preserved as the historical record of the question;
> the resolutions reached are summarised in §0 with links to the design docs
> that work through the detail. Two items remain genuinely open — see §0.4.

---

## 0. Resolution summary

### 0.1 What changed the shape of this question

Two upstream decisions, made after this briefing was written, resolved several
items here as a side effect rather than requiring them to be argued individually:

- **No Web UI in v1.** Surfaces are **Grafana App Plugin + Slack only** (see
  `../../diagrams/c4-l1-system-context.md`). This makes Grafana the *sole* rich
  surface, which promotes Grafana's identity assertion from "one option among
  several" to "the only strong one we have," and makes A1 blocking rather than
  merely important.
- **A confirmed Grafana platform limitation:** `externalServiceAccounts` does
  not support multi-org Grafana instances. Since workspace = Grafana Org is our
  model, this is not an edge case — see
  `../../design/grafana-authz-delegation.md` revision note and
  `../../design/grafana-mcp-provisioning.md`.

### 0.2 Resolutions, per question

| # | Question | Resolution | Detail |
|---|---|---|---|
| **A1** | How does the Grafana plugin authenticate to the harness? | **(a) Grafana ID token via JWKS (`X-Grafana-Id`, feature toggle `idForwarding`) as primary.** (b) plugin-signed JWT as an explicit, per-workspace, audit-visible fallback — **workspaces on fallback trust cannot approve destructive actions.** (c) `oauthPassThru` is reclassified as an A4 (downstream) mechanism, not an A1 (inbound authn) one. | `../../design/grafana-authz-delegation.md` |
| **A2** | Internal harness session token? | **Yes.** Short-lived (~10 min), run-scoped, audience-restricted to the Tool Gateway, revoked via deny-list + short TTL. The Tool Gateway validates independently — never trusts the agent worker. | `../../design/audit-and-attribution.md` §5.1 |
| **A3** | Slack identity and approval ceiling | **Restrictive, resolved harder than originally framed.** Slack triggers, converses, and *launches* approval via a signed single-use deep link — but **approval itself always happens in Grafana**, never in Slack, since there is no Web UI to round-trip through. | `../../diagrams/c4-l1-system-context.md` J4 |
| **A4** | Downstream credential strategy | **Hybrid, but reframed:** service identity is the default (must work with no user present); user identity is an *upgrade*, enforced via **check-then-act** (authorise as the principal via Grafana's own permission API, execute via a workspace service account) rather than naive pass-through. | `../../design/grafana-authz-delegation.md`, `../../design/grafana-mcp-multi-tenancy.md` |
| **A5** | Operate while the user is offline? | **Yes — confirmed, not just leaning.** `system_initiated` runs are structurally read-only: the run's capability token is minted without any write tool class, so this is enforced by absence of capability, not by a policy check that could be bypassed. | `../../design/audit-and-attribution.md` §2 |
| **A6** | Audit actor model | **Full schema defined**, including a hash-chained, insert-only record, `actor`/`downstream_identity` split, and outward propagation of `run_id` into customer-owned logs (K8s `impersonatedBy`, GitHub commit trailers). | `../../design/audit-and-attribution.md` |
| **(new)** | How is the Grafana-side service account provisioned? | **Imperative, self-service, per-org provisioning** (`POST /api/serviceaccounts` using the admin's own org-scoped session) — **not** `externalServiceAccounts`, which is confirmed broken for multi-org. One mechanism serves both the plugin's own enforcement SA and the `grafana-mcp` tool server's SA. | `../../design/grafana-mcp-provisioning.md` |
| **(new)** | Does one shared `grafana-mcp` server work across workspaces? | **Yes, as one logical service**, provided the credential is attached **per call**, never baked into the process at startup. Per-user variation is resolved *before* the call reaches this layer — the service only ever acts "as the workspace." | `../../design/grafana-mcp-multi-tenancy.md` |

### 0.3 Canonical identity model (§5) — resolved

Lives in **harness Postgres**, JIT-provisioned on first successful IdP login, no
SCIM in v1. A user who exists in Slack but not the IdP is **denied**, not
downgraded to read-only — per-surface leniency here was judged a data-leak risk
greater than the onboarding friction it saves.

### 0.4 Still genuinely open

1. **Minimum Grafana version for `idForwarding`** — feature-toggle status, exact
   header/claims, whether it's GA. This is now **blocking**, not merely
   important, given §0.1. Needs a verification spike, not a design decision.
2. **Compliance regime in scope** (SOC2 / ISO27001 / none yet) — drives audit
   retention and whether approval signatures must be independently verifiable.
3. **Cold-start provisioning** — what happens when a webhook/Slack event is the
   *first* interaction a brand-new workspace has, before any admin has visited
   the plugin to trigger SA provisioning. Leaning: make provisioning a
   mandatory, blocking step of workspace onboarding rather than lazy-on-first-use.
   See `../../design/grafana-mcp-provisioning.md` §9.3.
4. **Does OSS `grafana-mcp` support per-request credential override**, or only a
   startup-time token? Decides whether multi-tenancy (§0.2, last row) needs a
   fork/sidecar or works out of the box. See
   `../../design/grafana-mcp-multi-tenancy.md` §4.

---

## 1. System context *(original briefing — historical)*

We are building an SRE / observability **agent harness**: an API-first backend that
runs LLM agents which investigate production incidents, perform root cause
analysis, and propose (sometimes execute) remediations.

It is consumed through **four surfaces**:

| Surface | Nature | Native credential available |
|---|---|---|
| Custom web frontend | First-party SPA | OIDC/OAuth2 access token from the org IdP |
| **Grafana App Plugin** | Runs inside customer's Grafana; Go plugin backend proxies to us | Grafana `PluginContext` (user login, email, role, org ID); optionally a Grafana-signed ID token; optionally upstream IdP token via `oauthPassThru` |
| **Slack** | Slack app / bot | Slack request signature (authenticates the *workspace*), Slack user ID (not verified as a person) |
| Direct API | Machine clients, webhooks (Grafana Alerting, Alertmanager) | API key / OAuth2 client credentials / webhook shared secret |

> **Superseded:** the custom web frontend is **not in v1** — see §0.1. The table
> above is left as originally written since it is still useful context for the
> post-v1 Web UI.

It acts **downstream** against: Grafana datasources (Prometheus, Loki, Tempo,
Mimir), Kubernetes clusters (GKE, ACK), GitHub, Jira, ServiceNow, PagerDuty /
iLert / ITSI, Harbor, cloud APIs (GCP, AliCloud).

The IdP must be **pluggable**. The initial deployment uses **Azure AD / Entra ID
groups** for access, but Keycloak, Auth0, Okta and others must be supportable
without code changes.

---

## 2. Decisions already locked (constraints for this discussion)

- **D1** Grafana integration goes through the **plugin backend (Go) proxy**, not
  browser → API directly. The custom frontend calls the API directly.
- **D2** Trigger surfaces for v1: UI, Slack, and webhook with a normalised event.
  *(Superseded: UI dropped from v1, see §0.1.)*
- **R1/R2** The agent never calls MCP servers directly. All tool traffic goes
  through a harness-owned **Tool Gateway**, which is a separate service (a
  security boundary, not a library). All MCP servers are streamable-HTTP, never
  stdio — stdio MCP is single-identity by construction. The Tool Gateway is
  therefore the single place where downstream identity is bound.
- **D4** No arbitrary code execution in v1 (sandbox is Phase 2), but the seam
  must exist.

---

## 3. The three concerns to keep separate

Conflating these is the most common failure mode (per `identity.md`):

1. **Authentication** — proving who the caller is, *per surface*.
2. **Identity federation** — mapping each surface's notion of "user" onto one
   canonical internal identity.
3. **Authorisation** — what that canonical identity, and the agent acting on its
   behalf, may see and do downstream.

Skipping (2) yields three disconnected identity spaces (Slack user, Grafana user,
app user) with no consistent RBAC and no coherent audit trail.

---

## 4. Open questions *(original briefing — see §0.2 for resolutions)*

### A1 — How does the Grafana plugin backend authenticate to the harness?

| Option | Mechanism | Pros | Cons |
|---|---|---|---|
| **(a) Grafana ID token via JWKS** | Recent Grafana versions can forward a signed ID token for the logged-in user (`X-Grafana-Id`) to plugin backends; harness verifies against Grafana's JWKS | No shared secrets; genuine per-user assertion; revocable; standard JWT | Requires a Grafana version that supports it (**verify minimum version and whether it needs a feature toggle**); ties us to Grafana as an identity asserter |
| **(b) Plugin-signed JWT, shared secret** | Plugin backend mints a JWT asserting Grafana user + org, signed with a secret shared with the harness | Works on any Grafana version; simple | Shared secret management/rotation; the plugin can assert *any* identity — we're trusting plugin code, not Grafana |
| **(c) OAuth pass-through of upstream IdP token** | Grafana forwards the user's original IdP token (`oauthPassThru`) | Single identity domain end-to-end; downstream systems can validate it too | Only works if Grafana is an OIDC client of the same IdP; token audience/scope issues; not all Grafana auth modes support it |

**Resolved — see §0.2.** (a) primary, (b) fallback with reduced trust and no
destructive-approval rights, (c) moved to A4.

---

### A2 — Does the harness issue its own internal session token?

Proposal: every surface exchanges its native credential for a short-lived
**harness JWT** carrying `{principal_id, tenant_id, workspace_id, roles, surface,
session_id}`.

*Arguments for:* one token format internally; surfaces become thin adapters;
Slack has no bearer token at all, so something must be minted for it; token
lifetime becomes independent of the Grafana/Slack session (a stale Slack link
shouldn't extend agent authority indefinitely); the Tool Gateway has exactly one
credential format to validate.

*Arguments against:* an extra token-issuance/revocation surface to build and
secure; double validation on every request.

**Resolved — see §0.2.** Yes, with lifetime/revocation defined in
`audit-and-attribution.md`.

---

### A3 — Slack identity and Slack's authority ceiling

Slack request signing authenticates the **workspace**, not the person. The
Slack user ID in an event is not a verified assertion about a human in your IdP.

Proposed flow: a one-time "connect your account" OAuth link on first use,
persisting `slack_user_id + slack_workspace_id → principal_id`. Unlinked Slack
users get no access (or read-only).

Sub-question — **can Slack approve destructive actions?**

- *Restrictive (leaning):* Slack may trigger investigations and converse, but
  approval of any destructive/irreversible action must happen in the UI or
  Grafana. Slack's identity chain is the weakest of the surfaces, and Slack
  message actions are relatively easy to socially engineer.
- *Permissive:* Slack approvals allowed, protected by re-auth / a signed
  approval link that round-trips through the web UI.

**Resolved — see §0.2.** Restrictive, and now unambiguous: with no Web UI,
"round-trips through the web UI" becomes "round-trips through Grafana."

---

### A4 — Downstream credential strategy, per target

The central trade-off: **user identity (accurate authz, real attribution) vs
service identity (always available, simpler, needs harness-side policy)**.

| Target | Options | Notes |
|---|---|---|
| Grafana datasources (Prom/Loki/Tempo/Mimir) | `oauthPassThru` as the user; workspace service account | Passthru is cheap here because Grafana already supports it |
| Kubernetes | User's OIDC bearer token; `Impersonate-User`/`Impersonate-Group` headers with harness SA holding `impersonate`; scoped read-only SA + harness policy | User OIDC only works if the cluster trusts the same IdP as your users — often **not** true for AzureAD + GKE/ACK. Impersonation works regardless of user token format |
| GitHub | User OAuth token from vault; **GitHub App acting as a bot** | Leaning bot: PRs should be *visibly* authored by the agent with the human approver recorded, not spoofed as the user |
| Jira / ServiceNow / ITSI | User token; service account | |
| PagerDuty / iLert | Service account (paging is inherently system-initiated) | |
| Cloud APIs (GCP / AliCloud) | Scoped service credentials | User-level delegation rarely available |

*Current leaning:* **hybrid** — user identity where cheaply available (Grafana
passthru, K8s impersonation), scoped **workspace** service account + harness
policy + full audit everywhere else. This matches `identity.md` §5, which
predicts the same hybrid outcome.

**Resolved — see §0.2.** Reframed: service identity is the default (it must work
with no user present, per A5), and user identity is an upgrade via check-then-act
rather than naive delegation. GitHub confirmed as bot-identity.

---

### A5 — Must the harness operate while the user is offline?

Cases: scheduled/periodic RCA; a webhook firing at 03:00 with no human present;
an agent resuming after a multi-hour HITL pause once the user's token has expired.

If **yes**, user-token-based downstream auth is structurally impossible on those
paths — you need a **workspace service identity** plus a distinct
`system-initiated` audit category. This effectively forces the hybrid in A4.

If **no**, every run has a live human with a valid token, and pure delegation
becomes viable.

*Current leaning:* yes, needed — D2 already locks webhook triggers.

**Resolved — see §0.2.** Yes, confirmed. Enforced structurally (no write tool
class exists in a `system_initiated` run's capability token), not by policy check.

---

### A6 — Audit actor model

Proposal: every action record carries
`actor = {principal, on_behalf_of, initiated_by_surface, approval_chain, run_id, trace_id}`,
distinguishing:

- agent acting **autonomously** (system-initiated),
- agent acting **on behalf of** a named human,
- a **human** acting directly.

Per `oversight.md`, non-repudiation matters: when a user approves an agent PR,
their IdP token should be cryptographic proof a human signed off. Target storage
is WORM (object storage with object-lock / append-only index).

**Resolved — see §0.2.** Full schema in `audit-and-attribution.md`. Retention
period still depends on §0.4 item 2.

---

## 5. Canonical identity model (proposed, for critique) — resolved, see §0.3

```
Principal (canonical)
  ├── idp_subject        (Azure AD / Keycloak / Auth0 / Okta `sub`)
  ├── grafana_user + grafana_org_id
  ├── slack_user_id + slack_workspace_id
  └── api_key_ids[]
```

Every request, from any surface, resolves to a `principal_id` **before** it
reaches business logic. Roles are resolved per workspace from IdP group claims
via harness-side config (see `03-tenancy-and-scoping.md`, C4), so the IdP stays
swappable.

---

## 6. What a good outcome looks like *(met — see §0.2)*

1. A per-surface authentication decision (A1, A3) with named fallbacks. ✅
2. A yes/no on the internal harness token (A2), with lifetime and revocation. ✅
3. A filled-in credential strategy table (A4) with a rationale per target. ✅
4. A clear statement of what autonomous, human-absent runs may do (A5). ✅
5. An audit record schema (A6). ✅
6. Confirmation that the Tool Gateway is the sole enforcement point, and what it
   must validate on every call. ✅ — see `grafana-mcp-multi-tenancy.md`.

---

## 7. Things to verify before deciding (do not assume) — status

- Grafana ID-token forwarding to plugin backends: minimum version, feature-toggle
  status, exact header, JWKS endpoint, claim set. **Still open — §0.4 item 1.**
- Grafana `oauthPassThru` behaviour for each datasource type we care about.
  **Still open**, now scoped narrowly to datasources that must see the end user.
- Whether Slack's 2026 streaming/interaction APIs change any identity assumptions
  (the research doc asserts new streaming APIs — verify independently). **Open,
  low priority** given Slack's reduced authority ceiling (A3).
- Kubernetes impersonation: the exact RBAC needed, audit-log appearance, and
  whether GKE and ACK both behave the same way. **Still open.**
- MCP authorisation spec status (OAuth 2.1 / RFC 9728 protected-resource
  metadata) — note this authenticates *client → MCP server*, and does **not**
  provide downstream K8s identity. Two separate hops. **Still open.**
- **New:** does OSS `grafana-mcp` support per-request credential override? —
  §0.4 item 4.
- **New:** does Org Admin carry Grafana service-account-management rights on
  Cloud/hardened installs? — `grafana-mcp-provisioning.md` §7.
