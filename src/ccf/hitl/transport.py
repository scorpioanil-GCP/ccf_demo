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

from pydantic import field_validator

from ccf.artifacts.protocol import ArtifactStoreError, parse_artifact_uri
from ccf.contracts.base import CCFContract
from ccf.controlplane.artifact_base import ArtifactClass, validate_semver
from ccf.controlplane.registry import ControlPlaneProtocol
from ccf.hitl.identity_binding import (
    PrincipalBindingInvalid,
    SignedPrincipalBinding,
    verify_principal_binding,
)
from ccf.hitl.principal import HumanPrincipalBinding
from ccf.peering.identity import IdentityProvider, JsonWebKey

__ccf_mode__ = "algorithmic"

__all__ = [
    "HITL_ACTIONS",
    "HITL_EVENT_CLASSES",
    "HITL_POLICY",
    "HITLTransportProtocol",
    "HitlActionReceipt",
    "HitlActionSubmission",
    "HitlPolicy",
    "InMemoryHitlTransport",
    "PendingHitlEvent",
    "SignedBindingInvalidRefused",
    "SignedBindingRequiredRefused",
    "enforce_signed_binding",
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
    """Policy requires a signed principal binding and none was presented.

    SDK-defined (CLAUDE.md §8.2); the D-16 composition (08-CONTEXT),
    designed within the D-IMPL-21/63/67 contract envelope. Raised at the
    transport authority path when the Control Plane HITL policy in force
    declares ``signed_binding_required: true`` and the submission carries
    no :class:`~ccf.hitl.identity_binding.SignedPrincipalBinding`. A
    distinct class from :class:`SignedBindingInvalidRefused` so the
    Experience-Layer doors can map absence and invalidity to their own
    error-code constants (``ERROR_SIGNED_BINDING_REQUIRED``).
    """


class SignedBindingInvalidRefused(PermissionError):
    """A signed principal binding was presented and does not hold.

    SDK-defined (CLAUDE.md §8.2); D-16 within D-IMPL-21/63/67. Raised when
    the presented binding fails cryptographic verification
    (:func:`~ccf.hitl.identity_binding.verify_principal_binding`, with the
    typed identity error chained as the cause) or when the verified
    binding's principal does not equal the submission's principal — a
    validly signed binding over someone else's identity binds nothing
    here (spoofing, T-08-06). Maps to ``ERROR_SIGNED_BINDING_INVALID``
    at the doors.
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
            :class:`~ccf.hitl.identity_binding.SignedPrincipalBinding`.
            Defaults to ``False`` when the key is absent from the
            document, so a missing key is well-defined rather than a
            ``KeyError`` — requiredness *true* can only ever come from a
            registered Control Plane value (T-08-07).
    """

    semver: str
    signed_binding_required: bool = False

    @field_validator("semver")
    @classmethod
    def _semver_is_well_formed(cls, value: str) -> str:
        return validate_semver(value)


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
    if control_plane is None or hitl_policy_key is None:
        return False
    _, artifact = control_plane.resolve_latest(hitl_policy_key)
    if not isinstance(artifact, HitlPolicy):
        raise TypeError(
            f"artifact under {hitl_policy_key!r} is not a HitlPolicy (got"
            f" {type(artifact).__name__}); the bound policy key must name a"
            " registered ccf.hitl-policy artifact"
        )
    return artifact.signed_binding_required


def enforce_signed_binding(
    submission: HitlActionSubmission,
    *,
    identity_provider: IdentityProvider | None,
    trusted_keys: Mapping[str, JsonWebKey] | None,
) -> None:
    """Refuse the submission unless its signed binding holds.

    The shared verification helper (D-16; D-IMPL-69; D-IMPL-21;
    CLAUDE.md §8.2): one implementation, invoked independently by the
    transport and by the HITL primitives — idempotent double verification
    (D-13), never a trust marker crossing the layer seam.

    Raises:
        SignedBindingRequiredRefused: the policy requires a binding and
            the submission carries none.
        SignedBindingInvalidRefused: the binding fails verification, or
            its verified principal is not the submission's.
        RuntimeError: bindings are required but no identity provider or
            trusted keys were supplied — broken deployment wiring, not an
            expected refusal.
    """
    if submission.signed_binding is None:
        raise SignedBindingRequiredRefused(
            "the HITL policy in force requires a signed principal"
            " binding and this submission carries none (D-16;"
            " D-IMPL-21; D-IMPL-69; CLAUDE.md §8.2)"
        )
    if identity_provider is None or trusted_keys is None:
        raise RuntimeError(
            "the HITL policy requires signed bindings but no identity"
            " provider or trusted keys were supplied — broken"
            " composition-root wiring"
        )
    try:
        verified = verify_principal_binding(
            submission.signed_binding,
            provider=identity_provider,
            public_keys=trusted_keys,
        )
    except PrincipalBindingInvalid as error:
        raise SignedBindingInvalidRefused(
            "the presented signed principal binding does not verify"
            " (D-16; D-IMPL-21; D-IMPL-69)"
        ) from error
    if verified != submission.principal:
        raise SignedBindingInvalidRefused(
            "the verified signed binding's principal is not the"
            " submission's principal; a valid signature over a"
            " different identity binds nothing here (D-16; T-08-06)"
        )


class HitlActionSubmission(CCFContract):
    """One human action returning through the authority path (D-IMPL-20/21).

    SDK-defined. ``principal`` is required by type: there is no way to
    construct a submission without a complete
    :class:`~ccf.hitl.principal.HumanPrincipalBinding`, which is how the
    no-unrecorded-human-action commitment (CLAUDE.md §8.2) is enforced at
    the contract boundary rather than audited after the fact.
    """

    event_key: str
    tenant: str
    action: str
    principal: HumanPrincipalBinding
    annotation: str | None = None
    #: The optional D-16 non-repudiation leg: a detached-JWS-signed copy of
    #: the principal binding (D-IMPL-21 reference impl #2). Whether it is
    #: required is the Control Plane HITL policy's statement
    #: (:class:`HitlPolicy`), enforced at the transport authority path —
    #: never a code constant. When present it travels on the recorded
    #: submission, so the audit/receipt surface carries it verbatim.
    signed_binding: SignedPrincipalBinding | None = None

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
        """Queue ``event`` for its tenant, preserving arrival order."""
        ...

    def dequeue(self, *, tenant: str) -> PendingHitlEvent | None:
        """Pop the oldest pending event for ``tenant``, or ``None``."""
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
        """
        ...

    def submit(self, *, submission: HitlActionSubmission) -> None:
        """Record one human action returning through the authority path."""
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
    verifies the submission's signed binding and enforces principal match
    before recording. The policy is re-resolved per submission, so
    registering a flipped value changes behavior with zero code change.
    All four D-16 arguments are optional together: an unconfigured
    transport behaves exactly as before this composition existed.

    **Thread safety (WR-02; Phase-9 CONTEXT D-06).** A single plain
    :class:`threading.Lock` guards every queue mutation and snapshot read
    — the Protocol's concurrency contract, discharged here. The lock
    scope is deliberately minimal: D-16 verification
    (:meth:`_signed_binding_required` — a Control Plane resolve — and
    :meth:`_enforce_signed_binding` — JWS verification) runs *outside*
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
            through when the policy requires them.
        trusted_keys: The public keys this deployment accepts approver
            signatures under — trust stays the composition root's
            statement, outside the verification seam.
    """

    def __init__(
        self,
        *,
        control_plane: ControlPlaneProtocol | None = None,
        hitl_policy_key: str | None = None,
        identity_provider: IdentityProvider | None = None,
        trusted_keys: Mapping[str, JsonWebKey] | None = None,
    ) -> None:
        self._lock = threading.Lock()
        self._pending: dict[str, deque[PendingHitlEvent]] = {}
        self._submissions: dict[str, list[HitlActionSubmission]] = {}
        self._control_plane = control_plane
        self._hitl_policy_key = hitl_policy_key
        self._identity_provider = identity_provider
        self._trusted_keys = trusted_keys

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

    def _enforce_signed_binding(
        self, submission: HitlActionSubmission
    ) -> None:
        """Refuse the submission unless its signed binding holds (D-16).

        Raises:
            SignedBindingRequiredRefused: the policy requires a binding
                and the submission carries none.
            SignedBindingInvalidRefused: the binding fails verification,
                or its verified principal is not the submission's.
            RuntimeError: the policy requires bindings but the transport
                was constructed without verification machinery — broken
                deployment wiring, not an expected refusal.
        """
        enforce_signed_binding(
            submission,
            identity_provider=self._identity_provider,
            trusted_keys=self._trusted_keys,
        )

    def enqueue(self, *, event: PendingHitlEvent) -> None:
        """Queue ``event`` for its tenant, preserving arrival order."""
        with self._lock:
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
        """
        with self._lock:
            queue = self._pending.get(tenant)
            if not queue:
                return None
            for index, event in enumerate(queue):
                if event.event_key == event_key:
                    del queue[index]
                    return event
            return None

    def submit(self, *, submission: HitlActionSubmission) -> None:
        """Record one human action returning through the authority path.

        When the Control Plane HITL policy in force requires a signed
        principal binding, the submission is verified before anything is
        recorded (D-16): a refused submission never lands on the queue.

        Raises:
            SignedBindingRequiredRefused: binding required and absent.
            SignedBindingInvalidRefused: binding invalid or its verified
                principal mismatches the submission's.
        """
        if self._signed_binding_required():
            self._enforce_signed_binding(submission)
        with self._lock:
            self._submissions.setdefault(submission.tenant, []).append(
                submission
            )

    def submissions(self, *, tenant: str) -> tuple[HitlActionSubmission, ...]:
        """The tenant's recorded actions, oldest first."""
        with self._lock:
            return tuple(self._submissions.get(tenant, ()))
