# Q: I want to build an sre/observability agent harness, which will be served via APIs, two frontend, custom and grafana plugin app, and integration with Slack so the harness can used from from Slack. What identity mechanism we need to have? 

## A:

Good question — this is the kind of system where identity needs to work in three directions at once: who the human is, what surface they came through, and what the agent is allowed to do on their behalf downstream. Here's how I'd break it down.

**1. Separate three concerns that are easy to conflate**
- **Authentication** — proving who the caller is, per surface.
- **Identity federation** — mapping every surface's notion of "user" to one canonical internal identity.
- **Authorization** — what that canonical identity (and the agent acting for them) is allowed to see or do.

Skipping the federation step is the most common mistake — you end up with three disconnected identity spaces (Slack user, Grafana user, app user) and no consistent way to apply permissions or produce an audit trail.

**2. Per-surface authentication**

- **Custom frontend**: standard OIDC/OAuth2 against your IdP (Okta, Azure AD, Auth0, etc.), issuing short-lived JWT access tokens to your API.
- **Grafana app plugin**: Grafana's backend plugin SDK passes a `PluginContext` on every request containing the logged-in user (login, email, role, org ID) — you don't need a separate login flow inside the plugin. For calls the plugin makes back to *your* harness API, sign a short-lived JWT asserting that Grafana user + org and verify it server-side (shared secret or JWKS). If the agent needs to query Grafana datasources with the user's own permissions (not a shared service account), Grafana supports OAuth pass-through (`oauthPassThru`) to forward the logged-in user's token to the datasource call.
- **Slack**: use "Sign in with Slack" / OAuth on first use to link the Slack user ID + workspace to your canonical identity (a one-time "connect your account" flow). Every inbound Slack event must be verified via Slack's request signing secret — that's authenticating the *workspace*, not the user, so the linked-identity step is what gets you the actual person.
- **Direct API access**: OAuth2 client-credentials or API keys for machine clients, OIDC for humans hitting the API directly.

**3. Canonical identity mapping**

Maintain an identity table like `(canonical_user_id, idp_subject, grafana_login, slack_user_id, slack_workspace_id)`. Every request, regardless of surface, resolves to a canonical ID before it touches business logic. This is what makes RBAC, personalization, and audit logging consistent instead of three separate systems.

**4. Authorization — and treat "read" and "act" as different tiers**

SRE agents are unusual because they often don't just answer questions, they can also *do* things (silence an alert, restart a pod, trigger a runbook, page someone). Use RBAC/ABAC scoped by environment (prod vs staging), data source, and action type, and require step-up confirmation for anything destructive or irreversible — e.g., the agent proposes the action, but a human has to explicitly confirm in Slack/UI before it executes. Don't let "the agent already has a valid session" substitute for "this specific action is authorized."

**5. The agent's own service identity**

The harness itself needs credentials to call Prometheus/Loki/Tempo, PagerDuty, the Kubernetes API, etc. Two real options:
- **Single service account + app-level enforcement**: simpler to build, but the agent has broad blast radius and you're trusting your own authz code entirely.
- **On-behalf-of / token exchange (OAuth token exchange, RFC 8693)**: downstream systems enforce the actual user's permissions natively, which is safer but only works if those systems support delegated tokens — many SRE tools don't, so in practice you'll likely end up with a hybrid: pass-through where supported (Grafana datasources), service-account-plus-authz-check elsewhere.

**6. Propagate identity end-to-end for audit**

Every tool call the agent makes should carry the originating canonical user ID, surface, and a trace/session ID through the whole chain. For an SRE tool this isn't optional — "who told the agent to restart that deployment, from where, when" needs to be reconstructable after the fact.

**7. Token lifecycle**

Short-lived JWTs for the harness's internal session tokens, with refresh and revocation, independent of how long the Slack/Grafana session lasts — you don't want a stale Slack link or an old Grafana session implicitly extending the agent's authority indefinitely.

If it'd help, I can sketch this as an architecture diagram (surfaces → identity federation → authz → agent → downstream tools) — just say the word.
