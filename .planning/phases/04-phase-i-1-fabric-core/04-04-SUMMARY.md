---
phase: 04-phase-i-1-fabric-core
plan: 04
subsystem: graph-assembly-single-writer
tags: [l2, l3, graph-store, single-writer, conformance, bitemporal, sqlite]
requires:
  - 04-01 (packaging, pytest/mypy config, CI)
  - 04-02 (CINV lints — the ccf.graph._writer import restriction this plan builds on)
  - 04-03 (CCFContract, canonical_bytes/content_hash, claims, SignalEnvelope, ControlPlaneRegistry)
provides:
  - GraphReader / GraphWriter Protocols + GraphView / EntityRecord / RelationshipRecord / UpsertResult
  - SQLite reference GraphStore — compound uniqueness at the persistence tier, append-only claims, lineage set-union, supersession, bitemporal as-of reads
  - the parametrized six-semantics conformance suite (the acceptance bar the Postgres wave implements against)
  - AssemblyWorker — L2's sole write path, with the EntityResolutionStrategy seam and the L2 admission entry point
  - boot.py composition root + BootToken backstop (CINV-04 single-writer leg)
  - canonical_timestamp — the one text rendering backends may store
affects:
  - every later plan reads the graph through GraphReader and writes only via AssemblyWorker; no plan needs (or can get) a writer
  - the Postgres wave (D-11) adds a param to graph_backend and a writer class to ccf.graph._writer — it does not add a writer module
  - operator/projection plans get GraphView as their pure-function input; its deterministic ordering is what makes bit-for-bit composition tests possible
tech-stack:
  added:
    - stdlib sqlite3 (no ORM — physical layout is backend-internal per D-IMPL-34)
  patterns:
    - node-identity table + append-only claim table, so "one node per (tenant, uri)" and "every claim survives" are simultaneously true
    - claim content identity excludes lineage and observed_at, so corroboration accumulates instead of manufacturing supersessions
    - supersession chain restitched by observed-time on every append — idempotent, and correct for late-arriving observations
    - capability token minted per graph identity, consumed by exactly one writer
key-files:
  created:
    - src/ccf/graph/__init__.py
    - src/ccf/graph/protocols.py
    - src/ccf/graph/_writer.py
    - src/ccf/graph/backends/__init__.py
    - src/ccf/graph/backends/sqlite.py
    - src/ccf/assembly/__init__.py
    - src/ccf/assembly/worker.py
    - src/ccf/boot.py
    - tests/conformance/__init__.py
    - tests/conformance/test_graphstore.py
    - tests/invariants/__init__.py
    - tests/invariants/test_single_writer_boot.py
    - tests/assembly/__init__.py
    - tests/assembly/test_worker.py
  modified:
    - tests/conftest.py
    - src/ccf/contracts/canonical.py
decisions:
  - "Claim content identity (claim_id) is content_hash over the claim's non-lineage, non-observed_at fields. Excluding lineage keeps a claim addressable while its evidence grows (INV-CH7-17); excluding observed_at means a source repeating unchanged state corroborates rather than superseding — including it would manufacture a supersession per repeat."
  - "Node identity and claim history live in separate tables. UNIQUE(tenant_id, entity_uri) on the node table puts compound uniqueness at the persistence tier (INV-CH7-16) while the claim table stays append-only (INV-CH7-04); one table could not carry both."
  - "The supersession chain is recomputed for the whole node on every appended claim rather than only linking the newest. Idempotent, and it makes a late-arriving observation slot into history already superseded instead of wrongly displacing state the fabric learned later."
  - "Every backend's writer class lives in ccf.graph._writer, not next to its reader. A backend shipping its writer beside its reader would leave the CINV-02 lint guarding one module while the real write path lived unguarded."
  - "Single-writer is keyed on graph identity (the database path), not on 'one boot per process'. The invariant is one writer per graph; a process-wide singleton would forbid multi-fabric hosting and would pass the double-boot test for the wrong reason."
  - "FabricHandle.close() releases the graph for a subsequent boot and simultaneously invalidates the writer. Release without invalidation would permit two live writers; no release would make a configuration typo strand the database until process restart."
  - "AssemblyWorker types its handle as the GraphWriter Protocol and does not import the concrete writer — L2 is substrate-neutral, and ccf.boot is the sole importer. See deviation 1."
  - "valid_from opens at the source's observed_time when the source can say and at ingestion when it cannot; observed_at is always ingestion. Stated reconciliation rule, not a silent default (D-IMPL-38) — the fabric never claims to have known something before it did."
  - "The policy bundle is resolved once at worker construction (i.e. at boot) rather than per write: it validates the pin while the fabric can still refuse to start, and keeps the Control Plane audit log from filling with one identical entry per claim."
