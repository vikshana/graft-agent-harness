# Context assembly and compaction

> **Status: 🟡 Partially resolved.** The prompt-layer hierarchy and the
> capability/behaviour split are locked (**ADR-0062**). Compaction mechanics are
> **carried over as a proposal** and are owned by the *Context Assembly* session
> — see [`../backlog/future-sessions.md`](../backlog/future-sessions.md).
>
> Vocabulary per [`../GLOSSARY.md`](../GLOSSARY.md).
>
> *Promoted from `research/context-management.md` during the 2026-09-13 ADR
> migration, because **ADR-0062 cites this hierarchy normatively**. Claims that
> contradicted locked decisions have been corrected — see section 5.*

---

## 1. Prompt-layer hierarchy

Ordered layers, static first. The ordering serves **prompt caching** (KV-cache
reuse) and **security** (later layers cannot override earlier ones).

```
┌──────────────────────────────────────────────────────┐  [STATIC & CACHED]
│ L1  Platform system prompt, safety, execution schema │  Hardcoded invariants
├──────────────────────────────────────────────────────┤
│ L2  Tenant custom instructions                       │  Org conventions
├──────────────────────────────────────────────────────┤  [DYNAMIC SESSION]
│ L3  Principal custom instructions                    │  Personal preferences
├──────────────────────────────────────────────────────┤
│ L4  Working state & scratchpad                       │  Hypotheses, run state
├──────────────────────────────────────────────────────┤  [EPHEMERAL & COMPACTED]
│ L5  Conversation & action history                    │  Truncated turns + tools
└──────────────────────────────────────────────────────┘
```

**Precedence: higher layer wins on conflict** (ADR-0062). A Principal cannot opt
out of a Tenant convention.

| Layer | Contents | Notes |
|---|---|---|
| **L1** | Persona, tool-call format, output schemas, safety boundaries | Identical across all Tenants and requests — the basis for high prompt-cache hit rates |
| **L2** | Tenant-wide conventions, e.g. *"never suggest scaling nodes in `prod-us-east-1` automatically"* | Versioned; recorded on the Run |
| **L3** | Principal preferences, e.g. *"prefer Python over Bash"*, *"only search `payments-*`"* | Versioned; recorded on the Run |
| **L4** | Current hypothesis list, `graft_run_id`, topology context | Continually updated, never compacted away |
| **L5** | Messages and tool responses | The **only** layer subject to aggressive compaction |

## 2. Custom instructions are text, never policy

ADR-0062's hard rule, restated here because it governs assembly:

> Custom instructions govern **behaviour** (tone, persona, format). They can
> never enable a tool, widen a Role, alter a budget or bypass an approval.

An instruction reading *"you may restart pods without asking"* has **literally no
effect**, because capability comes from the run capability token (ADR-0010,
lattice layer L4 in ADR-0063), minted before the instruction is ever read. The
mitigation is **structural, not a filter** — which matters because L2 and L3 are
user-authored text flowing into model context, i.e. a prompt-injection channel by
construction.

Defence in depth at assembly time: enclose L2 and L3 in strict delimiters
(`<tenant_instructions>`, `<principal_instructions>`) and state in L1 that they
may never override L1 safety rules or authorisation outcomes.

**Both levels are versioned and recorded on the Run** — required for ADR-0015
audit attribution and for ADR-0040's `fork_workflow` eval replay to be
reproducible.

## 3. Compaction (proposed — not locked)

- **Tool-result reduction happens before the model sees anything.** The Tool
  Gateway truncates/summarises; full artifacts go to object storage and are
  fetched on demand (ADR-0034). This is the single largest lever, since raw
  diagnostic payloads are what overflow the window.
- **Summariser trigger:** before executing the next node, if total tokens exceed
  **70 % of the context window**, route L5 through a fast cheap model, compress
  to an updated scratchpad summary, and prune intermediate history prior to the
  last two turns, appending the summary to L4.
- **RAG payload compression:** pass retrieved runbook/doc text through an
  explicit compressor (e.g. LLMLingua-2) before prepending — claimed 30–50 %
  token saving. **Unverified; benchmark before adopting.**

## 4. Where context lives

| Element | Storage | Lifetime | Compaction |
|---|---|---|---|
| System invariants | Config / version-controlled templates | Permanent | Static KV prompt caching |
| Tenant & Principal instructions | Our own tables, versioned | Per Tenant / Principal | Injected into delimited tags |
| Active hypotheses | Run-state tables (L4) | Duration of Run | Updated, never deleted |
| Tool outputs | Object storage, referenced by event payload | Per tool call | Reduced at the Tool Gateway |
| Message history | **Postgres run-state tables** | Per Run | Summariser at >70 % window |

## 5. Corrections applied during promotion

The source research predated several locked decisions and is corrected here:

| Research claim | Corrected to |
|---|---|
| Message history in "Postgres / Redis Checkpoint" | **Postgres only, no Redis** (ADR-0030); **no LangGraph checkpointer** — conversational state is our own tables, passed explicitly into the graph (ADR-0040) |
| Tool outputs filtered "in MicroVM Sandbox" | **Tool Gateway result reduction** (ADR-0034). Sandboxing is deferred to Phase 2 (ADR-0004) |
| Topology context "from Neo4j" | Deferred — memory & knowledge is an unstarted session |
| "Incident Memory — Mem0 / Vector DB" | Deferred — same session |
| Single "Custom User Instructions" layer | **Two layers, Tenant then Principal, Tenant wins** (ADR-0062) |
| User instructions stored in "User DB / Keycloak" | Our own tables. The IdP authenticates; it does not hold authorisation or preference state (ADR-0056) |

## 6. Implementation checklist

1. **Prompt isolation** — store L1/L2 templates in version-controlled Jinja
   files (`system_prompt_v1.2.j2`), never embedded in code, so ADR-0040's eval
   replay can pin a prompt version.
2. **Context-window guardrail** —
   `max_tokens_allowed = model_context_limit − max_completion_tokens − safety_buffer`.
3. **Deterministic scrubbing before egress** — pass L5 through PII/secret/PAN
   scrubbing before any external LLM API call. PAN detection specifically is
   owned by the Evals session (ADR-0025).
