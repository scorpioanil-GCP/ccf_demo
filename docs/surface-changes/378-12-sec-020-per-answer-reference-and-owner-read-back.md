# 378-12 — SEC-020 Q11 and Q12: a per-answer replay reference, and owner read-back that is default-deny (PROPOSALS)

`D-IMPL-378`, lane `378b-s020record`, built red-first. Dave's rulings
(2026-10-07, 19:31 MST), verbatim. Q11: *"Amend before approval. Equal public
references must not identify different immutable record contents. Use a
caller-visible reference separate from the internal evidence address, or
another design preserving unique record identity. Test HTTP, MCP, in-memory and
refusal outputs."* Q12: *"(a) Default-deny owner read-back, with an explicit
tenant class allowlist. Reject withholding classes—including affected
composites—and apply the restriction to existing records and every read/replay
path."* **Both are PROPOSALS for Dave's design review, not integrations**: Q11
changes replay-record content and addressing, and Q12 adds a replay-record
member and a keyword to a public Protocol. **SEC-020 stays OPEN.**

**Q11, the answer's replay reference.** Every product answer's record carries
a fresh 256-bit issuance identifier and is filed under its own content
address. Two equal references therefore name byte-identical records, and the
reference a product answer hands out reflects nothing the answer read.
Measured on the in-memory, HTTP and MCP outputs, served and refused, by
`tests/http_api/test_sec020_replay_reference_issuance.py`. It reverses *"same
question, same state, same instant, same record and reference"*: 13 tests that
pin that property are red by design until Dave rules (`D-IMPL-253` amendment 3:
`tests/products/test_delivery_determinism.py`, 5 tests, and
`tests/replay/test_refusal_replay_record.py::test_two_identical_refusals_at_one_instant_are_one_decision`;
`D-IMPL-358` ruling 1:
`tests/products/test_resolver_seam.py::test_step4_two_serves_at_two_instants_are_two_records`;
`D-IMPL-148` Addendum A: `tests/client/conformance`, 3 tests,
`tests/mcp/test_egress_listing.py`, 2 tests, and
`tests/mcp/test_egress_refusal_envelope.py::test_the_mcp_refusal_is_field_identical_to_the_in_process_one`).

