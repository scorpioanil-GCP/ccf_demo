---
phase: 09
slug: hardening-defect-fixes-ruling-batch
status: verified
threats_open: 0
asvs_level: 1
created: 2026-08-01
---

# Phase 9 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Decision authority | Rulings must originate from Dave, never fabricated by the executor | D-IMPL ruling entries |
| docs/ tree | Ruling document may not leak credentials or private-repo assumptions stated as fact | Repo-visibility assumptions |
| sync caller → driver coroutine | Untrusted execution context (may or may not host a loop) crosses into async driver internals | Coroutine dispatch |
| orchestration tree → harness SDKs | CINV-02 carve-out; shared common module must stay harness-import-free | None (stdlib only) |
| FastAPI threadpool → transport | Concurrent multi-thread access from HTTP/MCP HITL doors crosses into shared queue state | HITL submissions/resolutions |
| submit path → Control Plane / crypto | D-16 verification must not execute under the queue lock | Signed bindings |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-09-01 | Spoofing/Repudiation | docs/DECISIONS.md entries | mitigate | checkpoint:decision gate — D-IMPL-68..73 written only after Dave's interactive answers (commit 663f08a), each dated "Approver: Dave" | closed |
| T-09-02 | Information disclosure | docs-toolchain ruling item | mitigate | Pages private-repo visibility verified against GitHub docs before presenting; ruling is CI-artifact-only | closed |
| T-09-03 | Tampering | examples byte-identity | mitigate | Pre-phase sha256 manifest (118e070, 57 files) precedes all code commits; independently recomputed — byte-identical | closed |
| T-09-04 | DoS | AdkWorkflowDriver.persisted_state | mitigate | `run_coroutine_sync` loop-aware dispatch; zero `asyncio.run(` in the driver; live-loop parity test (test_orchestration.py:503) | closed |
| T-09-05 | Information disclosure | driver introspection errors | mitigate | Typed `SegmentNotExecutedError`/`DriverStateRetrievalError` on all three legs; messages carry tenant/execution_id only, underlying exception chained | closed |
| T-09-06 | DoS (deadlock) | run_coroutine_sync join | mitigate | Dedicated background thread with own loop (never joins caller's loop); timeout leg fixed in 2c3c8c8 — `shutdown(wait=False)` so `Future.result(timeout)` expiry unblocks the caller; timeout-path conformance test added | closed |
| T-09-SC-02 | Tampering | package installs (plan 02) | accept | Zero new packages — stdlib asyncio/concurrent.futures only | closed |
| T-09-07 | Tampering/Repudiation | InMemoryHitlTransport queues | mitigate | Single `threading.Lock()` (no RLock) on all mutations/snapshots; 24-thread hammer asserts exactly-once/FIFO invariants | closed |
| T-09-08 | DoS (deadlock) | lock + Control Plane path | mitigate | D-16 verification outside the lock; no nested acquisition; bounded-join deadlock detection in tests | closed |
| T-09-09 | Elevation of privilege | submit refusal path | mitigate | Verification precedes any queue append; refused submissions structurally cannot reach `_submissions` | closed |
| T-09-SC-03 | Tampering | package installs (plan 03) | accept | Zero new packages — stdlib threading only | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-09-01 | T-09-SC-02 | Plan 09-02 adds only stdlib modules (asyncio, concurrent.futures); no supply-chain surface | Dave (plan approval) | 2026-08-01 |
| AR-09-02 | T-09-SC-03 | Plan 09-03 adds only stdlib threading; no supply-chain surface | Dave (plan approval) | 2026-08-01 |
| AR-09-03 | T-09-06 (residual) | On timeout expiry the worker thread is abandoned, not killed — the hung coroutine runs to completion on its own thread. Caller is unblocked; residual is bounded thread leakage under a pathological hang | Dave (fix-now ruling) | 2026-08-01 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-01 | 11 | 10 | 1 | gsd-security-auditor (T-09-06 timeout leg absent in effect) |
| 2026-08-01 | 11 | 11 | 0 | orchestrator re-verification after fix 2c3c8c8 (dispatch tests 5/5, full suite 1354 passed) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter
