# 374-04 — SEC-009: the minimum erasure mechanism

`D-IMPL-374` (4), ruling U1–U12 on the design's recommendations
(`docs/D-IMPL-367-ERASURE-DESIGN.md` §11). An erasure is a fact the fabric
records. The fabric does not perform it as a mutation. A human approves it
through the `ApprovalGate` of a workflow the deployment declares and the door
validates. It is written as an immutable `ccf.erasure-record`, and the
append-only registry mirror records it. The decorating store refuses to serve
erased content on every read. `compose_erasure_consult` composes the decorating
store at every store construction site (U12, ruling 2). Authorization runs
before the consult (ruling 1).

Three behavior changes apply to existing public names:

- `create_app`, `open_product`, `build_governed_resolver`, the in-process adapter's boot and the local CLI dependencies compose their store through `compose_erasure_consult`.
- `resolve_artifact` and `resolve_artifact_at_uri` re-raise `ErasedContentRefused` by name. They do not turn it into `ReplayUnresolvable`.
- `govern_dereference` runs the principal and grant holds first, against the unconsulted inner store. It then maps an erased address by the entitled caller's disclosure level:
  - at `minimal`, the route's not-found shell (404);
  - at `reasoned` and `full`, an `erased-content` shell (410).

What this change does not do:

- **No byte destruction and no destruction claim** (`D-IMPL-367` O1).
- **No field-scoped erasure** (U5). Erasure is whole-artifact only.
- **No retention lifecycle.**
- **No pseudonymization** (U1/U3).
- **No graph erasure** (G8/O2).
- **No un-erasure** (U6).
- **No legal-compliance claim.**

Disclosed residuals (ruling 5):

- `RequestedAddress.retained_since` is the instant the minimum age is measured from. It is requester-declared and human-approved, not derived from the store, because the `ArtifactStoreProtocol` records no write instant.
- `ClassRetention.minimum_age` is in whole days.
- The MCP artifact server holds no Control Plane, so it does not compose the consult itself. A deployment passes it a store already composed with `compose_erasure_consult` (ruling 2, named and stopped).

The door requires three things: the distinct `artifact.erase` capability for
exactly the request, the workflow's `Execute`/`Resume` capabilities, and the
recorded human approval (ruling 3).

## ccf.erasure.ClassRetention

- Surface: ccf.erasure.ClassRetention
- Public surface: true
- Change type: added
- Before: absent
- After: A contract for one artifact class's retention and hold policy: `erasable` (default False), `severity_exempt`, the closed `reasons`, active `holds`, and `minimum_age` in whole days, which is required and has no default (U10).
- Why: SEC-009; G7 default refuse; U10 rules the minimum age present on the contract with no SDK default.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.ERASURE_INDEX

- Surface: ccf.erasure.ERASURE_INDEX
- Public surface: true
- Change type: added
- Before: absent
- After: The `ArtifactClass` `ccf.erasure-index` for the per-tenant registry mirror.
- Why: SEC-009; U7 (b): the index the consult reads is an append-only registry mirror of the erasure records.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.ERASURE_INDEX_SEMVER

- Surface: ccf.erasure.ERASURE_INDEX_SEMVER
- Public surface: true
- Change type: added
- Before: absent
- After: The mirror's stated semver lane, `1.0.0`.
- Why: SEC-009; A versioned artifact states its lane; it is never defaulted.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.ERASURE_RECORD_CLASS

- Surface: ccf.erasure.ERASURE_RECORD_CLASS
- Public surface: true
- Change type: added
- Before: absent
- After: The constant `ccf.erasure-record`, the class an erasure record is filed under.
- Why: SEC-009; G3: the erasure fact is an immutable artifact filed through the store's one write verb.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.ERASURE_SUBJECT_DECLARATION

- Surface: ccf.erasure.ERASURE_SUBJECT_DECLARATION
- Public surface: true
- Change type: added
- Before: absent
- After: The `ArtifactClass` `ccf.erasure-subject-declaration`. Adopter-registered and not manifest-addressable.
- Why: SEC-009; G1: what a subject is, declared by the deployment.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.ErasedAddress

