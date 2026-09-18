# D-IMPL-344 — Retention and Reconstruction of Admitted Children on Composite Refusal — DESIGN

**Status:** IMPLEMENTED on this branch, awaiting review (2026-09-16); not merged. §1–§8
are the design as ruled (implementation GO with R-1/R-2/R-3 and three corrections,
`docs/DECISIONS.md`); §9 is the as-built synchronization, including the one deviation
from R-1's wording and the sabotage record.

**Branch / baseline:** `d-impl-344-retention`, forked from the approved `main` at
**`af91c7da`** (`origin/main` = `main` = `af91c7da`, verified before the fork; the
`D-GATE-343` merge). Every line reference below is at that SHA.

**Decision id, verified:** `docs/DECISIONS.md` carried no `D-IMPL-344` entry and its
footer read *"Next free decision id: `D-IMPL-344`"*; `D-IMPL-345` appears nowhere in
the file. The entry this design opens is `D-IMPL-344`; the footer advances to `345`.

**What this design is for.** `CP14-F-32`, measured at CP-14 Gate 2 slice 2
(`cp-14-gate-2-slice-1 @ 51c12fe1`): a composite that admitted at least one child and
then refused cannot be replayed from the store that recorded it. Classified
**launch-blocking SDK capability** (`docs/EXAMPLE-EVALUATION-CRITERIA.md` §B.1 — §D
*"replay and reconstruct"* and *"preserve sufficient refusal evidence"*; §C step 1:
no). Dave's rule for it: *"If reconstructing the refused parent requires those bytes
and no retained immutable artifact resolves the address, classify F-32 as a
launch-level replay defect and STOP. Do not copy bytes into CP-14 to repair it."*

**Boundary with the neighbors, stated once.** *344 retains contracts for admitted
children when the parent refuses. `D-IMPL-342` preserves the original reason and
reference when the child itself refuses.* `D-IMPL-341` (TTL anchor) and `CP14-F-33`
(a paved seam for post-traversal aggregation) are untouched.

---

## 1 · The defect, as measured

Three facts, each with its line:

1. **Admitted-child bytes are retained on the non-blocking path only.**
   `src/ccf/products/resolver.py:2137` runs `resolve_child_outcomes`; at `:2143` the
   branch splits on `resolved.blocking`. The blocking arm (`:2144–2148`) builds a
   `CompositionOutcome` with the rows and the refusal and never retains anything; the
   non-blocking arm (`:2150–2155`) derives `child_contract_view(resolved)` and calls
   `self._retain_child_contracts(children)`. `D-IMPL-338` made the rows survive every
   exit; `D-IMPL-339`'s byte retention did not follow them.
2. **Replay reads bytes for any admitted row.** `src/ccf/replay/engine.py::_children_of`
   selects every row with `outcome_status == CHILD_ADMITTED` and calls
   `src/ccf/replay/engine.py::_reconstruct_child_contracts`, which raises `ReplayUnresolvable` when the
   store has no artifact at the row's `child_content_address`.
3. **Nothing else resolves the address.** Producer stores hold the record and the
   query pins, never the served product's bytes (the record names
   `product_content_address`; `tests/examples/test_cp_14_second_slice.py:257,301`
   assert `ArtifactNotFound` on the producer side). The admitted contract exists in
   exactly one place after the serve — the parent's process memory — and is gone when
   it exits.

Measured on both slice-2 records (tolerance `0.25`: family admitted, spread withheld;
`1.0`: spread and family admitted, three slots unreachable): `replay()` raises
*"the child contract '…' is not retained in the store"* before reaching the
environment. Held, at the time of measurement, by the slice-2 proof
`test_f32_a_refused_composite_that_admitted_a_child_cannot_be_replayed_from_its_own_store`
(`cp-14-gate-2-slice-1 @ 51c12fe1`); converted at implementation into the positive proof
`tests/examples/test_cp_14_second_slice.py::test_f32_a_refused_composite_that_admitted_a_child_is_reconstructed_from_its_own_store`
(§9).

