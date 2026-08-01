"""Unit conformance for the shared driver dispatch helper and error hierarchy.

WR-03 (HARD-03): the loop-aware dispatch helper (`run_coroutine_sync`,
Phase-9 CONTEXT D-09) and the typed driver-error hierarchy
(`WorkflowDriverError` / `SegmentNotExecutedError` /
`DriverStateRetrievalError`, Phase-9 CONTEXT D-10) live once, in
``ccf_runtime.orchestration.common`` (D-12), shared by all three driver
legs (D-11). These tests pin the helper's two dispatch paths and the
hierarchy's shape before any driver adopts them — always-on in CI (D-15).
"""

from __future__ import annotations

import asyncio
import threading
import time

import pytest

from ccf_runtime.orchestration import (
    DriverStateRetrievalError,
    SegmentNotExecutedError,
    WorkflowDriverError,
    run_coroutine_sync,
)

pytestmark = [pytest.mark.conformance]


async def _thread_name_after_tick() -> str:
    """A real coroutine touching the loop — returns the running thread name."""
    await asyncio.sleep(0)
    return threading.current_thread().name


def test_run_coroutine_sync_from_a_plain_sync_context() -> None:
    """No running loop: the asyncio.run path, result returned verbatim."""
    assert (
        run_coroutine_sync(_thread_name_after_tick())
        == threading.current_thread().name
    )


def test_run_coroutine_sync_from_inside_a_running_loop() -> None:
    """Inside asyncio.run-hosted code: no RuntimeError, no touching the
    caller's loop — the coroutine runs on a dedicated background thread
    with its own loop (D-09)."""

    async def host() -> tuple[str, str]:
        # The sync call happens while THIS loop is running in THIS thread —
        # exactly the ADK persisted_state defect scenario (WR-03).
        return (
            run_coroutine_sync(_thread_name_after_tick()),
            threading.current_thread().name,
        )

    inner_thread, host_thread = asyncio.run(host())
    assert inner_thread != host_thread  # never the caller's loop's thread


def test_run_coroutine_sync_propagates_the_coroutine_error() -> None:
    async def boom() -> None:
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        run_coroutine_sync(boom())

    async def host() -> None:
        with pytest.raises(ValueError, match="boom"):
            run_coroutine_sync(boom())

    asyncio.run(host())


def test_run_coroutine_sync_timeout_bounds_the_join() -> None:
    """T-09-06: on the background-thread path, ``timeout`` actually unblocks
    the caller — the executor is shut down with ``wait=False`` so its
    ``__exit__``-style join cannot re-block past the enforced bound."""

    async def hang() -> None:
        await asyncio.sleep(3)

    async def host() -> float:
        start = time.monotonic()
        with pytest.raises(TimeoutError):
            run_coroutine_sync(hang(), timeout=0.2)
        return time.monotonic() - start

    elapsed = asyncio.run(host())
    assert elapsed < 2  # unblocked at ~0.2s, never joined through the 3s hang


def test_the_error_hierarchy_shape() -> None:
    """D-10: one base, two leaves; a clean break from KeyError (verified
    safe — nothing in the tree catches KeyError from drivers)."""
    assert issubclass(WorkflowDriverError, RuntimeError)
    assert issubclass(SegmentNotExecutedError, WorkflowDriverError)
    assert issubclass(DriverStateRetrievalError, WorkflowDriverError)
    assert not issubclass(SegmentNotExecutedError, KeyError)
    assert not issubclass(DriverStateRetrievalError, KeyError)
