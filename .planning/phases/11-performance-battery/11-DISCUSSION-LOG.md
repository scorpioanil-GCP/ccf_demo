# Phase 11: Performance Battery - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-01
**Phase:** 11-performance-battery
**Areas discussed:** Benchmark harness & metrics, Synthetic dataset generator, Baselines & thresholds mechanics, Cross-process & replay-at-scale design

---

## Benchmark harness & metrics

| Option | Description | Selected |
|--------|-------------|----------|
| pytest-benchmark | Benchmarks as pytest tests; calibrated warmup/rounds, JSON export, percentile stats | ✓ |
| pyperf | Best statistical rigor, but standalone-script idiom next to /tests | |
| Custom timing harness | Zero new deps, but we own calibration/warmup logic | |

| Option | Description | Selected |
|--------|-------------|----------|
| Terminal table + JSON file | Human table + gitignored perf/results/ JSON; same JSON the CI gate reads | ✓ |
| Terminal table only | CI would re-derive numbers from pytest-benchmark storage | |
| JSON only | Machine-first; unfriendly for the local adopter loop | |

| Option | Description | Selected |
|--------|-------------|----------|
| p50/p95/p99 + median-of-runs | PERF-01's percentiles + D-IMPL-70's gating statistic from one source | ✓ |
| Full distribution stats | Richer but noisier; gate still uses median only | |
| You decide | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Fully separate perf/ tree | Opt-in only; smoke test in /tests catches bitrot | ✓ |
| pytest marker in /tests | Risks accidental always-on inclusion | |
| Separate tree, no smoke test | Perf code can silently break between opt-in runs | |

| Option | Description | Selected |
|--------|-------------|----------|
| Fold in run_coroutine_sync overhead benchmark | Closes Phase 10's deferred item with numbers | ✓ |
| Keep out of scope | | |

**User's choice:** All recommended options.
**Notes:** Optimization motivated by the overhead numbers stays a later decision.

---

## Synthetic dataset generator

| Option | Description | Selected |
|--------|-------------|----------|
| perf/ tree, importable | Lives with its consumer; Phase 12 can import/copy; /src stays clean | ✓ |
| src/ccf shipped utility | Grows public API; drags fixture tool under strict tooling | |
| tests/fixtures extension | Couples perf tree to /tests | |

| Option | Description | Selected |
|--------|-------------|----------|
| Log ladder ~1k/10k/100k | Three decades of spread; top rung flexes on runtime budget | ✓ |
| Finer 5-rung ladder | Smoother curves, ~double runtime | |
| You decide | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed seed + shape assertion | Regenerate identically; checksum pins workload shape; no bulky fixtures | ✓ |
| Committed generated fixtures | Byte-stable but repo bloat | |
| Seed only | Generator refactors could silently change workload | |

| Option | Description | Selected |
|--------|-------------|----------|
| Abstract neutral ontology | Meaningless kinds/relations in definition artifacts under perf/ | ✓ |
| Thin realistic flavor | More readable, slight domain-pack risk | |
| You decide | | |

**User's choice:** All recommended options.

---

## Baselines & thresholds mechanics

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit declared runner-class key | CI declares e.g. gh-ubuntu-24.04; local defaults; unknown → report-only | ✓ |
| Auto-fingerprint hardware | Fingerprints churn with runner rotation | |
| Hybrid | Declared key + advisory fingerprint metadata | |

| Option | Description | Selected |
|--------|-------------|----------|
| Suite defaults + per-benchmark overrides | Small reviewed thresholds.toml with targeted exceptions | ✓ |
| Single global threshold | Noisiest benchmark sets the bar for all | |
| Per-benchmark only | Large file, per-benchmark decisions | |

| Option | Description | Selected |
|--------|-------------|----------|
| Median-only JSON per runner class | perf/baselines/<runner-class>.json + metadata incl. D-IMPL-70 approval ref | ✓ |
| Full stats per baseline | Noisier diffs each re-baseline | |
| You decide | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Report-only, loud notice | "no baseline — not gated" per entry; green exit | ✓ |
| Fail the job | Couples new benchmarks to a Dave re-baseline event | |
| Auto-record first run | Violates D-IMPL-70 | |

| Option | Description | Selected |
|--------|-------------|----------|
| perf/README.md | Ritual lives with the tree; events still logged in DECISIONS.md; Phase 14 links it | ✓ |
| docs/ page now | Risks colliding with Phase 14 docs toolchain | |
| DECISIONS.md only | Buries how-to in the decision log | |

**User's choice:** All recommended options.

---

## Cross-process & replay-at-scale design

| Option | Description | Selected |
|--------|-------------|----------|
| Real subprocess over localhost | Honest serialization + transport numbers across a real process boundary | ✓ |
| In-process loopback | Stable but measures serialization only | |
| Both, labeled separately | Richer but doubles surface and baseline count | |

| Option | Description | Selected |
|--------|-------------|----------|
| Scaled ladder + extrapolation | ~1k/10k/100k decision records; byte-exact replay + bounded latency curve | ✓ |
| Literal year-volume run | Strongest claim, blows runtime budget | |
| You decide | | |

| Option | Description | Selected |
|--------|-------------|----------|
| ~10 minutes total | Stable medians, adopters still run it; suites also individually runnable | ✓ |
| ~5 minutes | May weaken top-rung percentile stability | |
| ~30 minutes | Only CI would run it | |

| Option | Description | Selected |
|--------|-------------|----------|
| Gate with looser suite threshold | Same mechanism; wider cross-process default absorbs transport noise | ✓ |
| Report-only, never gated | No regression protection | |
| You decide | | |

**User's choice:** All recommended options.

---

## Claude's Discretion

- Benchmark selection within named surfaces; rounds/warmup calibration; per-rung sizing to the ~10-minute budget
- perf/ module layout, Makefile target names, perf.yml job structure (workflow_dispatch opt-in)
- Proposed threshold numeric values (ecosystem practice: 10–15% relative-median on shared runners)
- Generator graph topology/connectivity profile (determinism and L2/factory-only construction hold)

## Deferred Ideas

- Promotion of perf gating to always-on CI — future D-IMPL per D-IMPL-70
- Optimizations motivated by run_coroutine_sync overhead numbers — measure now, act later
