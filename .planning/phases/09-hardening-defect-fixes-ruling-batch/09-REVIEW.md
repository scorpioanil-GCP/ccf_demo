---
phase: 09-hardening-defect-fixes-ruling-batch
reviewed: 2026-08-01T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - docs/09-ruling-batch-minicycle.md
  - docs/DECISIONS.md
  - runtime/ccf_runtime/orchestration/adk/driver.py
  - runtime/ccf_runtime/orchestration/claude_agent/driver.py
  - runtime/ccf_runtime/orchestration/common.py
  - runtime/ccf_runtime/orchestration/__init__.py
  - runtime/ccf_runtime/orchestration/langgraph/driver.py
  - src/ccf/hitl/transport.py
  - tests/conformance/test_driver_dispatch.py
  - tests/conformance/test_orchestration.py
  - tests/hitl/test_transport_concurrency.py
findings:
  critical: 0
  warning: 4
  info: 5
  total: 9
status: issues_found
---

# Phase 9: Code Review Report

**Reviewed:** 2026-08-01
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Narrative Findings (AI reviewer)

## Summary

Reviewed the Phase-9 hardening deliverables: the shared loop-aware dispatch helper and typed driver-error hierarchy (WR-03) adopted by all three orchestration driver legs, the `threading.Lock` synchronization of `InMemoryHitlTransport` (WR-02) with D-16 verification held outside the lock, the two new test modules, and the ruling-batch documents (D-IMPL-68..73). The lock scope in `transport.py` is correct and minimal (no locked method calls another; snapshot reads copy under the lock; the D-16 TOCTOU on per-submission policy re-resolution is documented as intended semantics). The error hierarchy and `SegmentNotExecutedError` adoption is consistent across the three legs and parity-asserted in conformance. DECISIONS.md entries match the mini-cycle document's status table.

No blockers. Four warnings: the `timeout` parameter of `run_coroutine_sync` does not actually bound the wait it documents; the Claude driver's scripted transport hangs forever (rather than failing) on any error inside a scripted turn; a mypy-silenced attribute access in the LangGraph driver can surface as a raw `AttributeError`; and an `assert` used for control flow in the LangGraph gate node.

## Warnings

### WR-01: `run_coroutine_sync(timeout=...)` does not bound the wait it documents

**File:** `runtime/ccf_runtime/orchestration/common.py:100-101`
**Issue:** On the running-loop path, `executor.submit(asyncio.run, coro).result(timeout)` raises `TimeoutError` inside the `with ThreadPoolExecutor(...)` block — but the block's `__exit__` then calls `shutdown(wait=True)`, which blocks until the still-running coroutine finishes. A hung coroutine (exactly the T-09-06 deadlock shape the docstring says the timeout bounds) therefore hangs the caller indefinitely despite the timeout; the `TimeoutError` is only delivered after the hang resolves itself. The docstring's claim ("Optional bound ... on joining the background thread") is not what the code does. No current caller passes `timeout`, so the defect is latent, but the parameter as shipped is a trap.
**Fix:**
```python
executor = ThreadPoolExecutor(max_workers=1)
try:
    return executor.submit(asyncio.run, coro).result(timeout)
finally:
    executor.shutdown(wait=timeout is None, cancel_futures=True)
```
(or document that `timeout` cannot abandon a runaway coroutine and that the thread is leaked on timeout — a deliberate, stated trade-off either way).

### WR-02: Scripted-turn failures in the Claude driver hang `_drive` instead of failing

**File:** `runtime/ccf_runtime/orchestration/claude_agent/driver.py:166-174, 195-257`
**Issue:** `_ScriptedSessionTransport.write` launches each turn as a fire-and-forget task (`asyncio.ensure_future(self._turn(...))`) whose exceptions are never awaited or observed. If anything inside `_turn` raises — the permission-denied `RuntimeError` at line 212, a `KeyError` on an unexpected `mcp_response` shape at line 228, a JSON decode error — no `result` frame is ever put on `self._out`, so `client.receive_response()` in `_drive` (line 382) awaits forever. The failure mode of any scripted-protocol drift is an indefinite hang (in tests, a 30s-plus stall or CI timeout), not a raised error, and the underlying exception is silently discarded (surfacing at best as an unretrieved-task warning at GC).
**Fix:** Wrap `_turn`'s body in `try/except`, and on failure emit an `is_error: true` result frame (or put a sentinel that makes `read_messages` raise); alternatively attach `task.add_done_callback` that forwards the exception into `self._out` so `_drive` fails fast with the real cause.