- Surface: ccf.erasure.ErasedAddress
- Public surface: true
- Change type: added
- Before: absent
- After: A contract for one erased artifact on a record: address, class, key paths, `matched` (presence only), and `scope`, which is `whole` this phase (U5).
- Why: SEC-009; G3: design §2.3 record shape.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.ErasedContentRefused

- Surface: ccf.erasure.ErasedContentRefused
- Public surface: true
- Change type: added
- Before: absent
- After: An `ArtifactStoreError` the decorating store raises on a read of an erased address. It carries the record address, the reason and the instant, and nothing of the subject. It is not an `ArtifactNotFound` and not a `LookupError`.
- Why: SEC-009; G4/G5: an erasure is a recorded decision, not an absence.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.ErasureConsultingStore

- Surface: ccf.erasure.ErasureConsultingStore
- Public surface: true
- Change type: added
- Before: absent
- After: A decorator over any `ArtifactStoreProtocol`. `get` and `resolve_uri` consult the mirror and refuse erased addresses. `exists` does not consult (U8). `put` passes through. Every store construction site composes it through `compose_erasure_consult` (U12, ruling 2). It forwards the inner store's naming introspection only (`root`, `names_at`, `versions`).
- Why: SEC-009; G4: one consult at the substrate read, covering every route the store serves.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.ErasureIndex

- Surface: ccf.erasure.ErasureIndex
- Public surface: true
- Change type: added
- Before: absent
- After: The consult's reader. It reads every version of every tenant's mirror through unaudited registry introspection.
- Why: SEC-009; U7 (b). The whole history is read, so a later version cannot un-erase by omission (U6).
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.ErasureIndexEntry

- Surface: ccf.erasure.ErasureIndexEntry
- Public surface: true
- Change type: added
- Before: absent
- After: A contract for one erased address: record address, admitted reason, instant.
- Why: SEC-009; U7 (b): what the consult needs, and nothing of the subject.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.ErasureIndexMirror

- Surface: ccf.erasure.ErasureIndexMirror
- Public surface: true
- Change type: added
- Before: absent
- After: A versioned artifact holding one tenant's erased addresses. It grows only.
- Why: SEC-009; U7 (b), on the `EntityInvalidationRegister` precedent (`D-IMPL-334`).
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.ErasureIndexSource

- Surface: ccf.erasure.ErasureIndexSource
- Public surface: true
- Change type: added
- Before: absent
- After: A Protocol for the unaudited registry introspection the index reads: `keys_of_class`, `versions`, `peek`.
- Why: SEC-009; The consult runs on every read and must not audit each read as a resolution.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.ErasureRecord

- Surface: ccf.erasure.ErasureRecord
- Public surface: true
- Change type: added
- Before: absent
- After: The immutable erasure fact: tenant, record id, subject class, salted `subject_ref`, addresses, `erased_at`, approver `actor`, `requested_by`, authorizing decision, approval policy, retention decision, reason, legal basis.
- Why: SEC-009; G3; it can be asserted and never retracted (U6).
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.ErasureRequest

- Surface: ccf.erasure.ErasureRequest
- Public surface: true
- Change type: added
- Before: absent
- After: What a requester asks to erase. Its content hash `request_id` is the approval workflow's execution id.
- Why: SEC-009; U9: the human approves exactly this request.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.ErasureSubjectClass

- Surface: ccf.erasure.ErasureSubjectClass
- Public surface: true
- Change type: added
- Before: absent
- After: One declared subject class: `class_id`, `key_paths`, `artifact_classes`, `identifier_kind`, and `subject_ref_salt`. A key path that reaches a replay input is refused (U2). A `principal` subject is refused (U1).
- Why: SEC-009; G1/G2 with U1, U2 and U4.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.ErasureSubjectDeclaration

