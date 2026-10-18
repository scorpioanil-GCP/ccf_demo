# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""A HITL primitive that claims another pause's request gives it back and refuses (D-IMPL-391).

Found by the read-only review of the option-3 build (``4be75f02``). Every
primitive reads the oldest request under its key, checks it against the pause
its principal names, and only then claims through ``remove``, which takes the
oldest request under the key whatever pause it is for. When a concurrent act —
another approver resolving it, or a rebind retiring it — takes that request in
between, ``remove`` hands the primitive the request for ANOTHER pause queued
behind it. Since the transport judges a submission against the pause it names
(Dave's ruling of 2026-10-17 18:54 MST), the primitive's own submission was
recorded ``missing`` and its claim on the other pause's request was left
behind, with that request gone from the queue: a verdict sent straight to the
queue naming that pause was then stamped ``claimed`` and counted, while no
request for it was waiting. Measured: on ``4569d9f0`` the same schedule was
refused; on ``4be75f02`` it passed.

Each primitive now gives back a claimed request whose pause is not the one its
principal names, unanswered, and refuses as a lost race (WR-02's own refusal),
so no claim is left. The interleaving is forced by retiring the primitive's
own request inside its ``remove`` — the concurrent act — before the real
claim. Test vocabulary only (CINV-01).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ccf.contracts.canonical import content_hash
from ccf.hitl.approval_gate import UnknownGateEventError
from ccf.hitl.escalation import ExplicitEscalation, UnknownEscalationEventError
from ccf.hitl.override import UnknownOverrideEventError
from ccf.hitl.review_queue import UnknownReviewEventError
from ccf.hitl.transport import HitlActionSubmission, InMemoryHitlTransport
from tests.hitl import test_approval_gate as ag
from tests.hitl import test_escalation as es
from tests.hitl import test_override as ov
from tests.hitl import test_review_queue as rq
from tests.hitl.capabilities import submit_capability
from tests.workflow import test_engine as eh

ANOTHER_PAUSE = "e" * 64


def _straight_verdict(transport: InMemoryHitlTransport, *, tenant: str, event_key: str, pause: str) -> HitlActionSubmission:
    """A verdict naming ``pause``, sent straight to the queue (the submit-only door)."""
    return transport.submit(
        submit_capability(tenant=tenant, principal="door-approver", event_key=event_key),
        submission=HitlActionSubmission(
            event_key=event_key,
            action="approve",
            principal=eh._binding(pause, subject_id="door-approver"),
        ),
    )


def _race(
    transport: InMemoryHitlTransport,
    *,
    tenant: str,
    event_key: str,
    own_pause: str,
    resolve: Callable[[], Any],
) -> tuple[BaseException | None, HitlActionSubmission]:
    """File a request for another pause behind the primitive's own, retire the
    primitive's own request inside its ``remove``, resolve, then send a verdict
    naming the other pause straight to the queue. Returns what the primitive
    raised (or ``None``) and that verdict as recorded."""
    (own,) = [e for e in transport.pending(tenant=tenant) if e.event_key == event_key]
    assert own.product_content_hash == own_pause
    transport.enqueue(event=own.model_copy(update={"product_content_hash": ANOTHER_PAUSE}))
    real_remove = transport.remove
    armed = {"on": True}

    def remove_after_a_concurrent_retirement(**kwargs: Any) -> Any:
        if armed["on"]:
            armed["on"] = False
            transport.retire(tenant=tenant, event_key=event_key, product_content_hash=own_pause)
        return real_remove(**kwargs)

    transport.remove = remove_after_a_concurrent_retirement  # type: ignore[method-assign]
    raised: BaseException | None = None
    try:
        resolve()
    except BaseException as error:  # asserted on by the caller
        raised = error
    finally:
        del transport.remove
    stray = _straight_verdict(transport, tenant=tenant, event_key=event_key, pause=ANOTHER_PAUSE)
    return raised, stray


def _assert_given_back(
    transport: InMemoryHitlTransport,
    *,
    tenant: str,
    event_key: str,
    outcome: tuple[BaseException | None, HitlActionSubmission],
    lost_race: type[BaseException],
) -> None:
    raised, stray = outcome
    assert stray.event_state_at_submit != "claimed", (
        "the primitive left a claim on another pause's request, and a verdict sent"
        " straight to the queue naming that pause was stamped as its answer"
    )
    assert isinstance(raised, lost_race), f"the primitive did not refuse the lost race: {raised!r}"
    assert [e.product_content_hash for e in transport.pending(tenant=tenant) if e.event_key == event_key] == [
        ANOTHER_PAUSE
    ], "the other pause's request was not given back"


def test_the_approval_gate_gives_back_another_pauses_request() -> None:
    fixture = ag._hitl()
    gate, transport, _ = ag._gate()
    event = ag._event(fixture)
    transport.enqueue(event=event)
    pause = event.product_content_hash
    outcome = _race(
        transport, tenant=event.tenant, event_key=event.event_key, own_pause=pause,
        resolve=lambda: gate.resolve(
            ag._authorized(event.tenant, event.event_key),
            event_key=event.event_key,
            action="approve",
            principal=ag._principal(fixture, product_content_hash=pause),
        ),
    )
    _assert_given_back(
        transport, tenant=event.tenant, event_key=event.event_key, outcome=outcome,
        lost_race=UnknownGateEventError,
    )
    own = [x for x in transport.submissions(tenant=event.tenant) if x.principal.product_content_hash == pause]
    assert own == [], "the lost race recorded a submission for the primitive's own pause"


def test_an_escalation_gives_back_another_pauses_request() -> None:
    fixture = es._hitl()
    escalation, transport, _ = es._escalation()
    es._hand_off(escalation, fixture, ExplicitEscalation(reason=fixture["escalation"]["explicit_reason"]))
    document = es._event_document(fixture)
    pause = content_hash(document)
    outcome = _race(
        transport, tenant=document["tenant"], event_key=document["event_key"], own_pause=pause,
        resolve=lambda: escalation.resolve(
            es._authorized(document["tenant"], document["event_key"]),
            event_key=document["event_key"],
            action="approve",
            principal=es._principal(fixture, product_content_hash=pause),
        ),
    )
    _assert_given_back(
        transport, tenant=document["tenant"], event_key=document["event_key"], outcome=outcome,
        lost_race=UnknownEscalationEventError,
    )


def test_an_override_boundary_gives_back_another_pauses_request() -> None:
    fixture = ov._hitl()
    boundary, transport, _ = ov._boundary()
    original = ov._propose(boundary, fixture)
    document = fixture["override"]["event"]
    pause = content_hash(original)
    outcome = _race(
        transport, tenant=document["tenant"], event_key=document["event_key"], own_pause=pause,
        resolve=lambda: boundary.resolve(
            ov._authorized(document["tenant"], document["event_key"]),
            event_key=document["event_key"],
            principal=ov._principal(fixture, product_content_hash=pause),
        ),
    )
    _assert_given_back(
        transport, tenant=document["tenant"], event_key=document["event_key"], outcome=outcome,
        lost_race=UnknownOverrideEventError,
    )


def test_a_review_queue_gives_back_another_pauses_request() -> None:
    fixture = rq._hitl()
    queue, transport, _ = rq._queue()
    document, item = rq._submit(queue, fixture)
    pause = content_hash(item)
    outcome = _race(
        transport, tenant=document["tenant"], event_key=document["event_key"], own_pause=pause,
        resolve=lambda: queue.release(
            rq._authorized(document["tenant"], document["event_key"]),
            event_key=document["event_key"],
            principal=rq._principal(fixture, "credit_officer", product_content_hash=pause),
        ),
    )
    _assert_given_back(
        transport, tenant=document["tenant"], event_key=document["event_key"], outcome=outcome,
        lost_race=UnknownReviewEventError,
    )
