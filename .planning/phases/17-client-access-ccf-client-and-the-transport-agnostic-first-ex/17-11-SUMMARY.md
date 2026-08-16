---
phase: 17-client-access-ccf-client-and-the-transport-agnostic-first-ex
plan: 11
subsystem: products
tags: [debt, halflife, reference-implementation, claude-md-11, d-impl-47, amendment-a1, sabotage-controls]

requires:
  - phase: 17-03
    provides: "`AssemblyDebtScorerProtocol`, declared in `src/ccf/products/resolver.py` with no implementation"
  - phase: 17-07
    provides: "the sabotage-control pattern — a divergent subject fed to the *shipped* assertion function"
provides:
  - "`ccf.products.debt_scorer.AssemblyDebtScorer` — the SDK's reference `GraphView` → `DebtAssessment` adapter, with its row-selection choice stated at the seam"
  - "`ccf.products.debt_scorer.DeclaredFactor` — the honest form of an unmeasured C or S, pinned into replay under its own identity"
  - "CLAUDE.md §11 satisfied for `AssemblyDebtScorerProtocol`; Amendment A.1 of the 2026-08-16 spec discharged"
  - "`ProjectionPlanFactoryProtocol`'s absence recorded as Amendment A.2's ruling rather than left as an assumption"
  - "11 sabotage controls, every failure message observed and recorded below"
affects: [17-12, 17-13]

tech-stack:
  added: []
  patterns:
    - "A reference implementation that *states* its choice at the seam — which reading, why, the observable consequence, and the override path — rather than making it silently"
    - "An unmeasured factor declared through a pinned scorer, so replay can tell an assertion from a measurement without reading code"
    - "The empty-assembly branch carrying NO scorer pin, because naming a producer for a value nothing measured is a false record"
    - "Every assertion a module-level function taking its subject as a parameter, so a control can feed the shipped assertion a broken subject"

key-files:
  created:
    - src/ccf/products/debt_scorer.py
    - tests/products/test_reference_debt_scorer.py
    - docs/surface-changes/17-11-reference-debt-scorer.md
  modified:
    - src/ccf/products/__init__.py
    - src/ccf/products/resolver.py
    - docs/SURFACE-CHANGES.md

decisions:
  - "Row selection: the reference scorer measures the rows that SURVIVED being read — exactly the entity records of the view it is handed — because the seam carries one view and recovering the read rows would need a second graph consultation the replay record does not describe"
  - "C and S arrive as `DebtFactorScorerProtocol` implementations with no defaults, because `DebtFactors` records in the tree that the SDK has no reference measurement for either; `DeclaredFactor` ships so a deployment can state an assumption instead of measuring one"
  - "Relationships are deliberately not observations: an edge's natural type is its `relationship_type`, which would need its own λ_c row, and a deployment calibrating only entity classes would get a lookup failure instead of a number"
  - "The decision instant is `view.as_of`, not `max(observed_at)` — the fixture's claim that a scorer cannot see the question's `asked_at` is false, because `GraphView.as_of` carries it"
  - "The empty assembly scores every factor at zero and carries NO scorer pin; the routing band stays the profile's, so a profile declaring a fail-closed band of one still reports OK at D_c = 1"

metrics:
  duration: ~75 minutes
  tasks: 3
  completed: 2026-08-16
---

# Phase 17 Plan 11: Reference AssemblyDebtScorer Summary

The SDK now ships a working `AssemblyDebtScorerProtocol` implementation — the
thin `GraphView` → `DebtFactors` adapter over machinery `ccf.halflife.debt`
already had — with the row-selection choice the Protocol's docstring names made
explicitly at the seam rather than avoided, and the two factors the SDK cannot
measure arriving as pinned, deployment-supplied scorers rather than as numbers
the library invented.

## What was built

**`src/ccf/products/debt_scorer.py`** (345 lines, mostly docstring)

- `AssemblyDebtScorer` — a frozen, keyword-only dataclass taking a
  `HalfLifeTable`, a `DebtProfile`, and a `DebtFactorScorerProtocol` for each of
  `C` and `S`. None defaulted. It maps one `Observation` per entity record,
  typed by that record's own `entity_class` (which *is* the λ_c vocabulary) and
  dated by its `observed_at`, then scores `F` through the shipped
  `FreshnessScorer` at the view's own `as_of` and routes through `assess_debt`.