- Surface: ccf.erasure.ErasureSubjectDeclaration
- Public surface: true
- Change type: added
- Before: absent
- After: A versioned artifact listing a tenant's subject classes.
- Why: SEC-009; G1.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.LegalHold

- Surface: ccf.erasure.LegalHold
- Public surface: true
- Change type: added
- Before: absent
- After: A contract for one active legal hold, matched by salted subject refs or by addresses.
- Why: SEC-009; G7: a matching hold refuses erasure, by hold id.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.REPLAY_INPUT_PATHS

- Surface: ccf.erasure.REPLAY_INPUT_PATHS
- Public surface: true
- Change type: added
- Before: absent
- After: The tuple of Decision Replay record paths that are replay inputs.
- Why: SEC-009; U2: the SDK's own field names, a mechanism constant; no subject key may reach them.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.RETENTION_HOLD_POLICY

- Surface: ccf.erasure.RETENTION_HOLD_POLICY
- Public surface: true
- Change type: added
- Before: absent
- After: The `ArtifactClass` `ccf.retention-hold-policy`.
- Why: SEC-009; G7.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.RETENTION_REASON_CODES

- Surface: ccf.erasure.RETENTION_REASON_CODES
- Public surface: true
- Change type: added
- Before: absent
- After: The judgment's closed code vocabulary (`class-absent`, `not-erasable`, `severity-exempt`, `legal-hold`, `reason-unknown`, `under-minimum-age`, `policy-unresolvable`, `admitted`).
- Why: SEC-009; G7: a structured audit answer, never a subject identifier.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.RequestedAddress

- Surface: ccf.erasure.RequestedAddress
- Public surface: true
- Change type: added
- Before: absent
- After: One address a request names, with its class and a requester-declared, human-approved `retained_since`.
- Why: SEC-009; U10: the store's Protocol records no write instant, so the age is declared and approved.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.RetentionDecision

- Surface: ccf.erasure.RetentionDecision
- Public surface: true
- Change type: added
- Before: absent
- After: The judgment's audit answer: `policy_ref`, `verdict`, `reason_code`, `hold_id`, `address`.
- Why: SEC-009; G7.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.RetentionHoldPolicy

- Surface: ccf.erasure.RetentionHoldPolicy
- Public surface: true
- Change type: added
- Before: absent
- After: A versioned artifact mapping artifact classes to `ClassRetention`. An absent class refuses.
- Why: SEC-009; G7 default refuse.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.append_to_erasure_index

- Surface: ccf.erasure.append_to_erasure_index
- Public surface: true
- Change type: added
- Before: absent
- After: A function that appends entries to the capability's tenant mirror as a new audited version, under a composition-minted `Register` for exactly that key.
- Why: SEC-009; U7 (b); `D-IMPL-354`.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.erasure_index_key

- Surface: ccf.erasure.erasure_index_key
- Public surface: true
- Change type: added
- Before: absent
- After: The mirror's Control Plane key, `{tenant}/ccf.erasure-index`.
- Why: SEC-009; U7 (b): one mirror per tenant.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.judge_retention

- Surface: ccf.erasure.judge_retention
- Public surface: true
- Change type: added
- Before: absent
- After: A pure, fail-closed judgment of a request against a policy at an injected instant.
- Why: SEC-009; G7.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.subject_ref_for

- Surface: ccf.erasure.subject_ref_for
- Public surface: true
- Change type: added
- Before: absent
- After: Returns `sha256(salt || 0x00 || identifier)` under the declared class's salt.
- Why: SEC-009; U4: the raw identifier never enters the fabric.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.contracts.ClassRetention

- Surface: ccf.erasure.contracts.ClassRetention
- Public surface: true
- Change type: added
- Before: absent
- After: A contract for one artifact class's retention and hold policy: `erasable` (default False), `severity_exempt`, the closed `reasons`, active `holds`, and `minimum_age` in whole days, which is required and has no default (U10).
- Why: SEC-009; G7 default refuse; U10 rules the minimum age present on the contract with no SDK default.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.contracts.ERASURE_RECORD_CLASS

