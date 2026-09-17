# Delivery roadmap

> **Status: 🟡 Proposed.** Rewritten 2026-09-13 against ADR-0001–ADR-0072.
> Supersedes the pre-decision phase plan (in git history only).
>
> Phases 1–4 together deliver **v1**. Phase 5 is post-v1.
> Four decisions gate Phase 1 — see section 6.

---

## 1. "v1" is a scope boundary, not a phase

The ADRs use **v1** to mean *what ships to a customer*, and **Phase 2 / post-v1*
to mean *explicitly deferred*. Mapping v1 → Phase 1 directly does not work:

> v1 includes two regional deployments (ADR-0049), PCI-DSS compliance
> (ADR-0025), a hash-chained audit DAG anchored to WORM storage (ADR-0015),
> blue/green deploys with a version-aware reaper (ADR-0038, ADR-0046), five
> durable-timer use cases (ADR-0047), governed Schedules (ADR-0058), Tenant
> lifecycle with SA provisioning and drift reconciliation (ADR-0053), three
> surfaces, and the full approval and control-liveness model
> (ADR-0014, ADR-0065, ADR-0066).

**That is the whole product.** Building all of it before the first evaluation inverts the point of having an MVP. So:

| ADR language                             | Roadmap                           |
|------------------------------------------|-----------------------------------|
| "in v1", "for v1"                        | Somewhere in **Phases 1–4**       |
| "Phase 2", "deferred", "post-v1"         | **Phase 5+**                      |
| "structurally read-only", "denied at L2" | **Phase 1 is where this is free** |

## 2. The MVP: read-only is a complete product, not a crippled one

The single most useful thing the locked decisions give us is that **a read-only agent needs almost none of the expensive
machinery**:

- **ADR-0013** — `system_initiated` runs are structurally read-only, enforced by the capability token never containing a
  write class.
- **ADR-0063 L2** — the platform policy layer is a hard deny that is *not customer-raisable*. Denying every `write` and
  `destructive` ToolClass at L2 is a config fact, not a missing feature.
- **ADR-0067** — *"surface output is not a ToolClass."* The agent narrating its findings into Grafana and Slack flows
  from the event log through surface adapters and **never through the Tool Gateway**. It acts on *us*, not on a customer
  system.

Together those mean **Phase 1 needs no approval flow, no step-up auth, no write credentials, no driver/control model, no
proposal-diff UI** — and is still a coherent product: *an alert fires, the agent investigates, and a narrated finding
with evidence appears where the on-call engineer is already looking.*

ADR-0067 established that this is what on-call actually wants. It is also precisely what you need in order to evaluate
RCA quality.

## 3. What must be right from line one

Irreversible or prohibitively expensive to retrofit. These are not phased.

| Foundation                                                                         | ADR                | Why it cannot wait                                                                   |
|------------------------------------------------------------------------------------|--------------------|--------------------------------------------------------------------------------------|
| `graft_tenant_id` on every row, event, span, audit record                          | ADR-0051           | Adding a scoping key *below* every row later is the rewrite ADR-0051 exists to avoid |
| `FORCE ROW LEVEL SECURITY`, `SET LOCAL` per transaction, no ambient Tenant context | ADR-0050           | Thread-locals plus async task switching is the classic cross-tenant leak             |
| Prefixed identifiers everywhere                                                    | ADR-0059           | Free on day one; a mass rename later                                                 |
| Glossary vocabulary                                                                | ADR-0052           | Naming drift is unpickable once code exists                                          |
| Step decomposition: 1 LLM call = 1 step, 1 tool call = 1 step                      | ADR-0039, ADR-0041 | ADR-0048 names graph decomposition as the least reversible choice                    |
| Event log as the only streaming substrate                                          | ADR-0006, ADR-0030 | Single writer, transactional with run state; retrofitting removes the guarantee      |
| **All** tool access via the Tool Gateway                                           | ADR-0007, ADR-0068 | A direct client is a hole in five controls at once, invisible in the audit chain     |
| `dbos_workflow_id = graft_run_id`                                                  | ADR-0060           | Trivial now, a migration later                                                       |
| Audit actor derived from verified credential                                       | ADR-0015, ADR-0061 | Attribution cannot be reconstructed after the fact                                   |

## 4. Phases

