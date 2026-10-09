# 378-48 — SEC-020 decision 4 (a): the early-withholding stand-in is verified to name nothing; OWED-RULINGS-3 item 4 (b): a held refusal at the P6 probe refuses the question

`D-IMPL-378`, Dave's rulings of 2026-10-09. Decision 4, 06:06 MST, confirmed at 06:21 MST ("4a"), verbatim: *"(a).
Verify the stand-in is absent before and after acquisition. A failed check refuses without exposing
subject-dependent differences."* OWED-RULINGS-3 item 4, 06:21 MST, verbatim: *"4(b), plus the closing-test case and a
supported working twin"*; option (b), verbatim: *"Refuse when the probe call itself returns a held refusal (refuses
every question to a source that refuses unknown identifiers)."* Lane `378i-probe`. **SEC-020 stays OPEN.**

**What the tests measure, on test fixtures.**
`tests/products/test_sec020_stand_in_is_verified_absent.py`: an early-withholding deployment whose stand-in names
something — its source holds the stand-in under the stand-in's own URI or under another, or a declared population
phase writes it — refuses every question by name, `UndisclosedSubjectSubstituteIsHeld`, alike for the withheld subject,
two identifiers nothing holds and a served subject, with one message, recording nothing and never handing the
subject-keyed phase the asked subject; a fabric naming the stand-in after the question's own acquisition, and a
preloaded fabric naming it with no acquisition at all, are refused the same way; and the final panel's probe, judged by
the closing test's own rules at every door, finds the withheld and nonexistent answers no different (red before the
change: the questions were answered, and told apart at the empty finding and the debt under `from_decision`, by the
refusal kind under `from_entity_freshness`). The stand-in held nowhere, and an early policy over a read that acquires
the same content whatever is asked, are still answered.
`tests/products/test_sec020_held_refusal_at_the_probe.py`: a class the P6 probe reads, whose subject-keyed acquisition
answers an identifier it does not hold with a held refusal (`GovernedRefusalRaised`, or the SDK-declared
`IdentityRefused`), refuses every question by name, `UnheldSubjectProbeRefused`, alike for a withheld, a nonexistent
and a served subject, on the paved road and the low road, recording nothing, the phase handed the probe identifier and
never the asked subject (red before the change: the withheld subject was answered while an identifier nothing holds
was refused as data). The supported working twin, a class affirming `never`, and an early policy over the refusing
source are still answered. SEC-020's closing test holds the refusal as CT-A (a): every side refused alike and the twin
(its `subject_keyed` world) answering indistinguishably.

**What it changes for a deployment.** A class with a declared early policy and a subject-keyed acquisition: every
question first asks the acquisition about `UNHELD_SUBJECT_PROBE` and then about the stand-in (Q10 amended to exactly
these two calls; measured on the paved road's test fixture, three calls and five graph reads per question against one
and three for a class affirming `never`), and a stand-in your sources hold, or the graph names, refuses every
question. A class that may withhold and declares no early policy: a subject-keyed acquisition answering an identifier
it does not hold with a held refusal refuses every question, including a question the source refuses for a reason of
the question itself (an intent, a parameter, a role), which was refused as data with its record before and now raises
the refusal and records nothing.

## ccf.products.resolver.UndisclosedSubjectSubstituteIsHeld

- Surface: ccf.products.resolver.UndisclosedSubjectSubstituteIsHeld
- Public surface: true
- Change type: added
- Before: absent; the stand-in a declared early policy asks in place of an undisclosed subject was held only to `SUBJECT_FLOOR_V1`, and a source holding it told a withheld subject from a nonexistent one.
- After: an `UnsupportedComposition` raised by `GovernedResolver.__call__`, for every question of a class with a declared early policy, when the graph read before the subject-keyed acquisition names the stand-in, when that acquisition acquires for the stand-in what it does not acquire for `UNHELD_SUBJECT_PROBE`, or when the graph the plan reads names it; with one message whatever was asked and whichever check failed.
- Why: SEC-020, decision 4 (a) (`D-IMPL-378`, 2026-10-09): the checks read nothing about the asked subject, so the refusal is the same for a withheld subject and a nonexistent one. Not detected: a source that recognizes the stand-in and answers nothing for it, and what a composite's children's sources hold for it.
- Migration: declare a stand-in that no source, child or fabric of the deployment holds.

## ccf.products.resolver.UnheldSubjectProbeRefused

- Surface: ccf.products.resolver.UnheldSubjectProbeRefused
- Public surface: true
- Change type: added
- Before: absent; a held refusal from the P6 probe call counted as "acquired nothing", and a source refusing an identifier it does not hold told a withheld subject from a nonexistent one.
- After: an `UnsupportedComposition` raised by `GovernedResolver.__call__`, for a class the P6 probe reads, when the probe call ends in a held refusal (`GovernedRefusalRaised`, or a type the class or the SDK declares at the seam), before the subject-keyed phase is handed the question's subject, with one message whatever subject was asked.
- Why: SEC-020, OWED-RULINGS-3 item 4 (b) (`D-IMPL-378`, 2026-10-09): refuse every question to a source that refuses unknown identifiers.
- Migration: answer an identifier the sources do not hold with nothing; or declare an early policy; or affirm `subject_withholding: never` when the projection never withholds.

## ccf.products.resolver.GovernedResolver

