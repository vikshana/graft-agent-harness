---
id: ADR-0079
title: Internal surface credential resolution uses mTLS and typed decisions
status: accepted
date: 2026-09-20
deciders: [project owner]
category: identity
tags: [identity, authority-service, mtls, webhook, audit, phase-1]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: [ADR-0009, ADR-0010, ADR-0013, ADR-0015, ADR-0019, ADR-0069]
design: ../../design/mcp-authorization-server.md
phase: Phase 1
---

# ADR-0079 — Internal surface credential resolution uses mTLS and typed decisions

> **Status: accepted (2026-09-20).** The project owner formally accepted this
> architectural decision on 2026-09-20. This acceptance records the Gate 1
> Task 2 internal identity-resolution boundary; it does not claim
> implementation, verification or release evidence, or Gate 1 completion.
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Required living
> mechanism companion: [`../../design/mcp-authorization-server.md`](../../design/mcp-authorization-server.md).

---

## 1. Context

Gate 1 Task 2 needs one explicit contract between the Harness API and the
Authority Service. ADR-0069 requires the Token Service to verify the raw
surface credential itself, rather than trusting an identity asserted by the
Harness API. The accepted identity decisions also require surface-specific
verification ([`ADR-0009`](0009-grafana-identity-forwarding-via-x-grafana-id-is-the-primary-inbound-au.md),
[`ADR-0010`](0010-the-harness-mints-its-own-run-scoped-capability-token.md),
[`ADR-0013`](0013-system-initiated-runs-are-structurally-read-only.md)),
credential-derived attribution
([`ADR-0015`](../observability/0015-audit-records-form-an-insert-only-hash-chained-dag.md)),
and a logically distinct Authorisation Server and Tool Gateway
([`ADR-0019`](0019-the-mcp-authorization-server-is-logically-distinct-from-the-tool-gatew.md)
and [`ADR-0069`](../tools/0069-token-service-tool-gateway-and-registry-ship-as-one-authority-service.md)).

The identity binding held by the Harness Run repository and the fresh
credential verification performed by the Token Service are different
repository and authority boundaries. The contract must preserve both. It
must not make the Harness API an identity authority, make a webhook event
into its secret, or silently turn the two repositories into one distributed
transaction.

The Harness must also be able to prove that a replayed delivery is the same
identity-bound initiation rather than merely the same opaque replay key. A
single key can be reused accidentally or maliciously with a changed event,
verified identity, service identity, or initiation mode. The replay record
therefore needs an immutable binding against which a fresh second-call
verification can be compared.

## 2. Decision

**The exchange is two separate mTLS calls.** The first call sends the raw
surface credential and, for a webhook, its canonical normalised envelope to
the Token Service. The Token Service verifies the credential, resolves the
identity, service identity, Role set and initiation mode, checks credential
freshness, and returns only a typed `allow` or `deny` identity decision. It
also returns a configured short expiry for this first resolution.

After `allow`, the Harness API atomically persists the first verified
identity binding together with its immutable Run/replay record. The Harness
Run repository returns a formal `new`, `existing`, or `conflict` result. A
`new` result creates the Run; an `existing` result returns the original Run
and binding only when the binding tuple is identical; `conflict` creates no
Run and permits no mint exchange. There is no Token-Service-native
`duplicate` result and no generic denial in place of a replay conflict.

The second call resubmits the raw surface credential verbatim, and repeats
the same canonical normalised webhook envelope when the surface is
`webhook`, together with the Harness-created or Harness-returned
`graft_run_id`. The Token Service re-verifies the credential signature and
freshness and derives a fresh verified result. The Token Service trusts the
`graft_run_id` only because the call is authenticated as the configured
first-party Harness peer; it does not query the Harness Run store. The
Harness API compares the fresh verified result and fresh event fingerprint
with the immutable binding before it uses the returned capability token. A
mismatch is discarded and surfaced as a typed binding conflict, never used
to start or continue a Run.

