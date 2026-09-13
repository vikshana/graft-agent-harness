# Slack — Newer Platform Mechanisms and What They Change

> **Status: 🟢 Verified against live `docs.slack.dev` (2026-09-12).** Answers: do
> newer Slack app mechanisms (beyond classic Bolt + Events API webhooks) change
> the identity stance in `01-identity-and-access.md` A3 / D14?
>
> **All of §1–§3 are now grounded in fetched content from `docs.slack.dev`**
> (fetched live this session for §1's items, and in an earlier session for
> §2–3's `ai/agents` / `ai/agent-governance` pages) — no part of this document
> is recollection-based anymore.

---

## 1. Four platform mechanisms — verified live, 2026-09-12

### 1.1 Sign in with Slack (OpenID Connect) — the one that matters for identity

**Confirmed against `docs.slack.dev/authentication/sign-in-with-slack`.**
Classic Slack app installation (`oauth.v2.access`) authorises an *app*, not a
*login*. Separately, Slack supports **"Sign in with Slack,"** an OIDC flow
built on top of OAuth 2.0: the client redirects to a special
`/openid/connect/authorize` endpoint (not `/oauth/v2/authorize`), requests the
**`openid`, `email`, `profile`** scopes, and exchanges the resulting code via
**`/openid.connect.token`** (not `oauth.v2.access`) for a standard OpenID
response whose `id_token` carries `iss`/`aud`/`sub`/`email` claims,
verifiable against Slack's published JWKS (discoverable via Slack's OpenID
Well-Known endpoint) — structurally identical in strength to what our IdP
already gives us. User info can be refreshed via `openid.connect.userInfo`.

**This upgrades our account-linking step, confirmed, not assumed.** The
original A3 proposal was a generic *"connect your account, one-time OAuth
link."* Sign in with Slack is the same idea using Slack's own supported
primitive — verified `sub`, standard claims, same verification code path as
D9's Grafana ID-token check.

**Recommendation stands, now verified: use it for the one-time link, not a
bespoke OAuth dance.**

### 1.2 Socket Mode — verified, plus a new fact relevant to distribution

**Confirmed against `docs.slack.dev/apis/events-api/using-socket-mode`.**
Outbound WebSocket instead of a public HTTPS webhook — an infrastructure
decision, not an identity one, as previously stated. The WebSocket URL is
obtained per-connection via `apps.connections.open` and refreshes regularly;
requires the app to use "granular permissions" (true for any app created
since December 2019).

**New fact, not previously known:** *"Apps using Socket Mode are not currently
allowed in the public Slack Marketplace."* This has no bearing on D14 or
identity, but is a real constraint worth flagging now if there's ever an
ambition to list this integration on the Slack Marketplace — Socket Mode and
Marketplace distribution are presently mutually exclusive per Slack's own
docs, so that trade-off would need to be made consciously if it comes up.

### 1.3 Org-wide (Enterprise Grid) app installs — verified, with a concrete
identity-model consequence

**Confirmed against `docs.slack.dev/enterprise/developing-for-enterprise-orgs`.**
Provisioning granularity across a Grid is not just an infrastructure detail —
it introduces a genuine identity-model fact: workspaces in an **Enterprise
Grid** org expose a constant, unique **`enterprise_id`** (via `auth.test`,
`conversations.info`, `team.info`), and a single human can hold **an identity
in Workspace A and a separate one in Workspace B** within the same Grid, which
Slack reconciles via **"global user IDs"** valid across every workspace in the
org.

**Consequence for `01-identity-and-access.md` §5's canonical identity model:**
`slack_workspace_id` (`team_id`) alone is **not sufficient identity
granularity** for a Grid-linked principal — the same human can appear under
different `team_id`s within one Grid org, and Slack's own guidance is to key
data on `enterprise_id` once an app is in Grid territory. The canonical model
should key Grid-linked principals by `enterprise_id` (+ global user id) where
present, falling back to `team_id` (+ user id) for non-Grid, single-workspace
installs. Feeds `03-tenancy-and-scoping.md` directly (see its open question 2,
below).

---

## 2. What `docs.slack.dev/ai/agents` actually says — verified

Fetched directly. This is Slack's conceptual definition of what they mean by
"agent," and it's precise enough to matter for our vocabulary and design:

