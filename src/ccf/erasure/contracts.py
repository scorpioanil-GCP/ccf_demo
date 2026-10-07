"""The erasure contracts — subject, retention and hold, request, record (SEC-009; `D-IMPL-374` (4)).

SDK-defined mechanism, built to design ``docs/D-IMPL-367-ERASURE-DESIGN.md``
§2 and §4 with U1–U12 ruled on the design's recommendations at
``D-IMPL-374`` (4). Everything a deployment decides — what a subject is, which
artifact classes carry one, which classes are erasable for which reasons,
which holds are active, the minimum age, the salt a subject reference is
hashed with — is a declared artifact the SDK interprets; nothing here names a
subject class, an artifact class, a reason or a duration (CLAUDE.md §6.4).

**The one fixed list is the SDK's own field names.**
:data:`REPLAY_INPUT_PATHS` lists the Decision Replay record paths design §2.2
classifies as replay inputs; a subject key path that reaches one is refused at
declaration (U2), so an erasure can never make a recorded decision replay a
different question under the same identifier (G2).

Every defaulted field is declared NOT hash-transparent: these contracts are
new, so there is no yesterday for silence to equal (``D-IMPL-243``; the
``EntityInvalidationRegister`` precedent).

Algorithmic module (CINV-03): no clock is read here — every instant arrives
from the caller's injected fabric clock.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Final, Literal

from pydantic import Field, field_validator, model_validator

from ccf.artifacts.protocol import CONTENT_ADDRESS_PATTERN, parse_artifact_uri
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY, content_hash
from ccf.controlplane.artifact_base import ArtifactClass, VersionedArtifact
from ccf.hitl.principal import ApproverIdentity

__ccf_mode__ = "algorithmic"

__all__ = [
    "ERASURE_RECORD_CLASS",
    "ERASURE_SUBJECT_DECLARATION",
    "REPLAY_INPUT_PATHS",
    "RETENTION_HOLD_POLICY",
    "RETENTION_REASON_CODES",
    "ClassRetention",
    "ErasedAddress",
    "ErasureRecord",
    "ErasureRequest",
    "ErasureSubjectClass",
    "ErasureSubjectDeclaration",
    "LegalHold",
    "RequestedAddress",
    "RetentionDecision",
    "RetentionHoldPolicy",
    "judge_retention",
    "subject_ref_for",
]

#: The artifact class an erasure record is filed under (design §2.3). An SDK
#: mechanism identifier, as ``ccf.approval-policy`` is; the deployment still
#: declares it mechanism-written in its :class:`~ccf.artifacts.protocol.WriteKinds`
#: (under ``Resume`` — the resumption's authority writes it, §4.1).
ERASURE_RECORD_CLASS: Final[str] = "ccf.erasure-record"

#: The Decision Replay record paths that are replay INPUTS (design §2.2, U2):
#: never erased, so never declarable as a subject key path. The SDK's OWN field
#: names — a mechanism constant, not a domain value (U2's ruling).
REPLAY_INPUT_PATHS: Final[tuple[str, ...]] = (
    "perspective_conditioning.principal_id",
    "perspective_conditioning.role",
    "content_generation_path.request",
    "context_fabric_snapshot.touched_entities",
    "policy_bindings.hitl_actions",
    "policy_bindings.bindings",
    "content_generation_path.graph_query_sequence",
    "content_generation_path.operator_plan",
)

#: The retention judgment's refusal codes (design §4.2) — mechanism vocabulary,
#: never a subject identifier.
RETENTION_REASON_CODES: Final[frozenset[str]] = frozenset(
    {
        "admitted",
        "class-absent",
        "not-erasable",
        "severity-exempt",
        "legal-hold",
        "reason-unknown",
        "under-minimum-age",
        "policy-unresolvable",
    }
)


def _hashed_subject_ref(value: str) -> str:
    """Refuse anything but the salted sha256-hex form :func:`subject_ref_for` returns (I1)."""
    if not CONTENT_ADDRESS_PATTERN.match(value):
        raise ValueError(
            "subject_ref must be the salted sha256-hex form subject_ref_for returns;"
            " a raw identifier is refused, because it would be written permanently"
            " into an erasure record and would never match a hold keyed on the"
            " salted reference (SEC-009; D-IMPL-374 (4), I1)"
        )
    return value


def _touches_replay_input(path: str) -> bool:
    """Whether ``path`` equals, lies under, or contains a replay-input path."""
    for reserved in REPLAY_INPUT_PATHS:
        if path == reserved or path.startswith(f"{reserved}.") or reserved.startswith(f"{path}."):
            return True
    return False


class ErasureSubjectClass(CCFContract):
    """What a subject is, for one deployment-declared subject class (G1; SEC-009, `D-IMPL-374` (4)).

    Attributes:
        class_id: Deployment vocabulary for the subject class; never an SDK value.
        key_paths: Dotted canonical-document paths at which an identifier of
            this class appears in artifacts of :attr:`artifact_classes`.
        artifact_classes: The artifact classes whose documents may carry it.
        identifier_kind: ``"opaque"`` only this phase; a ``"principal"``
            subject is refused (U1 — principals reach replay inputs and audit
            actors, and pseudonymization-at-write, U3, is not built).
        subject_ref_salt: The deployment-declared salt a subject identifier is
            hashed with into an erasure record's ``subject_ref`` (U4).
    """

    class_id: str = Field(min_length=1)
    key_paths: tuple[str, ...] = Field(min_length=1)
    artifact_classes: tuple[str, ...] = Field(min_length=1)
    identifier_kind: Literal["opaque", "principal"]
    subject_ref_salt: str = Field(min_length=1)

    @field_validator("key_paths")
    @classmethod
    def _no_replay_input(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        for path in value:
            if not path or "*" in path or any(not part for part in path.split(".")):
                raise ValueError(f"key path {path!r} is not a dotted path without wildcards")
            if _touches_replay_input(path):
                raise ValueError(
                    f"key path {path!r} reaches a replay input"
                    f" ({sorted(REPLAY_INPUT_PATHS)}); erasing it would replay a"
                    " different question under the same decision id, so it cannot"
                    " be declared a subject key (SEC-009; D-IMPL-367 §2.2, U2)"
                )
        return value

    @field_validator("identifier_kind")
    @classmethod
    def _no_principal_subjects(cls, value: str) -> str:
        if value == "principal":
            raise ValueError(
                "a principal identifier cannot be an erasure subject this phase:"
                " it reaches requested_by, started_by, the approver and the HITL"
                " stamps, which are replay inputs and audit actors; the only route"
                " is pseudonymization at write, which is not built (SEC-009;"
                " D-IMPL-374 (4), U1/U3)"
            )
        return value


class ErasureSubjectDeclaration(VersionedArtifact):
    """A deployment's subject classes (G1). Adopter-registered; NOT manifest-addressable (SEC-009; `D-IMPL-374` (4))."""

    tenant_id: str = Field(min_length=1)
    subjects: tuple[ErasureSubjectClass, ...] = Field(min_length=1)

    def subject(self, class_id: str) -> ErasureSubjectClass | None:
        """The declared subject class ``class_id``, or ``None``."""
        return next((s for s in self.subjects if s.class_id == class_id), None)