The first resolution is bound to the mint exchange by the configured short
TTL stored in the immutable binding. Expiry at either the Harness binding
check or the Token Service credential-freshness check is a typed deny and
produces no usable token. This contract supports immediate Run-start token
minting only. It does not support delayed tool use or refresh of an expired
first resolution; later refresh requires a separate run-token renewal
design.

There is no distributed transaction between the Token Service and the
Harness Run repository. The Harness transaction owns the immutable replay
record and Run creation. The Token Service owns neither that replay state
nor a lookup into the Harness Run store.

The Authority Service remains one deployable with three modules, while the
Token Service/Authorisation Server and Tool Gateway remain logically
distinct and independently enforcing components as required by ADR-0069.

The first call is the internal Token Service route
`POST /internal/authority/v1/surface-resolution`. The second call is
`POST /internal/authority/v1/run-capability-mint`. Neither is customer-facing,
neither is available over a non-mTLS listener, and neither accepts bearer,
cookie, shared-header, or caller-asserted-identity fallback.

### 2.1 First-call request boundary

The first request is a discriminated envelope with these semantic fields:

| Field | Contract |
|---|---|
| `graft_surface` | An allow-listed surface discriminator selected by the configured integration contract, such as `grafana`, `slack`, `webhook`, `schedule`, or `api`. It selects the verifier and mapping; it is not a Principal claim. |
| `graft_surface_credential` | The raw credential supplied by the surface, opaque and verbatim to the Harness API, the Token Service and every transport intermediary. No caller trims, parses, normalises, decodes, re-encodes, or replaces it. |
| `graft_webhook_envelope` | Required only for `webhook`. It is the canonical normalised event envelope described in section 2.4. It is event data, not a credential, and never contains a raw secret or provider payload. |
| `graft_request_correlation_id` | A Harness-owned correlation value for tracing the request and its outcome. It is not an identity or authorisation input. |

The request has no caller-authoritative `graft_principal_id`,
`graft_tenant_id`, `graft_role_id`, `graft_initiation_mode`,
`graft_service_identity`, or `graft_audit_actor`. A request containing any
such asserted identity field is rejected as a contract violation; it is not
merged with, used as a fallback for, or compared preferentially to the
verified result. Foreign source identifiers may be present in the
normalised envelope only as integration data and must be resolved by the
Token Service rather than promoted to a Graft-owned identifier.
`graft_run_id` is not present in this request and cannot be preallocated as a
substitute for the Harness Run creation step.

### 2.2 First-call typed response boundary

Every successful first-call HTTP exchange returns one discriminated identity
decision. The response may contain safe reason and correlation metadata, but
never the raw surface credential, a downstream credential, a capability
token, a `graft_run_id`, a replay result, or a signed/server-generated
resolution handle.

| `graft_decision` | Required meaning and attributes |
|---|---|
| `allow` | The raw surface credential and, when applicable, the webhook envelope were verified. The response contains the verified identity block, `graft_event_fingerprint` for a webhook, the configured `graft_resolution_expires_at`, and the verifier revision. |
| `deny` | No Run may be created or continued from this request. The response contains a stable, non-secret `graft_deny_code` and correlation metadata, but no unverified identity claims. Expired credentials, stale first resolutions, an unauthorised mTLS peer, unsupported surface, failed verification, and malformed envelopes are typed denials. |

The verified identity block is the source for the Harness binding and
downstream request composition:

```json
{
  "graft_verified_identity": {
    "graft_principal_id": "<verified Graft Principal or null>",
    "graft_tenant_id": "<verified Graft Tenant>",
    "graft_role_ids": ["<effective graft_role_id>"],
    "graft_initiation_mode": "user_initiated|system_initiated",
    "graft_service_identity": "<verified service identity>",
    "graft_audit_actor": {
      "graft_principal_id": "<verified Graft Principal or null>",
      "graft_tenant_id": "<verified Graft Tenant>",
      "graft_role_ids": ["<effective graft_role_id>"],
      "graft_surface": "<verified surface>",
      "graft_initiation_mode": "user_initiated|system_initiated",
      "graft_trust_mode": "<configured, non-secret trust mode>"
    }
  },
  "graft_event_fingerprint": "sha256:<lower-case hex or null>",
  "graft_resolution_expires_at": "<configured short-TTL instant>",
  "graft_verifier_revision": "<configured revision>"
}
```

