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

- **A third-party store with no `names_at` cannot be erased through.** The door refuses by name, `class-unverifiable`, because it reads an address's stored class and tenant through the store's naming. The §7.4 reference store is NOT excluded: the MCP artifact server answers names through a resource, and `McpArtifactStore.names_at` reads it (ruling 2).
- **An attacker with write access to the index file can un-erase its tail; file modes and the deployment's filesystem controls are the mitigation.** The file index is hash-chained, so an edited, reordered or removed line in the middle is refused at boot (`ErasureIndexCorrupt`, fail closed), and it opens with `O_NOFOLLOW` under an owner-only mode (0600 file, 0700 parent, refused by name otherwise). A chain cannot show that its last lines were cut off, so a truncated tail reads as a shorter, valid index (fix round 2, (a)).
- **The approval is signature-bound, and verified again on every composition; an in-memory HITL transport still cannot resume a PENDING approval across a restart.** An erasure requires a SIGNED human approval: the door refuses, by name, an approval that is unsigned (`approval-unsigned`) or whose signature does not verify (`approval-signature-invalid`). Before the index append it files the approval as an immutable `ccf.erasure-approval` that carries the signed HITL attestation verbatim (claim set, signature, key id) and the pinned HITL policy version; its content address is the `approval_ref` on the record and the entry. The consult verifies that signature against the key the pinned HITL policy declares for the approver, resolved through its composed Control Plane, and requires the signed claims to name this request's gate, this tenant, the gate's state hash, the approver and an approving verdict; anything else is `index-unsupported` and audited (fix round 4). Holding `ArtifactErase` lets a requester file an approval artifact, not produce a signature the pinned policy accepts. The check survives a restart. A gate still PENDING in `InMemoryHitlTransport` does not: that is the transport's limit, not the record's.
- **The approval's instant is the human's.** `ErasureApproval.acted_at` is the signed attestation's `issued_at`, so a retry re-files the same approval and leaves no orphan.
- **The check is as strong as the custody of three things: the erasure door's private signing key, each tenant's HITL policy key, and the approvers' private keys.** What each custody failure still allows, as measured:
  - A holder of the door's private key can sign a record naming any requester, and the consult takes that `requested_by` as the door's statement (fix round 5, R2).
  - A party who can register a new version under a tenant's declared HITL policy key can pin a key it holds for an erasure officer's subject id, and approve as that officer.
  - A holder of an erasure officer's private key can approve while that officer's pinned policy version is current.
  - What fix round 4 left open and fix round 5 closed, each now measured `index-unsupported` in `tests/erasure/test_sec009_fix5_rulings.py`: a filer who writes another name into `requested_by` and approves his own request (b1; only a door-signed record verifies, R2); an approver pinned in the HITL policy who names another registered workflow, in the same tenant or another, whose gate policy lists him (b2, b3; the workflow and its tenant are fixed at composition and the policy is the declared workflow's erasure gate's, R1). An approval pinning any HITL policy key other than the tenant's declared one refuses by name (ruling 1).
  - A deployment whose HITL transport or erasure door signs under an algorithm other than the SDK's reference detached JWS passes its own `identity_provider` to `compose_erasure_consult` and the door; otherwise its approvals and records do not verify and fail closed. **An adopter-supplied identity provider that verifies nothing accepts everything; that is the adopter's trust choice** (ruling 6) — door signatures included.
- **The signed instant is the signer's claim.** Revocation (ruling 4) refuses a signature dated after the pinned version's supersession, but nothing anchors `issued_at` to a clock the signer does not control: a holder of a dropped key who backdates a signature to before the supersession still verifies under the old version. The transport's freshness window applies at the door, not to an artifact filed around it.
- **The effectivity window is read from the Control Plane's audit plane, and only its upper bound is enforced.** Ruling 4 defines the window from the version's registration instant to its supersession. The reference Control Plane is in-memory and re-registered at every boot, so the registration instant of every version is the boot instant and a lower bound would refuse every approval made before the last restart — measured in `tests/erasure/test_sec009_fix4_rulings.py` (the restart whose clock is later). The supersession bound is enforced; the lower bound is not, and that deviation is reported for a ruling rather than built.
- **The in-process adapter boots its own registry.** It composes with the erasure authority its `binding.yaml` declares (`erasure_authority:`; `{}` declares none). Its Control Plane holds only what its `ccf_config.yaml` registers, and `ccf.hitl-policy`, `ccf.approval-policy` and the erasure workflow definition are not manifest-addressable, so a genuine erasure consulted through the in-process adapter reads `index-unsupported` until the deployment registers its HITL policy, approval policy and erasure workflow into that booted registry by its own code. The content stays withheld either way.
- **A torn index line fails closed and is repaired by hand.** A process killed mid-append can leave a partial line that the next append merges into; the index is then refused as `ErasureIndexCorrupt` and every read under it is withheld. The repair procedure (evidence copy, truncate to the longest verifying prefix, restore the suffix before readers start) is in the `ccf.erasure.index` module docstring and §4.9 of the security deployment page. The SDK ships no repair tool.
- **A retry needs the same authorization.** The record names the erase decision id, and the write-ahead entries pin the record's address, so a retry of a completion under a FRESH erase authorization is refused as `retry-mismatch`. Present the same request and the same erase decision. A retry reuses the door signature its prior attempt appended — an ES256 signature is not deterministic, and the index takes only an identical entry again — after verifying it over the record the retry rebuilds; a prior entry whose signature does not verify is refused as `retry-mismatch`.
- **One erasure authority per tenant, declared at every site** (fix round 5, R4). `ErasureTrust` maps each tenant that may erase to its `ErasureAuthority`; the record's tenant selects it, and a tenant with no authority reads `index-unsupported` (`erasure-tenant-undeclared`). A multi-tenant site (the HTTP app, the MCP artifact server, a local-CLI embedder) declares one authority per erasing tenant; a single-tenant site declares one. The `--local` CLI arm, `tools/dump_openapi.py` and every example declare none, because none runs an erasure door. The erasure door is single-tenant: it takes one authority, and its HITL transport must be bound to that authority's HITL policy key, or the door refuses at construction (R5).
- **The validation cache is keyed by the identity provider instance** (fix round 5, R3), with the composed trust and the Control Plane's policy head: a verdict judged under one provider — a do-nothing one, say — is never served to a site composed with another. The provider is held strongly in the memo entry. The reference verifier is one shared instance, so compositions that declare no provider share the cache. `policy_head` digests each registration's key, version and instant, not its content: two Control Planes with an identical registration history and different content would share a head (not reproduced).
- **A refused names read is not told apart from an outage.** When the MCP names resource refuses a governed address, the client receives the refusal shell and reports `McpServerUnreachable`, and the door refuses `class-unverifiable`. That fails closed, but the caller cannot tell a refusal from an unreachable server.
- **Receivers that compose nothing.** `replay()`, `replay_refusal()` and `GrantBoundChildResolver` consult only if the store they are handed is composed (M5). The frozen `dr-01` example replays over a raw store. A child decision record that was erased still propagates `ErasedContentRefused` out of child admission (M4, not built).

- `RequestedAddress.retained_since` is the instant the minimum age is measured from. It is requester-declared and human-approved, not derived from the store, because the `ArtifactStoreProtocol` records no write instant.
- `ClassRetention.minimum_age` is in whole days.

The door requires three things: the distinct `artifact.erase` capability for
exactly the request, the workflow's `Execute`/`Resume` capabilities, and the
recorded human approval (ruling 3).

**Fix round 4, rulings 1–6: the requester never chooses the trust root.** The
re-review measured that the consult trusted whatever `key@version` the
requester's approval artifact named, so a policy the forger registered, a
policy in another tenant's key space, and self-approval all verified. Now:

1. **The HITL policy key is fixed at composition.** `compose_erasure_consult`,
   every site that calls it (`create_app` through `ApiDependencies`,
   `build_artifact_server`, `open_product`, `build_governed_resolver`, the
   in-process adapter through its binding document, the local CLI
   dependencies) and `ErasureDoor` take the deployment's HITL policy key —
   the same key the HITL transport is bound to; since fix round 5 it travels
   in the per-tenant `ErasureTrust` (below). The consult refuses, by name, an
   approval pinning any other key (`approval-policy-key-mismatch`); a key
   outside its tenant is now refused at composition, because an
   `ErasureAuthority`'s HITL key lies under its own tenant, so round 4's
   `approval-policy-tenant-mismatch` branch is gone. The requester's artifact
   may name the version, never the key.
2. **Approver ≠ requester, and eligible.** The consult refuses an approver who
   is the record's requester (`approver-is-requester`) and one who is not
   eligible under the approval policy, resolved at its exact version
   (`approver-not-eligible`) — the transport's door rule
   (`check_approver_eligibility`), applied again at the consult. As round 4
   built it, the requester and the policy were read from the record a filer
   writes, and the re-review measured both defeated (b1, b2); fix round 5
   binds them (R1, R2, below).
3. **The gate is the workflow definition's.** The consult resolves the
   definition and requires `approval.gate` to be one of its gates
   (`approval-workflow-unresolvable`, `approval-gate-unknown`). As round 4
   built it, the definition was whichever one the approval named, in any
   tenant, and the re-review measured that defeated (b2, b3); fix round 5
   fixes it at composition (R1, below).