**A fourth fact this design must not hide.** The replay engine has **no refusal
branch at all** today. `replay()` (`:758`) resolves the record, checks generation,
bindings and the resolution claim, reconstructs children, then unconditionally
resolves a plan (`:852`), operators (`:859`), re-executes (`:867`), and rehydrates a
product (`:946`) held to `path.product_content_address` (`:950`). A refusal record
carries `plan_id = NO_FABRIC_READ` and `product_content_address = NO_PRODUCT_ADDRESS`
(`src/ccf/replay/record.py::build_replay_record`), and `ReplayOutcome` (`src/ccf/replay/engine.py::ReplayOutcome`) requires
a `product`. No test in `tests/replay/` replays a refusal record of any kind. So
retaining the bytes moves the failure from *missing child* to *no plan named
`no-fabric-read`* — which is exactly the outcome Dave's instruction refuses to count
as closure. §4 is the design for the rest of the distance.

---

## 2 · The invariant, locked

> **Admitted-child contracts must be retained by exact content address whenever the
> parent records their admission, whether the parent subsequently serves or refuses.
> Retention follows admission, not composition success.**

Three things stay distinct, and the record keeps them distinct today:

| thing | what it is | where it lives | changed by 344? |
|---|---|---|---|
| **child-resolution rows** | what happened to each declared requirement — `outcome_status` from the closed vocabulary `src/ccf/replay/record.py::CHILD_OUTCOME_STATUSES`, `child_content_address`, producer identity, question address | dimension 5, `ContentGenerationPath.child_resolutions` (`src/ccf/replay/record.py::ContentGenerationPath`) | **no** — shape and content unchanged |
| **retained child contracts** | the exact bytes of every child that was *admitted*, filed under `src/ccf/products/composite.py::ADMITTED_CHILD_CONTRACT_CLASS` at `content_hash(contract)` | the parent's own `ArtifactStore`, one artifact per distinct address | **yes** — now filed on every exit that recorded an admission |
| **parent outcome** | served (a `ServedProduct` and a record naming a product address) or refused (a `RefusalEnvelope` and a record whose dimension 5 carries the refusal block) | the record; dimension 5 `assembly_refusal` (dimension 5, `src/ccf/replay/record.py::ContentGenerationPath`) | **no** |

Consequences the invariant forces, each stated so the proof can check it:

- **A partially admitted set is the normal case, not an edge.** One child admitted,
  a required sibling refused or unreachable, the parent's projection never run: the
  admitted child's bytes are retained; the sibling has a row and no bytes; the record
  names `NO_FABRIC_READ`.
- **`ChildContractView` is not the prerequisite.** `child_contract_view`
  (`src/ccf/products/composite.py::child_contract_view`) raises on a blocked resolution by design (`D-IMPL-339` Q2);
  retention must read `resolved.admitted` directly and never build a view over a
  composition already known not to compose.
- **Nothing is retained as admitted that was not admitted.** `AdmittedChild`
  (`src/ccf/products/composite.py::AdmittedChild`) is minted only by `CompositeAdmissionGate.admit`
  (`src/ccf/products/composite.py::CompositeAdmissionGate`); `ChildOutcomeResolution.admitted` (`:1621`) holds only those.
  A candidate rejected at admission, a refused child, an absent optional and an
  unreachable producer all have rows and never a retained contract. Zero admissions
  means zero artifacts filed.
- **Rows carry addresses, never bytes.** No duplicate contract bytes enter any row;
  the address is the join between the row and the retained artifact, as `D-IMPL-339`
  already has it on the served path.

---

## 3 · Retention — the exact point, and what failure does

**Where.** `src/ccf/products/resolver.py`, inside `GovernedResolver.__call__`'s
composite branch, immediately after `resolve_child_outcomes` returns (`:2137–2142`)
and **before** the `if resolved.blocking:` split at `:2143`:

```
resolved = resolve_child_outcomes(...)
self._retain_child_contracts(child.contract for child in resolved.admitted)   # NEW position
if resolved.blocking:
    composed = CompositionOutcome(factors=None, resolutions=resolved.rows, refusal=resolved.refusal)
else:
    children = child_contract_view(resolved)          # unchanged; no longer followed by retention
```

