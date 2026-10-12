# 20261011-13 — evidence dated after the decision instant is a governed refusal, not a raise

Dave, 2026-10-11 20:19 MST, ruling 1 (*"cp-08's error-versus-refusal behavior"*). Finding CP08-R3-F-01: asked at
its drawdown day, cp-08 ingests an amendment booked weeks later; the freshness factor refuses to score an
observation dated after the instant it is evaluated at (`TemporalOrderError`), and `GovernedResolver` let that
exception escape where `docs/EXAMPLE-EVALUATION-CRITERIA.md` §D owes a governed refusal.

What changed: the resolver catches exactly `TemporalOrderError` at its scoring step and returns
`EvidenceAfterDecisionRefusal` (kind `evidence-after-decision-refusal`, reason `evidence-after-decision`; not a gate and no `GATE_*` token, the roster being ruled exact by D-IMPL-364 C2), recorded as
a post-projection refusal — the execution's operators and plan, no debt (none could be assessed), a replay
reference. Nothing is excluded and nothing is scored as fresh. Any other scorer failure still raises. Minimal
disclosure carries the fixed statement and no field; the HTTP status is the fulfillment-withheld class.

## ccf.products.gates.EvidenceAfterDecisionRefusal

- Surface: ccf.products.gates.EvidenceAfterDecisionRefusal
- Public surface: true
- Change type: added
- Before: absent; the resolver raised `ccf.halflife.decay.TemporalOrderError`
- After: a refusal (not a `GateRefusal`, on the `ToleranceExceededRefusal` precedent) carrying `reason`, `detail` and `decided_at`, kind `evidence-after-decision-refusal` in `REFUSAL_KINDS`
- Why: CP08-R3-F-01; Dave 2026-10-11 20:19 MST ruling 1. Red test: `tests/products/test_evidence_after_decision_refusal.py::test_evidence_dated_after_the_decision_instant_is_refused_by_name_with_a_record`
- Migration: a consumer switching on refusal kinds handles the new kind

## ccf.products.resolver.GovernedResolver

- Surface: ccf.products.resolver.GovernedResolver
- Public surface: true
- Change type: behavior
- Before: a debt scorer raising `TemporalOrderError` propagated the exception out of `__call__`
- After: that error is recorded and returned as `evidence-after-decision-refusal` with a replay reference; every other scorer exception still propagates
- Why: CP08-R3-F-01; Dave 2026-10-11 20:19 MST ruling 1. Red test as above; control kept: `tests/products/test_evidence_after_decision_refusal.py::test_any_other_scorer_failure_is_not_converted`; end to end: `tests/examples/test_cp_08_output.py::test_a_question_asked_on_the_drawdown_day_gets_a_governed_outcome_not_a_raise` (strict xfail removed)
- Migration: none