- Surface: ccf.erasure.contracts.ERASURE_RECORD_CLASS
- Public surface: true
- Change type: added
- Before: absent
- After: The constant `ccf.erasure-record`, the class an erasure record is filed under.
- Why: SEC-009; G3: the erasure fact is an immutable artifact filed through the store's one write verb.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.contracts.ERASURE_SUBJECT_DECLARATION

- Surface: ccf.erasure.contracts.ERASURE_SUBJECT_DECLARATION
- Public surface: true
- Change type: added
- Before: absent
- After: The `ArtifactClass` `ccf.erasure-subject-declaration`. Adopter-registered and not manifest-addressable.
- Why: SEC-009; G1: what a subject is, declared by the deployment.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.contracts.ErasedAddress

- Surface: ccf.erasure.contracts.ErasedAddress
- Public surface: true
- Change type: added
- Before: absent
- After: A contract for one erased artifact on a record: address, class, key paths, `matched` (presence only), and `scope`, which is `whole` this phase (U5).
- Why: SEC-009; G3: design §2.3 record shape.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.contracts.ErasureRecord

- Surface: ccf.erasure.contracts.ErasureRecord
- Public surface: true
- Change type: added
- Before: absent
- After: The immutable erasure fact: tenant, record id, subject class, salted `subject_ref`, addresses, `erased_at`, approver `actor`, `requested_by`, authorizing decision, approval policy, retention decision, reason, legal basis.
- Why: SEC-009; G3; it can be asserted and never retracted (U6).
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.contracts.ErasureRequest

- Surface: ccf.erasure.contracts.ErasureRequest
- Public surface: true
- Change type: added
- Before: absent
- After: What a requester asks to erase. Its content hash `request_id` is the approval workflow's execution id.
- Why: SEC-009; U9: the human approves exactly this request.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.contracts.ErasureSubjectClass

- Surface: ccf.erasure.contracts.ErasureSubjectClass
- Public surface: true
- Change type: added
- Before: absent
- After: One declared subject class: `class_id`, `key_paths`, `artifact_classes`, `identifier_kind`, and `subject_ref_salt`. A key path that reaches a replay input is refused (U2). A `principal` subject is refused (U1).
- Why: SEC-009; G1/G2 with U1, U2 and U4.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.contracts.ErasureSubjectDeclaration

- Surface: ccf.erasure.contracts.ErasureSubjectDeclaration
- Public surface: true
- Change type: added
- Before: absent
- After: A versioned artifact listing a tenant's subject classes.
- Why: SEC-009; G1.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.contracts.LegalHold

- Surface: ccf.erasure.contracts.LegalHold
- Public surface: true
- Change type: added
- Before: absent
- After: A contract for one active legal hold, matched by salted subject refs or by addresses.
- Why: SEC-009; G7: a matching hold refuses erasure, by hold id.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.contracts.REPLAY_INPUT_PATHS

- Surface: ccf.erasure.contracts.REPLAY_INPUT_PATHS
- Public surface: true
- Change type: added
- Before: absent
- After: The tuple of Decision Replay record paths that are replay inputs.
- Why: SEC-009; U2: the SDK's own field names, a mechanism constant; no subject key may reach them.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.contracts.RETENTION_HOLD_POLICY

- Surface: ccf.erasure.contracts.RETENTION_HOLD_POLICY
- Public surface: true
- Change type: added
- Before: absent
- After: The `ArtifactClass` `ccf.retention-hold-policy`.
- Why: SEC-009; G7.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.contracts.RETENTION_REASON_CODES

- Surface: ccf.erasure.contracts.RETENTION_REASON_CODES
- Public surface: true
- Change type: added
- Before: absent
- After: The judgment's closed code vocabulary (`class-absent`, `not-erasable`, `severity-exempt`, `legal-hold`, `reason-unknown`, `under-minimum-age`, `policy-unresolvable`, `admitted`).
- Why: SEC-009; G7: a structured audit answer, never a subject identifier.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.contracts.RequestedAddress