**Q12, the record behind the reference.** A product class says whether its
answers may withhold their subject, and every decision record carries what its
class said. A tenant lists the classes whose records their owners may read
back. The governed evidence read hands a product record to its owner only when
the tenant lists the class and the record carries the class's affirmation that
its answers never withhold their subject, or the record read nothing at all.
No record written before this change carries the affirmation, so existing
records stay sealed. Listing a class that does not affirm it is refused where
the resolver is built. A class that affirms it and then withholds is refused at
serve time, before anything is recorded. The MCP Experience door's
`get_replay_record`, which names no address and so cannot be governed, refuses
every call. Read-refusal records, the evidence read's own records, carry no
product class and no read of any subject: they skip the new check as they skip
the grant check, so their owners still read them back (Dave's Q3). Measured by
`tests/http_api/test_sec020_q12_owner_read_back.py` on the HTTP decision,
resolution and artifact routes, the MCP artifact server's blob, presence and
names resources, the MCP Experience door and the `ccf` CLI.

## ccf.replay.record.ContentGenerationPath

- Surface: ccf.replay.record.ContentGenerationPath
- Public surface: true
- Change type: reshaped
- Before: dimension 5 carried nothing unique to one answer and nothing about whether the deciding class's answers may withhold their subject.
- After: adds `issuance: str`, 64 lowercase hex characters or the sentinel `NO_ISSUANCE`, and `subject_withholding: str`, the deciding class's posture (`"may-withhold"` or `"never"`) or the sentinel `UNSTATED_SUBJECT_WITHHOLDING`. Both are hash-transparent at their sentinels, so every record written before them keeps its bytes and its content address.
- Why: PROPOSAL, Dave's Q11 and Q12 (`D-IMPL-378`). The issuance makes each product answer's record unique; the posture is what the governed evidence read requires before an owner reads a record back.
- Migration: none for a reader. A record built for comparison without either value keeps the sentinels and its address.

## ccf.replay.record.NO_ISSUANCE

- Surface: ccf.replay.record.NO_ISSUANCE
- Public surface: true
- Change type: added
- Before: absent.
- After: `"no-issuance"`, the issuance of every record written before the member existed and of every record no product question issued (evidence reads, door-level denials, erasures).
- Why: PROPOSAL, Dave's Q11.
- Migration: none.

## ccf.replay.record.new_issuance

- Surface: ccf.replay.record.new_issuance
- Public surface: true
- Change type: added
- Before: absent.
- After: returns a fresh issuance: 256 bits from the operating system's CSPRNG (`secrets.token_hex(32)`). Called by the governed resolver on the served path and by the reference refusal recorder for a refusal that answers a product question; `build_replay_record` never mints one.
- Why: PROPOSAL, Dave's Q11.
- Migration: none.

## ccf.replay.record.UNSTATED_SUBJECT_WITHHOLDING

- Surface: ccf.replay.record.UNSTATED_SUBJECT_WITHHOLDING
- Public surface: true
- Change type: added
- Before: absent.
- After: `"unstated"`, the posture every record written before `ContentGenerationPath.subject_withholding` existed reads as. The governed evidence read treats it as a class that may withhold.
- Why: PROPOSAL, Dave's Q12: *"apply the restriction to existing records"*.
- Migration: none.

## ccf.replay.record.build_replay_record

- Surface: ccf.replay.record.build_replay_record
- Public surface: true
- Change type: reshaped
- Before: no `issuance` or `subject_withholding` keyword.
- After: adds `issuance: str | None = None` and `subject_withholding: str | None = None`, each recorded verbatim in dimension 5; `None` records the sentinel.
- Why: PROPOSAL, Dave's Q11 and Q12.
- Migration: none. Both keywords are additive and default to the sentinels.

## ccf.replay.serve.ReplayWriter

- Surface: ccf.replay.serve.ReplayWriter
- Public surface: true
- Change type: behavior
- Before: `write_replay_record` filed every record under dimension 1's `graph_snapshot_id`, a hash of the real read (`D-IMPL-371`), so a reference's name could differ between a withheld subject's answer and a nonexistent subject's with no dereference at all.
- After: files every record under its own content address, so a reference's name and version are one identity. Replay resolves by content address, unchanged.
- Why: PROPOSAL, Dave's Q11. Measured by the severing `sever-q11-name-2c96526` in the lane record: restoring the old name turns 12 of the Q11 tests red.
- Migration: none for a replay reader. Records already filed keep the names they were filed under.

## ccf.products.resolver.GovernedResolver

- Surface: ccf.products.resolver.GovernedResolver
- Public surface: true
- Change type: behavior
- Before: a served answer and a refused answer to a product question were the same record whenever the question, the governed state and the instant were the same, and a record carried nothing about its class's withholding posture.
- After: mints a fresh issuance for every served answer and every refusal it records for a product question, and stamps every record with its class declaration's `subject_withholding`. At construction it raises `WithholdingClassListedReadable` when the tenant's entitlement policy lists its class in `evidence_readable_classes` and the class does not affirm `"never"`. At serve time it raises `NeverWithholdingContradicted` when the projection withholds the subject under a class that affirms `"never"`, before anything is rendered, recorded or served.
- Why: PROPOSAL, Dave's Q11 and Q12.
- Migration: two answers to one question at one instant are now two records with two references; the 13 tests named above pin the old property and stay red until Dave rules. A class's records reach their owners only after the class declaration affirms `subject_withholding: never` and the tenant lists it; a projection that may withhold leaves its class at the default. Measured residual: a class that affirms `"never"` and then withholds is a broken deployment, and the answer door shows it as an error where a nonexistent subject's question answers (lane probe `probe_never_contradicted_at_the_door.py`).

## ccf.products.resolver.WithholdingClassListedReadable

- Surface: ccf.products.resolver.WithholdingClassListedReadable
- Public surface: true
- Change type: added
- Before: absent.
- After: a `ProductNotResolvable` raised where the resolver is built when the tenant lists for owner read-back a class whose declaration does not affirm `subject_withholding: never`. The check reads the class declaration, so a composite class is held exactly as any other.
- Why: PROPOSAL, Dave's Q12: *"Reject withholding classes—including affected composites"*. Measured by `tests/http_api/test_sec020_q12_owner_read_back.py::test_q12_a_tenant_listing_a_class_that_may_withhold_is_refused_where_the_resolver_boots` and `::test_q12_the_boot_check_rejects_every_listed_class_that_may_withhold_composites_included`.
- Migration: none unless a tenant lists a class; then the class declaration affirms `never` or the class leaves the list.

## ccf.products.resolver.NeverWithholdingContradicted

- Surface: ccf.products.resolver.NeverWithholdingContradicted
- Public surface: true
- Change type: added
- Before: absent.
- After: a `ProductNotResolvable` raised at serve time when the projection withholds the subject under a class that affirms `subject_withholding: never`, before anything is rendered, recorded or served.
- Why: PROPOSAL, Dave's Q12. The affirmation is what lets the class's records be read back, so it is enforced. Measured by `tests/http_api/test_sec020_q12_owner_read_back.py::test_q12_a_class_that_affirms_never_cannot_withhold_its_subject`.
- Migration: none for a class at the default.

## ccf.products.resolver.RefusalRecorderProtocol

- Surface: ccf.products.resolver.RefusalRecorderProtocol
- Public surface: true
- Change type: behavior
- Before: `record(...)` took no withholding posture.
- After: `record(..., subject_withholding: str | None = None)`, recorded in dimension 5. The governed resolver passes it on every refusal it records, so a recorder that cannot take it fails on every refusal alike, never only on one about a withheld subject.
- Why: PROPOSAL, Dave's Q12: the refusal records of a class that affirms `never` are read back by their owners only if they carry the affirmation.
- Migration: a deployment's own recorder accepts the keyword and hands it to `build_replay_record`. Without it, every refusal the governed resolver records raises `TypeError`.

## ccf.products.contract.SubjectWithholding

- Surface: ccf.products.contract.SubjectWithholding
- Public surface: true
- Change type: added
- Before: absent.
- After: `Literal["may-withhold", "never"]`, a product class's posture on withholding its subject.
- Why: PROPOSAL, Dave's Q12.
- Migration: none.

## ccf.products.contract.SUBJECT_WITHHOLDING_POSSIBLE

- Surface: ccf.products.contract.SUBJECT_WITHHOLDING_POSSIBLE
- Public surface: true
- Change type: added
- Before: absent.
- After: `"may-withhold"`, the default every class declaration carries.
- Why: PROPOSAL, Dave's Q12.
- Migration: none.

## ccf.products.contract.SUBJECT_WITHHOLDING_NEVER

- Surface: ccf.products.contract.SUBJECT_WITHHOLDING_NEVER
- Public surface: true
- Change type: added
- Before: absent.
- After: `"never"`, the affirmation that a class's answers never withhold their subject; the governed resolver enforces it.
- Why: PROPOSAL, Dave's Q12.
- Migration: none.

## ccf.controlplane.artifacts.ProductClassDeclaration

- Surface: ccf.controlplane.artifacts.ProductClassDeclaration
- Public surface: true
- Change type: reshaped
- Before: no withholding posture.
- After: adds `subject_withholding: SubjectWithholding`, default `"may-withhold"` and hash-transparent at it, so every declaration registered before the field keeps its content address. `docs/schemas/ccf.product-class.json` is regenerated.
- Why: PROPOSAL, Dave's Q12.
- Migration: a class whose records owners should read back declares `subject_withholding: never`, and only if its projection never withholds the subject.

## ccf.products.entitlement.ProductEntitlementPolicy

- Surface: ccf.products.entitlement.ProductEntitlementPolicy
- Public surface: true
- Change type: reshaped
- Before: `tenant_id`, `policy_version`, `principals`, `disclosure_level`.
- After: adds `evidence_readable_classes: frozenset[str]`, default empty and hash-transparent at it, so every policy registered before the field keeps its content address. `docs/schemas/ccf.product-entitlement-policy.json` is regenerated.
- Why: PROPOSAL, Dave's Q12: *"Default-deny owner read-back, with an explicit tenant class allowlist"*.
- Migration: owner read-back stops for every product record until the tenant lists the class and the class affirms `never`. Measured on this tree: the test worlds whose job is to deliver an owner's record (`tests/http_api/test_evidence_dereference.py`, the C2 tenant-hold suites for HTTP and MCP, the read-refusal attribution suites for HTTP and MCP) now list their class and stamp `never` on the records they file.

## ccf_runtime.authz.product_entitlement.EvidenceReadabilitySourceProtocol

- Surface: ccf_runtime.authz.product_entitlement.EvidenceReadabilitySourceProtocol
- Public surface: true
- Change type: added
- Before: absent.
- After: an optional, runtime-checkable capability of an entitlement source: `evidence_readable(*, tenant, product_class) -> tuple[bool, ProvenanceSource | None]`. `govern_dereference` reads a source that does not implement it as answering no for every class.
- Why: PROPOSAL, Dave's Q12; fail-closed for a deployment that never considered owner read-back.
- Migration: a deployment-supplied entitlement source that should let some classes' records reach their owners implements it. `ControlPlaneProductEntitlementSource` implements it over the tenant's own policy, with the same two near-miss refusals as `disclosure_level_for`; no policy answers `(False, None)`.

## ccf_runtime.http_api.errors.ERROR_EVIDENCE_CLASS_SEALED

- Surface: ccf_runtime.http_api.errors.ERROR_EVIDENCE_CLASS_SEALED
- Public surface: true
- Change type: added
- Before: absent.
- After: `"evidence-class-sealed"`, the internal error code of an evidence read refused because the tenant does not list the record's class or the record does not carry its class's affirmation. Internal truth only; decided per class and per record generation, never per decision.
- Why: PROPOSAL, Dave's Q12.
- Migration: none.

## ccf_runtime.authz.delivery_boundary.govern_dereference

- Surface: ccf_runtime.authz.delivery_boundary.govern_dereference
- Public surface: true
- Change type: behavior
- Before: a genuine record of the caller's own tenant and principal crossed after the grant was re-decided and at `full` disclosure (`D-IMPL-345` R-2).
- After: hold 2b, after the grant is re-decided and before the erasure consult and the disclosure hold: the tenant must list the record's class (asked through `EvidenceReadabilitySourceProtocol`), and a record that read the fabric must carry `subject_withholding: never`; a record whose dimension 1 is exactly the claim that nothing was read needs only the listing. Otherwise the read is refused `unauthorized` with `evidence-class-sealed`, pinning the policy that answered. Read-refusal records skip it, as they skip hold 2. Every caller inherits it: the HTTP replay and artifact routes, the MCP artifact server's blob, presence and names resources, and the `ccf` CLI's `replay query`, `replay resolve` and `artifact inspect`.
- Why: PROPOSAL, Dave's Q12, amending `D-IMPL-345` R-2. Measured by the severing `sever-q12-hold2b-0b01cee` in the lane record: removing the hold turns 11 of the Q12 and channel-3 tests red.
- Migration: list the classes whose records owners read in each tenant's entitlement policy, and affirm `never` in each such class declaration. Records written before this change stay sealed: they still replay to their own addresses through the replay engine, read from the store by an examiner, not through a door.

## ccf_runtime.mcp.experience.ExperienceReplayReadRefused

- Surface: ccf_runtime.mcp.experience.ExperienceReplayReadRefused
- Public surface: true
- Change type: added
- Before: absent.
- After: a `PermissionError` the Experience door's `get_replay_record` raises on every call, for every caller, before the deployment's `ReplayRecordReaderProtocol` is called.
- Why: PROPOSAL, Dave's Q12: *"every read/replay path"*. The tool names no address and returns whatever the deployment's reader returns, so it cannot show that the fabric's record writer filed the record, whose record it is, or what its class affirms. Measured by `tests/http_api/test_sec020_q12_owner_read_back.py::test_q12_the_experience_door_does_not_serve_the_record_behind_a_withheld_answer`.
- Migration: a deployment that exposed `get_replay_record` keeps constructing the door as before (the reader is still required where the tool is exposed); its callers read their own records back through a governed evidence read.