### Phase 1 — Walking skeleton *(MVP; internal only)*

**Goal:** one alert → investigation → narrated finding, end to end, read-only, single region, with section 3's foundations
correct.

**In scope:** ADR-0021 · ADR-0001 · ADR-0009 · ADR-0003 · ADR-0036 · ADR-0037 · ADR-0039 · ADR-0040 · ADR-0041 ·
ADR-0043 · ADR-0048 · ADR-0030 · ADR-0006 · ADR-0029 · ADR-0031 · ADR-0034 · ADR-0007 · ADR-0068 · ADR-0070 · ADR-0018 ·
ADR-0010 · ADR-0013 · ADR-0004 · ADR-0063 (L1/L2/L4) · ADR-0050 · ADR-0051 · ADR-0052 · ADR-0059 · ADR-0005 · ADR-0008 ·
ADR-0071 · ADR-0015 (chain, not yet WORM-anchored) · ADR-0054 (private runs only) · ADR-0062 · ADR-0067 (read class)

**Explicitly deferred:** every write path, approval, Slack, run sharing and the driver model, Schedules, second region,
blue/green, quota ceilings, PAN scrubbing.

**Exit criteria**

- A webhook-triggered run produces a narrated finding in the Grafana plugin with token-level streaming, and survives a
  worker kill mid-run (resumes, no duplicate tool calls).
- Every tool call is a DBOS step; `list_workflow_steps()` returns a readable trajectory.
- RLS proven: a query under Tenant A's GUC cannot see Tenant B's rows, including through a transaction-mode pooler.
- Zero direct clients to customer systems (assert in CI by dependency rule).
- Trajectories visible in the eval sink.

**Quality gates:** lint/type-check; a cross-tenant isolation test suite; crash recovery test; a dependency-direction
test enforcing ADR-0068.

---

### Phase 2 — Multi-tenant and measurable

**Goal:** more than one Tenant, real permission enforcement, and a quality signal you can act on.

**In scope:** ADR-0053 (lifecycle + brownfield backfill) · ADR-0012 · ADR-0022 · ADR-0023 · ADR-0026 · ADR-0056
(roles) · ADR-0016 · ADR-0060 · ADR-0061 · ADR-0020 · ADR-0028 · ADR-0024 · ADR-0017 · ADR-0044 · ADR-0057 (per-run and
per-Tenant caps) · ADR-0042 (idempotency; `fork_workflow` for replay) · ADR-0063 (L3, L5) · ADR-0019 · ADR-0027 ·
ADR-0069 · context compaction

**Exit criteria**

- Two Tenants, isolated, each with provisioned platform SAs and drift detection.
- Check-then-act denies a read the caller's Grafana role forbids.
- An incident-replay suite runs N historical incidents via `fork_workflow` and produces a comparable score between two
  prompt versions.
- A run hitting its per-run cap terminates gracefully with its best hypothesis, never a bare failure (ADR-0057).

---

### Phase 3 — Write actions, approval, and Slack

**Goal:** propose → approve → execute, plus the second surface.

**In scope:** ADR-0002 (Slack) · ADR-0014 · ADR-0065 · ADR-0066 · ADR-0032 · ADR-0064 · ADR-0072 · ADR-0033 · ADR-0045 ·
ADR-0011 · ADR-0016 (step-up) · ADR-0067 (`write` class) · ADR-0034 (diff view) · ADR-0054 (sharing/promotion)

**Order matters:** control liveness (ADR-0066) must land **with or before**
approval, because ADR-0065 makes control equal authority — shipping handover without the three clocks means approval
authority with no expiry.

**Exit criteria**

- A proposed change is approved in Grafana by a re-authenticated driver, bound to
  `proposal_hash`, and the audit chain shows proposer-context and approver separately with the control transfer as a
  `caused_by` edge.
- Slack can trigger and converse but **cannot** approve; an unlinked Slack user gets a link prompt, not a run
  (ADR-0061).
- A disconnected driver auto-releases; control goes to nobody (ADR-0066).

---

### Phase 4 — Production hardening *(v1 GA)*

**In scope:** ADR-0025 (PAN scrubbing) · ADR-0015 (WORM anchoring, 12-month retention) · ADR-0038 (reaper) · ADR-0046
(blue/green) · ADR-0047 (timers) · ADR-0058 (Schedules) · ADR-0035 (notification) · ADR-0049 (second region, Tenant
Directory) · ADR-0057 (quota request flow)

