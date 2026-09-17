# Platform topology and surfaces

> **Status: 🟢 Resolved for v1.** Mechanism for **ADR-0001**, **ADR-0002**,
> **ADR-0021**, **ADR-0049**.
>
> Vocabulary per [`../GLOSSARY.md`](../GLOSSARY.md). Related:
> [`tenancy-and-scoping.md`](./tenancy-and-scoping.md),
> [`../diagrams/c4-l2-containers.md`](../diagrams/c4-l2-containers.md).
>
> *Created during the 2026-09-13 ADR migration.*

---

## 1. Grafana ownership

**The platform owns and operates the Grafana instance** (ADR-0021). Customers are
**GrafanaOrgs within a single shared instance** — not customer-hosted. Grafana
runs **OSS**, at **latest release**.

Two consequences that shape everything else:

- We can rely on current-release behaviour, which is what makes ADR-0009's
  `idForwarding` dependency safe.
- Grafana OSS has no custom-role RBAC (ADR-0026), so basic roles are the only
  available enforcement granularity — not a fallback, the only option.

## 2. Surfaces

| Surface | v1? | Inbound authn |
|---|---|---|
| Grafana App Plugin | ✅ | `X-Grafana-Id` ID forwarding (ADR-0009) |
| Slack | ✅ | Verified identity link (ADR-0020, ADR-0061) |
| Webhooks (Grafana Alerting / Alertmanager) | ✅ | Shared secret; normalised event |
| Custom Web UI | ❌ post-v1 | OIDC/SSO (ADR-0072) |

**Two callers, one API** (ADR-0001): the Grafana integration goes through the
**plugin backend (Go) proxy**, never browser→API direct; the post-v1 custom
frontend calls the same API directly. The web UI gets **no private
capabilities** — it is deferred, not special.

Webhook triggers produce a **standardised normalised event**, so that alert
sources are interchangeable.

## 3. Regional deployment

**Two independent regional deployments** — GCP and AliCloud — each
shared-multi-tenant internally. **Not one logical system** (ADR-0049).

- **`graft_tenant_id` is globally unique across both regions and externally
  sourced** from existing platform team metadata. We adopt the key; we do not
  mint it. This is what makes a customer spanning both regions coherent.
- **Data residency:** run data, events, artifacts and audit records never leave
  their home region. Audit chains are wholly in-region and anchor to in-region
  WORM storage.
- **Cross-region access is a read-path proxy.** The local API resolves
  `home_region` from a globally-replicated, **metadata-only Tenant Directory**,
  forwards under the caller's identity, and returns without persisting outside
  the home region.
- Each region has its own workers and its own DBOS system database. **There is no
  cross-region workflow recovery** — which is how ADR-0048's multi-cloud
  placement risk is resolved by construction.

⚠️ **`grafana_org_id` is region-local** (ADR-0060, `is_global = false`): org `5`
exists in *both* regions meaning different Tenants. It is a mapped attribute,
never a key.

## 4. Open work

- Packaging (Helm/Terraform) and GPU/serving placement — tenancy itself is
  settled, this is not. The approved model and serving arrangement is supplied
  by organisation policy (ADR-0075); provider and routing detail remains a
  Phase 2 decision.
- Tenant Directory substrate.