The example is a shape, not a wire-schema commitment. The living design
companion defines the final versioned schema, allowed Role cardinality,
service-identity representation, trust-mode values, safe error taxonomy,
and comparison rules. A caller cannot populate the verified block.

`duplicate` is not a Token Service or Harness replay result. The Harness
repository result is exactly one of `new`, `existing`, or `conflict`, as
defined in section 2.3.

### 2.3 Harness-owned replay, identity binding and Run creation

After a first-call `allow`, the Harness API derives an opaque,
stable `graft_harness_replay_key` from the accepted surface event and its
configured integration contract. It is Harness-generated, not supplied by
the surface caller and not resolved or stored as replay state by the Token
Service. For webhook delivery, the key uses the configured stable source and
delivery identity and is deliberately distinct from the semantic event
fingerprint, so a changed event under the same key can be classified as a
conflict.

The Harness Run repository performs one atomic insert-or-classify operation
scoped by `(graft_tenant_id, graft_harness_replay_key)`. It persists the
first verified identity binding and immutable Run/replay record, including
the canonical binding tuple:

```text
(
  graft_event_fingerprint,
  graft_verified_identity,
  graft_service_identity,
  graft_initiation_mode
)
```

The repository result is formal and exhaustive:

| `graft_replay_result` | Meaning |
|---|---|
| `new` | This transaction inserted the immutable replay record and created one `graft_run_id`. |
| `existing` | The key already has an immutable record and every binding-tuple member matches; return the original `graft_run_id` and binding. |
| `conflict` | The key already has a record, but the fingerprint, verified identity, service identity, or initiation mode differs. Do not create a second Run, overwrite the original binding, or continue to mint. Return a stable typed conflict code and no new `graft_run_id`. |

Exactly one concurrent valid delivery obtains `new`; every equivalent
delivery obtains `existing` and the same original `graft_run_id`. A changed
delivery obtains `conflict`, not `duplicate` and not a generic `deny`. No
check-then-insert sequence, retry race, or API-process-local cache may create
a second Run.

The Harness transaction makes the replay disposition, immutable binding and
associated Run creation durable before the Harness API reports success. A
lost response or process restart is retried with the same Harness-generated
key. Malformed, unauthorised, or unverified input never claims a replay key.
The transaction is not coordinated with a Token Service transaction.

### 2.4 Canonical normalised webhook envelope and fingerprint

The webhook envelope is canonical event data, separate from
`graft_surface_credential`. The fingerprint is computed from a configured,
versioned canonical normalisation of the semantic **source**, **event**,
**delivery**, and **alert** fields. It is not computed from the provider's
HMAC signature base string.

For the initial configured fingerprint revision, the canonical construction
is:

1. Select only the configured semantic fields in the four groups
   `graft_source`, `graft_event`, `graft_delivery`, and `graft_alert`.
2. Exclude transport-only receipt time, the raw provider payload, the raw
   provider secret, the credential, signature material, and any other
   transport metadata not declared semantic by the integration contract.
3. Normalise each configured semantic scalar according to that contract,
   reject unknown or malformed values, recursively sort object keys by their
   Unicode code-point order, and encode the result as compact UTF-8 JSON with
   no insignificant whitespace. Arrays declared as unordered semantic
   collections are sorted by the canonical form of each member; ordered
   arrays retain their order.
4. Include the canonicalisation revision in the envelope configuration, and
   calculate `graft_event_fingerprint` as `sha256:` followed by lower-case
   hexadecimal SHA-256 over those canonical UTF-8 bytes.

