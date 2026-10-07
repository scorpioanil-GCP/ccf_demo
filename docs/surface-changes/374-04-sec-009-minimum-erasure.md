# 374-04 — SEC-009: the minimum erasure mechanism

`D-IMPL-374` (4), ruling U1–U12 on the design's recommendations
(`docs/D-IMPL-367-ERASURE-DESIGN.md` §11). An erasure is a fact the fabric
records. The fabric does not perform it as a mutation. A human approves it
through the `ApprovalGate` of a workflow the deployment declares and the door
validates. Its entry goes into the deployment's durable, append-only erasure
index (fix round 1 C1). That index is declared at every store construction
site, with no default, and it is written BEFORE the record (write-ahead). The
record itself is an immutable `ccf.erasure-record`, filed under the
`ArtifactErase` capability, and it stays the only authority: every index entry
is validated against it, and a disagreement is withheld and audited (§8).

The decorating store refuses to serve erased content on every read.
`compose_erasure_consult` composes it at every store construction site (U12,
ruling 2). It is scoped to the reader's tenant (I6), and authorization runs
before the consult (ruling 1).

Three behavior changes apply to existing public names:

- `create_app`, `build_artifact_server`, `open_product`, `build_governed_resolver`, the in-process adapter's boot and the local CLI dependencies compose their store through `compose_erasure_consult`.
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

- **`McpArtifactStore` cannot be erased through (ruling (iii), the fallback taken).** The erasure door reads the stored class and tenant through the store's naming (`names_at`). `McpArtifactStore`, the §7.4 MCP client store, answers no naming, so an erasure requested through a door that files via it is refused by name: `class-unverifiable`. Reads through it are still consulted. A `names_at` resource on the MCP artifact server and the matching client method are NOT built this round.
- **Receivers that compose nothing.** `replay()`, `replay_refusal()` and `GrantBoundChildResolver` consult only if the store they are handed is composed (M5). The frozen `dr-01` example replays over a raw store. A child decision record that was erased still propagates `ErasedContentRefused` out of child admission (M4, not built).

- `RequestedAddress.retained_since` is the instant the minimum age is measured from. It is requester-declared and human-approved, not derived from the store, because the `ArtifactStoreProtocol` records no write instant.
- `ClassRetention.minimum_age` is in whole days.

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
- After: A decorator over any `ArtifactStoreProtocol`. `get` and `resolve_uri` consult the durable erasure index and refuse erased addresses. A tenant-scoped view (`scoped`) withholds only what its tenant erased, and carries the facts. A tenantless read withholds if any tenant erased the address, with reason and record address redacted (I6). Every entry is validated against its record at composition, and a disagreement is withheld and audited `index-unsupported` (§8). `exists` does not consult (U8). `put` passes through. Every store construction site composes it through `compose_erasure_consult` (U12, ruling 2). It forwards the inner store's naming introspection only (`root`, `names_at`, `versions`).
- Why: SEC-009; G4: one consult at the substrate read, covering every route the store serves.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.ErasureIndexEntry

- Surface: ccf.erasure.ErasureIndexEntry
- Public surface: true
- Change type: added
- Before: absent
- After: A contract for one erased address: record address, admitted reason, instant.
- Why: SEC-009; U7 (b): what the consult needs, and nothing of the subject.
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

## ccf.erasure.index.ErasureIndexEntry

- Surface: ccf.erasure.index.ErasureIndexEntry
- Public surface: true
- Change type: added
- Before: absent
- After: A contract for one erased address: record address, admitted reason, instant.
- Why: SEC-009; U7 (b): what the consult needs, and nothing of the subject.
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
- After: A decorator over any `ArtifactStoreProtocol`. `get` and `resolve_uri` consult the durable erasure index and refuse erased addresses. A tenant-scoped view (`scoped`) withholds only what its tenant erased, and carries the facts. A tenantless read withholds if any tenant erased the address, with reason and record address redacted (I6). Every entry is validated against its record at composition, and a disagreement is withheld and audited `index-unsupported` (§8). `exists` does not consult (U8). `put` passes through. Every store construction site composes it through `compose_erasure_consult` (U12, ruling 2). It forwards the inner store's naming introspection only (`root`, `names_at`, `versions`).
- Why: SEC-009; G4: one consult at the substrate read, covering every route the store serves.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf_runtime.erasure.ErasureDoor

