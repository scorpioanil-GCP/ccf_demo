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

from pydantic import Field

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY

__ccf_mode__ = "algorithmic"

__all__ = [
    "AttributeAssertionRefusedAuditEvent",
    "AuditAction",
    "AuditEvent",
    "AuditLog",
    "AuthzDecisionAuditEvent",
    "AuthzFailingAxis",
    "WorkflowVerdictIntegrityAuditEvent",
    "WorkflowVerdictIntegrityFailure",
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
#: ``attribute_assertion_refused`` is the member added for SEC-023
#: (``D-IMPL-372``, ruling Q15 (a); CLAUDE.md §7.8 "the Control Plane is the
#: audit plane"): L2 refused an entity claim because its source is not
#: authorized for a governed attribute the claim asserts
#: (``src/ccf/assembly/worker.py::EntityResolutionRule``). It is RECORDED, never
#: raised — a raise would hand the least trusted source a lever over every
#: serve — so this member is the refusal's record of truth. None of the
#: existing members can express it: no Control Plane artifact was registered
#: or resolved, and a write refusal recorded as ``resolve`` would make the log
#: say something untrue. Always ``resolved=False``.
#: ``governed_attribute_omitted`` is the member added for SEC-023-C-01
#: (``D-IMPL-374`` ruling (3): audit AND admit): L2 ADMITTED an entity claim
#: from a source not authorized for a governed attribute the claim OMITS —
#: the claim supersedes the whole attribute dict, so the omission blanks the
#: label. A distinct member because the refusal event's schema carries no
#: reason field, and recording an admission as ``attribute_assertion_refused``
#: would make the log say something untrue. Carried by
#: :class:`AttributeAssertionRefusedAuditEvent`'s fields with
#: ``refused_value_present=False``. Always ``resolved=True``.
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
    "composition",
    "attribute_assertion_refused",
    "governed_attribute_omitted",
    # SEC-009 (`D-IMPL-374` (4), design §8): an erasure index entry whose
    # record is missing or disagrees — the address is withheld and this is
    # the audit answer.
    "erasure_index_unsupported",
]