metrics:
  duration: ~35 min
  completed: 2026-07-25
  tasks: 3
  commits: 3
---

# Phase 4 Plan 04: Graph, Assembly, and the Single-Writer Invariant Summary

L2 and L3 land together with the D-IMPL-41 stack wired end to end: a
reader/writer Protocol split, a SQLite backend that cannot write, a writer
module no one may import, a composition root that mints one capability token
per graph, and a conformance suite that drives all of it through the real boot
path because there is no other way in.

## What Was Built

**Task 1 — Protocols and the red conformance suite** (`35978f5`).
`ccf.graph.protocols` declares `GraphReader` and `GraphWriter` as separate
`typing.Protocol`s. The split is the seam the rest of the enforcement hangs on:
a read-path constructor has no parameter that *could* accept a write handle, so
the absence is a property of the type rather than of anyone's discipline
(INV-CH7-10, INV-CH7-15). `GraphView`, `EntityRecord`, and `RelationshipRecord`
are frozen contracts — an operator is a pure function over graph state, and
state that can change underneath it is not a value it can be pure over — with
deterministic ordering so canonical serialization of a view is stable, which is
the precondition for the bit-for-bit composition assertions the operator plan
will make.

The 12-test conformance suite was written first and confirmed red (12 collection
errors, no composition root yet). It is parametrized on a `graph_backend`
fixture whose single `sqlite` param the Postgres wave extends without touching a
test body (D-16). Two disciplines are enforced in the suite itself: nothing
constructs a writer, and every comparison runs over `canonical_bytes` of
contracts rather than raw rows — SQLite and Postgres disagree about timestamp
precision and row order, and the contract layer does not (Pitfall 3).

**Task 2 — the SQLite reference backend** (`77510c7`). Five tables, none of them
normative. `entities`/`relationships` carry node identity with
`UNIQUE (tenant_id, entity_uri)` — compound uniqueness *at the persistence
tier*, where a buggy caller still cannot get around it, unlike an
application-layer check. `entity_claims`/`relationship_claims` are append-only:
rows are never deleted, claim content is never updated, and the only columns
that change after insert are `superseded_by`/`superseded_at`, which is what
supersession *is*. `lineage` is keyed on the full entry identity, so
`INSERT OR IGNORE` gives L set-union for free — a re-delivered envelope collides
and is dropped, a second source does not (INV-CH7-17). Splitting node identity
from claim history is what lets "one node per `(tenant, uri)`" and "every claim
ever made survives" both be true.

`backends/sqlite.py` deliberately contains no way to write. Every `INSERT` and
every supersession `UPDATE` lives in `ccf.graph._writer`, and that module's
docstring states the rule that keeps the lint meaningful: a new backend adds a
writer *class* there, never a writer *module* elsewhere.

**Task 3 — AssemblyWorker, boot, and the CINV-04 boot check** (`c453e16`). The
worker runs three of L2's four converging concerns for the slice: spec-driven
entity resolution behind the D-IMPL-35 strategy seam (URIs of the INV-CH7-18
form `<entity-class>://<identity-hash>`, minted from *user-declared* identity
keys, so two systems naming the same counterparty converge without either
knowing about the other and the URI survives a source migration); bitemporal
stitching under a stated rule; and policy binding stamped on the way in, because
the fabric does not persist state first and ask who may see it afterwards
(INV-CH7-03). `admit_entity_claim` / `admit_relationship_claim` are the
DESIGN.md §2A.5.4 step-5 admission path — a claim that did not originate in this
fabric's L1 still enters L3 *through L2*.

`boot.py` is the one place a writer is constructed. It mints a capability token
per graph identity, hands it to exactly one writer, injects that writer into the
worker, and returns a `FabricHandle` carrying reader, worker, and registry —
with shutdown behind a closure, so there is no writer attribute to reach for,
private or otherwise. Its docstring carries DESIGN.md §9's residual claim
verbatim: *no unforced path exists, and every forced path fails CI or fails at
boot* — never absolute prevention.