- Surface: ccf_runtime.erasure.ErasureDoor
- Public surface: true
- Change type: added
- Before: absent
- After: The governed door. It takes a REQUIRED `index`.
  - `request` validates the declaration, then VERIFIES every requester-named address. Each must not already be erased, must be filed under the requesting tenant (I6), must have a stored class that is not the erasure record's and that equals the label (C2), must have a value at a subject key path that hashes to `subject_ref` (iv), and must carry no subject in a replay-input field (§7 `replay-input`). It judges retention against the STORED class and the pinned policy, then starts the deployment-declared one-gate workflow.
  - `complete` holds the presented approval to the RECORDED state and submission, and takes `requested_by` and `actor` from those (I2). It re-judges against the pinned and the newest policy and resumes. On completion it appends the index entries FIRST (write-ahead, I4), then files the record under the `ArtifactErase` capability (I3).
- Why: SEC-009; G6/U9: an erasure is written only on a recorded human approval.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf_runtime.erasure.door.ErasureDoor

- Surface: ccf_runtime.erasure.door.ErasureDoor
- Public surface: true
- Change type: added
- Before: absent
- After: The governed door. It takes a REQUIRED `index`.
  - `request` validates the declaration, then VERIFIES every requester-named address. Each must not already be erased, must be filed under the requesting tenant (I6), must have a stored class that is not the erasure record's and that equals the label (C2), must have a value at a subject key path that hashes to `subject_ref` (iv), and must carry no subject in a replay-input field (§7 `replay-input`). It judges retention against the STORED class and the pinned policy, then starts the deployment-declared one-gate workflow.
  - `complete` holds the presented approval to the RECORDED state and submission, and takes `requested_by` and `actor` from those (I2). It re-judges against the pinned and the newest policy and resumes. On completion it appends the index entries FIRST (write-ahead, I4), then files the record under the `ArtifactErase` capability (I3).
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
- After: THE composition helper. It wraps any store in `ErasureConsultingStore` over a REQUIRED declared erasure index and an audit log, optionally scoped to a tenant, and validates every entry against its record. It is idempotent on a store already composed over the same index, and refuses one composed over another (M1). `create_app`, `build_artifact_server`, `open_product`, `build_governed_resolver`, the in-process adapter's boot and the local CLI dependencies all compose through it.
- Why: SEC-009; ruling 2 on `D-IMPL-374` (4), "composed ALWAYS means every store construction site".
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.store.compose_erasure_consult

- Surface: ccf.erasure.store.compose_erasure_consult
- Public surface: true
- Change type: added
- Before: absent
- After: THE composition helper. It wraps any store in `ErasureConsultingStore` over a REQUIRED declared erasure index and an audit log, optionally scoped to a tenant, and validates every entry against its record. It is idempotent on a store already composed over the same index, and refuses one composed over another (M1). `create_app`, `build_artifact_server`, `open_product`, `build_governed_resolver`, the in-process adapter's boot and the local CLI dependencies all compose through it.
- Why: SEC-009; ruling 2 on `D-IMPL-374` (4), "composed ALWAYS means every store construction site".
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, and `ccf.erasure-record` under `Resume` in its `WriteKinds`.

## ccf.erasure.ErasureIndexUnavailable

- Surface: ccf.erasure.ErasureIndexUnavailable
- Public surface: true
- Change type: added
- Before: absent
- After: a `TypeError` raised at composition when the declared index is not an `ErasureIndexProtocol`, or when the store was already composed over a different index.
- Why: SEC-009; ruling 2. A store that cannot consult would serve erased content silently, so it is refused where an operator sees it.
- Migration: declare an index (`FileErasureIndex`, or `erasure_index_at(<store root>)`) at every store construction site.

## ccf.erasure.store.ErasureIndexUnavailable

- Surface: ccf.erasure.store.ErasureIndexUnavailable
- Public surface: true
- Change type: added
- Before: absent
- After: a `TypeError` raised at composition when the declared index is not an `ErasureIndexProtocol`, or when the store was already composed over a different index.
- Why: SEC-009; ruling 2. A store that cannot consult would serve erased content silently, so it is refused where an operator sees it.
- Migration: declare an index (`FileErasureIndex`, or `erasure_index_at(<store root>)`) at every store construction site.

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

## ccf_runtime.mcp.artifact_server.build_artifact_server

- Surface: ccf_runtime.mcp.artifact_server.build_artifact_server
- Public surface: true
- Change type: reshaped
- Before: `build_artifact_server(*, server_name, store, token_verifier, auth_settings, authorizer, entitlement_source, refusal_recorder, audit_log)`
- After: a new **required** keyword `erasure_index: ErasureIndexProtocol`, with no default. The server wraps `store` through `compose_erasure_consult`.
  - Every byte read goes through the wrapped store.
  - A governed record follows the authorization-first order (ruling 1).
  - An erased artifact on the client lane is returned as the erased reading: the not-found shell at `minimal`, and `erased-content` above it.
  - The naming resource still resolves through `store`, because it returns an address, never bytes (the U8 reasoning).
