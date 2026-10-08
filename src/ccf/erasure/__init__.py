"""Erasure — the MINIMUM SEC-009 mechanism (SDK-defined; `D-IMPL-374` (4); design `D-IMPL-367`).

An erasure is a **fact the fabric records**, never a mutation it performs
(design §1). A deployment declares what a subject is
(:class:`ErasureSubjectDeclaration`) and which artifact classes are erasable
under which reasons, holds and minimum age (:class:`RetentionHoldPolicy`,
default refuse). A request goes through the deployment-declared, factory-
validated one-gate workflow at the erasure door
(``ccf_runtime.erasure.ErasureDoor``), which also requires the distinct
``artifact.erase`` capability (ruling 3) and VERIFIES every address the
request names — its stored class and tenant from the store's naming, the
subject's salted reference in its declared key paths, no subject in a
replay-input field of a record the fabric's record writer filed (fix round 1:
C2, I6, (iv), §7; ``D-IMPL-378``). On a RECORDED human
approval the door appends the entries to the deployment's durable,
append-only erasure index (:class:`ErasureIndexProtocol`,
:class:`FileErasureIndex`) and THEN files the immutable
:class:`ErasureRecord` under the erase capability (write-ahead, I4). The
record is the only authority: the decorating store
(:class:`ErasureConsultingStore`, composed at every store construction site
through :func:`compose_erasure_consult` over a REQUIRED index) validates
every entry against its record and withholds — audited
``erasure_index_unsupported`` — an entry its record does not support (§8).
It serves an ``erased-content`` reading instead of the bytes, within the
erasing tenant (I6), to a caller entitled to the address after authorization
(ruling 1); replay over erased content stays positive with the erasure
disclosed for every erased input class (ruling 4).

**What this package does NOT do — stated, not implied:**

* **No byte destruction and no destruction claim** (``D-IMPL-367`` O1). The
  bytes an erasure names stay on the substrate; the fabric refuses to SERVE
  them. Nothing here is a legal-compliance claim.
* **No field-scoped erasure** (U5): erasure is whole-artifact this phase;
  payload separation is G10 phase 3.
* **No retention lifecycle**: no scheduled expiry, no tiering, no
  ``D-IMPL-50`` fidelity build — the policy only judges a request.
* **No pseudonymization** (U3): principals cannot be subjects (U1).
* **No graph erasure** (G8/O2) and **no key custody or crypto-shredding**
  (G9/O3).
* **No un-erasure** (U6): no record, verb or method reverses an erasure.

**Disclosed residuals (ruling 5 on ``D-IMPL-374`` (4)):**

* ``RequestedAddress.retained_since`` — the instant the minimum age is
  measured from — is **requester-declared and human-approved**, not derived
  from the store: the ``ArtifactStoreProtocol`` records no write instant. The
  approval binds to the request's content identity, this field included.
* ``ClassRetention.minimum_age`` is expressed in **whole days**, because the
  canonical form has no rendering for a duration and a policy must hash.
* A third-party store with no ``names_at`` cannot be erased through: the
  door refuses ``class-unverifiable``. The §7.4 reference store answers
  ``names_at`` through the MCP artifact server's names resource (ruling 2).
* **Enumeration is the deployment's** (ruling (iv)): the fabric verifies the
  addresses a request names; where a subject's artifacts are is the
  deployment's to know (:class:`ErasureSubjectLocator`, declared without a
  reference implementation).
* A tenantless read (the replay engine, ``record_of``, child admission)
  withholds an address ANY tenant erased, redacted (ruling (i)). The MCP
  artifact server's client lane is scoped to its caller's tenant and is not
  one of them (corrected 2026-10-07, ``D-IMPL-377``).
* The ``erasure_index_unsupported`` audit event is stamped with the fabric
  clock injected at composition (ruling 3) — never a wall clock read by the
  store, never the disputed entry's own ``erased_at``; it does not say WHICH
  judgment refused the entry (the reason codes are the verification
  functions' own, :class:`ErasureRecordInvalid` and
  :class:`ErasureApprovalInvalid`).
* ``subject_ref_salt`` sits in a Control Plane artifact beside the hashes it
  salts; for a low-entropy identifier the reference is dictionary-reversible
  by a reader of that artifact (U4, as ruled).

* The trust root is fixed at composition (fix rounds 4 and 5): every site
  passes the deployment's Control Plane and its :class:`ErasureTrust` — per
  tenant that may erase, an :class:`ErasureAuthority` naming the HITL policy
  key its transport is bound to, the content hash of its erasure workflow, and
  the erasure door's public signing key. The DOOR signs every record it files
  (:func:`sign_erasure_record`) and the consult verifies that signature before
  it reads the record (:func:`verify_erasure_entry`), so ``requested_by`` is
  what the door observed. The consult then refuses an approval for another
  workflow or tenant, pinning any other HITL key, by the requester, by an
  approver the declared workflow's gate policy does not name, for a gate that
  workflow does not declare, or signed after the pinned policy version's
  supersession; a tenant the trust names no authority for is
  ``index-unsupported``. The strength of all of it is the custody of three
  things: the door's private key, the approvers' private keys, and Control
  Plane registration under each tenant's HITL policy key. The signed instant
  is the signer's claim, so a backdated signature by a dropped key still
  verifies under the old version; and only the window's supersession bound is
  enforced, because the in-memory Control Plane re-registers every version at
  boot. An adopter-supplied identity provider that verifies nothing accepts
  everything, door signatures included.

Algorithmic package (CINV-03).
"""

