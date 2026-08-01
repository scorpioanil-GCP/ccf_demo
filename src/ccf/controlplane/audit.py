"""The Control Plane's audit plane (whitepaper §7.8.2; INV-CH7-71).

The whitepaper does not give the Control Plane an audit *feature*; it says the
Control Plane **is** the audit plane. Every configuration change is versioned,
timestamped, and retained against the decisions made under it. This module is
that commitment in mechanism: a typed event contract and an append-only log,
separated from the registry so that the log is a thing a reviewer can read,
hand to another surface, or persist — rather than a private list inside one
class.

Three properties are load-bearing:

**Append-only.** :class:`AuditLog` exposes ``append`` and ``events`` and
nothing else. There is no delete, no truncate, no compaction and no mutable
view. An audit log that can be edited answers a different question than the one
an examiner asks (threat T-04-16).

**Failed interactions are recorded.** ``resolved=False`` events exist because a
log of successes cannot answer "what did this deployment ask for and not
have?" — which is exactly the question a fail-closed posture makes material.

**Time is injected.** Events carry the timestamp the registry's clock supplied.
No module here reads a wall clock, so an audit log replays.

**Authorization decisions are standalone events in this one log** (HARD-04;
D-IMPL-68, an SDK-defined extension per CLAUDE.md §8.2; 10-CONTEXT
D-09/D-10/D-11). The D-11 reading this phase implements, explicitly: an
authz decision is its own ``authz_decision`` event in the same Control Plane
audit log — no new replay dimension, no separate log surface — rather than
fields attached to a ``hitl_action`` record, because a queue-read denial has
no HITL action to attach to. Correlation with the gated HITL action is by
tenant/action/timestamp within the single log. The decision tuple rides on
:class:`AuthzDecisionAuditEvent`, a derived event class rather than new
fields on :class:`AuditEvent` itself: the canonical serializer renders every
declared field (``None`` included), so base-class fields would change the
canonical bytes of *every* existing event — exactly the replay drift the A2
byte-pin (``tests/authz/test_authz_audit.py``) exists to refuse. Events that
carry no authz field serialize byte-identically to before this extension.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Literal

from ccf.contracts.base import CCFContract

__ccf_mode__ = "algorithmic"

__all__ = [
    "AuditAction",
    "AuditEvent",
    "AuditLog",
    "AuthzDecisionAuditEvent",
]

#: The Control Plane interactions worth a record. Registration and resolution
#: are both here because the audit plane's obligation is to reconstruct *what
#: configuration a decision ran under*, which needs the reads as much as the
#: writes. The ``grant_*`` members are the skill-grant state transitions
#: (D-IMPL-29; D-09): a grant is a Control Plane action like any other, and
#: every transition — refusals included — is a record (CLAUDE.md §6.2:
#: "a skill grant or revocation is itself an audited Control Plane action").
#: The ``peering_*`` members are the **Peering** admission verdicts (D-IMPL-16;
#: :mod:`ccf.peering.admission`): admitting a peer's Context Product is a Control
#: Plane decision like any other, and a refusal that left no record would let
#: a rejected federation attempt be denied afterwards (T-06-43). They name the
#: *seam*, not one of its transports (``D-IMPL-59``, Dave, 2026-07-27): one gate
#: runs uniformly over every Peering, so the verdict is a Peering verdict
#: whichever transport carried the bytes — A2A being the reference transport
#: rather than the category. Renaming the members is a rename of enum literals
#: only; ``AuditEvent``'s own fields are untouched.
#:
#: ``skill_invoked`` is the remaining member added for I.3: an ``mcp`` dispatch
#: leaves this process and contacts a remote server, and none of the existing
#: members can express that — ``resolve`` is a Control Plane read and the
#: ``grant_*`` family are grant-state transitions, so recording an invocation
#: as either would make the log say something untrue. It goes through this one
#: log, on the one existing ``append``; there is no parallel audit surface.
#:
#: ``state_written`` is the member added for the 07-02 D-20 closure: the
#: audited state-write surface (:class:`~ccf.controlplane.state.
#: AuditedStateWriter`) takes the caller's *domain* event, so a caller with
#: domain semantics (a grant transition, a workflow suspension) never uses
#: this member — its own transition action carries the write evidence, one
#: event per write (INV-CH7-71). ``state_written`` exists for callers with no
#: domain semantics of their own: a generic Control Plane state write is a
#: Control Plane action like any other, and forcing it under ``register`` or
#: a ``grant_*`` member would make the log say something untrue — the same
#: reasoning as ``skill_invoked``, one log, one ``append``, no parallel
#: surface.
#: The ``workflow_*`` members are the workflow engine's state-machine
#: transitions (07-06; CLAUDE.md §8.1; D-IMPL-18): every transition of a
#: running workflow — nominal (``workflow_transition``), suspension on a
#: hitl-gate (``workflow_suspended``), resumption (``workflow_resumed``,
#: which carries refusals as ``resolved=False`` in the same member — a
#: resume that was asked for and refused is a resume interaction, exactly as
#: a failed ``resolve`` is a resolve), exception routing (``workflow_
#: exception``, D-IMPL-61: the propagate-to-terminal transition and the
#: routed-to-handler transition are both first-class recorded events), and
#: terminal completion (``workflow_completed``). They exist for the same
#: reason as the ``grant_*`` family: a workflow transition is a Control
#: Plane state change like any other, and recording it under ``register`` or
#: ``state_written`` would make the log say something untrue. One log, one
#: ``append``, no parallel surface.
#: ``hitl_action`` is the member added for 07-07 (CLAUDE.md §8.2): a human
#: acting on a HITL gate is a Control Plane interaction like any other, and
#: none of the existing members can express it — the ``workflow_*`` family
#: records what the *engine* did, and a human verdict recorded as a workflow
#: transition would make the log say something untrue. Rejections and TOCTOU
#: refusals travel in the same member as ``resolved=False``, exactly as
#: ``workflow_resumed`` carries its refusals.
#: ``authz_decision`` is the member added for 10-01 (HARD-04; D-IMPL-68;
#: 10-CONTEXT D-09/D-10/D-11): a tenant-authorization verdict at an
#: Experience-Layer door is a Control Plane decision like any other — the
#: scope-mapping artifact in force *is* Control Plane configuration — and
#: none of the existing members can express it: ``hitl_action`` records the
#: human's verdict, and a queue-read denial has no HITL action at all.
#: Allows and denials travel in this one member as ``resolved=True/False``
#: (D-10: refusals are security-relevant events), with the exact artifact
#: version in ``version`` (D-04). One log, one ``append``, no parallel
#: surface (D-11; WR-07).
AuditAction = Literal[
    "register",
    "register_typed",
    "register_versioned",
    "resolve",
    "resolve_latest",
    "grant_requested",
    "grant_pending_approval",
    "grant_effective",
    "grant_refused",
    "grant_revoked",
    "peering_admitted",
    "peering_admission_refused",
    "skill_invoked",
    "state_written",
    "workflow_transition",
    "workflow_suspended",
    "workflow_resumed",
    "workflow_exception",
    "workflow_completed",
    "hitl_action",
    "authz_decision",
]


class AuditEvent(CCFContract):
    """One audit-plane record of a Control Plane interaction (INV-CH7-71).

    Attributes:
        sequence: Monotonic position in the log. Gaps are detectable; ordering
            does not depend on timestamp resolution.
        action: Which interaction occurred.
        key: The configuration key involved.
        version: The version involved, or the version requested when the
            resolution failed.
        resolved: Whether the interaction succeeded.
        occurred_at: Timestamp from the registry's injected clock.
        actor: Who performed the interaction, when the caller states it. The
            SDK does not synthesize an identity: an unattributed action
            recorded as if attributed is worse than one recorded as unknown
            (identity binding is D-IMPL-21).
        artifact_class: The artifact class this interaction concerned, for
            typed registrations. Present so the log answers "what *kind* of
            thing changed" without re-resolving the artifact.
    """

    sequence: int
    action: AuditAction
    key: str
    version: str
    resolved: bool
    occurred_at: datetime
    actor: str | None = None
    artifact_class: str | None = None


class AuthzDecisionAuditEvent(AuditEvent):
    """One ``authz_decision`` event carrying the full D-09 decision tuple.

    SDK-defined (CLAUDE.md §8.2; D-IMPL-68; 10-CONTEXT D-09/D-10/D-11).
    The tuple maps onto the base fields plus two of its own: principal in
    ``actor``, tenant in ``key``, decision in ``resolved``, artifact version
    in ``version``, timestamp in ``occurred_at``, the door-declared action
    identifier in ``authz_action_id``, and the tenant pattern that matched in
    ``authz_matched_pattern`` (``None`` on a deny-by-default). A derived
    class rather than base-class fields, deliberately: the canonical
    serializer renders every declared field, so fields on
    :class:`AuditEvent` itself would change the canonical bytes of every
    pre-existing event — the replay drift the A2 byte-pin refuses (Pitfall
    3). Events without authz semantics stay :class:`AuditEvent` and stay
    byte-identical.

    Attributes:
        authz_action_id: The door-declared action identifier the decision
            concerned (D-02) — e.g. the constants in
            :mod:`ccf_runtime.authz.refusals`. Optional-typed only so the
            base contract's construction surface stays uniform; the
            authorizer always supplies it.
        authz_matched_pattern: The tenant pattern that granted the allow,
            or ``None`` when nothing matched (D-09).
    """

    authz_action_id: str | None = None
    authz_matched_pattern: str | None = None


class AuditLog:
    """An append-only sequence of :class:`AuditEvent`.

    Assigns each event its own sequence number, so callers cannot mis-number
    the log and a reader can detect a gap. Deliberately not a contract: it is
    mutable-by-appending state, whereas contracts are values.

    **Thread safety (CR-01; the WR-02 transport precedent).** A single
    plain :class:`threading.Lock` guards sequence assignment, the append,
    and every snapshot read. HARD-04 put this log on every request path —
    :class:`~ccf_runtime.authz.protocol.ControlPlaneTenantAuthorizer`
    appends one ``authz_decision`` event per door request, and the HTTP
    HITL handlers run on FastAPI's threadpool — so unsynchronized appends
    would race by construction and could mint duplicate sequence numbers,
    defeating the "gaps are detectable" contract above.
    """

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []
        self._lock = threading.Lock()

    def __len__(self) -> int:
        with self._lock:
            return len(self._events)

    def append(
        self,
        *,
        action: AuditAction,
        key: str,
        version: str,
        resolved: bool,
        occurred_at: datetime,
        actor: str | None = None,
        artifact_class: str | None = None,
        authz_action_id: str | None = None,
        authz_matched_pattern: str | None = None,
    ) -> AuditEvent:
        """Append one event and return it, sequence number assigned.

        When either authz keyword is supplied the appended event is an
        :class:`AuthzDecisionAuditEvent`; otherwise it is a plain
        :class:`AuditEvent` whose canonical bytes are unchanged by the
        HARD-04 extension (the A2 stability commitment).

        Sequence assignment and the append happen under the log's lock,
        so concurrent appends from door threads can neither duplicate nor
        skip a sequence number (CR-01).
        """
        event: AuditEvent
        with self._lock:
            if authz_action_id is not None or authz_matched_pattern is not None:
                event = AuthzDecisionAuditEvent(
                    sequence=len(self._events),
                    action=action,
                    key=key,
                    version=version,
                    resolved=resolved,
                    occurred_at=occurred_at,
                    actor=actor,
                    artifact_class=artifact_class,
                    authz_action_id=authz_action_id,
                    authz_matched_pattern=authz_matched_pattern,
                )
            else:
                event = AuditEvent(
                    sequence=len(self._events),
                    action=action,
                    key=key,
                    version=version,
                    resolved=resolved,
                    occurred_at=occurred_at,
                    actor=actor,
                    artifact_class=artifact_class,
                )
            self._events.append(event)
        return event

    def events(self) -> tuple[AuditEvent, ...]:
        """Return every recorded event, oldest first.

        A tuple rather than the internal list: a caller holding the log must not
        be able to rewrite history through the reference it was handed. Taken
        under the log's lock, so the snapshot never observes a half-appended
        state (CR-01).
        """
        with self._lock:
            return tuple(self._events)