## Key Implementation Details

- **Corroboration versus supersession.** `claim_id` excludes both lineage and
  `observed_at`. Including lineage would move a claim's identity every time a
  second source confirmed it, making "the same claim" unaddressable; including
  `observed_at` would turn every repeated source poll into a supersession event
  and fill the graph with history that never happened.
- **The chain is restitched, not appended to.** Every appended claim recomputes
  the node's whole supersession chain by observed-time. That is idempotent, and
  it is what makes a *late-arriving* observation slot into history already
  superseded rather than wrongly displacing state the fabric learned later.
- **One writer per graph, not per process.** A process-wide singleton would pass
  the double-boot test for the wrong reason and would make multi-fabric hosting
  impossible. `test_booting_distinct_graphs_is_fine` exists to pin that down.
- **Closing is shutdown, not an escape hatch.** `close()` invalidates the writer
  *and* releases the graph. Either half alone is a bug: release-without-
  invalidation permits two live writers; no-release makes a configuration typo
  strand the database until process restart (`test_a_failed_boot_leaves_the_
  graph_bootable`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Architectural fidelity] `ccf.assembly.worker` does not import the concrete writer**

- **Found during:** Task 3
- **Issue:** The plan's `key_links` expects `worker.py → ccf.graph._writer`.
  Importing the concrete SQLite writer into L2 would couple assembly to one
  storage substrate, contradicting DESIGN.md §2A.3.1 (L2 "writes exclusively
  through `GraphWriter`", the *Protocol*) and D-IMPL-34's whole reason for the
  interface split.
- **Fix:** `AssemblyWorker` types its handle as the `GraphWriter` Protocol;
  `ccf.boot` is the sole importer of `ccf.graph._writer`. The plan's acceptance
  criterion — that only files under `src/ccf/assembly/` and `src/ccf/boot.py`
  import the writer — holds, satisfied by `boot.py` alone, and is asserted as a
  test (`test_only_l2_and_the_composition_root_name_the_writer_module`) as well
  as by the CINV-02 lint.
- **Files modified:** `src/ccf/assembly/worker.py`, `src/ccf/boot.py`
- **Commit:** `c453e16`

**2. [Rule 3 - Blocking] `canonical_timestamp` added to `ccf.contracts.canonical`**

- **Found during:** Task 2
- **Issue:** The backend must store timestamps as text. Formatting them in the
  backend would define a *second* canonical form — the one thing that module
  exists to prevent — and would reintroduce the cross-backend precision drift of
  Pitfall 3.
- **Fix:** Exported `canonical_timestamp()` from the existing normalizer, so the
  text a backend stores is the text the serializer produces. `canonical.py` was
  not in the plan's `files_modified`; the alternative was duplicating the format.
- **Files modified:** `src/ccf/contracts/canonical.py`
- **Commit:** `77510c7`

**3. [Rule 2 - Missing coverage] `tests/assembly/test_worker.py` added**

- **Found during:** Task 3
- **Issue:** Task 3's `<behavior>` block specifies the `ingest` path (resolution,
  stitching, policy binding), but the plan's only Task 3 test file is the boot
  check. The L1→L3 path would have shipped asserted only indirectly.
- **Fix:** Ten tests covering URI convergence across source systems, replay
  idempotence, both stitching branches, partial-identity refusal, the
  no-rule-matched case, policy stamping, and boot-time refusal on an
  unregistered policy pin.
- **Commit:** `c453e16`

### Interpretations

- **`GraphView` placement.** The plan says "a frozen contract from
  `ccf.contracts`". It is defined in `ccf/graph/protocols.py` as a `CCFContract`
  subclass — built *on* the contracts base, but living beside the Protocol it is
  the return type of, which keeps `files_modified` accurate and avoids a
  contracts module that imports graph vocabulary.
- **Writer signature.** The plan's interfaces block shows
  `upsert_entity(*, tenant_id, entity, lineage)`. `EntityClaim` as landed in
  04-03 already carries `lineage`, so passing it separately would create two
  sources of truth for the L axis. The shipped signature is
  `upsert_entity(*, tenant_id, claim, policy_bundle_version)` — lineage travels
  on the claim, and the added argument is what makes policy binding at write
  time structural rather than optional.
