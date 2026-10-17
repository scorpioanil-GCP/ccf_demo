# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""One paused run, one approval request: ``enqueue`` is atomic on the paused run's fingerprint (D-IMPL-391).

Dave's ruling 4(a) of 2026-10-17 13:27 MST (*"Key the duplicate-request fix by
the paused run's fingerprint."*) and his answer of 15:25 MST: *"``enqueue`` is
atomic on ``(tenant, event_key, product_content_hash)``. The same paused run's
request is filed only once. Third-party transports must meet the contract."*
Before the change a slow suspension, or a recovery overlapping another, could
file the same request twice (pinned as a residual in
``tests/workflow/test_restore_missing_approval_request.py``).

The contract
(``src/ccf/hitl/transport.py::HITLTransportProtocol.enqueue``): an event whose
``(tenant, event_key, product_content_hash)`` is already PENDING is not queued
again; an outstanding claim on the key does not count as pending, so the
primitives' give-back after a refused submission still re-files its event; an
enqueue that appends still discards the claim; the check and the append are one
atomic step.

The race test forces the interleaving on the reference transport: a rendezvous
on its read of its own pending queue, which is exactly between the absence
check and the append. With the check under the transport's lock the second
enqueue cannot reach its check, the first writer's wait times out, and one
request results; with the check outside the lock (severing S8) both writers pass
it and two identical requests result, every time. Test vocabulary only (CINV-01).
"""

from __future__ import annotations

import threading
from typing import Any

from ccf.hitl.transport import InMemoryHitlTransport, PendingHitlEvent

TENANT = "t"
EVENT_KEY = "t/exec/gate"
PAUSED = "a" * 64
ANOTHER_PAUSE = "b" * 64
_RENDEZVOUS_SECONDS = 1.0
_JOIN_SECONDS = 30.0


def request(product_content_hash: str = PAUSED) -> PendingHitlEvent:
    return PendingHitlEvent(
        event_key=EVENT_KEY,
        event_class="approval-gate",
        tenant=TENANT,
        workflow_state_ref="t/exec",
        product_content_hash=product_content_hash,
    )


class _ReadThenWait(dict):  # type: ignore[type-arg]
    """The transport's pending map, with a rendezvous on every ``get``: each
    reader, having read, waits for the other reader to have read too."""

    def __init__(self, barrier: threading.Barrier) -> None:
        super().__init__()
        self._barrier = barrier

    def get(self, key: Any, default: Any = None) -> Any:
        value = super().get(key, default)
        try:
            self._barrier.wait()
        except threading.BrokenBarrierError:
            pass  # the locked path: the other writer could not reach its read
        return value


def test_two_racing_enqueues_of_one_paused_runs_request_file_one() -> None:
    transport = InMemoryHitlTransport()
    transport._pending = _ReadThenWait(threading.Barrier(2, timeout=_RENDEZVOUS_SECONDS))  # type: ignore[assignment]
    errors: list[str] = []

    def enqueue() -> None:
        try:
            transport.enqueue(event=request())
        except BaseException as exc:  # reported by name, asserted below
            errors.append(f"{type(exc).__name__}: {exc}")

    threads = [threading.Thread(target=enqueue, daemon=True) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(_JOIN_SECONDS)
    assert not any(thread.is_alive() for thread in threads), "an enqueue never returned"
    assert errors == []
    queued = list(dict.get(transport._pending, TENANT, ()))
    assert queued == [request()], f"{len(queued)} identical requests queued for one paused run"


def test_an_enqueue_of_a_request_already_pending_files_nothing() -> None:
    transport = InMemoryHitlTransport()
    transport.enqueue(event=request())
    transport.enqueue(event=request())
    assert transport.pending(tenant=TENANT) == (request(),)


def test_a_request_for_another_pause_under_the_same_key_is_filed() -> None:
    """Guard: only the same paused run's request is folded; two independent
    stores that pause the same execution file two requests (a disclosed limit:
    each needs its own approval)."""
    transport = InMemoryHitlTransport()
    transport.enqueue(event=request(PAUSED))
    transport.enqueue(event=request(ANOTHER_PAUSE))
    assert [e.product_content_hash for e in transport.pending(tenant=TENANT)] == [
        PAUSED,
        ANOTHER_PAUSE,
    ]


def test_a_claimed_request_given_back_is_filed_again_and_its_claim_discarded() -> None:
    """Guard: a claim does not count as pending, so the primitives' give-back
    (remove, refused submit, enqueue) re-files the request and leaves no claim."""
    transport = InMemoryHitlTransport()
    transport.enqueue(event=request())
    claimed = transport.remove(tenant=TENANT, event_key=EVENT_KEY)
    assert claimed == request() and transport.pending(tenant=TENANT) == ()
    transport.enqueue(event=request())
    assert transport.pending(tenant=TENANT) == (request(),)
    assert (TENANT, EVENT_KEY) not in transport._claims