- Why: SEC-009; the coordinator's MCP ruling on `D-IMPL-374` (4). This server is the ArtifactStore's persistence transport (CLAUDE.md §7.4), so an erased artifact served over it is exactly the SEC-009 hole.
- Migration: pass `erasure_index=` with the deployment's durable index. The five in-tree call sites are updated.

## ccf_runtime.authz.delivery_boundary.govern_dereference

- Surface: ccf_runtime.authz.delivery_boundary.govern_dereference
- Public surface: true
- Change type: reshaped
- Before: no erasure handling.
- After:
  - Authorization runs first: the principal and grant holds read the record through the unconsulted inner store. Those bytes are used only for the rights check and never leave the door.
  - Only then does the consulted read run. An erased address becomes the erased reading at the entitled caller's level.
  - A new keyword `erased_client_read: ErasedContentRefused | None = None` lets the MCP artifact server render an erased client-lane artifact the same way. It can only ever produce a refusal, never bytes.
- Why: SEC-009; rulings 1 and MCP on `D-IMPL-374` (4).
- Migration: none.

## ccf.products.disclosure.TRANSLATED_AT_MINIMAL

- Surface: ccf.products.disclosure.TRANSLATED_AT_MINIMAL
- Public surface: true
- Change type: added
- Before: absent. Every kind crossed as itself at every level (`DisclosureDecision.external_kind == internal_kind`).
- After: `{"erased-content": "subject-unavailable"}`. At `minimal`, `disclose` renders an `erased-content` determination as the not-found shell, built from a fresh `SubjectUnavailableRefusal` that carries nothing of the determination. The replay record keeps the `erased-content` envelope, and the `DisclosureDecision` records `internal_kind = erased-content`, `external_kind = subject-unavailable`, with `kind` withheld.
- Why: SEC-009; fix round 1, I5 on `D-IMPL-374` (4). The wire must not disclose an erasure at `minimal`, and the audit trail must not record a false "nonexistent".
- Migration: none. A consumer at `minimal` sees exactly the not-found shell it saw before.

## ccf.erasure.ErasureIndexProtocol

- Surface: ccf.erasure.ErasureIndexProtocol
- Public surface: true
- Change type: added
- Before: absent
- After: The append-only durable erasure index, with four methods: `append(entry)`; `lookup(*, tenant_id, content_address)` (O(1)); `entries(*, tenant_id)`; and `tenants()`. It is REQUIRED at every store construction site.
- Why: SEC-009; fix round 1 C1, with rulings (i) and (ii). The artifact store is immutable by design, so the erasures in force live in an index of their own. The RECORD stays the only authority.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` under `ArtifactErase` in its `WriteKinds`, and a durable erasure index at every store construction site.

## ccf.erasure.index.ErasureIndexProtocol

- Surface: ccf.erasure.index.ErasureIndexProtocol
- Public surface: true
- Change type: added
- Before: absent
- After: The append-only durable erasure index, with four methods: `append(entry)`; `lookup(*, tenant_id, content_address)` (O(1)); `entries(*, tenant_id)`; and `tenants()`. It is REQUIRED at every store construction site.
- Why: SEC-009; fix round 1 C1, with rulings (i) and (ii). The artifact store is immutable by design, so the erasures in force live in an index of their own. The RECORD stays the only authority.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` under `ArtifactErase` in its `WriteKinds`, and a durable erasure index at every store construction site.

## ccf.erasure.FileErasureIndex

- Surface: ccf.erasure.FileErasureIndex
- Public surface: true
- Change type: added
- Before: absent
- After: The reference index. One append-only JSON-lines file per deployment, fsynced on every append. Entries are kept in memory, keyed by (tenant, address). It picks up lines that another process appended, and refuses a line that does not parse.
- Why: SEC-009; fix round 1 C1.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` under `ArtifactErase` in its `WriteKinds`, and a durable erasure index at every store construction site.

## ccf.erasure.index.FileErasureIndex

- Surface: ccf.erasure.index.FileErasureIndex
- Public surface: true
- Change type: added
- Before: absent
- After: The reference index. One append-only JSON-lines file per deployment, fsynced on every append. Entries are kept in memory, keyed by (tenant, address). It picks up lines that another process appended, and refuses a line that does not parse.
- Why: SEC-009; fix round 1 C1.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` under `ArtifactErase` in its `WriteKinds`, and a durable erasure index at every store construction site.