Thus equivalent input field order produces the same deterministic fingerprint
and a changed semantic value produces a different fingerprint. The
canonicalisation revision and selected field configuration must be versioned
and configured in the design/integration entry. They are separate from each
provider's HMAC canonicalisation, signature base string, parsing rules,
certificate profile, or PKI scheme. This ADR does not select those provider
verifier details.

### 2.5 Second-call capability-mint boundary

The Harness API calls
`POST /internal/authority/v1/run-capability-mint` only after a first-call
`allow` and a Harness repository result of `new` or `existing`. The request
contains:

| Field | Contract |
|---|---|
| `graft_surface` | The same configured surface discriminator used to select the verifier. It is routing input, not a Principal claim. |
| `graft_surface_credential` | The exact raw opaque credential from the first call, resubmitted verbatim for every surface. The Token Service re-verifies this value and does not trust the first-call response or a Harness-supplied identity block. |
| `graft_webhook_envelope` | For `webhook`, the same canonical normalised envelope is repeated on the mint call. The Token Service recomputes the fingerprint and the Harness compares the fresh result with the persisted binding. It is absent for non-webhook surfaces. |
| `graft_run_id` | The Run identifier created or returned by the Harness Run repository. The Token Service trusts it only from the authenticated, application-layer allow-listed first-party Harness API mTLS peer. It does not look up the Harness Run store. |
| `graft_request_correlation_id` | A Harness-owned correlation value. It is not an identity or authorisation input. |

The second request contains no `graft_principal_id`, `graft_tenant_id`, Role,
initiation mode, service identity, audit actor, resolution handle, or
capability token supplied by the caller. The Token Service re-verifies the
raw credential signature and freshness and derives the identity, service
identity and audit attributes afresh. On a fresh `allow`, it returns the
fresh verified result and a capability token scoped to exactly the supplied
`graft_run_id` and fresh authority.

Before the Harness API uses or forwards that token, it compares the fresh
verified result and, for a webhook, the fresh fingerprint with the immutable
binding stored in the Run/replay record. The comparison covers the full
verified identity, service identity, initiation mode and event fingerprint.
A mismatch is a typed binding conflict; the Harness discards the token and
does not use it. A matching result may be used only while the persisted
first-resolution binding remains within its configured short TTL.

The repeated raw credential is the only credential continuity between the
calls. There is no server-generated resolution handle. A valid retry of the
second call cannot create another Run or broaden token scope: any returned
token remains bound to exactly the supplied `graft_run_id` and freshly
verified authority. A changed, tampered, expired, or invalid raw credential,
an altered webhook envelope, or an untrusted peer produces a typed denial
and no token.

### 2.6 Authority Service placement, mTLS and explicit non-decisions

The endpoints terminate on the Token Service module inside the separately
deployable Authority Service. The Authority Service still contains the three
independent modules fixed by ADR-0069:

1. the Token Service / MCP Authorisation Server, which verifies raw surface
   credentials, resolves identity, and issues capability tokens;
2. the Tool Gateway, which is a Resource Server that validates capability
   tokens independently and enforces the authority lattice; and
3. the Tool Registry, which supplies curated, hash-pinned Tool definitions.

One deployable does not make these one logical authority. The Token Service
and Tool Gateway retain separate listeners and network policy, no shared
mutable request context, independent rate limits, and signing-key isolation.
The agent and DBOS worker do not receive this resolution authority, and the
Tool Gateway does not mint tokens or accept a caller's asserted identity.

mTLS trust configuration validates the peer certificate during the TLS
handshake. A TLS trust, certificate validity, or handshake failure produces
no application response because the HTTP request is never admitted. After a
successful handshake, the Token Service applies an application-layer
allow-list to the authenticated peer identity on both routes. A valid TLS
peer that is not the configured first-party Harness API receives a typed
`deny` with a safe code such as `mtls_peer_not_allowlisted`; the first call
returns no identity and the second call returns no token. All internal calls
are mTLS-only: there is no bearer, cookie, static-header, plain-HTTP, or
other fallback.