- Surface: ccf.erasure.contracts.RequestedAddress
- Public surface: true
- Change type: added
- Before: absent
- After: One address a request names, with its class and a requester-declared, human-approved `retained_since`.
- Why: SEC-009; U10: the store's Protocol records no write instant, so the age is declared and approved.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.contracts.RetentionDecision

- Surface: ccf.erasure.contracts.RetentionDecision
- Public surface: true
- Change type: added
- Before: absent
- After: The judgment's audit answer: `policy_ref`, `verdict`, `reason_code`, `hold_id`, `address`.
- Why: SEC-009; G7.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.contracts.RetentionHoldPolicy

- Surface: ccf.erasure.contracts.RetentionHoldPolicy
- Public surface: true
- Change type: added
- Before: absent
- After: A versioned artifact mapping artifact classes to `ClassRetention`. An absent class refuses.
- Why: SEC-009; G7 default refuse.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.contracts.judge_retention

- Surface: ccf.erasure.contracts.judge_retention
- Public surface: true
- Change type: added
- Before: absent
- After: A pure, fail-closed judgment of a request against a policy at an injected instant.
- Why: SEC-009; G7.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.contracts.subject_ref_for

- Surface: ccf.erasure.contracts.subject_ref_for
- Public surface: true
- Change type: added
- Before: absent
- After: Returns `sha256(salt || 0x00 || identifier)` under the declared class's salt.
- Why: SEC-009; U4: the raw identifier never enters the fabric.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.index.ERASURE_INDEX

- Surface: ccf.erasure.index.ERASURE_INDEX
- Public surface: true
- Change type: added
- Before: absent
- After: The `ArtifactClass` `ccf.erasure-index` for the per-tenant registry mirror.
- Why: SEC-009; U7 (b): the index the consult reads is an append-only registry mirror of the erasure records.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.index.ERASURE_INDEX_SEMVER

- Surface: ccf.erasure.index.ERASURE_INDEX_SEMVER
- Public surface: true
- Change type: added
- Before: absent
- After: The mirror's stated semver lane, `1.0.0`.
- Why: SEC-009; A versioned artifact states its lane; it is never defaulted.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.index.ErasureIndex

- Surface: ccf.erasure.index.ErasureIndex
- Public surface: true
- Change type: added
- Before: absent
- After: The consult's reader. It reads every version of every tenant's mirror through unaudited registry introspection.
- Why: SEC-009; U7 (b). The whole history is read, so a later version cannot un-erase by omission (U6).
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.index.ErasureIndexEntry

- Surface: ccf.erasure.index.ErasureIndexEntry
- Public surface: true
- Change type: added
- Before: absent
- After: A contract for one erased address: record address, admitted reason, instant.
- Why: SEC-009; U7 (b): what the consult needs, and nothing of the subject.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.index.ErasureIndexMirror

- Surface: ccf.erasure.index.ErasureIndexMirror
- Public surface: true
- Change type: added
- Before: absent
- After: A versioned artifact holding one tenant's erased addresses. It grows only.
- Why: SEC-009; U7 (b), on the `EntityInvalidationRegister` precedent (`D-IMPL-334`).
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.index.ErasureIndexSource

- Surface: ccf.erasure.index.ErasureIndexSource
- Public surface: true
- Change type: added
- Before: absent
- After: A Protocol for the unaudited registry introspection the index reads: `keys_of_class`, `versions`, `peek`.
- Why: SEC-009; The consult runs on every read and must not audit each read as a resolution.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.index.append_to_erasure_index

- Surface: ccf.erasure.index.append_to_erasure_index
- Public surface: true
- Change type: added
- Before: absent
- After: A function that appends entries to the capability's tenant mirror as a new audited version, under a composition-minted `Register` for exactly that key.
- Why: SEC-009; U7 (b); `D-IMPL-354`.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.index.erasure_index_key