That is the earliest point at which every admitted contract of this composition is
verified and re-bound (`D-IMPL-336` Amendment 3, `D-IMPL-337` provenance) and no
child-dependent computation has run. It precedes both refusal exits that can follow
an admission:

- the **pre-projection** blocking refusal at `:2156–2176` (`execution=None`, rows
  passed as `child_resolutions=composed.resolutions`);
- the **post-projection** gate and tolerance refusals at `:2514–2536` and
  `:2619–2639` (`execution=execution`, `child_resolutions=child_rows`), which already
  sat downstream of retention on the non-blocking path and stay there.

**Mechanism.** The existing `_retain_child_contracts` (`:2686`) generalized to take an
iterable of contracts instead of a `ChildContractView`: same class constant, same
`content_hash` address, same `exists()` short-circuit (idempotent by address — a
child consumed twice is filed once), same `RuntimeError` when the store files at an
address other than the contract's hash. No new artifact class, no new store method,
no row change, no record-shape change.

**If persistence fails.** `artifact_store.put` raising propagates out of `__call__`
before `_record_refusal` runs — the same posture `_record_refusal` documents at
`:2722` (*"a failure to record is a failure to serve … and 24.6-07 extends that
sentence to a governed 'no'"*). No refusal envelope is returned and no record is
written, so a record claiming an admitted child whose bytes are not resolvable
cannot be minted by this path. The address-mismatch `RuntimeError` behaves the same
way. This is the existing failure posture reused, not a new one; the served path
already fails exactly like this at `:2155`.

**What retention does not do.** It does not retain a refused child's product (there
is none in the parent's hands; the child's own reason and reference are `D-IMPL-342`),
does not touch the producer's store, and does not copy anything into an example.

---

## 4 · Reconstruction — the refused decision, from the parent's store, producers stopped

Retention is necessary and, on its own, **not** sufficient evidence (§1, fourth fact).
This section is what "the recorded refusal can be replayed" means for each of the two
refusal shapes, using the engine's existing steps wherever they apply and naming the
one place they do not.

### 4.1 What the store holds for a refused composite after 344

