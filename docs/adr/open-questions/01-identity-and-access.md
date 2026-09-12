# Open Question 01 — Identity, Authentication & Downstream Access

> **Status: 🟢 Fully resolved for v1 (fourth pass, 2026-09-12).** The original
> briefing (§1–§7 below) is preserved as the historical record; §0 summarises
> resolutions, §0.5 the interview round, §0.6 a live-verification pass, and
> **§0.7 records the final stakeholder decisions that closed every remaining
> item** — nothing in this track blocks moving on.

---

## 0. Resolution summary

### 0.1 What changed the shape of this question

Three upstream facts, confirmed after this briefing was written, resolved most
items here as a side effect rather than requiring them to be argued
individually:

- **No Web UI in v1.** Surfaces are **Grafana App Plugin + Slack only** (see
  `../../diagrams/c4-l1-system-context.md`). Makes Grafana the *sole* rich
  surface and A1 blocking rather than merely important.
- **`externalServiceAccounts` does not support multi-org Grafana** (confirmed
  by a Grafana maintainer). Irrelevant to us regardless, once the next point
  is factored in.
- **The platform owns the Grafana instance; customers are orgs within it**
  (confirmed in the interview round, §0.5). This is the single biggest
  simplification in the whole identity track — it removes the dependency on a
  customer admin's session/rights from every provisioning flow in this
  document.

### 0.2 Resolutions, per original question

| # | Question | Resolution | Detail |
|---|---|---|---|
| **A1** | How does the Grafana plugin authenticate to the harness? | **(a) Grafana ID token via JWKS (`X-Grafana-Id`, feature toggle `idForwarding`) as primary**, running on the **latest Grafana release** since we operate the instance ourselves (§0.5 Q2) — no customer-version negotiation. (b) plugin-signed JWT as an explicit, audit-visible fallback — **fallback trust cannot approve destructive actions.** (c) `oauthPassThru` reclassified as A4. | `../../design/grafana-authz-delegation.md` |
| **A2** | Internal harness session token? | **Yes.** Short-lived (~10 min), run-scoped, audience-restricted to the Tool Gateway (formalised as an OAuth 2.1 / RFC 8707 token — D19), independently validated. | `../../design/audit-and-attribution.md` §5.1, `../../design/mcp-authorization-server.md` |
| **A3** | Slack identity and approval ceiling | **Restrictive.** Slack triggers, converses, *launches* approval via a signed single-use deep link — **approval always happens in Grafana.** Account linking upgraded to **Sign in with Slack (OIDC)**. Verified against current `docs.slack.dev` (§0.6 item 5). | `../../diagrams/c4-l1-system-context.md` J4, `../../design/slack-identity-and-surface.md` |
| **A4** | Downstream credential strategy | **Hybrid, service-identity-by-default.** User identity is an upgrade via **check-then-act**, performed by the **Tool Gateway itself** (not the plugin backend — resolved in the interview, §0.5 Q7). Slack-initiated and system-initiated runs are always bounded by the workspace SA's own role — no per-user check for either. **The revisit trigger metric is now accepted (§0.7 item 1).** | `../../design/grafana-authz-delegation.md` §3 |
| **A5** | Operate while the user is offline? | **Yes, confirmed.** `system_initiated` runs are structurally read-only — the capability token is minted without any write tool class. | `../../design/audit-and-attribution.md` §2 |
| **A6** | Audit actor model | **Full schema defined.** Retention **resolved to 12 months minimum / 3 months hot**, driven by the confirmed compliance regime, **PCI-DSS** (§0.5 Q3) — which also adds a PAN-scrubbing requirement, **implementation now deferred to the Evals & Benchmarks session (§0.7 item 3)**. | `../../design/audit-and-attribution.md` §7 |
| **(new)** | Grafana-side service account provisioning | **Fully platform-internal, synchronous at workspace creation**, using a platform-level Grafana Server Admin credential — not a customer admin's session at all, now that the platform-owns-Grafana fact is confirmed. Eliminates the cold-start gap outright. **Blast-radius/rotation policy for that credential is the platform team's concern, not the harness's (§0.7 item 2).** | `../../design/grafana-mcp-provisioning.md` |
| **(new)** | One shared `grafana-mcp` server across workspaces? | **Yes**, credential attached per call, never baked in at startup. **Confirmed against the real implementation, and the header-collision it surfaced is now a locked decision (§0.6 item 3).** | `../../design/grafana-mcp-multi-tenancy.md` |
| **(new)** | Where does the MCP Authorization Server live? | **Separate logical component from the Tool Gateway** (which is Resource-Server-only), co-located with the harness API in v1. Harness-owned broker in front of the pluggable IdP. | `../../design/mcp-authorization-server.md` |

