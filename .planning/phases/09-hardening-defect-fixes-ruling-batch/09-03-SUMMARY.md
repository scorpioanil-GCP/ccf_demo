---
phase: 09-hardening-defect-fixes-ruling-batch
plan: 03
subsystem: hitl
tags: [WR-02, thread-safety, threading.Lock, hammer-test, D-14, byte-identity]
requires: [09-01, 09-02]
provides:
  - "threading.Lock-synchronized InMemoryHitlTransport (WR-02, HARD-02)"
  - "HITLTransportProtocol concurrency contract in docstring (D-05/D-08)"
  - "always-on 24-thread mixed-op hammer test with deadlock detection (D-07/D-15)"
  - "phase-close D-14 byte-identity verification against the plan-01 manifest"
affects: [phase-10]
tech-stack:
  added: []
  patterns:
    - "minimal-scope plain Lock: queue mutations/snapshots only; Control Plane resolve + JWS verification outside the lock (D-IMPL-69)"
    - "seeded Barrier-started hammer with per-thread event_key namespaces for exactly-once accounting; bounded join + pytest.fail as deadlock verdict"
key-files:
  created:
    - tests/hitl/test_transport_concurrency.py
  modified:
    - src/ccf/hitl/transport.py
decisions:
  - "Concurrency contract cited as WR-02 + Phase-9 CONTEXT D-05/D-06/D-08 with D-IMPL-69 adjacency (WR-02, like WR-03, was ruling-free — no dedicated D-IMPL number exists; D-IMPL-69's 'JWS verification stays outside any transport lock' is the ruled adjacency)"
  - "Deadlock detection via bounded thread.join(timeout=30) + pytest.fail — no pytest-timeout dependency, per plan"
metrics:
  duration: "~20 min"
  tasks: 3
  files: 2
  completed: 2026-08-01
---

# Phase 9 Plan 03: WR-02 HITL Transport Thread Safety Summary

Plain `threading.Lock` synchronization on `InMemoryHitlTransport` with the
concurrency contract documented on `HITLTransportProtocol`, proven by an
always-on 24-thread mixed-op hammer, and the phase's D-14 byte-identity
guarantee closed — HARD-02 satisfied.

## What Was Done

1. **Task 1 (commit f270197).** `src/ccf/hitl/transport.py`: single
   `threading.Lock` created in `__init__`; `with self._lock:` wraps ONLY
   queue mutations and snapshot reads — `enqueue` (setdefault+append),
   `dequeue` (check-then-popleft as one scope, closing the race), `pending`
   and `submissions` (tuple snapshots under the lock), and `submit`'s final
   append. `_signed_binding_required()` (Control Plane `resolve_latest`) and
   `_enforce_signed_binding()` (JWS verification) stay OUTSIDE the lock per
   D-IMPL-69; a refused submission never touches the queues, so the D-16
   refusal contract is preserved trivially. No nested acquisition, no RLock
   (`grep -c "threading.Lock()"` = 1, `grep -c RLock` = 0). The
   `HITLTransportProtocol` docstring now states the contract: all methods of
   every conforming implementation must be safe for concurrent calls from
   multiple threads (the FastAPI-threadpool doors invoke it that way);
   docstring is the sole documentation surface (D-08), citing WR-02,
   Phase-9 CONTEXT D-05/D-06/D-08, D-IMPL-69, CLAUDE.md §8.2.
2. **Task 2 (commit b9bb42d).** `tests/hitl/test_transport_concurrency.py`
   (309 lines): main hammer — 24 threads (in the 16-32 envelope),
   `threading.Barrier` start, per-thread `random.Random(BASE_SEED + index)`,
   300 mixed ops each across 3 tenants against one unconfigured transport;
   per-thread event_key namespaces (`{tenant}/hammer/{thread}/{i}`) make
   exactly-once accounting by-construction checkable. Post-run invariants:
   no duplicated dequeues/pendings, dequeued ∪ still-pending == enqueued
   (counts and sets), submission totals match per-thread tallies,
   single-producer FIFO per tenant. Every `join(timeout=30)` bounded with
   `pytest.fail` on miss; no pytest-timeout (grep = 0). Second case: a
   D-16-wired transport (signed-binding-required policy, per the
   `test_signed_binding_authority.py` wiring pattern) hammered on the
   submit path — 8×25 verified submissions all recorded, no lock-ordering
   issue against the Control Plane/JWS path. Always-on, no markers (D-15).
   Runtime: ~0.25s.
