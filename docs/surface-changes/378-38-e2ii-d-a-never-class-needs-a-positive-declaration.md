# 378-38 — SEC-020 E2 (ii) (d): a class affirming `never` needs its plan factory's positive declaration; silence is refused at construction

`D-IMPL-378` owed ruling **E2 (ii)**, ruled option **(d)** by Dave on 2026-10-08 at 16:40 MST, verbatim:
*"Require a positive declaration, default silence to refusal, and explicitly limit the trusted-code assumption to
deployment code callers cannot influence. Keep the false-declaration counterexample visible."* **SEC-020 stays OPEN**:
Dave did not approve its closure, and a false declaration still tells a withheld subject from a nonexistent one.

**What changes.** A plan factory may now state, in its own code, that no projection it builds withholds its subject:
`withholds_no_subject()` returning `True` (`ccf.products.resolver.NonWithholdingPlanFactoryProtocol`, an optional
companion to `ProjectionPlanFactoryProtocol`, read once when the resolver is built, with no argument). A class
affirming `subject_withholding: never` is built only over a factory that says so. Silence — a factory that does not
implement the protocol — or any value but exactly `True` counts as able to withhold, and the class is refused where its
resolver is built (`NeverWithholdingNeedsAPositiveDeclaration`, a subclass of `NeverWithholdingProjectionCanWithhold`),
after a factory declaring that it withholds is named by that refusal and before Q8's composite refusals. On the paved
road, which builds a resolver per question, the refusal arrives with each question, before anything is fetched, the
same for every subject. `NeverWithholdingProjectionCanWithhold` and the serve-time defense `NeverWithholdingContradicted`
are unchanged in behavior; their docstrings, and `CompositeNeedsAWithholdingStance`'s, now say that a factory declaring
nothing is refused and that the defense remains for a FALSE positive declaration.

**Trusted deployment code, measured at its boundary.** The SDK cannot see inside a projection before running it, so the
declaration is trusted, and the assumption is limited to code no caller can influence. Measured by
`tests/products/test_sec020_e2ii_trusted_declaration.py::test_e2ii_d_no_caller_input_supplies_selects_or_alters_the_positive_declaration`:
statically, the declaration is read in one place, with no argument, on the resolver's own plan factory, and no door,
harness adapter or caller-supplied document builds a resolver or selects a factory; dynamically, at the in-process,
HTTP and MCP doors, a recording factory is read once per question with nothing handed to it, parameters naming the
declaration or a factory are refused `undeclared-parameter`, and a silent factory's class is refused whatever the
question claims; a control in which deployment code reads a caller's value into its declaration shows the measure sees
that influence. A false declaration is the residual: the class is built, and its withheld question raises
`NeverWithholdingContradicted` (an HTTP 500) where a nonexistent subject's is answered —
`tests/products/test_sec020_e2ii_trusted_declaration.py::test_e2ii_d_counterexample_a_false_positive_declaration_still_tells_the_withheld_subject_apart`,
and every run of SEC-020's closing test reports it outside the gate
(`tests/products/test_sec020_combined_proof.py::test_e2ii_limitation_the_false_declaration_cells_are_measured_not_gated`).

**What the tests measure, on test fixtures.** `tests/products/test_sec020_never_capability.py` (red before the change,
`DID NOT RAISE`): a `never` class over a factory declaring nothing, whether or not its projection withholds, and a
`never` composite over one, are refused at construction by name; so is a factory returning `False`, `None`, `1` or the
string `"True"`; the paved road refuses the withheld subject, an identifier nothing holds and the subject in a
deployment not holding it with one refusal and one text, and no source is asked. Controls: a positively declaring
factory constructs and answers; a `may-withhold` class over a silent factory is not refused; a factory declaring late
withholding and also that it never withholds is named by `NeverWithholdingProjectionCanWithhold`. One severing (the
check's call removed) turns the refusal tests red again.

**What it breaks.** Every class affirming `never` whose plan factory does not declare it. In this tree's tests, the
factories paired with `never` classes were measured (every projection they built under a `never` class ran with no
withheld signal) and now declare it; the closing test's worlds declare it on their policy-off factories. Outside the
tests, nothing on this tree: no example class affirms `never`. When the example batch makes `cp-14` and `cp-20` affirm
`never` (P2 (c)), their factories will need the declaration: `examples/cp-14-credit-memo-context/produce.py::MemoPlanFactory`
and `examples/cp-20-syndicated-lending-co-lender/produce.py::CoLenderPlanFactory`.

## ccf.products.resolver.NonWithholdingPlanFactoryProtocol

- Surface: ccf.products.resolver.NonWithholdingPlanFactoryProtocol
- Public surface: true
- Change type: added
- Before: absent; nothing let a plan factory state that its projection never withholds.
- After: a `runtime_checkable` Protocol with one method, `withholds_no_subject() -> bool`, an optional companion to `ProjectionPlanFactoryProtocol` on the `SubjectDisclosingPlanFactoryProtocol` precedent: `True` only if no projection the factory builds sets the withheld signal, for any subject or principal. Read once, with no argument, when a `GovernedResolver` is built over a class affirming `never`; classes at the default never read it.
- Why: SEC-020, E2 (ii) (d) (Dave, 2026-10-08 16:40 MST): require a positive declaration. A method rather than an attribute so a configurable or wrapping factory can state truthfully what it builds.
- Migration: a deployment whose class affirms `never` implements `withholds_no_subject()` returning `True` on its plan factory, only if its projection never sets the withheld signal. A plain function factory may carry it as an attribute.

## ccf.products.resolver.NeverWithholdingNeedsAPositiveDeclaration

- Surface: ccf.products.resolver.NeverWithholdingNeedsAPositiveDeclaration
- Public surface: true
- Change type: added
- Before: absent; a class affirming `never` over a plan factory that declared nothing constructed, and a projection of it that withheld anyway raised `NeverWithholdingContradicted` at serve for the withheld subject alone.
- After: a `NeverWithholdingProjectionCanWithhold` (so an `UnsupportedComposition`) raised by `GovernedResolver` construction when the class declaration affirms `subject_withholding: never` and the plan factory does not implement `NonWithholdingPlanFactoryProtocol`, or its `withholds_no_subject()` returns anything but `True`. The message names the class, never the subject.
- Why: SEC-020, E2 (ii) (d): default silence to refusal. A refusal where the resolver is built is the same whatever subject would have been asked.
- Migration: declare the factory's `withholds_no_subject()` (see above) or leave the class at the default `may-withhold`. Code catching `NeverWithholdingProjectionCanWithhold` catches this too.

## ccf.products.resolver.GovernedResolver

- Surface: ccf.products.resolver.GovernedResolver
- Public surface: true
- Change type: behavior
- Before: construction refused a class affirming `never` only when its plan factory declared, through `SubjectDisclosingPlanFactoryProtocol`, that it withholds; `never` alone was a composite's withholding stance under P2 (c).
- After: construction also refuses a class affirming `never` whose plan factory does not positively declare that it never withholds, with `NeverWithholdingNeedsAPositiveDeclaration` — after the declared-capability check, before Q8's composite refusals (`CompositeNeedsAnEarlyPolicy`, `EarlyPolicyNeedsRequestAwareChildren`) and before Q12's listing check. A composite's `never` stance therefore needs the declaration as well. On the paved road the refusal arrives when the resolver is built for a question.
- Why: as above.
- Migration: as above; a class at the default `may-withhold` is unaffected.
