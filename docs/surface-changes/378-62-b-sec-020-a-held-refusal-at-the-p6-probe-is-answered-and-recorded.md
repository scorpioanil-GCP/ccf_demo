# 378-62-b — SEC-020 repair 2.3 (b): a held refusal at the P6 probe is answered and recorded as one constant SDK refusal

`D-IMPL-378`, Dave's repair batch of 2026-10-09 10:54 MST (sent again unchanged at 10:58). Decision 2.3, verbatim:
*"Use (d) only if “unknown identifier” has a typed, stable cause. Do not infer it from message text. Otherwise implement
(b) with a recorded constant SDK cause. Role and parameter refusals must retain their decision records."* The condition
for (d) was measured not met: a source's refusal of an identifier it does not hold reaches the probe with no typed cause
as a refusal shell (its cause a string in `fields`) or an assembler's refusal (a deployment's own reason), and the SDK
declares the typed `nonexistent` for `TemporalWriteRefused`, which is not about the identifier. So (b). Lane
`378j-resolver`. It applies to a class ruling P6 (a)'s probe reads: one that may withhold its subject and declares no
early policy. **SEC-020 stays OPEN.**

**What the tests measure, on test fixtures.**
`tests/products/test_sec020_held_refusal_at_the_probe_is_recorded.py`: a refusal the source decides by the question's
role, and one it decides by a parameter (the "i" panel's F-G1-2 probe), each answer the question at the probe as
`UNHELD_SUBJECT_PROBE_REFUSAL` with exactly one decision record, at the `acquisition` seam beside the caller's question
(red before: `UnheldSubjectProbeRefused` raised, no record); and for every route a held refusal takes to the probe — a
`subject-unavailable` refusal of each cause, a request violation, an assembler's refusal, a refusal shell recorded by its
raiser or not, a class-declared and the SDK-declared seam refusal — the withheld subject's, two nonexistent subjects'
and a served subject's question each get the constant, one record each, the withheld and nonexistent refusals differing
only at the hash of each caller's own question, and the source's own text, code and cause in no served or record byte;
judged by SEC-020's closing test's own rules at every door, no difference. The phase is handed the probe identifier and
never the asked subject. `tests/products/test_sec020_held_refusal_at_the_probe.py`, migrated by behavior: the same
sides on the paved road and the low road, each answered and recorded as the constant.

**What it changes for a deployment.** For a class the probe reads, a subject-keyed acquisition that answers the probe
identifier with a held refusal now refuses every question with one recorded refusal — kind `subject-unavailable`,
cause `undisclosed`, no code, one SDK sentence, the HTTP door's status for that kind — instead of the raised
`UnheldSubjectProbeRefused` a door answered with its opaque failure. A question your source refuses for a reason of the
question itself keeps its decision record; neither the answer nor the record keeps the source's own kind, cause, code or
text.

## ccf.products.resolver.UNHELD_SUBJECT_PROBE_REFUSAL

- Surface: ccf.products.resolver.UNHELD_SUBJECT_PROBE_REFUSAL
- Public surface: true
- Change type: added
- Before: absent; a held refusal at the P6 probe raised `UnheldSubjectProbeRefused` and recorded nothing.
- After: a `SubjectUnavailableRefusal` constant (cause `undisclosed`, no code, one SDK sentence) every question of a class the probe reads is answered and recorded with when the probe call itself ends in a held refusal, on any route.
- Why: SEC-020, decision 2.3 (b) (`D-IMPL-378`, 2026-10-09): role and parameter refusals keep their decision records, with a constant SDK cause. Its own constant rather than `EARLY_POLICY_ACQUISITION_REFUSAL`, whose sentence says the class declares an early policy.
- Migration: none to declare; read the constant to recognize such a refusal.

## ccf.products.resolver.UnheldSubjectProbeRefused

- Surface: ccf.products.resolver.UnheldSubjectProbeRefused
- Public surface: true
- Change type: removed
- Before: an `UnsupportedComposition` raised for every question of a class the probe reads when the probe call ended in a held refusal, recording nothing.
- After: absent; the SDK raises it nowhere, and such a question is answered and recorded as `UNHELD_SUBJECT_PROBE_REFUSAL`.
- Why: SEC-020, decision 2.3 (b) (see above). A public exception the SDK never raises would invite `except` clauses that never fire; it was added in this same unmerged batch (fragment 378-48).
- Migration: catch nothing; recognize the returned refusal by `UNHELD_SUBJECT_PROBE_REFUSAL`'s sentence, or by its record at the `acquisition` seam.

## ccf.products.resolver.GovernedResolver

- Surface: ccf.products.resolver.GovernedResolver
- Public surface: true
- Change type: behavior
- Before: for a class the probe reads, a held refusal from the probe call raised `UnheldSubjectProbeRefused`, recording nothing.
- After: such a question is recorded at the `acquisition` seam, before the subject-keyed phase is handed its subject, and answered with `UNHELD_SUBJECT_PROBE_REFUSAL`, for every route a held refusal takes (the typed handoff of any refusal kind, a refusal shell recorded by its raiser or not, a class- or SDK-declared seam refusal). A raiser stating `ResolutionNotApplicable` is refused as before.
- Why: SEC-020, decision 2.3 (b) (see above).
- Migration: none for a class with an early policy or one affirming `never`.

## ccf.products.resolver.PopulationReadInSubjectKeyedPhase

- Surface: ccf.products.resolver.PopulationReadInSubjectKeyedPhase
- Public surface: true
- Change type: behavior
- Before: said a held refusal from the probe refuses the question by its own name, `UnheldSubjectProbeRefused`.
- After: says such a question is answered and recorded as `UNHELD_SUBJECT_PROBE_REFUSAL`. The refusal this type names is unchanged.
- Why: SEC-020, decision 2.3 (b) (see above).
- Migration: none.

## ccf.products.resolver.AcquisitionSeamProtocol

- Surface: ccf.products.resolver.AcquisitionSeamProtocol
- Public surface: true
- Change type: behavior
- Before: said the probe's call ending in a held refusal refuses the question as `UnheldSubjectProbeRefused`.
- After: says such a question is answered and recorded as `UNHELD_SUBJECT_PROBE_REFUSAL`. The calls the seam receives are unchanged.
- Why: SEC-020, decision 2.3 (b) (see above).
- Migration: none.

## ccf.products.product.AcquireProtocol

- Surface: ccf.products.product.AcquireProtocol
- Public surface: true
- Change type: behavior
- Before: said a held refusal for the probe identifier refuses every question, `UnheldSubjectProbeRefused`.
- After: says such a question is answered and recorded as `UNHELD_SUBJECT_PROBE_REFUSAL`, with no part of the refusal as `acquire` stated it.
- Why: SEC-020, decision 2.3 (b) (see above).
- Migration: none; an `acquire` relying on its own refusal of the probe identifier reaching the caller no longer gets it.

## ccf.products.refusal.SubjectUnavailableRefusal

- Surface: ccf.products.refusal.SubjectUnavailableRefusal
- Public surface: true
- Change type: behavior
- Before: named one place the cause `undisclosed` is recorded as a determination, `EARLY_POLICY_ACQUISITION_REFUSAL`.
- After: names two, adding `UNHELD_SUBJECT_PROBE_REFUSAL`.
- Why: SEC-020, decision 2.3 (b) (see above).
- Migration: none.