The record at the envelope's `replay_reference`; one retained artifact per admitted
row's `child_content_address`; the query pins if a projection ran. Dimension 5 of the
record carries: the rows; `assembly_refusal`, which is the **refusal envelope's own
canonical bytes** (`src/ccf/replay/record.py::mint_assembly_refusal` — "the canonical bytes
of the refusal, decoded"), so the refusal's kind, its `reason` and, for a child
admission refusal, its `product_class` (`src/ccf/products/composite.py::ChildAdmissionRefusal`) are recoverable by
rehydration and never inferred; `plan_id`, `steps`, `graph_query_sequence` and
`product_content_address` stating positively whether a projection ran and that no
product exists.

### 4.2 Refusal before projection

The record's own claims: `plan_id == NO_FABRIC_READ`, `steps == ()`,
`operator_plan == ()`, `graph_query_sequence == NO_GRAPH_QUERIES`,
`product_content_address == NO_PRODUCT_ADDRESS`, dimension 1
`store_watermark == NO_FABRIC_READ` (`src/ccf/replay/record.py::ContextFabricSnapshot`), `assembly_refusal` a real
block. Reconstruction:

1. the engine's prologue, unchanged: `_resolve_record`, the generation check,
   `_resolve_bindings`, `_verify_resolution_claim` (`src/ccf/replay/engine.py::_reconstruct_child_contracts`);
2. `_reconstruct_child_contracts` over the admitted rows, unchanged (`:713`) — every
   admitted address resolves from the store and re-hashes to itself, or the
   reconstruction fails by name (`ReplayUnresolvable` / `ReplayDivergence`);
3. **no plan, no operators, no execution, no rehydration** — the record says nothing
   was read and nothing was computed, and the reconstruction asserts each of those
   claims positively rather than skipping past them (a "refusal" record whose
   dimension 5 names a plan or a query sequence is a contradiction and is refused by
   name);
4. the refusal block rehydrates through the same admissibility check the builder
   applies at write (`src/ccf/replay/record.py::_admissible_refusal_block`) and is held
   against the rows: the class it names is a declared requirement whose row carries a
   blocking status from the closed vocabulary and `required=True`; no admitted row is
   the one refused. Nothing re-derives the verdict from a producer — the producers are
   stopped, and the dispositions are what the rows say they were.

Result: the recorded refusal, its child dispositions, and the admitted children's
exact bytes, with no parent payload invented and no operator pretended to have run.

### 4.3 Refusal after projection

The record's claims: a real `plan_id`, non-empty `steps`, pins, a snapshot,
`product_content_address == NO_PRODUCT_ADDRESS`, a refusal block whose `evidence`
carries `operators_invoked`, `plan_id`, `debt` and `computed_empty`
(`resolver.py:2502–2506`). Reconstruction:

1. prologue and child reconstruction as in 4.2;
2. `resolve_composite_plan` over the reconstructed children, `resolve_operators`, and
   `ProjectionEngine.execute` under the recorded snapshot, exactly as the served path
   (`src/ccf/replay/engine.py::replay`); the step, query-pin and snapshot comparisons (`:893–943`)
   unchanged — the operator path the refused decision took is re-derived and held to
   the record;
3. **stop before `rehydrate_product`.** The record names no product; nothing is
   rehydrated as one and nothing served-shaped is returned. The re-executed
   projection is *provisional computation* and the outcome type (§4.4) has no member
   that could carry it as a `ServedProduct` or a `ContextProductContract`;
4. the refusal block rehydrates and is held to the re-execution where the record lets
   it be: its evidence `plan_id` equals the path's; its `operators_invoked` equals the
   re-executed set; its `debt` equals the recorded dimension-5 `debt`.

**The boundary, stated rather than bridged.** The record does not carry the
provisional candidate's own content address (the builder writes `NO_PRODUCT_ADDRESS`
whenever no product is passed, and the gate and tolerance exits pass none), and
`ReplayEnvironment` (`src/ccf/replay/engine.py::ReplayEnvironment`) exposes no gate configuration or debt scorer.
So a post-projection reconstruction under 344 re-derives **the operator path, the
children and the recorded evidence**, and reproduces **the recorded verdict**; it does
not recompute the gate or tolerance comparison. Recording the candidate's address and
re-running the verdict would be a record-shape change (a generation boundary under
`D-IMPL-243`) and an environment-protocol change — a different decision. Ruling `R-2`
asks whether that boundary is accepted for 344.

### 4.4 The interface gap, and the smallest change

**Gap.** `ReplayOutcome.product: ContextProductContract` is required (`src/ccf/replay/engine.py::ReplayOutcome`)
and `replay()` has one path, which ends in a product. There is no representation of a
reconstructed refusal, and no discrimination of record kind: today `replay()` on a
refusal record fails at `environment.resolve_plan(plan_id="no-fabric-read")` with a
message about a missing plan — a *don't know* reported as a *no*.

**Proposed change (for the implementation ruling, `R-1`).** Two entry points, one
prologue, no union return:

- `replay_refusal(*, record_address, store, reader, control_plane, environment)
  -> ReplayedRefusal` in `ccf.replay.engine`, executing §4.2 or §4.3 as the record's
  own claims direct. `ReplayedRefusal(CCFContract)` carries `record`,
  `record_content_address`, `assembly_refusal` (the rehydrated block, re-minted equal),
  `child_contract_addresses` (every admitted address that resolved and re-hashed) and
  `graph_snapshot_id` (`NO_FABRIC_READ` for §4.2; the re-derived id for §4.3). **No
  `product` member exists on the type**, so nothing served-shaped can be read off a
  reconstructed refusal.
- `replay()` gains one named guard at the top of its path: a record whose dimension 5
  carries a refusal block, or names `NO_PRODUCT_ADDRESS`, is refused with
  `ReplayRecordKindMismatch(ReplayError)` — and `replay_refusal()` refuses a served
  record the same way. Both directions asserted positively, so neither entry point can
  be pointed at the other's record and return anything.