4. **Revocation.** The signed `issued_at` must precede the pinned HITL policy
   version's supersession — the instant the Control Plane's audit plane
   records the next version's registration; the current version's window is
   open-ended. A signature dated after supersession, under a version whose key
   was since dropped, refuses by name (`approval-policy-superseded`); an
   approval made while that version was current stays valid (replay
   determinism). The validation cache — the per-store verdicts and the
   per-head memo — is keyed by the Control Plane's **policy head**
   (`policy_head`, the digest of its registration history), so any
   registration re-judges every cached verdict; never by a Control Plane
   object's identity.
5. **No fresh-registry fallback.** `open_product` takes the deployment's
   Control Plane, required, and refuses `None` by name; `build_governed_resolver`
   refuses a Control Plane with no pinned-read surface; and re-composing an
   already composed store with a different Control Plane, identity provider or
   trust root refuses by name (`ErasureCompositionRefused`) instead of
   silently keeping the first.
6. An adopter-supplied identity provider that verifies nothing accepts
   everything; that is the adopter's trust choice.

**Fix round 5, rulings R1–R5: the record is door-signed; the erasure workflow,
its tenant and the door key are fixed at composition.** The re-review of round
4 measured three forgeries SUPPORTED, because rulings 2 and 3 read fields a
filer writes — the record's `requested_by` and `approval_policy_ref` and the
approval's `workflow_definition_hash`: b1, an eligible officer who is the real
requester writes another name into `requested_by` and approves himself; b2 and
b3, an approver pinned in the HITL policy but no erasure officer names another
registered workflow, of the same tenant or another, whose gate policy lists
him. It also measured the validation cache serving a do-nothing provider's
SUPPORTED to a real-verifier site. Now:

