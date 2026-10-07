"""Erasure — the MINIMUM SEC-009 mechanism (SDK-defined; `D-IMPL-374` (4); design `D-IMPL-367`).

An erasure is a **fact the fabric records**, never a mutation it performs
(design §1). A deployment declares what a subject is
(:class:`ErasureSubjectDeclaration`) and which artifact classes are erasable
under which reasons, holds and minimum age (:class:`RetentionHoldPolicy`,
default refuse). A request goes through the deployment-declared, factory-
validated one-gate workflow at the erasure door
(``ccf_runtime.erasure.ErasureDoor``); on a human approval it is written as an
immutable :class:`ErasureRecord` through the store's one write verb, and
mirrored into the append-only registry index (:class:`ErasureIndex`) that the
decorating store (:class:`ErasureConsultingStore`, composed ALWAYS) consults on
every read, serving an ``erased-content`` reading instead of the bytes.

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
    LegalHold,
    RequestedAddress,
    RetentionDecision,
    RetentionHoldPolicy,
    judge_retention,
    subject_ref_for,
)
from ccf.erasure.index import (
    ERASURE_INDEX,
    ERASURE_INDEX_SEMVER,
    ErasureIndex,
    ErasureIndexEntry,
    ErasureIndexMirror,
    ErasureIndexSource,
    append_to_erasure_index,
    erasure_index_key,
)
from ccf.erasure.store import ErasedContentRefused, ErasureConsultingStore

__ccf_mode__ = "algorithmic"

__all__ = [
    "ERASURE_INDEX",
    "ERASURE_INDEX_SEMVER",
    "ERASURE_RECORD_CLASS",
    "ERASURE_SUBJECT_DECLARATION",
    "REPLAY_INPUT_PATHS",
    "RETENTION_HOLD_POLICY",
    "RETENTION_REASON_CODES",
    "ClassRetention",
    "ErasedAddress",
    "ErasedContentRefused",
    "ErasureConsultingStore",
    "ErasureIndex",
    "ErasureIndexEntry",
    "ErasureIndexMirror",
    "ErasureIndexSource",
    "ErasureRecord",
    "ErasureRequest",
    "ErasureSubjectClass",
    "ErasureSubjectDeclaration",
    "LegalHold",
    "RequestedAddress",
    "RetentionDecision",
    "RetentionHoldPolicy",
    "append_to_erasure_index",
    "erasure_index_key",
    "judge_retention",
    "subject_ref_for",
]
