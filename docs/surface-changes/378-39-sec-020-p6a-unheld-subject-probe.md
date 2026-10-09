# 378-39 — SEC-020 ruling P6 (a): a population read left in the subject-keyed phase is refused, decided by a probe asked before the subject

`D-IMPL-378`, Dave's ruling of 2026-10-08 16:40 MST, item 2, verbatim: *"P6: (a), conditional implementation GO.
Amend Q10 to permit the probe. Extend CT-A with the working declared-population twin. Do not declare closure based on
this probe alone: prove it runs before real-subject acquisition, and retain the counterexample where a source treats
the probe identifier differently. Verify that the fixed identifier is actually absent; do not assume it."* Lane
`378f-p6a`, built from lane `378e-p6`'s proposal. **SEC-020 stays OPEN.** The probe is not closure: a source that
recognizes the probe identifier is not detected.

**What the tests measure, on test fixtures.**
`tests/products/test_sec020_p6_population_read_in_subject_keyed_phase.py`: a class that may withhold and declares no
early policy, whose subject-keyed acquisition acquires the same content whatever is asked, is refused by name on every
question, the withheld subject's and an identifier nothing holds alike, and the subject-keyed phase is never handed
either asked identifier, on the paved road and on the low road (red before the change: the configuration was
answered). The order is logged, not inferred: the subject-keyed phase is handed the probe identifier and the fabric
is read again strictly before the phase is handed the question's subject, and a refused question never hands the
phase the question's subject. The same read declared as the population phase, a source keyed on the subject, the
same read under a declared early policy and under a class affirming `never` are still answered.
`tests/products/test_sec020_p6_unheld_subject_probe_is_verified_absent.py`: that the probe identifier names nothing is
checked, not assumed — a fabric naming it (an entity, or a relationship end) before the question, and a source
holding it, are each refused by name, `UnheldSubjectProbeIsHeld`, before the phase is handed the question's subject
(red before the check: the first two were answered and the third was refused as a population read).

**What it changes for a deployment.** Every question of a class that may withhold and declares no early policy calls
the subject-keyed phase twice: once with the probe identifier, then once for the question's subject (Q10 amended to
exactly that call). A subject-keyed acquisition that returns content for an identifier it does not hold (a constant
or population-shaped fixture, or a read keyed on a parameter rather than on the subject) is refused unless its class
affirms `never` or declares an early policy, or the read moves to the declared population phase.

## ccf.products.resolver.PopulationReadInSubjectKeyedPhase

- Surface: ccf.products.resolver.PopulationReadInSubjectKeyedPhase
- Public surface: true
- Change type: added
- Before: absent; a population read left in the subject-keyed phase ran, and a subject withheld inside the projection was rendered over a fabric a nonexistent subject's question is not answered over.
- After: an `UnsupportedComposition` raised by `GovernedResolver.__call__`, before the subject-keyed phase is asked about the question's subject, when asking that phase about `UNHELD_SUBJECT_PROBE` changed the fabric, for a class that may withhold and declares no early policy.
- Why: SEC-020, ruling P6 (a) (`D-IMPL-378`, 2026-10-08 16:40 MST): the refusal is decided by the phase's answer for an identifier that names nothing, never by the asked subject, so it is the same for a withheld subject and a nonexistent one. Not closure: a source that recognizes the probe is not detected.
- Migration: declare a subject-independent read as the population phase (`open_product(population=...)` or `GovernedResolver(population_acquisition=...)`), declare an early policy, or affirm `subject_withholding: never` when the projection never withholds.

## ccf.products.resolver.UnheldSubjectProbeIsHeld

