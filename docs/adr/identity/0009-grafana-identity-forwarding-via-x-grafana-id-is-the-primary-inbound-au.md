---
id: ADR-0009
title: Grafana identity forwarding via X-Grafana-Id is the primary inbound authn
status: accepted
date: 2026-09-12
deciders: []
category: identity
tags: [identity, authn, authz]
supersedes: []
superseded_by: []
amends: []
amended_by: []
relates_to: []
design: ../../design/external-identity-mapping.md
legacy_id: D9
---

# ADR-0009 — Grafana identity forwarding via X-Grafana-Id is the primary inbound authn

> **Status: accepted (2026-09-12).** Migrated verbatim from `DECISION-REGISTER.md` (legacy `D9`).
>
> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism: [`../../design/external-identity-mapping.md`](../../design/external-identity-mapping.md).

---

## 1. Context

<!-- TODO(migration): extract the forces from the Decision text below. The register did not separate them. -->

## 2. Decision

**Grafana identity forwarding: `X-Grafana-Id` (ID forwarding, feature toggle `idForwarding`) is the primary inbound authn mechanism** for the Grafana surface, running on **latest Grafana** (ADR-0021) since we operate the instance. A plugin-signed-JWT fallback is permitted, but a workspace on fallback trust **cannot approve destructive actions**. `oauthPassThru` is a downstream (ADR-0011) concern, not an inbound authn one. **Verified live 2026-09-12** against Grafana OSS `latest` (resolves to v13.0.2): `idForwarding` is enabled by default; the signing-key/JWKS-equivalent endpoint is **`/api/signing-keys/keys`**, not `/.well-known/jwks.json`.

## 3. Considered options

<!-- TODO(migration): several register cells name the rejected option inline ("considered and rejected", "chosen over"). Lift them here. -->

## 4. Consequences

<!-- TODO(migration): lift "accepted tension" / revisit metrics here. -->

## 5. Verification

<!-- Claims marked "verified live" in the register carry their date inline in section 2; restate them here when this ADR is next touched. -->
