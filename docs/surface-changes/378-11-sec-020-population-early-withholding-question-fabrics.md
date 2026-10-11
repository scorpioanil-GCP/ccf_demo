# 378-11 — SEC-020: an explicit population phase, early withholding as a declared policy, and a fresh fabric per question

`D-IMPL-378`, Dave's rulings of 2026-10-07 19:31 MST, verbatim: **Q7** *"(a)
Approve an explicit population-fetch mode. Subject-independent acquisition
must not receive the requested subject indirectly through context or closures.
Unsupported combinations must refuse construction."* **Q8** *"(a) Require early
withholding for affected composites. Make it an enforced policy decision before
subject-dependent fetches, child resolution or scoring. It cannot depend on
learning whether the subject exists."* **Q9** *"(a) Enforce a fresh fabric per
question whenever acquisition exists, including concurrent use. Document the
migration."* **Q10** *"(a), conditional. Two declared acquisition phases are
permitted, each once. This does not authorize recomputing the product twice or
fetching a synthetic nonexistent subject as a comparison."* Lane
`378-s020design`. **SEC-020 stays OPEN**: Dave's closure condition is a combined
proof across responses, refusal codes, public references, composite paths and
authorized record reads, which this change does not supply.

**What the tests measure, on test fixtures.** Every claim below is a measurement
in `tests/products/test_withheld_subject_population_composite_and_fabric.py` or
`tests/products/test_withheld_similarity_registry.py`, each red before the
change and green after, with one severing per ruling that reddened it.

- **A fabric that outlives the question (channel 6, M-6).** A fabric not booted
  for its question takes no acquisition, and a question fabric answers one
  question: a second one — sequential or concurrent, about any identifier — is
  refused before anything is read or fetched for it. The two-step existence
  measurement no longer runs on one handle, nor through a second boot of the
  same store that declares an acquisition phase.
- **Population-shaped acquisition (channel 1).** A population read declared as
  the population phase is handed no subject (a walk of everything reachable
  from what it is handed found none) and runs first; a late-withheld subject is
  rendered over the fabric after it, and matched a nonexistent subject's answer
  for a population and a hybrid source, both anchors, with and without the
  similarity operator.
- **Composite children (channel 4, I-1).** Under a declared early policy the
  children are asked about the declared undisclosed subject in place of the
  withheld one; the withheld composite matched a nonexistent subject's on both
  child anchors, including the case where a nonexistent subject's child refuses
  before the composite's plan runs.
- **One computation.** Under the early decision each declared acquisition phase
  is called once, the stand-in replaces the subject (it is never fetched in
  addition), and the product is computed once — exact even where the fabric
  already holds the withheld subject — and replays to its own address.

**What it does not cover** (each measured on the lane's probes at the
candidate, and disclosed in the security how-to, section 4.12). A population
read left inside the subject-keyed seam under a late withhold still differs:
that seam's obligation (acquire nothing for an identifier the source does not
hold) is trusted, not enforced. The owner check compares the phases, their
bound objects and one level of their closures, and does not see state two
separate objects share through a third. A composite's child-arguments mapping
is handed no request, so one that reads the subject from state the deployment
captured itself asks the child about the withheld subject, and the composite is
refused where a nonexistent subject's is served. A composite that declares
nothing and withholds inside its projection raises `CompositeWithheldLate` at
call time, after its children were asked. The question-fabric claim is held
per handle in one process, and a question's store stays on disk: booted again
plainly and asked with no acquisition phase, it still shows what the withheld
subject's question acquired. Freshness is verified at boot from the adapter's
path settings, so a substrate with none (a network store, and the in-memory
development store although each boot of it is new) cannot be booted for a
question and so cannot carry an acquisition phase. The record of an
early-withheld decision names the stand-in in its walk seeds and in a
composite's child questions; its replay reference and record are lane
`378-s020record`'s.

**Migration (Q9).** A deployment that composes `GovernedResolver` by hand and
declares an acquisition phase boots that fabric with `for_question=True` onto a
path that does not exist yet, asks it one question, and closes it. The paved
road does this for every question. A composition that asks a long-lived fabric
several questions with an acquisition phase now raises
`AcquisitionNeedsAQuestionFabric` at its first question; one with no
acquisition phase is unaffected. In this tree, 13 hand-built test sites hand
the resolver a seam (9 in `tests/products/test_resolver_seam.py`, 4 in
`tests/products/test_served_at_severings.py`): 12 refuse before acquisition and
needed nothing, and E5 moved to a fabric booted for its question, as did the
two fabrics in `tests/products/test_paved_road.py`'s low-road equivalence test.
Five sites that construct `GovernedResolver` directly now state
`population_acquisition=None`. The SEC-020 modules boot their question fabrics
the same way.

