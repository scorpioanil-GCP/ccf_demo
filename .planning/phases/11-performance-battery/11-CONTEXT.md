# Phase 11: Performance Battery - Context

**Gathered:** 2026-08-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a `perf/` tree with four suites — micro-benchmarks (operators, factory,
validation gates), fabric load/scale curves for assembly and projection,
cross-process latency (MCP egress, A2A/peering), and replay-at-scale — driven
by a deterministic, domain-neutral synthetic dataset generator that builds
fixtures only through L2/factory paths. `make perf` runs the battery locally
and reports p50/p95/p99 reproducibly; committed runner-class-keyed baselines
plus `perf/thresholds.toml` power an opt-in `perf.yml` CI job with
relative-median regression gating, with the re-baseline ritual documented.
Governance is fully ruled by D-IMPL-70 (Dave-gated re-baseline, repo-owned
reviewed thresholds, opt-in posture — always-on CI stays deterministic-only).
Requirements: PERF-01, PERF-02, PERF-03, PERF-04.

</domain>

<decisions>
## Implementation Decisions

### Benchmark harness & metrics (PERF-01)
- **D-01:** Timing harness is **pytest-benchmark** — benchmarks are pytest
  tests reusing existing test infra/fixtures, with calibrated warmup/rounds
  and JSON export.
- **D-02:** `make perf` reports a **terminal percentile table + a
  machine-readable JSON results file** under `perf/results/` (gitignored) —
  the same JSON the CI gate compares against committed baselines.
- **D-03:** Every suite reports **p50/p95/p99 + median-of-runs**; median is
  the D-IMPL-70 gating statistic, so report and gate read the same numbers.
- **D-04:** Perf suites live in a **fully separate `perf/` tree**, run only
  via `make perf` and the opt-in `perf.yml`. Always-on CI never runs
  benchmarks. A cheap smoke test in `/tests` asserts the suites import and
  run one iteration so `make ci` catches bitrot.
- **D-05:** The Phase-10 deferred item — measuring `run_coroutine_sync`
  per-call executor overhead — **folds in as a micro-benchmark**. Any
  optimization it motivates remains a later decision.

### Synthetic dataset generator (PERF-02)
- **D-06:** Generator lives in the **`perf/` tree** (e.g. `perf/synth/`),
  packaged importable so Phase 12 can reuse or copy it. `/src` stays free of
  fixture machinery.
- **D-07:** Scale ladder is a **log ladder ~1k/10k/100k entities** (three
  decades shows curve shape); the top rung can flex if it blows the runtime
  budget.
- **D-08:** Determinism via **fixed documented seed + checksum/shape
  assertion per rung** (entity/edge counts pinned) — generator drift is
  caught without committing bulky fixture files.
- **D-09:** Synthetic domain is an **abstract neutral ontology** —
  deliberately meaningless entity kinds/relations declared in definition
  artifacts under `perf/` (No-Hardcoding holds; unmistakably not a domain
  pack).

### Baselines & thresholds mechanics (PERF-04)
- **D-10:** Runner class is an **explicit declared key** — CI sets e.g.
  `gh-ubuntu-24.04`; local runs default to `local` or a user-passed key.
  Unknown key → report-only, no gate. No hardware fingerprinting.
- **D-11:** `perf/thresholds.toml` uses **suite-level default relative-median
  thresholds + optional per-benchmark overrides** for known-noisy
  benchmarks.
- **D-12:** Baselines are **median-only JSON per runner class** at
  `perf/baselines/<runner-class>.json`, with metadata (date, commit,
  D-IMPL-70 approval reference). Percentiles stay in run reports.
- **D-13:** **Missing baseline → report-only with a loud per-entry
  "no baseline — not gated" notice and a green exit.** Never auto-record a
  baseline (D-IMPL-70: re-baselining is a deliberate Dave-approved act).
- **D-14:** The re-baseline ritual is documented in **`perf/README.md`**
  (ritual steps, runner-class key list, thresholds review rules); each
  re-baseline event still logs in `docs/DECISIONS.md`; Phase 14's
  PERFORMANCE.md links/includes it.

### Cross-process & replay-at-scale design (PERF-03)
- **D-15:** Cross-process latency is measured against a **real subprocess
  over localhost** (actual MCP server / peering endpoint spawned as a
  subprocess) — honest serialization + transport numbers across a real
  process boundary, matching example 04's functional shape.
- **D-16:** The year-scale replay claim is quantified via a **scaled ladder +
  extrapolation**: replay against decision-history volumes on a ladder
  (~1k/10k/100k decision records sampled from the synthetic workload),
  assert byte-exact replay and bounded (sub-linear or documented-linear)
  latency in history size, and report the measured curve as the empirical
  support. No literal multi-hour year run.
