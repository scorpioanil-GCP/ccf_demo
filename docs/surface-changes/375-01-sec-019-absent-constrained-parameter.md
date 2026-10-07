# 375-01 — SEC-019: an absent constrained parameter is refused, never skipped

`D-IMPL-356`, sub-ruling D11 (the `SEC-019` rider of the accepted v1.0.2
design), built red-first. The row as worded in the 2026-09-23 security review:
*"A policy `maximum` on `debt_tolerance` is skipped when the caller omits the
parameter and no default exists, served at any debt."* The ruled remedy: *"a
bounding constraint (`maximum`/`minimum`/`allowed_set`) on a parameter with no
value and no declared default is a `required-absent` refusal; `required` stays
the explicit form; `preferred` stays non-refusing."* It amends the realization
of `D-IMPL-253` Q5, under which only `required` refused absence. The exploit
tests are `tests/products/test_sec019_absent_constrained_parameter.py`.

**Two skip sites closed, one kept by ruling.** The constraint layer skipped a
bounded parameter with no value
(`src/ccf/products/constraints.py::resolve_effective_request`, step 3), and the
tolerance step served an absent tolerance at any Debt
(`src/ccf/products/gates.py::refuse_over_tolerance`). Both now refuse. The
capability step (step 4 of the same function) still passes over an absent
parameter that only a technical capability bounds: that is not a registered
policy constraint, and a parameter with no registered constraint keeps its
behavior.

**No value is invented.** The SDK supplies no default for an absent bounded
parameter (CINV-01). A deployment that wants an omitted parameter served under
a bound declares the default itself.

**The reference resolver's version moves with its behavior.** The reference
resolution now refuses a case it used to skip, so
`REFERENCE_CONSTRAINT_RESOLVER_VERSION` goes from `1.0.0` to `1.1.0`, and a
test pins the label to a fingerprint of the behavior it names.

## ccf.products.constraints.resolve_effective_request

- Surface: ccf.products.constraints.resolve_effective_request
- Public surface: true
- Change type: behavior
- Before: a `maximum`, `minimum` or `allowed_set` that reached a parameter with no value after defaults and the caller's overlay was skipped. The resolution completed, the constraint's pin was recorded in `applied`, and the bound was held against nothing. For `debt_tolerance` with no class default, the governed resolver then served the product at any observed Debt.
- After: that case is refused as a `ConstraintRefusal` with reason `required-absent`, carrying the highest-priority such bound (authority `policy`, the constraint's artifact pin and `policy_id`), `requested=None`, every attempted override, and the evidence accumulated so far. It is the same determination a `required` constraint already returned for an absent parameter. Through `ReferencePolicyConstraintResolver`, every governed serve (`GovernedResolver` and the doors over it) answers `constraint-refusal` / `required-absent` before anything is read. Unchanged: `required`; `preferred` alone (guidance, never refusing); a parameter a default or the caller supplies (held to the bound as before); a parameter no registered policy constraint bounds.
- Why: SEC-019 (`D-IMPL-356` D11). There is no value to hold to the bound, and skipping it served the request as though the bound did not exist. Red tests: `tests/products/test_sec019_absent_constrained_parameter.py::test_the_worded_case_a_policy_maximum_on_an_omitted_tolerance_is_refused_not_served` and `::test_an_absent_parameter_a_bounding_constraint_reaches_is_refused_required_absent`.
- Migration: declare a default (the class's `default_debt_tolerance`, or the request contract's `defaults` or `relative_defaults`) for every parameter a policy constraint bounds that a caller may omit, or the request is refused. A constraint whose `applies_to` reaches a class that does not declare the parameter at all now refuses that class's requests in its scope; narrow `applies_to` to the classes that carry the parameter.

## ccf.products.constraints.PolicyConstraintResolver

- Surface: ccf.products.constraints.PolicyConstraintResolver
- Public surface: true
- Change type: behavior
- Before: the Protocol's contract said nothing about an absent bounded parameter, and the reference implementation skipped it.
- After: a conforming resolver refuses an absent bounded parameter as `required-absent`, as the reference implementation now does. The governed resolver hands the tolerance step only what a completed resolution established, so a resolver that skipped an absent bounded tolerance would still be served at any Debt.
- Why: SEC-019 (`D-IMPL-356` D11). The governed resolver cannot re-derive the constraint set; the seam that reads it owns the refusal.
- Migration: a deployment-supplied resolver adopts the same rule, or delegates to `resolve_effective_request`.

## ccf.products.constraints.REFERENCE_CONSTRAINT_RESOLVER_VERSION

- Surface: ccf.products.constraints.REFERENCE_CONSTRAINT_RESOLVER_VERSION
- Public surface: true
- Change type: behavior
- Before: `"1.0.0"`, reported by `ReferencePolicyConstraintResolver.resolver_version`. The label named the resolution that skipped an absent bounded parameter.
- After: `"1.1.0"`, the resolution that refuses it (`required-absent`). `tests/products/test_reference_resolver_version.py` pins the label together with a fingerprint of the behavior it names: nineteen fixed questions put to the reference resolver over a real Control Plane, reaching every decision the resolution makes. A behavior change that keeps the label is a red build, and `1.0.0` and `1.1.0` are recorded as differing in exactly the three absent-bounded questions.
- Why: SEC-019 (`D-IMPL-356` D11). `D-IMPL-253` Q8 puts `resolver_version` on the Protocol so the resolver in force can be pinned into replay, which makes the version a claim about behavior: a label that outlives a change in what it labels is a false pin.
- Migration: none, unless a consumer compares `resolver_version` against `"1.0.0"`; it reads `"1.1.0"` now.

## ccf.products.gates.refuse_over_tolerance

- Surface: ccf.products.gates.refuse_over_tolerance
- Public surface: true
- Change type: reshaped
- Before: `(product, *, tolerance: EffectiveParameter | None) -> ToleranceExceededRefusal | None`. An absent tolerance (`None`) was served at any Debt, with no way for the step to learn whether a policy bounded it.
- After: `(product, *, tolerance: EffectiveParameter | None, policy_bound: ParameterBound | None) -> ToleranceExceededRefusal | ConstraintRefusal | None`. `policy_bound` is required and has no default: it is the bound a registered policy constraint places on `debt_tolerance`, as the Authority layer reported it, or `None` when none does. With no tolerance and a `policy_bound`, the step returns a `ConstraintRefusal` (`required-absent`, carrying the bound) instead of serving. With neither, it serves as before. A present tolerance is compared exactly as before, and `policy_bound` is not read: the policy's fold already happened upstream. The governed resolver passes the policy bound off the resolved tolerance's own record; for an absent tolerance that is `None` by construction, because the resolution has already refused the bounded case.
- Why: SEC-019 (`D-IMPL-356` D11), the same rule at the delivery step, so "nothing bounds it" is a statement the caller makes rather than a default it gets by leaving an argument out. Red tests: `tests/products/test_sec019_absent_constrained_parameter.py::test_the_tolerance_step_cannot_serve_an_absent_tolerance_a_policy_bounds` and `::test_control_the_tolerance_step_still_serves_an_absent_tolerance_nothing_bounds`.
- Migration: every direct caller passes `policy_bound=`: the policy bound on the tolerance, or `None` when no policy constraint bounds it. A caller that receives the `ConstraintRefusal` envelopes it as the pre-assembly kind it is, with no lineage, because `envelope_for` refuses a lineage for `ConstraintRefusal`.