Why this rather than `replay() -> ReplayOutcome | ReplayedRefusal`: `ReplayOutcome`'s
contract (*"holding one of these is the evidence"* of a product) stays exactly as
written; the eight modules that call `replay(record_address=…)` today
(`tests/replay/test_golden_13bd250.py` among them) change nothing; and a caller that
wants a product cannot receive a refusal by forgetting to narrow a union. The cost is
one new function and one new exception class. This is the only interface change the
design asks for.

---

## 5 · Proof and sabotage plan — defined before implementation

Controls are named as node ids they will carry; the first two rows reuse fixtures that
already exist in `tests/products/test_d_impl_339_child_contract_view.py`.

| # | case | control | required result |
|---|---|---|---|
| 1 | one admitted child + a blocking required sibling | new, beside `::test_a_known_blocking_outcome_prevents_child_dependent_projection` (`:372`): a two-requirement composite, one door serving, one absent | refusal recorded with `NO_FABRIC_READ`; the admitted row's address resolves from a **fresh** store instance and re-hashes; the plan factory was never called; the sibling row has status `no-producing-skill` and no artifact |
| 2 | admitted children + later tolerance or gate refusal | extend `::test_a_later_governing_failure_serves_nothing_and_keeps_the_acquired_evidence` (`:410`) | after the `tolerance-exceeded` record, the admitted address resolves from a fresh store instance; `replay_refusal` re-executes to the recorded steps and pins and returns a `ReplayedRefusal` whose block equals the recorded one; nothing served-shaped is returned |
| 3 | no admitted children | new: every requirement refused or unreachable | store holds zero `ccf.admitted-child-contract` artifacts; every row's `child_content_address` is `None`; `replay_refusal` returns with an empty address tuple and no `put` was observed |
| 4 | fresh reconstruction, producers stopped | new, on the shape of `::test_a_fresh_environment_reconstructs_the_parent_with_providers_disabled` (`:548`): one-shot doors, a new store instance over the same root, no live object from the serve | for **both** case 1 and case 2 records, `replay_refusal` returns; any provider call raises (the door is one-shot); `replay()` on the same record raises `ReplayRecordKindMismatch` |
| 5 | missing or corrupted retained bytes | new: delete the retained artifact, then separately overwrite it with bytes hashing elsewhere | `ReplayUnresolvable` naming the address; `ReplayDivergence` naming both hashes; no substitution, no producer call |
| 6 | existing served composite | unchanged: `::test_a_fresh_environment_reconstructs_the_parent_with_providers_disabled` and `tests/examples/test_cp_03_canonical_paved_consumer.py` | product address and `replay()` outcome byte-identical before and after |
| 7 | persistence failure | new: a store whose `put` raises for the admitted-child class | the serve raises; no record is written; no refusal envelope is returned |

**Sabotage, targeted at the refusal path.** Move the retention call back under the
non-blocking arm (the shipped defect, restored by hand). Required: case 1 and case 4's
early-blocking half go **RED** (missing child at reconstruction); case 6 and case 2
stay **GREEN** (the served path and the post-projection path never depended on the
move). A second sabotage removes the `replay()` kind guard: case 4's
`ReplayRecordKindMismatch` assertion goes RED while case 6 stays GREEN. A control that
stays green under both sabotages is not measuring this design.

**The F-32 test's disposition.** It stays exactly as written on
`cp-14-gate-2-slice-1` until implementation is approved — the measurement is the
evidence. On implementation it inverts: the `pytest.raises(ReplayUnresolvable, …)`
becomes a positive assertion that `replay_refusal` reconstructs both slice-2 records
from the consumer's store with the producers stopped, and the pre-fix form is
preserved in `CP14-F-32`'s row as the measurement that forced the decision. **The
property is not weakened to fit the test that was written while the defect existed.**

---

## 6 · Compatibility impact

- **Served path:** byte-identical products and records; retention runs at the same
  addresses one branch earlier. Case 6 pins it.
