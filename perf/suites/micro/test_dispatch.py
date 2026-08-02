"""``run_coroutine_sync`` overhead micro-benchmark (PERF-01; D-05).

The Phase-10 deferred item: quantify the sync-dispatch overhead of
``ccf_runtime.orchestration.common.run_coroutine_sync`` — the loop-aware
dispatch every ``OrchestrationProtocol`` driver leg's sync introspection
seam routes through (Phase-9 D-09, WR-03). This suite *measures* the
overhead; optimizing it is explicitly out of scope here (deferred — the
number feeds Phase 14's PERFORMANCE.md).

Plain sync test function on purpose (RESEARCH Pitfall 7): no asyncio
plugin involvement, so the benchmarked path is exactly the production call
shape — a sync caller with no running loop, dispatching a coroutine.

Timing judgments live only in ``perf/gate.py`` (D-02).
"""

from __future__ import annotations

from ccf_runtime.orchestration.common import run_coroutine_sync

#: A sentinel constant the trivial coroutine returns, so the correctness
#: assert proves the dispatched coroutine actually ran to completion.
_SENTINEL = object()


async def _trivial() -> object:
    return _SENTINEL


def test_run_coroutine_sync_overhead(benchmark) -> None:
    def dispatch() -> object:
        # A fresh coroutine per round — a coroutine object is single-use,
        # and constructing it is part of the production call shape (D-05).
        return run_coroutine_sync(_trivial())

    result = benchmark(dispatch)
    assert result is _SENTINEL