### 0.3 Canonical identity model (§5) — resolved, with one Grid caveat

Lives in **harness Postgres**, JIT-provisioned on first successful IdP login,
no SCIM in v1. A Slack user with no IdP account is **denied**, not downgraded
to read-only. **Caveat confirmed this session (§0.6 item 5):** if a customer's
Slack workspace is part of an **Enterprise Grid**, `slack_workspace_id` alone
is not a stable enough key — Grid introduces a constant `enterprise_id` and
"global user IDs" valid across every workspace in the org. The model should key
Grid-linked principals by `enterprise_id` (+ global user id) where present,
falling back to `team_id` (+ user id) for non-Grid workspaces. Feeds
`03-tenancy-and-scoping.md`, where this has now been flagged directly (D28).

### 0.4 Deployment fact that supersedes several "must verify" items

**The platform owns the Grafana instance; customers are orgs within a single
shared instance.** Confirmed in the interview round (§0.5 Q1, Q5). This means:

- We choose the Grafana version. **Decision: run latest** (§0.5 Q2) — resolves
  the former "blocking verification" on `idForwarding` version support into a
  simple "verify latest supports it, then ship," not a customer negotiation.
  **Now actually verified — see §0.6 item 1.**
- "Does Org Admin have SA-management rights on Cloud/hardened installs?" is
  **moot** — we are Server Admin of our own instance.
- The cold-start provisioning gap (previously open) **no longer exists** —
  provisioning happens synchronously at workspace creation, before any
  customer or webhook ever arrives.

### 0.5 Interview round — resolved this session