- **Refused records:** no field added, no generation boundary; rows unchanged. New
  artifacts appear in the parent's store on refused exits only, under the class
  `D-IMPL-339` already registered.
- **Behavior change on the refused path, named:** a store whose `put` fails now fails
  the refusal (exception, no record) where before the refusal was recorded without the
  evidence it claims. That is the invariant, not a regression.
- **`replay()` on a refusal record:** a named `ReplayRecordKindMismatch` where today a
  misleading missing-plan `ReplayUnresolvable` is raised. Callers that catch
  `ReplayError` are unaffected; none in the tree replays a refusal.
- **No example, producer, door, or CP-14 change**; no bytes copied anywhere; no
  provider-availability requirement introduced.

## 7 · Rulings asked

- **R-1** — the interface: `replay_refusal()` + `ReplayedRefusal` + the two-way
  `ReplayRecordKindMismatch` guard (§4.4), versus a union return from `replay()`.
  Recommended: as proposed.
- **R-2** — the post-projection boundary (§4.3): 344 reproduces the recorded verdict
  over a re-derived operator path and does not recompute the gate or tolerance
  comparison; recording the candidate's address for a later verdict re-run is a
  separate decision if wanted. Recommended: accept the boundary for 344 and record
  the follow-on under `D-IMPL-345` or later.
- **R-3** — confirmation that retention failure on the refused path fails the
  determination (no record, no envelope), reusing `_record_refusal`'s posture (§3).

## 8 · What this document does not do

No SDK code. No CP-14 continuation, page, gate roster, or merge. No `D-IMPL-341`,
`D-IMPL-342` or `F-33` work. No generic mid-pipeline hook. No new replay framework
and no record redesign. The separate CP-14 structural cleanup (`D-IMPL-344` entry,
"structural checks") lives on `cp-14-gate-2-slice-1` in its own commit and touches no
product behavior.

---

## 9 · As built (2026-09-16, synchronization of this design to the tree)

Implementation GO given by Dave on `6046e0fa` with R-1, R-2 and R-3 as proposed and three
corrections, recorded verbatim in `docs/DECISIONS.md` under `D-IMPL-344`: the F-32 test
converts to a positive reconstruction proof (a kind-mismatch failure is not closure); both
refusal paths carry their complete checks; the full seven-case package with both sabotages
is required, and "zero admissions" means zero admitted-child artifacts, not zero writes.


**One deviation from R-1's wording, reported rather than hidden: the outcome type is
named `RefusalReplayOutcome`, not `ReplayedRefusal`.** The tree's refusal-vocabulary gate
(`tests/products/test_refusal_envelope.py::test_the_refusal_vocabulary_is_closed_by_set_equality`)
walks `src/` for every contract-based class named `…Refusal` and requires each to be a
`REFUSAL_KINDS` member or an entry on an exact allowlist that "demands a ruling" to grow.
A `…Refusal`-named contract that is not a refusal — this type is a verified reconstruction,
the mirror of `ReplayOutcome` — is exactly what that gate exists to refuse, so the name
was changed rather than the allowlist. Shape, members and semantics are as R-1 proposed.
If the ruled name is preferred, the change is one allowlist line plus a rename.

**Retention** (`src/ccf/products/resolver.py::GovernedResolver.__call__`): as §3 —
immediately after `resolve_child_outcomes`, before the `blocking` split, over
`resolved.admitted`; `_retain_child_contracts` now takes an iterable of contracts. A
store that raises on `put` propagates before any record is minted (case 7).

