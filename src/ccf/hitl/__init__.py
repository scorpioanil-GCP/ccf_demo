"""The Human-in-the-Loop contract layer (CLAUDE.md §8.2 — SDK-defined).

Everything in this package is an **SDK extension beyond the whitepaper**:
the whitepaper assumes a control plane; the HITL primitives — ApprovalGate,
ExceptionEscalation, OverrideBoundary, ReviewQueue — and their
audit-by-construction integration into the five-dimension Decision Replay
record are committed by CLAUDE.md §8.2, and every public docstring here
says so.

This package holds the contract layer the primitives (07-07/07-08)
implement against: the :class:`~ccf.hitl.principal.HumanPrincipalBinding`
that every human action must carry (D-IMPL-21), and the
:class:`~ccf.hitl.transport.HITLTransportProtocol` typed queue with its
in-memory reference implementation (D-IMPL-20). The load-bearing commitment
is CLAUDE.md §8.2's, quoted: "no path through the HITL surface produces an
unrecorded human action". At the strength this package enforces it (D-22
scoping): an *unattributed* action is type-unrepresentable — the submission
and resolution contracts require a :class:`HumanPrincipalBinding` by type —
and capture completeness is CI-covered by the CINV-04 owning tests
(``tests/invariants/test_replay_by_construction.py``), each proven red
under a severed capture, not asserted absolutely here.
"""

from __future__ import annotations

from ccf.hitl.approval_gate import (
    GATE_ACTIONS,
    HITL_ACTION_ARTIFACT_CLASS,
    ApprovalGate,
    ApprovalSinkAdapter,
    GateActionError,
    GateResolution,
    GateResolutionRefused,
    HitlActionRecord,
    UnboundDecisionError,
    UnknownGateEventError,
)
from ccf.hitl.escalation import (
    ESCALATION_ACTIONS,
    EscalationActionError,
    EscalationActionRecord,
    EscalationHandOff,
    EscalationRefused,
    EscalationResolution,
    EscalationResolutionRefused,
    ExceptionEscalation,
    ExplicitEscalation,
    UnknownEscalationEventError,
)
from ccf.hitl.override import (
    OverrideActionRecord,
    OverrideBoundary,
    OverrideResolution,
    OverrideResolutionRefused,
    UnknownOverrideEventError,
)
from ccf.hitl.principal import (
    ApproverIdentity,
    AuthenticationContext,
    HumanPrincipalBinding,
)
from ccf.hitl.review_queue import (
    ReviewActionRecord,
    ReviewQueue,
    ReviewQueueItem,
    ReviewResolution,
    ReviewResolutionRefused,
    UnknownReviewEventError,
)
from ccf.hitl.transport import (
    HITL_ACTIONS,
    HITL_EVENT_CLASSES,
    HITLTransportProtocol,
    HitlActionSubmission,
    InMemoryHitlTransport,
    PendingHitlEvent,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "ESCALATION_ACTIONS",
    "GATE_ACTIONS",
    "HITL_ACTIONS",
    "HITL_ACTION_ARTIFACT_CLASS",
    "HITL_EVENT_CLASSES",
    "ApprovalGate",
    "ApprovalSinkAdapter",
    "ApproverIdentity",
    "EscalationActionError",
    "EscalationActionRecord",
    "EscalationHandOff",
    "EscalationRefused",
    "EscalationResolution",
    "EscalationResolutionRefused",
    "ExceptionEscalation",
    "ExplicitEscalation",
    "UnknownEscalationEventError",
    "OverrideActionRecord",
    "OverrideBoundary",
    "OverrideResolution",
    "OverrideResolutionRefused",
    "UnknownOverrideEventError",
    "ReviewActionRecord",
    "ReviewQueue",
    "ReviewQueueItem",
    "ReviewResolution",
    "ReviewResolutionRefused",
    "UnknownReviewEventError",
    "GateActionError",
    "GateResolution",
    "GateResolutionRefused",
    "HitlActionRecord",
    "UnboundDecisionError",
    "UnknownGateEventError",
    "AuthenticationContext",
    "HITLTransportProtocol",
    "HitlActionSubmission",
    "HumanPrincipalBinding",
    "InMemoryHitlTransport",
    "PendingHitlEvent",
]