| Q | Asked | Answer | Consequence |
|---|---|---|---|
| Q1 | Grafana OSS, Enterprise, Cloud, or mixed? | **OSS** — and platform-owned, single shared instance, multi-org (see §0.4) | Resolves most of A1's version/edition uncertainty; simplifies `grafana-authz-delegation.md` §5 to "verify OSS reachability of the permission-evaluation endpoint," which we can test ourselves |
| Q2 | Minimum Grafana version floor? | **Latest** | Removes the "minimum version" negotiation entirely — a pure verify-then-ship task |
| Q3 | Compliance regime? | **PCI-DSS** | Retention set to 12mo/3mo-hot; new PAN-scrubbing requirement added to `audit-and-attribution.md` §7.1; reinforces (doesn't change) the step-up/least-privilege/tamper-evidence designs already in place |
| Q4 | Comfortable asking customers to grant elevated SA roles for write tools? | **Yes, expected — but start read-only, expand with confidence** | Confirms D16's step-up flow as the correct default-narrow posture; no architecture change, validates existing design |
| Q5 | Block onboarding on SA provisioning, or lazy-provision? | **"Whatever makes the journey better"** — combined with Q1's platform-ownership fact, this made **synchronous provisioning at workspace creation** the obvious answer, not a trade-off | Eliminates the cold-start gap; simplifies `grafana-mcp-provisioning.md` substantially |
| Q6 | SA lifecycle on tool/server disable? | **Full removal (SA + token deleted) when the whole Grafana MCP server is disabled**; role recomputed to minimum on individual tool disable | `grafana-mcp-provisioning.md` §4 |
| Q7 | Check-then-act: harness or plugin backend? | **Harness (Tool Gateway)** | Resolves former open question 1 in `grafana-authz-delegation.md`; also the only option compatible with Slack-triggered runs having no plugin in the path |
| Q8 | Slack-initiated Grafana access: per-user check or workspace-SA-ceiling? | **Workspace-SA-ceiling — simpler path, revisit after PoC feedback** | `grafana-authz-delegation.md` §3.6; revisit trigger **accepted 2026-09-12, §0.7 item 1** |

### 0.6 Live-verification pass (2026-09-12) — tested, not researched

Rather than rely on documentation alone, this pass actually ran Grafana OSS
`latest` in a disposable container, cloned and read the real `mcp-grafana` and
`langchain-mcp-adapters` (+ its `mcp` SDK dependency) source, and fetched
current `docs.slack.dev` pages.

1. **`idForwarding` reachability — confirmed.** Grafana OSS `latest` resolves
   to **v13.0.2**, and ships with `featureToggles.idForwarding: true` enabled
   by default. The relevant signing-key endpoint is **`/api/signing-keys/keys`**
   (returns live ES256 JWKS-shaped keys), **not** `/.well-known/jwks.json`
   (404s). `grafana-authz-delegation.md` and D9 should name the correct
   endpoint.
2. **`/api/access-control/user/permissions` reachability in OSS — confirmed**,
   200 with full RBAC data. Reachable via **either SA-token Bearer auth or
   session-cookie auth** (confirmed against Grafana's own SA-token debugging
   docs, which use exactly this endpoint with `Authorization: Bearer
   glsa_...`); plain Basic Auth (username/password) specifically 404s.
   Separately, `POST /api/access-control/roles` (custom role creation) **404s
   in OSS** — confirms **custom-role evaluation is Enterprise-only**,
   validating the doc's planned fallback to basic-role (Viewer/Editor/Admin)
   checks as not just a fallback but the only option available to us in OSS.
3. **Does OSS `grafana-mcp` support per-call credential override? — resolved
   and locked, including the header-collision it surfaced.** The real
   implementation supports `GRAFANA_FORWARD_HEADERS` (forwards an
   allow-listed set of headers from each **incoming** request to every
   outbound Grafana call, verbatim), and its internal Grafana client cache is
   genuinely keyed by `{url, apiKey, username, password, orgID,
   forwardedHeaders}` — not a single global client.
   **The downstream Grafana credential is, as expected, a Service Account
   token sent as `Authorization: Bearer glsa_...`** (confirmed against
   Grafana's own docs) — there was never any doubt that MCP-to-Grafana auth
   works via SA token; the open question was purely about *how a different
   SA token reaches `grafana-mcp` on each call*, given `grafana-mcp`'s own
   optional caller-authentication (`MCP_GRAFANA_SERVER_TOKEN`) **also** wants
   the `Authorization` header, for the unrelated purpose of authenticating the
   Tool Gateway's own calls into `grafana-mcp`. Because Grafana only accepts
   an SA token on `Authorization` (never a custom header — `grafana-mcp`
   forwards header names verbatim, it doesn't translate them), the two uses
   of `Authorization` cannot coexist on one request; the codebase itself
   detects this and refuses to start if both are configured.
   **Locked decision (2026-09-12):** drop `grafana-mcp`'s built-in caller-auth
   and protect the Tool Gateway↔`grafana-mcp` hop via **network isolation**
   instead (private network / mTLS / service-mesh policy), freeing
   `Authorization` to carry only the per-workspace Grafana SA token,
   forwarded verbatim end-to-end. See `grafana-mcp-multi-tenancy.md` §5/§6
   decision 2 and D18.
4. **Does `langchain-mcp-adapters` perform RFC 9728 discovery? — resolved.**
   The library itself does not implement discovery — it exposes a generic
   `auth: httpx.Auth | None` hook. Its dependency, the official `mcp` Python
   SDK, ships `mcp.client.auth.oauth2.OAuthClientProvider`, which **does**
   implement full RFC 9728 protected-resource-metadata discovery,
   401-triggered re-discovery, PKCE, and token refresh — a drop-in `auth=`
   value, not a gap we need to fill ourselves. Feeds
   `mcp-authorization-server.md` §7.
5. **Sign in with Slack / Socket Mode / Enterprise Grid — verified against
   live `docs.slack.dev`** (previously recollection-based, per the prior
   revision of `slack-identity-and-surface.md`). Sign in with Slack's OIDC
   flow (`openid`/`email`/`profile` scopes, JWKS-verifiable `id_token`)
   confirmed as described. Socket Mode confirmed as described, **plus a new
   fact**: *"Apps using Socket Mode are not currently allowed in the public
   Slack Marketplace"* — relevant if there's ever Marketplace-distribution
   ambition. Enterprise Grid confirmed to introduce a constant `enterprise_id`
   distinct from `team_id`, plus "global user IDs" valid across every
   workspace in the org — see §0.3's caveat.

### 0.7 Final stakeholder decisions (2026-09-12) — closes this track

All three items that remained after the live-verification pass were resolved
by direct product/stakeholder decision this session, not further research:

1. **PoC feedback trigger for Q8's simplification — accepted as
   recommended.** Metric: track denials where a Slack-triggered action would
   have succeeded under the *linked user's* actual Grafana role but failed at
   the workspace SA's role; revisit the always-workspace-SA-ceiling decision
   (D24) if that rate exceeds an agreed threshold or a customer explicitly
   complains. Locked in `grafana-authz-delegation.md` §7 and D24.
2. **Blast radius / rotation policy for the platform Grafana Server Admin
   credential — out of scope for the harness.** This is already handled by
   the platform team as part of their existing credential/secret-management
   practice; it is not a harness-project decision or open item. Removed from
   this track's open questions; noted as explicitly out of scope in D22 and
   the Decision Register §7.
3. **PAN-scrubbing implementation — deferred to the Evals & Benchmarks
   deep-dive session.** The *requirement* (D25, driven by PCI-DSS) remains
   locked; only the Luhn-check-backed detector's design and build are
   deferred to that session, alongside the related D8b eval-sink-scrubbing
   tension, since they're the same piece of work.

**Nothing remains open in this track that blocks proceeding to L2 Containers.**

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

> **Superseded:** the custom web frontend is **not in v1** (§0.1). More
> significantly, **"Grafana App Plugin" here implicitly assumed customer-hosted
> Grafana — also superseded.** The platform owns the Grafana instance;
> customers are orgs within it (§0.1, §0.4).

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
- **D2** Trigger surfaces for v1: **Grafana App Plugin and Slack** (UI dropped).
- **R1/R2** The agent never calls MCP servers directly. All tool traffic goes
  through a harness-owned **Tool Gateway** — a separate service, not a library.
  All MCP servers are streamable-HTTP, never stdio.
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

## 4. Open questions *(original briefing — see §0.2/§0.5/§0.6/§0.7 for resolutions)*

### A1 — How does the Grafana plugin backend authenticate to the harness?

**Resolved — see §0.2, §0.5 Q1/Q2, §0.6 item 1.** ID token via JWKS-equivalent
(`/api/signing-keys/keys`), on latest Grafana, which we operate ourselves —
now live-tested, not just planned.

### A2 — Does the harness issue its own internal session token?

**Resolved — see §0.2.** Yes, formalised under D19.

### A3 — Slack identity and Slack's authority ceiling

**Resolved — see §0.2, §0.6 item 5.** Restrictive; Sign in with Slack for
linking, verified against current Slack docs.

### A4 — Downstream credential strategy, per target

**Resolved — see §0.2, §0.5 Q7/Q8, §0.6 item 3, §0.7 item 1.** Hybrid;
check-then-act performed by the Tool Gateway; Slack/system-initiated always at
workspace-SA ceiling with an accepted revisit trigger; per-call SA-token
attachment to `grafana-mcp` confirmed feasible and its one header collision
resolved by a locked network-isolation decision.

### A5 — Must the harness operate while the user is offline?

**Resolved — see §0.2.** Yes, structurally enforced.

### A6 — Audit actor model

**Resolved — see §0.2, §0.5 Q3/Q6, §0.7 item 3.** Full schema; retention set
by PCI-DSS; PAN-scrubbing implementation deferred to the Evals session.

---

## 5. Canonical identity model — resolved, see §0.3

```
Principal (canonical)
  ├── idp_subject        (Azure AD / Keycloak / Auth0 / Okta `sub`)
  ├── grafana_user + grafana_org_id
  ├── slack_user_id + slack_workspace_id (or enterprise_id on Grid — §0.3)
  └── api_key_ids[]
```

---

## 6. What a good outcome looks like *(met)*

1. A per-surface authentication decision (A1, A3) with named fallbacks. ✅
2. A yes/no on the internal harness token (A2), with lifetime and revocation. ✅
3. A filled-in credential strategy table (A4) with a rationale per target. ✅
4. A clear statement of what autonomous, human-absent runs may do (A5). ✅
5. An audit record schema (A6), with retention resolved. ✅
6. Confirmation of the Tool Gateway as sole enforcement point. ✅

---

## 7. Things to verify before deciding — status, see §0.6/§0.7 for the current list

Superseded by §0.6 (live-verified) and §0.7 (final decisions). Kept briefly
here for continuity with the original briefing:

- Grafana ID-token forwarding: **verified this session (§0.6 item 1)** —
  enabled by default on latest OSS, correct endpoint identified.
- Grafana `oauthPassThru` behaviour: still open, narrowly scoped.
- Slack platform mechanisms beyond `ai/agents`/`ai/agent-governance`:
  **verified this session (§0.6 item 5)**.
- Kubernetes impersonation specifics: still open.
- MCP authorisation spec status: resolved by D19; `langchain-mcp-adapters`
  discovery support **verified this session (§0.6 item 4)**.
- PoC feedback trigger, credential blast-radius, PAN-scrubbing: **all closed
  by stakeholder decision, §0.7.**