Identity-provider provisioning, account linking, and mapping from an
external identity to a Graft Principal, Tenant, or Role are explicitly
**not decisions in this ADR**. The configured verifier/mapping contract is
assumed to provide the verified attributes used by the two calls. This ADR
neither provisions those records automatically nor trusts caller-provided
mappings.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| Two mTLS calls: first raw-credential verification returns typed `allow`/`deny`; Harness atomically persists the verified binding and creates or finds the Run; second raw-credential reverification plus trusted `graft_run_id` mints the capability token | ✅ Chosen | Preserves ADR-0069's confused-deputy protection, keeps credential verification and minting in the Authority Service, gives the Harness repository ownership of replay and immutable Run binding, permits fresh-result comparison, and avoids a distributed transaction or resolution-handle lifecycle. |
| One Token Service call that verifies the credential, owns replay disposition, creates or finds the Run, and mints the token | ❌ Rejected | Couples Token Service identity/replay state to the Harness Run store, requires a distributed transaction or ambiguous partial outcome, and cannot safely compare a later fresh identity result with the immutable Run binding. |
| First call returns a signed/server-generated resolution handle for the Harness API to exchange on the second call | ❌ Rejected | Adds an artefact, signing and expiry/revocation lifecycle, and another state binding; the immutable Harness record, short TTL, raw-credential reverification and mTLS peer binding provide the selected boundary without a handle. |
| Harness API verifies the surface credential and sends only a resolved identity or normalised webhook event | ❌ Rejected | Makes the Harness API an authority, permits caller-asserted identity to cross the boundary, and violates ADR-0069's requirement that the Token Service verify the raw credential itself. |
| Send the normalised webhook envelope as the credential, or combine the envelope and secret into one provider-shaped payload | ❌ Rejected | Event data and authentication material have different trust and redaction rules; conflating them makes replay, logging, and secret handling ambiguous. |
| Permit bearer, cookie, static-header, or non-mTLS fallback for either internal call | ❌ Rejected | A fallback weakens the workload boundary and invalidates the first-party peer guarantee; both internal endpoints are mTLS-only. |
| Use separate physical deployments for the Token Service and Tool Gateway | ❌ Rejected | ADR-0069 chooses one Authority Service deployable to avoid operational overhead; logical AS/Gateway separation and independent validation remain mandatory. |

## 4. Consequences

- **Positive —** the Harness API is an untrusted transport caller rather than
  an identity authority; the Token Service has auditable points to verify the
  raw credential and derive the identity, service identity, Role set,
  initiation mode, and audit actor on both calls.
- **Positive —** the Harness Run repository owns one atomic replay operation,
  one immutable identity binding, and one stable `graft_run_id`. Equivalent
  retries are `existing`; changed bindings are typed `conflict`; neither can
  create a second Run.
- **Positive —** the Harness compares a fresh verified result to the
  persisted binding before token use, while the Token Service remains free
  of Harness Run-store queries and distributed transactions.
- **Positive —** mTLS peer authentication protects both internal workload
  hops while the Authority Service retains the single-deployable operational
  model and the AS/Gateway logical boundary.
- **Negative / accepted trade —** the raw credential crosses the internal
  boundary twice. It must remain opaque and verbatim, be excluded from all
  responses and evidence, and be protected by mTLS and configured secret
  handling controls.
- **Negative / accepted trade —** the two calls and the Harness transaction
  have independent failure windows. A successful first call followed by a
  repository, expiry, conflict, or second-call failure requires safe retry
  handling; the API must not guess a Run ID or use a token without a matching
  immutable binding.
- **Security trade —** the Token Service does not look up the Harness Run
  store. The authenticated first-party Harness API is trusted to supply
  `graft_run_id` as a binding input, while the Token Service still rejects
  caller-provided identity and re-verifies the raw credential.