## ccf.products.resolver.GovernedResolver

- Surface: ccf.products.resolver.GovernedResolver
- Public surface: true
- Change type: reshaped
- Before: no population phase; the acquisition seam ran over any fabric, as often as asked; a subject Π withheld was always rendered by re-executing the plan without the request seed.
- After: adds the required, stated field `population_acquisition: PopulationAcquisitionSeamProtocol | None`. Before the first acquisition phase, the fabric must have been booted for its question (`AcquisitionNeedsAQuestionFabric`) and is claimed for it under a lock (`AcquiredFabricReused` for any second question, concurrent or not). The population phase runs once, handed a `PopulationQuestion`; the fabric is read; the subject-keyed seam runs once. A plan factory implementing `SubjectDisclosingPlanFactoryProtocol` is read once at construction; under its policy the decision is taken before anything is fetched, any child asked or anything scored, and an undisclosed subject is replaced by the declared undisclosed subject for the subject-keyed acquisition phase, the child questions and the walk's seed (the population phase is never handed a subject), with the product computed once. Construction refuses `PopulationPhaseSharesAnOwner`, `CompositeNeedsAnEarlyPolicy` and `EarlyPolicyNeedsRequestAwareChildren`; a call raises `UndisclosedSubjectAnswered` or `CompositeWithheldLate` before its decision is gated, recorded or served (a composite's children were already asked, and what they filed stays filed). Route A's re-execution runs only for a late withhold on a non-composite product.
- Why: SEC-020 channels 1, 4 and 6 under Q7–Q10.
- Migration: state `population_acquisition=None` where the resolver is constructed directly; boot a fabric with an acquisition phase `for_question=True` and ask it one question.

## ccf.products.resolver.build_governed_resolver

- Surface: ccf.products.resolver.build_governed_resolver
- Public surface: true
- Change type: reshaped
- Before: no population phase parameter.
- After: adds the optional `population_acquisition`, handed to the resolver as stated.
- Why: SEC-020 Q7.
- Migration: none; the parameter defaults to no population phase.

## ccf.products.resolver.PopulationQuestion

- Surface: ccf.products.resolver.PopulationQuestion
- Public surface: true
- Change type: added
- Before: absent.
- After: the effective request's class, lane, intent, freshness, instant and parameters, with no subject member.
- Why: SEC-020 Q7: what the population phase is handed cannot carry the asked identifier. A declared parameter that itself names an entity still reaches it.
- Migration: none; additive.

## ccf.products.resolver.PopulationAcquisitionSeamProtocol

- Surface: ccf.products.resolver.PopulationAcquisitionSeamProtocol
- Public surface: true
- Change type: added
- Before: absent.
- After: the population phase, `__call__(*, question, perspective)`, declared on its own and invoked once per question before the subject-keyed seam.
- Why: SEC-020 Q7 and Q10.
- Migration: none; additive.

## ccf.products.resolver.SubjectDisclosingPlanFactoryProtocol

- Surface: ccf.products.resolver.SubjectDisclosingPlanFactoryProtocol
- Public surface: true
- Change type: added
- Before: absent.
- After: an optional companion to `ProjectionPlanFactoryProtocol`: `subject_disclosure()` returns the declared `SubjectDisclosurePolicy`, read once at construction, or `None` for a projection that withholds only late (which a composite may not do).
- Why: SEC-020 Q8.
- Migration: none; additive.

## ccf.products.resolver.UnsupportedComposition

- Surface: ccf.products.resolver.UnsupportedComposition
- Public surface: true
- Change type: added
- Before: absent.
- After: a `ProductNotResolvable` naming a composition SEC-020's rulings do not support; decided by the composition, never by the subject.
- Why: SEC-020 Q7–Q9.
- Migration: none; additive.

## ccf.products.resolver.AcquisitionNeedsAQuestionFabric