- Surface: ccf.products.resolver.UnheldSubjectProbeIsHeld
- Public surface: true
- Change type: added
- Before: absent; nothing checked that the identifier the P6 probe asks about names nothing.
- After: an `UnsupportedComposition` raised by `GovernedResolver.__call__`, for a class the P6 probe reads, when the fabric as read before the probe names `UNHELD_SUBJECT_PROBE` (an entity whose URI it is, or a relationship with it at either end; the subject-keyed phase is then asked nothing), or when the fabric as read after the probe does; before the phase is handed the question's subject, with one message whatever subject was asked.
- Why: SEC-020, ruling P6 (a), Dave's condition "Verify that the fixed identifier is actually absent; do not assume it." Fail closed: a probe identifier that names something cannot show what the phase acquires for an identifier its sources do not hold.
- Migration: nothing in a deployment may be named by `UNHELD_SUBJECT_PROBE`. L2's ingest never mints it (every node it writes is `<entity_class>://<content hash>`); only the admission path for an already-resolved claim, or a store written outside this SDK, can.

## ccf.products.resolver.UNHELD_SUBJECT_PROBE

- Surface: ccf.products.resolver.UNHELD_SUBJECT_PROBE
- Public surface: true
- Change type: added
- Before: absent.
- After: `"ccf-sdk:unheld-subject-probe"`, the identifier the subject-keyed phase is asked about first, inside `SUBJECT_FLOOR_V1`; a deployment's source sees it as an identifier it does not hold.
- Why: SEC-020, ruling P6 (a) (see above).
- Migration: none; a source must treat it as any identifier it does not hold.

## ccf.products.resolver.GovernedResolver

- Surface: ccf.products.resolver.GovernedResolver
- Public surface: true
- Change type: behavior
- Before: the declared subject-keyed acquisition seam was called once per question, with the question's effective request.
- After: for a class that may withhold and declares no early policy, the seam is first called with the effective request carrying `UNHELD_SUBJECT_PROBE` as its subject, the fabric is read once more, and the question is refused with `PopulationReadInSubjectKeyedPhase` if that read differs; otherwise the question proceeds as before. A fabric that names the probe identifier, before or after that call, is refused with `UnheldSubjectProbeIsHeld` instead. A class affirming `never`, or declaring an early policy, is not probed.
- Why: SEC-020, ruling P6 (a) (see above); Q10 amended to exactly this one extra call.
- Migration: as above.

## ccf.products.resolver.AcquisitionSeamProtocol

- Surface: ccf.products.resolver.AcquisitionSeamProtocol
- Public surface: true
- Change type: behavior
- Before: invoked once per question.
- After: for a class that may withhold and declares no early policy, also invoked once with `UNHELD_SUBJECT_PROBE` in place of the subject, immediately before its call for the question's subject.
- Why: SEC-020, ruling P6 (a) (see above).
- Migration: none for a seam keyed on the subject; a seam that counts its calls sees one more.

## ccf.products.resolver.PopulationAcquisitionSeamProtocol

- Surface: ccf.products.resolver.PopulationAcquisitionSeamProtocol
- Public surface: true
- Change type: behavior
- Before: said the subject-keyed phase's obligation to acquire nothing for an identifier its source does not hold stays a trusted statement.
- After: says that obligation is checked by the probe for a class that may withhold and declares no early policy, that the check does not detect a source recognizing the probe, and that for that source and any other class it stays a trusted statement. The population phase itself is still invoked once per question, first.
- Why: SEC-020, ruling P6 (a) (see above).
- Migration: none.

## ccf.products.product.AcquireProtocol

- Surface: ccf.products.product.AcquireProtocol
- Public surface: true
- Change type: behavior
- Before: the paved road called the deployment's `acquire` once per question, for the question's subject.
- After: for a class that may withhold and declares no early policy, the paved road first calls `acquire` with a context whose request carries `UNHELD_SUBJECT_PROBE` as its subject; what it returns is ingested, and if it changed the fabric the question is refused with `PopulationReadInSubjectKeyedPhase` before `acquire` is handed the question's subject.
- Why: SEC-020, ruling P6 (a) (see above).
- Migration: return nothing for an identifier the sources do not hold; read what does not depend on the subject in `population` (`PopulationAcquireProtocol`).
