# 17-11 — the reference `AssemblyDebtScorer`

## What did **not** change, stated first

- **`AssemblyDebtScorerProtocol` is byte-identical in shape.** Same
  `@runtime_checkable` Protocol, same single keyword-only `__call__(*, view)`,
  same `DebtAssessment` return. Only its *docstring* changed, and only to stop
  asserting something that is no longer true. No entry is filed against the
  Protocol name below, and that absence is deliberate.
- **No scoring machinery moved.** `ccf.halflife.debt.FreshnessScorer`,
  `assess_debt`, `basic_debt`, `context_debt`, `DebtFactors`, `DebtProfile`,
  `HalfLifeTable` and `ScorerPin` are all unedited. This plan *adapts* them; it
  reshapes none of them.
- **`GovernedResolver` gained no default.** Its `debt_scorer` field is still
  required with no default, and the SDK still invokes nothing on its own
  authority. Wiring the reference scorer as a default is `17-13`'s work, not
  this plan's.
- **No `ProjectionPlanFactory` reference implementation was added, and none is
  coming under this scope.** Amendment A.2 of the 2026-08-16 spec ruled one
  impossible as scoped. A "pass-through" plan was proposed during that exchange
  and withdrawn.

## ccf.products.debt_scorer.AssemblyDebtScorer

- Surface: ccf.products.debt_scorer.AssemblyDebtScorer
- Public surface: true
- Change type: added
- Before: absent. `AssemblyDebtScorerProtocol` was declared in
  `ccf.products.resolver` and nothing in `src/` or `runtime/` implemented it,
  so every deployment wrote the `GraphView` → `DebtFactors` adapter itself and
  made the seam's row-selection choice silently, in its own tree. The Phase 17
  client fixture's `resolver.py` is the measured cost
- After: a frozen, keyword-only dataclass conforming to
  `AssemblyDebtScorerProtocol`, taking a `HalfLifeTable`, a `DebtProfile` and a
  `DebtFactorScorerProtocol` for each of `C` and `S` — none defaulted. It maps
  one `Observation` per entity record, typed by that record's own
  `entity_class` and dated by its `observed_at`, and scores `F` through the
  shipped `FreshnessScorer` at the view's own `as_of`
- Why: CLAUDE.md §11 — *"Reference implementations ship alongside Protocols"* —
  and Amendment A.1 of
  `docs/superpowers/specs/2026-08-16-reference-plan-factory-and-debt-scorer.md`,
  which rules that the Protocol's stated objection overstates the case: a
  documented, overridable default is not a choice imposed on every deployment,
  it is what a reference implementation is. The row-selection choice the
  Protocol names is made **explicitly** here — the rows that *survived* being
  read, with its reason, its observable consequence and its override path in
  the class docstring — rather than avoided
- Migration: none. A deployment keeps its own scorer if it has one; this one is
  supplied by the deployment, never selected by the SDK. A deployment adopting
  it supplies the two artifacts it already registered plus its own `C` and `S`

## ccf.products.debt_scorer.DeclaredFactor

- Surface: ccf.products.debt_scorer.DeclaredFactor
- Public surface: true
- Change type: added
- Before: absent. `DebtFactors` records that only `F` has an SDK reference
  scorer — `C` and `S` are supplied by the caller, because the SDK would
  otherwise have to invent a required-field vocabulary and a contradiction
  detector — but there was no shipped way to *state* an unmeasured factor, so a
  deployment either wrote a scorer or passed a bare number that reached the
  delivered product indistinguishable from a measurement
- After: a `DebtFactorScorerProtocol` implementation that reports a value the
  deployment declared, reading neither `observations` nor `now`, and carrying
  its own `scorer_id` / `scorer_version` so the assertion is pinned into the
  Decision Replay record under `D-IMPL-47`
- Why: the honest form of "we did not measure this". An examiner reading a
  replay record can tell a declared factor from a measured one without reading
  any code, which an unpinned bare number does not allow. `value` has no
  default on the `D-IMPL-38` discipline: a defaulted factor would put a number
  the SDK invented inside a delivered product's content address
- Migration: none — new name, no prior shape

## ccf.products.debt_scorer.DECLARED_FACTOR_SCORER_ID

- Surface: ccf.products.debt_scorer.DECLARED_FACTOR_SCORER_ID
- Public surface: true
- Change type: added
- Before: absent
- After: `"ccf.reference.declared-factor"`, the identity `DeclaredFactor` pins
  into replay
- Why: exported for the reason `ccf.halflife.debt.FRESHNESS_SCORER_ID` is —
  the id a replay record carries and the id a consumer matches against must
  come from one place, or the two drift and a replay silently resolves nothing
- Migration: none

## ccf.products.debt_scorer.DECLARED_FACTOR_SCORER_VERSION

- Surface: ccf.products.debt_scorer.DECLARED_FACTOR_SCORER_VERSION
- Public surface: true
- Change type: added
- Before: absent
- After: `"1.0.0"` — the version of `DeclaredFactor`'s *computation*, which is
  "report what was declared". Not a calibration and not an artifact value; it
  moves only if that computation changes
- Why: `D-IMPL-47` requires the scorer version *in force* to be pinned into
  replay, because a factor value is only reproducible alongside the computation
  that produced it. Exported beside the id for the same reason the id is
- Migration: none

## src/ccf/products/resolver.py

- Surface: src/ccf/products/resolver.py
- Public surface: false
- Change type: behavior
- Before: the docstring asserted that the SDK ships no implementation of this
  Protocol and implied it should not — *"a resolver that scored debt itself
  would be choosing for every deployment, which is CLAUDE.md §6.4 firing"*
- After: it names `ccf.products.debt_scorer.AssemblyDebtScorer` as the shipped
  reference, states the row-selection choice made there, and keeps the argument
  about why the choice is semantically load-bearing. `ProjectionPlanFactoryProtocol`'s
  docstring likewise records Amendment A.2's ruling and the measurement behind
  it, and `GovernedResolver`'s "the debt scorer is deployment code and has no
  artifact form" paragraph was corrected
- Why: the Protocol's argument was good and its conclusion was wrong. Shipping
  no implementation did not spare any deployment the choice; it made every
  deployment write the adapter *and* make the choice unstated. Classified
  `Public surface: false` because no exported Python name changed shape — the
  Protocol's signature, return type and export are untouched, so this entry can
  never correspond to a manifest diff line
- Migration: none — no signature moved
