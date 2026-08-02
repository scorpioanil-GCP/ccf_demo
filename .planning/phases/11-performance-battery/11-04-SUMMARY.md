---
phase: 11-performance-battery
plan: 04
subsystem: perf
tags: [cross-process, mcp-egress, peering, replay-at-scale, curve-fit]
requires: [11-01, 11-02]
provides:
  - perf/suites/crossproc (MCP egress + A2A/peering round-trip benchmarks over a real localhost subprocess)
  - perf/suites/replay (1k/10k/100k decision-history ladder, byte-exact + curve-shape asserts)
  - perf/results/replay.curve.json fitted-exponent artifact for Phase 14 PERFORMANCE.md
affects: [11-05, phase-14]
tech-stack:
  added: []
  patterns:
    - READY-handshake session subprocess fixture with per-transport warm-up (D-15)
    - log-log least-squares curve-shape assert as the primary scale guard (D-16/D-21)
key-files:
  created:
    - perf/suites/crossproc/__init__.py
    - perf/suites/crossproc/conftest.py
    - perf/suites/crossproc/test_mcp_egress.py
    - perf/suites/crossproc/test_peering.py
    - perf/suites/replay/__init__.py
    - perf/suites/replay/conftest.py
    - perf/suites/replay/test_replay_scale.py
  modified:
    - perf/synth/artifacts/controlplane.yaml
decisions:
  - "Child-spawn approach: reuse examples/04-cross-process/producer_child.py directly (property-intelligence example artifacts, not banking) — no perf-local child copy"
  - "100k-decision rung sourced from decision_stream(100_000) (10k base records) with deterministic replica-index replication (D-07 flex; decision_stream(1_000_000) topology takes >5 minutes)"
  - "History-store population uses an O(n) bulk writer producing FileArtifactStore's exact on-disk format, because put()'s per-call naming-index rewrite is O(n²) across 100k records; the TIMED path uses only the public store surface"
metrics:
  duration: "~55 min"
  completed: "2026-08-01"
---

# Phase 11 Plan 04: Cross-Process + Replay-at-Scale Suites Summary

Real-subprocess cross-process latency benchmarks (MCP egress + A2A/peering
over 127.0.0.1, startup excluded) and the replay ladder with per-rung
byte-exact reproduction plus a fitted growth exponent **b = 0.0013** —
empirical support for the year-scale replay claim (PERF-03).

## Measured results

**Cross-process (rounds=50, warm-up 5 + 10 fixture warm-ups per transport):**

| Benchmark | Median |
| --- | --- |
| `test_mcp_egress_roundtrip` | 17.24 ms |
| `test_peering_roundtrip` | 0.62 ms |

Suite wall time: **2.3 s** (budget ≤ ~2.5 min). gate.py: exit 0, report-only
(no baseline, D-13).

**Replay ladder (rounds=3, warmup 1, session-populated stores):**

| History records | Replay median |
| --- | --- |
| 1,000 | 555.4 ms |
| 10,000 | 556.2 ms |
| 100,000 | 558.8 ms |

Fitted `t = a * n^b`: **b = 0.00132** (a = 0.550 s), asserted
`b <= 1.0 + EPS` with `EPS = 0.1`; exponent + medians written to
`perf/results/replay.curve.json`. Byte-exact reproduction asserted per rung
via the canonical serializer BEFORE any timing (T-11-11). Suite wall time:
**66 s** (budget ≤ ~3.5 min). Always-on `pytest tests/ -q`: 1475 passed,
2 skipped.

## Child-spawn approach (recorded per plan output spec)

Reused example 04's `producer_child.py` unmodified: it is the canonical
server child (real `/runtime` MCP egress server + `TypedHttpWire` A2A
endpoint, ephemeral 127.0.0.1 ports, `READY {mcp_port} {a2a_port}`
announce), and its artifacts are property-intelligence values authored fresh
for that example — no banking artifacts dragged in, so the plan's
perf-local-child alternative was unnecessary. Fixture: session-scoped,
blocking-readline handshake (no sleeps), stderr captured for diagnosis,
process-group SIGTERM→wait(10s)→SIGKILL in `finally`.

## Rung flex (D-07, per plan instruction to record)

The ladder counts are exactly 1k/10k/100k **decision records**, but
`decision_stream` sizes its output at rung/10, so 100k records would need
the 1M-entity topology — measured at **>300 s** to generate (the weighted
hub-attachment edge fill), which blows the D-25 budget outright. Flex:
base records come from `decision_stream(100_000)` (10,000 records, ~6 s);
the 100k rung replicates them with a deterministic `-r{k}` replica suffix.
Every record still references a real generated entity URI (D-30).

## Deviations from Plan

**1. [Rule 3 - Blocking] Worktree had no `.venv`**
- Symlinked the main repo's `.venv` (same resolution as wave 1, 11-01).

**2. [Rule 3 - Blocking] `serve()` requires a `ServableProduct`**
- The plan's "serve the record" step used `ccf.replay.serve.serve`, which
  couples record-append to product delivery. The suite appends the record
  via the public `ReplayWriter.write_replay_record` directly (the same
  store path `serve` uses) — no product delivery is being benchmarked.

**3. [Rule 3 - Blocking] O(n²) history population through `FileArtifactStore.put`**
- `put()` rewrites the whole naming index per call; 100k puts is quadratic
  (hundreds of GB of index rewrites). Fix: `_bulk_write` in
  `perf/suites/replay/conftest.py` lays records down in the store's exact
  on-disk format (canonical bytes at content-hash filename,
  temp-write + rename) without index entries — history records are
  resolved by content address only. The timed replay path touches only the
  public store surface. Documented in the module docstring.

**4. [Rule 2 - Missing config] `artifacts:` block added to
`perf/synth/artifacts/controlplane.yaml`**
- The replay suite needs artifact-class names for the store; per the
  No-Hardcoding discipline they were added to the perf Control Plane
  artifact rather than held as code constants.

## Verification evidence

- `make perf-xproc` pipeline (pytest + gate.py) exit 0; raw JSON has 2
  benchmarks × 50 timings each in `stats.data`
- Grep gates: `READY` in crossproc conftest = 3; `sleep(` = 0; `kill` = 3;
  `0.0.0.0` anywhere in the suite = 0; warm-up loops source-visible
- Replay: byte-exact `canonical_bytes` equality assert per rung; curve test
  asserts `b <= 1.1`; exponent artifact present under `perf/results/`
- Timed replay excludes population (session-cached stores; source-visible)
- `pytest tests/ -q`: 1475 passed, 2 skipped (always-on unaffected)

## Known Stubs

None.

## Threat Flags

None — T-11-09 (127.0.0.1-only, source-asserted), T-11-10 (process-group
terminate→wait→kill in finally), T-11-11 (byte-exact assert precedes
timing; exponent computed from the same medians gate.py reports) all
implemented per the plan's threat register.

## Commits

| Task | Commit | Description |
| --- | --- | --- |
| 1 | b26abab | crossproc suite: fixture + MCP egress + peering benchmarks |
| 2 | db7a10c | replay ladder: byte-exact + curve-shape + exponent artifact |

## Self-Check: PASSED

All 7 created files + `perf/results/replay.curve.json` exist; commits
b26abab and db7a10c present in log; both suites + gate.py exit 0
report-only; full always-on suite green; working tree clean.