**Exit criteria:** colour retirement gated on a machine check, not a human eyeball (ADR-0046); PANs demonstrably
stripped before reaching either sink; cross-region read proxy returns without persisting outside the home region.

---

### Phase 5 — Post-v1

ADR-0004 (micro-VM sandbox behind the `ToolExecutor` seam) · ADR-0002 (custom web frontend) · ADR-0029 (AG-UI adapter,
web only) · memory & knowledge · ADR-0067's
`write`/`destructive` paging classes — noting maintenance windows and notification suppression are **permanently
L2-denied** and need their own decision, never a phase.

## 5. Sequencing rules

1. **Nothing in section 3 is phased.** It lands in Phase 1 or the phase plan is void.
2. **Read-only until Phase 3.** Enforced at L2, so it is a policy row, not discipline.
3. **ADR-0066 ships with ADR-0065**, never after.
4. **No surface ships before its identity story** — Slack requires ADR-0061.
5. **Evaluation capability is Phase 2, not Phase 4.** If quality is only measurable at the end, the phases before it are
   unfalsifiable.

## 6. Decision gates — what must be clarified before each phase

**Two items gate Phase 1.** Both are cheap selections. S1 closed on
2026-09-13 (see [ADR-0039](../adr/agent/0039-the-run-is-the-durable-workflow.md),
[ADR-0040](../adr/agent/0040-langgraph-is-compiled-with-no-checkpointer.md),
[ADR-0041](../adr/agent/0041-step-granularity-is-one-llm-call-or-one-tool-call.md)).
Each remaining item has a self-contained brief in [`spikes/`](./spikes/README.md), written to
be taken into its own session.

| #      | Item                                                                                                   | Gates           | Why it blocks                                                                                                                                                                                                                  | Cost        |
|--------|--------------------------------------------------------------------------------------------------------|-----------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------|
| **S3** | Langfuse vs Phoenix for the eval sink                                                                  | **Phase 1**     | "Start testing and evaluating" requires somewhere to *look at* trajectories from day one                                                                                                                                       | ~1 day      |
| **S4** | Provisional model + serving choice                                                                     | **Phase 1**     | Phase 1 needs a model. ADR-0057 forbids mid-run degradation but picks nothing. A provisional choice is enough; the full routing session is Phase 2                                                                             | ~1 day      |
| **S5** | Context compaction mechanics                                                                           | **Phase 2**     | Locked hierarchy, unlocked mechanics ([`../design/context-assembly.md`](../design/context-assembly.md) section 3). Long investigations overflow without it — but Phase 1 runs are short enough to defer                               |             |
| **S6** | Eval methodology: ground truth, metrics, corpus size                                                   | **Phase 2**     | `fork_workflow` is the mechanism (ADR-0040); "good" is undefined. Phase 1 can rely on qualitative trajectory review                                                                                                            |             |
| **S7** | HITL & write-action model; two-person rule                                                             | **Phase 3**     | Re-openable now that ADR-0055 is superseded                                                                                                                                                                                    |             |
| **S8** | Quota numbers; Schedule defaults (proposed 10 / 1 h); ITSM vs deep link                                | **Phase 2 / 4** | Needs real cost data — deliberately deferred until there is some                                                                                                                                                               |             |
| **S9** | Tenant Directory substrate                                                                             | **Phase 4**     | Single region until then                                                                                                                                                                                                       |             |

**S2 is closed by [ADR-0073](../adr/platform/0073-dbos-system-database-is-separate-and-pci-scoped.md).** Its findings determine the Phase 1 topology, RLS boundary and PCI treatment. S3 and S4 are a day's work and can run in parallel.

Everything else resolves inside the phase that needs it. **The backlog does not need clearing before the roadmap is finalised** — it is not a prerequisite planning round.

## 7. What this roadmap deliberately does not do

- **No estimates.** Phase content is decided; duration is not, and the Phase 1 shape is now settled.
- **No parallel tracks.** Phases 1–3 are strictly ordered by the sequencing rules.
- **No "Phase 0".** Section 3's foundations are not a phase; they are the definition of done for every phase.
