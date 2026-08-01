---
phase: 09-hardening-defect-fixes-ruling-batch
verified: 2026-08-01T18:20:00Z
status: passed
score: 9/9 must-haves verified
overrides_applied: 0
re_verification: false
---

# Phase 9: Hardening — Defect Fixes & Ruling Batch Verification Report

**Phase Goal:** Thread-safe HITL transports, loop-safe ADK driver, and the six-item D-IMPL ruling batch surfaced to Dave as one mini-cycle. No gated item implemented before its ruling — implement per rulings only, never defaults.
**Verified:** 2026-08-01
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 (09-01) | Consolidated mini-cycle document covers all six ruling items with options + recommendations | ✓ VERIFIED | `docs/09-ruling-batch-minicycle.md` — 364 lines (min 120), 7 "recommendation" hits, six item sections |
| 2 (09-01) | Dave ruled each item; every ruling logged in DECISIONS.md house format | ✓ VERIFIED | D-IMPL-68..73 all present in `docs/DECISIONS.md` (grep count 6), 78 "Approver: Dave" entries file-wide; zero deferrals per SUMMARY |
| 3 (09-01) | Pre-change sha256 manifest of all eight example dirs exists before code plans | ✓ VERIFIED | `09-examples-hash-manifest.txt` — 57 lines, each of examples/00- through 07- covered; commit 118e070 precedes code commits |
| 4 (09-02) | Sync introspection from inside a running loop returns state, no RuntimeError | ✓ VERIFIED | `run_coroutine_sync` in `common.py` (get_running_loop probe → asyncio.run or single-use ThreadPoolExecutor); `test_the_introspection_seam_is_loop_safe` at test_orchestration.py:499 passes under CCF_REQUIRE_HARNESSES=1 |
| 5 (09-02) | Never-executed segment raises SegmentNotExecutedError (identical type, all three drivers), not bare KeyError | ✓ VERIFIED | Uniform `_outcome` helper with `except KeyError: raise SegmentNotExecutedError ... from None` in ADK:171, LangGraph:98, Claude-Agent:288; `test_a_never_executed_segment_raises_the_same_typed_error_on_every_leg` at :480 passes |
| 6 (09-02) | State-retrieval failures surface as typed DriverStateRetrievalError; parity tests always-on | ✓ VERIFIED | `DriverStateRetrievalError(WorkflowDriverError)` in common.py; ADK persisted_state chains it; parity tests carry no markers; `CCF_REQUIRE_HARNESSES=1 pytest tests/conformance/test_orchestration.py` — 33 passed |
| 7 (09-03) | InMemoryHitlTransport survives 16-32-thread mixed-op hammer, no lost/dup events, no deadlock, plain Lock | ✓ VERIFIED | `threading.Lock()` count 1, RLock count 0 in transport.py; `tests/hitl/test_transport_concurrency.py` (309 lines, Barrier + join(timeout) + pytest.fail) — passes in 0.27s; full tests/hitl 112 passed |
| 8 (09-03) | HITLTransportProtocol docstring states the thread-safety contract as sole doc surface | ✓ VERIFIED | Protocol docstring "Concurrency contract (WR-02; D-IMPL-69 adjacency; CLAUDE.md §8.2)... safe for concurrent calls from multiple threads... sole documentation surface" — read directly |
| 9 (09-03) | Eight-example sweep byte-identical against plan-01 manifest, no regeneration | ✓ VERIFIED | Manifest recomputed independently by verifier (same find/sort/sha256sum command): diff empty — BYTE-IDENTICAL |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `docs/09-ruling-batch-minicycle.md` | Six-item ruling doc, min 120 lines | ✓ VERIFIED | 364 lines |
| `docs/DECISIONS.md` | D-IMPL-68+ entries | ✓ VERIFIED | D-IMPL-68..73 each present, Approver: Dave |
| `09-examples-hash-manifest.txt` | Pre-phase sha256 manifest | ✓ VERIFIED | 57 files, all eight example dirs |
| `runtime/ccf_runtime/orchestration/common.py` | Dispatch helper + error hierarchy, four exports | ✓ VERIFIED | Import check passed: `run_coroutine_sync`, `WorkflowDriverError`, `SegmentNotExecutedError`, `DriverStateRetrievalError`; `__ccf_mode__ = "algorithmic"`; no nest_asyncio/run_until_complete/run_coroutine_threadsafe (grep 0) |
| `runtime/ccf_runtime/orchestration/adk/driver.py` | persisted_state without direct asyncio.run; typed errors | ✓ VERIFIED | `asyncio.run(` count 0; `run_coroutine_sync` count 4; SegmentNotExecutedError count 4 |
| `tests/conformance/test_orchestration.py` | Per-leg typed-error and loop-safety parity cases | ✓ VERIFIED | Contains SegmentNotExecutedError (3), `pytest.raises(SegmentNotExecutedError` (1); tests at lines 480, 499 |
| `src/ccf/hitl/transport.py` | threading.Lock-synchronized transport + Protocol contract | ✓ VERIFIED | `threading.Lock()` = 1, no RLock; D-IMPL- citation count 22 |
| `tests/hitl/test_transport_concurrency.py` | Mixed-op hammer, min 80 lines | ✓ VERIFIED | 309 lines; Barrier/join(timeout/pytest.fail present (grep 5) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| minicycle doc | DECISIONS.md | D-IMPL-6[89]/7x entries | ✓ WIRED | 6 matching entries |
| adk/driver.py | common.py | run_coroutine_sync replacing asyncio.run | ✓ WIRED | 4 call sites, 0 asyncio.run |
| langgraph/driver.py | common.py | SegmentNotExecutedError on _outcomes | ✓ WIRED | guarded try/except at line 98 |
| test_orchestration.py | common.py | pytest.raises(SegmentNotExecutedError | ✓ WIRED | parametrized across all driver legs |
| test_transport_concurrency.py | transport.py | InMemoryHitlTransport hammer | ✓ WIRED | 4 references, both unconfigured and D-16-wired cases |
| transport.py | DECISIONS.md | D-IMPL- docstring citation | ✓ WIRED | D-IMPL-69 adjacency cited (WR-02 was ruling-free; deviation documented in SUMMARY, self-consistent) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Public exports importable, no KeyError co-subclass | `python -c "from ccf_runtime.orchestration import ..."` | imports OK | ✓ PASS |
| Hammer + dispatch tests | `pytest tests/hitl/test_transport_concurrency.py tests/conformance/test_driver_dispatch.py -q` | 6 passed, 0.27s | ✓ PASS |
| Full HITL + orchestration suites | `pytest tests/conformance/test_orchestration.py tests/hitl -q` | 112 passed | ✓ PASS |
| Harness legs required | `CCF_REQUIRE_HARNESSES=1 pytest tests/conformance/test_orchestration.py -q` | 33 passed | ✓ PASS |
| D-14 byte identity (independent recompute) | find/sort/sha256sum + diff vs baseline | diff empty | ✓ PASS |
| Submit lock ordering | source read | verification calls precede `with self._lock:` in submit | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| HARD-01 | 09-01 | Six-item ruling batch surfaced as one mini-cycle, rulings logged | ✓ SATISFIED | Truths 1-3; D-IMPL-68..73 |
| HARD-02 | 09-03 | Thread-safe in-memory HITL transport, documented contract, stress test | ✓ SATISFIED | Truths 7-8 |
| HARD-03 | 09-02 | Loop-safe ADK driver, typed errors, cross-adapter parity tests | ✓ SATISFIED | Truths 4-6 |

No orphaned requirements: HARD-04/HARD-05 map to Phase 10 per REQUIREMENTS.md and depend on the D-IMPL-68/69/73 rulings this phase produced (rulings-first ordering held — ruling commit 663f08a precedes all code commits).

### Anti-Patterns Found

None. No TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER markers in any modified file. No stub patterns; all guarded `_outcomes` subscripts sit inside try/except-raise constructs or are writes.

### Human Verification Required

None. The one inherently human element — Dave's rulings — is a checkpoint:decision gate already executed and evidenced in `docs/DECISIONS.md` (six entries dated 2026-08-01, Approver: Dave), which is the audit surface the plan defines.

### Notes for D-GATE-9 (advisory, carried from SUMMARYs)

- Branching-strategy divergence (config `branching_strategy: none` vs CLAUDE.md §2.2 phase branches) needs Dave's disposition at the gate — surfaced, not defaulted.
- Mixed model mandate (Fable 5 for 09-01, Opus for 09-02/03) was deliberate; record at gate.
- Hammer test is a structural regression guard, not a GIL-bound race reproducer (documented deviation in 09-03 SUMMARY) — honest and acceptable.

### Gaps Summary

No gaps. Phase goal achieved: rulings landed first and were never defaulted (six RESOLVED, zero fabricated, zero deferrals); WR-03 and WR-02 fixed with shared mechanism and always-on tests; examples byte-identical per D-14, independently reverified.

---

_Verified: 2026-08-01_
_Verifier: Claude (gsd-verifier)_