- `DeclaredFactor` — a `DebtFactorScorerProtocol` that reports a value the
  deployment declared, reading neither `observations` nor `now`. It carries its
  own `scorer_id` / `scorer_version` so the assertion is pinned into the
  Decision Replay record under `D-IMPL-47`. An examiner can now tell a declared
  factor from a measured one without reading code.

**Measured behaviour** (fixture: one entity class, λ_c = 3600s, sensitivity 1,
bands 0.30 / 0.70):

| view | F | D_c | signal | pins |
|---|---|---|---|---|
| one row observed at `as_of` | `1` | `0` | `ok` | 3 |
| one row 10 half-lives stale | `0.0009765625` | `0.9990234375` | `fail_closed` | 3 |
| no rows | `0` | `1` | `fail_closed` | **0** |

## The row-selection choice, as shipped

The Protocol's docstring argued the choice is "bigger than a threshold", and it
is right. The shipped reference states it:

- **Which:** the rows that **survived** being read — exactly the entity records
  of the view it is handed, and no others, because it holds no graph handle and
  issues no second read. Under `GovernedResolver` that is `execution.view`, the
  composed post-operator view.
- **Why:** the seam carries one view. Recovering the rows the question *read*
  would need a second consultation at a second boundary, which the Decision
  Replay record does not describe, and would report freshness over rows the
  delivered payload was not built from.
- **Observable consequence:** a filtering operator moves `F` in whichever
  direction its survivors lean — drop the stale rows and freshness rises, drop
  the fresh ones and it falls. Where the operator plan is principal-scoped, the
  figure describes *this* principal's assembly. That is consistent with
  `D-IMPL-105` rather than a leak around it (a consultation a principal was
  refused is not part of their `C_required`, so there is no second figure to
  difference against), but it does mean the number is not comparable across
  principals.
- **Override:** a deployment whose product means "how fresh was the source data
  we consulted" supplies its own conforming callable. The SDK invokes this one
  never.

## Verification — measured, not assumed

| Gate | Result |
|---|---|
| `make ci-core` | **exit 0** — `3661 passed, 0 failed, 118 skipped` in 384.64s; `400 passed` lint tests; `144 passed` tools tests |
| `.venv/bin/python -m tools.lints --all` | **exit 0** |
| `make docs-strict` | **exit 0** |
| `pytest tests/products/test_reference_debt_scorer.py -q` | **19 passed** in 0.17s |
| `make surface-changes` | wrote `docs/SURFACE-CHANGES.md`; fragment `docs/surface-changes/17-11-reference-debt-scorer.md` present |
| `command grep -nE "[0-9]+\.[0-9]+\|= [0-9]+" src/ccf/products/debt_scorer.py` | one code survivor, `DECLARED_FACTOR_SCORER_VERSION = "1.0.0"`, carrying a comment naming what it is **not** (a calibration, an artifact value). Every other match is prose in a docstring (`§7.7`, `§7.10`, `D_c = 1`) |

The orchestrator's pre-dispatch baseline was `3642 passed / 118 skipped`. The
delta is **+19**, which is exactly this plan's new test module — no other test
count moved.

> **Measured in a worktree.** Every number above was produced inside
> `/home/parkave/ccf_code/.claude/worktrees/agent-a0c792c79904fc22b`. Tree-walking
> gates measured in a worktree are not evidence about the branch (DEF-17-04);
> the orchestrator should re-measure `make ci-core` after merge.

## Sabotage controls — every observed failure message

Eleven controls. Each hands a deliberately divergent subject to the **shipped**
assertion function; none re-implements an assertion. These are the messages
observed, not paraphrases:

1. **`assert_conforms`** — subject with no `__call__`:
   `<object object at 0x...> does not satisfy AssemblyDebtScorerProtocol`
2. **`assert_freshness_falls_as_observations_age`** — a scorer reporting a
   constant: `freshness did not fall with age: young=0.5, old=0.5`
3. **`assert_half_life_is_read_from_the_artifact`** — a scorer ignoring the λ_c
   table: `freshness did not move when the half-life artifact changed: 3600s
   gave 0.5, 360s gave 0.5`
4. **`assert_risk_sensitivity_is_read_from_the_artifact`** — a scorer ignoring
   the profile: `freshness did not move when the profile's risk sensitivity
   changed: 1 gave 0.5, 0.25 gave 0.5`
5. **`assert_bands_come_from_the_profile`** — a scorer deciding its own routing
   state: `bands (forced_llm=0.30, fail_closed=0.70) routed to ok rather than
   fail_closed`