1. **R1 — the erasure workflow is fixed at composition.**
   `compose_erasure_consult` and every site that calls it (`create_app`
   through `ApiDependencies.erasure_trust`, `build_artifact_server`,
   `open_product`, `build_governed_resolver`, the in-process adapter through
   `binding.yaml`'s `erasure_authority`, the local CLI dependencies) take an
   `ErasureTrust`: per tenant, an `ErasureAuthority` naming the erasure
   workflow definition's content hash and its tenant, beside the HITL policy
   key and the door key. An approval for another workflow or in another tenant
   refuses by name (`approval-workflow-mismatch`, `approval-tenant-mismatch`).
   The declared workflow is resolved from the Control Plane by its hash —
   content-verified, in its tenant (`approval-workflow-unresolvable`); the
   approval's gate must be its ERASURE gate, an approval gate whose approve
   route completes the workflow (`approval-gate-unknown`); and the approver is
   judged eligible under THAT gate's approval policy at its pinned version.
   `ErasureRecord.approval_policy_ref` is DELETED — no record field names the
   policy — and `approval-gate-policy-mismatch`, which compared against it, is
   gone with it. The door takes the same authority and runs no other workflow
   (`workflow-not-declared`).
2. **R2 — the record is door-signed.** The erasure door signs the canonical
   bytes of every `ErasureRecord` it files (`sign_erasure_record`) with a
   deployment-held key that requesters never hold; the authority declares its
   public half, and private material is refused by name. The consult verifies
   the door signature over the record's stored bytes before it reads any
   field (`verify_erasure_entry`): a record without a verifying door signature
   is `index-unsupported` and audited, so `requested_by` is the starter the
   engine recorded — what the door observed — and approver ≠ requester and
   eligibility are judged against it. The signature asserts, in its protected
   header, that it signs an erasure record (`DOOR_SIGNATURE_ASSERTION`). It
   travels in every `ErasureIndexEntry` (`door_signature`, `door_key_id`)
   rather than in the record artifact, because an ES256 signature is not
   deterministic and a write-ahead retry must re-append identical entries; a
   retry reuses its prior attempt's signature, verified. The door refuses, at
   construction, a signing key that does not verify under the declared door
   key.
3. **R3 — the validation cache is keyed by the identity provider instance**,
   held strongly in the memo entry, and by the composed trust: a do-nothing
   provider's verdict never serves a real-verifier site.
4. **R4 — per tenant.** The record's tenant selects its authority; a tenant
   with no authority refuses by name (`erasure-tenant-undeclared`), read
   `index-unsupported`. A multi-tenant site declares one authority per erasing
   tenant.
5. **R5.** `approval-policy-window-unknown` is exercised by a test; the door
   refuses, at construction, a HITL transport bound to any key but its
   authority's (`InMemoryHitlTransport.hitl_policy_key`, read-only); and this
   fragment and §4.9 of the security deployment page say what was measured.

## ccf.erasure.ClassRetention

- Surface: ccf.erasure.ClassRetention
- Public surface: true
- Change type: added
- Before: absent
- After: A contract for one artifact class's retention and hold policy: `erasable` (default False), `severity_exempt`, the closed `reasons`, active `holds`, and `minimum_age` in whole days, which is required and has no default (U10).
- Why: SEC-009; G7 default refuse; U10 rules the minimum age present on the contract with no SDK default.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.ERASURE_RECORD_CLASS

- Surface: ccf.erasure.ERASURE_RECORD_CLASS
- Public surface: true
- Change type: added
- Before: absent
- After: The constant `ccf.erasure-record`, the class an erasure record is filed under.
- Why: SEC-009; G3: the erasure fact is an immutable artifact filed through the store's one write verb.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.ERASURE_SUBJECT_DECLARATION

- Surface: ccf.erasure.ERASURE_SUBJECT_DECLARATION
- Public surface: true
- Change type: added
- Before: absent
- After: The `ArtifactClass` `ccf.erasure-subject-declaration`. Adopter-registered and not manifest-addressable.
- Why: SEC-009; G1: what a subject is, declared by the deployment.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.ErasedAddress

- Surface: ccf.erasure.ErasedAddress
- Public surface: true
- Change type: added
- Before: absent
- After: A contract for one erased artifact on a record: address, class, key paths, `matched` (presence only), and `scope`, which is `whole` this phase (U5).
- Why: SEC-009; G3: design §2.3 record shape.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.ErasedContentRefused

- Surface: ccf.erasure.ErasedContentRefused
- Public surface: true
- Change type: added
- Before: absent
- After: An `ArtifactStoreError` the decorating store raises on a read of an erased address. It carries the record address, the reason and the instant, and nothing of the subject. It is not an `ArtifactNotFound` and not a `LookupError`.
- Why: SEC-009; G4/G5: an erasure is a recorded decision, not an absence.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.ErasureConsultingStore

- Surface: ccf.erasure.ErasureConsultingStore
- Public surface: true
- Change type: added
- Before: absent
- After: A decorator over any `ArtifactStoreProtocol`. `get` and `resolve_uri` consult the durable erasure index and refuse erased addresses. A tenant-scoped view (`scoped`) withholds only what its tenant erased, and carries the facts. A tenantless read withholds if any tenant erased the address, with reason and record address redacted (I6). Every entry is validated against its record at composition, and a disagreement is withheld and audited `index-unsupported` (§8). `exists` does not consult (U8). `put` passes through. Every store construction site composes it through `compose_erasure_consult` (U12, ruling 2). It forwards the inner store's naming introspection only (`root`, `names_at`, `versions`). It verifies the erasure door's signature over each record before reading it, then each approval's signed HITL attestation, through the Control Plane it was composed with, readable as `control_plane`, against the per-tenant `ErasureTrust` it was composed with, readable as `erasure_trust` (fix round 5), with the identity provider as declared, readable as `identity_provider` (fix round 4). Its verdicts are keyed by the Control Plane's policy head, so a registration re-judges them (ruling 4), and the global validation memo is also keyed by the composed trust and the identity provider instance (fix round 5, R3).
- Why: SEC-009; G4: one consult at the substrate read, covering every route the store serves.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.ErasureIndexEntry

- Surface: ccf.erasure.ErasureIndexEntry
- Public surface: true
- Change type: added
- Before: absent
- After: A contract for one erased address within one tenant: the record address, the request, the hashed subject, the approval reference, the admitted reason and instant, and the erasure door's detached signature over the record (`door_signature`, `door_key_id`; fix round 5, R2).
- Why: SEC-009; U7 (b): what the consult needs, and nothing of the subject.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.ErasureRecord

- Surface: ccf.erasure.ErasureRecord
- Public surface: true
- Change type: added
- Before: absent
- After: The immutable erasure fact: tenant, record id, subject class, salted `subject_ref`, addresses, `erased_at`, approver `actor`, `requested_by`, authorizing decision, approval reference, retention decision, reason, legal basis. Door-signed: the erasure door signs its canonical bytes and the consult verifies that before reading it (fix round 5, R2). It names no approval policy (R1 deleted `approval_policy_ref`).
- Why: SEC-009; G3; it can be asserted and never retracted (U6).
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.ErasureRequest

- Surface: ccf.erasure.ErasureRequest
- Public surface: true
- Change type: added
- Before: absent
- After: What a requester asks to erase. Its content hash `request_id` is the approval workflow's execution id.
- Why: SEC-009; U9: the human approves exactly this request.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.ErasureSubjectClass

- Surface: ccf.erasure.ErasureSubjectClass
- Public surface: true
- Change type: added
- Before: absent
- After: One declared subject class: `class_id`, `key_paths`, `artifact_classes`, `identifier_kind`, and `subject_ref_salt`. A key path that reaches a replay input is refused (U2). A `principal` subject is refused (U1).
- Why: SEC-009; G1/G2 with U1, U2 and U4.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.ErasureSubjectDeclaration

- Surface: ccf.erasure.ErasureSubjectDeclaration
- Public surface: true
- Change type: added
- Before: absent
- After: A versioned artifact listing a tenant's subject classes.
- Why: SEC-009; G1.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.LegalHold

- Surface: ccf.erasure.LegalHold
- Public surface: true
- Change type: added
- Before: absent
- After: A contract for one active legal hold, matched by salted subject refs or by addresses.
- Why: SEC-009; G7: a matching hold refuses erasure, by hold id.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.REPLAY_INPUT_PATHS

- Surface: ccf.erasure.REPLAY_INPUT_PATHS
- Public surface: true
- Change type: added
- Before: absent
- After: The tuple of Decision Replay record paths that are replay inputs.
- Why: SEC-009; U2: the SDK's own field names, a mechanism constant; no subject key may reach them.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.RETENTION_HOLD_POLICY

- Surface: ccf.erasure.RETENTION_HOLD_POLICY
- Public surface: true
- Change type: added
- Before: absent
- After: The `ArtifactClass` `ccf.retention-hold-policy`.
- Why: SEC-009; G7.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.RETENTION_REASON_CODES

- Surface: ccf.erasure.RETENTION_REASON_CODES
- Public surface: true
- Change type: added
- Before: absent
- After: The judgment's closed code vocabulary (`class-absent`, `not-erasable`, `severity-exempt`, `legal-hold`, `reason-unknown`, `under-minimum-age`, `policy-unresolvable`, `admitted`).
- Why: SEC-009; G7: a structured audit answer, never a subject identifier.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.RequestedAddress

- Surface: ccf.erasure.RequestedAddress
- Public surface: true
- Change type: added
- Before: absent
- After: One address a request names, with its class and a requester-declared, human-approved `retained_since`.
- Why: SEC-009; U10: the store's Protocol records no write instant, so the age is declared and approved.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.RetentionDecision

- Surface: ccf.erasure.RetentionDecision
- Public surface: true
- Change type: added
- Before: absent
- After: The judgment's audit answer: `policy_ref`, `verdict`, `reason_code`, `hold_id`, `address`.
- Why: SEC-009; G7.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.RetentionHoldPolicy

- Surface: ccf.erasure.RetentionHoldPolicy
- Public surface: true
- Change type: added
- Before: absent
- After: A versioned artifact mapping artifact classes to `ClassRetention`. An absent class refuses.
- Why: SEC-009; G7 default refuse.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.judge_retention

- Surface: ccf.erasure.judge_retention
- Public surface: true
- Change type: added
- Before: absent
- After: A pure, fail-closed judgment of a request against a policy at an injected instant.
- Why: SEC-009; G7.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.subject_ref_for

- Surface: ccf.erasure.subject_ref_for
- Public surface: true
- Change type: added
- Before: absent
- After: Returns `sha256(salt || 0x00 || identifier)` under the declared class's salt.
- Why: SEC-009; U4: the raw identifier never enters the fabric.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.contracts.ClassRetention

- Surface: ccf.erasure.contracts.ClassRetention
- Public surface: true
- Change type: added
- Before: absent
- After: A contract for one artifact class's retention and hold policy: `erasable` (default False), `severity_exempt`, the closed `reasons`, active `holds`, and `minimum_age` in whole days, which is required and has no default (U10).
- Why: SEC-009; G7 default refuse; U10 rules the minimum age present on the contract with no SDK default.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.contracts.ERASURE_RECORD_CLASS

- Surface: ccf.erasure.contracts.ERASURE_RECORD_CLASS
- Public surface: true
- Change type: added
- Before: absent
- After: The constant `ccf.erasure-record`, the class an erasure record is filed under.
- Why: SEC-009; G3: the erasure fact is an immutable artifact filed through the store's one write verb.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.contracts.ERASURE_SUBJECT_DECLARATION

- Surface: ccf.erasure.contracts.ERASURE_SUBJECT_DECLARATION
- Public surface: true
- Change type: added
- Before: absent
- After: The `ArtifactClass` `ccf.erasure-subject-declaration`. Adopter-registered and not manifest-addressable.
- Why: SEC-009; G1: what a subject is, declared by the deployment.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.contracts.ErasedAddress

- Surface: ccf.erasure.contracts.ErasedAddress
- Public surface: true
- Change type: added
- Before: absent
- After: A contract for one erased artifact on a record: address, class, key paths, `matched` (presence only), and `scope`, which is `whole` this phase (U5).
- Why: SEC-009; G3: design §2.3 record shape.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.contracts.ErasureRecord

- Surface: ccf.erasure.contracts.ErasureRecord
- Public surface: true
- Change type: added
- Before: absent
- After: The immutable erasure fact: tenant, record id, subject class, salted `subject_ref`, addresses, `erased_at`, approver `actor`, `requested_by`, authorizing decision, approval reference, retention decision, reason, legal basis. Door-signed: the erasure door signs its canonical bytes and the consult verifies that before reading it (fix round 5, R2). It names no approval policy (R1 deleted `approval_policy_ref`).
- Why: SEC-009; G3; it can be asserted and never retracted (U6).
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.contracts.ErasureRequest

- Surface: ccf.erasure.contracts.ErasureRequest
- Public surface: true
- Change type: added
- Before: absent
- After: What a requester asks to erase. Its content hash `request_id` is the approval workflow's execution id.
- Why: SEC-009; U9: the human approves exactly this request.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.contracts.ErasureSubjectClass

- Surface: ccf.erasure.contracts.ErasureSubjectClass
- Public surface: true
- Change type: added
- Before: absent
- After: One declared subject class: `class_id`, `key_paths`, `artifact_classes`, `identifier_kind`, and `subject_ref_salt`. A key path that reaches a replay input is refused (U2). A `principal` subject is refused (U1).
- Why: SEC-009; G1/G2 with U1, U2 and U4.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.contracts.ErasureSubjectDeclaration

- Surface: ccf.erasure.contracts.ErasureSubjectDeclaration
- Public surface: true
- Change type: added
- Before: absent
- After: A versioned artifact listing a tenant's subject classes.
- Why: SEC-009; G1.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.contracts.LegalHold

- Surface: ccf.erasure.contracts.LegalHold
- Public surface: true
- Change type: added
- Before: absent
- After: A contract for one active legal hold, matched by salted subject refs or by addresses.
- Why: SEC-009; G7: a matching hold refuses erasure, by hold id.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.contracts.REPLAY_INPUT_PATHS

- Surface: ccf.erasure.contracts.REPLAY_INPUT_PATHS
- Public surface: true
- Change type: added
- Before: absent
- After: The tuple of Decision Replay record paths that are replay inputs.
- Why: SEC-009; U2: the SDK's own field names, a mechanism constant; no subject key may reach them.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.contracts.RETENTION_HOLD_POLICY

- Surface: ccf.erasure.contracts.RETENTION_HOLD_POLICY
- Public surface: true
- Change type: added
- Before: absent
- After: The `ArtifactClass` `ccf.retention-hold-policy`.
- Why: SEC-009; G7.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.contracts.RETENTION_REASON_CODES

- Surface: ccf.erasure.contracts.RETENTION_REASON_CODES
- Public surface: true
- Change type: added
- Before: absent
- After: The judgment's closed code vocabulary (`class-absent`, `not-erasable`, `severity-exempt`, `legal-hold`, `reason-unknown`, `under-minimum-age`, `policy-unresolvable`, `admitted`).
- Why: SEC-009; G7: a structured audit answer, never a subject identifier.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.contracts.RequestedAddress

- Surface: ccf.erasure.contracts.RequestedAddress
- Public surface: true
- Change type: added
- Before: absent
- After: One address a request names, with its class and a requester-declared, human-approved `retained_since`.
- Why: SEC-009; U10: the store's Protocol records no write instant, so the age is declared and approved.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.contracts.RetentionDecision

- Surface: ccf.erasure.contracts.RetentionDecision
- Public surface: true
- Change type: added
- Before: absent
- After: The judgment's audit answer: `policy_ref`, `verdict`, `reason_code`, `hold_id`, `address`.
- Why: SEC-009; G7.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.contracts.RetentionHoldPolicy

- Surface: ccf.erasure.contracts.RetentionHoldPolicy
- Public surface: true
- Change type: added
- Before: absent
- After: A versioned artifact mapping artifact classes to `ClassRetention`. An absent class refuses.
- Why: SEC-009; G7 default refuse.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.contracts.judge_retention

- Surface: ccf.erasure.contracts.judge_retention
- Public surface: true
- Change type: added
- Before: absent
- After: A pure, fail-closed judgment of a request against a policy at an injected instant.
- Why: SEC-009; G7.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.contracts.subject_ref_for

- Surface: ccf.erasure.contracts.subject_ref_for
- Public surface: true
- Change type: added
- Before: absent
- After: Returns `sha256(salt || 0x00 || identifier)` under the declared class's salt.
- Why: SEC-009; U4: the raw identifier never enters the fabric.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.index.ErasureIndexEntry

- Surface: ccf.erasure.index.ErasureIndexEntry
- Public surface: true
- Change type: added
- Before: absent
- After: A contract for one erased address within one tenant: the record address, the request, the hashed subject, the approval reference, the admitted reason and instant, and the erasure door's detached signature over the record (`door_signature`, `door_key_id`; fix round 5, R2).
- Why: SEC-009; U7 (b): what the consult needs, and nothing of the subject.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.store.ErasedContentRefused

- Surface: ccf.erasure.store.ErasedContentRefused
- Public surface: true
- Change type: added
- Before: absent
- After: An `ArtifactStoreError` the decorating store raises on a read of an erased address. It carries the record address, the reason and the instant, and nothing of the subject. It is not an `ArtifactNotFound` and not a `LookupError`.
- Why: SEC-009; G4/G5: an erasure is a recorded decision, not an absence.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.store.ErasureConsultingStore

- Surface: ccf.erasure.store.ErasureConsultingStore
- Public surface: true
- Change type: added
- Before: absent
- After: A decorator over any `ArtifactStoreProtocol`. `get` and `resolve_uri` consult the durable erasure index and refuse erased addresses. A tenant-scoped view (`scoped`) withholds only what its tenant erased, and carries the facts. A tenantless read withholds if any tenant erased the address, with reason and record address redacted (I6). Every entry is validated against its record at composition, and a disagreement is withheld and audited `index-unsupported` (§8). `exists` does not consult (U8). `put` passes through. Every store construction site composes it through `compose_erasure_consult` (U12, ruling 2). It forwards the inner store's naming introspection only (`root`, `names_at`, `versions`). It verifies the erasure door's signature over each record before reading it, then each approval's signed HITL attestation, through the Control Plane it was composed with, readable as `control_plane`, against the per-tenant `ErasureTrust` it was composed with, readable as `erasure_trust` (fix round 5), with the identity provider as declared, readable as `identity_provider` (fix round 4). Its verdicts are keyed by the Control Plane's policy head, so a registration re-judges them (ruling 4), and the global validation memo is also keyed by the composed trust and the identity provider instance (fix round 5, R3).
- Why: SEC-009; G4: one consult at the substrate read, covering every route the store serves.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf_runtime.erasure.ErasureDoor

- Surface: ccf_runtime.erasure.ErasureDoor
- Public surface: true
- Change type: added
- Before: absent
- After: The governed door. It takes a REQUIRED `index`; a REQUIRED `authority` (fix round 5), the tenant's `ErasureAuthority` — its HITL policy key, which its `transport` must be bound to or construction refuses by name (R5), its erasure workflow, the only workflow it runs (`workflow-not-declared`, R1), and the door's public key; a REQUIRED `door_signer` and `door_key_id`, the door's private signing key, which must verify under the declared door key or construction refuses by name (R2); and an optional `identity_provider` that verifies signatures (`None`: the SDK's reference detached-JWS verifier). It refuses, by name, an approval for another workflow or tenant (`approval-workflow-mismatch`, `approval-tenant-mismatch`), that is unsigned (`approval-unsigned`), that pins another HITL policy key (`approval-policy-key-mismatch`), whose pinned HITL policy does not resolve (`approval-policy-unresolvable`), whose signature does not verify under the key that policy declares for the approver (`approval-signature-invalid`), whose signed claims do not approve this request (`approval-claims-mismatch`), signed after the pinned version's supersession (`approval-policy-superseded`), by the requester or an approver the declared workflow's erasure gate policy does not name (`approver-is-requester`, `approver-not-eligible`), or for a gate that is not that workflow's erasure gate (`approval-gate-unknown`) (fix rounds 4 and 5).
  - `request` validates the declaration, then VERIFIES every requester-named address. Each must not already be erased, must be filed under the requesting tenant (I6), must have a stored class that is not the erasure record's and that equals the label (C2), must have a value at a subject key path that hashes to `subject_ref` (iv), and must carry no subject in a replay-input field (§7 `replay-input`). It judges retention against the STORED class and the pinned policy, then starts the deployment-declared one-gate workflow.
  - `complete` holds the presented approval to the RECORDED state and submission, and takes `requested_by` and `actor` from those (I2). It re-judges against the pinned and the newest policy and resumes. On completion it SIGNS the record (R2), appends the index entries carrying that signature FIRST (write-ahead, I4), then files the record under the `ArtifactErase` capability (I3). A retry reuses its prior attempt's signature, verified.
