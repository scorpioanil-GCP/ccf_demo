"""The HITL transport seam — a typed queue, and the only authority path.

SDK-defined (CLAUDE.md §8.2 — an extension beyond the whitepaper, and it
says so). D-IMPL-20 rules the ``HITLTransportProtocol`` typed queue as the
core mechanism: pending HITL events (ApprovalGate, ExceptionEscalation,
OverrideBoundary, ReviewQueue items) are typed records enqueued by the HITL
primitives, and actions (approve/reject/override/annotate) return through
the same surface. **Notification and authority are separated by ruling**:
this transport carries authority; the webhook leg is notify-only — the
webhook notifies, the action always flows back through this typed queue, so
audit-by-construction cannot be bypassed from a notification channel. The
notify-only webhook emitter ships in :mod:`ccf.hitl.webhook` per D-IMPL-64;
MCP server endpoints exposing these queues are the Experience-Layer
primary (D-IMPL-20) and live on that surface, not here.

**The audit claim is D-22-scoped.** The transport carries the
:class:`~ccf.hitl.principal.HumanPrincipalBinding` — the action-submission
contract requires it by type, so an unattributed action is unrepresentable
through this surface. The *recording* obligation — landing the action in
the Decision Replay record — is discharged by the HITL primitives
(07-07/07-08) that consume this seam, not by the queue: a transport that
recorded replay dimensions itself would be a second writer to the replay
surface.

**The authority path requires the capability for its own action (D-IMPL-353
§1.2, §2 P6).** :meth:`HITLTransportProtocol.submit` takes an
``Authorized[HitlSubmit]`` and :meth:`HITLTransportProtocol.view` an
``Authorized[HitlQueueRead]`` — each verified by
:func:`~ccf.authz.capability.verify` for its kind and for the event
it acts on before the handle's first real statement. The tenant a
submission is filed under and the tenant a view reads are the capability's,
and only the capability's: :class:`HitlActionSubmission` carries no tenant
field, so there is no second source. The recorded actor is the capability's
principal — a binding over anyone else is refused
(:class:`PrincipalMismatchRefused`) — and the record names the authorizer's
decision (``authorizing_decision_id``), transport-stamped like the claim
stamp. The in-process reads the primitives and the workflow engine use
(``pending``, ``submissions``, ``remove``, ``dequeue``) keep their tenant
parameter: those callers hold ``Execute``/``Resume``/``HitlSubmit``
capabilities, not a queue-read one, and in-process trust is the deployment's
(design §5 — the same limit single-writer states). The served doors call
``view`` and ``submit`` and nothing else.

:class:`InMemoryHitlTransport` ships in this module per CLAUDE.md §11
(reference implementations alongside Protocols): it is a reference
implementation, not a placeholder for one — the in-process queue matches
the v0 Control Plane posture, and a durable or remote transport is an
alternative implementation of the same Protocol, added without touching a
consumer.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import threading
from collections import deque
from collections.abc import Mapping
from typing import Literal, Protocol, runtime_checkable

from pydantic import Field, field_validator, model_validator

from ccf.artifacts.protocol import ArtifactStoreError, parse_artifact_uri
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY
from ccf.controlplane.artifact_base import ArtifactClass, validate_semver
from ccf.controlplane.registry import ControlPlaneProtocol
from ccf.hitl.identity_binding import (
    AttestationInvalid,
    HitlActionClaims,
    SignedHitlAction,
    verify_hitl_action,
)
from ccf.hitl.principal import HumanPrincipalBinding, validate_content_hash
from ccf.peering.identity import IdentityProvider, JsonWebKey
from ccf.authz.capability import (
    Authorized,
    HitlQueueRead,
    HitlSubmit,
    verify,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "HITL_ACTIONS",
    "HITL_EVENT_CLASSES",
    "HITL_POLICY",
    "HITLTransportProtocol",
    "HitlActionReceipt",
    "HitlActionRequest",
    "HitlActionSubmission",
    "HitlPolicy",
    "InMemoryHitlTransport",
    "PendingHitlEvent",
    "PrincipalMismatchRefused",
    "SignedBindingInvalidRefused",
    "SignedBindingMismatchRefused",
    "SignedBindingRequiredRefused",
    "SignedBindingStaleRefused",
    "enforce_attestation",
    "resolve_hitl_policy",
    "signed_binding_required",
]

#: The four HITL primitive event classes (CLAUDE.md §8.2). Mechanism
#: identifiers, not domain values: each names an SDK-shipped primitive, and
#: an event declaring anything else is malformed rather than merely unknown.
HITL_EVENT_CLASSES: frozenset[str] = frozenset(
    {
        "approval-gate",
        "exception-escalation",
        "override-boundary",
        "review-queue",
    }
)

#: The action vocabulary D-IMPL-20 names (approve/reject/override/annotate).
#: Mechanism identifiers: which actions a given gate *permits* is the
#: approval policy's statement, never enumerated here.
HITL_ACTIONS: frozenset[str] = frozenset(
    {"approve", "reject", "override", "annotate"}
)


class PendingHitlEvent(CCFContract):
    """One pending HITL event awaiting a human (D-IMPL-20; CLAUDE.md §8.2).

    SDK-defined. The typed record the ruling specifies: event class,
    workflow state reference, the identity of the Context Product the human
    must see (its D-IMPL-26 content hash — the same identity the
    :class:`~ccf.hitl.principal.HumanPrincipalBinding` echoes back, so
    "what was shown" and "what was approved" are comparable byte for byte),
    and the deadline/escalation policy reference, pinned.
    """

    event_key: str
    event_class: str
    tenant: str
    workflow_state_ref: str
    product_content_hash: str
    policy_ref: str | None = None

    @field_validator("event_class")
    @classmethod
    def _event_class_is_a_known_primitive(cls, value: str) -> str:
        if value not in HITL_EVENT_CLASSES:
            raise ValueError(
                f"unknown HITL event class {value!r}; the shipped primitives"
                f" are {sorted(HITL_EVENT_CLASSES)} (CLAUDE.md §8.2;"
                " D-IMPL-20)"
            )
        return value

    @field_validator("policy_ref")
    @classmethod
    def _policy_ref_is_pinned(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            parse_artifact_uri(value)
        except ArtifactStoreError as error:
            raise ValueError(str(error)) from error
        return value


class SignedBindingRequiredRefused(PermissionError):
    """Policy requires a signed attestation and none was presented.

    SDK-defined (CLAUDE.md §8.2); the D-16 composition (08-CONTEXT),
    designed within the D-IMPL-21/63/67 contract envelope. Raised at the
    transport authority path when the Control Plane HITL policy in force
    declares ``signed_binding_required: true`` and the submission carries
    no :class:`~ccf.hitl.identity_binding.SignedHitlAction`. A
    distinct class from :class:`SignedBindingInvalidRefused` so the
    Experience-Layer doors can map absence and invalidity to their own
    error-code constants (``ERROR_SIGNED_BINDING_REQUIRED``).
    """


class SignedBindingInvalidRefused(PermissionError):
    """A signed attestation was presented and its signature does not hold.

    SDK-defined (CLAUDE.md §8.2); D-16 within D-IMPL-21/63/67. Raised when
    the presented attestation fails cryptographic verification
    (:func:`~ccf.hitl.identity_binding.verify_hitl_action`, with the
    typed identity error chained as the cause) under the keys the pinned
    policy declares for its subject. A signature that VERIFIES but whose
    claims disagree with the capability, the request or the minted binding
    is :class:`SignedBindingMismatchRefused` (`D-IMPL-363` E6), not this.
    Maps to ``ERROR_SIGNED_BINDING_INVALID`` at the doors.
    """


class PrincipalMismatchRefused(PermissionError):
    """The submission's binding names a subject other than the capability's principal.

    SDK-defined (CLAUDE.md §8.2; D-IMPL-353 §2 P6). The actor of a recorded
    human action is the principal the authorizer decided *allowed* for —
    ``authorized.principal`` — and the binding is the record of that actor.
    A binding over anyone else binds nothing here, in the same sense a
    validly signed binding over someone else's identity binds nothing
    (:class:`SignedBindingInvalidRefused`). Unreachable from the served doors,
    which mint the binding from the capability; raised for an in-process
    caller that built one for the wrong subject. Refused rather than
    rewritten, because a signed binding covers the subject and a transport
    that overwrote it would record a signature over someone else.
    """


class HitlPolicy(CCFContract):
    """The Control Plane HITL policy artifact (CLAUDE.md §8.2; D-16).

    SDK-defined mechanism schema: which HITL postures a deployment
    requires are the artifact's statements, never code constants
    (No-Hardcoding, CLAUDE.md §6.4). This is the schema behind the
    documented ``hitl.signed_binding_required`` surface examples set in
    their ``artifacts/`` HITL policy YAML: a document like
    ``{semver: "1.0.0", signed_binding_required: true}`` registered under
    the deployment's chosen HITL-policy key.

    Attributes:
        semver: The artifact's own semver lane (whitepaper §6.3).
        signed_binding_required: Whether a submission at the authority
            path must carry a verifiable
            :class:`~ccf.hitl.identity_binding.SignedHitlAction` (the
            ``attestation``; `D-IMPL-363`).
            Defaults to ``False`` when the key is absent from the
            document, so a missing key is well-defined rather than a
            ``KeyError`` — requiredness *true* can only ever come from a
            registered Control Plane value (T-08-07).
    """

    semver: str
    signed_binding_required: bool = False
    #: `D-IMPL-363` E3 — the directional freshness window the shared verifier
    #: applies to a signed attestation, against the RECORDED door-minted
    #: ``action_time`` and never a verifier clock: ``issued_at`` may be at
    #: most ``signature_max_age_seconds`` BEFORE the recorded instant and at
    #: most ``permitted_clock_skew_seconds`` AFTER it. Both are REQUIRED
    #: whenever ``signed_binding_required`` is true — no SDK default
    #: (CINV-01) — and refused at parse when absent, so a required policy
    #: never admits under an invented window. Hash-transparent at ``None``
    #: (CINV-06; D-IMPL-243): a policy written before the window existed keeps
    #: its content address.
    signature_max_age_seconds: int | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    permitted_clock_skew_seconds: int | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    #: `D-IMPL-363` E5 / C6(a) — the ONE trust source: approver subject →
    #: ``kid`` → public JWK. The verifier offers an attestation's verifier
    #: exactly the keys declared for ``claims.subject_id``, so a key trusted
    #: for one approver signs for no other; a ``kid`` not declared for the
    #: subject refuses as a mismatch. Required with ``signed_binding_required``;
    #: hash-transparent at ``None`` for the same reason as the window.
    trusted_keys: Mapping[str, Mapping[str, JsonWebKey]] | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )

    @field_validator("semver")
    @classmethod
    def _semver_is_well_formed(cls, value: str) -> str:
        return validate_semver(value)

    @field_validator("signature_max_age_seconds")
    @classmethod
    def _max_age_is_positive(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("signature_max_age_seconds must be a positive number of seconds (D-IMPL-363 E3)")
        return value

    @field_validator("permitted_clock_skew_seconds")
    @classmethod
    def _skew_is_non_negative(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("permitted_clock_skew_seconds cannot be negative (D-IMPL-363 E3)")
        return value

    @model_validator(mode="after")
    def _a_required_policy_states_its_window_and_keys(self) -> "HitlPolicy":
        """E3 / E5: ``signed_binding_required: true`` without the window or the
        per-subject keys is refused at parse — never admitted with a default
        the deployment did not write (CINV-01)."""
        if not self.signed_binding_required:
            return self
        missing = [
            name
            for name in ("signature_max_age_seconds", "permitted_clock_skew_seconds", "trusted_keys")
            if getattr(self, name) is None
        ]
        if missing:
            raise ValueError(
                "signed_binding_required is true but the policy does not state"
                f" {missing}; a required attestation needs the window and the"
                " per-subject trusted keys the verifier judges it against, and"
                " the SDK supplies no default (D-IMPL-363 E3/E5; CINV-01)"
            )
        return self

    def keys_for(self, subject_id: str) -> Mapping[str, JsonWebKey]:
        """The public keys this policy declares for ``subject_id`` — possibly none."""
        return {} if self.trusted_keys is None else self.trusted_keys.get(subject_id, {})

    def pinned_ref(self, *, key: str, version: str) -> str:
        """The ``key@version`` a submission records as the policy that admitted it (E3)."""
        return f"{key}@{version}"


#: The HITL policy artifact class (CLAUDE.md §8.2; D-16).
HITL_POLICY = ArtifactClass(class_id="ccf.hitl-policy", contract=HitlPolicy)


def signed_binding_required(
    *,
    control_plane: ControlPlaneProtocol | None,
    hitl_policy_key: str | None,
) -> bool:
    """Whether the HITL policy in force requires a signed binding.

    The shared verification helper (D-IMPL-69): one implementation consumed
    by the transport authority path and by every HITL primitive resolution
    surface. Sharing *code* is deliberate and permitted — D-13 forbids only
    verified-marker plumbing between layers (a forgeable trust marker),
    never a shared implementation each layer invokes independently.

    Resolved from the Control Plane per call — the requiredness value lives
    ONLY in the registered :class:`HitlPolicy` artifact, never here
    (T-08-07). An unbound Control Plane or key is the pre-composition
    posture: not required.

    Raises:
        TypeError: the key names a registered artifact that is not a
            :class:`HitlPolicy` — broken deployment wiring.
    """
    resolved = resolve_hitl_policy(
        control_plane=control_plane, hitl_policy_key=hitl_policy_key
    )
    return False if resolved is None else resolved[1].signed_binding_required


def resolve_hitl_policy(
    *,
    control_plane: ControlPlaneProtocol | None,
    hitl_policy_key: str | None,
) -> tuple[str, HitlPolicy] | None:
    """The HITL policy in force and its pinned version, or ``None`` when unbound.

    One resolution for the three readers that need the policy itself rather
    than its boolean — the shared verifier (the window and the per-subject
    keys), the transport's ``hitl_policy_ref`` stamp, and
    :func:`signed_binding_required`. Resolved latest per call, as before
    (`D-IMPL-363` E3: the pin makes replay honest, not admission immutable).

    Raises:
        TypeError: the key names a registered artifact that is not a
            :class:`HitlPolicy` — broken deployment wiring.
    """
    if control_plane is None or hitl_policy_key is None:
        return None
    version, artifact = control_plane.resolve_latest(hitl_policy_key)
    if not isinstance(artifact, HitlPolicy):
        raise TypeError(
            f"artifact under {hitl_policy_key!r} is not a HitlPolicy (got"
            f" {type(artifact).__name__}); the bound policy key must name a"
            " registered ccf.hitl-policy artifact"
        )
    return str(version), artifact


class SignedBindingMismatchRefused(PermissionError):
    """A presented attestation verifies but a signed claim does not match the
    capability or the request (`D-IMPL-363` E6; SEC-005): another tenant,
    another event, a subject other than the capability's principal, a key not
    declared for that subject in the pinned policy, a product hash other than
    the one the door minted, or a verdict other than the one presented.
    Maps to ``signed-binding-mismatch`` at both doors.
    """


class SignedBindingStaleRefused(PermissionError):
    """A presented attestation verifies and matches but is not fresh
    (`D-IMPL-363` E3/E4/E6; SEC-005): ``issued_at`` falls outside the pinned
    window against the RECORDED door instant, or its nonce was already
    presented for this event. Maps to ``signed-binding-stale`` at both doors.
    """


def enforce_attestation(
    authorized: Authorized[HitlSubmit],
    submission: HitlActionSubmission,
    *,
    identity_provider: IdentityProvider | None,
    policy: HitlPolicy,
) -> HitlActionClaims:
    """Refuse the submission unless its attestation holds; return the verified claims.

    The shared verification helper (D-16; D-IMPL-69; D-IMPL-21; `D-IMPL-363`
    E2; CLAUDE.md §8.2): one implementation, invoked independently by the
    transport and by the HITL primitives — idempotent double verification
    (D-13), never a trust marker crossing the layer seam. **It reads no
    clock.** Every comparison is between the signed claims, the capability,
    the door-minted binding on the submission and the pinned policy, so the
    transport site (which has no clock) and a replay re-verify identically.

    In order, after the attestation is present and the wiring is whole:

    1. **Subject ↔ key (E5 / C6(a)).** The envelope's ``key_id`` must be one
       the pinned policy declares for ``claims.subject_id``; any other key
       — trusted for someone else, or for no one — is a mismatch. The
       signature is then verified against exactly those keys.
    2. **Claims ↔ capability and request (E1, C1(a)).** ``tenant`` is the
       capability's; ``event_key`` is the capability's resource;
       ``subject_id`` is the capability's principal and the minted binding's
       approver; ``action`` is the presented action and the minted binding's
       verdict; ``product_content_hash`` is the minted binding's. Each a
       mismatch.
    3. **Freshness (E3), directional, against the RECORDED instant.**
       ``issued_at <= action_time + permitted_clock_skew_seconds`` and
       ``action_time − issued_at <= signature_max_age_seconds``, where
       ``action_time`` is the door-minted ``submission.principal.action_time``
       — never a verifier clock. An absolute delta would admit a claim issued
       after the door recorded the action. Each a stale refusal.

    The nonce is NOT consumed here: reuse is refused by the transport,
    atomically under its lock, at :meth:`InMemoryHitlTransport.submit`
    (E4 / C11(a)), so a verifier that runs twice does not burn it.

    Raises:
        SignedBindingRequiredRefused: the policy requires an attestation and
            the submission carries none.
        SignedBindingInvalidRefused: the attestation's signature does not
            verify under the keys declared for its subject.
        SignedBindingMismatchRefused: a signed claim disagrees with the
            capability, the request, the minted binding, or the key map.
        SignedBindingStaleRefused: ``issued_at`` is outside the window.
        RuntimeError: attestations are required but no identity provider was
            supplied, or the policy states no window — broken deployment
            wiring, not an expected refusal.
    """
    signed = submission.attestation
    if signed is None:
        raise SignedBindingRequiredRefused(
            "the HITL policy in force requires a signed attestation and this"
            " submission carries none (D-16; D-IMPL-21; D-IMPL-69;"
            " D-IMPL-363; CLAUDE.md §8.2)"
        )
    if identity_provider is None:
        raise RuntimeError(
            "the HITL policy requires signed attestations but no identity"
            " provider was supplied — broken composition-root wiring"
        )
    max_age = policy.signature_max_age_seconds
    skew = policy.permitted_clock_skew_seconds
    if max_age is None or skew is None:
        raise RuntimeError(
            "the HITL policy requires signed attestations but states no"
            " freshness window — broken Control Plane wiring (D-IMPL-363 E3)"
        )
    claims = signed.claims
    declared = policy.keys_for(claims.subject_id)
    if signed.key_id not in declared:
        raise SignedBindingMismatchRefused(
            f"key {signed.key_id!r} is not declared for subject"
            f" {claims.subject_id!r} in the HITL policy in force; a key trusted"
            " for another approver, or for no one, signs for no one"
            " (D-IMPL-363 E5)"
        )
    try:
        verified = verify_hitl_action(
            signed, provider=identity_provider, public_keys=declared
        )
    except AttestationInvalid as error:
        raise SignedBindingInvalidRefused(
            "the presented signed attestation does not verify"
            " (D-16; D-IMPL-21; D-IMPL-69; D-IMPL-363)"
        ) from error
    principal = submission.principal
    mismatches: list[str] = []
    if verified.tenant != authorized.tenant:
        mismatches.append("tenant")
    if verified.event_key != authorized.resource:
        mismatches.append("event_key")
    if (
        verified.subject_id != authorized.principal
        or verified.subject_id != principal.approver.subject_id
    ):
        mismatches.append("subject_id")
    if verified.action != submission.action or verified.action != principal.verdict:
        mismatches.append("action")
    if verified.product_content_hash != principal.product_content_hash:
        mismatches.append("product_content_hash")
    if mismatches:
        raise SignedBindingMismatchRefused(
            f"the signed claims {mismatches} do not match the capability, the"
            " request or the door-minted binding; a signature over one"
            " statement does not authorize another (SEC-005; D-IMPL-363 E1)"
        )
    recorded_at = principal.action_time
    ahead = (verified.issued_at - recorded_at).total_seconds()
    behind = (recorded_at - verified.issued_at).total_seconds()
    if ahead > skew:
        raise SignedBindingStaleRefused(
            f"the attestation is post-dated: issued_at is {ahead:.0f}s after"
            f" the recorded action instant, beyond the permitted clock skew of"
            f" {skew}s (D-IMPL-363 E3)"
        )
    if behind > max_age:
        raise SignedBindingStaleRefused(
            f"the attestation is expired: issued_at is {behind:.0f}s before"
            f" the recorded action instant, beyond the signature max age of"
            f" {max_age}s (D-IMPL-363 E3)"
        )
    return verified


class HitlActionRequest(CCFContract):
    """What a caller may say about a human action at a served door (D-IMPL-353 §2 P6).

    SDK-defined (CLAUDE.md §8.2/§8.3). The request half of the authority
    path — the HTTP ``POST /hitl/actions`` body, and the field set the MCP
    ``submit_hitl_action`` tool takes as arguments. Deliberately **not** the
    submission: the :class:`~ccf.hitl.principal.HumanPrincipalBinding` is
    minted by the door from the capability, the verified credential's
    :class:`~ccf.hitl.principal.AuthenticationClaims` and the door's clock
    (:func:`ccf_runtime.identity_binding.principal_from_authorized`), so this
    contract has no ``principal``, no ``subject_id``, no
    ``identity_provider_ref``, no ``method``, no ``assurance_level``, no
    ``session_ref``, no ``action_time`` and no ``tenant``. ``extra=forbid``
    makes a body that still sends any of them a boundary refusal — and a
    caller-typed step-up-MFA claim unrepresentable rather than refused.

    What remains is what only the human can state: which event, which
    action, the content hash of what they actually saw, an optional
    annotation, and — where the HITL policy requires non-repudiation — the
    signed :class:`~ccf.hitl.identity_binding.HitlActionClaims` the human
    made about this action (D-16; `D-IMPL-363` E1): the ``attestation``, one
    object in one shape at both doors (C12(a)), replacing the former signed
    copy of the door-minted binding whose ``action_time`` a signer had to
    predict.
    """

    event_key: str
    action: str
    product_content_hash: str
    annotation: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    attestation: SignedHitlAction | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )

    @field_validator("action")
    @classmethod
    def _action_is_known(cls, value: str) -> str:
        if value not in HITL_ACTIONS:
            raise ValueError(
                f"unknown HITL action {value!r}; the typed queue carries"
                f" {sorted(HITL_ACTIONS)} (D-IMPL-20)"
            )
        return value

    @field_validator("product_content_hash")
    @classmethod
    def _product_hash_is_a_content_hash(cls, value: str) -> str:
        return validate_content_hash(value)


class HitlActionSubmission(CCFContract):
    """One human action returning through the authority path (D-IMPL-20/21).

    SDK-defined. ``principal`` is required by type: there is no way to
    construct a submission without a complete
    :class:`~ccf.hitl.principal.HumanPrincipalBinding`, which is how the
    no-unrecorded-human-action commitment (CLAUDE.md §8.2) is enforced at
    the contract boundary rather than audited after the fact.

    **No tenant field (D-IMPL-353 §1.3).** The tenant a submission is filed
    under is the capability's — ``authorized.tenant`` at
    :meth:`HITLTransportProtocol.submit` — and a second source on the
    contract would be a value a door could forget to compare. Deleted, not
    deprecated: a document that still carries one is refused at the boundary.
    """

    event_key: str
    action: str
    principal: HumanPrincipalBinding
    annotation: str | None = None
    #: The optional D-16 non-repudiation leg (`D-IMPL-363` E1): the signer's
    #: detached-JWS-signed :class:`~ccf.hitl.identity_binding.HitlActionClaims`.
    #: Whether it is required is the Control Plane HITL policy's statement
    #: (:class:`HitlPolicy`), enforced at the transport authority path —
    #: never a code constant. When present it travels on the recorded
    #: submission, so the audit/receipt surface and the dimension-2 block
    #: carry it verbatim. Hash-transparent at ``None`` (CINV-06; D-IMPL-243):
    #: an unsigned submission renders exactly as it did before the field
    #: existed. Replaces ``signed_binding``, a base-roster field retired by
    #: ruling under `D-IMPL-363` (replaced, not deprecated).
    attestation: SignedHitlAction | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    #: **Transport-stamped, never caller-authored** (`D-IMPL-363` E3): the
    #: pinned ``key@version`` of the :class:`HitlPolicy` that was in force
    #: when this submission was admitted — so the recorded submission, which
    #: the engine's authority join consumes later and the dimension-2 block
    #: embeds, says which window and which keys decided its admission.
    #: Stamped whenever a Control Plane and a policy key are bound; ``None``
    #: on an unbound transport, hash-transparent at that sentinel. The pin
    #: makes replay honest; it does not make admission immutable — the policy
    #: is resolved latest at submit.
    hitl_policy_ref: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    #: **Transport-stamped, never caller-authored** (SEC-001 Tier 0; the
    #: 2026-09-24 follow-up read). The :data:`HITL_EVENT_CLASSES` member of
    #: the pending event this action was recorded as answering, and that
    #: event's ``workflow_state_ref``. A submitter cannot decide either:
    #: :meth:`HITLTransportProtocol.submit` overwrites both from the event
    #: the transport ITSELF observed being claimed through
    #: :meth:`HITLTransportProtocol.remove`, and writes ``None`` when no
    #: claim exists. Declared on the contract rather than kept in a
    #: side-table because the stamp travels with the action wherever the
    #: recorded submission travels.
    #:
    #: They are what lets a consumer of
    #: :meth:`HITLTransportProtocol.submissions` ask **which primitive
    #: answered, and about which execution** — questions a submission could
    #: not answer before, so an approval-gate authority check could be
    #: satisfied by an action taken against an escalation, an override or a
    #: review item that happened to name the same event key.
    #:
    #: **Hash-transparent at the sentinel (CINV-06; D-IMPL-243).** ``None``
    #: here is not "an older record that did not declare" — it is a live,
    #: current state the transport writes on purpose: *this submitter
    #: claimed nothing*. That is exactly what was true of every submission
    #: recorded before the stamp existed, so "silence equals yesterday"
    #: holds literally and the two fields render into
    #: :func:`~ccf.contracts.canonical.canonical_bytes` only once a claim
    #: was actually observed. Note the direction, because it is what
    #: separates this from the ``False`` cases: the sentinel is the
    #: RESTRICTIVE reading everywhere it is consumed — an unstamped
    #: submission fails the gate check's stamped leg and the escalation
    #: authority join outright — so an unset value never means
    #: "unconstrained".
    answered_event_class: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    answered_workflow_state_ref: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    #: **Transport-stamped, never caller-authored** (D-IMPL-353 §2 P6; design
    #: §3, *deny audit contents*). The ``decision_id`` of the authorizer's
    #: *allow* the capability presented at :meth:`HITLTransportProtocol.submit`
    #: is evidence of — so every recorded human action is traceable to the
    #: decision that authorized it. Overwritten from ``authorized`` on every
    #: submit, exactly as the claim stamp is; a caller-supplied value is
    #: discarded. Hash-transparent at the sentinel (CINV-06; D-IMPL-243):
    #: ``None`` is what was true of every submission recorded before the
    #: capability existed.
    authorizing_decision_id: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )

    @field_validator("action")
    @classmethod
    def _action_is_known(cls, value: str) -> str:
        if value not in HITL_ACTIONS:
            raise ValueError(
                f"unknown HITL action {value!r}; the typed queue carries"
                f" {sorted(HITL_ACTIONS)} (D-IMPL-20)"
            )
        return value


class HitlActionReceipt(CCFContract):
    """The honest submit-only receipt (D-IMPL-62).

    SDK-defined. D-IMPL-62 rules the HTTP/CLI HITL action door submit-only:
    a submission enqueues on the typed transport and effects no state
    transition and no authority action by itself — the owning primitive
    resolves it. This receipt is the ruled hardening of that contract:
    ``status`` is the literal ``"submitted"`` (it cannot state or imply
    ``resolved`` — the field is type-closed to the one honest word), and
    the two disposition fields carry real queue state so the caller sees
    the action's disposition rather than inferring it from an echo:
    ``event_pending`` — whether the submission's event is still on the
    tenant's pending queue (it is, immediately after a submit; resolution
    is the primitive's act) — and ``submissions_for_event`` — how many
    actions the transport has recorded against this event key, this one
    included.
    """

    status: Literal["submitted"]
    submission: HitlActionSubmission
    event_pending: bool
    submissions_for_event: int


@runtime_checkable
class HITLTransportProtocol(Protocol):
    """The typed HITL queue surface (D-IMPL-20; CLAUDE.md §8.2).

    A Protocol because delivery to humans is the deployment's
    infrastructure — an enterprise task system, an MCP-exposed queue, a
    bespoke pager — and the SDK has no business choosing
    (:class:`InMemoryHitlTransport` is the development reference, not a
    recommendation). What the Protocol omits is deliberate: there is no
    notification hook here — webhooks are notify-only and live in
    :mod:`ccf.hitl.webhook` (D-IMPL-64) — and no replay handle: recording
    is the primitives' obligation.

    ``runtime_checkable`` supports composition-root wiring checks; it
    verifies method presence only, so static conformance still rests on
    mypy.

    **Concurrency contract (WR-02; D-IMPL-69 adjacency; CLAUDE.md §8.2).**
    All methods of every conforming implementation must be safe for
    concurrent calls from multiple threads. The Experience-Layer HITL
    doors (HTTP and MCP) invoke the transport from FastAPI's threadpool,
    so enqueue/dequeue/pending/remove/submit/submissions race by
    construction in any real deployment — an implementation whose queue
    state can be lost, duplicated, or corrupted under concurrent access
    does not conform to this Protocol. ``remove`` exists precisely for
    that mode (WR-02): consuming one resolved event must be a single
    atomic operation of the implementation, because a caller-side
    drain-and-requeue over ``dequeue``/``enqueue`` exposes concurrent
    readers to a partially drained queue and lets two racing resolves
    double-submit. This docstring is the contract's sole documentation
    surface (Phase-9 CONTEXT D-05/D-08).
    """

    def enqueue(self, *, event: PendingHitlEvent) -> None:
        """Queue ``event`` for its tenant, preserving arrival order.

        An enqueue discards any outstanding claim (see :meth:`remove`) for
        the same ``(tenant, event_key)``: a re-enqueued event is pending
        again, so nothing has answered it. That is what keeps the
        primitives' give-the-claim-back rollback honest — a refused
        authority submission must leave no residue that a later bare
        submission could inherit as a stamp.
        """
        ...

    def dequeue(self, *, tenant: str) -> PendingHitlEvent | None:
        """Pop the oldest pending event for ``tenant``, or ``None``.

        A drain, not a resolution: it records no claim, so a submission
        made against a drained event carries no stamp (see :meth:`submit`).
        """
        ...

    def pending(self, *, tenant: str) -> tuple[PendingHitlEvent, ...]:
        """The tenant's pending events, oldest first, without consuming."""
        ...

    def remove(
        self, *, tenant: str, event_key: str
    ) -> PendingHitlEvent | None:
        """Atomically remove and return the tenant's pending event with
        ``event_key``, or ``None`` when no such event is pending.

        The compare-and-consume primitive (WR-02): removal is one atomic
        operation of the conforming implementation — never a caller-side
        drain-and-requeue over ``dequeue``/``enqueue``, which would expose
        concurrent readers to a partially drained queue and let two
        concurrent resolves both pass a ``pending()`` snapshot check. The
        relative order of every event not removed is preserved. Exactly
        one of any number of concurrent ``remove`` calls for the same
        event receives it; the rest receive ``None``.

        **Removal is a claim, and the transport records it** (SEC-001 Tier
        0). The winning caller is the primitive that is about to resolve
        this event, so the transport retains the removed event against
        ``(tenant, event_key)`` and stamps the next :meth:`submit` for that
        pair with its class and ``workflow_state_ref``. The claim is
        consumed by that submit and discarded by a re-:meth:`enqueue`;
        conforming implementations must do both, because a consumer asking
        "which primitive answered this?" gets ``None`` — and must fail
        closed — from an implementation that stamps nothing.
        """
        ...

    def view(
        self, authorized: Authorized[HitlQueueRead]
    ) -> tuple[PendingHitlEvent, ...]:
        """The served queue view: the capability's tenant's pending events.

        The read the Experience-Layer doors make (D-IMPL-353 §1.2). Requires
        an ``Authorized[HitlQueueRead]`` — verified for its kind and for the
        door's own action id as resource, since a queue is addressed by
        tenant alone and the tenant is the capability's — and returns what
        :meth:`pending` would for ``authorized.tenant``. There is no tenant
        parameter: whose queue is read is not a thing the door decides.
        """
        ...

    def submit(
        self,
        authorized: Authorized[HitlSubmit],
        *,
        submission: HitlActionSubmission,
    ) -> HitlActionSubmission:
        """Record one human action returning through the authority path.

        Requires an ``Authorized[HitlSubmit]`` for exactly
        ``submission.event_key`` (D-IMPL-353 §1.2, §1.5f), verified before
        the handle's first real statement; files the record under
        ``authorized.tenant``; refuses a binding whose subject is not
        ``authorized.principal`` (:class:`PrincipalMismatchRefused`).

        The recorded submission is stamped with the class and
        ``workflow_state_ref`` of the event this action claimed — taken
        from the transport's own :meth:`remove` observation, never from
        ``submission`` — stamped ``None`` when this submitter claimed
        nothing, and stamped with the capability's ``decision_id``.
        ``submission`` itself is not mutated (it is a frozen contract); the
        stamped copy is what :meth:`submissions` returns, and it is returned
        here so a door can answer with what was recorded rather than with
        an echo of what was sent.
        """
        ...

    def submissions(self, *, tenant: str) -> tuple[HitlActionSubmission, ...]:
        """The tenant's recorded actions, oldest first."""
        ...


