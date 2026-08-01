"""``ExceptionEscalation`` — the routing HITL primitive (CLAUDE.md §8.2).

SDK-defined (CLAUDE.md §8.2 — an extension beyond the whitepaper, and it
says so); HITL-01; D-IMPL-20/21. The second of the four HITL primitives: a
routing primitive that hands a workflow state to a designated human role
when a condition is met — typically a ``D_c`` threshold breach or an
agent's explicit escalation.

**The condition source is Control Plane content, never a code constant
(CINV-01).** The two trigger shapes:

* :class:`ExplicitEscalation` — an agent's own escalation, carrying its
  stated reason (deployment content, supplied by the caller).
* :class:`~ccf.halflife.debt.DebtAssessment` — the CAR routing state
  produced by :func:`ccf.halflife.debt.assess_debt` against a
  :class:`~ccf.controlplane.artifacts.DebtProfile` **artifact**. The
  thresholds live in that artifact; this module holds none. An assessment
  whose signal is ``OK`` is a returned typed refusal
  (:class:`EscalationRefused`, audited ``resolved=False``) — escalating a
  nominal state would be this module inventing a condition the Control
  Plane never declared.

**The designated role is the routing artifact's statement.** ``policy_ref``
pins the artifact (an exception-handler or escalation-policy declaration)
whose content names the role the deployment routes to. Nothing here
enumerates roles or routing values.

**Workflow integration is composition-root shape (CLAUDE.md §8.1).** The
engine's :class:`~ccf_runtime.workflow.engine.WorkflowExceptionRouted`
outcome names the artifact-declared handler ref; the deployment hands that
routed state to this primitive on the shared HITL transport. `/src` never
imports `/runtime`, so the seam is the routed outcome's *data* — tenant,
state key, node, handler ref — not an import.

**D-22 scope statement — which claims are guaranteed by what.**

* **Type-unrepresentable paths:** an *unbound* resolution — a human action
  without a complete :class:`~ccf.hitl.principal.HumanPrincipalBinding` —
  cannot be constructed through the typed transport contract
  (:class:`~ccf.hitl.transport.HitlActionSubmission` requires the binding
  by type), so that path does not exist in the type system.
* **Lint/CI-covered paths:** *capture completeness* — that every exercised
  escalation resolution actually lands its block on replay dimension 2 —
  is guarded by the owning tests (``tests/hitl/test_escalation.py``,
  ``tests/workflow/test_exception_paths.py``), demonstrated by assertion,
  not proven by construction. Never an absolute "no path" claim.

**TOCTOU guard (T-07-39, inherited doctrine).** The escalated event binds
the workflow state's content hash at hand-off time; the resolver's binding
echoes the hash of what they actually reviewed. A mismatch is a returned
typed :class:`EscalationResolutionRefused`, audited ``resolved=False``,
with the event left pending.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime

from pydantic import field_validator

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.audit import AuditLog
from ccf.controlplane.registry import ControlPlaneProtocol
from ccf.halflife.debt import DebtAssessment, DebtSignal
from ccf.hitl.approval_gate import HITL_ACTION_ARTIFACT_CLASS
from ccf.hitl.identity_binding import SignedPrincipalBinding
from ccf.hitl.principal import HumanPrincipalBinding
from ccf.hitl.transport import (
    HITLTransportProtocol,
    HitlActionSubmission,
    PendingHitlEvent,
    enforce_signed_binding,
    signed_binding_required,
)
from ccf.peering.identity import IdentityProvider, JsonWebKey

__ccf_mode__ = "algorithmic"

__all__ = [
    "ESCALATION_ACTIONS",
    "EscalationActionError",
    "EscalationActionRecord",
    "EscalationHandOff",
    "EscalationRefused",
    "EscalationResolution",
    "EscalationResolutionRefused",
    "ExceptionEscalation",
    "ExplicitEscalation",
    "UnknownEscalationEventError",
]

#: The two verdicts an escalation resolution accepts: the designated role
#: either accepts the hand-off (takes the state) or declines it. Mechanism
#: identifiers, never routing rules — *who* the designated role is comes
#: from the pinned ``policy_ref`` artifact (CINV-01).
ESCALATION_ACTIONS: frozenset[str] = frozenset({"approve", "reject"})


class UnknownEscalationEventError(LookupError):
    """The named event is not pending on the transport — broken wiring.

    Raised — never a returned refusal — on the I.1 line: a caller resolving
    an escalation the queue does not hold is mis-wired, not an expected
    governance outcome.
    """


class EscalationActionError(ValueError):
    """The action is not an escalation-resolution verdict.

    Raised for actions outside :data:`ESCALATION_ACTIONS`: an override or
    an annotation submitted to an escalation is a category error in the
    caller — those actions belong to other HITL primitives (CLAUDE.md §8.2).
    """


class ExplicitEscalation(CCFContract):
    """An agent's own escalation — the explicit trigger shape.

    SDK-defined (CLAUDE.md §8.2). ``reason`` is the agent's stated ground,
    deployment content carried verbatim into the replay record — the SDK
    fixes the shape, never the vocabulary.
    """

    reason: str

    @field_validator("reason")
    @classmethod
    def _reason_is_stated(cls, value: str) -> str:
        if not value.strip():
            raise ValueError(
                "an explicit escalation must state its reason; a blank"
                " reason is an unrecorded ground for a human hand-off"
                " (CLAUDE.md §8.2 audit-by-construction)"
            )
        return value


#: The trigger union: an explicit agent escalation, or the CAR routing
#: state assessed against a Control-Plane DebtProfile artifact.
EscalationTrigger = ExplicitEscalation | DebtAssessment


class EscalationHandOff(CCFContract):
    """A hand-off the primitive accepted — the state is on the queue.

    Pairs the pending event (what the human will see) with the trigger
    (why the state was handed off), so the eventual resolution record can
    carry both.
    """

    event: PendingHitlEvent
    trigger: EscalationTrigger


class EscalationRefused(CCFContract):
    """A hand-off the primitive refuses — typed value, audited
    ``resolved=False``.

    The nominal-assessment case foremost: a ``D_c`` assessment whose
    signal is ``OK`` breaches no Control-Plane-declared band, so there is
    no condition to escalate on. An expected outcome on the I.1 line,
    never an exception.
    """

    tenant: str
    event_key: str
    reason: str


class EscalationActionRecord(CCFContract):
    """One completed escalation resolution, in full — the dimension-2 payload.

    SDK-defined (CLAUDE.md §8.2). Pairs what was pending (the event, with
    the hand-off-time state hash), why it was pending (the trigger), what
    the human did (the submission, with the required principal binding),
    and the verdict. Canonically serializable, so the primitive can
    pre-serialize it once and replay records it verbatim (the 07-05
    keyword discipline).
    """

    event: PendingHitlEvent
    trigger: EscalationTrigger
    submission: HitlActionSubmission
    accepted: bool


class EscalationResolution(CCFContract):
    """A completed escalation decision — outcome plus the pre-serialized block.

    ``hitl_actions_block`` is the canonical serialization of ``record``,
    serialized once by the primitive and passed verbatim to
    :func:`ccf.replay.record.build_replay_record`'s ``hitl_actions``
    keyword (dimension 2). Derived here, never reconstructed by the record
    builder.
    """

    record: EscalationActionRecord
    hitl_actions_block: str


class EscalationResolutionRefused(CCFContract):
    """A resolution the primitive refuses — typed value, audited
    ``resolved=False``.

    The TOCTOU case foremost: the resolver's binding names a state hash
    other than the one bound at hand-off time. The pending event survives,
    so the human can re-review the current state.
    """

    tenant: str
    event_key: str
    reason: str


class ExceptionEscalation:
    """The routing HITL primitive (CLAUDE.md §8.2; HITL-01).

    Everything is injected — transport, audit log, clock — in the
    constructor-injection discipline of every Control Plane service: the
    primitive holds no role, no threshold, and no wall clock of its own.
    Role and threshold parameters come from artifact content only — the
    pinned ``policy_ref`` routing artifact and the
    :class:`~ccf.controlplane.artifacts.DebtProfile` behind any
    :class:`~ccf.halflife.debt.DebtAssessment` trigger (CINV-01).

    Args:
        transport: The typed HITL queue escalations surface on and actions
            return through (D-IMPL-20 — the only authority path).
        audit: The append-only log every hand-off and resolution lands in,
            refusals included (``resolved=False``).
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
        trusted_keys: The public keys this deployment accepts approver
            signatures under.
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
        trusted_keys: Mapping[str, JsonWebKey] | None = None,
    ) -> None:
        self._transport = transport
        self._audit = audit
        self._clock = clock
        self._control_plane = control_plane
        self._hitl_policy_key = hitl_policy_key
        self._identity_provider = identity_provider
        self._trusted_keys = trusted_keys
        self._triggers: dict[tuple[str, str], EscalationTrigger] = {}

    def escalate(
        self,
        *,
        tenant: str,
        event_key: str,
        workflow_state_ref: str,
        product_content_hash: str,
        policy_ref: str | None,
        trigger: EscalationTrigger,
    ) -> EscalationHandOff | EscalationRefused:
        """Hand a workflow state to the designated role, if a condition holds.

        Args:
            tenant: The owning tenant (D-23 — queues never interleave).
            workflow_state_ref: The suspended/routed workflow state key the
                human resumes against.
            product_content_hash: The content hash of the state the human
                will review, bound at hand-off time (TOCTOU guard).
            policy_ref: The pinned routing artifact whose declaration names
                the designated role — the artifact's statement, never this
                module's (CINV-01).
            trigger: :class:`ExplicitEscalation`, or a
                :class:`~ccf.halflife.debt.DebtAssessment` whose signal
                must breach a DebtProfile-declared band.

        Returns:
            :class:`EscalationHandOff` on acceptance, or
            :class:`EscalationRefused` (audited ``resolved=False``) for a
            nominal assessment.
        """
        if (
            isinstance(trigger, DebtAssessment)
            and trigger.signal is DebtSignal.OK
        ):
            self._record(event_key, version=product_content_hash, resolved=False)
            return EscalationRefused(
                tenant=tenant,
                event_key=event_key,
                reason=(
                    f"the assessment's D_c ({trigger.debt}) breaches no band"
                    " the decision class's DebtProfile artifact declares"
                    " (signal 'ok'); escalating a nominal state would invent"
                    " a condition the Control Plane never stated (CINV-01;"
                    " whitepaper §7.7 CAR)"
                ),
            )
        event = PendingHitlEvent(
            event_key=event_key,
            event_class="exception-escalation",
            tenant=tenant,
            workflow_state_ref=workflow_state_ref,
            product_content_hash=product_content_hash,
            policy_ref=policy_ref,
        )
        self._transport.enqueue(event=event)
        self._triggers[(tenant, event_key)] = trigger
        self._record(event_key, version=product_content_hash, resolved=True)
        return EscalationHandOff(event=event, trigger=trigger)

    def resolve(
        self,
        *,
        tenant: str,
        event_key: str,
        action: str,
        principal: HumanPrincipalBinding,
        annotation: str | None = None,
        signed_binding: SignedPrincipalBinding | None = None,
    ) -> EscalationResolution | EscalationResolutionRefused:
        """Resolve one pending escalation under a bound human decision.

        The principal binding is required by type — an unattributed
        resolution is unrepresentable through this signature (D-IMPL-21;
        the D-22 type-unrepresentable leg). The TOCTOU guard runs before
        anything is consumed or submitted.

        **Signed-binding verification (D-IMPL-69; SDK-defined, CLAUDE.md
        §8.2).** When a Control Plane is bound and the HitlPolicy in force
        declares ``signed_binding_required``, this surface verifies
        ``signed_binding`` before any queue consumption — a refused
        resolution raises and leaves the event pending. Verification is
        read-only and holds no lock; the transport re-verifies
        independently at submission (idempotent double verification,
        D-13).

        Returns:
            :class:`EscalationResolution` for both verdicts — a decline is
            a returned typed value carrying ``accepted=False``, audited
            ``resolved=False``, never an exception — or
            :class:`EscalationResolutionRefused` on a hash mismatch.

        Raises:
            UnknownEscalationEventError: ``event_key`` names no pending
                escalation for ``tenant`` — broken wiring, not a
                governance outcome.
            EscalationActionError: ``action`` is not an escalation verdict.
        """
        if action not in ESCALATION_ACTIONS:
            raise EscalationActionError(
                f"action {action!r} is not an escalation-resolution verdict;"
                f" this primitive accepts {sorted(ESCALATION_ACTIONS)} —"
                " override and annotate belong to other HITL primitives"
                " (CLAUDE.md §8.2)"
            )
        event = next(
            (
                pending
                for pending in self._transport.pending(tenant=tenant)
                if pending.event_key == event_key
                and pending.event_class == "exception-escalation"
            ),
            None,
        )
        if event is None:
            raise UnknownEscalationEventError(
                f"no pending escalation {event_key!r} for tenant {tenant!r};"
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
            return EscalationResolutionRefused(
                tenant=tenant,
                event_key=event_key,
                reason=(
                    "the binding's product_content_hash"
                    f" {principal.product_content_hash!r} does not equal the"
                    " hash bound at hand-off time"
                    f" {event.product_content_hash!r}: the state changed"
                    " between hand-off and the human action. The event stays"
                    " pending — re-review the current state and act on its"
                    " hash (T-07-39 doctrine)"
                ),
            )
        submission = HitlActionSubmission(
            event_key=event_key,
            tenant=tenant,
            action=action,
            principal=principal,
            annotation=annotation,
            signed_binding=signed_binding,
        )
        if signed_binding_required(
            control_plane=self._control_plane,
            hitl_policy_key=self._hitl_policy_key,
        ):
            # Verify BEFORE any queue consumption: a refusal raises here
            # and the pending event survives (D-IMPL-69; Pitfall 4).
            enforce_signed_binding(
                submission,
                identity_provider=self._identity_provider,
                trusted_keys=self._trusted_keys,
            )
        self._transport.submit(submission=submission)
        self._consume(tenant, event_key)
        trigger = self._triggers.pop((tenant, event_key))
        accepted = action == "approve"
        self._record(
            event_key,
            version=event.product_content_hash,
            resolved=accepted,
            actor=principal.approver.subject_id,
        )
        record = EscalationActionRecord(
            event=event,
            trigger=trigger,
            submission=submission,
            accepted=accepted,
        )
        return EscalationResolution(
            record=record,
            hitl_actions_block=canonical_bytes(record).decode("utf-8"),
        )

    # -- helpers ---------------------------------------------------------------

    def _consume(self, tenant: str, event_key: str) -> None:
        """Remove one resolved event, preserving the others' relative order."""
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
        self,
        event_key: str,
        *,
        version: str,
        resolved: bool,
        actor: str | None = None,
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