## ccf.erasure.ErasureIndexEntryExists

- Surface: ccf.erasure.ErasureIndexEntryExists
- Public surface: true
- Change type: added
- Before: absent
- After: A `ValueError` raised when a different entry is offered for an address the tenant has already erased. An entry is never replaced.
- Why: SEC-009; fix round 1 C1 and U6 (no un-erasure).
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` under `ArtifactErase` in its `WriteKinds`, and a durable erasure index at every store construction site.

## ccf.erasure.index.ErasureIndexEntryExists

- Surface: ccf.erasure.index.ErasureIndexEntryExists
- Public surface: true
- Change type: added
- Before: absent
- After: A `ValueError` raised when a different entry is offered for an address the tenant has already erased. An entry is never replaced.
- Why: SEC-009; fix round 1 C1 and U6 (no un-erasure).
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` under `ArtifactErase` in its `WriteKinds`, and a durable erasure index at every store construction site.

## ccf.erasure.ERASURE_INDEX_FILENAME

- Surface: ccf.erasure.ERASURE_INDEX_FILENAME
- Public surface: true
- Change type: added
- Before: absent
- After: The conventional file name `.erasure-index.jsonl`, beside a file-backed store. It is dot-prefixed and is not a content address, so the store's read path can never serve it.
- Why: SEC-009; fix round 1 C1.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` under `ArtifactErase` in its `WriteKinds`, and a durable erasure index at every store construction site.

## ccf.erasure.index.ERASURE_INDEX_FILENAME

- Surface: ccf.erasure.index.ERASURE_INDEX_FILENAME
- Public surface: true
- Change type: added
- Before: absent
- After: The conventional file name `.erasure-index.jsonl`, beside a file-backed store. It is dot-prefixed and is not a content address, so the store's read path can never serve it.
- Why: SEC-009; fix round 1 C1.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` under `ArtifactErase` in its `WriteKinds`, and a durable erasure index at every store construction site.

## ccf.erasure.erasure_index_at

- Surface: ccf.erasure.erasure_index_at
- Public surface: true
- Change type: added
- Before: absent
- After: Returns the conventional `FileErasureIndex` beside a file store root. The in-process and local-CLI sites use it with their declared root, and so do the examples.
- Why: SEC-009; fix round 1 C1: the in-process and local-CLI sites take the index path from their existing declared root.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` under `ArtifactErase` in its `WriteKinds`, and a durable erasure index at every store construction site.

## ccf.erasure.index.erasure_index_at

- Surface: ccf.erasure.index.erasure_index_at
- Public surface: true
- Change type: added
- Before: absent
- After: Returns the conventional `FileErasureIndex` beside a file store root. The in-process and local-CLI sites use it with their declared root, and so do the examples.
- Why: SEC-009; fix round 1 C1: the in-process and local-CLI sites take the index path from their existing declared root.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` under `ArtifactErase` in its `WriteKinds`, and a durable erasure index at every store construction site.

## ccf.erasure.INDEX_UNSUPPORTED

- Surface: ccf.erasure.INDEX_UNSUPPORTED
- Public surface: true
- Change type: added
- Before: absent
- After: The reason `index-unsupported`, carried by an address whose index entry is not supported by an agreeing erasure record. The address is still withheld, and the event is audited `erasure_index_unsupported`.
- Why: SEC-009; design §8 and fix round 1 I3: the record is the only authority.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` under `ArtifactErase` in its `WriteKinds`, and a durable erasure index at every store construction site.

## ccf.erasure.store.INDEX_UNSUPPORTED

- Surface: ccf.erasure.store.INDEX_UNSUPPORTED
- Public surface: true
- Change type: added
- Before: absent
- After: The reason `index-unsupported`, carried by an address whose index entry is not supported by an agreeing erasure record. The address is still withheld, and the event is audited `erasure_index_unsupported`.
- Why: SEC-009; design §8 and fix round 1 I3: the record is the only authority.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` under `ArtifactErase` in its `WriteKinds`, and a durable erasure index at every store construction site.

## ccf.erasure.ErasureSubjectLocator

