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
replay-input field (fix round 1: C2, I6, (iv), §7). On a RECORDED human
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
* **Enumeration is the deployment's** (ruling (iv)): the fabric verifies the
  addresses a request names; where a subject's artifacts are is the
  deployment's to know (:class:`ErasureSubjectLocator`, declared without a
  reference implementation).
* A tenantless read (the replay engine, ``record_of``, child admission, the MCP
  client lane) withholds an address ANY tenant erased, redacted (ruling (i)).
* The ``erasure_index_unsupported`` audit event carries the disputed entry's
  own ``erased_at`` as its instant (the decorating store reads no clock); the
  audit log's sequence number orders it.
* ``subject_ref_salt`` sits in a Control Plane artifact beside the hashes it
  salts; for a low-entropy identifier the reference is dictionary-reversible
  by a reader of that artifact (U4, as ruled).

Algorithmic package (CINV-03).
"""

from __future__ import annotations

from ccf.erasure.contracts import (
    ERASURE_RECORD_CLASS,
    ERASURE_SUBJECT_DECLARATION,
    REPLAY_INPUT_PATHS,
    RETENTION_HOLD_POLICY,
    RETENTION_REASON_CODES,
    ClassRetention,
    ErasedAddress,
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
from ccf.erasure.index import (
    ERASURE_INDEX_FILENAME,
    ErasureIndexEntryExists,
    ErasureIndexEntry,
    ErasureIndexProtocol,
    FileErasureIndex,
    erasure_index_at,
)
from ccf.erasure.store import (
    INDEX_UNSUPPORTED,
    ErasedContentRefused,
    ErasureConsultingStore,
    ErasureIndexUnavailable,
    compose_erasure_consult,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "ERASURE_INDEX_FILENAME",
    "ERASURE_RECORD_CLASS",
    "ERASURE_SUBJECT_DECLARATION",
    "INDEX_UNSUPPORTED",
    "REPLAY_INPUT_PATHS",
    "RETENTION_HOLD_POLICY",
    "RETENTION_REASON_CODES",
    "ClassRetention",
    "ErasedAddress",
    "ErasedContentRefused",
    "ErasureConsultingStore",
    "ErasureIndexEntryExists",
    "ErasureIndexEntry",
    "ErasureIndexProtocol",
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
    "subject_ref_for",
]
