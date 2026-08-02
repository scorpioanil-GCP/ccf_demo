---
phase: 11-performance-battery
plan: 03
subsystem: perf
tags: [pytest-benchmark, micro-benchmarks, scale-curves, pedantic]
requires: [11-01, 11-02]
provides:
  - perf/suites/micro — 13 benchmarks (operators, composed/sequential pair, factories, gates, run_coroutine_sync)
  - perf/suites/scale — assembly + projection curves over the flexed (500, 1000) ladder
  - perf/suites/common.py — artifact-driven operator-registry builder + PerfPlan
  - neutral agent/prompt/task/workflow fixture artifacts under perf/synth/artifacts/
  - perf/conftest.boot_fabric (boot-only path for pedantic setup callables)
affects: [11-04, 11-05, phase-14]
tech-stack:
  added: []
  patterns:
    - pedantic-setup-fresh-graph (assembly rounds boot a new fabric outside the clock)
    - category-based operator lookup (no operator-key literals in tests)
key-files:
  created:
    - perf/suites/__init__.py
    - perf/suites/common.py
    - perf/suites/micro/__init__.py
    - perf/suites/micro/conftest.py
    - perf/suites/micro/test_operators.py
    - perf/suites/micro/test_factory.py
    - perf/suites/micro/test_gates.py
    - perf/suites/micro/test_dispatch.py
    - perf/suites/scale/__init__.py
    - perf/suites/scale/conftest.py
    - perf/suites/scale/test_assembly.py
    - perf/suites/scale/test_projection.py
    - perf/synth/artifacts/agent.yaml
    - perf/synth/artifacts/prompt.yaml
    - perf/synth/artifacts/task.yaml
    - perf/synth/artifacts/workflow.yaml
  modified:
    - perf/conftest.py
decisions:
  - "D-07 rung flex: scale ladder is (500, 1000) — ingestion is ~5 ms/envelope so 10k is ~7 min/round; rungs below ~400 hang the generator's unique-edge sampler (hub_count x tail_count < 3 x rung)"
  - "Assembly rounds per rung {500: 3, 1000: 2}, warmup 0 (a warmup round at 1k costs ~42 s and blows the D-25 budget); projection rounds 3 + 1 warmup"
  - "D-24 pair: B=policy, A=similarity (canonical adjacency); composed leg is one engine execution and therefore includes the engine's as_of read + planning overhead"
metrics:
  duration: "~75 min"
  completed: "2026-08-01"
  tasks: 2
---

# Phase 11 Plan 03: Micro + Fabric-Scale Suites Summary

13 micro-benchmarks (PERF-01, D-23/D-24/D-05) and assembly + projection
scale curves (PERF-02, D-26) over a D-07-flexed (500, 1000) ladder, all
reporting through the single gate.py pipeline in report-only mode.

## Benchmark inventory (13 micro + 4 scale)

Micro (`perf/suites/micro`, auto-calibrated, medians from this run):
- `test_policy_operator` 682 µs, `test_similarity_operator` 465 µs,
  `test_temporal_operator` 2.25 ms, `test_traversal_operator` 1.51 ms
- `test_composed_chain` (four-category engine execution, 1k fabric) 362 ms
- `test_composed_ab` 227 ms vs `test_sequential_ab` 1.17 ms (D-24, below)
- `test_agent_factory_construct` 117 µs, `test_task_factory_construct` 65 µs
- `test_gate_empty_operator_guard` 0.8 µs, `test_gate_lineage_strict_equality`
  1.8 µs, `test_gate_ttl_bounds` 4.6 µs
- `test_run_coroutine_sync_overhead` 29.4 µs (D-05; optimization deferred)

Scale (`perf/suites/scale`, pedantic, explicit rounds):
- `test_assembly_scale[500]` 17.6 s / `[1000]` 46.4 s (fresh graph per
  round via setup callable; only the `handle.worker.ingest` loop timed)
- `test_projection_scale[500]` 151 ms / `[1000]` 371 ms (read-only over
  session-scoped fabrics)

Medians are monotonically increasing with rung size for both families.

## Suite wall times vs D-25 budget

- Micro: **56 s** (includes the ~40 s session 1k fabric build) — within
  the 2-minute budget.
- Scale: **207 s (3.44 min)** — within the plan's ≤3.5-minute acceptance
  ceiling, over the 3-minute target; the 1k assembly rung at 2 rounds is
  the dominant cost. Recorded for 11-05's perf/README.md budget notes.

## Chosen top rung and ladder (D-07 flex — for perf/README.md in 11-05)

- **Top rung: 1,000** (down from the pinned 100k). Measured basis: L2
  ingestion ≈ 5 ms/envelope on the reference SQLite path (1k rung =
  8,090 envelopes ≈ 42 s), so 10k ≈ 7 min/round and 100k is >1 hour.
