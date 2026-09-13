# Tool Registry & the Authority Lattice

> **Status: 🟢 Resolved for v1 (2026-09-13).** Locked as **ADR-0063**.
> Narrows **ADR-0016**; implements **ADR-0007**'s enforcement point concretely.
>
> Vocabulary per [`../GLOSSARY.md`](../GLOSSARY.md). Related:
> [`ux-mcp-tool-configuration.md`](./ux-mcp-tool-configuration.md),
> [`tenancy-and-scoping.md`](./tenancy-and-scoping.md).

---

## 1. The requirement

> *"There should be layers where the platform has ultimate say if the tool can
> be used or not."*

The mechanism that delivers this is a **monotonically narrowing lattice**: five
layers, each of which may only ever **remove** capability, never add it. The
effective capability of any tool call is the **intersection of all five**.

Stated as an invariant worth testing directly:

> **No layer can grant what a layer above it has not already granted.**

---

## 2. Verified grounding

### 2.1 OWASP LLM06:2025 — Excessive Agency *(read directly, 2026-09-13)*

OWASP names three root causes, and our layers map onto them one-for-one:

| Root cause | Our layer |
|---|---|
| **Excessive functionality** | Layers 1–3 — catalogue, platform policy, Tenant policy |
| **Excessive permissions** | Layer 4 — run capability token; plus ADR-0022's minimum-role SA |
| **Excessive autonomy** | Layer 5 + ADR-0014/ADR-0055 approval |

Their eight mitigations, mapped to decisions already taken:

| OWASP mitigation | Ours |
|---|---|
| 1. "Minimize extensions" | Layer 2/3 — deny-by-default catalogue |
| 2. "Minimize extension **functionality**" | **Policy is per *tool*, not per *server*** (section 3.3) |
| 3. **Avoid open-ended extensions** | **ADR-0004** — no arbitrary code execution in v1 |
| 4. "Minimize extension permissions" | **ADR-0022** — SA role recomputed to the minimum across enabled tools |
| 5. Execute in the user's context | **ADR-0011 / ADR-0023** — check-then-act under the Principal's own identity |
| 6. Require user approval | **ADR-0014 / ADR-0065** — re-authenticated, in Grafana, **by the current driver** (was initiator-only under ADR-0055, withdrawn 2026-09-13) |
| 7. **Complete mediation** — *"implement authorization in downstream systems rather than relying on an LLM to decide if an action is allowed"* | **ADR-0007** — the Tool Gateway is a separate service precisely because in-process policy is not a boundary |
| 8. Sanitise inputs and outputs | Collector scrubbing (ADR-0008/ADR-0025); section 4.2 below |

Mitigation 7 is the load-bearing one and it is worth quoting because it is the
whole argument for ADR-0007: **the model is never the policy decision point.** A tool
the lattice has not granted is not "discouraged in the prompt" — it is **absent
from the token and rejected at the gateway**.

### 2.2 MCP Security Best Practices *(index read 2026-09-13)*

The MCP specification carries a dedicated security-best-practices document
alongside its authorisation spec, enumerating confused-deputy, **token
passthrough**, SSRF, session hijacking, OAuth URL validation, stdio-proxy
weaknesses and **scope minimisation**. Two of its named attacks are already
closed by decisions we hold — **token passthrough** (ADR-0010/ADR-0019: the Tool Gateway
is a Resource Server that validates independently and never forwards a caller's
token onward as its own) and **stdio transport in proxy scenarios** (ADR-0070: no
stdio, ever). The remainder are implementation-review material for the Tool
Gateway build, not open architecture.

---

## 3. The lattice

```
 L1  PLATFORM CATALOGUE      what exists at all
     ├─ platform_admin only. Not customer-visible, not customer-raisable.
     ▼
 L2  PLATFORM POLICY         what may EVER be enabled, per tool class
     ├─ hard deny wins over everything below. The "ultimate say".
     ▼
 L3  TENANT POLICY           what IS enabled for this Tenant
     ├─ tenant_admin. Versioned, never overwritten (ADR-0016).
     ├─ write-capable classes need step-up auth (ADR-0016).
     ▼
 L4  RUN CAPABILITY TOKEN    what THIS run may call
     ├─ minted per run (ADR-0010). system_initiated ⇒ no write classes (ADR-0013).
     ├─ forked/eval runs ⇒ no write classes (ADR-0042).
     ▼
 L5  CALL-TIME CHECK         may THIS principal do THIS, right now
     └─ check-then-act against Grafana (ADR-0023); tool-policy role for
        non-Grafana classes (ADR-0056); per-connection throttle (ADR-0044).

 effective = L1 ∩ L2 ∩ L3 ∩ L4 ∩ L5
```

