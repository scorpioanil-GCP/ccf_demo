"""``ApprovalGate`` — the suspending HITL primitive, and its sync adapter.

SDK-defined (CLAUDE.md §8.2 — an extension beyond the whitepaper, and it
says so); HITL-01; D-IMPL-20/21. The first of the four HITL primitives: a
workflow step that suspends until a human approves or rejects, with the
approval landing in the Decision Replay record carrying the approver's
identity, the time of approval, and the identity of the Context Product
the approver saw.

**The dual face is composed, never conflated.** The tier-2 grant seam
(:class:`~ccf.skills.grants.ApprovalSink`) is synchronous and
grant-scoped; the workflow gate is asynchronous — transport suspend/resume
plus :class:`~ccf.hitl.principal.HumanPrincipalBinding`. One object
honestly doing both would have to lie in ``decide()`` when no human has
acted yet. So:

* :class:`ApprovalGate` owns the async workflow face — pending decisions
  surface on the injected :class:`~ccf.hitl.transport.HITLTransportProtocol`
  queue; a submitted decision must carry a binding; the gate yields the
  pre-serialized HITL-action block (replay dimension 2, the 07-05 verbatim
  keyword) alongside the typed outcome. This is the CINV-04
  hitl-action-capture owner.
* :class:`ApprovalSinkAdapter` is a thin adapter conforming structurally
  to ``ApprovalSink`` by wrapping an **already-completed** bound decision
  the gate produced. ``decide`` never blocks on a pending human and never
  fabricates a verdict: with no completed decision bound it raises
  :class:`UnboundDecisionError`. The grant state machine still owns every
  transition and every audit record (grants.py's seam doctrine) — the
  adapter changes nothing about the machine; the composition is
  property-preserving relative to the "joins with zero state-machine
  change" commitment (D-09).

**Approval policy is the artifact's statement (CINV-01).** The gate holds
no approval rule: which policy governs a gate comes from the
WorkflowDefinition's ``gate_policies`` binding, carried on the pending
event as a pinned ``policy_ref`` the deployment's reviewers interpret.
Nothing here enumerates approver roles, quorums, or thresholds.

**D-22 scope statement — which claims are guaranteed by what.** The
"no unrecorded human action" commitment is discharged in two named ways:

* **Type-unrepresentable paths:** an *unbound* submission — a human action
  without a complete :class:`~ccf.hitl.principal.HumanPrincipalBinding` —
  cannot be constructed through the typed transport contract
  (:class:`~ccf.hitl.transport.HitlActionSubmission` requires the binding
  by type), so that path does not exist in the type system.
* **Lint/CI-covered paths:** *capture completeness* — that every exercised
  gate resolution actually lands its block on replay dimension 2 — is
  guarded by the CINV-04 ``hitl-action-capture`` owning test
  (``tests/invariants/test_replay_by_construction.py``), demonstrated to
  fail under a severed capture, not proven by construction.

**TOCTOU guard (T-07-39).** The pending event binds the product's content
hash at suspend time; the approver's binding echoes the hash of what they
actually reviewed. A mismatch — the product mutated between suspend and
the human action — is a returned typed :class:`GateResolutionRefused`,
audited ``resolved=False``, with the event left pending so the human can
re-review the current version. A refusal that consumed the event would
turn a detected tamper into a lost approval opportunity.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.audit import AuditLog
from ccf.hitl.principal import HumanPrincipalBinding
from ccf.hitl.transport import (
    HITLTransportProtocol,
    HitlActionSubmission,
    PendingHitlEvent,
)
from ccf.skills.grants import ApprovalOutcome, SkillGrant

__ccf_mode__ = "algorithmic"

__all__ = [
    "GATE_ACTIONS",
    "HITL_ACTION_ARTIFACT_CLASS",
    "ApprovalGate",
    "ApprovalSinkAdapter",
    "GateActionError",
    "GateResolution",
    "GateResolutionRefused",
    "HitlActionRecord",
    "UnboundDecisionError",
    "UnknownGateEventError",
]

#: The artifact class the gate's audit records name. A mechanism identifier:
#: it names the gate's own action records, exactly as WORKFLOW_STATE names
#: the engine's.
HITL_ACTION_ARTIFACT_CLASS = "ccf.hitl-action"

#: The two verdicts an approval gate accepts (CLAUDE.md §8.2: "suspends
#: until a human approves or rejects"). A subset of the transport's
#: D-IMPL-20 action vocabulary — override and annotate belong to the
#: OverrideBoundary and ReviewQueue primitives, not to this gate. Mechanism
#: identifiers, never approval rules: *who* may act and under what policy is
#: the gate's pinned ``policy_ref``'s statement (CINV-01).
GATE_ACTIONS: frozenset[str] = frozenset({"approve", "reject"})


class UnknownGateEventError(LookupError):
    """The named event is not pending on the transport — broken wiring.

    Raised — never a returned refusal — on the I.1 line: a caller resolving
    an event the queue does not hold is mis-wired (a stale key, a wrong
    tenant), not an expected governance outcome.
    """


class GateActionError(ValueError):
    """The action is not an approval-gate verdict.

    Raised for actions outside :data:`GATE_ACTIONS`: an override or an
    annotation submitted to an *approval* gate is a category error in the
    caller — those actions belong to other HITL primitives (CLAUDE.md §8.2).
    """


class UnboundDecisionError(RuntimeError):
    """``decide`` was called with no completed decision bound.

    The sync face is honest (07-07 review resolution): the adapter wraps an
    already-completed decision produced through the gate face. With none
    bound there is no verdict to return, and blocking on a pending human or
    fabricating an outcome would both be lies — so this raises instead.
    """


class HitlActionRecord(CCFContract):
    """One completed human action, in full — the dimension-2 payload.

    SDK-defined (CLAUDE.md §8.2). Pairs what was pending (the event, with
    the suspend-time product hash) with what the human did (the submission,
    with the required principal binding) and the verdict. Canonically
    serializable, so the gate can pre-serialize it once and replay records
    it verbatim (the 07-05 keyword discipline).
    """

    event: PendingHitlEvent
    submission: HitlActionSubmission
    approved: bool


class GateResolution(CCFContract):
    """A completed gate decision — outcome plus the pre-serialized block.

    ``hitl_actions_block`` is the canonical serialization of ``record``,
    serialized once by the gate and passed verbatim to
    :func:`ccf.replay.record.build_replay_record`'s ``hitl_actions``
    keyword (dimension 2). Derived by the gate, never reconstructed by the
    record builder.
    """

    record: HitlActionRecord
    outcome: ApprovalOutcome
    hitl_actions_block: str


class GateResolutionRefused(CCFContract):
    """A resolution the gate refuses — typed value, audited ``resolved=False``.

    The TOCTOU case (T-07-39) foremost: the approver's binding names a
    product hash other than the one bound at suspend time. An expected
    outcome on the I.1 line, never an exception — and the pending event
    survives, so the human can re-review the current product version.
    """

    tenant: str
    event_key: str
    reason: str


class ApprovalGate:
    """The suspending workflow-face HITL primitive (CLAUDE.md §8.2; HITL-01).

    Everything is injected — transport, audit log, clock — in the
    constructor-injection discipline of every Control Plane service: the
    gate holds no approval rule, no approver, and no wall clock of its own.
    Approval-policy parameters come from the WorkflowDefinition's
    ``gate_policies`` binding (artifact content, carried on the pending
    event's ``policy_ref``) — no approval rule exists in this module
    (CINV-01).

    Args:
        transport: The typed HITL queue pending decisions surface on and
            actions return through (D-IMPL-20 — the only authority path).
        audit: The append-only log every resolution lands in, refusals
            included (``resolved=False``) — the audit plane records what it
            turned away.
        clock: Time source for audit timestamps. Injected, never read.
    """

    def __init__(
        self,
        *,
        transport: HITLTransportProtocol,
        audit: AuditLog,
        clock: Callable[[], datetime],
    ) -> None:
        self._transport = transport
        self._audit = audit
        self._clock = clock

    def resolve(
        self,
        *,
        tenant: str,
        event_key: str,
        action: str,
        principal: HumanPrincipalBinding,
        annotation: str | None = None,
    ) -> GateResolution | GateResolutionRefused:
        """Resolve one pending gate event under a bound human decision.

        The principal binding is required by type — an unattributed
        resolution is unrepresentable through this signature (D-IMPL-21;
        the D-22 type-unrepresentable leg). The TOCTOU guard runs before
        anything is consumed or submitted: the binding's
        ``product_content_hash`` must equal the hash the pending event
        bound at suspend time.

        Returns:
            :class:`GateResolution` for both verdicts — a rejection is a
            returned typed value carrying ``approved=False``, audited
            ``resolved=False``, never an exception — or
            :class:`GateResolutionRefused` on a TOCTOU hash mismatch.

        Raises:
            UnknownGateEventError: ``event_key`` names no pending event for
                ``tenant`` — broken wiring, not a governance outcome.
            GateActionError: ``action`` is not an approval-gate verdict.
        """
        if action not in GATE_ACTIONS:
            raise GateActionError(
                f"action {action!r} is not an approval-gate verdict; this"
                f" gate accepts {sorted(GATE_ACTIONS)} — override and"
                " annotate belong to other HITL primitives (CLAUDE.md §8.2)"
            )
        event = next(
            (
                pending
                for pending in self._transport.pending(tenant=tenant)
                if pending.event_key == event_key
            ),
            None,
        )
        if event is None:
            raise UnknownGateEventError(
                f"no pending HITL event {event_key!r} for tenant {tenant!r};"
                " resolving an event the queue does not hold is broken"
                " wiring, not a governance outcome (I.1 line)"
            )
        if principal.product_content_hash != event.product_content_hash:
            self._record(
                event_key,
                version=event.product_content_hash,
                resolved=False,
                actor=principal.approver.subject_id,
            )
            return GateResolutionRefused(
                tenant=tenant,
                event_key=event_key,
                reason=(
                    "the binding's product_content_hash"
                    f" {principal.product_content_hash!r} does not equal the"
                    f" hash bound at suspend time"
                    f" {event.product_content_hash!r}: the product changed"
                    " between suspend and the human action, so the approval"
                    " would attest to something the approver never saw"
                    " (T-07-39). The event stays pending — re-review the"
                    " current version and act on its hash"
                ),
            )
        submission = HitlActionSubmission(
            event_key=event_key,
            tenant=tenant,
            action=action,
            principal=principal,
            annotation=annotation,
        )
        self._transport.submit(submission=submission)
        self._consume(tenant, event_key)
        approved = action == "approve"
        self._record(
            event_key,
            version=event.product_content_hash,
            resolved=approved,
            actor=principal.approver.subject_id,
        )
        record = HitlActionRecord(
            event=event, submission=submission, approved=approved
        )
        return GateResolution(
            record=record,
            outcome=ApprovalOutcome(
                approved=approved,
                approver_id=principal.approver.subject_id,
            ),
            hitl_actions_block=canonical_bytes(record).decode("utf-8"),
        )

    # -- helpers ---------------------------------------------------------------

    def _consume(self, tenant: str, event_key: str) -> None:
        """Remove one resolved event, preserving the others' relative order.

        The transport Protocol deliberately exposes only queue semantics
        (D-IMPL-20), so removal is a drain-and-requeue over the tenant's
        events — order-preserving for everything not consumed.
        """
        retained: list[PendingHitlEvent] = []
        while True:
            pending = self._transport.dequeue(tenant=tenant)
            if pending is None:
                break
            if pending.event_key != event_key:
                retained.append(pending)
        for pending in retained:
            self._transport.enqueue(event=pending)

    def _record(
        self, event_key: str, *, version: str, resolved: bool, actor: str
    ) -> None:
        self._audit.append(
            action="hitl_action",
            key=event_key,
            version=version,
            resolved=resolved,
            occurred_at=self._clock(),
            actor=actor,
            artifact_class=HITL_ACTION_ARTIFACT_CLASS,
        )


class ApprovalSinkAdapter:
    """The sync grant face — a completed bound decision behind ``decide``.

    Conforms structurally to :class:`~ccf.skills.grants.ApprovalSink`
    (D-09: the grant state machine still owns every transition and every
    audit record; this adapter never touches the ledger's log). It wraps a
    decision **already completed** through the gate face —
    transport-suspended, principal-bound, audited — and hands the grant
    machinery the typed verdict.

    The D-22 scope of its honesty claim: "decide never blocks and never
    fabricates" holds by construction *of this type* — there is no pending
    state to block on, because the only constructor input is a completed
    :class:`GateResolution` or nothing, and nothing raises. It is not a
    claim about callers that choose to wait for a human before
    constructing the adapter; that waiting happens on the gate face, where
    it belongs.

    Args:
        resolution: The completed bound decision, or ``None`` — in which
            case :meth:`decide` raises :class:`UnboundDecisionError`.
    """

    def __init__(self, *, resolution: GateResolution | None = None) -> None:
        self._resolution = resolution

    def decide(self, grant: SkillGrant) -> ApprovalOutcome:
        """Return the completed decision's verdict for ``grant``.

        Raises:
            UnboundDecisionError: no completed decision is bound — the sync
                face never blocks on a pending human and never fabricates a
                verdict.
        """
        if self._resolution is None:
            raise UnboundDecisionError(
                "no completed decision is bound to this adapter; the sync"
                " grant face wraps a decision already completed through the"
                " ApprovalGate's workflow face and never blocks on a pending"
                " human or fabricates a verdict (07-07; D-09)"
            )
        return self._resolution.outcome
