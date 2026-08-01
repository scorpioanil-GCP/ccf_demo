"""CR-01 — the Control Plane audit log's thread safety under a live hammer.

Claim pinned here (Phase-10 review CR-01; the WR-02 transport precedent):
:class:`~ccf.controlplane.audit.AuditLog.append` assigns sequence numbers
and appends under one lock, so the concurrent appends HARD-04 introduced —
``ControlPlaneTenantAuthorizer.authorize()`` appends one ``authz_decision``
event per door request from FastAPI's threadpool — can neither duplicate
nor skip a sequence number, preserving the "gaps are detectable" contract.

Deadlock detection is bounded ``join(timeout=...)`` + ``pytest.fail``, and
the hammer is deterministic (fixed thread/op counts), matching the
transport-concurrency test's discipline.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime

import pytest

from ccf.controlplane.audit import AuditLog

THREAD_COUNT = 16
APPENDS_PER_THREAD = 200
JOIN_TIMEOUT_SECONDS = 30.0

OCCURRED_AT = datetime(2026, 8, 1, 12, 0, 0, tzinfo=UTC)


def test_concurrent_appends_never_duplicate_or_skip_sequence_numbers() -> None:
    """16 threads x 200 appends: sequence numbers stay a gapless 0..N-1."""
    log = AuditLog()
    barrier = threading.Barrier(THREAD_COUNT)
    errors: list[BaseException] = []

    def hammer(index: int) -> None:
        try:
            barrier.wait(timeout=JOIN_TIMEOUT_SECONDS)
            for i in range(APPENDS_PER_THREAD):
                log.append(
                    action="authz_decision",
                    key=f"tenant-{index}",
                    version="1.0.0",
                    resolved=True,
                    occurred_at=OCCURRED_AT,
                    actor=f"principal-{index}",
                    authz_action_id=f"test.action/{index}/{i}",
                    authz_matched_pattern="tenant-*",
                )
        except BaseException as error:  # noqa: BLE001 - collected for report
            errors.append(error)

    threads = [
        threading.Thread(target=hammer, args=(index,), name=f"append-{index}")
        for index in range(THREAD_COUNT)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=JOIN_TIMEOUT_SECONDS)
        if thread.is_alive():
            pytest.fail(
                f"thread {thread.name} did not finish within"
                f" {JOIN_TIMEOUT_SECONDS}s — deadlock in AuditLog.append"
                " under concurrent load (CR-01)"
            )

    assert errors == [], f"worker threads raised: {errors!r}"

    events = log.events()
    expected_total = THREAD_COUNT * APPENDS_PER_THREAD
    assert len(events) == expected_total
    assert len(log) == expected_total

    sequences = [event.sequence for event in events]
    # Gapless and duplicate-free: exactly 0..N-1, in log order.
    assert sequences == list(range(expected_total))