3. **Task 3 (no file change — verification only).** Recomputed the identical
   plan-01 manifest command (`find examples -type f \( -name run.py -o
   -path '*/artifacts/*' \) | sort | xargs sha256sum`) and diffed against
   the committed `09-examples-hash-manifest.txt`: **diff empty —
   byte-identical (D-14 holds, no regeneration)**. `git diff --stat` against
   the phase-wave base for `examples/` is empty. Full `make ci` green.

## D-GATE-9 Numbers (phase gate record)

- **Byte-identity (D-14):** recomputed manifest diffs empty against the
  plan-01 baseline (57 files across all eight examples) — PASS.
- **`make ci`:** exit 0 — `tools.lints --all` green, `mypy --strict` clean
  over 157 source files, **1353 tests passed** (was 1351 after plan 02;
  +2 concurrency cases), all eight examples run OK end-to-end including
  the example-03 two-harness portability assertion.
- Ruling deferrals flagged by plan 01: **none** (all six batch items
  D-IMPL-68..73 RESOLVED; D-04 partial-proceed never invoked).

## Deviations from Plan

- **Concurrency-contract citation.** The plan's key_link asked for "the
  Phase 9 concurrency-contract D-IMPL number." As plan 02 established for
  WR-03, the audit's two ruling-free defects (WR-02 here) received no
  dedicated D-IMPL number; the docstrings cite WR-02 + Phase-9 CONTEXT
  D-05/D-06/D-08 with explicit D-IMPL-69 adjacency (whose ruling text
  itself mandates "JWS verification stays outside any transport lock").
  The `D-IMPL-` pattern link to docs/DECISIONS.md is satisfied. [Rule 3 —
  same self-consistent reading plan 02 recorded; no ruling invented.]
- **TDD sequencing on Task 2.** The plan orders implementation (Task 1)
  before the hammer (Task 2, tdd="true"), so a classical RED against the
  unlocked transport was impossible without unwinding Task 1. A
  RED-equivalent sanity check was run out-of-tree (null-lock monkeypatch,
  5 runs): under CPython's GIL the 300-op hammer does not reliably trigger
  the dict/deque races, so the unlocked variant also passed — the hammer's
  value is as an always-on structural regression guard (and it will bite
  under free-threaded Python or any future lock removal), not as a
  GIL-bound race reproducer. Nothing committed from the sanity check.
- **Environment note (same as plans 01/02):** the worktree lacks `.venv`;
  a temporary symlink to the main checkout's venv was used for make/pytest
  and removed before commit (`PYTHONPATH=src:runtime` ensures worktree
  code resolves first — verified via `ccf.__file__`).

## Known Stubs

None.

## Threat Flags

None new. T-09-07/08/09 all mitigated as planned (single Lock on
mutations/snapshots + hammer invariants; verification outside the lock +
bounded-join deadlock detection; D-16 refusal ordering unchanged — all
existing signed-binding tests green). T-09-SC accepted as planned (zero
new packages; stdlib threading only).

## Commits

- f270197 — fix(09-03): synchronize InMemoryHitlTransport with a plain threading.Lock
- b9bb42d — test(09-03): 24-thread mixed-op hammer for the locked HITL transport

## Self-Check: PASSED

- `src/ccf/hitl/transport.py` contains `threading.Lock()` (1) and no RLock (0)
- `tests/hitl/test_transport_concurrency.py` exists (309 lines ≥ 80)
- Commits f270197, b9bb42d present in git log
- `make ci` exit 0; manifest diff empty; `git status` clean before SUMMARY