- Why: SEC-009; G6/U9: an erasure is written only on a recorded human approval.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf_runtime.erasure.door.ErasureDoor

- Surface: ccf_runtime.erasure.door.ErasureDoor
- Public surface: true
- Change type: added
- Before: absent
- After: The governed door. It takes a REQUIRED `index`; a REQUIRED `authority` (fix round 5), the tenant's `ErasureAuthority` — its HITL policy key, which its `transport` must be bound to or construction refuses by name (R5), its erasure workflow, the only workflow it runs (`workflow-not-declared`, R1), and the door's public key; a REQUIRED `door_signer` and `door_key_id`, the door's private signing key, which must verify under the declared door key or construction refuses by name (R2); and an optional `identity_provider` that verifies signatures (`None`: the SDK's reference detached-JWS verifier). It refuses, by name, an approval for another workflow or tenant (`approval-workflow-mismatch`, `approval-tenant-mismatch`), that is unsigned (`approval-unsigned`), that pins another HITL policy key (`approval-policy-key-mismatch`), whose pinned HITL policy does not resolve (`approval-policy-unresolvable`), whose signature does not verify under the key that policy declares for the approver (`approval-signature-invalid`), whose signed claims do not approve this request (`approval-claims-mismatch`), signed after the pinned version's supersession (`approval-policy-superseded`), by the requester or an approver the declared workflow's erasure gate policy does not name (`approver-is-requester`, `approver-not-eligible`), or for a gate that is not that workflow's erasure gate (`approval-gate-unknown`) (fix rounds 4 and 5).
  - `request` validates the declaration, then VERIFIES every requester-named address. Each must not already be erased, must be filed under the requesting tenant (I6), must have a stored class that is not the erasure record's and that equals the label (C2), must have a value at a subject key path that hashes to `subject_ref` (iv), and must carry no subject in a replay-input field (§7 `replay-input`). It judges retention against the STORED class and the pinned policy, then starts the deployment-declared one-gate workflow.
  - `complete` holds the presented approval to the RECORDED state and submission, and takes `requested_by` and `actor` from those (I2). It re-judges against the pinned and the newest policy and resumes. On completion it SIGNS the record (R2), appends the index entries carrying that signature FIRST (write-ahead, I4), then files the record under the `ArtifactErase` capability (I3). A retry reuses its prior attempt's signature, verified.
- Why: SEC-009; G6/U9: an erasure is written only on a recorded human approval.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf_runtime.erasure.ErasureRefused

- Surface: ccf_runtime.erasure.ErasureRefused
- Public surface: true
- Change type: added
- Before: absent
- After: A `PermissionError` carrying `reason_code` and, for a retention refusal, the `RetentionDecision`.
- Why: SEC-009; Every refusal is by name and writes nothing.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf_runtime.erasure.door.ErasureRefused

- Surface: ccf_runtime.erasure.door.ErasureRefused
- Public surface: true
- Change type: added
- Before: absent
- After: A `PermissionError` carrying `reason_code` and, for a retention refusal, the `RetentionDecision`.
- Why: SEC-009; Every refusal is by name and writes nothing.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf_runtime.erasure.ErasureWorkflowUngated

- Surface: ccf_runtime.erasure.ErasureWorkflowUngated
- Public surface: true
- Change type: added
- Before: absent
- After: A `ValueError` raised when the deployment's erasure workflow can reach a terminal state without crossing a typed approval gate.
- Why: SEC-009; U9: the request/approval shape is the deployment's, validated by the door.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf_runtime.erasure.door.ErasureWorkflowUngated

- Surface: ccf_runtime.erasure.door.ErasureWorkflowUngated
- Public surface: true
- Change type: added
- Before: absent
- After: A `ValueError` raised when the deployment's erasure workflow can reach a terminal state without crossing a typed approval gate.
- Why: SEC-009; U9: the request/approval shape is the deployment's, validated by the door.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.products.refusal.ErasedContentRefusal

- Surface: ccf.products.refusal.ErasedContentRefusal
- Public surface: true
- Change type: added
- Before: absent
- After: A refusal kind `erased-content`: detail, `erasure_reason`, `erased_at`, `erasure_record_address`. A door renders it only at `reasoned` and `full`. The record address is withheld below `full`.
- Why: SEC-009; G5/U11: a disclosure-governed reading of an erased address.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.replay.engine.ERASED_SITE_RETAINED_CHILD_QUESTION

- Surface: ccf.replay.engine.ERASED_SITE_RETAINED_CHILD_QUESTION
- Public surface: true
- Change type: added
- Before: absent
- After: The site token `retained-child-question`.
- Why: SEC-009; §5.2: names where a replay met an erased member.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.replay.engine.ErasedContent

- Surface: ccf.replay.engine.ErasedContent
- Public surface: true
- Change type: added
- Before: absent
- After: A replay result member reporting one erased retained member: site, address, record address, reason, instant.
- Why: SEC-009; §5.2: a replay over erased retained content completes, and the erasure is disclosed rather than reported as absent.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf_runtime.http_api.refusal_status.STATUS_GONE

