"""``ReviewQueue`` — the asynchronous review HITL primitive (07-08).

Written before the implementation per the TDD discipline. The claims:

A queued item exposes the output reference plus its passage-level lineage
— the real :class:`~ccf.contracts.claims.LineageEntry` /
:class:`~ccf.contracts.claims.PassageAnchor` types, not a string — so a
reviewer can see what each claim anchors to (whitepaper §7.10.3); an item
without lineage is unconstructible; release requires a bound review action
and lands on dimension 2 (a rejection is audited ``resolved=False``); two
reviewers on two tenants' queues are isolated (D-23); resolving an event
the queue does not hold raises (broken wiring, I.1 line).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.contracts.claims import LineageEntry, PassageAnchor
from ccf.controlplane.audit import AuditLog
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
    UnknownReviewEventError,
)
from ccf.hitl.transport import HitlActionSubmission, InMemoryHitlTransport

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking"


def _hitl() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "hitl.yaml").read_text()
    )
    return loaded


def _clock() -> Any:
    state = {"now": datetime(2026, 7, 30, tzinfo=UTC)}

    def clock() -> datetime:
        state["now"] += timedelta(seconds=1)
        return state["now"]

    return clock


def _principal(
    fixture: dict[str, Any], approver_key: str, *, product_content_hash: str
) -> HumanPrincipalBinding:
    approver = fixture["approvers"][approver_key]
    return HumanPrincipalBinding(
        approver=ApproverIdentity(**approver["identity"]),
        authentication=AuthenticationContext(**approver["authentication"]),
        action_time=datetime.fromisoformat(approver["action_time"]),
        product_content_hash=product_content_hash,
    )


def _queue() -> tuple[ReviewQueue, InMemoryHitlTransport, AuditLog]:
    transport = InMemoryHitlTransport()
    audit = AuditLog()
    queue = ReviewQueue(transport=transport, audit=audit, clock=_clock())
    return queue, transport, audit


def _item(document: dict[str, Any]) -> ReviewQueueItem:
    return ReviewQueueItem(
        output_ref=document["output_ref"],
        lineage=tuple(
            LineageEntry(**entry) for entry in document["lineage"]
        ),
    )


def _submit(
    queue: ReviewQueue, fixture: dict[str, Any]
) -> tuple[dict[str, Any], ReviewQueueItem]:
    document = fixture["review"]["event"]
    item = _item(fixture["review"]["item"])
    queue.submit_for_review(
        tenant=document["tenant"],
        event_key=document["event_key"],
        workflow_state_ref=document["workflow_state_ref"],
        item=item,
        policy_ref=document.get("policy_ref"),
    )
    return document, item


def test_a_queued_item_exposes_passage_level_lineage() -> None:
    """The reviewer sees the output plus what each claim anchors to, in the
    real lineage types (whitepaper §7.10.3), never a string."""
    fixture = _hitl()
    queue, transport, _ = _queue()
    document, item = _submit(queue, fixture)
    ((event, queued),) = queue.items(tenant=document["tenant"])
    assert queued == item
    assert isinstance(queued.lineage[0], LineageEntry)
    anchor = queued.lineage[0].passage_anchor
    assert isinstance(anchor, PassageAnchor)
    expected = fixture["review"]["item"]["lineage"][0]["passage_anchor"]
    assert anchor.kind == expected["kind"]
    assert anchor.locator == expected["locator"]
    assert event.event_class == "review-queue"
    assert event.product_content_hash == content_hash(item)
    (pending,) = transport.pending(tenant=document["tenant"])
    assert pending == event


def test_an_item_without_lineage_is_unconstructible() -> None:
    """Citation-aware review is the point: no lineage, no queue item."""
    fixture = _hitl()
    with pytest.raises(ValidationError):
        ReviewQueueItem(
            output_ref=fixture["review"]["item"]["output_ref"], lineage=()
        )


def test_an_unbound_release_is_unrepresentable() -> None:
    """The typed transport contract requires the principal by type (D-22
    type-unrepresentable leg)."""
    fixture = _hitl()
    document = fixture["review"]["event"]
    with pytest.raises(ValidationError):
        HitlActionSubmission(  # type: ignore[call-arg]
            event_key=document["event_key"],
            tenant=document["tenant"],
            action="approve",
        )


def test_a_release_is_a_bound_action_on_dimension_two() -> None:
    fixture = _hitl()
    queue, transport, audit = _queue()
    document, item = _submit(queue, fixture)
    resolution = queue.release(
        tenant=document["tenant"],
        event_key=document["event_key"],
        principal=_principal(
            fixture, "credit_officer", product_content_hash=content_hash(item)
        ),
    )
    assert isinstance(resolution, ReviewResolution)
    assert isinstance(resolution.record, ReviewActionRecord)
    assert resolution.record.released
    assert resolution.record.item == item
    assert resolution.hitl_actions_block == canonical_bytes(
        resolution.record
    ).decode("utf-8")
    assert queue.items(tenant=document["tenant"]) == ()
    (submission,) = transport.submissions(tenant=document["tenant"])
    assert submission.action == "approve"
    events = audit.events()
    assert events[-1].action == "hitl_action" and events[-1].resolved


def test_a_rejection_is_recorded_resolved_false() -> None:
    fixture = _hitl()
    queue, _, audit = _queue()
    document, item = _submit(queue, fixture)
    resolution = queue.reject(
        tenant=document["tenant"],
        event_key=document["event_key"],
        principal=_principal(
            fixture, "credit_officer", product_content_hash=content_hash(item)
        ),
    )
    assert isinstance(resolution, ReviewResolution)
    assert not resolution.record.released
    events = audit.events()
    assert events[-1].action == "hitl_action" and not events[-1].resolved


def test_two_tenants_queues_are_isolated() -> None:
    """D-23: a view of one tenant's queue says nothing about another's, and
    resolving one tenant's item never touches the other's queue."""
    fixture = _hitl()
    queue, _, _ = _queue()
    document, item = _submit(queue, fixture)
    other = fixture["review"]["other_tenant"]
    other_item = _item(other["item"])
    queue.submit_for_review(
        tenant=other["event"]["tenant"],
        event_key=other["event"]["event_key"],
        workflow_state_ref=other["event"]["workflow_state_ref"],
        item=other_item,
    )
    ((_, mine),) = queue.items(tenant=document["tenant"])
    assert mine == item
    ((_, theirs),) = queue.items(tenant=other["event"]["tenant"])
    assert theirs == other_item
    queue.release(
        tenant=document["tenant"],
        event_key=document["event_key"],
        principal=_principal(
            fixture, "credit_officer", product_content_hash=content_hash(item)
        ),
    )
    assert queue.items(tenant=document["tenant"]) == ()
    assert len(queue.items(tenant=other["event"]["tenant"])) == 1


def test_releasing_an_unknown_event_raises() -> None:
    fixture = _hitl()
    queue, _, _ = _queue()
    document = fixture["review"]["event"]
    with pytest.raises(UnknownReviewEventError):
        queue.release(
            tenant=document["tenant"],
            event_key="acme-bank/exec-rev/no-such-event",
            principal=_principal(
                fixture,
                "credit_officer",
                product_content_hash=content_hash({"any": "thing"}),
            ),
        )