6. **`assert_pins_identify_the_scorers` (dropped pins)** — `scorer pins do not
   identify the shipped scorers: {} != {'freshness':
   ('ccf.reference.freshness-from-decay', '1.0.0'), 'completeness':
   ('ccf.reference.declared-factor', '1.0.0'), 'semantic_consistency':
   ('ccf.reference.declared-factor', '1.0.0')}`
7. **`assert_pins_identify_the_scorers` (wrong version)** — `scorer pins do not
   identify the shipped scorers: {'completeness':
   ('ccf.reference.declared-factor', '9.9.9'), 'freshness':
   ('ccf.reference.freshness-from-decay', '9.9.9'), 'semantic_consistency':
   ('ccf.reference.declared-factor', '9.9.9')} != {...'1.0.0'...}`
8. **`assert_empty_assembly_fails_closed` — THE EMPTY CASE, leg 1** — a scorer
   reporting a confident number: `an empty assembly reported D_c=0.5, not 1 — a
   confident number about a graph that said nothing`
9. **`assert_empty_assembly_fails_closed` — THE EMPTY CASE, leg 2** — right
   number, false record: `an empty assembly named a scorer as the producer of
   factors nothing measured: (ScorerPin(factor='completeness',
   scorer_id='ccf.reference.declared-factor', scorer_version='1.0.0'), ...)`
10. **`assert_refuses_an_uncalibrated_class` — THE UNRESOLVABLE CASE** — a
    scorer substituting a rate: `an entity class with no declared half-life was
    scored at a rate nobody declared: freshness=Decimal('0.9')
    completeness=Decimal('1') semantic_consistency=Decimal('1')`
11. **`assert_measures_the_rows_it_is_handed`** — `freshness was unchanged by
    dropping rows from the view: 0.5`

An honest-subject test (`test_the_honest_scorer_satisfies_every_assertion`)
runs first and passes every assertion, so no control's expectation of failure
is satisfied by a fixture that never worked.

## Deviations from Plan

### 1. [Rule 4-adjacent, resolved by the tree] The plan assumed the SDK could produce C and S; the tree says it cannot

- **Found during:** Task 1
- **The plan said:** *"It must be constructed from Control Plane material only:
  the half-life table and debt profile the deployment already registered."* That
  wording leaves `C` and `S` with no source, and both are required to reach
  `DebtFactors`.
- **The measurement:** `src/ccf/halflife/assessment.py::DebtFactors` states the
  standing position in its own docstring — *"Only F has an SDK reference
  scorer. C and S are supplied by the caller until their scorers ship (DESIGN.md
  §2B.4, D-IMPL-47) — the SDK would otherwise have to invent a required-field
  vocabulary and a contradiction detector, both of which are deployment
  knowledge."*
