# 378-31 — SEC-020 E2 (ii): a class affirming `never` over a plan factory that declares it withholds is refused at construction; CT-D (a)

`D-IMPL-378` owed ruling **E2 (ii)**, ruled by Dave on 2026-10-08 at 12:29 MST,
verbatim: *"E2 (ii) REJECTED as disclosure-only: The proposed hidden-subject
exception versus nonexistent-subject 200 is a measured oracle. Validate
withholding capability against the class declaration at construction; retain
the runtime check as defense. Keep the violation probe visible until the
treatment satisfies the closure criterion."* **SEC-020 stays OPEN.**

**What the SDK can know at construction, and what it now checks.** Whether a
projection withholds is decided inside the deployment's own `invoke()`, which
sets the withheld signal on its output; no operator and no declared plan step
sets it. What the resolver can read without asking a question is the plan
factory's `SubjectDisclosingPlanFactoryProtocol` declaration, read once at
construction: an early policy that does not disclose some subject to some
principal or role (verified: the resolver itself withholds that subject), or
`subject_disclosure()` returning `None` (declared: the projection withholds
late). A class affirming `subject_withholding: never` over either is now
refused by name when its resolver is built (on the paved road, which builds a
resolver for each question, before anything is read for it), the same for
every subject. A plan factory that declares nothing
still constructs under `never`; if its projection withholds anyway, the
serve-time `NeverWithholdingContradicted` remains the defense, and it still
tells the withheld subject from a nonexistent one.

**What the tests measure, on test fixtures.**
`tests/products/test_sec020_never_capability.py` (red before the change: three
of the compositions constructed, and a `never` composite declaring late
withholding was refused as `CompositeNeedsAnEarlyPolicy`): a `never` class
whose early policy withholds the asked subject, one whose plan factory
declares late withholding, and the same two as composites are refused at
construction by name; `never` over a plan factory declaring nothing, or an
early policy that withholds nobody, constructs and serves; a `may-withhold`
class with an early policy constructs and serves; a `never` class whose
undeclared projection withholds constructs, and its question raises
`NeverWithholdingContradicted`. In SEC-020's closing test
(`tests/products/test_sec020_combined_proof.py::test_a_withheld_subject_under_a_never_class_is_indistinguishable`)
the three declaring configurations are refused alike on every side, with the
same configuration without the capability answering; the two undeclared ones
still tell a withheld subject from a nonexistent one (an exception, an HTTP
500, against an answer) and stay red. One severing (the check's call removed)
turns the refusal tests red again.

**What it breaks.** A class affirming `never` whose plan factory implements
`SubjectDisclosingPlanFactoryProtocol` returning `None`, or a policy that
withholds some subject. None on this tree outside the new tests: the closing
test's readable worlds declare early policies that withhold nobody.

**CT-D (a), in the same change.** Dave, 2026-10-08 12:29 MST: *"for
diagnostic precedence; this does not resolve E2(ii)'s oracle."* At serve, a
composite whose class affirms `never` and whose projection withholds late was
refused as `CompositeWithheldLate`, because Q8's check ran first; it is now
refused as `NeverWithholdingContradicted`, which is checked first. Both refuse
before anything is recorded. `CompositeWithheldLate` remains for a composite
whose early policy does not cover a subject its projection withholds.
Measured by `tests/products/test_sec020_never_capability.py` (red before the
reordering: `CompositeWithheldLate` observed) and by the closing test's
listed-class cell, whose expectation for the composite moved with it.

## ccf.products.resolver.NeverWithholdingProjectionCanWithhold

- Surface: ccf.products.resolver.NeverWithholdingProjectionCanWithhold
- Public surface: true
- Change type: added
- Before: absent; a class affirming `never` constructed whatever its plan factory declared, and the question about a subject its projection withheld raised `NeverWithholdingContradicted` at serve, for that subject only.
- After: an `UnsupportedComposition` raised by `GovernedResolver` construction when the class declaration affirms `subject_withholding: never` and the plan factory, through `SubjectDisclosingPlanFactoryProtocol`, returns `None` or a `SubjectDisclosurePolicy` that does not disclose some subject to some principal or role.
- Why: SEC-020, E2 (ii) (Dave, 2026-10-08 12:29 MST): validate withholding capability against the class declaration at construction. A refusal at construction is the same whatever subject would have been asked; one at serve is raised for the withheld subject alone.
- Migration: affirm `never` only for a class whose projection never withholds; a class whose plan factory declares withholding keeps the default `may-withhold`.

## ccf.products.resolver.GovernedResolver

- Surface: ccf.products.resolver.GovernedResolver
- Public surface: true
- Change type: behavior
- Before: construction accepted a class affirming `never` whatever its plan factory declared through `SubjectDisclosingPlanFactoryProtocol`.
- After: construction refuses it with `NeverWithholdingProjectionCanWithhold` when the plan factory declares it withholds, immediately after reading `subject_disclosure()` (once) and before Q8's composite refusals (`CompositeNeedsAnEarlyPolicy`, `EarlyPolicyNeedsRequestAwareChildren`), so a `never` composite declaring late withholding is named by this check first. At serve, the `never` check now runs before Q8's `CompositeWithheldLate` check (CT-D (a)).
- Why: as above; each order names the class's own contradiction before the composite rule it also breaks.
- Migration: as above; a class at the default `may-withhold` is unaffected.

## ccf.products.resolver.NeverWithholdingContradicted

- Surface: ccf.products.resolver.NeverWithholdingContradicted
- Public surface: true
- Change type: behavior
- Before: the only check of a class affirming `never`, at serve, after Q8's `CompositeWithheldLate` check.
- After: checked first among the serve-time withholding refusals, so a composite affirming `never` that withholds late raises it rather than `CompositeWithheldLate` (CT-D (a)); documented as the defense Dave retained for a plan factory that declares nothing and whose projection withholds anyway, and as still telling the withheld subject from a nonexistent one (measured by the closing test's E2 (ii) cells).
- Why: SEC-020, E2 (ii): *"retain the runtime check as defense"*; CT-D (a): *"for diagnostic precedence; this does not resolve E2(ii)'s oracle."*
- Migration: code catching `CompositeWithheldLate` for a composite whose class affirms `never` catches `NeverWithholdingContradicted` instead; both are `ProductNotResolvable`.

## ccf.products.resolver.CompositeWithheldLate

- Surface: ccf.products.resolver.CompositeWithheldLate
- Public surface: true
- Change type: behavior
- Before: raised for any composite whose projection withheld a subject its early policy did not, including one whose class affirms `never`.
- After: not raised for a composite whose class affirms `never`; that composite raises `NeverWithholdingContradicted`, checked first. Still raised for a composite whose early policy does not cover a subject its projection withholds.
- Why: SEC-020, CT-D (a) (Dave, 2026-10-08 12:29 MST): diagnostic precedence only.
- Migration: as for `NeverWithholdingContradicted` above.
