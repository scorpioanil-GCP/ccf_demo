# 378-08 — an SDK reader of a store accepts a record only where the fabric's record writer filed it

Lane 378-clientlane measured, and the coordinator reproduced on the
integration tree, that the SDK code which reads a store DIRECTLY — rather than
through the governed read — accepted a record-shaped artifact a tenant's own
principal filed on its client lane (an ordinary `ArtifactWrite` for an
undeclared class) as a Decision Replay record naming another principal:
`resolve_artifact` and `resolve_artifact_at_uri` returned it, over the raw
file store and over the erasure-consulting composition; `replay_refusal`
verified a forged refused record; `replay` reproduced a forged served record
(measured by this lane); child admission took a forged record's touched
entities as the child's own; and `OpenedProduct.record_of` returned a forgery
an outcome named. Dave's ruling (item 3, 2026-10-07): such bytes *"may remain
ordinary client artifacts only if their untrusted origin is explicit and
consumers cannot accept them as governed evidence. Otherwise refuse that path
until provenance is enforced."* This change enforces it.

**The rule** is `govern_dereference`'s "Provenance, before any hold", stated
once in `src` (`ccf.replay.provenance.filed_by_record_writer`) and now also
called by `govern_dereference` itself (a one-call substitution, no behavior
change there): a record is accepted only where the store's own naming shows
the address filed under the tenant the record names, in a class the store's
`WriteKinds` declares under `ReplayMint` — a kind minted only at composition,
which no door can obtain. The writer files under its capability's tenant and
refuses a record naming another (`ReplayTenantMismatch`), so every record it
filed passes.

**What a test measured, and nothing more.** Red before, green after, and red
again with the predicate severed: `tests/replay/test_record_provenance.py` and
`tests/products/test_record_provenance_admission.py`. Records written before
this change replay to their own addresses: the committed `golden_13bd250`
record (`tests/replay/test_golden_13bd250.py`) and a golden record produced
by the unchanged `25a6caa8` source.

## ccf.replay.provenance.filed_by_record_writer

- Surface: ccf.replay.provenance.filed_by_record_writer
- Public surface: true
- Change type: added
- Before: absent; the rule existed only inline in `ccf_runtime.authz.delivery_boundary.govern_dereference`.
- After: `filed_by_record_writer(store, *, content_address, tenant_id) -> bool` answers whether some name the store holds for the address is under `tenant_id` in a class its `WriteKinds` declares under `ReplayMint`. It reads naming only, never bytes. A store that answers no `names_at` or declares no `WriteKinds` raises `UnattributableRecordStore`; through an `ErasureConsultingStore`, the store it wraps must answer `names_at` too.
- Why: Dave's item 3 (`D-IMPL-378`): one provenance check, called at every place SDK code accepts a record read from a store.
- Migration: none; new.

## ccf.replay.provenance.require_filed_by_record_writer

- Surface: ccf.replay.provenance.require_filed_by_record_writer
- Public surface: true
- Change type: added
- Before: absent.
- After: returns only if `filed_by_record_writer` holds; otherwise raises `RecordNotFiledByRecordWriter` (or `UnattributableRecordStore` for a store that cannot answer). Called after the record's bytes are parsed and before anything they say is accepted, by `resolve_artifact`, `GrantBoundChildResolver` child admission and `OpenedProduct.record_of`.
- Why: Dave's item 3 (`D-IMPL-378`).
- Migration: none; new. Code outside the SDK that turns stored bytes into a `DecisionReplayRecord` and treats it as evidence calls this after parsing.

## ccf.replay.provenance.RecordNotFiledByRecordWriter

- Surface: ccf.replay.provenance.RecordNotFiledByRecordWriter
- Public surface: true
- Change type: added
- Before: absent.
- After: an `ArtifactNotFound` (so also a `KeyError` and an `ArtifactStoreError`), on the precedent of `MalformedContentAddress`: the store holds record-shaped bytes at the address and shows no filing of them by the fabric's record writer under the record's tenant. Every caller that already handles an absent record handles it identically; a caller that wants the mechanism catches it by name. The replay engine chains it as the cause of a `ReplayUnresolvable`.
- Why: Dave's item 3 (`D-IMPL-378`): forged bytes answer as a missing record does.
- Migration: none; new.

## ccf.replay.provenance.UnattributableRecordStore

- Surface: ccf.replay.provenance.UnattributableRecordStore
- Public surface: true
- Change type: added
- Before: absent.
- After: a `TypeError` raised when a record is read through a store that cannot say who filed an address — no `names_at`, no `WriteKinds`, or an `ErasureConsultingStore` over a store with no `names_at`. A wiring defect, refused by name, never a record accepted on the bytes' word; the posture of `UnattributableDeliveryBoundaryError`.
- Why: Dave's item 3 (`D-IMPL-378`): a store that cannot attribute fails closed.
- Migration: none; new.

## ccf.replay.engine.resolve_artifact