- Surface: ccf.erasure.index.erasure_index_key
- Public surface: true
- Change type: added
- Before: absent
- After: The mirror's Control Plane key, `{tenant}/ccf.erasure-index`.
- Why: SEC-009; U7 (b): one mirror per tenant.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.store.ErasedContentRefused

- Surface: ccf.erasure.store.ErasedContentRefused
- Public surface: true
- Change type: added
- Before: absent
- After: An `ArtifactStoreError` the decorating store raises on a read of an erased address. It carries the record address, the reason and the instant, and nothing of the subject. It is not an `ArtifactNotFound` and not a `LookupError`.
- Why: SEC-009; G4/G5: an erasure is a recorded decision, not an absence.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.store.ErasureConsultingStore

- Surface: ccf.erasure.store.ErasureConsultingStore
- Public surface: true
- Change type: added
- Before: absent
- After: A decorator over any `ArtifactStoreProtocol`. `get` and `resolve_uri` consult the mirror and refuse erased addresses. `exists` does not consult (U8). `put` passes through. Every store construction site composes it through `compose_erasure_consult` (U12, ruling 2). It forwards the inner store's naming introspection only (`root`, `names_at`, `versions`).
- Why: SEC-009; G4: one consult at the substrate read, covering every route the store serves.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf_runtime.erasure.ErasureDoor

- Surface: ccf_runtime.erasure.ErasureDoor
- Public surface: true
- Change type: added
- Before: absent
- After: The governed door. `request` validates the declaration and judges retention against the pinned policy, then starts the deployment-declared one-gate workflow. `complete` holds the presented approval to what the HITL authority path recorded, re-judges against the pinned and the newest policy, resumes, and only on completion files the record and appends the mirror.
- Why: SEC-009; G6/U9: an erasure is written only on a recorded human approval.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf_runtime.erasure.door.ErasureDoor

- Surface: ccf_runtime.erasure.door.ErasureDoor
- Public surface: true
- Change type: added
- Before: absent
- After: The governed door. `request` validates the declaration and judges retention against the pinned policy, then starts the deployment-declared one-gate workflow. `complete` holds the presented approval to what the HITL authority path recorded, re-judges against the pinned and the newest policy, resumes, and only on completion files the record and appends the mirror.
- Why: SEC-009; G6/U9: an erasure is written only on a recorded human approval.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf_runtime.erasure.ErasureRefused

- Surface: ccf_runtime.erasure.ErasureRefused
- Public surface: true
- Change type: added
- Before: absent
- After: A `PermissionError` carrying `reason_code` and, for a retention refusal, the `RetentionDecision`.
- Why: SEC-009; Every refusal is by name and writes nothing.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf_runtime.erasure.door.ErasureRefused

- Surface: ccf_runtime.erasure.door.ErasureRefused
- Public surface: true
- Change type: added
- Before: absent
- After: A `PermissionError` carrying `reason_code` and, for a retention refusal, the `RetentionDecision`.
- Why: SEC-009; Every refusal is by name and writes nothing.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf_runtime.erasure.ErasureWorkflowUngated

- Surface: ccf_runtime.erasure.ErasureWorkflowUngated
- Public surface: true
- Change type: added
- Before: absent
- After: A `ValueError` raised when the deployment's erasure workflow can reach a terminal state without crossing a typed approval gate.
- Why: SEC-009; U9: the request/approval shape is the deployment's, validated by the door.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf_runtime.erasure.door.ErasureWorkflowUngated

- Surface: ccf_runtime.erasure.door.ErasureWorkflowUngated
- Public surface: true
- Change type: added
- Before: absent
- After: A `ValueError` raised when the deployment's erasure workflow can reach a terminal state without crossing a typed approval gate.
- Why: SEC-009; U9: the request/approval shape is the deployment's, validated by the door.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.products.refusal.ErasedContentRefusal