- **Bottom rung: 500, not a lower decade.** The generator requires
  `hub_count × tail_count ≥ 3 × rung` unique (hub, tail) pairs (each pair
  admits exactly one relationship type) with hubs at 1% of entities;
  below ~400 entities the unique-edge sampler cannot terminate (rung 100:
  198 possible edges vs a 300-edge target — infinite loop). 500 gives
  2,475 possible vs 1,500 target.
- Rung values are baseline keys (Pitfall 6): `test_assembly_scale[500]`
  etc. must stay stable or be re-baselined.

## Composed-vs-sequential observation (D-24, for Phase 14)

`test_composed_ab` median **227 ms** vs `test_sequential_ab` median
**1.17 ms**. The gap is not composition cost: the composed leg is one full
`ProjectionEngine.execute`, which includes the engine's `reader.as_of`
graph-view read (~225 ms at 1k) and plan build, while the sequential leg
applies the two already-constructed operators to an already-materialized
view. Phase 14's PERFORMANCE.md should read the pair as "engine dispatch
overhead ≈ composed − sequential − view-read", not as composition being
slower than sequential application — the operator work itself is the
~1 ms visible in the sequential leg.

## Deviations from Plan

**1. [Rule 2 - Missing critical] Neutral factory fixture artifacts added**
- **Found during:** Task 1 (factory benchmarks)
- **Issue:** the factory construction paths need agent/prompt/task/workflow
  definition artifacts; none existed in the perf tree and inlining
  definitions in code violates the No-Hardcoding Rule (§6.4)
- **Fix:** added `perf/synth/artifacts/{agent,prompt,task,workflow}.yaml`
  with neutral perf vocabulary, mirroring the example artifact shapes
- **Commit:** 95fe14a

**2. [Rule 3 - Blocking] `perf/conftest.py` refactor: `boot_fabric` extracted**
- **Found during:** Task 2 (assembly setup callable)
- **Issue:** `build_fabric` boots *and* ingests; the assembly curve must
  boot a fresh graph in the pedantic setup while timing only ingestion
- **Fix:** extracted `boot_fabric(database_path=...)`; `build_fabric` now
  calls it then ingests. Always-on suite re-run green (1475 passed).
- **Commit:** 8702108

**3. [Rule 3 - Blocking] Scale ladder flexed to (500, 1000), assembly rounds {3, 2}, no assembly warmup**
- **Found during:** Task 2 (first scale run timed out)
- **Issue:** plan anticipated flexing only the 100k rung; measurement
  showed 10k also infeasible, and sub-400 rungs hang the generator
  (unique-edge sampler capacity)
- **Fix:** ladder (500, 1000) per D-07; per-rung assembly rounds
  {500: 3, 1000: 2} and warmup_rounds=0 for assembly (a 1k warmup adds
  ~42 s and breaks the budget); projection keeps rounds=3 + warmup 1
- **Commit:** 8702108

**4. [Minor] `perf/suites/micro/conftest.py` and `perf/suites/common.py` added**
- Shared fixtures/helpers not in the plan's file list; keeps the four
  micro modules thin and lets the scale suite reuse the artifact-driven
  operator-registry builder. Commit 95fe14a.

## Verification

- `pytest perf/suites/micro` + `gate.py --suite micro`: 13 passed, exit 0,
  "NO BASELINE — NOT GATED" on every row, p50/p95/p99/median printed
- `pytest perf/suites/scale` + `gate.py --suite scale`: 4 passed, exit 0
- `micro.raw.json` benchmark count: 13 (within [10, 15]); IDs carry all
  required tokens (traversal/temporal/policy/similarity/composed/
  sequential/agent_factory/task_factory/run_coroutine_sync + three gates)
- `grep -rc "assert.*elapsed|assert.*< [0-9]"` → 0 matches in both suites
- `grep -c "setup=" perf/suites/scale/test_assembly.py` → 1
- Always-on `pytest tests/ -q`: 1475 passed, 2 skipped (untouched, green)

## Known Stubs

None.

## Threat Flags

None — T-11-07 mitigated (explicit pedantic rounds + D-07 flex + wall-time
criteria met); T-11-08 mitigated (every benchmark carries a correctness
sanity check on its result value).

## Commits

| Commit | Type | Description |
| --- | --- | --- |
| 95fe14a | feat | micro suite (13 benchmarks) + shared helpers + factory fixture artifacts |
| 8702108 | feat | scale suite (assembly + projection curves) + boot_fabric refactor |

## Self-Check: PASSED

All 16 created files and the modified `perf/conftest.py` exist; commits
95fe14a and 8702108 present in log; both suites green through gate.py;
always-on suite green.