from __future__ import annotations

from ccf.erasure.approval import (
    APPROVING_VERDICT,
    ErasureApprovalInvalid,
    PinnedPolicySource,
    policy_head,
    reference_approval_verifier,
    verify_erasure_approval,
)
from ccf.erasure.contracts import (
    ERASURE_APPROVAL_CLASS,
    ERASURE_RECORD_CLASS,
    ERASURE_SUBJECT_DECLARATION,
    REPLAY_INPUT_PATHS,
    RETENTION_HOLD_POLICY,
    RETENTION_REASON_CODES,
    ClassRetention,
    ErasedAddress,
    ErasureApproval,
    ErasureRecord,
    ErasureRequest,
    ErasureSubjectClass,
    ErasureSubjectDeclaration,
    ErasureSubjectLocator,
    LegalHold,
    RequestedAddress,
    RetentionDecision,
    RetentionHoldPolicy,
    RetentionReasonCode,
    judge_retention,
    subject_ref_for,
)
from ccf.erasure.errors import (
    INDEX_CORRUPT,
    ErasureCompositionRefused,
    ErasureIndexCorrupt,
    ErasureIndexInsecure,
    ErasureIndexWriteFailed,
)
from ccf.erasure.index import (
    ERASURE_INDEX_FILENAME,
    GENESIS,
    ErasureIndexEntryExists,
    ErasureIndexEntry,
    ErasureIndexProtocol,
    FileErasureIndex,
    erasure_index_at,
    require_append_authority,
)
from ccf.erasure.store import (
    INDEX_UNSUPPORTED,
    ErasedContentRefused,
    ErasureConsultingStore,
    ErasureIndexUnavailable,
    compose_erasure_consult,
)
from ccf.erasure.trust import (
    DOOR_SIGNATURE_ASSERTION,
    ErasureAuthority,
    ErasureRecordInvalid,
    ErasureTrust,
    sign_erasure_record,
    verify_door_signature,
    verify_erasure_entry,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "APPROVING_VERDICT",
    "ErasureApprovalInvalid",
    "PinnedPolicySource",
    "policy_head",
    "reference_approval_verifier",
    "verify_erasure_approval",
    "DOOR_SIGNATURE_ASSERTION",
    "ErasureAuthority",
    "ErasureRecordInvalid",
    "ErasureTrust",
    "sign_erasure_record",
    "verify_door_signature",
    "verify_erasure_entry",
    "ERASURE_INDEX_FILENAME",
    "ERASURE_APPROVAL_CLASS",
    "ERASURE_RECORD_CLASS",
    "ERASURE_SUBJECT_DECLARATION",
    "GENESIS",
    "INDEX_CORRUPT",
    "INDEX_UNSUPPORTED",
    "REPLAY_INPUT_PATHS",
    "RETENTION_HOLD_POLICY",
    "RETENTION_REASON_CODES",
    "ClassRetention",
    "ErasedAddress",
    "ErasureApproval",
    "ErasedContentRefused",
    "ErasureCompositionRefused",
    "ErasureConsultingStore",
    "ErasureIndexCorrupt",
    "ErasureIndexEntry",
    "ErasureIndexEntryExists",
    "ErasureIndexInsecure",
    "ErasureIndexProtocol",
    "ErasureIndexWriteFailed",
    "ErasureIndexUnavailable",
    "ErasureRecord",
    "ErasureRequest",
    "ErasureSubjectClass",
    "ErasureSubjectDeclaration",
    "ErasureSubjectLocator",
    "FileErasureIndex",
    "LegalHold",
    "RequestedAddress",
    "RetentionDecision",
    "RetentionHoldPolicy",
    "RetentionReasonCode",
    "compose_erasure_consult",
    "erasure_index_at",
    "judge_retention",
    "require_append_authority",
    "subject_ref_for",
]
