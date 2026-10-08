# 378-24 — SEC-020: every composite declares its withholding stance at construction (P2 (c), a CANDIDATE)

`D-IMPL-378` owed ruling **P2** ("composites that decide to withhold late"),
option **(c)**: *"Require every composite to declare its stance at
construction."* The coordinator recommends (c); **Dave has not ruled P2**, so
this is a candidate built on lane `378d-s020trial`'s branch so that its effect
on SEC-020's closing test is measured before the ruling. **SEC-020 stays
OPEN.** Dave's Q8 (2026-10-07), verbatim: *"(a) Require early withholding for
affected composites. Make it an enforced policy decision before
subject-dependent fetches, child resolution or scoring. It cannot depend on
learning whether the subject exists."*

**What the tests measure, on test fixtures.**
`tests/products/test_sec020_p2c_composite_stance.py`: a composite whose plan
factory declares no early policy and whose class does not affirm
`subject_withholding: never` is refused when its `GovernedResolver` is
constructed, before any question, by name (red before the change: the
composition constructed); one declaring an early policy constructs; one whose
class affirms `never` constructs. One severing (the check neutered) turns the
refusal test red again.

**What it breaks.** Every composite that declares neither stance is refused at
construction. On this tree that includes the shipped composite examples
`examples/cp-14-credit-memo-context` and `examples/cp-20-syndicated-lending-co-lender`
(each needs `subject_withholding: never` on its product class; neither
projection withholds) and the composite test fixtures that build a composite
with a plain plan factory. They are listed by test id in the lane report and
are not migrated here: the examples wait for Dave's ruling and C3's timing.

## ccf.products.resolver.CompositeNeedsAWithholdingStance

- Surface: ccf.products.resolver.CompositeNeedsAWithholdingStance
- Public surface: true
- Change type: added
- Before: absent; a composite that declared no early policy constructed, and a withhold decided inside its projection raised `CompositeWithheldLate` at call time, for the withheld subject only.
- After: an `UnsupportedComposition` raised by `GovernedResolver` construction when a class that declares `requires` has neither an early policy (`SubjectDisclosingPlanFactoryProtocol.subject_disclosure()` returning a `SubjectDisclosurePolicy`) nor `subject_withholding: never` on its declaration.
- Why: SEC-020, owed ruling P2 option (c), a candidate: a refusal decided when a projection withholds is decided for the withheld subject only and is itself distinguishable; a refusal at construction is the same for every subject.
- Migration: declare a stance on every composite: `subject_withholding: never` on the product class when its projection never withholds, or an early policy through the plan factory's `subject_disclosure()`.

## ccf.products.resolver.GovernedResolver

- Surface: ccf.products.resolver.GovernedResolver
- Public surface: true
- Change type: behavior
- Before: construction accepted a composite that declared no withholding stance.
- After: construction refuses such a composite with `CompositeNeedsAWithholdingStance`, after the Q12 listed-class check and before any authority is minted.
- Why: SEC-020, owed ruling P2 option (c), a candidate (see above).
- Migration: as above; a non-composite class is unaffected.
