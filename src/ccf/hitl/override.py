"""``OverrideBoundary`` — the typed substitution HITL primitive (CLAUDE.md §8.2).

SDK-defined (CLAUDE.md §8.2 — an extension beyond the whitepaper, and it
says so); HITL-01; D-IMPL-20/21. The third of the four HITL primitives: a
typed boundary at which a human can substitute a value the agent would
otherwise have produced. Overrides are audited; **the original agent
output and the override are both in the replay record** — T-07-16's
repudiation threat is mitigated by carrying both values, canonically
serialized, in the dimension-2 block, byte-assertable.

**The boundary is generic over the contract type being overridden.** The
deployment parameterizes :class:`OverrideBoundary` with its own
:class:`~ccf.contracts.base.CCFContract` output type; the SDK ships the
boundary mechanism only — no output schema, no substitution rule, no
policy value lives here (CINV-01). Original and override are never mutated
in place: both are preserved verbatim in the
:class:`OverrideActionRecord`.

**A declined override is an action, not an absence.** The human confirming
the agent value resolves through the same bound path (``approve``) and
lands on dimension 2 with ``overridden=False`` — a reviewer who looked and
kept the value is as auditable as one who substituted.

**D-22 scope statement — which claims are guaranteed by what.**

* **Type-unrepresentable paths:** an *unbound* override — a human action
  without a complete :class:`~ccf.hitl.principal.HumanPrincipalBinding` —
  cannot be constructed through the typed transport contract
  (:class:`~ccf.hitl.transport.HitlActionSubmission` requires the binding
  by type), so that path does not exist in the type system.
* **Lint/CI-covered paths:** *capture completeness* — that every exercised
  override resolution actually lands both values on replay dimension 2 —
  is guarded by the owning tests (``tests/hitl/test_override.py``),
  demonstrated by byte assertion, not proven by construction. Never an
  absolute "no path" claim.

**TOCTOU guard (T-07-17/T-07-39 doctrine).** ``propose`` binds the
original's content hash at proposal time; the overrider's binding echoes
the hash of what they actually reviewed. A mismatch is a returned typed
:class:`OverrideResolutionRefused`, audited ``resolved=False``, with the
event left pending.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Generic, TypeVar

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.audit import AuditLog
from ccf.controlplane.registry import ControlPlaneProtocol
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
    "OverrideActionRecord",
    "OverrideBoundary",
    "OverrideResolution",
    "OverrideResolutionRefused",
    "UnknownOverrideEventError",
]

ProductT = TypeVar("ProductT", bound=CCFContract)


class UnknownOverrideEventError(LookupError):
    """The named event is not pending on the transport — broken wiring.

    Raised — never a returned refusal — on the I.1 line: a caller resolving
    an override the queue does not hold is mis-wired, not an expected
    governance outcome.
    """


class OverrideActionRecord(CCFContract, Generic[ProductT]):
    """One completed override action, in full — the dimension-2 payload.

    SDK-defined (CLAUDE.md §8.2). Carries what was pending (the event, with
    the proposal-time original hash), what the human did (the submission,
    with the required principal binding), and **both values**: ``original``
    (the agent's output, verbatim) and ``final`` (the substituted value, or
    the original again on a confirm). Canonically serializable, so the
    boundary pre-serializes it once and replay records it verbatim
    (T-07-16 — losing the original would make an override unrepudiable).
    """

    event: PendingHitlEvent
    submission: HitlActionSubmission
    original: ProductT
    final: ProductT
    overridden: bool


class OverrideResolution(CCFContract, Generic[ProductT]):
    """A completed override decision — outcome plus the pre-serialized block.

    ``hitl_actions_block`` is the canonical serialization of ``record``,
    serialized once by the boundary and passed verbatim to
    :func:`ccf.replay.record.build_replay_record`'s ``hitl_actions``
    keyword (dimension 2). Derived here, never reconstructed by the record
    builder.
    """

    record: OverrideActionRecord[ProductT]
    hitl_actions_block: str


class OverrideResolutionRefused(CCFContract):
    """A resolution the boundary refuses — typed value, audited
    ``resolved=False``.

    The TOCTOU case foremost: the overrider's binding names a content hash
    other than the original's proposal-time hash. The pending event
    survives, so the human can re-review the current output.
    """

    tenant: str
    event_key: str
    reason: str


class OverrideBoundary(Generic[ProductT]):
    """The typed substitution HITL primitive (CLAUDE.md §8.2; HITL-01).

    Everything is injected — transport, audit log, clock — in the
    constructor-injection discipline of every Control Plane service: the
    boundary holds no output schema, no substitution rule, and no wall
    clock of its own. Which policy governs a boundary comes from the
    pinned ``policy_ref`` carried on the pending event (CINV-01).

    Args:
        transport: The typed HITL queue proposals surface on and actions
            return through (D-IMPL-20 — the only authority path).
        audit: The append-only log every resolution lands in, refusals
            included (``resolved=False``).
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
        self._originals: dict[tuple[str, str], ProductT] = {}

    def propose(
        self,
        *,
        tenant: str,
        event_key: str,
        workflow_state_ref: str,
        original: ProductT,
        policy_ref: str | None = None,
    ) -> PendingHitlEvent:
        """Surface the agent's output for a possible human substitution.

        The original's content hash is bound into the pending event at
        proposal time — the value the overrider's binding must echo — and
        the original itself is retained verbatim for the eventual record.
        Proposal is the agent side of the boundary, not a human action; the
        human action audits at :meth:`resolve`.
        """
        event = PendingHitlEvent(
            event_key=event_key,
            event_class="override-boundary",
            tenant=tenant,
            workflow_state_ref=workflow_state_ref,
            product_content_hash=content_hash(original),
            policy_ref=policy_ref,
        )
        self._transport.enqueue(event=event)
        self._originals[(tenant, event_key)] = original
        return event

    def resolve(
        self,
        *,
        tenant: str,
        event_key: str,
        principal: HumanPrincipalBinding,
        override: ProductT | None = None,
        annotation: str | None = None,
        signed_binding: SignedPrincipalBinding | None = None,
    ) -> OverrideResolution[ProductT] | OverrideResolutionRefused:
        """Resolve one pending boundary under a bound human decision.

        The principal binding is required by type — an unattributed
        override is unrepresentable through this signature (D-IMPL-21; the
        D-22 type-unrepresentable leg). The TOCTOU guard runs before
        anything is consumed or submitted.

        **Signed-binding verification (D-IMPL-69; SDK-defined, CLAUDE.md
        §8.2).** When a Control Plane is bound and the HitlPolicy in force
        declares ``signed_binding_required``, this surface verifies
        ``signed_binding`` before any queue consumption — a refused
        resolution raises and leaves the event pending. Verification is
        read-only and holds no lock; the transport re-verifies
        independently at submission (idempotent double verification,
        D-13).

        Args:
            override: The substituted value, or ``None`` — the human
                confirms the agent value. **Both paths are recorded
                actions**; a confirm is never an absence.

        Returns:
            :class:`OverrideResolution` carrying both original and final
            values and the pre-serialized dimension-2 block, or
            :class:`OverrideResolutionRefused` on a hash mismatch.

        Raises:
            UnknownOverrideEventError: ``event_key`` names no pending
                override for ``tenant`` — broken wiring, not a governance
                outcome.
        """
        event = next(
            (
                pending
                for pending in self._transport.pending(tenant=tenant)
                if pending.event_key == event_key
                and pending.event_class == "override-boundary"
            ),
            None,
        )
        if event is None:
            raise UnknownOverrideEventError(
                f"no pending override {event_key!r} for tenant {tenant!r};"
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
            return OverrideResolutionRefused(
                tenant=tenant,
                event_key=event_key,
                reason=(
                    "the binding's product_content_hash"
                    f" {principal.product_content_hash!r} does not equal the"
                    " original's proposal-time hash"
                    f" {event.product_content_hash!r}: the output changed"
                    " between proposal and the human action, so the override"
                    " would substitute against something the human never saw"
                    " (T-07-17; T-07-39 doctrine). The event stays pending —"
                    " re-review the current output and act on its hash"
                ),
            )
        overridden = override is not None
        submission = HitlActionSubmission(
            event_key=event_key,
            tenant=tenant,
            action="override" if overridden else "approve",
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
        original = self._originals.pop((tenant, event_key))
        final = override if override is not None else original
        self._record(
            event_key,
            version=event.product_content_hash,
            resolved=True,
            actor=principal.approver.subject_id,
        )
        record: OverrideActionRecord[ProductT] = OverrideActionRecord(
            event=event,
            submission=submission,
            original=original,
            final=final,
            overridden=overridden,
        )
        return OverrideResolution(
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
