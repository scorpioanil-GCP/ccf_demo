# Phase 24.6 — deferred items

Out-of-scope discoveries, logged rather than fixed. Each names who measured it,
on which tree, and why it was left.

## D-1 — `tests/client/test_codec.py::test_every_refusal_kind_survives_the_round_trip_whole` is RED for three kinds

**Measured by:** plan `24.6-05`'s executor, at `921b85a8`, **before any edit of
this plan** — so it is not this plan's.

```
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/client -q
  → FAILED ...[tolerance-exceeded]
    FAILED ...[constraint-refusal]
    FAILED ...[policy-resolution-conflict]
```

**Cause.** The test is parameterized over `REFUSAL_KINDS` itself — deliberately,
so a new kind cannot escape the round-trip guarantee — and builds one instance of
each kind through a generic `_sample_value(field.annotation)` helper that knows
`str` and little else. The three kinds plans `24.6-02` and `24.6-04` added carry
`ProvenanceSource`, `Decimal` and `DebtAssessment` fields, which `_sample_value`
returns `"x"` for, and pydantic refuses at construction.

**Why left.** `tests/client/test_codec.py` is named by no plan in this phase, and
the repair — teaching `_sample_value` about model-typed and `Decimal` fields — is
a genuine widening of a shared test helper rather than a fix to anything
`24.6-05` touched. It fails **loudly**, so it is not a control silently reporting
clean. Plan `24.6-05` removed one kind (`empty-result-refusal`), which changes
the parameter list by one and fixes nothing here.

**Who should own it.** A phase plan that touches the refusal vocabulary again, or
a close-time fix. It is a one-function change.

## D-2 — a British spelling in `src/ccf/products/debt_scorer.py`'s module docstring

`"honoured"` (module docstring, the "Amendment A.1" paragraph), against
CLAUDE.md §11's US-English rule. Predates this phase. Left because plan `24.6-05`
rewrote a different section of that docstring and a drive-by edit to an untouched
paragraph is an unclaimed change to a file another plan may hold.