- **Security trade —** denied requests may not have a verified Tenant or
  Principal. The design companion must distinguish a Tenant-scoped
  application audit record from a safe transport/security denial event, must
  preserve the `graft_tenant_id` requirement whenever a Tenant is verified,
  and must never invent identity to make an audit row appear attributable.
- **Follow-on work —** after this architectural decision is accepted, the
  versioned schemas, canonicalisation configuration, Harness transaction,
  mTLS integration, TTL handling, comparison, denial/retry handling, and
  audit redaction rules remain mandatory implementation and release work.
- **Revisit trigger —** more than one Token Service caller invalidates the
  first-party mTLS trust assumption and requires a new ADR. Exposing either
  endpoint beyond the first-party Harness API, introducing Dynamic Client
  Registration, changing the Authority Service deployment boundary, or
  evidence that the two-call binding cannot protect the exact
  `graft_run_id` scope also requires review; no fallback is added here.

## 5. Required design companion and mandatory follow-on verification

Acceptance of this architectural decision is recorded now. The companion
update and implementation/release evidence below are mandatory follow-on
work, not preconditions for accepting the architectural decision. The living
companion
[`mcp-authorization-server.md`](../../design/mcp-authorization-server.md)
must describe how, not re-argue why, the following are realised:

1. the versioned first-call and second-call request and discriminated response
   schemas, including safe denial codes, the verified identity/audit-actor
   block, service identity, fingerprint and short-TTL fields;
2. the sequence from mTLS peer authentication through first-call raw
   credential verification and freshness, surface mapping, Role and
   initiation-mode resolution, immutable Harness replay/Run binding,
   second-call raw credential reverification and freshness, fresh-result
   comparison, and capability-token minting/use;
3. the canonical normalised webhook envelope and deterministic,
   order-independent fingerprint construction over semantic source, event,
   delivery and alert fields, including the version/configuration boundary
   separate from provider HMAC canonicalisation;
4. the Harness Run repository transaction and its formal `new`, `existing`,
   and `conflict` taxonomy, including fingerprint, verified identity,
   service-identity and initiation-mode comparisons and timeout, retry, crash,
   and concurrent-delivery behaviour;
5. the configured short TTL, credential signature/freshness checks on both
   calls, typed expiry denial with no token, and the immediate Run-start-only
   boundary pending a separate run-token renewal design;
6. the mTLS trust and application allow-list integration contract, including
   handshake failure versus typed application denial, no internal fallback,
   the first-party caller assumption, and the three-module
   listener/network-policy boundary, without selecting a certificate PKI
   design;
7. the audit event shape, actor derivation, Tenant scoping, safe denial-event
   handling, redaction, retention reference, and chain linkage; and
8. the explicit rule that neither the Harness API's asserted identity fields,
   agent, DBOS worker, model output, nor a caller-supplied Run identity can
   populate verified identity or audit attributes, and that the Token Service
   performs no Authority lookup of the Harness Run store. Identity-provider
   provisioning remains outside this decision.

The following verification matrix is mandatory follow-on implementation and
release evidence. It defines required evidence to be produced by the
implementation and release work; this ADR claims none of it:

