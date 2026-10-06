# 370-20 — SEC-020: a projection can withhold a subject, and a withheld subject reads as a nonexistent one

`D-IMPL-370` (and `D-IMPL-368`/`D-IMPL-369`), row SEC-020, ruling Q12 (a) of
`docs/superpowers/specs/2026-10-05-remaining-rows-rulings-batch.md`
(constant-fill). Measured before this entry: a Policy-OPERATOR withhold was
already indistinguishable from a nonexistent subject, because the debt, the
empty finding and the TTL anchor are computed from the operator view. A
PROJECTION-level withhold was not. When Π returned a missing subject's payload
for an admitted subject, the served vessel differed from a nonexistent
subject's at `computed_empty`, `debt.debt`, `debt.factors.freshness` and
`debt.scorers`. A `from_entity_freshness` class also SERVED the withheld subject
on its observation instant, where the nonexistent subject was refused
`ttl-anchor-refusal`. `ProjectionOutput` had no way to say "withheld", so the
resolver could not tell a withhold from a legitimately empty answer. The exploit
test is `tests/products/test_withheld_is_indistinguishable_from_absent.py`.

**Constant-fill, ruled:** when the signal is raised, the product is the vessel
the same plan yields over an EMPTY view. That means the same empty finding
naming every operator, the same debt, scorers and signal, and the same anchor.
For an evidence-anchored class that anchor is the empty view's own refusal. The
vessel is never `None`/zero. The signal is the only key into that branch. An
empty payload without it keeps the debt and finding its real view earned.

## ccf.projection.plan.ProjectionOutput

- Surface: ccf.projection.plan.ProjectionOutput
- Public surface: true
- Change type: reshaped
- Before: `plan_id: str`, `payload: Mapping[str, Any]`. A projection that withheld a subject could only do so silently.
- After: adds `withheld: bool = False`, which is hash-transparent at `False`, so every output written before the field existed is byte-identical. A projection sets `withheld=True` and returns, as `payload`, exactly what it returns for a subject it cannot see. The governed resolver then computes the product's debt, empty finding, TTL anchor, the staleness gate's touched set and a declared product gate's evidence from `ExecutionResult.over_empty_view()`. The replay record keeps the execution that ran.
- Why: SEC-020 and Q12 (a). The withheld subject's claims must not move any member a consumer reads. A withhold is never inferred from an empty payload (`D-IMPL-242` amendment 1).
- Migration: none for a projection that does not withhold. A projection that withholds today by returning an empty payload should set `withheld=True` to get the constant-fill rendering.

## ccf.projection.engine.ExecutionResult

- Surface: ccf.projection.engine.ExecutionResult
- Public surface: true
- Change type: reshaped
- Before: no way to express the execution the same plan would have produced over an empty view.
- After: adds the method `over_empty_view()`. It returns a copy whose `view` is the empty view of the same tenant as of the same instant, and whose `empty_results` names every invoked operator. Every other member (plan, operators, steps, queries, attestation, store pin, projection) is the execution that ran.
- Why: SEC-020. This is the one definition of "the plan over an empty view" that the resolver's constant-fill branch reads.
- Migration: none. The method is additive.