#: The subject-declaration artifact class (design §2.1).
ERASURE_SUBJECT_DECLARATION = ArtifactClass(
    class_id="ccf.erasure-subject-declaration", contract=ErasureSubjectDeclaration
)


def subject_ref_for(declaration: ErasureSubjectDeclaration, subject_class: str, identifier: str) -> str:
    """The salted hash an erasure record carries instead of the identifier (U4; SEC-009, `D-IMPL-374` (4)).

    ``sha256(salt || 0x00 || identifier)`` under the declared class's
    ``subject_ref_salt``. The raw identifier never enters the fabric: a
    requester computes this, and only the hash is recorded.

    Raises:
        ValueError: ``subject_class`` is not declared.
    """
    declared = declaration.subject(subject_class)
    if declared is None:
        raise ValueError(f"subject class {subject_class!r} is not declared (SEC-009)")
    material = declared.subject_ref_salt.encode("utf-8") + b"\x00" + identifier.encode("utf-8")
    return hashlib.sha256(material).hexdigest()


class LegalHold(CCFContract):
    """One active legal hold (G7): a matching subject or address refuses erasure (SEC-009; `D-IMPL-374` (4)).

    ``subject_refs`` are the salted references (:func:`subject_ref_for`), never
    raw identifiers. ``None`` on either axis matches nothing on that axis.
    """

    hold_id: str = Field(min_length=1)
    subject_refs: tuple[str, ...] | None
    addresses: tuple[str, ...] | None
    placed_at: datetime
    placed_by: str
    basis: str

    @field_validator("subject_refs")
    @classmethod
    def _refs_are_hashed(cls, value: tuple[str, ...] | None) -> tuple[str, ...] | None:
        return None if value is None else tuple(_hashed_subject_ref(ref) for ref in value)


