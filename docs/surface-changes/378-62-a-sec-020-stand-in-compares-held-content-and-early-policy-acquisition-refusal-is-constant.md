# 378-62-a — SEC-020 repair 1.3: the stand-in check compares what was acquired, delivery lineage set aside; repair 2.2 (a): under an early policy, an acquisition refusal is one constant SDK refusal

`D-IMPL-378`, Dave's repair batch of 2026-10-09 10:54 MST (sent again unchanged at 10:58). Repair 1.3, verbatim:
*"Compare entities, relationships and claim values, excluding delivery lineage. Preserve security-relevant differences
and the existing held-stand-in controls."* Decision 2.2 (a), verbatim: *"Replace acquisition-refusal free text under
early withholding with constant SDK text in responses and records. Verify that neither the stand-in identifier nor
another distinguishing value survives."* Lane `378j-resolver`. Both apply only to a class with a declared early policy.
**SEC-020 stays OPEN.**

**What the tests measure, on test fixtures.**
`tests/products/test_sec020_stand_in_delivery_lineage.py`: under an early policy, a population read whose deliveries
differ only in delivery lineage — a fresh envelope id per delivery, or each delivery's own receipt instant on the low
road — is answered, and the withheld and nonexistent answers are judged no different by SEC-020's closing test's own
rules at every door (red before: every question was refused, `UndisclosedSubjectSubstituteIsHeld`, the stand-in held
nowhere); an adapter whose envelope ids name what it was asked is answered, and no envelope id reaches an answer or any
artifact in the deployment's store. A claim value naming the stand-in, a relationship naming it at an end or in its
attributes, and a lineage entry whose source or passage anchor names it still refuse every question alike, by name,
nothing recorded (green before and after). The check after acquisition refuses only a question whose own acquisition
wrote the stand-in.
`tests/products/test_sec020_early_policy_acquisition_refusal.py`: under an early policy, for six ways a subject-keyed
source refuses an identifier it does not hold — its text or its `error_code` naming what it was asked, an envelope the
raiser built, the SDK-declared `IdentityRefused` whose message names it, a source answering the stand-in with another
cause or another refusal kind — and for a refusal shell its raiser says it recorded, every side's served and recorded
refusal is `EARLY_POLICY_ACQUISITION_REFUSAL`, recorded at the `acquisition` seam; the withheld and nonexistent
refusals differ, in process, only at the hash of each caller's own question, the closing test's own rules find no other
difference at any door, and the stand-in's identifier is in neither the answer nor the record (red before: the stand-in's identifier was in the withheld subject's text, code and
record, and the cause, the kind and at the HTTP door the status differed). A declared population phase keeps its own
refusal text, and a class affirming `never` keeps its source's refusal.

**What it changes for a deployment.** A class with a declared early policy and an adapter that gives each delivery
its own envelope id, or each delivery its own receipt instant, is answered instead of refused on every question. A
refusal its subject-keyed acquisition raises, for any question of the class, now reaches the caller and the record as
one constant: kind `subject-unavailable`, cause `undisclosed`, no code, one SDK sentence, and the HTTP door's status for
that kind; neither the answer nor the record keeps the source's own kind, cause, code or text.

## ccf.products.resolver.EARLY_POLICY_ACQUISITION_REFUSAL

- Surface: ccf.products.resolver.EARLY_POLICY_ACQUISITION_REFUSAL
- Public surface: true
- Change type: added
- Before: absent; under a declared early policy a refusal the subject-keyed acquisition raised was served and recorded as its source stated it, its text and code carrying the stand-in's identifier for a withheld subject.
- After: a `SubjectUnavailableRefusal` constant (cause `undisclosed`, no code, one SDK sentence) that every refusal the subject-keyed acquisition raises becomes, served and recorded, for every question of a class with a declared early policy.
- Why: SEC-020, decision 2.2 (a) (`D-IMPL-378`, 2026-10-09): neither the stand-in's identifier nor a value a source chose by what it was asked may survive in the answer or the record.
- Migration: none to declare; read the constant to recognize such a refusal.

## ccf.products.resolver.GovernedResolver

- Surface: ccf.products.resolver.GovernedResolver
- Public surface: true
- Change type: behavior
- Before: for a class with a declared early policy, the stand-in check compared the graph read after the stand-in's call with the one after the probe's call whole, lineage included; a refusal the subject-keyed acquisition raised was recorded and served as its source stated it.
- After: the check compares entities, relationships and claim values, with each lineage entry's source and passage anchor, and sets aside the envelope id and receipt instant a delivery carries; a refusal the subject-keyed acquisition raises (a `GovernedRefusalRaised` of any kind, an envelope recorded by its raiser or not, or a class- or SDK-declared seam refusal) is recorded at the `acquisition` seam and served as `EARLY_POLICY_ACQUISITION_REFUSAL`.
- Why: SEC-020, repair 1.3 and decision 2.2 (a) (see above).
- Migration: none for a class with no early policy.

## ccf.products.resolver.UndisclosedSubjectSubstituteIsHeld

- Surface: ccf.products.resolver.UndisclosedSubjectSubstituteIsHeld
- Public surface: true
- Change type: behavior
- Before: raised when the graph after the stand-in's call differed in any way from the graph after the probe's call, a lineage entry that differed only in its envelope id included.
- After: raised when they differ in entities, relationships, claim values, or a lineage entry's source or passage anchor; a difference only in the envelope id or the receipt instant a delivery carries is not one. Its type and its one message are unchanged.
- Why: SEC-020, repair 1.3 (see above).
- Migration: none.

## ccf.products.refusal.SubjectUnavailableRefusal

- Surface: ccf.products.refusal.SubjectUnavailableRefusal
- Public surface: true
- Change type: behavior
- Before: said the cause `undisclosed` is never a determination the fabric reaches, and that the record keeps what the fabric determined.
- After: says the fabric records `undisclosed` as a determination in one place, `EARLY_POLICY_ACQUISITION_REFUSAL`, where under a declared early policy the record keeps no statement of the source's.
- Why: SEC-020, decision 2.2 (a) (see above).
- Migration: none.

## ccf.products.product.AcquireProtocol

- Surface: ccf.products.product.AcquireProtocol
- Public surface: true
- Change type: behavior
- Before: under a declared early policy, the question was refused if what `acquire` returned for the stand-in added anything to what it returned for the probe identifier; a refusal `acquire` raised reached the caller and the record as it stated it.
- After: "anything" is an entity, a relationship, a claim value, or evidence from another source or passage; the envelope id and receipt instant each delivery carries are set aside. Under such a policy a refusal `acquire` raises is served and recorded as `EARLY_POLICY_ACQUISITION_REFUSAL`.
- Why: SEC-020, repair 1.3 and decision 2.2 (a) (see above).
- Migration: none; an `acquire` relying on its refusal's own text, code, cause or kind reaching the caller under an early policy no longer gets it.

## ccf.products.subject_disclosure.SubjectDisclosurePolicy

- Surface: ccf.products.subject_disclosure.SubjectDisclosurePolicy
- Public surface: true
- Change type: behavior
- Before: the module's account of the early policy did not say what becomes of a refusal the subject-keyed acquisition raises.
- After: it says such a refusal is served and recorded as `EARLY_POLICY_ACQUISITION_REFUSAL` for every question of a class with the policy.
- Why: SEC-020, decision 2.2 (a) (see above).
- Migration: none.
