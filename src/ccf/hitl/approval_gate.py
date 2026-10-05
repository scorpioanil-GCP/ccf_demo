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

from collections.abc import Callable, Mapping
from datetime import datetime

from ccf.authz.capability import Authorized, HitlSubmit, verify
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.audit import AuditLog
from ccf.controlplane.registry import ControlPlaneProtocol
from ccf.hitl.identity_binding import SignedHitlAction
from ccf.hitl.principal import HumanPrincipalBinding
from ccf.hitl.transport import (
    check_approver_eligibility,
    HITLTransportProtocol,
    HitlActionSubmission,
    PendingHitlEvent,
    enforce_attestation,
    resolve_hitl_policy,
)
from ccf.peering.identity import IdentityProvider, JsonWebKey
from ccf.skills.grants import ApprovalOutcome, SkillGrant

__ccf_mode__ = "algorithmic"

__all__ = [
    "GATE_ACTIONS",
    "GATE_APPROVE",
    "GATE_EVENT_CLASS",
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

#: The affirmative verdict — the one gate action that authorizes passage
#: past the gate it resolves. A mechanism identifier drawn from
#: :data:`GATE_ACTIONS`, named so consumers that must distinguish "a human
#: acted" from "a human said yes" (the workflow engine's gate-authority
#: check, SEC-001) reference the vocabulary rather than a bare literal.
GATE_APPROVE = "approve"

#: The :data:`~ccf.hitl.transport.HITL_EVENT_CLASSES` member this primitive
#: owns. A mechanism identifier, named here because this is the module that
#: owns the vocabulary: a consumer asking "did an approval gate answer
#: this?" — the workflow engine's gate-authority check (SEC-001) — must not
#: reach for a bare ``"approval-gate"`` literal outside it. Exactly the
#: reasoning that put :data:`GATE_APPROVE` here.
GATE_EVENT_CLASS = "approval-gate"


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
        control_plane: The registry the HITL policy resolves through
            (D-IMPL-69; SDK-defined, CLAUDE.md §8.2). Optional together
            with the other three verification kwargs: all-unbound is the
            pre-Phase-10 posture, byte-identical behavior.
        hitl_policy_key: The Control Plane key the deployment registered
            its :class:`~ccf.hitl.transport.HitlPolicy` under —
            deployment vocabulary, no default (CINV-01).
        identity_provider: The D-IMPL-15 provider signatures verify
            through when the policy requires them.
    """

    def __init__(
        self,
        *,
        transport: HITLTransportProtocol,
        audit: AuditLog,
        clock: Callable[[], datetime],
        control_plane: ControlPlaneProtocol | None = None,
        hitl_policy_key: str | None = None,
        identity_provider: IdentityProvider | None = None,
    ) -> None:
        self._transport = transport
        self._audit = audit
        self._clock = clock
        self._control_plane = control_plane
        self._hitl_policy_key = hitl_policy_key
        self._identity_provider = identity_provider

    def resolve(
        self,
        authorized: Authorized[HitlSubmit],
        *,
        event_key: str,
        action: str,
        principal: HumanPrincipalBinding,
        annotation: str | None = None,
        attestation: SignedHitlAction | None = None,
    ) -> GateResolution | GateResolutionRefused:
        """Resolve one pending gate event under a bound human decision.

        The principal binding is required by type — an unattributed
        resolution is unrepresentable through this signature (D-IMPL-21;
        the D-22 type-unrepresentable leg). The TOCTOU guard runs before
        anything is consumed or submitted: the binding's
        ``product_content_hash`` must equal the hash the pending event
        bound at suspend time.

        **The capability first (D-IMPL-353 §1.2).** ``authorized`` is the
        ``Authorized[HitlSubmit]`` the gate minted for exactly this event;
        :func:`~ccf.authz.capability.verify` runs before the handle's first
        real statement, so a fabricated capability, one of another kind, or
        one minted for another event dies before the queue is read, before
        anything is audited, and before the claim is taken. The tenant is
        ``authorized.tenant`` and nothing else — there is no tenant
        parameter (§1.3) — and the transport records the action under the
        capability's principal.

        **Signed-binding verification (D-IMPL-69; SDK-defined, CLAUDE.md
        §8.2).** When a Control Plane is bound and the HitlPolicy in force
        declares ``signed_binding_required``, the resolution surface
        verifies ``attestation`` before any queue consumption — a
        refused resolution leaves the event pending. Verification is
        read-only and holds no lock (D-IMPL-69 accepted consequence). The
        transport's own submission-time verification runs independently
        afterwards (idempotent double verification, D-13 — no trust
        marker crosses the layer seam).

        Returns:
            :class:`GateResolution` for both verdicts — a rejection is a
            returned typed value carrying ``approved=False``, audited
            ``resolved=False``, never an exception — or
            :class:`GateResolutionRefused` on a TOCTOU hash mismatch.

        **Approver eligibility (SEC-006; `D-IMPL-366`).** With a Control
        Plane bound, :func:`~ccf.hitl.transport.check_approver_eligibility`
        judges the capability's principal against the event's pinned
        ``ccf.approval-policy`` and its recorded requester, after the TOCTOU
        equality and before the atomic claim — so an ineligible resolution
        never takes ``remove`` and the event stays pending.

        Raises:
            ccf.authz.capability.CapabilityBypassError: ``authorized`` is
                not a genuine ``Authorized[HitlSubmit]`` for ``event_key``.
            UnknownGateEventError: ``event_key`` names no pending event for
                the capability's tenant — broken wiring, not a governance
                outcome.
            GateActionError: ``action`` is not an approval-gate verdict.
            ccf.hitl.transport.ApproverNotEligible: the principal may not
                approve this gate under its pinned policy (SEC-006).
            ccf.hitl.transport.SignedBindingRequiredRefused: the policy in
                force requires a signed attestation and none was presented.
            ccf.hitl.transport.SignedBindingInvalidRefused: the presented
                attestation's signature does not verify under the keys the
                policy declares for its subject.
            ccf.hitl.transport.SignedBindingMismatchRefused: the attestation
                verifies but a signed claim disagrees with the capability,
                the request, the door-minted binding or the per-subject key
                map — the verdict included (`D-IMPL-363` E6).
            ccf.hitl.transport.SignedBindingStaleRefused: the signer's
                ``issued_at`` is outside the policy's window against the
                recorded ``action_time`` (`D-IMPL-363` E3); a reused nonce
                is refused by the transport at submit, not here.
        """
        verify(authorized, kind=HitlSubmit, resource=event_key)
        tenant = authorized.tenant
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
        if self._control_plane is not None:
            # SEC-006 (D-IMPL-366 §4 (4)): approver eligibility at the primitive,
            # after the TOCTOU equality and BEFORE the atomic claim, with the
            # event in hand — a refusal raises here, `remove` is never called
            # and the event stays pending. The transport re-judges against the
            # claimed event at submit (idempotent double verification, D-13).
            check_approver_eligibility(
                policy_ref=event.policy_ref,
                requested_by=event.requested_by,
                subject_id=authorized.principal,
                control_plane=self._control_plane,
            )
        submission = HitlActionSubmission(
            event_key=event_key,
            action=action,
            principal=principal,
            annotation=annotation,
            attestation=attestation,
        )
        resolved_policy = resolve_hitl_policy(
            control_plane=self._control_plane,
            hitl_policy_key=self._hitl_policy_key,
        )
        if resolved_policy is not None and resolved_policy[1].signed_binding_required:
            # Verify BEFORE any queue consumption: a refusal raises here
            # and the pending event survives (D-IMPL-69; Pitfall 4). The
            # nonce is not consumed here — the transport does that once,
            # atomically, at submit (D-IMPL-363 E4).
            enforce_attestation(
                authorized,
                submission,
                identity_provider=self._identity_provider,
                policy=resolved_policy[1],
            )
        claimed = self._transport.remove(tenant=tenant, event_key=event_key)
        if claimed is None:
            # A concurrent resolve claimed the event between the snapshot
            # check above and this atomic claim (WR-02): exactly one
            # resolver wins; the loser raises without submitting, so one
            # human action never becomes two authority submissions.
            raise UnknownGateEventError(
                f"no pending HITL event {event_key!r} for tenant {tenant!r}:"
                " a concurrent resolution claimed it after this call's"
                " pending-snapshot check (WR-02 — exactly one resolve wins"
                " the claim; this one lost)"
            )
        try:
            # The transport returns the RECORDED copy — stamped with the
            # authorizing decision id (D-IMPL-353 §9) — and that copy, not
            # this primitive's input, is what the replay block carries.
            recorded = self._transport.submit(authorized, submission=submission)
        except BaseException:
            # The claim precedes the submit so a failed submit must give
            # the event back — a refused authority submission never
            # consumes the pending event (Pitfall 4 doctrine). Re-enqueued
            # at the tail: arrival order is re-established, not preserved.
            self._transport.enqueue(event=claimed)
            raise
        approved = action == "approve"
        self._record(
            event_key,
            version=event.product_content_hash,
            resolved=approved,
            actor=principal.approver.subject_id,
        )
        record = HitlActionRecord(
            event=event, submission=recorded, approved=approved
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