class ClassRetention(CCFContract):
    """Retention and hold policy for one artifact class (G7, default refuse; SEC-009, `D-IMPL-374` (4)).

    Attributes:
        erasable: ``False`` by default — a class is erasable only when declared so.
        severity_exempt: Whitepaper §7.10: significant decisions keep full
            fidelity permanently; an exempt class refuses erasure.
        reasons: The closed reason vocabulary this class admits (G1's rule).
        holds: The active legal holds.
        minimum_age: The window before which erasure refuses, in **whole
            days**. **Present, with no SDK default** (U10): a policy states it,
            ``None`` included. A :class:`~datetime.timedelta` of whole days is
            accepted and held as its day count, because the canonical form has
            no rendering for a duration and a policy must hash.
    """

    erasable: bool = Field(default=False, json_schema_extra={HASH_TRANSPARENT_KEY: False})
    severity_exempt: bool = Field(default=False, json_schema_extra={HASH_TRANSPARENT_KEY: False})
    reasons: tuple[str, ...]
    holds: tuple[LegalHold, ...] = Field(default=(), json_schema_extra={HASH_TRANSPARENT_KEY: False})
    minimum_age: int | None = Field(ge=0)

    @field_validator("minimum_age", mode="before")
    @classmethod
    def _whole_days(cls, value: object) -> object:
        if isinstance(value, timedelta):
            if value % timedelta(days=1):
                raise ValueError("minimum_age is a whole number of days (SEC-009)")
            return value.days
        return value


class RetentionHoldPolicy(VersionedArtifact):
    """A tenant's retention-and-hold policy, keyed by artifact class; an absent class refuses (SEC-009; `D-IMPL-374` (4))."""

    tenant_id: str = Field(min_length=1)
    classes: Mapping[str, ClassRetention]


#: The retention-and-hold policy artifact class (design §4.2).
RETENTION_HOLD_POLICY = ArtifactClass(
    class_id="ccf.retention-hold-policy", contract=RetentionHoldPolicy
)


class RetentionDecision(CCFContract):
    """The structured audit answer of :func:`judge_retention` (G7). Never names a subject (SEC-009; `D-IMPL-374` (4))."""

    policy_ref: str
    verdict: Literal["admit", "refuse"]
    reason_code: str
    hold_id: str | None = Field(default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False})
    address: str | None = Field(default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False})


class RequestedAddress(CCFContract):
    """One artifact a request asks to erase, whole (U5) (SEC-009; `D-IMPL-374` (4)).

    ``retained_since`` is the instant the minimum age is measured from. The
    store's Protocol records no write instant, so it is REQUESTER-DECLARED and
    HUMAN-APPROVED: the approval is bound to the request's content identity,
    this field included.
    """

    content_address: str
    artifact_class: str = Field(min_length=1)
    retained_since: datetime

    @field_validator("content_address")
    @classmethod
    def _is_an_address(cls, value: str) -> str:
        if not CONTENT_ADDRESS_PATTERN.match(value):
            raise ValueError(f"{value!r} is not a content address (SEC-009)")
        return value


