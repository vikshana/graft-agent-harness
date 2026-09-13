# Capability inventory

> Untriaged braindump. Every item still needs **keep / defer / drop** and a
> concrete choice. Items that survive triage become ADRs or design content;
> items that do not are deleted, not archived.
>
> *Migrated from `DECISION-REGISTER.md` §8 and `research/Agent Harness.csv`
> during the 2026-09-13 ADR migration. The CSV was the raw ideation artifact and
> is retained only in git history (`git show ab62775`).*

---

## Orchestration & agent loop
Agent loop · planner · workers · validator · router · sub-agents · specialised
agents · intent · hypothesis · RCA · chat · shallow vs deep research · split
conversation · framework.

**Largely decided:** ADR-0003 (LangGraph + DeepAgents), ADR-0036 (one run
primitive), ADR-0039 (run = durable workflow, sub-agent = child workflow).

## Context management
Context compaction · offloading · state · memory · knowledge graph · custom user
instructions · rules · agent steering · caching · *"store result in memory, pass
schema only, let the agent query it via jq/yq"*.

**Partly decided:** ADR-0062. Rest owned by the Context Assembly and Memory
sessions.

## Interfaces
Grafana App · custom UI · API-first · Slack agent · AG-UI · React · MCP Apps ·
interactive · artifacts · mermaid graphs · follow-up questions · `@context`
(datasource/dashboard/panel/alert) · jump-to Explore/Dashboard/Alert · data
visualisation · per-message feedback icon · per-conversation feedback modal ·
token usage/budget display · quota indicator · tool-call input/output display ·
scroll-to-last · usage tips · custom doc links.

**Partly decided:** ADR-0002 (surfaces), ADR-0029 (AG-UI scope), ADR-0031
(Grafana Live), ADR-0034 (artifact rendering incl. diff view), ADR-0057 (quota
indicator), ADR-0072 (run list).

## Observability (of the agent)
Tracing · logs · metrics · trajectories · feedback · token count · Langfuse · LGTM.

**Decided:** ADR-0005, ADR-0008, ADR-0071. Open: Langfuse vs Phoenix; sampling policy.

## Observability (as the problem domain)
Dashboards · alerts · investigations · dashboard queries · recording rules ·
search (SearXNG, qsearch, Camoufox) · K8s · GCP.

## Tools & integrations
MCP client · tool registry · tool use · single call for a specific task/tool ·
GitHub · Jira · Slack · ServiceNow · ITSI · iLert · Harbor · K8s · GCP · build ·
deploy.

**Decided:** ADR-0007, ADR-0063, ADR-0067, ADR-0068, ADR-0070. Each new
integration needs a ToolClass classification per ADR-0063 before it can ship.

## Security & governance
Guardrails · sandbox · governance · authn · authz · HITL · rate limiting · max
tool calls · token budget · NeMo · OpenShell · Arrakis · Kata Containers ·
Firecracker · Cloud Hypervisor.

**Decided:** ADR-0004 (no code exec in v1; micro-VM candidates are Phase 2),
ADR-0044, ADR-0056, ADR-0057, ADR-0063.

## Models
Multi-model · cross-provider models · Python/TypeScript runtime split.

**Owned by** the Model Routing session, under ADR-0057's no-degrade constraint.

## Evals
Evals · benchmark · DeepEval · O11y-Bench.

**Owned by** the Evals & Benchmarks session, which also holds PAN scrubbing
(ADR-0025).
