# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The HITL queue retires, and judges a verdict, by the paused run's fingerprint (D-IMPL-391).

Dave's ruling of 2026-10-17 18:54 MST (option 3): *"File the new request first,
then remove the old request with a new queue step that matches its exact
fingerprint and leaves no claim. Count an approval sent straight to the queue
only while the request for this exact pause is waiting."* The fingerprint is
``(tenant, event_key, product_content_hash)``: the content hash of the suspended
record, which names the state store that wrote it.

* :meth:`~ccf.hitl.transport.HITLTransportProtocol.retire` removes every pending
  request bearing the fingerprint, wherever it sits, keeps every other request in
  place and in order, returns what it removed oldest first, and records NO claim
  — unlike ``remove``, a retirement is not a resolution. It discards a claim only
  when the claimed request bears the same fingerprint.
* :meth:`~ccf.hitl.transport.HITLTransportProtocol.submit` stamps a verdict's
  state against the request for the pause the verdict NAMES: ``claimed`` when a
  primitive's claim is on that pause's request, ``pending`` when that pause's
  request is waiting (wherever it sits under the key), else ``missing`` — never
  authority (``D-IMPL-366`` H2, narrowed from "any request under the key"). A
  claim on another pause's request is neither used nor consumed.

New transport members are probed with ``getattr``, so a red before the change
fails on an assertion. Test vocabulary only (CINV-01).
"""

from __future__ import annotations

from typing import Any

from ccf.hitl.transport import HitlActionSubmission, InMemoryHitlTransport, PendingHitlEvent
from tests.hitl.capabilities import submit_capability
from tests.workflow import test_engine as eh

TENANT = "t"
EVENT_KEY = "t/exec/gate"
OTHER_KEY = "t/other/gate"
PAUSE = "a" * 64
OLD_PAUSE = "b" * 64
OTHER_PAUSE = "c" * 64
APPROVER = "approver"


def request(product_content_hash: str = PAUSE, *, event_key: str = EVENT_KEY) -> PendingHitlEvent:
    return PendingHitlEvent(
        event_key=event_key,
        event_class="approval-gate",
        tenant=TENANT,
        workflow_state_ref=event_key.rsplit("/", 1)[0],
        product_content_hash=product_content_hash,
    )


def retire(transport: Any, product_content_hash: str, *, event_key: str = EVENT_KEY) -> Any:
    method = getattr(transport, "retire", None)
    assert callable(method), "the HITL transport offers no retire"
    return method(tenant=TENANT, event_key=event_key, product_content_hash=product_content_hash)


def verdict(transport: InMemoryHitlTransport, product_content_hash: str) -> HitlActionSubmission:
    """A verdict naming ``product_content_hash``, sent straight to the queue."""
    return transport.submit(
        submit_capability(tenant=TENANT, principal=APPROVER, event_key=EVENT_KEY),
        submission=HitlActionSubmission(
            event_key=EVENT_KEY,
            action="approve",
            principal=eh._binding(product_content_hash, subject_id=APPROVER),
        ),
    )


def queued(transport: InMemoryHitlTransport) -> list[tuple[str, str]]:
    return [(e.event_key, e.product_content_hash) for e in transport.pending(tenant=TENANT)]


# --- retire ----------------------------------------------------------------------------


def test_retire_takes_every_request_of_one_pause_wherever_it_sits_and_keeps_the_rest_in_order() -> None:
    transport = InMemoryHitlTransport()
    old = request(OLD_PAUSE)
    for event in (request(OTHER_PAUSE), old, request(PAUSE, event_key=OTHER_KEY), request(PAUSE)):
        transport.enqueue(event=event)

    retired = retire(transport, OLD_PAUSE)

    assert tuple(retired) == (old,)
    assert queued(transport) == [
        (EVENT_KEY, OTHER_PAUSE),
        (OTHER_KEY, PAUSE),
        (EVENT_KEY, PAUSE),
    ]


def test_retire_records_no_claim() -> None:
    """A retirement is not a resolution: a verdict sent afterwards, with nothing
    waiting for its pause, is recorded ``missing`` and unstamped."""
    transport = InMemoryHitlTransport()
    transport.enqueue(event=request(OLD_PAUSE))
    retire(transport, OLD_PAUSE)

    recorded = verdict(transport, OLD_PAUSE)

    assert (recorded.event_state_at_submit, recorded.answered_event_class) == ("missing", None)


def test_retire_discards_a_claim_on_its_own_pause_and_leaves_any_other() -> None:
    mine = InMemoryHitlTransport()
    mine.enqueue(event=request(OLD_PAUSE))
    assert mine.remove(tenant=TENANT, event_key=EVENT_KEY) is not None
    retire(mine, OLD_PAUSE)
    assert verdict(mine, OLD_PAUSE).event_state_at_submit == "missing", (
        "a claim on the retired pause survived the retirement"
    )

    other = InMemoryHitlTransport()
    other.enqueue(event=request(PAUSE))
    assert other.remove(tenant=TENANT, event_key=EVENT_KEY) is not None
    retire(other, OLD_PAUSE)
    assert verdict(other, PAUSE).event_state_at_submit == "claimed", (
        "the retirement discarded a claim on another pause"
    )


def test_retire_of_a_pause_with_nothing_waiting_changes_nothing() -> None:
    transport = InMemoryHitlTransport()
    transport.enqueue(event=request(PAUSE))
    assert tuple(retire(transport, OLD_PAUSE)) == ()
    assert queued(transport) == [(EVENT_KEY, PAUSE)]


# --- submit judges the verdict against its own pause -----------------------------------


def test_a_verdict_naming_a_pause_with_no_request_waiting_is_missing_whatever_else_waits() -> None:
    """Only another pause's request is waiting under the key: before the ruling
    the verdict was stamped ``pending`` against it and could count."""
    transport = InMemoryHitlTransport()
    transport.enqueue(event=request(OLD_PAUSE))

    recorded = verdict(transport, PAUSE)

    assert recorded.event_state_at_submit == "missing", recorded.event_state_at_submit
    assert queued(transport) == [(EVENT_KEY, OLD_PAUSE)]


def test_a_verdict_naming_a_pause_whose_request_waits_behind_another_is_pending() -> None:
    transport = InMemoryHitlTransport()
    transport.enqueue(event=request(OLD_PAUSE))
    transport.enqueue(event=request(PAUSE))
    assert verdict(transport, PAUSE).event_state_at_submit == "pending"


def test_a_claim_on_another_pause_neither_stamps_the_verdict_nor_is_consumed_by_it() -> None:
    """A primitive holds a claim on the old pause's request; a verdict naming the
    new pause is judged against the new pause's request, and the primitive's own
    submission still finds its claim."""
    transport = InMemoryHitlTransport()
    transport.enqueue(event=request(OLD_PAUSE))
    transport.enqueue(event=request(PAUSE))
    assert transport.remove(tenant=TENANT, event_key=EVENT_KEY) == request(OLD_PAUSE)

    stray = verdict(transport, PAUSE)
    own = verdict(transport, OLD_PAUSE)

    assert (stray.event_state_at_submit, stray.answered_event_class) == ("pending", None), stray
    assert (own.event_state_at_submit, own.answered_event_class) == ("claimed", "approval-gate"), own


def test_the_claimed_path_is_unchanged() -> None:
    """Guard: a primitive's claim on the pause its verdict names stamps it."""
    transport = InMemoryHitlTransport()
    transport.enqueue(event=request(PAUSE))
    assert transport.remove(tenant=TENANT, event_key=EVENT_KEY) is not None
    recorded = verdict(transport, PAUSE)
    assert (recorded.event_state_at_submit, recorded.answered_event_class) == ("claimed", "approval-gate")
