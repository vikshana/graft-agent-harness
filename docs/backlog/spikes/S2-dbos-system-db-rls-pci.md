# S2 — DBOS system database vs `FORCE ROW LEVEL SECURITY` and PCI scope

> **Gates: Phase 1 and C4 L3. Timebox: 4 days.**
> Determines the Phase 1 database topology. Retrofitting isolation onto a
> third-party schema is expensive; getting it right costs nothing now.

---

## 1. The questions

Two, related, both must be answered:

**(a) Placement and isolation.** Can DBOS Transact's system database live
alongside our application tables without compromising ADR-0050's isolation
model — `FORCE ROW LEVEL SECURITY`, `SET LOCAL graft.tenant_id` per transaction,
no ambient Tenant context — and does it survive a transaction-mode pooler?

**(b) Compliance scope.** Does the DBOS system database fall **inside PCI-DSS
scope** (ADR-0025)? It persists workflow inputs, outputs and step results, which
could carry a PAN quoted from an investigated log line.

## 2. Why this blocks Phase 1

- ADR-0051 and ADR-0050 require the scoping key and RLS to exist **before
  anything writes rows**. The DBOS system tables are rows we do not control.
- ADR-0050 states two hard rules that a third-party library can silently break:
  `SET LOCAL` never `SET`, and `FORCE ROW LEVEL SECURITY` because the
  application role is typically the table owner and would otherwise bypass every
  policy.
- ADR-0048 named **Postgres connection count (pooler, not engine)** as the
  binding scale constraint — so pooler compatibility is not a detail.
- ADR-0037 risk X1 already flagged PCI scope extending to the system database and
  handed it to the Evals session. **It is being pulled forward** because it
  changes the Phase 1 schema, not just the compliance paperwork.

## 3. Constraints — do not relitigate

| Constraint | ADR |
|---|---|
| Isolation is exactly three mechanisms: run-scoped capability token, Tool Gateway credential resolution, **Postgres RLS on `graft_tenant_id`**. Never thread-level | ADR-0050 |
| RLS established per transaction with `SET LOCAL`, never `SET` | ADR-0050 |
| `FORCE ROW LEVEL SECURITY` is required | ADR-0050 |
| No ambient or thread-local Tenant context — scope travels as an explicit argument through the `runtime` seam | ADR-0050, ADR-0048 |
| One `graft_tenant_id`, on every row, event, span and audit record | ADR-0051 |
| Our durable event log is Postgres, single writer, transactionally consistent with run state | ADR-0030 |
| **Steps return pointers, never large payloads**; artifacts live in object storage | ADR-0041 |
| `dbos_workflow_id = graft_run_id` | ADR-0060 |
| One DBOS system database per region; no cross-region recovery | ADR-0049 |
| Compliance regime is PCI-DSS; PAN detection must strip **before** data lands, not redact after | ADR-0025 |

## 4. Method

### E1 — Inventory the system schema
Stand up DBOS against a scratch Postgres. Enumerate every table it creates, and
for a representative run record **exactly what is persisted**: workflow inputs,
step return values, child-workflow arguments, queue entries, `send`/`recv`
message bodies (ADR-0045).

*This inventory is the input to question (b).*

### E2 — Same database or separate?
Determine whether DBOS requires its own database, tolerates its own schema in
our database, or assumes ownership of the connection. Test both topologies.

### E3 — RLS interference
With `FORCE ROW LEVEL SECURITY` enabled on our tables:
- Do DBOS's own connections and migrations still work?
- Does DBOS run as table owner or superuser, and would its migrations bypass our
  policies?
- Can DBOS's system tables themselves carry a `graft_tenant_id` policy, or is
  Tenant isolation for workflow metadata necessarily enforced elsewhere?

### E4 — `SET LOCAL` survival
Confirm DBOS does not reset, pool, or reuse a session in a way that leaks
`graft.tenant_id` across transactions. **Specifically test under pgBouncer in
transaction mode** — the case ADR-0050 was written to defend against.

### E5 — Connection behaviour
Measure connections held per concurrent workflow, and whether DBOS holds session
state that is incompatible with transaction-mode pooling. Feed the number back
to ADR-0048's scale note.

### E6 — Migration story
How do DBOS schema migrations interact with ours? Same tool, separate tool,
ordering constraints, and what happens on a DBOS version upgrade mid-deploy
(relevant to ADR-0046's blue/green).

### E7 — PCI determination
From E1's inventory, decide whether the system database is in scope. Test the
mitigation: **if ADR-0041's pointer rule is honoured strictly, do PANs ever reach
the system tables at all?** Try deliberately violating it (return a raw log blob
from a step) and confirm what lands.

## 5. Outcomes and what each means

| Outcome | Action |
|---|---|
| **Separate database, no RLS interference** | Cleanest. Document the topology; PCI question narrows to whether workflow metadata alone is sensitive |
| **Same database, coexists cleanly** | Document; confirm ADR-0030's transactional consistency with run state still holds |
| **DBOS bypasses or breaks RLS** | Serious. Tenant isolation for workflow metadata must come from elsewhere — likely separate databases per region *and* strict pointer discipline. May require an ADR amending ADR-0050 |
| **Transaction-mode pooling incompatible** | Directly contradicts ADR-0048's scale assumption. Escalate — this changes the deployment shape |
| **System DB is in PCI scope** | ADR-0041's pointer rule is promoted from a design preference to a **hard, lint-enforced invariant**, and the system DB inherits ADR-0025's scrubbing and ADR-0015's retention |

## 6. Deliverables

1. The E1 inventory table — what DBOS persists, per run.
2. **One ADR** on system-database placement and PCI scope.
3. Updates to [`../../design/tenancy-and-scoping.md`](../../design/tenancy-and-scoping.md)
   (RLS pattern) and [`../../design/durable-execution.md`](../../design/durable-execution.md)
   (topology, X1 closed).
4. If the pointer rule becomes load-bearing: a CI lint that fails a step
   returning anything but a pointer, added to `scripts/`.
5. Delete this file.

## 7. Out of scope

The PAN detector itself (Luhn-check implementation) — that stays with the Evals
session per ADR-0025. This spike decides **whether the system database needs
one**, not how it works.
