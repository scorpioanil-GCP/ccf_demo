---
phase: 09-hardening-defect-fixes-ruling-batch
plan: 02
subsystem: orchestration
tags: [WR-03, loop-safety, typed-errors, drivers, conformance]
requires: [09-01]
provides:
  - "run_coroutine_sync loop-aware dispatch helper (Phase-9 CONTEXT D-09)"
  - "WorkflowDriverError / SegmentNotExecutedError / DriverStateRetrievalError hierarchy (D-10)"
  - "all three drivers on the shared pattern (D-11/D-12)"
  - "cross-adapter typed-error and loop-safety parity tests, always-on (D-13/D-15)"
affects: [phase-10, phase-13]
tech-stack:
  added: []
  patterns:
    - "loop-aware sync dispatch: get_running_loop probe -> asyncio.run, or single-use background thread + Future.result"
    - "uniform per-driver _outcome guarded lookup, parity-asserted across legs"
key-files:
  created:
    - runtime/ccf_runtime/orchestration/common.py
    - tests/conformance/test_driver_dispatch.py
  modified:
    - runtime/ccf_runtime/orchestration/__init__.py
    - runtime/ccf_runtime/orchestration/adk/driver.py
    - runtime/ccf_runtime/orchestration/langgraph/driver.py
    - runtime/ccf_runtime/orchestration/claude_agent/driver.py
    - tests/conformance/test_orchestration.py
decisions:
  - "Docstrings cite Phase-9 CONTEXT D-09..D-12 (WR-03 was ruling-free; plan 01's D-IMPL-68..73 cover other items — see deviations)"
  - "Uniform private _outcome helper on all three drivers as the D-13(b) parity surface (no public-signature change)"
metrics:
  duration: "~25 min"
  tasks: 3
  files: 7
  completed: 2026-08-01
---

# Phase 9 Plan 02: WR-03 Driver Loop-Safety & Typed Errors Summary

Shared loop-aware dispatch (`run_coroutine_sync`) plus a typed
`WorkflowDriverError` hierarchy under `runtime/ccf_runtime/orchestration/common.py`,
applied to all three OrchestrationProtocol drivers, with always-on
cross-adapter parity tests — HARD-03 satisfied.

## What Was Done

1. **Task 1 (TDD, commits 2463d37 test / 07bcc70 feat).**
   `runtime/ccf_runtime/orchestration/common.py`: `run_coroutine_sync(coro, *,
   timeout=None)` — `asyncio.get_running_loop()` probe; no loop →
   `asyncio.run`; running loop → single-use `ThreadPoolExecutor(max_workers=1)`
   submitting `asyncio.run`, joined via `Future.result(timeout)` (never
   touches the caller's loop; no `nest_asyncio`/`run_until_complete`/
   `run_coroutine_threadsafe`, grep-verified 0). Error hierarchy:
   `WorkflowDriverError(RuntimeError)` base, `SegmentNotExecutedError` (no
   KeyError co-subclass — clean break, verified safe) and
   `DriverStateRetrievalError`. `__ccf_mode__ = "algorithmic"`, stdlib-only
   imports, re-exported from `ccf_runtime.orchestration.__init__`. Unit
   tests in `tests/conformance/test_driver_dispatch.py` (4 cases incl.
   inside-asyncio.run dispatch on a distinct thread).
2. **Task 2 (commit f28f498).** ADK `persisted_state` now dispatches via
   `run_coroutine_sync` (no `asyncio.run(` remains in the file, grep 0),
   wraps substrate failures in `DriverStateRetrievalError` (chained), and
   preserves the `session is None -> ()` contract. Every bare
   `_outcomes[...]` lookup across ADK/LangGraph/Claude-Agent drivers raises
   `SegmentNotExecutedError` naming tenant and execution_id. Module
   docstrings carry the WR-03 loop-safety note. No other sync-entry
   `asyncio.run` existed in any driver (audited — all other dispatch is
   already async).