class ErasureRequest(CCFContract):
    """What a requester asks the erasure door to erase (design §4.1; SEC-009, `D-IMPL-374` (4)).

    Its content hash, :attr:`request_id`, is the workflow execution id: the
    human approves exactly this request and nothing else.
    """

    tenant_id: str = Field(min_length=1)
    subject_declaration_ref: str
    subject_class: str = Field(min_length=1)
    subject_ref: str = Field(min_length=1)
    addresses: tuple[RequestedAddress, ...] = Field(min_length=1)
    reason: str = Field(min_length=1)
    legal_basis: str
    retention_policy_ref: str

    @field_validator("subject_ref")
    @classmethod
    def _subject_ref_is_hashed(cls, value: str) -> str:
        return _hashed_subject_ref(value)

    @field_validator("subject_declaration_ref", "retention_policy_ref")
    @classmethod
    def _pinned(cls, value: str) -> str:
        parse_artifact_uri(value)
        return value

    @model_validator(mode="after")
    def _addresses_are_distinct(self) -> "ErasureRequest":
        seen = [a.content_address for a in self.addresses]
        if len(seen) != len(set(seen)):
            raise ValueError("an erasure request names each address once (SEC-009)")
        return self

    @property
    def request_id(self) -> str:
        """The request's content identity — the execution id of its workflow."""
        return content_hash(self)


def judge_retention(
    policy: RetentionHoldPolicy,
    *,
    policy_ref: str,
    request: ErasureRequest,
    now: datetime,
) -> RetentionDecision:
    """Judge ``request`` against ``policy`` at the injected instant ``now`` (G7; SEC-009, `D-IMPL-374` (4)).

    Pure and fail-closed (design §4.2): the first address that refuses decides,
    in the order class-absent, severity-exempt, not-erasable, reason-unknown,
    legal-hold, under-minimum-age. No clock is read.
    """
    for address in sorted(request.addresses, key=lambda a: a.content_address):
        retention = policy.classes.get(address.artifact_class)

        def refuse(code: str, hold_id: str | None = None) -> RetentionDecision:
            return RetentionDecision(
                policy_ref=policy_ref, verdict="refuse", reason_code=code,
                hold_id=hold_id, address=address.content_address,
            )

        if retention is None:
            return refuse("class-absent")
        if retention.severity_exempt:
            return refuse("severity-exempt")
        if not retention.erasable:
            return refuse("not-erasable")
        if request.reason not in retention.reasons:
            return refuse("reason-unknown")
        for hold in retention.holds:
            if (hold.subject_refs is not None and request.subject_ref in hold.subject_refs) or (
                hold.addresses is not None and address.content_address in hold.addresses
            ):
                return refuse("legal-hold", hold.hold_id)
        if retention.minimum_age is not None and now - address.retained_since < timedelta(days=retention.minimum_age):
            return refuse("under-minimum-age")
    return RetentionDecision(policy_ref=policy_ref, verdict="admit", reason_code="admitted")


class ErasedAddress(CCFContract):
    """One erased artifact on an erasure record (design §2.3; SEC-009, `D-IMPL-374` (4)).

    ``matched`` says whether every declared key path is PRESENT in the stored
    document — presence only: the fabric never holds the raw identifier to
    compare. ``scope`` is ``"whole"`` this phase (U5).
    """

    content_address: str
    artifact_class: str
    key_paths: tuple[str, ...]
    matched: bool
    scope: Literal["whole", "fields"] = Field(default="whole", json_schema_extra={HASH_TRANSPARENT_KEY: False})


class ErasureRecord(CCFContract):
    """The immutable erasure FACT (G3) — asserted, never retracted (U6) (SEC-009; `D-IMPL-374` (4)).

    Filed as ``ccf.erasure-record`` through the store's one write verb. Nothing
    is deleted: the bytes it names remain on the substrate, and the SDK claims
    no destruction (``D-IMPL-367`` O1).
    """

    tenant_id: str
    record_id: str
    subject_class: str
    subject_ref: str
    addresses: tuple[ErasedAddress, ...] = Field(min_length=1)
    erased_at: datetime
    actor: ApproverIdentity
    requested_by: str
    authorizing_decision_id: str
    approval_policy_ref: str
    retention_decision: RetentionDecision
    reason: str
    legal_basis: str
