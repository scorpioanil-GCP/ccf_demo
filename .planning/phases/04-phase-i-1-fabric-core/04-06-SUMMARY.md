---
phase: 04-phase-i-1-fabric-core
plan: 06
subsystem: operator-subsystem-and-composition-property
tags: [l4, l5, operators, registry, planner, hypothesis, composition-preservation, property-testing]
requires:
  - 04-01 (packaging, pytest/mypy config, CI; hypothesis==6.161.5 already pinned)
  - 04-02 (CINV-01/02/03 lints — CINV-01b is what keeps params.py default-free)
  - 04-03 (CCFContract, canonical_bytes/content_hash, claims)
  - 04-04 (GraphReader/GraphView)
  - 04-05 (operator contract, the four category operators, two-stage engine)
provides:
  - operator registry carrying category, declared parameter *schema* class, and deployment-assigned version, with category-scoped lookup
  - operator planner producing a totally-ordered plan (Policy→Similarity→Temporal→Traversal, then by key) from a declared key set
  - per-execution IntermediateCache keyed on everything `apply` can observe (D-IMPL-36, I.1 scope)
  - `compose()` / `ComposedOperator` — the composite `A∘B` as production code, so the property harness exercises the fabric's own composition path
  - `ccf.operators.params` — the four category parameter contracts as a module the Control Plane can register against, with no default on any field
  - the D-14 property harness: banking-shaped Hypothesis strategies, `ci`/`nightly` profiles, curated edge graphs, and both FEASIBILITY §11 D-08 test classes
affects:
  - the λ_c/D_c plan registers its debt parameters the same way params.py declares operator parameters; no numeric ever enters /src
  - every future operator is covered by the composition property automatically — the pairs are enumerated from the registry, not from a list
  - the Postgres wave changes nothing here: the harness runs over GraphView values and never touches a substrate
  - I.2's agent framework binds to the registry's metadata (category, parameter schema, version) rather than to operator instances
tech-stack:
  added:
    - Hypothesis 6.161.5, first use (already a pinned dev dependency)
  patterns:
    - composite operators are production code, so a property harness cannot pass by agreeing with its own re-implementation of the thing under test
    - the composite path runs through the intermediate cache while the direct path does not, which turns a cache-key defect into a byte difference
    - the harness asserts its own premise (Policy must remove exactly the inadmissible claims), so an equality between two identity functions cannot be mistaken for evidence
    - parametrization derived from the registry via itertools.product — n² by construction, not by maintenance
key-files:
  created:
    - src/ccf/operators/params.py
    - src/ccf/operators/registry.py
    - src/ccf/operators/planner.py
    - tests/operators/__init__.py
    - tests/operators/test_planner.py
    - tests/properties/__init__.py
    - tests/properties/strategies.py
    - tests/properties/test_composition.py
    - tests/properties/test_staged_vs_direct.py
    - tests/fixtures/banking/edge_graphs.yaml
  modified:
    - src/ccf/operators/categories.py
    - src/ccf/operators/__init__.py
    - src/ccf/projection/engine.py
decisions:
  - "`compose()` lives in `/src`, not in the test harness. A composition-preservation property whose left-hand side is written by the test is a property about the test: it can agree with itself while disagreeing with the fabric. Putting the composite in `ccf.operators.planner` means the harness asserts against the same code the engine's composition path is built from."
  - "The composite is run through the IntermediateCache and the direct application is not. That asymmetry is the point — it makes the D-IMPL-36 cache a participant in the property rather than an untested optimization sitting beside it, so a cache key that omitted the upstream chain would fail as a byte difference instead of as a silent wrong answer months later."
  - "The cache key is (operator key, parameter hash, input-view hash, upstream-chain hash) — every input `apply` can observe. Anything less returns an intermediate computed over a different input, which is precisely how a memoized fabric stops being replayable while still looking fast."
  - "The similarity corpus is built once over a fixed URI pool and is independent of the drawn state. A corpus derived from the generated view would make the index a function of its own input, and an operator whose index moves with its input is not a pure function of graph state — the property would then be asserting over a moving target."
  - "Generated entity URIs are drawn from a bounded pool rather than generated freely. Free URIs cannot be covered by a fixed corpus, and shrinking over URI *text* produces failure reports about string minimization rather than about graph shape."
  - "Registration reads category and parameter schema off the operator instead of accepting them as arguments. A registration able to declare a category the operator disagrees with could place an operator in a plan position it does not belong in — which is the Policy-after-Similarity failure INV-CH7-26 exists to forbid."
  - "`OperatorRegistration.version` defaults to None and means 'this deployment assigned no version'. Not `\"0\"`, not `\"unknown\"` — a placeholder the SDK invented would be indistinguishable in an audit from a version a deployment chose."
  - "A key declared twice by a plan yields one step. An operator is a pure function of the view; running it twice changes the provenance chain without changing the state, which would make the product a function of how the projection happened to spell its declaration."
  - "The `ci` Hypothesis profile is the default when HYPOTHESIS_PROFILE is unset. An unset variable buying randomness is how a build that is being trusted as green quietly becomes a build that was green once."