- Surface: ccf.erasure.ErasureSubjectLocator
- Public surface: true
- Change type: added
- Before: absent
- After: A Protocol: `addresses(*, tenant_id, subject_class, subject_ref)`. It has NO reference implementation this phase. Enumerating where a subject appears is the deployment's job; the erasure door VERIFIES every address a request names.
- Why: SEC-009; ruling (iv) on §4.1.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` under `ArtifactErase` in its `WriteKinds`, and a durable erasure index at every store construction site.

## ccf.erasure.contracts.ErasureSubjectLocator

- Surface: ccf.erasure.contracts.ErasureSubjectLocator
- Public surface: true
- Change type: added
- Before: absent
- After: A Protocol: `addresses(*, tenant_id, subject_class, subject_ref)`. It has NO reference implementation this phase. Enumerating where a subject appears is the deployment's job; the erasure door VERIFIES every address a request names.
- Why: SEC-009; ruling (iv) on §4.1.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` under `ArtifactErase` in its `WriteKinds`, and a durable erasure index at every store construction site.

## ccf.erasure.RetentionReasonCode

- Surface: ccf.erasure.RetentionReasonCode
- Public surface: true
- Change type: added
- Before: absent
- After: The closed `Literal` of retention codes, now including `replay-input`. `RetentionDecision.reason_code` is typed with it.
- Why: SEC-009; fix round 1 M2 and §7 `replay-input`.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` under `ArtifactErase` in its `WriteKinds`, and a durable erasure index at every store construction site.

## ccf.erasure.contracts.RetentionReasonCode

- Surface: ccf.erasure.contracts.RetentionReasonCode
- Public surface: true
- Change type: added
- Before: absent
- After: The closed `Literal` of retention codes, now including `replay-input`. `RetentionDecision.reason_code` is typed with it.
- Why: SEC-009; fix round 1 M2 and §7 `replay-input`.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` under `ArtifactErase` in its `WriteKinds`, and a durable erasure index at every store construction site.

## ccf.products.resolver.build_governed_resolver

- Surface: ccf.products.resolver.build_governed_resolver
- Public surface: true
- Change type: reshaped
- Before: no erasure index.
- After: a new **required** keyword `erasure_index: ErasureIndexProtocol`, with no default. The selected store, whether supplied or default, is composed with the erasure consult over it and scoped to the fabric's tenant.
- Why: SEC-009; fix round 1 C1 on `D-IMPL-374` (4). A composition without a declared durable index refuses by name.
- Migration: declare the deployment's index. Use `FileErasureIndex(path)`, or `erasure_index_at(<file store root>)` for a file store. Every in-tree caller is updated, including the examples, under D-IMPL-261's deliberate-surface-change rule.

## ccf.products.product.OpenedProduct

- Surface: ccf.products.product.OpenedProduct
- Public surface: true
- Change type: reshaped
- Before: no erasure index.
- After: a new required constructor keyword `erasure_index`, and an `erasure_index` attribute. `open_product` derives the index from its declared scratch root (`erasure_index_at`), composes its store scoped to the deployment's tenant, and `build_arguments` hands the index to every resolver it builds.
- Why: SEC-009; fix round 1 C1 on `D-IMPL-374` (4). A composition without a declared durable index refuses by name.
- Migration: declare the deployment's index. Use `FileErasureIndex(path)`, or `erasure_index_at(<file store root>)` for a file store. Every in-tree caller is updated, including the examples, under D-IMPL-261's deliberate-surface-change rule.

## ccf_runtime.http_api.dependencies.ApiDependencies

- Surface: ccf_runtime.http_api.dependencies.ApiDependencies
- Public surface: true
- Change type: reshaped
- Before: no erasure index.
- After: a new **required** field `erasure_index: ErasureIndexProtocol`, with no default. `create_app` composes `artifact_store` over it, together with `control_plane.audit_log`.
- Why: SEC-009; fix round 1 C1 on `D-IMPL-374` (4). A composition without a declared durable index refuses by name.
- Migration: declare the deployment's index. Use `FileErasureIndex(path)`, or `erasure_index_at(<file store root>)` for a file store. Every in-tree caller is updated, including the examples, under D-IMPL-261's deliberate-surface-change rule.

## ccf.replay.engine.ReplayOutcome

- Surface: ccf.replay.engine.ReplayOutcome
- Public surface: true
- Change type: reshaped
- Before: no erasure field.
- After: a new field `erased_content: tuple[ErasedContent, ...] = ()`. `RefusalReplayOutcome` gets the same field. It is hash-transparent at `()`, so an outcome with nothing erased renders as before.
- Why: SEC-009; design §5.2. A replay over erased retained content completes, and the erasure is disclosed on the result. The replay record is unchanged.
- Migration: none.