- **D-17:** `make perf` targets **~10 minutes total** locally; suites also
  runnable individually (e.g. `make perf-micro`) for tight loops.
- **D-18:** The cross-process suite **is gated, with a looser suite-default
  threshold** in `thresholds.toml` to absorb transport noise — the
  suite-defaults design (D-11) handles this naturally.

### Claude's Discretion
- Exact benchmark selection within the named surfaces (which operators,
  factory paths, validation gates), rounds/warmup calibration, and per-rung
  sizing to hit the ~10-minute budget.
- Exact module layout inside `perf/`, Makefile target names, and `perf.yml`
  job structure (must be `workflow_dispatch` opt-in per D-IMPL-70, mirroring
  the live-legs.yml pattern).
- Threshold numeric values proposed for review (D-IMPL-70 evidence: 10–15%
  relative-median is ecosystem practice on shared runners).
- Graph topology/connectivity profile of the synthetic generator, provided
  determinism (D-08) and L2/factory-only construction hold.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Rulings (binding)
- `docs/DECISIONS.md` — **D-IMPL-70** (perf governance: Dave-gated
  re-baseline, repo-owned reviewed thresholds, opt-in posture, relative-median
  gating); also Phase-8 D-10/D-11 split (always-on CI deterministic-only)
- `docs/09-ruling-batch-minicycle.md` — item 3: full options analysis and
  ecosystem evidence behind D-IMPL-70

### Milestone scope
- `.planning/REQUIREMENTS.md` — PERF-01..04 texts
- `.planning/ROADMAP.md` — Phase 11 goal, success criteria (L2/factory-only
  generator, no lint-exempted shortcuts)

### Project invariants
- `CLAUDE.md` §6.4 (No-Hardcoding — generator domain values in definition
  artifacts), §11 (mechanism-not-values), §13 (observability infra is the
  deployment's problem)

### Prior phase carry-forward
- `.planning/phases/10-hardening-authorization-posture/10-CONTEXT.md` —
  deferred item: `run_coroutine_sync` per-call executor overhead (folded in
  per D-05)

### Code surfaces / patterns
- `.github/workflows/live-legs.yml` — the opt-in `workflow_dispatch` pattern
  `perf.yml` mirrors
- `Makefile` — `ci: ci-core examples` composition; `perf` targets join
  alongside, never inside `ci`
- `examples/04-cross-process/` — functional shape the cross-process latency
  suite measures (MCP egress + peering across a process boundary)
- `runtime/ccf_runtime/orchestration/` — shared loop-aware dispatch helper
  (`run_coroutine_sync`) for the D-05 micro-benchmark

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Existing `/tests` fixture and factory paths — the generator must construct
  through the same L2/factory surfaces (no bespoke graph writes).
- `live-legs.yml` — proven opt-in workflow pattern for `perf.yml`.
- Example 04's cross-process wiring — subprocess MCP/peering endpoints to
  measure against.
- pytest infra (`make test`, conftest layout) — pytest-benchmark slots in.

### Established Patterns
- D-IMPL-70 / Phase-8 D-10: always-on CI is deterministic-only; anything
  timing-dependent is opt-in. The perf tree must never leak into `make ci`
  beyond the deterministic smoke test.
- Definition artifacts (Pydantic `extra=forbid`, YAML per D-IMPL-28) carry
  all domain values — the synthetic ontology follows this.

### Integration Points
- Makefile: new `perf` (and per-suite) targets; smoke test joins `/tests`.
- `.github/workflows/perf.yml`: new opt-in job comparing
  `perf/results/*.json` against `perf/baselines/<runner-class>.json` via
  `perf/thresholds.toml`.
- Phase 12 may import/copy `perf/synth/`; Phase 14 PERFORMANCE.md consumes
  measured baselines and `perf/README.md`.

</code_context>

<specifics>
## Specific Ideas

- Report and gate must read the same JSON — no parallel number pipelines.
- Missing-baseline notices must be loud and explicit, not silent greens.

</specifics>

<deferred>
## Deferred Ideas

- Promotion of perf gating to always-on CI — explicitly a future D-IMPL per
  D-IMPL-70 (only if dedicated hardware or an instrumented-measurement
  service appears).
- Any optimization motivated by the `run_coroutine_sync` overhead numbers —
  measure here, act in a later phase.

</deferred>

---

*Phase: 11-performance-battery*
*Context gathered: 2026-08-01*