- Surface: ccf_runtime.http_api.refusal_status.STATUS_GONE
- Public surface: true
- Change type: added
- Before: absent
- After: The HTTP status `410` for the `erased-content` kind.
- Why: SEC-009; U11: 410 at `reasoned`/`full`; the route's not-found rendering at `minimal`.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.compose_erasure_consult

- Surface: ccf.erasure.compose_erasure_consult
- Public surface: true
- Change type: added
- Before: absent
- After: THE composition helper. It wraps any store in `ErasureConsultingStore` over four REQUIRED arguments, optionally scoped to a tenant:
  - a declared erasure index;
  - an audit log;
  - the injected fabric `clock`, which stamps the `index-unsupported` audit event (ruling 3);
  - the DEPLOYMENT's `control_plane` through which each approval's pinned HITL policy, approval policy and workflow definition are resolved (fix round 4); there is no fresh-registry fallback (ruling 5);
  - the deployment's `erasure_trust` (fix round 5, R1, R2, R4): per tenant that may erase, an `ErasureAuthority` naming the HITL policy key its transport is bound to (fix round 4, ruling 1), its erasure workflow's content hash, and the erasure door's public key.

  An optional `identity_provider` is the verifier of approvals and door signatures; `None` is the SDK's reference detached-JWS verifier; one that verifies nothing accepts everything (the adopter's trust choice). It validates every entry against its door-signed record. That validation is memoized per index head (index identity, entry count, store identity), per Control Plane policy head (`policy_head`), per composed trust and per identity provider instance (fix round 5, R3), so a site composing once per question does not re-read every record; an append or any Control Plane registration invalidates the memo (ruling 4). It is idempotent on a store already composed over the same index with the same Control Plane, identity provider and trust, refuses one composed over another index (M1) and refuses, by name, a re-composition with a different trust root (`ErasureCompositionRefused`, ruling 5). `create_app`, `build_artifact_server`, `open_product`, `build_governed_resolver`, the in-process adapter's boot and the local CLI dependencies all compose through it.
- Why: SEC-009; ruling 2 on `D-IMPL-374` (4), "composed ALWAYS means every store construction site".
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.store.compose_erasure_consult

- Surface: ccf.erasure.store.compose_erasure_consult
- Public surface: true
- Change type: added
- Before: absent
- After: THE composition helper. It wraps any store in `ErasureConsultingStore` over four REQUIRED arguments, optionally scoped to a tenant:
  - a declared erasure index;
  - an audit log;
  - the injected fabric `clock`, which stamps the `index-unsupported` audit event (ruling 3);
  - the DEPLOYMENT's `control_plane` through which each approval's pinned HITL policy, approval policy and workflow definition are resolved (fix round 4); there is no fresh-registry fallback (ruling 5);
  - the deployment's `erasure_trust` (fix round 5, R1, R2, R4): per tenant that may erase, an `ErasureAuthority` naming the HITL policy key its transport is bound to (fix round 4, ruling 1), its erasure workflow's content hash, and the erasure door's public key.

  An optional `identity_provider` is the verifier of approvals and door signatures; `None` is the SDK's reference detached-JWS verifier; one that verifies nothing accepts everything (the adopter's trust choice). It validates every entry against its door-signed record. That validation is memoized per index head (index identity, entry count, store identity), per Control Plane policy head (`policy_head`), per composed trust and per identity provider instance (fix round 5, R3), so a site composing once per question does not re-read every record; an append or any Control Plane registration invalidates the memo (ruling 4). It is idempotent on a store already composed over the same index with the same Control Plane, identity provider and trust, refuses one composed over another index (M1) and refuses, by name, a re-composition with a different trust root (`ErasureCompositionRefused`, ruling 5). `create_app`, `build_artifact_server`, `open_product`, `build_governed_resolver`, the in-process adapter's boot and the local CLI dependencies all compose through it.
- Why: SEC-009; ruling 2 on `D-IMPL-374` (4), "composed ALWAYS means every store construction site".
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

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
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.replay.engine.ERASED_SITE_CHILD_CONTRACT

- Surface: ccf.replay.engine.ERASED_SITE_CHILD_CONTRACT
- Public surface: true
- Change type: added
- Before: absent
- After: The site token `child-contract`.
- Why: SEC-009; ruling 4.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.replay.engine.ERASED_SITE_DECISION_RECORD

- Surface: ccf.replay.engine.ERASED_SITE_DECISION_RECORD
- Public surface: true
- Change type: added
- Before: absent
- After: The site token `decision-record`.
- Why: SEC-009; ruling 4.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.replay.engine.ERASED_SITE_REPLAY_ARTIFACT

- Surface: ccf.replay.engine.ERASED_SITE_REPLAY_ARTIFACT
- Public surface: true
- Change type: added
- Before: absent
- After: The site token `replay-artifact`, for any other artifact the re-execution reads.
- Why: SEC-009; ruling 4.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

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
- After: three new **required** keywords with no default: `erasure_index: ErasureIndexProtocol`, (fix round 4) `control_plane: PinnedPolicySource`, the deployment's Control Plane through which each erasure approval is verified, and (fix round 5) `erasure_trust: ErasureTrust`, the per-tenant erasure authorities every erasure is verified against (replacing fix round 4's `hitl_policy_key`). The server wraps `store` through `compose_erasure_consult`.
  - Every byte read goes through the wrapped store.
  - A governed record follows the authorization-first order (ruling 1).
  - An erased artifact on the client lane is returned as the erased reading: the not-found shell at `minimal`, and `erased-content` above it.
  - The naming resource still resolves through `store`, because it returns an address, never bytes (the U8 reasoning).
- Why: SEC-009; the coordinator's MCP ruling on `D-IMPL-374` (4). This server is the ArtifactStore's persistence transport (CLAUDE.md §7.4), so an erased artifact served over it is exactly the SEC-009 hole.
- Migration: pass `erasure_index=` with the deployment's durable index, `control_plane=` with its Control Plane and `erasure_trust=` with its per-tenant erasure authorities. Every in-tree call site is updated.

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

## ccf_runtime.mcp.artifact_server.ARTIFACT_NAMES_URI_SCHEME

- Surface: ccf_runtime.mcp.artifact_server.ARTIFACT_NAMES_URI_SCHEME
- Public surface: true
- Change type: added
- Before: absent
- After: The scheme `ccf-artifact-names`.
- Why: SEC-009; ruling 2 on `D-IMPL-374` (4). The erasure door verifies an address's STORED class and tenant through `names_at`, and the §7.4 MCP-backed reference store must not be excluded from that.
- Migration: none. A deployment running an older artifact server must upgrade it before erasing through `McpArtifactStore`.

## ccf_runtime.mcp.artifact_server.NAMES_URI_TEMPLATE

- Surface: ccf_runtime.mcp.artifact_server.NAMES_URI_TEMPLATE
- Public surface: true
- Change type: added
- Before: absent
- After: `ccf-artifact-names://{content_address}`. It is a resource, grant-tenanted and declared under `artifact.read`, that answers every `(tenant, class, name)` the backing store filed the address under. It returns the caller's verified tenant only, and only naming, never bytes.
- Why: SEC-009; ruling 2 on `D-IMPL-374` (4). The erasure door verifies an address's STORED class and tenant through `names_at`, and the §7.4 MCP-backed reference store must not be excluded from that.
- Migration: none. A deployment running an older artifact server must upgrade it before erasing through `McpArtifactStore`.

## ccf.artifacts.mcp_store.McpArtifactStore

- Surface: ccf.artifacts.mcp_store.McpArtifactStore
- Public surface: true
- Change type: reshaped
- Before: the four Protocol verbs, plus `url` and `write_kinds`.
- After: adds `names_at(*, content_address)`. It reads the server's names resource for this credential's tenant. A malformed address returns `()` with no round trip. An answer that is not a list of names raises `McpServerUnreachable`.
- Why: SEC-009; ruling 2 on `D-IMPL-374` (4). The same naming introspection `FileArtifactStore.names_at` offers, so an erasure through the §7.4 reference store is verified and admitted.
- Migration: none.

## ccf.replay.engine.ReplayOutcome

- Surface: ccf.replay.engine.ReplayOutcome
- Public surface: true
- Change type: reshaped
- Before: no erasure field.
- After: a new field `erased_content: tuple[ErasedContent, ...] = ()`. `RefusalReplayOutcome` gets the same field. It is hash-transparent at `()`, so an outcome with nothing erased renders as before.
- Why: SEC-009; design §5.2. A replay over erased retained content completes, and the erasure is disclosed on the result. The replay record is unchanged.
- Migration: none.

## ccf.erasure.errors.ErasedContentRefused

- Surface: ccf.erasure.errors.ErasedContentRefused
- Public surface: true
- Change type: added
- Before: absent
- After: The same `ArtifactStoreError` as `ccf.erasure.store.ErasedContentRefused`, defined in the dependency-free errors module that the index and the store both import. Its facts (record address, reason, instant) come from the RECORD, never the index entry (fix round 2, N2).
- Why: SEC-009; fix round 2, N3: one home for the refusal family, so the index can raise a member of it without importing the store.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.errors.ErasureIndexCorrupt