3. **Task 3 (TDD, commits aa9c565 test / edb7065 refactor).** Two new
   parametrized conformance tests over the existing leg/World fixtures:
   D-13(b) — never-executed lookup raises the identical
   `SegmentNotExecutedError` on every driver leg; D-13(c) — each leg's
   introspection probe (persisted_state / checkpointed_values /
   session_transcript) succeeds from plain sync AND from inside
   `asyncio.run`-hosted code with equivalent results (exercises RESEARCH A1:
   ADK InMemorySessionService cross-loop reads — confirmed working). D-13(a)
   equivalence stays covered by the existing
   `test_the_replay_record_is_equivalent_to_the_reference_legs` (extended
   nothing, per plan: no duplication). GREEN required giving ADK and
   Claude-Agent the same private `_outcome` helper LangGraph got in Task 2 —
   uniform pattern, no public method signature changed. Tests are always-on
   (no markers, D-15) and respect `CCF_REQUIRE_HARNESSES`.

## Verification

- `CCF_REQUIRE_HARNESSES=1 pytest tests/conformance/test_orchestration.py
  tests/conformance/test_driver_dispatch.py -q` — 37 passed
- `make ci-core` — lint (`tools.lints --all` incl. d06-orchestration-split
  and harness-import lints), `mypy --strict` (157 files), full test suite:
  1351 passed
- `make examples` — exit 0; D-14 manifest spot-check: `sha256sum -c` against
  `09-examples-hash-manifest.txt` — zero non-OK lines (byte-identical)

## Deviations from Plan

- **Docstring citations (plan Task 1 read_first said "cite the Phase 9
  D-IMPL numbers assigned in plan 01").** Plan 01's assigned numbers
  (D-IMPL-68..73) cover the six ruling-batch items, none of which is WR-03 —
  WR-03 was one of the audit's two *ruling-free* defects and received no
  D-IMPL number. The new docstrings therefore cite "SDK-defined (CLAUDE.md
  §8.1; Phase-9 CONTEXT D-09..D-12, WR-03)", matching how D-IMPL-72 itself
  refers to "Phase 9's CONTEXT D-10 (the WR-03 error-hierarchy decision)".
  [Rule 3 — blocking ambiguity resolved with the only self-consistent
  reading; no ruling invented.]
- **Environment note (same as plan 01):** the worktree lacks `.venv`; a
  temporary symlink to the main checkout's venv was used for
  make/pytest runs and removed before the final commit (PYTHONPATH=src:runtime
  ensures worktree code resolves first — verified via `ccf.__file__`).

## Known Stubs

None.

## Threat Flags

None — T-09-04/05/06 all mitigated as planned (loop-aware dispatch, typed
controlled-message errors, background-thread join with optional timeout);
T-09-SC accepted as planned (zero new packages, stdlib only).

## Commits

- 2463d37 — test(09-02): add failing tests for run_coroutine_sync and driver-error hierarchy
- 07bcc70 — feat(09-02): shared loop-aware dispatch helper and driver-error hierarchy
- f28f498 — fix(09-02): apply loop-aware dispatch and typed errors to all three drivers
- aa9c565 — test(09-02): add cross-adapter typed-error and loop-safety parity cases
- edb7065 — refactor(09-02): uniform _outcome lookup helper on all three drivers

## TDD Gate Compliance

Both TDD tasks show the RED→GREEN commit sequence in git log (test commits
2463d37 and aa9c565 each precede their implementing commits 07bcc70 and
edb7065; RED runs were observed failing before each implementation).

## Self-Check: PASSED

- `runtime/ccf_runtime/orchestration/common.py`,
  `tests/conformance/test_driver_dispatch.py` exist on disk
- Commits 2463d37, 07bcc70, f28f498, aa9c565, edb7065 present in git log
- `grep -c asyncio.run runtime/ccf_runtime/orchestration/adk/driver.py` = 0;
  SegmentNotExecutedError count in test_orchestration.py = 3 (>= 2)