- Surface: ccf.products.resolver.GovernedResolver
- Public surface: true
- Change type: behavior
- Before: a class with a declared early policy asked its subject-keyed acquisition once per question; a held refusal from the P6 probe call was ignored.
- After: for a class with a declared early policy, before the subject-keyed acquisition is handed the question, the graph is checked not to name the stand-in, the acquisition is asked about `UNHELD_SUBJECT_PROBE` and then the stand-in with one graph read after each, and the graph the plan reads is checked not to name the stand-in; a failed check raises `UndisclosedSubjectSubstituteIsHeld`. For a class the P6 probe reads, a held refusal from the probe call raises `UnheldSubjectProbeRefused`.
- Why: SEC-020, decision 4 (a) and OWED-RULINGS-3 item 4 (b) (see above).
- Migration: as above.

## ccf.products.resolver.AcquisitionSeamProtocol

- Surface: ccf.products.resolver.AcquisitionSeamProtocol
- Public surface: true
- Change type: behavior
- Before: invoked once per question, and once more with `UNHELD_SUBJECT_PROBE` for a class the P6 probe reads.
- After: also invoked twice more per question for a class with a declared early policy, with `UNHELD_SUBJECT_PROBE` and then the declared stand-in in place of the subject, immediately before its call for the question; and a held refusal from the P6 probe's call refuses the question.
- Why: SEC-020, decision 4 (a) and OWED-RULINGS-3 item 4 (b) (see above).
- Migration: none for a seam that holds no record for the stand-in and answers an unheld identifier with nothing; a seam that counts its calls sees two more under an early policy.

## ccf.products.resolver.PopulationAcquisitionSeamProtocol

- Surface: ccf.products.resolver.PopulationAcquisitionSeamProtocol
- Public surface: true
- Change type: behavior
- Before: said the subject-keyed phase's obligation is checked by the P6 probe only, and stays a trusted statement for any other class.
- After: says that for a class with a declared early policy, what the subject-keyed phase acquires for the stand-in is compared with what it acquires for `UNHELD_SUBJECT_PROBE`, and that neither check detects a source recognizing the identifier it is asked about. The population phase itself is still invoked once per question, first.
- Why: SEC-020, decision 4 (a) (see above).
- Migration: none.

## ccf.products.resolver.PopulationReadInSubjectKeyedPhase

- Surface: ccf.products.resolver.PopulationReadInSubjectKeyedPhase
- Public surface: true
- Change type: behavior
- Before: said a held refusal from the probe acquires nothing, and that a class with a declared early policy is not probed.
- After: says a held refusal from the probe refuses the question by its own name (`UnheldSubjectProbeRefused`), and that a class with a declared early policy is not refused by this probe but has its stand-in verified, with `UNHELD_SUBJECT_PROBE` as the baseline.
- Why: SEC-020, decision 4 (a) and OWED-RULINGS-3 item 4 (b) (see above).
- Migration: none.

## ccf.products.resolver.UNHELD_SUBJECT_PROBE

- Surface: ccf.products.resolver.UNHELD_SUBJECT_PROBE
- Public surface: true
- Change type: behavior
- Before: the identifier the P6 probe asks about, for a class that may withhold and declares no early policy.
- After: also the baseline a declared early policy's stand-in is compared with: the subject-keyed acquisition is asked about it, and then about the stand-in, for every question of such a class.
- Why: SEC-020, decision 4 (a) (see above).
- Migration: none; a source must treat it as any identifier it does not hold.

## ccf.products.product.AcquireProtocol

- Surface: ccf.products.product.AcquireProtocol
- Public surface: true
- Change type: behavior
- Before: called once more for a class the P6 probe reads; a held refusal for the probe identifier counted as nothing returned.
- After: a held refusal for the probe identifier refuses every question (`UnheldSubjectProbeRefused`); and under a declared early policy `acquire` is called twice more per question, with `UNHELD_SUBJECT_PROBE` and then the declared stand-in, the question refused (`UndisclosedSubjectSubstituteIsHeld`) if the graph names the stand-in or what `acquire` returned for it added anything to what it returned for the probe identifier.
- Why: SEC-020, decision 4 (a) and OWED-RULINGS-3 item 4 (b) (see above).
- Migration: return nothing for an identifier the sources do not hold; hold nothing for the declared stand-in.

## ccf.products.product.PopulationAcquireProtocol

- Surface: ccf.products.product.PopulationAcquireProtocol
- Public surface: true
- Change type: behavior
- Before: said `acquire` is called once for the question's subject, plus once for the P6 probe for a class that may withhold and declares no early policy.
- After: also says that for a class with a declared early policy `acquire` is called twice to verify its stand-in. The population phase itself is unchanged.
- Why: SEC-020, decision 4 (a) (see above).
- Migration: none.

## ccf.products.subject_disclosure.SubjectDisclosurePolicy

- Surface: ccf.products.subject_disclosure.SubjectDisclosurePolicy
- Public surface: true
- Change type: behavior
- Before: `undisclosed_subject` was the deployment's statement that it names nothing, held only to `SUBJECT_FLOOR_V1` and to naming none of the subjects it stands in for.
- After: that statement is checked for every question, not assumed: a fabric or a subject-keyed acquisition phase that names it, or that acquires for it what it does not acquire for an identifier that names nothing, is refused (`UndisclosedSubjectSubstituteIsHeld`).
- Why: SEC-020, decision 4 (a) (see above).
- Migration: declare a stand-in that nothing in the deployment holds.