### 3.1 Why L1 and L2 are separate

L1 is *inventory* ("we have a `k8s-mcp` integration"). L2 is *permission*
("nobody may enable pod deletion, on any Tenant, regardless of what their
admin wants"). Collapsing them means the only way to forbid something globally
is to delete the integration, which also removes its safe read-only tools.

L2 is where a platform-wide kill switch lives: disabling a tool class at L2
takes effect for **in-flight runs at their next tool call**, because L5
re-evaluates on every call. That is the property that makes it an incident
control rather than a config change.

### 3.2 Where L4 gets its power

The run capability token is the reason this is a security boundary and not a
preference. **A tool absent from the token cannot be called even if the model
is convinced it should be** — the gateway rejects it without consulting any
policy at request time. This is the same mechanism ADR-0013 uses to make
`system_initiated` runs *structurally* read-only, and ADR-0042 uses for forked eval
runs.

### 3.3 Policy granularity is the tool, not the server

OWASP mitigation 2, made concrete. `grafana-mcp` exposes both read and write
tools; enabling the *server* must not enable the *set*. ADR-0022 already depends on
this: it recomputes the SA's Grafana role to *"the minimum required across
enabled tools"*, which is only meaningful if enablement is per tool.

**Tool classes** (`read`, `write`, `destructive`) are the unit of *policy and
approval*; individual tools are the unit of *enablement*.

---

## 4. Registry content

### 4.1 A tool definition is pinned, and re-approval is required on change

The registry stores, per tool: `tool_id`, owning server, class, input schema,
our curated description, required Role for non-Grafana classes (ADR-0056), and a
**definition hash**.

**If an upstream MCP server changes a tool's name, description or schema, the
hash changes and the tool is treated as not-enabled until re-approved.**

This is the "rug pull" / tool-poisoning case: a server is approved while benign
and mutates afterwards. Without pinning, L3's approval is an approval of
whatever the upstream happens to serve at call time — which is not an approval
at all. ADR-0016 already requires tool policy to be versioned and never overwritten;
the hash is what makes that version *mean* something.

### 4.2 Upstream tool descriptions are untrusted input

A tool's description is injected into the model's context. An upstream MCP
server therefore has a **direct prompt-injection channel into our agent**,
which is ADR-0007's stated primary threat arriving through the front door rather than
through log data.

**The registry serves our own curated description, not the upstream's.** The
upstream description is stored for diffing and review only, never forwarded to
the model.

### 4.3 Deny by default

A tool not in the registry is not callable. Discovery from an upstream server
produces **registry candidates for review**, never live capability.

---

## 5. v1 defaults

Every value here is **configuration, not a constant**, and
`platform_admin`-customisable per Tenant (ADR-0057).

| Setting | v1 default | Decision |
|---|---|---|
| Schedules per Tenant | **10** | ADR-0058 |
| Minimum Schedule interval | **1 hour** | ADR-0058 |
| Budget warning threshold | **80% of ceiling** | ADR-0057 |
| Approval expiry | **72 hours** | ADR-0047 |
| Driver idle auto-release | **10 min** (warn at T−60s) | ADR-0066 |
| Driver **disconnect** auto-release | **2 min** — a separate clock | ADR-0066 |
| Control-clock evaluation | **30s sweep**, not a per-Run durable timer | ADR-0066 |
| Per-Principal / per-Tenant monthly quota | **unset — platform-assigned at onboarding** | ADR-0057 |

Monthly token/cost ceilings stay deliberately unset: any number chosen before
real cost data is a guess that would be mistaken for a decision. Onboarding
assigns them explicitly per Tenant, and section 6's monitoring is what turns them into
an informed default later.

---

## 6. Monitoring

- **Denials by layer** — a spike at L2 or L3 means policy is wrong; a spike at
  L5 means ADR-0024's SA-ceiling assumption is wrong and is exactly its revisit
  metric.
- **Definition-hash drift events** (section 4.1) — an upstream mutating tools is a
  supply-chain signal, not a routine event.
- **Tools enabled but never called** — OWASP risk example 2 (an extension
  trialled and never removed). Feeds a periodic least-privilege review, which
  PCI-DSS requires anyway (ADR-0025).