- Surface: ccf.products.refusal.ErasedContentRefusal
- Public surface: true
- Change type: added
- Before: absent
- After: A refusal kind `erased-content`: detail, `erasure_reason`, `erased_at`, `erasure_record_address`. A door renders it only at `reasoned` and `full`. The record address is withheld below `full`.
- Why: SEC-009; G5/U11: a disclosure-governed reading of an erased address.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.replay.engine.ERASED_SITE_RETAINED_CHILD_QUESTION

- Surface: ccf.replay.engine.ERASED_SITE_RETAINED_CHILD_QUESTION
- Public surface: true
- Change type: added
- Before: absent
- After: The site token `retained-child-question`.
- Why: SEC-009; §5.2: names where a replay met an erased member.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.replay.engine.ErasedContent

- Surface: ccf.replay.engine.ErasedContent
- Public surface: true
- Change type: added
- Before: absent
- After: A replay result member reporting one erased retained member: site, address, record address, reason, instant.
- Why: SEC-009; §5.2: a replay over erased retained content completes, and the erasure is disclosed rather than reported as absent.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf_runtime.http_api.refusal_status.STATUS_GONE

- Surface: ccf_runtime.http_api.refusal_status.STATUS_GONE
- Public surface: true
- Change type: added
- Before: absent
- After: The HTTP status `410` for the `erased-content` kind.
- Why: SEC-009; U11: 410 at `reasoned`/`full`; the route's not-found rendering at `minimal`.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.compose_erasure_consult

- Surface: ccf.erasure.compose_erasure_consult
- Public surface: true
- Change type: added
- Before: absent
- After: THE composition helper. It wraps any store in `ErasureConsultingStore` over a Control Plane's registry mirror, and is idempotent on a store that is already wrapped. `create_app`, `open_product`, `build_governed_resolver`, the in-process adapter's boot and the local CLI dependencies all compose through it.
- Why: SEC-009; ruling 2 on `D-IMPL-374` (4), "composed ALWAYS means every store construction site".
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.store.compose_erasure_consult

- Surface: ccf.erasure.store.compose_erasure_consult
- Public surface: true
- Change type: added
- Before: absent
- After: THE composition helper. It wraps any store in `ErasureConsultingStore` over a Control Plane's registry mirror, and is idempotent on a store that is already wrapped. `create_app`, `open_product`, `build_governed_resolver`, the in-process adapter's boot and the local CLI dependencies all compose through it.
- Why: SEC-009; ruling 2 on `D-IMPL-374` (4), "composed ALWAYS means every store construction site".
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.ErasureIndexUnavailable

- Surface: ccf.erasure.ErasureIndexUnavailable
- Public surface: true
- Change type: added
- Before: absent
- After: a `TypeError` raised at composition when a Control Plane offers no `keys_of_class`/`versions`/`peek`. The shipped `ControlPlaneRegistry` offers all three.
- Why: SEC-009; ruling 2. A store that cannot consult would serve erased content silently, so it is refused where an operator sees it.
- Migration: a deployment that passes `build_governed_resolver` a custom `ControlPlaneProtocol` implementation without registry introspection must add those three methods.

## ccf.erasure.store.ErasureIndexUnavailable

- Surface: ccf.erasure.store.ErasureIndexUnavailable
- Public surface: true
- Change type: added
- Before: absent
- After: a `TypeError` raised at composition when a Control Plane offers no `keys_of_class`/`versions`/`peek`. The shipped `ControlPlaneRegistry` offers all three.
- Why: SEC-009; ruling 2. A store that cannot consult would serve erased content silently, so it is refused where an operator sees it.
- Migration: a deployment that passes `build_governed_resolver` a custom `ControlPlaneProtocol` implementation without registry introspection must add those three methods.

## ccf.authz.actions.ACTION_ARTIFACT_ERASE

- Surface: ccf.authz.actions.ACTION_ARTIFACT_ERASE
- Public surface: true
- Change type: added
- Before: absent
- After: the action id `artifact.erase`. Its resource is `"<subject_class>/<request_id>"`.
- Why: SEC-009; ruling 3 on `D-IMPL-374` (4) (design §4.1). Erasure is an action of its own, kept apart from every read, write and workflow action.
- Migration: a deployment that erases grants this action to its erasure requesters in its scope mapping.