#: Which axis of a four-axis ``(grant, tenant, action, resource)`` decision
#: refused, as recorded on a deny (D-IMPL-353 §3). Closed on purpose: the
#: fourth member, ``mapping``, is the honest record of a deny that no scope
#: mapping decided — nothing resolved at the pinned version, or a near-miss
#: artifact was found there — because writing ``tenant``, ``action`` or
#: ``resource`` for it would name a rule that never ran. Three states, not
#: two: *refused on axis X*, *refused because nothing could decide*, and (on
#: an allow) *no axis refused*.
AuthzFailingAxis = Literal["tenant", "action", "resource", "mapping"]


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

    **A deny says what it denied** (D-IMPL-353 §3). Three further fields,
    added on this derived class for the same byte-stability reason: the
    resource the action was to be performed on, the resource pattern that
    granted an allow, and — on a deny — the axis that refused. A capability
    (:class:`~ccf_runtime.authz.capability.Authorized`) carries the content
    address of the *allow* event as its ``decision_id``, so every action taken
    under it is traceable to this one record, and every refusal on the log
    says which rule refused it.

    Attributes:
        authz_action_id: The door-declared action identifier the decision
            concerned (D-02) — e.g. the constants in
            :mod:`ccf_runtime.authz.refusals`. Optional-typed only so the
            base contract's construction surface stays uniform; the
            authorizer always supplies it.
        authz_matched_pattern: The tenant pattern that granted the allow,
            or ``None`` when nothing matched (D-09).
        authz_resource: The resource the decision was about — the Control
            Plane key, the content address, the product class, or the door's
            own action id (``SEC-002``). ``None`` only on events appended by
            a decision surface that has no resource axis.
        authz_matched_resource_pattern: The resource pattern that granted
            the allow, or ``None`` when nothing matched. Separate from the
            tenant pattern so an examiner asking *which rule let this
            through* gets both halves.
        authz_failing_axis: On a deny, the deepest axis any scope entry the
            grant held reached before failing — ``"action"`` when no held
            entry names the action, ``"tenant"`` when one did but its tenant
            patterns matched nothing, ``"resource"`` when action and tenant
            matched and no resource pattern did — or ``"mapping"`` when no
            scope mapping resolved at the pinned version (or a near-miss
            artifact was found there), so that a deny nothing decided is
            never recorded as a rule that never ran. ``None`` on an allow.
    """

    authz_action_id: str | None = None
    authz_matched_pattern: str | None = None
    #: ``True`` — hash-transparent at the sentinel (``D-IMPL-243``: *"silence
    #: equals yesterday"*). An ``authz_decision`` event appended before these
    #: three fields existed carried none of them, and one appended now with
    #: any of them at ``None`` renders byte-identically to it; a set value is
    #: a real claim and is rendered. So the events already on a deployment's
    #: log and the events the same authorizer appends today canonicalize the
    #: same way, and no examiner's hash of an old event moves.
    authz_resource: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    authz_matched_resource_pattern: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    authz_failing_axis: AuthzFailingAxis | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )


#: Which verdict-integrity rule refused a workflow resumption past an approval
#: gate (D-IMPL-357 A4). Closed on purpose, and the two members are the two
#: questions a gate resumption asks about a recorded human verdict:
#: ``"route_disagreement"`` — the caller's decision does not name the target
#: the artifact declares for the verdict the authority path recorded — and
#: ``"conflicting_verdicts"`` — more than one distinct verdict is recorded
#: against this one suspension, so no single recorded verdict can be routed
#: on at all. ``None`` on every other refusal and on every allow: a refusal
#: that no verdict-integrity rule produced must never claim one of these.
WorkflowVerdictIntegrityFailure = Literal[
    "route_disagreement", "conflicting_verdicts"
]


class WorkflowVerdictIntegrityAuditEvent(AuditEvent):
    """A ``workflow_resumed`` refusal that a RECORDED HUMAN VERDICT caused.

    SDK-defined (CLAUDE.md §8.2; D-IMPL-357 A4; SEC-001). Every resume
    refusal was audited identically before this class existed — same
    ``workflow_resumed`` action, ``resolved=False``, ``actor=None``, and no
    reason on the event — so *"a caller tried to route a recorded rejection
    down the approving branch"* was byte-identical in the log to *"a caller
    mistyped the decision"*. For a bank that is the one refusal an
    investigator would search for, and the log could not answer it.

    Two fields, and between them the record says what the prose refusal
    deliberately does not tell the CALLER (SEC-001 remedy 3: a refusal never
    answers the caller's question for them). The audit plane is a different
    reader with a different entitlement — that separation is the point.

    A derived class rather than fields on :class:`AuditEvent`, for the same
    reason :class:`AuthzDecisionAuditEvent` is one: the canonical serializer
    renders every declared field, so a field on the base would change the
    canonical bytes of every pre-existing event. Both fields are additionally
    hash-transparent at their sentinel (CINV-06; D-IMPL-243, *"silence equals
    yesterday"*), so an event appended with either unset renders
    byte-identically to one appended before they existed.

    Attributes:
        workflow_verdict_integrity: Which rule refused. The member, not
            prose: an investigator queries a closed vocabulary.
        workflow_recorded_approver: The approver whose recorded verdict the
            engine's selection rule reached — the actor the resumption would
            have been attributed to had it proceeded. Carried because it is
            the fact in scope at the refusal site and the reason
            ``actor=None`` was wrong here: a verdict-integrity refusal is
            ALWAYS about a human action that really was recorded, so
            recording nothing about the human made the log say less than it
            knew. On ``"conflicting_verdicts"`` it names the approver at the
            head of the eligible verdicts and **not** the only party — by
            construction at least one other human recorded a contradicting
            verdict against the same suspension, which is what the member
            itself says.
    """

    workflow_verdict_integrity: WorkflowVerdictIntegrityFailure | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    workflow_recorded_approver: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )


class AttributeAssertionRefusedAuditEvent(AuditEvent):
    """An ``attribute_assertion_refused`` event: L2 refused a non-authoritative claim.

    SEC-023 (``D-IMPL-372``, ruling Q15 (a)); whitepaper §7.8.2 (the Control
    Plane is the audit plane) and §7.3 (L2 is the only writer). Appended by
    ``src/ccf/assembly/worker.py::AssemblyWorker.ingest`` once per governed
    attribute a refused entity claim asserted. The base fields carry: the
    refused entity's URI in ``key``, the policy-bundle version in force in
    ``version``, ``resolved=False``, the envelope's own ingestion instant in
    ``occurred_at`` (the worker reads no clock, D-IMPL-159), and
    ``ccf.resolution-spec`` — the artifact class whose declaration refused it —
    in ``artifact_class``. ``actor`` stays ``None``: a source system id is the
    adapter's self-declared logical identity, not an attested actor
    (D-IMPL-21), so it is recorded in its own field rather than promoted.

    **The refused VALUE is never recorded** — only that one was present
    (SEC-024 discipline): the audit plane must not become a copy of the data a
    classification was protecting, nor a channel through which a refused
    source's text reaches an examiner's tooling.

    **Also the carrier of ``governed_attribute_omitted``** (SEC-023-C-01,
    ``D-IMPL-374`` ruling (3)): the same fields describe an ADMITTED claim
    whose source, not authorized for the attribute, omitted it — with
    ``resolved=True`` and ``refused_value_present=False``. The ``action``
    member, not the field names, says which of the two happened.

    A derived class for the byte-stability reason
    :class:`AuthzDecisionAuditEvent` gives, and every field is hash-transparent
    at its ``None`` sentinel (CINV-06; D-IMPL-243).

    Attributes:
        refused_entity_class: The entity class of the refused claim.
        refused_attribute: The governed attribute the source is not
            authorized to assert.
        refused_source_system_id: ``SourceIdentity.system_id`` of the
            envelope, as the source declared it.
        refused_envelope_id: The envelope whose claim was refused.
        refused_value_present: Whether the envelope carried a value for the
            attribute. Recorded in place of the value itself.
    """

    refused_entity_class: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    refused_attribute: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    refused_source_system_id: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    refused_envelope_id: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    refused_value_present: bool | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )


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
        authz_resource: str | None = None,
        authz_matched_resource_pattern: str | None = None,
        authz_failing_axis: AuthzFailingAxis | None = None,
        workflow_verdict_integrity: WorkflowVerdictIntegrityFailure
        | None = None,
        workflow_recorded_approver: str | None = None,
        refused_entity_class: str | None = None,
        refused_attribute: str | None = None,
        refused_source_system_id: str | None = None,
        refused_envelope_id: str | None = None,
        refused_value_present: bool | None = None,
    ) -> AuditEvent:
        """Append one event and return it, sequence number assigned.

        When any authz keyword is supplied the appended event is an
        :class:`AuthzDecisionAuditEvent`; when
        ``workflow_verdict_integrity`` is supplied it is a
        :class:`WorkflowVerdictIntegrityAuditEvent`; otherwise it is a plain
        :class:`AuditEvent` whose canonical bytes are unchanged by the
        HARD-04 extension (the A2 stability commitment). When
        ``refused_attribute`` is supplied it is an
        :class:`AttributeAssertionRefusedAuditEvent` (SEC-023), dispatched on
        the attribute because the attribute is what names the governed
        declaration that refused. The three
        D-IMPL-353 §3 keywords are additive and default to ``None``, so
        every pre-existing call shape appends exactly what it appended.

        The verdict-integrity pair is dispatched on the MEMBER rather than on
        the approver (D-IMPL-357 A4): the member is what names the rule that
        refused, and an approver alone would silently promote any event that
        happens to name a human. The two class tests are mutually exclusive
        by construction — no call site supplies both families, and an authz
        decision is never a workflow transition.

        Sequence assignment and the append happen under the log's lock,
        so concurrent appends from door threads can neither duplicate nor
        skip a sequence number (CR-01).
        """
        event: AuditEvent
        with self._lock:
            if refused_attribute is not None:
                event = AttributeAssertionRefusedAuditEvent(
                    sequence=len(self._events),
                    action=action,
                    key=key,
                    version=version,
                    resolved=resolved,
                    occurred_at=occurred_at,
                    actor=actor,
                    artifact_class=artifact_class,
                    refused_entity_class=refused_entity_class,
                    refused_attribute=refused_attribute,
                    refused_source_system_id=refused_source_system_id,
                    refused_envelope_id=refused_envelope_id,
                    refused_value_present=refused_value_present,
                )
            elif workflow_verdict_integrity is not None:
                event = WorkflowVerdictIntegrityAuditEvent(
                    sequence=len(self._events),
                    action=action,
                    key=key,
                    version=version,
                    resolved=resolved,
                    occurred_at=occurred_at,
                    actor=actor,
                    artifact_class=artifact_class,
                    workflow_verdict_integrity=workflow_verdict_integrity,
                    workflow_recorded_approver=workflow_recorded_approver,
                )
            elif (
                authz_action_id is not None
                or authz_matched_pattern is not None
                or authz_resource is not None
                or authz_matched_resource_pattern is not None
                or authz_failing_axis is not None
            ):
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
                    authz_resource=authz_resource,
                    authz_matched_resource_pattern=authz_matched_resource_pattern,
                    authz_failing_axis=authz_failing_axis,
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
