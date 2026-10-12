# 20261011-11 — a request contract declares a decimal default for a `number` argument

Dave, 2026-10-11 20:19 MST, ruling 1 (the second bounded SDK round: *"decimal defaults ... Preserve exact decimal
meaning"*). Finding CP05-R2-F-01: a Control Plane document quotes its numbers (a bare float is refused as not
bit-stable), so `defaults: {materiality: "0.05"}` arrived as text and the contract refused it against the declared
`number` type. A `number` argument therefore had no way to declare what omission means; cp-05 kept its defaults
under an unread key, and since SEC-019 the `internal-appetite` regime (a policy `maximum` on `materiality`) refused
every question omitting it `required-absent` — in cp-05, door-cp-05 and cp-14's exposure child.

What changed: the declared default is decoded by the SAME rule that decodes a caller's value (`D-IMPL-302`):
declared `number` + canonical decimal text (`CANONICAL_DECIMAL`: sign, digits, optional fraction — no exponent,
padding, `NaN`, `Infinity` or leading `+`) -> exact `Decimal`, built from the text, never through a float. Nothing
else is decoded: text under `integer` or `string` is unchanged, and a Python float default is still refused.

No kind flag (contrast `PolicyConstraint.preferred_decimal`): the kind is already in the same document's bytes —
the argument's declared `type` — and a decoded decimal renders back to exactly the text it was read from, so the
contract's canonical bytes and content address are those of what the author wrote (`"0.050"` stays its own value
and address). Measured in `tests/products/test_declared_decimal_default.py`.

## ccf.products.request.ProductRequestContract

- Surface: ccf.products.request.ProductRequestContract
- Public surface: true
- Change type: behavior
- Before: a `defaults` entry for a declared `number` argument given as canonical decimal text (`"0.05"`) was refused at construction ("declares defaults it cannot honor ... do not satisfy the declared argument's own type")
- After: the same entry is read as the exact `Decimal("0.05")`; every other default is judged exactly as before
- Why: CP05-R2-F-01; Dave 2026-10-11 20:19 MST ruling 1. Red test: `tests/products/test_declared_decimal_default.py::test_a_quoted_decimal_default_for_a_number_argument_is_the_exact_decimal`; refusals kept: `::test_text_that_is_not_a_canonical_decimal_for_a_number_is_still_refused`, `::test_a_python_float_default_is_still_refused`
- Migration: a deployment that converted a quoted decimal default to `Decimal` by hand may hand the document's value over unchanged; a deployment that kept decimal defaults under an unread key moves them to `defaults:`

## ccf.products.request.decode_declared_number

- Surface: ccf.products.request.decode_declared_number
- Public surface: true
- Change type: added
- Before: the decoding lived inline in `decode_declared_request`
- After: `decode_declared_number(value, *, declared_type)` is the one decoding, used by `decode_declared_request` (callers) and by `ProductRequestContract` (declared defaults); `decode_declared_request`'s behavior is unchanged
- Why: one rule for a caller's value and a declared default, so the two cannot drift. Red test: `tests/products/test_declared_decimal_default.py::test_the_default_and_a_caller_stating_the_same_text_are_one_value`
- Migration: none