| Guarantee | Required evidence |
|---|---|
| mTLS peer boundary for both calls | Configured valid first-party Harness API peers succeed on both routes; no certificate, untrusted/invalid peer, wrong configured peer identity, expired peer, plain HTTP, or bearer-only fallback is admitted. TLS trust/handshake failures have no application response. A valid TLS but non-allow-listed peer receives a typed denial at the application layer and never receives identity or a token. The test uses configured test trust material and does not prescribe production PKI details. |
| First-call typed resolution | Positive fixtures prove verified `graft_principal_id`, `graft_tenant_id`, effective Role set, initiation mode, service identity, audit actor, fingerprint and short expiry; negative fixtures prove no unverified identity is returned. The first call returns only `allow` or `deny`, never a Token-Service-native `duplicate`, replay result, `graft_run_id`, token, or resolution handle. |
| Harness immutable replay taxonomy | Positive duplicate fixtures prove equivalent concurrent deliveries produce one `new` result and `existing` results with the same original `graft_run_id` and binding. Negative conflict fixtures prove that the same Tenant and replay key with a changed fingerprint, verified identity, service identity, or initiation mode returns `conflict`, creates no second Run, and never becomes `duplicate` or a generic denial. |
| Canonical fingerprint boundary | Fixtures with reordered JSON object fields produce the same fingerprint; semantic changes produce a different fingerprint; receipt time, raw provider payload and raw secret do not affect it. The selected canonicalisation revision/configuration is distinct from provider HMAC canonicalisation. |
| Raw credential repeat and no leakage | A synthetic credential fixture proves both calls carry the exact raw value, including significant bytes, for every surface, and that no raw credential appears in either response, logs, telemetry, error body, audit payload, persisted decision, or replay/Run record. Webhook fixtures prove the canonical normalised envelope is repeated on the mint call. |
| Freshness, TTL and second-call binding | Tests prove signature and freshness verification on both calls, short-TTL expiry as typed deny with no token, fresh-result comparison against the persisted immutable binding before token use, exact `graft_run_id` scope from the authenticated first-party Harness peer, and no Harness Run-store lookup by the Token Service. Changed, tampered, expired, or invalid credentials; altered envelopes; caller identity fields; and altered or untrusted peer bindings are denied or discarded without token use. |
| Second-call replay behaviour | A valid retry or replay of the second call cannot create another Run or broaden Run scope; any returned token remains bound to the same supplied `graft_run_id`. The companion defines safe issuance/idempotency handling for response loss without introducing a resolution handle or distributed transaction. Delayed use after the first-resolution TTL is denied; no renewal behaviour is inferred. |
| Surface/envelope separation | Webhook event normalisation does not alter or stand in for the raw credential; non-webhook requests cannot supply a webhook envelope; malformed envelopes are typed denials and never claim a Harness replay key. |
| Caller cannot assert identity | Requests carrying forged `graft_principal_id`, `graft_tenant_id`, `graft_role_id`, `graft_initiation_mode`, `graft_service_identity`, or `graft_audit_actor` are rejected and cannot influence either call's result. A caller cannot preallocate or override `graft_run_id` through an identity field. |
| Audit guarantee | Allow and deny outcomes across both calls have an auditable typed result; verified outcomes derive the actor only from the verified credential; Tenant scope is retained on every application audit record; no raw secret, capability token, downstream credential, or resolution handle is present; safe handling of no-Tenant denials is demonstrated. |
| Authority separation | Build/configuration and integration tests prove the Token Service, Tool Gateway, and Tool Registry remain one deployable but three modules with separate listeners/policy, independent Gateway token validation, signing-key isolation, no shared mutable request context, and independent rate limits. |

## 6. Evidence input and Phase 1 placement

This ADR's decision input is dated **2026-09-20**. It consists of the
accepted identity and Authority Service decisions cited above, the Gate 1
Task 2 requirement in the
[`Phase 1 walking skeleton plan`](../../../specs/phase-1-walking-skeleton/PLAN.md),
and the retained Task 1 implementation note that production Authority Service
identity resolution remains pending Gate 1 Task 2 in
[`IMPLEMENTATION-NOTES.md`](../../../specs/phase-1-walking-skeleton/IMPLEMENTATION-NOTES.md).
The input establishes the required boundary; it is not live mTLS, provider
verification, replay, audit, or production implementation evidence.

This ADR is placed in **Phase 1** as the accepted Gate 1 Task 2 architectural
decision. Its placement does not check the plan task, close Gate 1, or claim
Phase 1 completion. The companion design and the verification evidence listed
in section 5 remain mandatory follow-on implementation and release work.