- **Resolution:** the scorer takes `completeness` and `semantic_consistency` as
  `DebtFactorScorerProtocol` implementations with **no defaults** (`D-IMPL-38`:
  a default is a value nobody chose), and `DeclaredFactor` ships alongside so a
  deployment with no measurement can state an assumption that lands in replay
  under its own pin. Three alternatives were considered and rejected: `C = 1`
  (a value the SDK chose, inside a delivered product's content address);
  `C = 0` (every deployment fail-closes, so the reference is useless); and
  deriving `C` from the breadth of the λ_c table (couples every product's
  completeness to how many observation types the deployment happens to
  calibrate — a deployment declaring five types and serving a one-type product
  would always score `C = 0.2`).
- **Commit:** `b0b9709`

### 2. [Rule 1 - Bug] The plan's "resolved by key" was deferred to 17-13, deliberately

- **Found during:** Task 1
- **Issue:** reading the λ_c table and debt profile off `BootedFabric.artifacts`
  by manifest key would put the same narrowing refusal `GovernedResolver._artifact`
  already performs in a second place, and would make the scorer untestable
  without booting a fabric.
- **Resolution:** the scorer takes the two typed artifacts directly. The
  manifest read stays in one place; `17-13`'s `build_governed_resolver(...)`
  helper is where the key → artifact resolution belongs, since it already reads
  eight other keys. The `must_have` — *"reads every number from a Control Plane
  artifact"* — is satisfied exactly: `HalfLifeTable` and `DebtProfile` are the
  artifacts, and no threshold, half-life or sensitivity literal appears in the
  module.
- **Commit:** `b0b9709`

### 3. [Rule 2 - Correctness] Three further docstring claims in `resolver.py` were made false by task 1

- **Found during:** Task 2
- **Issue:** the plan scoped task 2 to `AssemblyDebtScorerProtocol`'s docstring
  alone, but shipping the reference falsified two neighbours:
  `GovernedResolver`'s *"the projection factory and the debt scorer are
  deployment code and have no artifact form"* paragraph, and its `debt_scorer:`
  attribute doc. `ProjectionPlanFactoryProtocol`'s *"could not"* was true but
  unsourced.
- **Fix:** all three corrected. The `GovernedResolver` paragraph now states the
  asymmetry (one Protocol has a reference, the other was ruled impossible) and
  the plan-factory docstring cites Amendment A.2 with the measurement behind it.
- **Commit:** `82b6ad7`

### 4. [Measurement] The fixture's stated reason for scoring against `max(observed_at)` is false

- **Found during:** Task 1, reading
  `tests/client/fixtures/deployment/resolver.py::_debt_scorer`.
- **The claim:** *"`GovernedResolver` takes one `debt_scorer` at construction
  and calls it with the view alone, so a scorer cannot see the question's
  `asked_at`."*
- **The measurement:** `GraphView.as_of` carries it.
  `GovernedResolver.__call__` reads the graph at `request.asked_at`, and
  `src/ccf/operators/categories.py::_substitute` preserves `view.as_of` through
  every operator, so `execution.view.as_of == request.asked_at`. The reference
  scorer reads it and therefore measures **absolute age**, not spread.
- **Not fixed here:** the fixture is `17-13`'s to replace, and editing it now
  would churn a file that plan deletes. Recorded so the claim does not survive
  as folklore.

### 5. [Vacuous acceptance criterion] Task 3's "mypy --strict clean"

- **Measured:** `pyproject.toml` sets `[tool.mypy] files = ["src", "runtime"]`.
  `tests/` is not in scope, so the criterion cannot be discharged by the gate.
  Run explicitly, `mypy --strict tests/products/test_reference_debt_scorer.py`
  reports 9 `import-untyped` errors — and the identical class of error appears
  on a pre-existing file (`tests/products/test_gate_independence.py`, 3 errors),
  so the finding is about the environment's editable install, not about this
  module. `make typecheck` (the real gate) is **clean over 209 source files**.
- This is the same shape as the standing hazard about `examples/` not being
  typechecked. Recorded, not worked around.

## What this plan deliberately did not do

`ProjectionPlanFactory` was **not** attempted, gestured at, or partially added.
Amendment A.2 ruled it impossible as scoped: `ProjectionPlan` is itself a
Protocol, no declarative plan artifact exists in the tree, and mapping a
`GraphView` of entities onto a payload schema's declared fields is invention
rather than mapping. `17-12` handles the narrow written exception that replaces
it. `GovernedResolver` also gained **no default** for `debt_scorer` — wiring the
reference as the default is `17-13`'s work and its success criterion.

## Known Stubs

None. `AssemblyDebtScorer` is complete for the seam it implements;
`DeclaredFactor` is a shipped mechanism (a stated assumption with an identity),
not a placeholder.

## Threat Flags

None. This plan adds no network endpoint, no auth path, no file access pattern
and no schema at a trust boundary. `AssemblyDebtScorer` holds no graph handle,
opens no connection, and reads no clock.

One adjacent property worth naming for the record rather than as a flag: the
debt figure this scorer produces is computed over a possibly principal-scoped
view, and is therefore **not comparable across principals**. That is consistent
with `D-IMPL-105`'s resolution — a refused consultation is not part of that
principal's `C_required`, so there is no second figure to difference against —
and it is stated in the class docstring so a deployment does not learn it from a
support ticket.

## Self-Check: PASSED

Files claimed created, verified present:

- `src/ccf/products/debt_scorer.py` — FOUND
- `tests/products/test_reference_debt_scorer.py` — FOUND
- `docs/surface-changes/17-11-reference-debt-scorer.md` — FOUND

Commits claimed, verified in `git log`:

- `b0b9709` — FOUND (`feat(17-11): ship the reference AssemblyDebtScorer`)
- `82b6ad7` — FOUND (`docs(17-11): correct the resolver seam's claim`)
- `26303ab` — FOUND (`test(17-11): the reference debt scorer, with every
  assertion watched failing`)
- `2d0b443` — FOUND (`docs(17-11): surface-change fragment`)

No modification to `.planning/STATE.md` or `.planning/ROADMAP.md`; no
`state.*` or `roadmap.*` SDK writer was invoked.