metrics:
  duration: ~55 min
  completed: 2026-07-25
  tasks: 3
  commits: 4
---

# Phase 4 Plan 06: The Operator Subsystem and the Composition Property Summary

`(A∘B)(G) = A(B(G))` is no longer a claim the design makes on paper. It is
asserted bit-for-bit, on canonical bytes, for all sixteen ordered pairs of the
operators the SDK ships, over Hypothesis-generated banking state and three
curated edge graphs — and the engine's two-stage execution is proven to add
nothing and lose nothing on top of it.

## What Was Built

**Task 1 — the operator subsystem widens** (`c703d63`). L4 was one contract and
four operators; it is now five modules with the mechanism/values line drawn as a
module boundary.

`params.py` holds the four category parameter contracts, moved out of
`categories.py`. It is the module the Control Plane registers against, and it is
the module CINV-01b watches: no field in it carries a default, so a missing
threshold is a registration failure rather than a number the SDK picked
(`grep -rEc "= *[0-9]+\.[0-9]+"` returns 0).

`registry.py` records more than the callable. Each registration carries the
operator's category, its declared parameter *schema class*, and the version the
deployment assigned — so the fabric's operator surface is describable without
instantiating anything, and a replay can name the contract a decision's
parameters validated against, not merely the values they held. Both are read off
the operator rather than passed in: a registration free to declare a category
the operator disagrees with could seat an operator in a plan position it does
not belong in.

`planner.py` is where the order lives, and it is deliberately not in the engine.
`build_operator_plan` imposes Policy → Similarity → Temporal → Traversal with
intra-category order by key; `IntermediateCache` memoizes per execution on
everything `apply` can observe; and `compose()` builds the composite `A∘B`.

The engine now resolves through the planner and runs through the cache. Its
public surface is unchanged — it still re-exports the registry names it no
longer defines — and all 115 tests from 04-05 pass untouched.

**Task 2 — the FABR-02 harness** (`604c855` RED, `7966077` GREEN). The
strategies draw banking-shaped states: entities across the ontology's four
classes with drawn classifications and policy-bundle versions, typed edges
between drawn endpoints, and bitemporal instants straddling the decision
boundary on both axes. Shapes come from `ontology.yaml`, operator parameters
from `controlplane.yaml`, and the drawable vocabulary plus the curated graphs
from the new `edge_graphs.yaml` — the No-Hardcoding discipline holds in fixture
code too, so the harness itself names no entity class, no threshold, and no
policy version.

Two things make the equality evidence rather than ceremony:

- **The composite is production code.** A test that wrote its own `A∘B` could
  agree with itself while disagreeing with the fabric.
- **The composite runs through the cache and the direct path does not.** A cache
  key that omitted the upstream chain fails here as a byte difference, at the
  moment it is introduced.

And the harness asserts its own premise: for any drawn state, Policy must remove
exactly the claims the principal is not admitted to. An equality between two
identity functions is not composition preservation, and this is what rules that
reading out.

**Task 3 — the second D-08 class** (`6c0bf85`). Composition preservation is a
statement about the algebra; staged-vs-direct is a statement about the *engine*.
The suite runs `ProjectionEngine.execute` against a hand-folded composite plus a
direct `Π.invoke`, and requires the same view, the same provenance chain, and
the same payload — canonically. It reads through a `FixedViewReader`, which is a
reader: no writer, no test-only write path, no database.

## Key Implementation Details

- **Sixteen pairs, derived not listed.** `itertools.product` over the registry
  keys. The count is asserted equal to `n²`, so an operator that ships without
  a composition test is not a reachable state.
- **The three curated cases earn their names.** `empty-result` (every operator
  empties it — where an operator that special-cased "nothing to do" and skipped
  its own provenance would be caught), `policy-filtered` (three different routes
  to inadmissibility, plus an edge that must go with its endpoints), and
  `temporal-boundary` (observed exactly at, observed after, `valid_to` exactly
  at, superseded exactly at, and superseded *after* — the last being the case a
  naive "is superseded" check gets wrong).
- **Profiles, not luck.** `ci` is derandomized at 50 examples; `nightly` is
  randomized at 500. `HYPOTHESIS_PROFILE` selects, and an unset variable gets
  `ci`.
