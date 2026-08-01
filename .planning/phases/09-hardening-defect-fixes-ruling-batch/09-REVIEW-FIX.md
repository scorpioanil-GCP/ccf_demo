---
phase: 09-hardening-defect-fixes-ruling-batch
fixed_at: 2026-08-01T00:00:00Z
review_path: .planning/phases/09-hardening-defect-fixes-ruling-batch/09-REVIEW.md
iteration: 1
findings_in_scope: 9
fixed: 9
skipped: 0
status: all_fixed
---

# Phase 9: Code Review Fix Report

**Fixed at:** 2026-08-01
**Source review:** .planning/phases/09-hardening-defect-fixes-ruling-batch/09-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 9 (4 Warning, 5 Info — `--all`)
- Fixed: 9 (one already resolved by the orchestrator)
- Skipped: 0

**Verification after every fix and at the end:** full suite `make test`
(1352 passed + 2 now-visible skips = 1354), `make lint` (CINV lints)
clean, `make typecheck` (mypy --strict, 157 files) clean, conformance
runs under `CCF_REQUIRE_HARNESSES=1`.

## Fixed Issues

### WR-01: `run_coroutine_sync(timeout=...)` does not bound the wait it documents

**Files modified:** none (already resolved)
**Commit:** 2c3c8c8 (orchestrator, prior to this run)
**Applied fix:** already resolved (2c3c8c8) — verified: `common.py` now
avoids the context manager, uses `executor.shutdown(wait=False)` in a
`finally`, and the docstring states the abandoned-worker trade-off; a
timeout-path conformance test accompanies it.

### WR-02: Scripted-turn failures in the Claude driver hang `_drive` instead of failing

**Files modified:** `runtime/ccf_runtime/orchestration/claude_agent/driver.py`
**Commit:** 760b0f9
**Applied fix:** turns now launch through `_guarded_turn`, which wraps
`_turn` in try/except and, on any exception, emits an `is_error: true`
result frame carrying `TypeName: message`; `_drive` raises it as a typed
`WorkflowDriverError` — scripted-protocol drift fails fast with the real
cause instead of hanging `receive_response` forever.

### WR-03: mypy-silenced `outcome.execution_id` access can raise a raw `AttributeError`

**Files modified:** `runtime/ccf_runtime/orchestration/langgraph/driver.py`
**Commit:** 37ab623 (shared with WR-04 — same file, adjacent hunks)
**Applied fix:** `_park` now takes the known `execution_id` from
`state["execution_id"]` at both call sites, matching the ADK and Claude
legs; the `# type: ignore[attr-defined]` is removed.

### WR-04: `assert` used for control-flow typing in the LangGraph gate node

**Files modified:** `runtime/ccf_runtime/orchestration/langgraph/driver.py`
**Commit:** 37ab623 (shared with WR-03)
**Applied fix:** replaced `assert isinstance(suspended, WorkflowSuspended)`
with an explicit check raising `WorkflowDriverError` naming
tenant/execution_id — safe under `python -O`, typed per the phase's
driver-error hierarchy.

### IN-01: Loop-safety and typed-error conformance tests silently pass for legs without a probe

**Files modified:** `tests/conformance/test_orchestration.py`
**Commit:** e5f53ca
**Applied fix:** `return` → `pytest.skip("in-sdk reference adapter holds
no outcome store")` in both tests; the suite now reports 2 skips for the
in-sdk leg instead of silent passes.

### IN-02: Unused unpacked variables in `_options`

**Files modified:** `runtime/ccf_runtime/orchestration/claude_agent/driver.py`
**Commit:** e719882
**Applied fix:** deleted the dead `tenant, execution_id = key` line.

### IN-03: "Continuation of the same session" docstring overstates what resume does

**Files modified:** `runtime/ccf_runtime/orchestration/claude_agent/driver.py`
**Commit:** ba6ffa8
**Applied fix:** module and `resume_execution` docstrings reworded to
"same session identity (the same `session_id`); each turn runs a fresh
client over a fresh scripted transport; continuity lives in the engine."

### IN-04: Driver-side outcome/transcript maps grow unboundedly

**Files modified:** `runtime/ccf_runtime/orchestration/adk/driver.py`,
`runtime/ccf_runtime/orchestration/claude_agent/driver.py`,
`runtime/ccf_runtime/orchestration/langgraph/driver.py`
**Commit:** 19c0c4b
**Applied fix:** documented retention posture on the `_outcomes` (and
`_transcripts`) attribute doc comments of all three legs — lifetime of
the driver instance, no eviction, sized for conformance-suite and
per-composition lifetimes. Chose the review's documented-note option;
no config values or thresholds added (No-Hardcoding Rule).

### IN-05: Import placement inconsistency in the conformance module

**Files modified:** `tests/conformance/test_orchestration.py`
**Commit:** 1d975ec
**Applied fix:** `_pytest.outcomes` moved into the third-party block;
`ccf_runtime.orchestration` import moved into sorted position within the
first-party block; `conftest` import last in that block.

---

_Fixed: 2026-08-01_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