> An AI agent is a partially autonomous system that can operate independently
> over extended periods, using various tools to accomplish complex tasks.
> ...**Autonomous within defined boundaries**: The defining characteristic of
> an agent is that it can decide what to do next without a human prompting
> each step. The agent should understand the boundaries of its authority and
> recognize when a decision exceeds those boundaries; it can then pause for
> human input rather than guess.

And, critically, a taxonomy that draws a hard line:

> **Agents are not just... Assistants**: An assistant is a conversational and
> reactive tool. It responds to a question or prompt with language
> understanding and reasoning, **but it cannot take autonomous actions or
> decide what to do next.**

**Consequence for us:** in Slack's own vocabulary, what we're building is an
**Agent**, not an "Assistant" — even though it consumes the Assistant
*container* APIs (thread status, suggested prompts) for its UI. Worth being
precise about this distinction in any Slack Marketplace listing or app
description, since Slack reviewers will read it through this exact lens.

The page also states three "core principles" that read as independent
confirmation of decisions we'd already made from the identity/audit side:

1. *"Any action with real-world output... should require explicit human
   confirmation."* — D13/D14.
2. *"Agents are available where people are already working, but not
   disruptive."* — J2's "conversational surface, not a notification channel."
3. *"Agents are not inherently safe... It is the duty of every developer to
   build guardrails, permissions, and human-in-the-loop checkpoints as
   engineering requirements, not afterthoughts."* — the entire premise of D7's
   Tool Gateway.

None of this is a new *authentication* mechanism. It's Slack's product
philosophy for agents, and it happens to agree with the architecture we
already derived independently from the identity/audit chain work.

---

## 3. What `docs.slack.dev/ai/agent-governance` actually says — verified, and this is the useful one

**Important framing correction:** this page is a **governance and UX
framework built on existing Slack primitives** (OAuth scopes, Block Kit, the
Assistant API, the Audit Logs API) — it is **not** a new authentication
mechanism, and nothing on it changes D14. But three things on it are directly
actionable for our design.

### 3.1 Confirms our bot-identity principle, independently, for Slack itself

> **Clear agent identity**: The agent should be clearly distinguishable from a
> human at all times. An agent that masquerades as a human user breaks trust
> and complicates auditability.

We already apply this to GitHub (D11: bot identity, never impersonating the
user). **This extends it to the Slack surface itself** — our Slack app must
never present as, or be mistaken for, a human teammate. Worth stating as an
explicit UX rule alongside D11 rather than assuming it's implied.

### 3.2 Confirms D13/D14, in Slack's own words

> **Checkpoints**: Approval gates before the agent creates, sends, or deletes
> anything.

No new information for us — but useful as external validation that the
restrictive HITL stance isn't an idiosyncratic choice, it's what the platform
vendor itself prescribes.

### 3.3 Their audit guidance is complementary to ours, not a substitute

> Log which channels were accessed, what actions were taken, **who triggered
> the request**, and what model was used... Use the **Audit Logs API** to keep
> a record of admin-level changes (e.g., exclusion settings, configuration
> changes).

**Read the scope carefully: the Audit Logs API is admin-level org changes
only** — installs, exclusions, config edits. It does **not** give per-tool-call
granularity for what an agent actually did inside a conversation. It's a
useful *additional* signal for a customer's Slack admin (e.g., confirming when
our app was installed/excluded), but it is not, and cannot be, a substitute for
our own audit chain (D15/`audit-and-attribution.md`), which is the only place
per-action attribution actually lives.

### 3.4 Two concrete, reusable platform mechanisms — new to our design

**The progressive-trust Block Kit pattern:**

> Start with confirmations for every new capability. As the user selects
> "Always allow" for specific action classes, remove the friction for those
> actions.

Rendered as three buttons: `Always allow` / `Allow once` / `Deny`. This is a
**directly reusable Slack-native UI pattern** for any Slack-surfaced tool
proposal under J2 — rather than inventing our own confirm-then-remember
affordance, we can use Slack's prescribed one. Doesn't change D14 (an "Always
allow" here still only grants **triggering** a proposal in Slack, never
**approving** a destructive action — that distinction must survive the
implementation).

**`chat.startStream` with `task_display_mode: plan | timeline`:**

