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

from collections.abc import Callable
from datetime import datetime

from pydantic import Field, field_validator

from ccf.artifacts.protocol import ArtifactStoreError, parse_artifact_uri
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.contracts.claims import LineageEntry
from ccf.controlplane.audit import AuditLog
from ccf.hitl.approval_gate import HITL_ACTION_ARTIFACT_CLASS
from ccf.hitl.principal import HumanPrincipalBinding
from ccf.hitl.transport import (
    HITLTransportProtocol,
    HitlActionSubmission,
    PendingHitlEvent,
)

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
        self._items: dict[tuple[str, str], ReviewQueueItem] = {}

    def submit_for_review(
        self,
        *,
        tenant: str,
        event_key: str,
        workflow_state_ref: str,
        item: ReviewQueueItem,
        policy_ref: str | None = None,
    ) -> PendingHitlEvent:
        """Queue one output for asynchronous review pre-release.

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
        )
        self._transport.enqueue(event=event)
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
        return tuple(
            (pending, self._items[(tenant, pending.event_key)])
            for pending in self._transport.pending(tenant=tenant)
            if pending.event_class == "review-queue"
            and (tenant, pending.event_key) in self._items
        )

    def release(
        self,
        *,
        tenant: str,
        event_key: str,
        principal: HumanPrincipalBinding,
        annotation: str | None = None,
    ) -> ReviewResolution | ReviewResolutionRefused:
        """Release one reviewed output under a bound human decision.

        The principal binding is required by type (D-IMPL-21; the D-22
        type-unrepresentable leg). Returns the resolution with the
        pre-serialized dimension-2 block, or a typed refusal on a TOCTOU
        hash mismatch.
        """
        return self._resolve(
            tenant=tenant,
            event_key=event_key,
            principal=principal,
            annotation=annotation,
            released=True,
        )

    def reject(
        self,
        *,
        tenant: str,
        event_key: str,
        principal: HumanPrincipalBinding,
        annotation: str | None = None,
    ) -> ReviewResolution | ReviewResolutionRefused:
        """Reject one reviewed output — a recorded action, audited
        ``resolved=False``, never an absence."""
        return self._resolve(
            tenant=tenant,
            event_key=event_key,
            principal=principal,
            annotation=annotation,
            released=False,
        )

    # -- helpers ---------------------------------------------------------------

    def _resolve(
        self,
        *,
        tenant: str,
        event_key: str,
        principal: HumanPrincipalBinding,
        annotation: str | None,
        released: bool,
    ) -> ReviewResolution | ReviewResolutionRefused:
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
        submission = HitlActionSubmission(
            event_key=event_key,
            tenant=tenant,
            action="approve" if released else "reject",
            principal=principal,
            annotation=annotation,
        )
        self._transport.submit(submission=submission)
        self._consume(tenant, event_key)
        item = self._items.pop((tenant, event_key))
        self._record(
            event_key,
            version=event.product_content_hash,
            resolved=released,
            actor=principal.approver.subject_id,
        )
        record = ReviewActionRecord(
            event=event, item=item, submission=submission, released=released
        )
        return ReviewResolution(
            record=record,
            hitl_actions_block=canonical_bytes(record).decode("utf-8"),
        )

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