class InMemoryHitlTransport:
    """In-process reference implementation of :class:`HITLTransportProtocol`.

    Ships alongside the Protocol per CLAUDE.md §11 — a reference
    implementation, not a placeholder for one. Queues are partitioned by
    tenant (D-23): two tenants' events and actions never interleave, and a
    view of one tenant's queue says nothing about another's.

    **The D-16 composition (SDK-defined; CLAUDE.md §8.2; within
    D-IMPL-21/63/67).** When a Control Plane and an HITL-policy key are
    bound at construction, :meth:`submit` resolves the policy in force at
    submission time and — when it declares ``signed_binding_required`` —
    verifies the submission's attestation through
    :func:`enforce_attestation` and refuses a reused nonce under its lock
    before recording (`D-IMPL-363`). The policy is re-resolved per submission, so
    registering a flipped value changes behavior with zero code change.
    All four D-16 arguments are optional together: an unconfigured
    transport behaves exactly as before this composition existed.

    **Thread safety (WR-02; Phase-9 CONTEXT D-06).** A single plain
    :class:`threading.Lock` guards every queue mutation and snapshot read
    — the Protocol's concurrency contract, discharged here. The lock
    scope is deliberately minimal: D-16 verification
    (:meth:`_signed_binding_required` — a Control Plane resolve — and
    :func:`enforce_attestation` — JWS verification) runs *outside*
    the lock, per D-IMPL-69's "JWS verification stays outside any
    transport lock." A refused submission never touches the queues, so
    the refusal contract is unaffected; no locked method calls another
    locked method, so no reentrant locking is needed.

    Args:
        control_plane: The registry the HITL policy resolves through. The
            deployment's composition root supplies it; the transport never
            constructs one.
        hitl_policy_key: The Control Plane key the deployment registered
            its :class:`HitlPolicy` under — deployment vocabulary, no
            default (CINV-01).
        identity_provider: The D-IMPL-15 provider signatures verify
            through when the policy requires them. The keys they verify
            under are the pinned :class:`HitlPolicy`'s per-subject map —
            the ONE trust source (`D-IMPL-363` E5 / C6(a)); there is no
            constructor fallback.
    """

    def __init__(
        self,
        *,
        control_plane: ControlPlaneProtocol | None = None,
        hitl_policy_key: str | None = None,
        identity_provider: IdentityProvider | None = None,
    ) -> None:
        self._lock = threading.Lock()
        self._pending: dict[str, deque[PendingHitlEvent]] = {}
        self._submissions: dict[str, list[HitlActionSubmission]] = {}
        #: Nonces already presented, keyed ``(tenant, event_key, nonce)`` —
        #: the reference transport's seen-set (`D-IMPL-363` E4 / C11(a)).
        #: Checked and inserted in ONE step under the lock, after
        #: verification and before recording, so two racing presentations
        #: of one attestation cannot both land. Retained for the transport's
        #: lifetime; a user-implemented transport stays as replayable as
        #: before until the Protocol amendment (1.0.3, its own entry).
        self._seen_nonces: set[tuple[str, str, str]] = set()
        #: Events claimed through :meth:`remove` and not yet answered or
        #: given back, keyed ``(tenant, event_key)`` — the transport's own
        #: record of which primitive is resolving what (SEC-001 Tier 0).
        #: Guarded by the same lock as the queues.
        self._claims: dict[tuple[str, str], PendingHitlEvent] = {}
        self._control_plane = control_plane
        self._hitl_policy_key = hitl_policy_key
        self._identity_provider = identity_provider

    def _signed_binding_required(self) -> bool:
        """Whether the policy in force requires a signed binding.

        Resolved from the Control Plane per call — the requiredness value
        lives ONLY in the registered :class:`HitlPolicy` artifact, never
        here (T-08-07). An unbound Control Plane or key is the
        pre-composition posture: not required.
        """
        return signed_binding_required(
            control_plane=self._control_plane,
            hitl_policy_key=self._hitl_policy_key,
        )

    def enqueue(self, *, event: PendingHitlEvent) -> None:
        """Queue ``event`` for its tenant, preserving arrival order.

        Any outstanding claim for the same ``(tenant, event_key)`` is
        discarded: the event is pending again, so nothing has answered it.
        This is what makes the primitives' rollback path
        (``remove`` → failed ``submit`` → ``enqueue``) leave no stamp
        behind for a later bare submission to inherit.
        """
        with self._lock:
            self._claims.pop((event.tenant, event.event_key), None)
            self._pending.setdefault(event.tenant, deque()).append(event)

    def dequeue(self, *, tenant: str) -> PendingHitlEvent | None:
        """Pop the oldest pending event for ``tenant``, or ``None``."""
        with self._lock:
            queue = self._pending.get(tenant)
            if not queue:
                return None
            return queue.popleft()

    def pending(self, *, tenant: str) -> tuple[PendingHitlEvent, ...]:
        """The tenant's pending events, oldest first, without consuming."""
        with self._lock:
            return tuple(self._pending.get(tenant, ()))

    def remove(
        self, *, tenant: str, event_key: str
    ) -> PendingHitlEvent | None:
        """Atomically remove and return the named pending event (WR-02).

        One lock acquisition covers the search and the removal, so a
        concurrent ``pending()`` never observes a partially drained
        queue, a concurrent ``enqueue`` never interleaves into a drain,
        and exactly one of any number of racing removals for the same
        event key receives the event. Every retained event keeps its
        relative order.

        The removal is recorded as a claim in the same lock acquisition
        (SEC-001 Tier 0), so the next :meth:`submit` for this pair is
        stamped with what was actually claimed. Only the winner records a
        claim, because only the winner removes anything.
        """
        with self._lock:
            queue = self._pending.get(tenant)
            if not queue:
                return None
            for index, event in enumerate(queue):
                if event.event_key == event_key:
                    del queue[index]
                    self._claims[(tenant, event_key)] = event
                    return event
            return None

    def view(
        self, authorized: Authorized[HitlQueueRead]
    ) -> tuple[PendingHitlEvent, ...]:
        """The capability's tenant's pending events, oldest first.

        :func:`~ccf.authz.capability.verify` first: the kind by
        identity, and the resource against the queue-read action id — the
        one honest resource for a read addressed by tenant alone (the HTTP
        door's ``ResourceBinding.route()`` semantics). After that line the
        tenant is ``authorized.tenant`` and nothing else.
        """
        verify(authorized, kind=HitlQueueRead, resource=HitlQueueRead.action_id)
        return self.pending(tenant=authorized.tenant)

    def submit(
        self,
        authorized: Authorized[HitlSubmit],
        *,
        submission: HitlActionSubmission,
    ) -> HitlActionSubmission:
        """Record one human action returning through the authority path.

        **The capability first (D-IMPL-353 §1.5c/f).** A fabricated
        capability, a genuine one of another kind, or a submit capability
        minted for some other event dies at
        :func:`~ccf.authz.capability.verify` before anything below
        runs — before the binding is compared, before the policy is
        resolved, before the lock is taken. Then the binding's subject must
        be the capability's principal: the recorded actor has one source.

        When the Control Plane HITL policy in force requires a signed
        attestation, the submission is verified by
        :func:`enforce_attestation` before anything is recorded (D-16): a
        refused submission never lands on the queue. Verification runs
        outside the lock and before the claim is consumed, so a refusal
        leaves both the pending event and its claim untouched (D-IMPL-69;
        Pitfall 4). The nonce is then checked and inserted in ONE step under
        the lock, after verification and before recording (`D-IMPL-363` E4 /
        C11(a)), and the recorded copy carries ``hitl_policy_ref`` — the
        ``key@version`` of the policy that judged it, where ``version`` is
        the Control Plane's version identifier for the pinned artifact.

        What is recorded is a copy stamped with the claim this submitter
        actually made — ``answered_event_class`` and
        ``answered_workflow_state_ref`` come from the event the transport
        observed being :meth:`remove`\\ d, never from ``submission``, and
        are stamped ``None`` when nothing was claimed. A caller-supplied
        value on either field is therefore discarded rather than trusted
        (SEC-001 Tier 0: a guard whose input the caller supplies is not a
        guard).

        **Residual: the claim is addressed, not held.** A claim is keyed
        ``(tenant, event_key)`` and consumed by whichever submission for
        that pair arrives first, because ``submit`` has no caller identity
        to bind it to. A submitter that races the window a primitive opens
        between its ``remove`` and its ``submit`` — the two adjacent
        statements in
        :meth:`~ccf.hitl.approval_gate.ApprovalGate.resolve` — therefore
        takes the stamp, and the primitive's own submission is recorded
        unstamped. Closing it means ``remove`` minting an opaque claim
        token that ``submit`` requires, which is a
        :class:`HITLTransportProtocol` signature change and belongs with
        the D-IMPL-62 door ruling rather than here. Recorded because it
        NARROWS an existing hole rather than opening one: a submit-only
        submission that wins no race is still admitted by the engine's
        unstamped fallback leg today, with no race at all.

        Raises:
            CapabilityBypassError: ``authorized`` is not a genuine
                ``Authorized[HitlSubmit]`` for ``submission.event_key``.
            PrincipalMismatchRefused: the binding's subject is not
                ``authorized.principal``.
            SignedBindingRequiredRefused: attestation required and absent.
            SignedBindingInvalidRefused: the attestation's signature does
                not verify under the keys declared for its subject.
            SignedBindingMismatchRefused: a signed claim disagrees with the
                capability, the request, the door-minted binding or the
                per-subject key map (`D-IMPL-363` E6).
            SignedBindingStaleRefused: ``issued_at`` is outside the policy's
                window against the recorded ``action_time``, or the nonce
                was already presented for this ``(tenant, event_key)``
                (`D-IMPL-363` E3 / E4).
        """
        verify(authorized, kind=HitlSubmit, resource=submission.event_key)
        if submission.principal.approver.subject_id != authorized.principal:
            raise PrincipalMismatchRefused(
                "the submission's binding names a subject other than the"
                " capability's principal; the actor of a recorded human"
                " action is the principal the authorizer decided for, and a"
                " binding over anyone else binds nothing here"
                " (D-IMPL-353 §2 P6; D-IMPL-21)"
            )
        resolved = resolve_hitl_policy(
            control_plane=self._control_plane,
            hitl_policy_key=self._hitl_policy_key,
        )
        policy_ref: str | None = None
        verified: HitlActionClaims | None = None
        if resolved is not None:
            version, policy = resolved
            assert self._hitl_policy_key is not None
            policy_ref = policy.pinned_ref(key=self._hitl_policy_key, version=version)
            if policy.signed_binding_required:
                # Outside the lock, before the claim is consumed (D-IMPL-69).
                verified = enforce_attestation(
                    authorized,
                    submission,
                    identity_provider=self._identity_provider,
                    policy=policy,
                )
        tenant = authorized.tenant
        with self._lock:
            if verified is not None:
                # E4 / C11(a): the nonce check and insert are ONE step under
                # the lock, after verification and before anything is
                # recorded — a reuse refuses here and lands nothing, and two
                # racing presentations cannot both pass.
                nonce_key = (tenant, verified.event_key, verified.nonce)
                if nonce_key in self._seen_nonces:
                    raise SignedBindingStaleRefused(
                        "the attestation's nonce was already presented for"
                        f" event {verified.event_key!r}; a signed statement"
                        " is admitted once (D-IMPL-363 E4)"
                    )
                self._seen_nonces.add(nonce_key)
            claimed = self._claims.pop((tenant, submission.event_key), None)
            recorded = submission.model_copy(
                update={
                    "answered_event_class": (
                        None if claimed is None else claimed.event_class
                    ),
                    "answered_workflow_state_ref": (
                        None if claimed is None else claimed.workflow_state_ref
                    ),
                    "authorizing_decision_id": authorized.decision_id,
                    "hitl_policy_ref": policy_ref,
                }
            )
            self._submissions.setdefault(tenant, []).append(recorded)
        return recorded

    def submissions(self, *, tenant: str) -> tuple[HitlActionSubmission, ...]:
        """The tenant's recorded actions, oldest first."""
        with self._lock:
            return tuple(self._submissions.get(tenant, ()))