- Surface: ccf.erasure.errors.ErasureIndexCorrupt
- Public surface: true
- Change type: added
- Before: absent
- After: An `ErasedContentRefused` with reason `index-corrupt` and every fact `None`. The file index raises it on a shrunk file, an unparseable or empty line, a broken hash chain, or a conflicting duplicate. The decorating store raises it on EVERY read under that index: a corrupt index fails CLOSED.
- Why: SEC-009; fix round 2, N3 and (a).
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.ErasureIndexCorrupt

- Surface: ccf.erasure.ErasureIndexCorrupt
- Public surface: true
- Change type: added
- Before: absent
- After: Re-export of `ccf.erasure.errors.ErasureIndexCorrupt`.
- Why: SEC-009; fix round 2, N3.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.errors.ErasureIndexInsecure

- Surface: ccf.erasure.errors.ErasureIndexInsecure
- Public surface: true
- Change type: added
- Before: absent
- After: A `PermissionError` the file index raises, by name, when its file is a symlink or not a regular file, is not owned by the effective user, has a mode other than 0600, or sits in a parent directory that is not owned by the effective user or is open to group or other.
- Why: SEC-009; fix round 2, (a).
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.ErasureIndexInsecure

- Surface: ccf.erasure.ErasureIndexInsecure
- Public surface: true
- Change type: added
- Before: absent
- After: Re-export of `ccf.erasure.errors.ErasureIndexInsecure`.
- Why: SEC-009; fix round 2, (a).
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.errors.INDEX_CORRUPT

- Surface: ccf.erasure.errors.INDEX_CORRUPT
- Public surface: true
- Change type: added
- Before: absent
- After: The reason code `index-corrupt` an `ErasureIndexCorrupt` carries.
- Why: SEC-009; fix round 2, N3.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.INDEX_CORRUPT

- Surface: ccf.erasure.INDEX_CORRUPT
- Public surface: true
- Change type: added
- Before: absent
- After: Re-export of `ccf.erasure.errors.INDEX_CORRUPT`.
- Why: SEC-009; fix round 2, N3.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.index.GENESIS

- Surface: ccf.erasure.index.GENESIS
- Public surface: true
- Change type: added
- Before: absent
- After: The 64-zero predecessor hash the first line of a file index chains from.
- Why: SEC-009; fix round 2, (a): every line carries the sha256 of the previous line's bytes, and a broken chain is refused at boot.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.GENESIS

- Surface: ccf.erasure.GENESIS
- Public surface: true
- Change type: added
- Before: absent
- After: Re-export of `ccf.erasure.index.GENESIS`.
- Why: SEC-009; fix round 2, (a).
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.index.require_append_authority

- Surface: ccf.erasure.index.require_append_authority
- Public surface: true
- Change type: added
- Before: absent
- After: The check every `ErasureIndexProtocol.append` makes: the presented capability is a genuine `Authorized[ArtifactErase]` for the resource `<subject_class>/<request_id>` of the entry and for the entry's tenant. Anything else raises `CapabilityBypassError`.
- Why: SEC-009; fix round 2, I3: an index append is an erasure, so it takes the erase capability bound to its request.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.require_append_authority

- Surface: ccf.erasure.require_append_authority
- Public surface: true
- Change type: added
- Before: absent
- After: Re-export of `ccf.erasure.index.require_append_authority`.
- Why: SEC-009; fix round 2, I3.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.products.product.open_product (erasure index)

- Surface: ccf.products.product.open_product
- Public surface: true
- Change type: behavior
- Before: A supplied `artifact_store` was composed with the erasure consult over an index derived from the scratch root.
- After: A new keyword `erasure_index`. The consult uses the SELECTED store's own index. A raw supplied store must come with `erasure_index`, or `ErasureIndexUnavailable` is raised by name. A store already composed through `compose_erasure_consult` carries its index, and its tenant scope must be this product's or none. An `erasure_index` presented beside it must be the same index by path. With no supplied store, the index is derived from the scratch root as before.
- Why: SEC-009; fix round 2, N1: an index derived from the scratch root is not the supplied store's, so every erasure filed against that store would have been missed.
- Migration: pass `erasure_index=` with a raw supplied store, or supply the store composed through `compose_erasure_consult`.

## ccf.erasure.contracts.ERASURE_APPROVAL_CLASS

- Surface: ccf.erasure.contracts.ERASURE_APPROVAL_CLASS
- Public surface: true
- Change type: added
- Before: absent
- After: The artifact class `ccf.erasure-approval`, under which the door files the recorded human approval before the index append. A subject declaration cannot list it as erasable.
- Why: SEC-009; fix round 3, I3 part 2, option (a): the approval check needs a durable record, and the ArtifactStore already holds replay records.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.ERASURE_APPROVAL_CLASS

- Surface: ccf.erasure.ERASURE_APPROVAL_CLASS
- Public surface: true
- Change type: added
- Before: absent
- After: Re-export of `ccf.erasure.contracts.ERASURE_APPROVAL_CLASS`.
- Why: SEC-009; fix round 3.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.contracts.ErasureApproval

