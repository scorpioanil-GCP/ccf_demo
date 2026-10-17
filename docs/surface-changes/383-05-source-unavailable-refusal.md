# 383-05 (D-IMPL-383, 2026-10-16) — a declared source outage is refused as itself

`D-IMPL-383`, closing `CP06C-F-06`. Dave, 2026-10-16 12:11 MST, choosing option B
of three: add an honest "source unavailable" refusal to the SDK, then have cp-06C declare it.

Before this, the only refusal a class's declared seam exception (`D-IMPL-347` B2) could mint was
`subject-unavailable`, whose one external sentence — *"the requested subject is not available to this
principal under this product"* — is false for an outage and reads as a missing entitlement.

## ccf.products.refusal.SourceUnavailableRefusal

- Surface: ccf.products.refusal.SourceUnavailableRefusal
- Public surface: true
- Change type: added
- Before: no such kind; a declared outage could only be refused as `subject-unavailable`.
- After: refusal kind `source-unavailable` with `detail` (the exception's own message) and `error_code` (the class's declared code). Registered in `REFUSAL_KINDS` and the pre-assembly set; its external sentence says a source could not be reached and to ask again later; `detail` is withheld below `full` because a driver's message can name hosts and ports; HTTP status 409 (fulfillment withheld), never a 5xx (`D-IMPL-253` Q18). Under a declared early policy it is still recorded as the one constant `subject-unavailable` (SEC-020).
- Why: `CP06C-F-06`. Red test: `tests/examples/test_cp_06_canonical_evidence_dir.py::test_an_unreachable_source_is_a_recorded_source_unavailable_refusal` raises `psycopg.OperationalError` with the declaration removed; `tests/products/test_source_unavailable_refusal.py` does not import on `a06b66fc`.
- Migration: none; nothing mints it unless a class declares `cause: source-unavailable`.

## ccf.products.contract.SeamRefusalCause

- Surface: ccf.products.contract.SeamRefusalCause
- Public surface: true
- Change type: added
- Before: a seam binding's cause was typed `RefusalCause` (the three subject causes).
- After: `RefusalCause | Literal["source-unavailable"]`. `RefusalCause` itself is unchanged, so a `SubjectUnavailableRefusal` can never carry the new value.
- Why: `CP06C-F-06`.
- Migration: none.

## ccf.controlplane.artifacts.SeamRefusalBinding

- Surface: ccf.controlplane.artifacts.SeamRefusalBinding
- Public surface: true
- Change type: reshaped
- Before: `cause: RefusalCause`; every binding minted `subject-unavailable`.
- After: `cause: SeamRefusalCause`; `source-unavailable` mints a `SourceUnavailableRefusal`, every other cause mints `subject-unavailable` exactly as before. Matching is unchanged: exact `module.QualName`, never imported, never a subclass.
- Why: `CP06C-F-06`.
- Migration: none; every existing binding's cause is still valid and hashes as before.
