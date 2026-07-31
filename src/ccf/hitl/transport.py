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
webhook leg's v0 disposition is owned by plan 07-08, the single owning plan
for that surface; MCP server endpoints exposing these queues are the
Experience-Layer primary (D-IMPL-20) and live on that surface, not here.

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

from collections import deque
from typing import Literal, Protocol, runtime_checkable

from pydantic import field_validator

from ccf.artifacts.protocol import ArtifactStoreError, parse_artifact_uri
from ccf.contracts.base import CCFContract
from ccf.hitl.principal import HumanPrincipalBinding

__ccf_mode__ = "algorithmic"

__all__ = [
    "HITL_ACTIONS",
    "HITL_EVENT_CLASSES",
    "HITLTransportProtocol",
    "HitlActionReceipt",
    "HitlActionSubmission",
    "InMemoryHitlTransport",
    "PendingHitlEvent",
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
    notification hook here — webhooks are notify-only and live elsewhere
    (07-08) — and no replay handle: recording is the primitives' obligation.

    ``runtime_checkable`` supports composition-root wiring checks; it
    verifies method presence only, so static conformance still rests on
    mypy.
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
    """

    def __init__(self) -> None:
        self._pending: dict[str, deque[PendingHitlEvent]] = {}
        self._submissions: dict[str, list[HitlActionSubmission]] = {}

    def enqueue(self, *, event: PendingHitlEvent) -> None:
        """Queue ``event`` for its tenant, preserving arrival order."""
        self._pending.setdefault(event.tenant, deque()).append(event)

    def dequeue(self, *, tenant: str) -> PendingHitlEvent | None:
        """Pop the oldest pending event for ``tenant``, or ``None``."""
        queue = self._pending.get(tenant)
        if not queue:
            return None
        return queue.popleft()

    def pending(self, *, tenant: str) -> tuple[PendingHitlEvent, ...]:
        """The tenant's pending events, oldest first, without consuming."""
        return tuple(self._pending.get(tenant, ()))

    def submit(self, *, submission: HitlActionSubmission) -> None:
        """Record one human action returning through the authority path."""
        self._submissions.setdefault(submission.tenant, []).append(submission)

    def submissions(self, *, tenant: str) -> tuple[HitlActionSubmission, ...]:
        """The tenant's recorded actions, oldest first."""
        return tuple(self._submissions.get(tenant, ()))