**Reconstruction** (`src/ccf/replay/engine.py`): `replay()`'s prologue factored into
`_prologue` and its re-execution into `_re_execute` (stops before any product); both
entry points share them, stated once. `replay_refusal()` runs the prologue, the kind
guard, rehydrates dimension 5's block through the builder's own two admissible shapes and
holds it to re-canonicalize equal, reconstructs the admitted children from retained bytes,
then: before projection, asserts each of `steps == ()`, `operator_plan == ()`,
`graph_query_sequence` sentinel and dimension-1 `store_watermark == no-fabric-read`
positively and holds a child-admission refusal to a declared, required, blocking row
carrying the refusal's own reason — consulting the environment for nothing; after
projection, re-derives the operator path through `_re_execute` and holds the refusal's
evidence to it (`operators_invoked` against the re-execution; `plan_id` and `debt` against
dimension 5 as integrity checks), never calling `rehydrate_product` and never recomputing
the gate or tolerance verdict (R-2). `RefusalReplayOutcome` has no `product` member.
`ReplayRecordKindMismatch` is raised in both directions and for a self-contradicting
record. One addition to `_reconstruct_child_contracts`: bytes at the address that do not
rehydrate as a contract are a named `ReplayDivergence` (case 5's third form) rather than a
validation error escaping from the store's answer.

**Proof** — `tests/products/test_d_impl_344_refusal_reconstruction.py`, 11 controls, all
driven through the real composite fixture (a real grant, the child's own door, real
admission), each on a fresh store instance with a one-shot door so a provider call raises:

| case | control(s) | result |
|---|---|---|
| 1 | `test_case_1_an_early_blocking_refusal_retains_the_admitted_sibling_and_runs_no_plan` | green |
| 2 | `test_case_2_a_tolerance_refusal_after_projection_keeps_its_children_and_reconstructs` | green |
| 3 | `test_case_3_no_admitted_children_files_no_admitted_child_artifact` (zero admitted-child puts; the refusal record written) | green |
| 4 | `test_case_4_early_blocking_refusal_reconstructs_with_the_producer_stopped`, `test_case_4_late_tolerance_refusal_reconstructs_with_the_producer_stopped` (each also asserts `replay()` refuses the record by name) | green |
| 5 | missing / substituted (both hashes named) / unparseable retained bytes | green |
| 6 | `test_case_6_a_served_composite_replays_as_before_and_replay_refusal_refuses_it_by_name` | green |
| 7 | `test_case_7_a_store_that_cannot_retain_fails_the_determination_before_any_record` | green |
| vocabulary | the engine's quoted child-refusal kind equals the live `REFUSAL_KINDS` entry | green |

**Sabotage record** (run by hand on the candidate, restored by copy and verified with
`cmp`; the 344 module and the 339 module together, 19 controls):

| sabotage | red | green |
|---|---|---|
| S1 — retention moved back under the non-blocking arm (the shipped defect restored) | case 1, case 4 early, case 5 ×3, case 7 (6) | case 2, case 3, case 4 late, case 6, all 8 of the 339 module (13) |
| S2 — `replay()`'s record-kind guard removed | case 4 early, case 4 late (2) | everything else including case 6 (17) |

**F-32's disposition.** The measurement is preserved in `CP14-F-32`'s row on
`examples/cp-14-credit-memo-context/FINDINGS.md`; the test on `cp-14-gate-2-slice-1`
converts, with this branch merged into it, to a positive proof that both slice-2 records
reconstruct through `replay_refusal` from the consumer's own store after the producer
processes have exited — see the slice branch's commit.

**Compatibility, measured.** `make typecheck` clean; `tests/replay` 180 passed; the
composite, 339 and paved-consumer suites 100 passed; served-path replay unchanged. The
three new names are recorded in `docs/surface-changes/344-01-refusal-reconstruction.md`
and the manifest regenerated.

### 9.1 · Focused completion before merge (2026-09-16, Dave's source review of `b8212ac6`)

**Accepted:** the retention point, the separate refusal-replay path, the shared halves,
both kind guards, and the name `RefusalReplayOutcome` — *"a reconstruction result, not a
refusal kind"*; the naming deviation from R-1's wording is recorded as accepted and the
refusal-vocabulary allowlist is not expanded.

**The defect Dave found.** `_hold_refusal_to_rows` assumed every early composite refusal
names a *required* child row. Two determinations the SDK legitimately records did not fit:

| determination | recorded as | what the first helper did |
|---|---|---|
| an **optional** child invoked, then refused or rejected at admission | the composite refuses (`D-IMPL-336` F1: optional means optional *absence*, not optional governance); the row carries `required=False`, `rejected-at-admission` / `as-of-mismatch`, the refused child's identity | rejected the record because `row.required` was false — optional absence and optional refusal conflated again, this time in reconstruction |
| requirements declared, **no child resolver wired** | the resolver records `no-producing-skill` against the composite's OWN class with **no** child rows (nothing attempted, nothing invented) | demanded a child row that never existed |

Both were reproduced through the supported resolver and a fresh store before the repair
(the probe output is in the commit message), and the bounded check of the helper's
callers found two more early shapes `resolve_child_outcomes` records: `undeclared-outcome`
(the resolver produced an outcome for a class the composite does not require; the refusal
names a class no row declares, by definition, while the admitted rows and their retained
bytes stand) and `requirement-mismatch` (one class declared twice; the walk returns before
any row — unreachable through the supported writer path, because product-class
registration refuses the duplicate first).

**The bounded check of the helper's callers** was run twice: by hand over
`resolve_child_outcomes` and the resolver's composite branch, and by a three-reader
read-only census (each reader from a different starting point; results in the session
journal). The census found one shape the hand pass had mis-filed: `requirement-mismatch`
is ALSO the token `_rebinding_failure` records when an admitted child is walked under
another slot or invocation — and that shape writes a row. The helper now treats the token
as the duplicate-declaration shape only when the rows are empty, and otherwise as a
child-row refusal. It also confirmed `mixing-refused` is a post-projection shape (it is
raised by `compose_children`, after the plan ran) and so is held by the evidence check, not
by this helper; and that `ambiguous-producer` never reaches a record (the error escapes
before any refusal is minted).

**The repair (`src/ccf/replay/engine.py::_hold_refusal_to_rows`).** The governing
distinction, Dave's words: *"A refusal must agree with the evidence and scope of the
determination that actually occurred — not with an assumption that every composite refusal
is a required-slot failure."* The helper now takes the whole dimension-5 path and checks by
shape: `undeclared-outcome` → the named class has no row; `requirement-mismatch` → no rows;
a parent-scope `no-producing-skill` with no rows → the named class equals the recorded
request's own class (a record with no request cannot evidence that scope and is refused by
name, so there is no "empty rows means valid" escape); every other reason → a row exists,
carries a blocking disposition (anything but `admitted` and `optional-absent`) and the
refusal's reason is the row's. **`required` is no longer a condition.** No determination
was changed to fit replay: no flag flipped, no row invented, no blocking rule weakened.