- Surface: ccf.products.resolver.AcquisitionNeedsAQuestionFabric
- Public surface: true
- Change type: added
- Before: absent.
- After: an `UnsupportedComposition` raised immediately before the first acquisition phase when the fabric was not booted for its question.
- Why: SEC-020 Q9.
- Migration: boot the fabric with `for_question=True`.

## ccf.products.resolver.AcquiredFabricReused

- Surface: ccf.products.resolver.AcquiredFabricReused
- Public surface: true
- Change type: added
- Before: absent.
- After: a `ProductNotResolvable` raised when a question fabric already claimed is asked another question that reaches acquisition, sequentially or concurrently.
- Why: SEC-020 Q9.
- Migration: boot a fabric per question.

## ccf.products.resolver.PopulationPhaseSharesAnOwner

- Surface: ccf.products.resolver.PopulationPhaseSharesAnOwner
- Public surface: true
- Change type: added
- Before: absent.
- After: an `UnsupportedComposition` raised at construction (and at open on the paved road) when the two phases are one callable, bound to one object, or the population phase's closure holds the subject-keyed phase or its object.
- Why: SEC-020 Q7.
- Migration: declare the phases on separate objects.

## ccf.products.resolver.CompositeNeedsAnEarlyPolicy

- Surface: ccf.products.resolver.CompositeNeedsAnEarlyPolicy
- Public surface: true
- Change type: added
- Before: absent.
- After: an `UnsupportedComposition` raised at construction for a composite whose plan factory declares it withholds with no early policy.
- Why: SEC-020 Q8.
- Migration: declare a `SubjectDisclosurePolicy`.

## ccf.products.resolver.EarlyPolicyNeedsRequestAwareChildren

- Surface: ccf.products.resolver.EarlyPolicyNeedsRequestAwareChildren
- Public surface: true
- Change type: added
- Before: absent.
- After: an `UnsupportedComposition` raised at construction for early withholding over a child resolver that is never handed the request.
- Why: SEC-020 Q8.
- Migration: use a request-aware child resolver.

## ccf.products.resolver.UndisclosedSubjectAnswered

- Surface: ccf.products.resolver.UndisclosedSubjectAnswered
- Public surface: true
- Change type: added
- Before: absent.
- After: a `ProductNotResolvable` raised before the decision is gated, recorded or served when the policy did not disclose the subject and the projection answered it.
- Why: SEC-020 Q8.
- Migration: none; additive.

## ccf.products.resolver.CompositeWithheldLate

- Surface: ccf.products.resolver.CompositeWithheldLate
- Public surface: true
- Change type: added
- Before: absent.
- After: a `ProductNotResolvable` raised after the composite's children were asked, and before its decision is gated, recorded or served, when its projection withholds a subject its early policy did not. What the children filed stays filed.
- Why: SEC-020 Q8.
- Migration: a composite withholds through a declared early policy.

## ccf.products.subject_disclosure.SubjectDisclosurePolicy

- Surface: ccf.products.subject_disclosure.SubjectDisclosurePolicy
- Public surface: true
- Change type: added
- Before: absent.
- After: the declared early policy: `undisclosed_subject` (inside `SUBJECT_FLOOR_V1`, never itself withheld), `by_principal` and `by_role` (both stated); `discloses(*, subject, perspective)` reads only those.
- Why: SEC-020 Q8: a policy decision taken from the request and the declaration alone; measured identical for a subject the source holds and one it does not.
- Migration: none; additive.

## ccf.products.product.PopulationAcquireProtocol

- Surface: ccf.products.product.PopulationAcquireProtocol
- Public surface: true
- Change type: added
- Before: absent.
- After: the paved road's population phase, `__call__(context)`, declared to `open_product` as `population`.
- Why: SEC-020 Q7.
- Migration: none; additive.

## ccf.products.product.PopulationAcquisitionContext

- Surface: ccf.products.product.PopulationAcquisitionContext
- Public surface: true
- Change type: added
- Before: absent.
- After: what the paved population phase is handed: the `PopulationQuestion`, the perspective, the tenant, the declared sources and the question's instant; no request.
- Why: SEC-020 Q7.
- Migration: none; additive.

## ccf.products.product.open_product

- Surface: ccf.products.product.open_product
- Public surface: true
- Change type: reshaped
- Before: no population phase parameter.
- After: adds the optional `population` (the population phase), refused at open when it shares an owner with `acquire`; every question's fabric is booted `for_question`.
- Why: SEC-020 Q7 and Q9.
- Migration: none.