- **`ON CONFLICT` location.** The acceptance criterion greps
  `backends/sqlite.py` for `ON CONFLICT`, but the same task instructs that the
  concrete writer live in `_writer.py`. Upsert is write SQL, so it is in
  `_writer.py` (2 occurrences); `backends/sqlite.py` has none *because* it has no
  write path at all, which is the stronger reading of the plan's intent.
- **`grep -rl "ccf.graph._writer" src/`** returns six files because the module is
  *named* in several docstrings explaining the invariant. Import-level, the
  answer is `src/ccf/boot.py` alone — asserted by the invariant test's regex over
  real import statements and by the CINV-02 lint.

## TDD Gate Compliance

Task 1 ran a clean RED → GREEN: the conformance suite was committed failing
(12 collection errors) at `35978f5` and turned green at `77510c7`/`c453e16`.

**Task 3's boot check was written after `boot.py`, not before.** The
implementation and its test landed in one commit (`c453e16`). D-15 mandates
tests-first for invariants, and this is a genuine shortfall against that
discipline rather than a reinterpretation of it — recorded here rather than
smoothed over. Mitigating facts: the eight assertions were not tuned to the
implementation (the retired-writer release semantics and the failed-boot
recovery path were both *specified in the tests first* and are why `close()` and
boot's rollback exist in their current form), and one test caught a real defect
in the sibling assembly suite (`test_partial_identity_is_refused_rather_than_
hashed` initially asserted an unreachable branch and was rewritten to exercise
the guard directly rather than deleted).

## Verification

| Check | Result |
|---|---|
| `.venv/bin/pytest tests -q` | 73 passed |
| `.venv/bin/pytest tests/conformance -q` (six D-IMPL-34 semantics) | 12 passed |
| `.venv/bin/pytest tests/invariants -q` (CINV-04 single-writer leg) | 8 passed |
| `.venv/bin/python -m tools.lints --all` | exit 0, zero allowlist entries added |
| `.venv/bin/pytest tools/lints/tests -q` | 45 passed |
| `.venv/bin/mypy --strict src` | Success, 19 source files |
| `grep -cE 'f"(INSERT\|UPDATE\|SELECT\|DELETE)'` on backend + writer | 0 — no f-string SQL |
| `grep -ci "DELETE FROM"` on backend + writer | 0 — nothing is ever deleted |
| `ON CONFLICT` upsert present | 2 occurrences (`_writer.py`; see Interpretations) |
| Import-level importers of `ccf.graph._writer` under `src/` | `ccf/boot.py` only |
| Conformance tests collected and parametrized | 12, all `[sqlite]` |
| No writer construction in test bodies (`grep -c "SqliteGraphStore("` in conformance) | 0 |
| RED before GREEN, Task 1 | confirmed (12 collection errors at `35978f5`) |
| Post-commit deletion check, all 3 commits | no deletions |

## Known Stubs

None. Two bounded-scope notes, both intentional and both named in the plan:

- The policy bundle in the test fixture is a placeholder artifact — what this
  plan owes is that a *version* of it is resolved from the Control Plane and
  stamped onto every claim, which is asserted; the bundle schema belongs to the
  policy subsystem plan.
- `SpecDrivenEntityResolution` is the deterministic reference strategy
  (D-IMPL-35). Probabilistic matching, precedence, and survivorship are
  deployment plugins behind the `EntityResolutionStrategy` Protocol, per the
  ruling — the seam is real, not a placeholder.

## Threat Flags

None. The three registered threats are mitigated as planned: T-04-07 (second
writer) by the four-layer stack plus eight boot-check assertions; T-04-08 (SQL
injection) by parameterized statements only, grep-gated above; T-04-09
(cross-tenant reads) by persistence-tier compound uniqueness, keyword-only
`tenant_id` on every reader and writer method, and a writer-side refusal when a
claim's tenant disagrees with its call scope rather than the fabric silently
picking one.

## Self-Check: PASSED

All 14 created files and 2 modified files exist on disk; all three commit hashes
(`35978f5`, `77510c7`, `c453e16`) are present in `git log`.