## ccf.authz.capability.ArtifactErase

- Surface: ccf.authz.capability.ArtifactErase
- Public surface: true
- Change type: added
- Before: absent
- After: the erasure door's `ActionKind`. A door mints it with `mint` from an authorizer's allow. It is never composition-mintable. `ErasureDoor.request` and `ErasureDoor.complete` take it as a required keyword (`erase=`), alongside the recorded human approval. A general `Execute`/`Resume` passed in its place, or an erase capability issued for a different request, is refused by `verify` as `CapabilityBypassError`.
- Why: SEC-009; ruling 3. A principal that holds only general workflow `Execute`/`Resume` must not be able to have an erasure written.
- Migration: callers of the erasure door pass `erase=` with a capability for exactly the request.

## ccf.replay.engine.ErasedReplayOutcome

- Surface: ccf.replay.engine.ErasedReplayOutcome
- Public surface: true
- Change type: added
- Before: absent
- After: A positive replay outcome for a replay that met erased content it would have to read to re-execute: the decision record itself, an admitted child contract, or a re-execution artifact. It carries `record_content_address`, `record` (`None` when the record itself was erased) and a non-empty `erased_content`. No product is reproduced.
- Why: SEC-009; ruling 4 (design §5.2). Replay stays positive and discloses the erasure for every erased input class. It never refuses by name, and it never re-derives a product from bytes the fabric refuses to serve.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.replay.engine.ERASED_SITE_CHILD_CONTRACT

- Surface: ccf.replay.engine.ERASED_SITE_CHILD_CONTRACT
- Public surface: true
- Change type: added
- Before: absent
- After: The site token `child-contract`.
- Why: SEC-009; ruling 4.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.replay.engine.ERASED_SITE_DECISION_RECORD

- Surface: ccf.replay.engine.ERASED_SITE_DECISION_RECORD
- Public surface: true
- Change type: added
- Before: absent
- After: The site token `decision-record`.
- Why: SEC-009; ruling 4.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.replay.engine.ERASED_SITE_REPLAY_ARTIFACT

- Surface: ccf.replay.engine.ERASED_SITE_REPLAY_ARTIFACT
- Public surface: true
- Change type: added
- Before: absent
- After: The site token `replay-artifact`, for any other artifact the re-execution reads.
- Why: SEC-009; ruling 4.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.replay.engine.replay

- Surface: ccf.replay.engine.replay
- Public surface: true
- Change type: reshaped
- Before: returned `ReplayOutcome`.
- After: returns `ReplayOutcome | ErasedReplayOutcome`. It returns the second when the record itself, an admitted child contract, or an artifact the re-execution reads was erased.
- Why: SEC-009; ruling 4. Before this change the call raised `ErasedContentRefused`.
- Migration: a caller that replays over a store composed with the erasure consult handles `ErasedReplayOutcome`. On a store with nothing erased it never appears.

## ccf.replay.engine.replay_refusal

- Surface: ccf.replay.engine.replay_refusal
- Public surface: true
- Change type: reshaped
- Before: returned `RefusalReplayOutcome`.
- After: returns `RefusalReplayOutcome | ErasedReplayOutcome`. When nothing reads the children (the no-read path), an erased child is disclosed on the `RefusalReplayOutcome` and the reconstruction completes.
- Why: SEC-009; ruling 4.
- Migration: as for `replay`.

## ccf.replay.engine.ReplayOutcome

- Surface: ccf.replay.engine.ReplayOutcome
- Public surface: true
- Change type: reshaped
- Before: no erasure field.
- After: a new field `erased_content: tuple[ErasedContent, ...] = ()`. `RefusalReplayOutcome` gets the same field. It is hash-transparent at `()`, so an outcome with nothing erased renders as before.
- Why: SEC-009; design §5.2. A replay over erased retained content completes, and the erasure is disclosed on the result. The replay record is unchanged.
- Migration: none.
