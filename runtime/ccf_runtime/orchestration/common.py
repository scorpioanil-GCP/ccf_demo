"""Shared driver mechanism — loop-aware dispatch and the typed error hierarchy.

SDK-defined (CLAUDE.md §8.1; HARD-03/WR-03 — Phase-9 CONTEXT rulings
D-09..D-12). One copy for all three `OrchestrationProtocol` driver legs
(D-11/D-12): the loop-safety pattern and the error hierarchy live here, under
the orchestration tree and out of `/src` core, so the harness-neutrality lint
is unaffected and the WR-03 defect class (nested ``asyncio.run``, bare
``KeyError`` leaking from ``_outcomes`` lookups) cannot recur per-adapter.

Imports are stdlib only — asyncio and concurrent.futures — so this module
stays inside the algorithmic posture of the package and adds nothing to the
CINV-02 harness carve-out.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

from collections.abc import Coroutine

__ccf_mode__ = "algorithmic"

__all__ = [
    "DriverStateRetrievalError",
    "SegmentNotExecutedError",
    "WorkflowDriverError",
    "run_coroutine_sync",
]

_T = TypeVar("_T")


class WorkflowDriverError(RuntimeError):
    """Base of the drivers' typed error hierarchy.

    SDK-defined (CLAUDE.md §8.1; Phase-9 CONTEXT D-10, WR-03). The small
    dedicated hierarchy every driver leg raises from, mirroring the SDK's
    precise-exception style (cf. :class:`~ccf.hitl.transport.
    SignedBindingRequiredRefused` / ``SignedBindingInvalidRefused``). A
    common base so composition roots can catch driver failures as one
    class while the leaves keep absence-of-state and retrieval-failure
    distinguishable.
    """


class SegmentNotExecutedError(WorkflowDriverError):
    """The requested segment was never executed through this driver.

    SDK-defined (CLAUDE.md §8.1; Phase-9 CONTEXT D-10, WR-03). Replaces the
    bare ``KeyError`` the drivers formerly leaked from their ``_outcomes``
    lookups — deliberately NOT a ``KeyError`` subclass (a clean break,
    verified safe: nothing in the tree catches ``KeyError`` from drivers),
    so callers handle a driver-domain condition, not a dict accident. A
    distinct class from :class:`DriverStateRetrievalError` because absence
    of an execution is the caller's addressing mistake, while retrieval
    failure is the driver's substrate misbehaving.
    """


class DriverStateRetrievalError(WorkflowDriverError):
    """The driver's state substrate failed while retrieving persisted state.

    SDK-defined (CLAUDE.md §8.1; Phase-9 CONTEXT D-10, WR-03). Raised —
    chained from the underlying failure — when an introspection seam's
    substrate call (e.g., ADK's session service) fails unexpectedly, so
    state-retrieval failures surface typed rather than as raw
    ``RuntimeError`` from harness internals. Distinct from
    :class:`SegmentNotExecutedError`: this is the substrate failing, not
    the caller asking after an execution that never ran.
    """


def run_coroutine_sync(
    coro: Coroutine[object, object, _T], *, timeout: float | None = None
) -> _T:
    """Run a coroutine to completion from a sync entry point, loop-aware.

    SDK-defined (CLAUDE.md §8.1; Phase-9 CONTEXT D-09, WR-03). The drivers'
    sync introspection seams dispatch through this instead of calling
    ``asyncio.run`` directly: with no running loop in the calling thread,
    it IS ``asyncio.run``; with a running loop detected, the coroutine runs
    via ``asyncio.run`` on a dedicated single-use background thread with
    its own event loop, joined through ``Future.result`` — the caller's
    loop is never touched, blocked, or re-entered, so the nested-run
    ``RuntimeError`` (and the T-09-06 deadlock shape) cannot occur.

    Args:
        coro: The coroutine to execute.
        timeout: Optional bound, in seconds, on joining the background
            thread when one is used (T-09-06). ``None`` waits indefinitely.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coro).result(timeout)