- Surface: ccf.replay.engine.resolve_artifact
- Public surface: true
- Change type: behavior
- Before: for `contract=DecisionReplayRecord`, any bytes at the address that hashed to it and parsed as a record were returned as one, whoever filed them, including a record-shaped artifact on a tenant's client lane naming another principal.
- After: for a `DecisionReplayRecord`, after the byte-first hash check and validation, the store must show the address filed by the fabric's record writer under the tenant the record names (`require_filed_by_record_writer`). Otherwise it raises `ReplayUnresolvable`, as for a missing record, with `RecordNotFiledByRecordWriter` as its cause. A store that cannot attribute raises `UnattributableRecordStore`. Every caller inherits it: `resolve_artifact_at_uri`, `replay` and `replay_refusal`, whose prologue resolves the record through it, and `govern_dereference`'s own record read. Unchanged: every other contract, missing and erased addresses, and the hash check.
- Why: Dave's item 3 (`D-IMPL-378`). Red tests: `tests/replay/test_record_provenance.py` (`resolve_artifact` and `resolve_artifact_at_uri` over the raw store and the erasure-consulting composition, `replay`, `replay_refusal`, a record filed by another tenant's writer, a store without `names_at` or `WriteKinds`).
- Migration: a store a replay reads through must answer `names_at` and declare `WriteKinds` naming every record class its records were filed under, under `ReplayMint`, as the shipped `FileArtifactStore` and `McpArtifactStore` do when opened with the deployment's declaration. Consequences: a read-back store opened with an empty or partial declaration now refuses genuine records; a deployment that renames its record class keeps declaring the old class under `ReplayMint` to replay records filed under it; records written straight to a substrate without a naming entry no longer resolve; file them through `put` under the record class.

## ccf.replay.engine.resolve_artifact_at_uri

- Surface: ccf.replay.engine.resolve_artifact_at_uri
- Public surface: true
- Change type: behavior
- Before: a URI naming a record-shaped artifact on a client lane resolved to it as a `DecisionReplayRecord`.
- After: naming resolution is unchanged, then `resolve_artifact` applies the provenance rule. A URI naming bytes the record writer did not file raises `ReplayUnresolvable`. A URI naming a copy of a genuine record under another name resolves, because identical bytes are one artifact.
- Why: Dave's item 3 (`D-IMPL-378`).
- Migration: as for `resolve_artifact`.

## ccf.replay.engine.replay_refusal

- Surface: ccf.replay.engine.replay_refusal
- Public surface: true
- Change type: behavior
- Before: a forged refused record filed on a client lane was resolved, verified and returned as a `RefusalReplayOutcome` naming the principal the bytes named.
- After: the prologue's record read applies the provenance rule, so such a record raises `ReplayUnresolvable` before any binding is resolved. `replay` changes identically for a forged served record, which it previously reproduced into a `ReplayOutcome`.
- Why: Dave's item 3 (`D-IMPL-378`).
- Migration: as for `resolve_artifact`.

## ccf.products.child_resolver.GrantBoundChildResolver

- Surface: ccf.products.child_resolver.GrantBoundChildResolver
- Public surface: true
- Change type: behavior
- Before: for a locally dispatched child, the record its replay reference named was read as the child's own execution record whoever filed it; only its product address was checked against the child's, so a record-shaped client-lane artifact with the right product address and forged touched entities decided the eligibility check.
- After: the referenced bytes must have been filed by the fabric's record writer under the tenant they name, or `RecordNotFiledByRecordWriter` is raised before anything is read out of them. It propagates as any lookup failure from child resolution does, out of the composite resolver unless the deployment declares it a seam refusal. `UnattributableRecordStore` is raised for a store that cannot attribute. Inherited by `QuestionBoundChildResolver`, which admits through it.
- Why: Dave's item 3 (`D-IMPL-378`). Red test: `tests/products/test_record_provenance_admission.py::test_child_admission_refuses_a_child_record_forged_on_the_tenants_own_client_lane`, through the shipped composite resolver.
- Migration: as for `resolve_artifact`. A child producer's replay reference names a record its fabric's record writer filed in the store the composite reads.

## ccf.products.product.OpenedProduct.record_of

- Surface: ccf.products.product.OpenedProduct.record_of
- Public surface: true
- Change type: behavior
- Before: returned the bytes at the address or URI an outcome named, parsed as a `DecisionReplayRecord`, whoever filed them.
- After: returns them only where the product's store shows the fabric's record writer filed them under the tenant they name; otherwise raises `RecordNotFiledByRecordWriter`, or `UnattributableRecordStore` for a store that cannot attribute.
- Why: Dave's item 3 (`D-IMPL-378`). Red test: `tests/products/test_record_provenance_admission.py::test_record_of_refuses_a_record_forged_on_the_tenants_own_client_lane` (a served outcome naming the forgery's address, a refusal naming its URI).
- Migration: none for outcomes the product itself returned.
