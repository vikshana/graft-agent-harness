---
id: ADR-0009
title: Grafana identity forwarding via X-Grafana-Id is the primary inbound authn
status: accepted
date: 2026-09-12
deciders: [ ]
category: identity
tags: [ identity, authn, authz ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ]
amended_by: [ ]
relates_to: [ ]
design: ../../design/external-identity-mapping.md
legacy_id: D9
---

# ADR-0009 — Grafana identity forwarding via X-Grafana-Id is the primary inbound authn

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D9`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [
`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

The Grafana surface (ADR-0002) needs an inbound authentication mechanism that lets the harness resolve a caller's
Grafana identity without re-implementing Grafana's own session model. The candidates were the plugin platform's built-in
ID-forwarding mechanism, a plugin-signed JWT fallback, and
`oauthPassThru` (which forwards the user's own OAuth token to a datasource). Because the platform owns and operates the
instance (ADR-0021) and runs
`latest`, the newest identity-forwarding mechanism is available rather than merely aspirational, and destructive actions
(approval, ADR-0014) need a trust level strong enough to survive scrutiny.

## 2. Decision

**Grafana identity forwarding: `X-Grafana-Id` (ID forwarding, feature toggle `idForwarding`) is the primary inbound
authn mechanism** for the Grafana surface, running on **latest Grafana** (ADR-0021) since we operate the instance. A
plugin-signed-JWT fallback is permitted, but a workspace on fallback trust **cannot approve destructive actions**.
`oauthPassThru` is a downstream (ADR-0011) concern, not an inbound authn one. **Verified live 2026-09-12** against
Grafana OSS `latest` (resolves to v13.0.2): `idForwarding` is enabled by default; the signing-key/JWKS-equivalent
endpoint is **`/api/signing-keys/keys`**, not `/.well-known/jwks.json`.

## 3. Considered options

| Option                                              | Verdict     | Why                                                                                                                                                       |
|-----------------------------------------------------|-------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| `X-Grafana-Id` ID forwarding (`idForwarding`)       | ✅ Chosen   | Runs on latest Grafana, which the platform controls (ADR-0021); confirmed live as enabled by default                                                      |
| Plugin-signed JWT fallback as the primary mechanism | ❌ Rejected | Weaker trust chain; a workspace running on this fallback cannot be trusted to approve destructive actions                                                 |
| `oauthPassThru` as the inbound authn mechanism      | ❌ Rejected | Conflates inbound authn with the downstream credential question (ADR-0011) — it is a datasource-access concern, not how the harness learns who is calling |

## 4. Consequences

- **Positive —** one primary mechanism, confirmed by direct testing rather than assumed from docs; running latest keeps
  it current.
- **Negative / accepted trade —** a workspace that falls back to the plugin-signed JWT path is deliberately restricted:
  it cannot approve destructive actions, which is friction for whatever caused the fallback (e.g. an older Grafana
  build, if `latest` slips).
- **Follow-on work —** the signing-key endpoint is `/api/signing-keys/keys`, not the more common
  `/.well-known/jwks.json`; anything that fetches signing keys must target the right one.
- **Revisit trigger —** Grafana changes `idForwarding`'s default-on status, or moves/removes the signing-key endpoint.

## 5. Verification

- Verified live 2026-09-12 against Grafana OSS `latest` (resolved to v13.0.2): `idForwarding` enabled by default;
  signing-key endpoint confirmed at `/api/signing-keys/keys`. Mechanism:
  [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