**Controls added** (`tests/products/test_d_impl_344_refusal_reconstruction.py`, now 19):
case 8 (optional invoked and refused, through the child's real door, `required=False`
preserved) with its F1 control (the same optional requirement honestly absent still
serves); case 9 (no resolver → parent-scope refusal reconstructs) with its scope control
(the same record re-pointed at a class the request does not name is refused); case 10
(`undeclared-outcome`, the admitted row's bytes retained); case 11 (the re-binding
`requirement-mismatch`, with its row); the record-kind guard in all
four quadrants (valid served, valid refused, both present, neither present — the
contradictory records built off real ones and filed on the store); the quoted tokens
pinned to `CHILD_REFUSAL_REASONS`.

**Mutation M3** — the required-row assumption restored by hand (the four early returns
disabled, `not row.required` raising again), restored by copy and verified with `cmp`:
case 8, case 9 and case 10 **red**; the required-child cases 1–7, both controls, case 11,
the guard quadrants and the 339 module **green**. **Mutation M4** — the first
reconciliation's own assumption restored (`requirement-mismatch` beside rows refused): case
11 **red** alone; the other 27 controls **green**.

**Documentation corrected:** `ReplayRecordKindMismatch`'s docstring states the actual
order (the shared prologue resolves and verifies the record and its bindings first; the
guard runs after that and before any child, plan or operator is resolved or anything is
re-executed); the slice-2 module header states that F-32's missing-byte measurement is
historical and the converted test proves retention and reconstruction. The
`store_watermark == no-fabric-read` check stands as written — it is what the builder's
`ContextFabricSnapshot.unread()` writes; the hashed `graph_snapshot_id` is not compared to
the sentinel.

