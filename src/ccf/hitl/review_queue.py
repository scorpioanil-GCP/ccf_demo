"""``ReviewQueue`` — the asynchronous review HITL primitive (CLAUDE.md §8.2).

SDK-defined (CLAUDE.md §8.2 — an extension beyond the whitepaper, and it
says so); HITL-01; D-IMPL-20/21. The fourth of the four HITL primitives: a
primitive for asynchronous human review of ContentGeneration-style outputs
(credit memos, narratives) before release. It integrates with
passage-level lineage (whitepaper §7.10.3) so reviewers can see what each
claim is anchored to: a :class:`ReviewQueueItem` carries the real
:class:`~ccf.contracts.claims.LineageEntry` /
:class:`~ccf.contracts.claims.PassageAnchor` types, never a string
rendering of them, and an item with *no* lineage is unconstructible —
citation-aware review is the point of the queue.

**§8.2's boundary is honored: no inbox, no UI.** The queue exposes
Protocol surfaces only — pending items on the injected
:class:`~ccf.hitl.transport.HITLTransportProtocol`, typed views through
:meth:`ReviewQueue.items` — for the deployment's own human-task systems to
consume. Notification delivery (webhook or otherwise) is notify-only and
carries no authority; the release action always returns through the typed
queue (D-IMPL-20 — see the 07-08 SUMMARY for the webhook leg's v0
disposition).

**Tenancy (D-23, T-07-18).** Items and views are partitioned by tenant on
both the transport and the queue's own retention: two reviewers on two
tenants' queues see disjoint worlds, and resolving one tenant's item never
touches another's queue.

**D-22 scope statement — which claims are guaranteed by what.**

* **Type-unrepresentable paths:** an *unbound* release — a human action
  without a complete :class:`~ccf.hitl.principal.HumanPrincipalBinding` —
  cannot be constructed through the typed transport contract
  (:class:`~ccf.hitl.transport.HitlActionSubmission` requires the binding
  by type), so that path does not exist in the type system.
* **Lint/CI-covered paths:** *capture completeness* — that every exercised
  release or rejection actually lands its block on replay dimension 2 —
  is guarded by the owning tests (``tests/hitl/test_review_queue.py``),
  demonstrated by assertion, not proven by construction. Never an
  absolute "no path" claim.

**TOCTOU guard (T-07-39 doctrine).** The queued event binds the item's
content hash at submission time; the reviewer's binding echoes the hash of
what they actually reviewed. A mismatch is a returned typed
:class:`ReviewResolutionRefused`, audited ``resolved=False``, with the
event left pending.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Mapping
from datetime import datetime

from pydantic import Field, field_validator

from ccf.artifacts.protocol import ArtifactStoreError, parse_artifact_uri
from ccf.authz.capability import Authorized, HitlSubmit, verify
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.contracts.claims import LineageEntry
from ccf.controlplane.audit import AuditLog
from ccf.controlplane.registry import ControlPlaneProtocol
from ccf.hitl.approval_gate import HITL_ACTION_ARTIFACT_CLASS
from ccf.hitl.identity_binding import SignedHitlAction
from ccf.hitl.principal import HumanPrincipalBinding
from ccf.hitl.transport import (
    HITLTransportProtocol,
    HitlActionSubmission,
    PendingHitlEvent,
    enforce_attestation,
    resolve_hitl_policy,
)
from ccf.peering.identity import IdentityProvider, JsonWebKey

__ccf_mode__ = "algorithmic"

__all__ = [
    "ReviewActionRecord",
    "ReviewQueue",
    "ReviewQueueItem",
    "ReviewResolution",
    "ReviewResolutionRefused",
    "UnknownReviewEventError",
]


class UnknownReviewEventError(LookupError):
    """The named event is not pending on the transport — broken wiring.

    Raised — never a returned refusal — on the I.1 line: a caller
    releasing an item the queue does not hold is mis-wired, not an
    expected governance outcome.
    """


class ReviewQueueItem(CCFContract):
    """One output awaiting review, with its passage-level lineage view.

    SDK-defined (CLAUDE.md §8.2; whitepaper §7.10.3). ``output_ref`` pins
    the reviewed artifact by versioned URI (D-IMPL-26); ``lineage``
    carries the passage-anchored provenance the reviewer inspects — the
    real :class:`~ccf.contracts.claims.LineageEntry` type, at least one
    entry required: an unanchored output has nothing for a reviewer to
    trace, which defeats citation-aware review.
    """

    output_ref: str
    lineage: tuple[LineageEntry, ...] = Field(min_length=1)

    @field_validator("output_ref")
    @classmethod
    def _output_ref_is_pinned(cls, value: str) -> str:
        try:
            parse_artifact_uri(value)
        except ArtifactStoreError as error:
            raise ValueError(str(error)) from error
        return value


class ReviewActionRecord(CCFContract):
    """One completed review action, in full — the dimension-2 payload.

    SDK-defined (CLAUDE.md §8.2). Pairs what was queued (the event and the
    item, lineage included) with what the human did (the submission, with
    the required principal binding) and the verdict. Canonically
    serializable, so the queue pre-serializes it once and replay records
    it verbatim (the 07-05 keyword discipline).
    """

    event: PendingHitlEvent
    item: ReviewQueueItem
    submission: HitlActionSubmission
    released: bool


class ReviewResolution(CCFContract):
    """A completed review decision — outcome plus the pre-serialized block.

    ``hitl_actions_block`` is the canonical serialization of ``record``,
    serialized once by the queue and passed verbatim to
    :func:`ccf.replay.record.build_replay_record`'s ``hitl_actions``
    keyword (dimension 2). Derived here, never reconstructed by the record
    builder.
    """

    record: ReviewActionRecord
    hitl_actions_block: str


class ReviewResolutionRefused(CCFContract):
    """A resolution the queue refuses — typed value, audited
    ``resolved=False``.

    The TOCTOU case foremost: the reviewer's binding names a content hash
    other than the item's submission-time hash. The pending event
    survives, so the reviewer can re-review the current item.
    """

    tenant: str
    event_key: str
    reason: str


class ReviewQueue:
    """The asynchronous review HITL primitive (CLAUDE.md §8.2; HITL-01).

    Everything is injected — transport, audit log, clock — in the
    constructor-injection discipline of every Control Plane service: the
    queue holds no reviewer role, no release rule, and no wall clock of
    its own. Which policy governs a review comes from the pinned
    ``policy_ref`` carried on the pending event (CINV-01).

    Args:
        transport: The typed HITL queue items surface on and actions
            return through (D-IMPL-20 — the only authority path).
        audit: The append-only log every release and rejection lands in,
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
        # Side-band item state, keyed (tenant, event_key). Per-instance
        # and in-memory — narrower than the transport, which may be shared
        # or durable — so :meth:`_resolve` verifies this state exists
        # *before* touching the transport (WR-01) and surfaces absence as
        # the typed broken-wiring error, never a bare ``KeyError`` after
        # the authority path has already recorded the action. Guarded by
        # its own lock: the transport's lock does not cover this dict.
        self._state_lock = threading.Lock()
        self._items: dict[tuple[str, str], ReviewQueueItem] = {}

    def submit_for_review(
        self,
        *,
        tenant: str,
        event_key: str,
        workflow_state_ref: str,
        item: ReviewQueueItem,
        policy_ref: str | None = None,
        requested_by: str | None = None,
    ) -> PendingHitlEvent:
        """Queue one output for asynchronous review pre-release.

        ``requested_by`` (SEC-006; `D-IMPL-366` G6 (a)) is carried on the
        event as data and NOT judged for this event class.

        The item's content hash — output ref and lineage together — is
        bound into the pending event at submission time; the reviewer's
        binding must echo it (TOCTOU guard). Submission is the producing
        agent's side, not a human action; the human action audits at
        :meth:`release` / :meth:`reject`.
        """
        event = PendingHitlEvent(
            event_key=event_key,
            event_class="review-queue",
            tenant=tenant,
            workflow_state_ref=workflow_state_ref,
            product_content_hash=content_hash(item),
            policy_ref=policy_ref,
            requested_by=requested_by,
        )
        self._transport.enqueue(event=event)
        with self._state_lock:
            self._items[(tenant, event_key)] = item
        return event

    def items(
        self, *, tenant: str
    ) -> tuple[tuple[PendingHitlEvent, ReviewQueueItem], ...]:
        """The tenant's queued reviews, oldest first, without consuming.

        Each pair carries the pending event and the item with its
        passage-level lineage — the view a deployment's task system
        renders for its reviewers (D-23: one tenant's view says nothing
        about another's).
        """
        with self._state_lock:
            retained = dict(self._items)
        return tuple(
            (pending, retained[(tenant, pending.event_key)])
            for pending in self._transport.pending(tenant=tenant)
            if pending.event_class == "review-queue"
            and (tenant, pending.event_key) in retained
        )

    def release(
        self,
        authorized: Authorized[HitlSubmit],
        *,
        event_key: str,
        principal: HumanPrincipalBinding,
        annotation: str | None = None,
        attestation: SignedHitlAction | None = None,
    ) -> ReviewResolution | ReviewResolutionRefused:
        """Release one reviewed output under a bound human decision.

        The principal binding is required by type (D-IMPL-21; the D-22
        type-unrepresentable leg). Returns the resolution with the
        pre-serialized dimension-2 block, or a typed refusal on a TOCTOU
        hash mismatch.

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
        declares ``signed_binding_required``, this surface verifies
        ``attestation`` before any queue consumption — a refused
        release raises and leaves the event pending. Verification is
        read-only and holds no lock; the transport re-verifies
        independently at submission (idempotent double verification,
        D-13).
        """
        return self._resolve(
            authorized,
            event_key=event_key,
            principal=principal,
            annotation=annotation,
            released=True,
            attestation=attestation,
        )

    def reject(
        self,
        authorized: Authorized[HitlSubmit],
        *,
        event_key: str,
        principal: HumanPrincipalBinding,
        annotation: str | None = None,
        attestation: SignedHitlAction | None = None,
    ) -> ReviewResolution | ReviewResolutionRefused:
        """Reject one reviewed output — a recorded action, audited
        ``resolved=False``, never an absence. Signed-binding verification
        applies exactly as at :meth:`release` (D-IMPL-69; D-12 — every
        authority-bearing surface verifies)."""
        return self._resolve(
            authorized,
            event_key=event_key,
            principal=principal,
            annotation=annotation,
            released=False,
            attestation=attestation,
        )

    # -- helpers ---------------------------------------------------------------

    def _resolve(
        self,
        authorized: Authorized[HitlSubmit],
        *,
        event_key: str,
        principal: HumanPrincipalBinding,
        annotation: str | None,
        released: bool,
        attestation: SignedHitlAction | None = None,
    ) -> ReviewResolution | ReviewResolutionRefused:
        # The capability first (D-IMPL-353 §1.2): verified for its kind and
        # for THIS event before the queue is read; the tenant is the
        # capability's and nothing else (§1.3).
        verify(authorized, kind=HitlSubmit, resource=event_key)
        tenant = authorized.tenant
        event = next(
            (
                pending
                for pending in self._transport.pending(tenant=tenant)
                if pending.event_key == event_key
                and pending.event_class == "review-queue"
            ),
            None,
        )
        if event is None:
            raise UnknownReviewEventError(
                f"no queued review {event_key!r} for tenant {tenant!r};"
                " resolving an item the queue does not hold is broken"
                " wiring, not a governance outcome (I.1 line)"
            )
        if principal.product_content_hash != event.product_content_hash:
            self._record(
                event_key,
                version=event.product_content_hash,
                resolved=False,
                actor=principal.approver.subject_id,
            )
            return ReviewResolutionRefused(
                tenant=tenant,
                event_key=event_key,
                reason=(
                    "the binding's product_content_hash"
                    f" {principal.product_content_hash!r} does not equal the"
                    " item's submission-time hash"
                    f" {event.product_content_hash!r}: the output changed"
                    " between submission and the review action (T-07-39"
                    " doctrine). The event stays pending — re-review the"
                    " current item and act on its hash"
                ),
            )
        with self._state_lock:
            item = self._items.get((tenant, event_key))
        if item is None:
            # WR-01: the pending event exists on the transport but this
            # instance holds no queued item for it — the transport may be
            # shared or durable while this side-band state is
            # per-instance. Refused typed and *before* any transport
            # mutation.
            raise UnknownReviewEventError(
                f"review {event_key!r} for tenant {tenant!r} is pending"
                " on the transport but this ReviewQueue instance holds"
                " no queued item for it; the transport is shared state"
                " while the item record is per-instance — resolve on the"
                " instance that queued the item (broken wiring, not a"
                " governance outcome; WR-01)"
            )
        submission = HitlActionSubmission(
            event_key=event_key,
            action="approve" if released else "reject",
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
            # resolver wins; the loser raises without submitting.
            raise UnknownReviewEventError(
                f"no queued review {event_key!r} for tenant {tenant!r}:"
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
            # A refused authority submission never consumes the pending
            # event: the claim is given back (re-enqueued at the tail).
            self._transport.enqueue(event=claimed)
            raise
        with self._state_lock:
            self._items.pop((tenant, event_key), None)
        self._record(
            event_key,
            version=event.product_content_hash,
            resolved=released,
            actor=principal.approver.subject_id,
        )
        record = ReviewActionRecord(
            event=event, item=item, submission=recorded, released=released
        )
        return ReviewResolution(
            record=record,
            hitl_actions_block=canonical_bytes(record).decode("utf-8"),
        )

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