### WR-03: mypy-silenced `outcome.execution_id` access can raise a raw `AttributeError`

**File:** `runtime/ccf_runtime/orchestration/langgraph/driver.py:119`
**Issue:** `key = (tenant, outcome.execution_id)  # type: ignore[attr-defined]` — `CCFContract` does not declare `execution_id`; the ignore suppresses exactly the check that would catch an engine outcome type lacking the field. If the engine ever returns a terminal/error outcome without `execution_id`, this fails as a bare `AttributeError` from driver internals — the same "untyped accident" class WR-03 (the phase task) just eliminated for `KeyError`. The ADK and Claude legs avoid this by closing over `execution_id` from the call arguments; the LangGraph leg is the odd one out.
**Fix:** Close over the known `execution_id` instead of reading it off the outcome:
```python
def _park(outcome: CCFContract, execution_id: str) -> _Position:
    self._outcomes[(tenant, execution_id)] = outcome
    ...
```
(`drive`/`gate` both already have `state["execution_id"]` in scope), removing the `type: ignore`.

### WR-04: `assert` used for control-flow typing in the LangGraph gate node

**File:** `runtime/ccf_runtime/orchestration/langgraph/driver.py:134`
**Issue:** `assert isinstance(suspended, WorkflowSuspended)` in production code: under `python -O` the assert is stripped and a non-suspended outcome reaching `gate` (state-channel desync, a resume raced with a fresh execute) proceeds to `suspended.gate` / `suspended.event_key` and fails as `AttributeError`. With asserts on, the failure is a bare `AssertionError` — neither is the typed driver-error hierarchy this phase introduced for exactly this class of condition.
**Fix:** Replace with an explicit check raising the typed hierarchy:
```python
if not isinstance(suspended, WorkflowSuspended):
    raise WorkflowDriverError(
        f"gate node reached with non-suspended outcome for {tenant!r}/"
        f"{state['execution_id']!r}"
    )
```

## Info

### IN-01: Loop-safety and typed-error conformance tests silently pass for legs without a probe

**File:** `tests/conformance/test_orchestration.py:488-490, 505-507`
**Issue:** `test_a_never_executed_segment_raises_the_same_typed_error_on_every_leg` and `test_the_introspection_seam_is_loop_safe` do `if leg.positions is None: return` — the in-sdk leg reports PASS while asserting nothing, indistinguishable in reports from a real pass.
**Fix:** `pytest.skip("in-sdk reference adapter holds no outcome store")` so the non-exercise is visible.

### IN-02: Unused unpacked variables in `_options`

**File:** `runtime/ccf_runtime/orchestration/claude_agent/driver.py:303`
**Issue:** `tenant, execution_id = key` — neither name is used in the method body (closures use `key` and tool args directly). Dead assignments.
**Fix:** Delete the line.

### IN-03: "Continuation of the same session" docstring overstates what resume does

**File:** `runtime/ccf_runtime/orchestration/claude_agent/driver.py:29-34, 408-414`
**Issue:** Module and method docstrings say a resume is "a continuation of the same session (the same `session_id`)", but `_drive` constructs a fresh `ClaudeSDKClient` and a fresh `_ScriptedSessionTransport` per call — only the `session_id` string is reused; no session state carries over. The behavior is fine (the engine holds state), but the doc claims more continuity than exists.
**Fix:** Reword to "the same session identity; each turn runs a fresh client over a fresh scripted transport."

### IN-04: Driver-side outcome/transcript maps grow unboundedly

**File:** `runtime/ccf_runtime/orchestration/adk/driver.py:169`, `claude_agent/driver.py:274-277`, `langgraph/driver.py:88`
**Issue:** `_outcomes` (and `_transcripts`) accumulate one entry per execution for the driver's lifetime with no eviction path. Acceptable for conformance-suite lifetimes; a long-lived composition root leaks. Worth a docstring note or a `forget(execution_id)` seam eventually.
**Fix:** Note the retention posture in the class docstrings, or add an explicit eviction method.

### IN-05: Import placement inconsistency in the conformance module

**File:** `tests/conformance/test_orchestration.py:47`
**Issue:** `from ccf_runtime.orchestration import SegmentNotExecutedError` is inserted between two `ccf.*` imports (lines 46 and 48), breaking the module's otherwise-grouped ordering; likewise `_pytest`/`conftest` imports at 56-57 sit after first-party imports.
**Fix:** Regroup per the project's import-sorting convention.

---

_Reviewed: 2026-08-01_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
