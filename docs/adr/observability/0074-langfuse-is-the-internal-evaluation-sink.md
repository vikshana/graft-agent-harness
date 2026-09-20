---
id: ADR-0074
title: Langfuse is the internal evaluation sink
status: accepted
date: 2026-09-17
deciders: [ ]
category: observability
tags: [ observability, evaluation, otel, langfuse ]
supersedes: [ ]
superseded_by: [ ]
amends: [ ADR-0008, ADR-0071 ]
amended_by: [ ]
relates_to: [ ADR-0005, ADR-0015, ADR-0025, ADR-0040, ADR-0049 ]
design: ../../design/observability-pipeline.md
verified: 2026-09-17
---

# ADR-0074 — Langfuse is the canonical internal evaluation sink

> Vocabulary per [`../../GLOSSARY.md`](../../GLOSSARY.md). Mechanism:
> [`../../design/observability-pipeline.md`](../../design/observability-pipeline.md).

---

## 1. Context

Phase 1 needs one internal-only sink to inspect trajectories, compare
prompt versions, annotate runs and curate evaluation datasets. The sink must
receive OTLP through the Collector, after the same PAN/PII and secret
scrubbing as the audit path; no product feature may read its API. It must also
be self-hostable per region and suitable for commercial use. S3 considered
Langfuse and Arize Phoenix; ELv2 does not disqualify Phoenix for internal-only
commercial self-hosting.

## 2. Decision

Use **self-hosted Langfuse as the canonical internal evaluation sink** in local
and regional environments, receiving only scrubbed OTLP/HTTP exports from the
OTel Collector; the agent process uses no Langfuse SDK and no product runtime
depends on the sink.

## 3. Considered options

| Option | Verdict | Why |
|---|---|---|
| Langfuse | ✅ Chosen | It has a documented OTLP/HTTP Collector path, GenAI attribute mapping, prompt/version metadata, experiment comparison, annotation and dataset-curation workflows. Using the same product locally and regionally preserves evaluation parity. |
| Arize Phoenix | ❌ Rejected as the canonical sink | Phoenix is eligible for internal commercial self-hosting and supports OTel tracing, datasets and experiments. It was not selected because supporting a second product would split the evaluation data model and operating procedure; Langfuse provides the clearer first-class prompt-comparison workflow for this architecture. |

The deciding criterion was **one first-class evaluation workflow usable
consistently in local and regional environments**, with Langfuse's
prompt-version comparison and dataset workflow providing the best fit.

## 4. Consequences

- **Positive —** The Collector remains the only integration point. Switching
  later remains bounded to an exporter and sink-side mapping while OTLP is kept
  canonical.
- **Positive —** Langfuse provides a first-class path for prompt/version
  comparison, annotations, dataset curation and experiments without creating a
  product runtime dependency.
- **Negative / accepted trade —** Langfuse's direct OTLP path is OTLP/HTTP;
  the checked documentation says gRPC is not supported by that endpoint. The
  Collector configuration therefore uses `otlphttp` for Langfuse.
- **Negative / accepted trade —** Self-hosted Langfuse is a multi-component
  deployment (including PostgreSQL, ClickHouse, Redis and object storage), so
  its regional operational footprint is larger than a minimal Phoenix
  container.
- **Follow-on work —** Pin and test a Langfuse release in the Phase 1 regional
  deployment; configure database/object-store retention with the deployment
  owner; and add a Collector integration test using the synthetic trajectory
  corpus before production rollout.
- **Follow-on work —** The eval sink remains internal-only. Audit records are
  never sampled, and trajectories continue to come from OTel spans plus the
  event log, never from a checkpointer.
- **Revisit trigger —** Reopen only if Langfuse removes the required OTLP
  ingestion path, cannot meet the Collector scrubbing boundary, or no longer
  supports the required prompt-comparison and dataset workflows.

## 5. Verification

On 2026-09-17:

- Langfuse's primary OpenTelemetry documentation was checked for the
  `/api/public/otel` OTLP endpoint, Collector `otlphttp` example, HTTP
  transport, GenAI attribute mapping, version fields, and experiment ingestion:
  [`langfuse.com/integrations/native/opentelemetry`](https://langfuse.com/integrations/native/opentelemetry).
- Langfuse's primary dataset documentation was checked for annotation-to-
  dataset curation, trace-to-dataset items, versioning and experiments:
  [`langfuse.com/docs/evaluation/experiments/datasets`](https://langfuse.com/docs/evaluation/experiments/datasets).
- Langfuse's repository `LICENSE` was checked at
  [`github.com/langfuse/langfuse/LICENSE`](https://github.com/langfuse/langfuse/blob/main/LICENSE).
- Phoenix `arizephoenix/phoenix:latest` was started locally. Its UI returned
  HTTP 200 and its startup log advertised OTLP/gRPC on `4317` and OTLP/HTTP on
  `6006/v1/traces`. Phoenix's repository `LICENSE` was checked at
  [`github.com/Arize-ai/phoenix/LICENSE`](https://github.com/Arize-ai/phoenix/blob/main/LICENSE)
  and its ELv2 internal-use boundary was found compatible with this design.
- The final selection does not claim a statistically measured quality
  advantage. It is an architectural and operational choice: one canonical
  workflow, verified Langfuse OTLP ingestion, and local/regional parity. A
  Phase 1 integration test remains follow-on work for PAN scrubbing and
  production retention.
