---
phase: 11-performance-battery
plan: 02
subsystem: perf
tags: [perf, synthetic-data, determinism, fixtures]
requires: []
provides:
  - perf.synth deterministic generator (events + decision stream)
  - neutral ontology/controlplane artifacts under perf/synth/artifacts/
  - session-scoped rung fabric fixtures (fabric_1k/10k/100k)
  - always-on determinism drift alarm in tests/perf_synth
affects: [11-03, 11-04, 11-05, phase-12]
tech-stack:
  added: []
  patterns:
    - seeded-rng-threading (single random.Random per stream, seed + rung offsets)
    - values-in-artifacts fixture ontology (D-09)
key-files:
  created:
    - perf/__init__.py
    - perf/synth/__init__.py
    - perf/synth/generator.py
    - perf/synth/artifacts/ontology.yaml
    - perf/synth/artifacts/controlplane.yaml
    - perf/conftest.py
    - perf/pytest.ini
    - tests/perf_synth/__init__.py
    - tests/perf_synth/test_determinism.py
  modified: []
decisions:
  - "PERF_SEED = 20260801; per-stream rngs seeded PERF_SEED + rung (+1 events, +2 decisions)"
  - "k (average degree) = 3; hubs = 1% of entities; tail obs 3-7, hub obs 8-10"
  - "Generator-side URIs are class://ref (pin/cross-reference names); fabric mints its own content-hashed URIs at L2"
metrics:
  duration: "~35 min"
  completed: "2026-08-02"
---

# Phase 11 Plan 02: Synthetic Generator + Rung Fixtures Summary

Deterministic hub-heavy synthetic dataset generator (`perf.synth`) with neutral
YAML artifacts, session-scoped fabric fixtures ingesting through
`handle.worker.ingest` only, and always-on pinned-checksum drift tests.

## Pinned values (D-08)

- **Seed:** `PERF_SEED = 20260801`
- **k (average degree):** 3 (D-28; edges = 3 × entities at every rung)
- **Shapes** `(entities, edges, observations)`:
  - 1k: `(1000, 3000, 5090)` — checksum `6c79a33f8789f7653df24d95ec80c2d97fd1dd7a606c832a822792d956c30a77`
  - 10k: `(10000, 30000, 50749)` — checksum `24ff0e669b456312e3d67d6467d4ce2dac9c7bf2ff8be612f64b82dda6b355df`
  - 100k: `(100000, 300000, 503755)` — checksum `83a61d5a518d4c1823852f6ae53fac3e7b1e3fb66a87badc11f28c232bdd1cd4` (perf-tree only, not pinned in always-on tests)

## Degree-distribution sanity (D-27)

Inline check at rung 1000: max entity degree **780**, mean degree **6** —
max ≥ 130× mean, comfortably hub-heavy. (Script: count subject/object
occurrences over `_topology(1000).edges` via `collections.Counter`.)

## 100k timing observation (for 11-05 budget calibration)

- Topology + checksum at 100k: **~6.4 s**
- Envelope materialization (803,755 SignalEnvelope objects): **~3.6 s**
- Total generator-side cost at the top rung ≈ **10 s** — fits the D-25
  fabric-scale 3-minute budget with the dominant cost expected to be
  ingestion, not generation.

## Always-on runtime delta

`pytest tests/` full suite: **131 s** (1457 passed, 2 skipped). The fabric
boot test (test 4, rung-1k ingestion of 8090 envelopes through L2 into
SQLite) accounts for ~46 s of that. This is the L2-path proof the plan
mandates; if it becomes a CI concern, 11-05 can size-guard it.

## Task Commits

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 | Neutral ontology artifacts + seeded generator | bcf2354 |
| 2 (RED) | Failing determinism tests | d8d5b3d |
| 2 (GREEN) | Rung fabric fixtures + perf rootdir config | 85d960a |

## Grep gates verified

- `ccf.graph` imports in generator (comment-filtered): 0
- `now()` in generator (comment-filtered): 0
- Ontology vocabulary literals (`node_alpha|node_beta|node_gamma|rel_link|rel_tie|alpha_ref`) in generator source: 0
- `pytest tests/ --collect-only | grep -c "perf/suites"`: 0 (perf tree never collected by the always-on run)

## Deviations from Plan

None - plan executed exactly as written. (Note: no worktree `.venv`; verification
used the main checkout's interpreter with `PYTHONPATH=src:runtime` resolving the
worktree's sources — same discipline as the Makefile.)

## Known Stubs

None.

## Threat Flags

None — all threat-register mitigations applied (yaml.safe_load only; typed
`extra=forbid` contract construction for the resolution spec; ingestion
exclusively via `handle.worker.ingest`; grep gate asserts zero `ccf.graph`
imports in the generator).

## Self-Check: PASSED

All 9 created files exist; commits bcf2354, d8d5b3d, 85d960a present in log;
`pytest tests/perf_synth -q` 6 passed; full `pytest tests/ -q` green.

## TDD Gate Compliance

Task 2: RED commit d8d5b3d (test 4 failing on missing `perf.conftest`) →
GREEN commit 85d960a (all 6 passing). No refactor commit needed.