## ccf.products.product.OpenedProduct

- Surface: ccf.products.product.OpenedProduct
- Public surface: true
- Change type: reshaped
- Before: no population phase.
- After: adds `population`; `build_arguments` states `population_acquisition` when one is declared.
- Why: SEC-020 Q7.
- Migration: none.

## ccf.deployment.manifest.QuestionFabricNotFresh

- Surface: ccf.deployment.manifest.QuestionFabricNotFresh
- Public surface: true
- Change type: added
- Before: absent.
- After: a `ValueError` raised before anything is registered or booted when a fabric booted for a question names no path, or a path that already exists.
- Why: SEC-020 Q9.
- Migration: none; additive.

## ccf.deployment.QuestionFabricNotFresh

- Surface: ccf.deployment.QuestionFabricNotFresh
- Public surface: true
- Change type: added
- Before: absent.
- After: the package-level spelling of `ccf.deployment.manifest.QuestionFabricNotFresh`.
- Why: SEC-020 Q9.
- Migration: none; additive.

## ccf.deployment.manifest.BootedFabric

- Surface: ccf.deployment.manifest.BootedFabric
- Public surface: true
- Change type: reshaped
- Before: no question-fabric declaration.
- After: adds `for_question: bool = False`.
- Why: SEC-020 Q9.
- Migration: none; the default is the fabric that outlives its questions.

## ccf.deployment.BootedFabric

- Surface: ccf.deployment.BootedFabric
- Public surface: true
- Change type: reshaped
- Before: no question-fabric declaration.
- After: the package-level spelling of the same change.
- Why: SEC-020 Q9.
- Migration: none.

## ccf.deployment.manifest.load_and_boot

- Surface: ccf.deployment.manifest.load_and_boot
- Public surface: true
- Change type: reshaped
- Before: no question-fabric option.
- After: adds `for_question: bool = False`; when set, the substrate is verified fresh first.
- Why: SEC-020 Q9.
- Migration: none; the default is unchanged.

## ccf.deployment.load_and_boot

- Surface: ccf.deployment.load_and_boot
- Public surface: true
- Change type: reshaped
- Before: no question-fabric option.
- After: the package-level spelling of the same change.
- Why: SEC-020 Q9.
- Migration: none.

## ccf.deployment.config.load_config_and_boot

- Surface: ccf.deployment.config.load_config_and_boot
- Public surface: true
- Change type: reshaped
- Before: no question-fabric option.
- After: adds `for_question: bool = False`, as `load_and_boot`.
- Why: SEC-020 Q9.
- Migration: none; the default is unchanged.

## ccf.deployment.load_config_and_boot

- Surface: ccf.deployment.load_config_and_boot
- Public surface: true
- Change type: reshaped
- Before: no question-fabric option.
- After: the package-level spelling of the same change.
- Why: SEC-020 Q9.
- Migration: none.

## ccf.projection.engine.ExecutionResult

- Surface: ccf.projection.engine.ExecutionResult
- Public surface: true
- Change type: reshaped
- Before: no record of the seeds an execution was asked to use.
- After: adds `seeds: frozenset[str] | None = None`, hash-transparent at `None`.
- Why: SEC-020 Q10: the decision record keeps the seed the one computation used.
- Migration: none.

## ccf.replay.record.ContentGenerationPath

- Surface: ccf.replay.record.ContentGenerationPath
- Public surface: true
- Change type: reshaped
- Before: replay seeded every walk with its recorded question's subject.
- After: adds `executed_seeds: tuple[str, ...] | None = None`, hash-transparent at `None`, recorded only when the walk did not start at the question's own subject (the early decision's stand-in); replay re-executes from it. Records written before the member existed, and every record whose walk started at its own subject, keep their content addresses (measured: three records written by the base source replayed to their own addresses).
- Why: SEC-020 Q10.
- Migration: none.

## ccf.products.resolver.AcquisitionSeamProtocol

- Surface: ccf.products.resolver.AcquisitionSeamProtocol
- Public surface: true
- Change type: behavior
- Before: documented as invoked exactly once per question, with the effective request.
- After: still once per question; a declared population phase is the second declared phase, also once, immediately before it and without the subject; under the early decision the request it receives carries the declared undisclosed subject in place of the caller's.
- Why: SEC-020 Q7 and Q10 (the "exactly once" rule as Dave ruled it).
- Migration: none.