A real Slack API for streaming agent progress as structured task cards
(`pending → in_progress → complete`), rather than raw text. Directly relevant
to **D6** (streaming decoupled from orchestration via a durable event log) —
this is a concrete Slack-side adapter target: our internal event model can
render into this API for the Slack surface specifically, the same way it
renders into SSE for Grafana/Web UI. Worth a line item when `02-streaming-
and-events.md` gets its dedicated session.

**App Home + slash commands for inspectable state:**

`/agent logs`, `/agent state`, `/agent settings`, plus App Home as "the
persistent surface for workflow visibility and controls" with pause/resume/
stop/retry/redirect actions. This is a Slack-native home for our back-channel
decision (**R7**: plain REST for cancel/signal/steer/approve) — App Home
becomes the Slack-side *rendering* of that same back-channel, not a different
mechanism.

---

## 4. Does any of this change D14 (approval always happens in Grafana, never Slack)?

**No.** Nothing in either fetched page describes a per-message, per-action
re-authentication primitive — the governance guide's "approval gates" are a
**UX pattern** (a Block Kit button demanding confirmation), not a
**cryptographic re-assertion of identity at decision time**. A Slack button
click is still authenticated the same way every other Slack interaction
payload is: workspace-signed, carrying a `user_id` trusted because of the
earlier account link, not freshly asserted.

**D14's rationale is unchanged and, if anything, reinforced**: Slack's own
governance guidance treats "approval gate" as a UX/trust-building pattern for
*normal-risk* actions (creating a canvas, sending a message) — it does not
claim to solve non-repudiation for high-stakes, audited, production-affecting
actions, which is the bar D14 is actually held to.

---

## 5. Decisions

| # | Decision |
|---|---|
| 1 | **Slack account linking (A3) uses Sign in with Slack (OIDC)** — verified against current `docs.slack.dev`, see §1.1. |
| 2 | **D14 is unchanged.** Reinforced, not weakened, by Slack's own governance guidance treating approval gates as a UX pattern, not a re-authentication mechanism. |
| 3 | **Our Slack app must never present as human** — extends D11's bot-identity principle to the Slack surface itself, per Slack's own governance guidance. |
| 4 | **Adopt the "Always allow / Allow once / Deny" Block Kit pattern** for Slack-surfaced tool proposals under J2 — with the explicit caveat that "Always allow" only ever grants *triggering*, never *approving* a destructive action. |
| 5 | **`chat.startStream` (`task_display_mode`) is a candidate Slack-side rendering target for D6's event model** — tracked for `02-streaming-and-events.md`. |
| 6 | **App Home is the Slack-side rendering of R7's back-channel** (pause/resume/stop/retry/redirect), not a separate mechanism. |
| 7 | **Slack's Audit Logs API is a complementary signal, not a substitute, for our own audit chain (D15)** — it is admin-level-changes-only and lacks per-tool-call granularity. |
| 8 | **Canonical identity model keys Grid-linked Slack principals by `enterprise_id` (+ global user id)**, falling back to `team_id` (+ user id) for non-Grid installs — confirmed necessary by §1.3, not previously modelled. |
| 9 | **Socket Mode and public Slack Marketplace listing are presently mutually exclusive** per Slack's own docs (§1.2) — noted as a constraint to weigh consciously if Marketplace distribution is ever pursued, not acted on now. |

---

## 6. Open questions

1. ~~Verify Sign in with Slack, Socket Mode, and Enterprise Grid claims in §1
   against current `docs.slack.dev` pages~~ — **done, 2026-09-12.**
2. **Does Enterprise Grid change the `slack_workspace_id` granularity assumed in
   the canonical identity model (§5 of `01-identity-and-access.md`)?** —
   **answered: yes** (§1.3, §5 decision 8). Still to do: thread this change
   through `03-tenancy-and-scoping.md`'s scope model (R3) concretely — it
   currently assumes `graft_tenant_id` as a stable key, and Grid may need
   `enterprise_id` recognised as a first-class scoping dimension alongside it.
3. Read `docs.slack.dev/ai/agent-sessions` and `docs.slack.dev/ai/
   agent-context-management` before the L2 container pass — both are directly
   adjacent to our run/session model and were listed in the sidebar but not
   fetched in this session.
4. Read `docs.slack.dev/ai/mcp-overview` — Slack has a documented MCP
   integration story; worth checking whether it says anything relevant to our
   Tool Gateway / MCP Authorization Server design (D19) before finalising it.