- **Nothing here reads a clock.** `temporal_boundary` comes from the fixture at
  every level, exactly as in 04-05.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] The harness's first vacuity check was too strong**

- **Found during:** Task 2, immediately after raising the `ci` example count
- **Issue:** The premise assertion was "for any non-empty drawn state, some
  operator changes it". Hypothesis promptly found the counterexample: a single
  permitted-classification counterparty under the admitted bundle version is a
  fixed point of all four operators (it is admissible, it is not a ranked class,
  it is temporally current, and it is its own traversal seed). The check was
  wrong, not the fabric.
- **Fix:** Reformulated against the operator whose exclusion rule is total —
  Policy must remove *exactly* the inadmissible claims of any drawn state. That
  is a real invariant, and it still rules out the identity reading.
- **Files modified:** `tests/properties/test_composition.py`
- **Commit:** `7966077`

### Interpretations

- **A unit suite the plan's file list does not name.** The acceptance criteria
  require a test asserting planner order and deterministic intra-category
  ordering, which needs two operators in one category — something the four
  shipped operators cannot supply. `tests/operators/test_planner.py` (10 tests)
  provides inert operators for that purpose, and also covers registry metadata,
  duplicate-key fatality, cache-key soundness, and composite nesting.
- **`test_staged_vs_direct.py` had no RED gate, and manufacturing one would have
  been dishonest.** The behavior it asserts shipped in 04-05 and was widened in
  Task 1; a test written to fail first would have had to break the engine to do
  it. Instead the suite was verified to *bite*: reversing the engine's execution
  order (`for operator in reversed(...)`) fails all five cases, and the mutation
  was reverted before commit. D-15 permits implementation-first for existing
  plumbing; this records which of the two it was.
- **A worktree-local `.venv`.** Created because the shared interpreter's
  editable install resolves to the main checkout's `src`, and a property suite
  validating the wrong tree is worse than no property suite. `.venv/` is already
  gitignored.
- **`edge_graphs.yaml` carries a `generation:` block as well as the curated
  graphs.** The generator's vocabulary — classifications, bundle versions,
  instants, corpus texts, pool size — is values, and values belong in a fixture.
  Splitting it into a second file for the sake of the filename would have put
  two halves of one harness input in two places.

## Verification

| Check | Result |
|---|---|
| `pytest tests -q -m "not postgres and not chroma"` | 198 passed (115 from 04-05, unchanged) |
| `HYPOTHESIS_PROFILE=ci pytest tests/properties -q` | 73 passed in 3.0s (budget: 5 min) |
| `HYPOTHESIS_PROFILE=ci pytest tests/properties/test_composition.py -q` | 68 passed |
| `pytest tests/operators -q` | 10 passed |
| `mypy --strict src` | Success, 39 source files |
| `python -m tools.lints --all` | exit 0, zero allowlist entries added |
| `pytest tools/lints/tests -q` | 45 passed |
| Composition parametrization count | 16 = 4², asserted in `test_the_parametrization_covers_every_ordered_pair` |
| Curated cases present | `empty-result`, `policy-filtered`, `temporal-boundary`, asserted |
| `grep -rEc "= *[0-9]+\.[0-9]+" src/ccf/operators/params.py` | 0 |
| `canonical_bytes` used in the assertions | yes, in both property modules |
| Mutation check (engine order reversed) | all 5 staged-vs-direct cases fail; reverted |
| Post-commit deletion check, all 4 commits | no deletions |

## Known Stubs

None. Two bounded-scope items, both named in the plan:

- The intermediate cache is **per-execution only** (D-IMPL-36 as scoped for
  I.1). A longer-lived cache needs the invalidation story D-IMPL-36 defers, and
  the class docstring says so rather than implying a cache that outlives the
  as-of read it was computed under.
- `OperatorRegistration.version` is recorded but nothing yet *enforces* version
  compatibility between a plan and the operators it names. That belongs with the
  Control Plane artifact-versioning surface, not here.

## Threat Flags

None new. Both registered threats are mitigated as planned: T-04-13 (replay
determinism) by the bit-for-bit property over all pairs, the injected boundary,
and the derandomized CI profile; T-04-14 (policy-filtered nodes leaking via
composition order) by the `policy-filtered` curated graph, which carries an edge
whose survival past its endpoints would leak by absence — and which is asserted
identical under both composition orders.

## Self-Check: PASSED

All 10 created files and 3 modified files exist on disk; all four commit hashes
(`c703d63`, `604c855`, `7966077`, `6c0bf85`) are present in `git log`.