- Surface: ccf.erasure.contracts.ErasureApproval
- Public surface: true
- Change type: added
- Before: absent
- After: The recorded, SIGNED approval of one erasure request: tenant, request id, approver, verdict, the instant (the attestation's `issued_at`), the gate and the state hash the approver saw, the workflow definition's hash, the submission's hash, the signed HITL attestation verbatim (`attestation`: claim set, signature, key id) and the pinned HITL policy (`hitl_policy_ref`, `key@version`). Its content address is `approval_ref`; the door and the decorating store verify its signature against the key the pinned policy declares for the approver (fix round 4).
- Why: SEC-009; fix round 3, I3 part 2: a forged `approval_ref`, or one naming another request, tenant or a non-approving verdict, is `index-unsupported`, durably across restarts and processes.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.ErasureApproval

- Surface: ccf.erasure.ErasureApproval
- Public surface: true
- Change type: added
- Before: absent
- After: Re-export of `ccf.erasure.contracts.ErasureApproval`.
- Why: SEC-009; fix round 3.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.approval.verify_erasure_approval

- Surface: ccf.erasure.approval.verify_erasure_approval
- Public surface: true
- Change type: added
- Before: absent
- After: The ONE approval check the door and the decorating store run, taking `requested_by` (the door-signed record's, fix round 5 R2) and the tenant's `authority` (an `ErasureAuthority`, fix round 5): require the approval to be in the authority's tenant and for its declared erasure workflow (`approval-tenant-mismatch`, `approval-workflow-mismatch`, R1); require the pin's key to be the authority's HITL policy key (ruling 1); resolve that key at the pinned version; require its key id to be declared for the signer and verify the signature against exactly those keys; require the signed claims to name this request's gate event (`{tenant}/{request_id}/{gate}`), this tenant, the gate's state hash, the approver and the approving verdict, with `acted_at` equal to `issued_at`; require `issued_at` to precede the pinned version's supersession (ruling 4); require the approver not to be the requester (ruling 2); resolve the declared workflow by its hash, content-verified, in its tenant; require the gate to be its erasure gate (ruling 3, R1); and require the approver to be eligible under that gate's approval policy at its pinned version (ruling 2, R1). Returns the verified claims or raises `ErasureApprovalInvalid`.
- Why: SEC-009; fix round 4: the re-review's probe D — an approving approval filed with only the requester's `ArtifactErase` was served as supported.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.verify_erasure_approval

- Surface: ccf.erasure.verify_erasure_approval
- Public surface: true
- Change type: added
- Before: absent
- After: Re-export of `ccf.erasure.approval.verify_erasure_approval`.
- Why: SEC-009; fix round 4.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.approval.ErasureApprovalInvalid

- Surface: ccf.erasure.approval.ErasureApprovalInvalid
- Public surface: true
- Change type: added
- Before: absent
- After: A `ValueError` with a `reason_code`: `approval-tenant-mismatch`, `approval-workflow-mismatch` (fix round 5, R1), `approval-unsigned`, `approval-policy-key-mismatch`, `approval-policy-unresolvable`, `approval-signature-invalid`, `approval-claims-mismatch`, `approval-policy-superseded`, `approval-policy-window-unknown`, `approver-is-requester`, `approver-not-eligible`, `approval-workflow-unresolvable` or `approval-gate-unknown` (fix round 4, rulings 1–4). Fix round 5 removed `approval-policy-tenant-mismatch` (an authority refuses, at construction, a key outside its tenant) and `approval-gate-policy-mismatch` (the record field it compared was deleted).
- Why: SEC-009; fix round 4: the door refuses with the same reason code; the consult counts any of them as `index-unsupported`.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.ErasureApprovalInvalid

- Surface: ccf.erasure.ErasureApprovalInvalid
- Public surface: true
- Change type: added
- Before: absent
- After: Re-export of `ccf.erasure.approval.ErasureApprovalInvalid`.
- Why: SEC-009; fix round 4.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.approval.PinnedPolicySource

- Surface: ccf.erasure.approval.PinnedPolicySource
- Public surface: true
- Change type: added
- Before: absent
- After: A read-only Protocol: `resolve(key, version)` (exact, never latest), `versions`, `peek`, `artifact_class_of` (the pinned-read surface the eligibility judgment shares with the transport), `keys_of_class` (locating the workflow definition by its hash) and `audit_events` (the registration history the supersession instant and `policy_head` are read from). Every `ControlPlaneRegistry` satisfies it (fix round 4, rulings 2–4).
- Why: SEC-009; fix round 4: the narrowest read surface the check needs.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.PinnedPolicySource

- Surface: ccf.erasure.PinnedPolicySource
- Public surface: true
- Change type: added
- Before: absent
- After: Re-export of `ccf.erasure.approval.PinnedPolicySource`.
- Why: SEC-009; fix round 4.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.approval.reference_approval_verifier

- Surface: ccf.erasure.approval.reference_approval_verifier
- Public surface: true
- Change type: added
- Before: absent
- After: The SDK's reference detached-JWS verifier with no signing material, used where a site supplies no `identity_provider`. Always the same, stateless instance (fix round 5, R3), so compositions that declare no provider share the validation cache keyed by the provider instance.
- Why: SEC-009; fix round 4: verification needs a provider; the reference one signs nothing.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.reference_approval_verifier

- Surface: ccf.erasure.reference_approval_verifier
- Public surface: true
- Change type: added
- Before: absent
- After: Re-export of `ccf.erasure.approval.reference_approval_verifier`.
- Why: SEC-009; fix round 4.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.approval.APPROVING_VERDICT

- Surface: ccf.erasure.approval.APPROVING_VERDICT
- Public surface: true
- Change type: added
- Before: absent
- After: The signed HITL action that approves: `approve`.
- Why: SEC-009; fix round 4.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.APPROVING_VERDICT

- Surface: ccf.erasure.APPROVING_VERDICT
- Public surface: true
- Change type: added
- Before: absent
- After: Re-export of `ccf.erasure.approval.APPROVING_VERDICT`.
- Why: SEC-009; fix round 4.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, and a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.errors.ErasureCompositionRefused

- Surface: ccf.erasure.errors.ErasureCompositionRefused
- Public surface: true
- Change type: added
- Before: absent
- After: A `TypeError` raised at composition, by name, when a store construction site composes the erasure consult without the deployment's Control Plane (there is no fresh-registry fallback) or without an `ErasureTrust`, or re-composes an already composed store with a different Control Plane, identity provider or trust; and when the erasure door is built with a non-`ErasureAuthority`, a HITL transport bound to another key, or a signing key that does not verify under the declared door key (fix round 5).
- Why: SEC-009; fix round 4, ruling 5: a silently ignored trust root is a trust root the site did not name.
- Migration: pass `erasure_trust=` — per tenant that may erase, its HITL policy key (the key its HITL transport is bound to), its erasure workflow's content hash and the door's public key — and the deployment's own Control Plane; register the HITL policy, the erasure workflow's approval policy and the workflow definition in that Control Plane, as the door's deployment already does.

## ccf.erasure.ErasureCompositionRefused

- Surface: ccf.erasure.ErasureCompositionRefused
- Public surface: true
- Change type: added
- Before: absent
- After: A `TypeError` raised at composition, by name, when a store construction site composes the erasure consult without the deployment's Control Plane (there is no fresh-registry fallback) or without an `ErasureTrust`, or re-composes an already composed store with a different Control Plane, identity provider or trust; and when the erasure door is built with a non-`ErasureAuthority`, a HITL transport bound to another key, or a signing key that does not verify under the declared door key (fix round 5). Re-export.
- Why: SEC-009; fix round 4, ruling 5: a silently ignored trust root is a trust root the site did not name.
- Migration: pass `erasure_trust=` — per tenant that may erase, its HITL policy key (the key its HITL transport is bound to), its erasure workflow's content hash and the door's public key — and the deployment's own Control Plane; register the HITL policy, the erasure workflow's approval policy and the workflow definition in that Control Plane, as the door's deployment already does.

## ccf.erasure.store.ErasureCompositionRefused

- Surface: ccf.erasure.store.ErasureCompositionRefused
- Public surface: true
- Change type: added
- Before: absent
- After: A `TypeError` raised at composition, by name, when a store construction site composes the erasure consult without the deployment's Control Plane (there is no fresh-registry fallback) or without an `ErasureTrust`, or re-composes an already composed store with a different Control Plane, identity provider or trust; and when the erasure door is built with a non-`ErasureAuthority`, a HITL transport bound to another key, or a signing key that does not verify under the declared door key (fix round 5). Re-export.
- Why: SEC-009; fix round 4, ruling 5: a silently ignored trust root is a trust root the site did not name.
- Migration: pass `erasure_trust=` — per tenant that may erase, its HITL policy key (the key its HITL transport is bound to), its erasure workflow's content hash and the door's public key — and the deployment's own Control Plane; register the HITL policy, the erasure workflow's approval policy and the workflow definition in that Control Plane, as the door's deployment already does.

## ccf.erasure.approval.policy_head

- Surface: ccf.erasure.approval.policy_head
- Public surface: true
- Change type: added
- Before: absent
- After: `policy_head(control_plane) -> str`: the sha256 of the Control Plane's registration history (every resolved `register*` audit event: action, key, version, instant, in order). The decorating store keys its validation cache by it, so any registration re-judges every cached verdict, and a verdict is never keyed by a Control Plane object's identity.
- Why: SEC-009; fix round 4, ruling 4: a cached SUPPORTED survived a key rotation, and the memo was keyed by `id(control_plane)`.
- Migration: none.

## ccf.erasure.policy_head

- Surface: ccf.erasure.policy_head
- Public surface: true
- Change type: added
- Before: absent
- After: `policy_head(control_plane) -> str`: the sha256 of the Control Plane's registration history (every resolved `register*` audit event: action, key, version, instant, in order). The decorating store keys its validation cache by it, so any registration re-judges every cached verdict, and a verdict is never keyed by a Control Plane object's identity. Re-export.
- Why: SEC-009; fix round 4, ruling 4: a cached SUPPORTED survived a key rotation, and the memo was keyed by `id(control_plane)`.
- Migration: none.

## ccf_runtime.cli.local.build_local_dependencies

- Surface: ccf_runtime.cli.local.build_local_dependencies
- Public surface: true
- Change type: reshaped
- Before: `build_local_dependencies(*, root)` — the in-memory HITL transport unbound, the erasure consult composed without a trust root.
- After: `build_local_dependencies(*, root, hitl_policy_key, erasure_trust)`: a REQUIRED `hitl_policy_key` (from `--local-hitl-policy-key`) that the in-memory HITL transport is bound to (fix round 4), and a REQUIRED `erasure_trust` the erasure consult verifies erasures against (fix round 5). The `--local` arm declares none (`ErasureTrust(authorities={})`): the local dev fabric runs no erasure door and registers no erasure workflow, so every erasure its index names is withheld as `index-unsupported`.
- Why: SEC-009; fix round 4, ruling 1, and fix round 5, R1, R2, R4: every store construction site takes the deployment's trust root.
- Migration: pass `hitl_policy_key=` and `erasure_trust=`; the `--local` arm (suspended under SEC-002) takes `--local-hitl-policy-key`.

## ccf.products.product.open_product

- Surface: ccf.products.product.open_product
- Public surface: true
- Change type: reshaped
- Before: `control_plane: ControlPlaneRegistry | None = None` (a fresh registry when omitted); no erasure trust root.
- After: `control_plane: ControlPlaneRegistry` is REQUIRED with no default and `None` is refused by name (`ErasureCompositionRefused`, fix round 4); a new REQUIRED `erasure_trust: ErasureTrust` (fix round 5; it replaces fix round 4's `hitl_policy_key`), the per-tenant erasure authorities the composed store verifies every erasure against. A deployment that runs no erasure door passes `ErasureTrust(authorities={})`.
- Why: SEC-009; fix round 4, rulings 1 and 5, and fix round 5, R1, R2, R4: the fallback registry lacked the door's HITL policy, and a trust root read from filed artifacts let a filer choose who counts as the requester and which workflow's gate policy applies.
- Migration: pass `control_plane=` (the deployment's registry) and `erasure_trust=`. Every in-tree caller is updated; the examples declare no erasure authority, because none runs an erasure door.

## ccf.products.product.OpenedProduct

- Surface: ccf.products.product.OpenedProduct
- Public surface: true
- Change type: reshaped
- Before: No erasure trust root.
- After: Carries `erasure_trust` (the trust `open_product` took) and hands it to every resolver it builds through `build_arguments`, so a server composed over an opened product passes `opened.erasure_trust` to `ApiDependencies`.
- Why: SEC-009; fix round 5 (it replaces fix round 4's `hitl_policy_key`).
- Migration: none; read `opened.erasure_trust` where a server composes over the product.

## ccf.products.resolver.build_governed_resolver

- Surface: ccf.products.resolver.build_governed_resolver
- Public surface: true
- Change type: reshaped
- Before: No erasure trust root; any `ControlPlaneProtocol` accepted.
- After: A new REQUIRED `erasure_trust: ErasureTrust` the composed store verifies every erasure against (fix round 5; it replaces fix round 4's `hitl_policy_key`); a `control_plane` offering no pinned-read surface (`PinnedPolicySource`) is refused by name (`ErasureCompositionRefused`).
- Why: SEC-009; fix round 4, rulings 1 and 5; fix round 5, R1, R2, R4.
- Migration: pass `erasure_trust=` beside the other declared keys; `OpenedProduct.build_arguments` already does.

## ccf_runtime.http_api.dependencies.ApiDependencies

- Surface: ccf_runtime.http_api.dependencies.ApiDependencies
- Public surface: true
- Change type: reshaped
- Before: No erasure trust root.
- After: A new REQUIRED field `erasure_trust: ErasureTrust` — per tenant that may erase, the HITL policy key its `hitl_transport` is bound to, its erasure workflow's content hash and the erasure door's public key — which `create_app` composes the erasure consult with (fix round 5; it replaces fix round 4's `hitl_policy_key`).
- Why: SEC-009; fix round 4, ruling 1; fix round 5, R1, R2, R4.
- Migration: pass `erasure_trust=`. Every in-tree construction is updated.

## ccf.client.adapters.binding_document.BindingDocument

- Surface: ccf.client.adapters.binding_document.BindingDocument
- Public surface: true
- Change type: reshaped
- Before: No erasure trust root.
- After: A new REQUIRED data key `erasure_authority` (fix round 5; it replaces fix round 4's `hitl_policy_key`): `{}` declares none, or a mapping of exactly `hitl_policy_key` (confined under the deployment's tenant at boot), `workflow_definition_hash` and `door_keys` (the erasure door's public JWKs by key id), held as an `ErasureAuthorityDeclaration`. `erasure_trust(*, tenant_id)` builds the `ErasureTrust` the in-process adapter composes the erasure consult with.
- Why: SEC-009; fix round 4, ruling 1, and fix round 5: the in-process adapter's boot is a store construction site, and its deployment is declared by its binding document.
- Migration: add `erasure_authority: {}` to `binding.yaml`, or the three fields for a deployment that runs an erasure door; the loader refuses a document that omits the key.

## ccf.client.adapters.binding_document.load_binding_document

- Surface: ccf.client.adapters.binding_document.load_binding_document
- Public surface: true
- Change type: behavior
- Before: `erasure_authority` was not a binding-document key.
- After: `erasure_authority` is a required data key; a document that omits it is refused by name, like every other required key, and a value that is neither `{}` nor exactly its three fields is refused by name (`BindingError`).
- Why: SEC-009; fix round 5 (it replaces fix round 4's `hitl_policy_key`).
- Migration: add `erasure_authority:` to the document.

## ccf.erasure.trust.ErasureAuthority

- Surface: ccf.erasure.trust.ErasureAuthority
- Public surface: true
- Change type: added
- Before: absent
- After: A contract: what ONE tenant's erasures are verified against, declared at composition — `tenant_id` (the erasure workflow's tenant), `hitl_policy_key` (the key its HITL transport is bound to; refused unless it lies under `tenant_id`), `workflow_definition_hash` (the erasure workflow definition's content hash) and `door_keys` (the erasure door's PUBLIC signing keys by key id; a key carrying private material is refused by name).
- Why: SEC-009; fix round 5, R1, R2, R4: the requester never chooses the workflow, the policy or who counts as the requester.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.ErasureAuthority

- Surface: ccf.erasure.ErasureAuthority
- Public surface: true
- Change type: added
- Before: absent
- After: Re-export of `ccf.erasure.trust.ErasureAuthority`.
- Why: SEC-009; fix round 5, R1, R2, R4: the requester never chooses the workflow, the policy or who counts as the requester.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.trust.ErasureTrust

- Surface: ccf.erasure.trust.ErasureTrust
- Public surface: true
- Change type: added
- Before: absent
- After: A contract: `authorities`, a mapping from each tenant that may erase to its `ErasureAuthority`, keyed by the authority's own tenant; `authority_for(tenant_id)`. Empty declares that a site verifies no erasure as supported — every erased address stays withheld, `index-unsupported`.
- Why: SEC-009; fix round 5, R4: one deployment-wide HITL key let only that key's tenant erase.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.ErasureTrust

- Surface: ccf.erasure.ErasureTrust
- Public surface: true
- Change type: added
- Before: absent
- After: Re-export of `ccf.erasure.trust.ErasureTrust`.
- Why: SEC-009; fix round 5, R4: one deployment-wide HITL key let only that key's tenant erase.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.trust.ErasureRecordInvalid

- Surface: ccf.erasure.trust.ErasureRecordInvalid
- Public surface: true
- Change type: added
- Before: absent
- After: A `ValueError` with a `reason_code`: `erasure-tenant-undeclared` (no authority for the entry's tenant), `record-address-mismatch`, `record-signature-invalid` (no door signature verifies over the record's bytes under the tenant's declared door keys) or `record-entry-mismatch`. The consult counts any of them as `index-unsupported`.
- Why: SEC-009; fix round 5, R2 and R4.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.ErasureRecordInvalid

- Surface: ccf.erasure.ErasureRecordInvalid
- Public surface: true
- Change type: added
- Before: absent
- After: Re-export of `ccf.erasure.trust.ErasureRecordInvalid`.
- Why: SEC-009; fix round 5, R2 and R4.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.trust.DOOR_SIGNATURE_ASSERTION

- Surface: ccf.erasure.trust.DOOR_SIGNATURE_ASSERTION
- Public surface: true
- Change type: added
- Before: absent
- After: The protected-header member (`ccf_signed_class`) a door signature asserts, with the value `ccf.erasure-record`: a signature the door key made for anything else does not verify as a record signature.
- Why: SEC-009; fix round 5, R2: domain separation for the door key.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.DOOR_SIGNATURE_ASSERTION

- Surface: ccf.erasure.DOOR_SIGNATURE_ASSERTION
- Public surface: true
- Change type: added
- Before: absent
- After: Re-export of `ccf.erasure.trust.DOOR_SIGNATURE_ASSERTION`.
- Why: SEC-009; fix round 5, R2: domain separation for the door key.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.trust.sign_erasure_record

- Surface: ccf.erasure.trust.sign_erasure_record
- Public surface: true
- Change type: added
- Before: absent
- After: `sign_erasure_record(record, *, signer, key_id) -> str`: the door's detached signature (`protected..signature`) over the record's canonical bytes — the bytes the store holds at its content address — asserting `DOOR_SIGNATURE_ASSERTION`.
- Why: SEC-009; fix round 5, R2: the record is door-signed.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.sign_erasure_record

- Surface: ccf.erasure.sign_erasure_record
- Public surface: true
- Change type: added
- Before: absent
- After: Re-export of `ccf.erasure.trust.sign_erasure_record`.
- Why: SEC-009; fix round 5, R2: the record is door-signed.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.trust.verify_door_signature

- Surface: ccf.erasure.trust.verify_door_signature
- Public surface: true
- Change type: added
- Before: absent
- After: `verify_door_signature(payload, *, door_signature, door_key_id, authority, identity_provider)`: refuses (`ErasureRecordInvalid`, `record-signature-invalid`) unless the signature's key id is `door_key_id`, it verifies over exactly `payload` against the authority's declared door keys, and its protected header asserts it signs an erasure record.
- Why: SEC-009; fix round 5, R2.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.verify_door_signature

- Surface: ccf.erasure.verify_door_signature
- Public surface: true
- Change type: added
- Before: absent
- After: Re-export of `ccf.erasure.trust.verify_door_signature`.
- Why: SEC-009; fix round 5, R2.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.trust.verify_erasure_entry

- Surface: ccf.erasure.trust.verify_erasure_entry
- Public surface: true
- Change type: added
- Before: absent
- After: `verify_erasure_entry(entry, payload, *, trust, identity_provider) -> (ErasureRecord, ErasureAuthority)`: the consult's judgment of an entry's record, door signature first — the entry's tenant selects its authority (R4); the bytes hash to the entry's record address; the door's signature verifies over them (R2) before any record field is read; and the record carries every fact the entry does.
- Why: SEC-009; fix round 5: the record a filer writes is not the door's statement until the door's signature says so.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.erasure.verify_erasure_entry

- Surface: ccf.erasure.verify_erasure_entry
- Public surface: true
- Change type: added
- Before: absent
- After: Re-export of `ccf.erasure.trust.verify_erasure_entry`.
- Why: SEC-009; fix round 5: the record a filer writes is not the door's statement until the door's signature says so.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.client.adapters.binding_document.ErasureAuthorityDeclaration

- Surface: ccf.client.adapters.binding_document.ErasureAuthorityDeclaration
- Public surface: true
- Change type: added
- Before: absent
- After: A frozen dataclass: the erasure authority a deployment declares in `binding.yaml` — `hitl_policy_key`, `workflow_definition_hash`, `door_keys` — minus the tenant, which is the booted fabric's.
- Why: SEC-009; fix round 5: the in-process adapter's boot is a store construction site, and its trust root is declared in its binding document.
- Migration: none. A deployment that wants erasure declares a subject declaration, a retention-and-hold policy, an erasure workflow with a typed approval gate, `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in its `WriteKinds`, a HITL policy that requires signed bindings and pins each approver's key, and an `ErasureTrust` naming, per tenant that may erase, that HITL policy's key, the erasure workflow definition's content hash and the erasure door's public signing key — the door holding the private half (fix round 5).

## ccf.hitl.transport.InMemoryHitlTransport

- Surface: ccf.hitl.transport.InMemoryHitlTransport
- Public surface: true
- Change type: reshaped
- Before: The bound HITL policy key was private.
- After: A read-only `hitl_policy_key` property: the Control Plane key the transport's HITL policy resolves under, or `None` when unbound. The erasure door holds its authority's HITL policy key to it at construction and refuses a mismatch by name.
- Why: SEC-009; fix round 5, R5: a door and a transport judging approvals under different policies would file approvals no consult verifies.
- Migration: none.
