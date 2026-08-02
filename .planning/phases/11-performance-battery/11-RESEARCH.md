# Phase 11: Performance Battery - Research

**Researched:** 2026-08-01
**Domain:** Python performance benchmarking, CI perf regression gating, deterministic synthetic data generation
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Benchmark harness & metrics (PERF-01)
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

#### Synthetic dataset generator (PERF-02)
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

#### Baselines & thresholds mechanics (PERF-04)
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

#### Cross-process & replay-at-scale design (PERF-03)
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

#### Threshold numbers
- **D-19:** Suite-default relative-median threshold is **10%** for the
  micro-benchmark and fabric-scale suites.
- **D-20:** Cross-process latency suite default is **25%**.
- **D-21:** Replay-at-scale suite default is **15%**; the primary guard
  remains the curve-shape (sub-linear or documented-linear) and byte-exact
  replay assertions — the % gate is secondary.
- **D-22:** Per-benchmark overrides in `perf/thresholds.toml` may only
  **loosen** the suite default. Tightening happens by lowering the suite
  default.

#### Benchmark selection
- **D-23:** Micro suite is a **representative set (~10–15 benchmarks)**: one
  per operator category (traversal/temporal/policy/similarity) plus a
  composed chain, agent + task factory construction, all three validation
  gates, and the `run_coroutine_sync` overhead benchmark (D-05).
- **D-24:** Dedicated **composed-vs-sequential** benchmark quantifying the
  cost of `(A∘B)(G)` versus `A(B(G))` — timing evidence for the composition
  claim, feeding Phase 14's PERFORMANCE.md.
- **D-25:** The ~10-minute budget splits **micro 2 / fabric-scale 3 /
  cross-process 2 / replay 3 minutes**.
- **D-26:** Fabric-scale curves cover **assembly + projection only** — no
  operator- or serve-path curves in v0.2.

#### Generator topology
- **D-27:** Degree distribution is **skewed/hub-heavy** (power-law-ish),
  deterministic under the fixed seed.
- **D-28:** **Constant average degree across rungs** (edges grow linearly
  with entities).
- **D-29:** Entities carry a **multi-observation temporal history** (~3–10
  timestamped observations, hubs more).
- **D-30:** The **same generator emits both graph fixtures and the
  deterministic decision-record stream** for the replay ladder (D-16).

### Claude's Discretion
- Rounds/warmup calibration and per-rung sizing to hit the per-suite budgets
  in D-25.
- Exact module layout inside `perf/`, Makefile target names, and `perf.yml`
  job structure (must be `workflow_dispatch` opt-in per D-IMPL-70, mirroring
  the live-legs.yml pattern).
- Exact hub/tail parameters of the skewed distribution and per-entity
  observation counts, provided D-08 determinism and D-27..D-29 shape hold.

### Deferred Ideas (OUT OF SCOPE)
- Promotion of perf gating to always-on CI — explicitly a future D-IMPL per
  D-IMPL-70 (only if dedicated hardware or an instrumented-measurement
  service appears).
- Any optimization motivated by the `run_coroutine_sync` overhead numbers —
  measure here, act in a later phase.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PERF-01 | `make perf` reproducible micro-benchmark suite (operators, factory, validation gates) with p50/p95/p99 | pytest-benchmark harness pattern + percentile computation from raw timings (Standard Stack, Pattern 1, Pitfall 1) |
| PERF-02 | Fabric load/scale curves for assembly + projection via deterministic L2/factory-path generator | `perf/synth/` generator design (Pattern 3), pedantic-mode scale benchmarks (Pattern 2), determinism discipline (Pitfall 4) |
| PERF-03 | Cross-process latency (MCP egress, A2A/peering) + replay-at-scale proving year-scale claim | Subprocess-over-localhost measurement (Pattern 4), replay ladder + curve-fit assertion (Pattern 5) |
| PERF-04 | Committed runner-class-keyed baselines, thresholds.toml, opt-in `perf.yml`, re-baseline ritual | Custom gate script over shared JSON (Pattern 6 — Don't Hand-Roll caveat), workflow_dispatch structure mirroring live-legs.yml |
</phase_requirements>

## Summary

The core stack question is settled by D-01: pytest-benchmark. Verified current
version is **5.2.3** on PyPI. Its JSON export (`--benchmark-json`) includes
**all raw timings**, not just stats — which is exactly what D-03 needs, because
pytest-benchmark's built-in stats table has median/IQR/min/max/mean but **not
p95/p99**. The correct architecture is: pytest-benchmark produces one raw JSON
per suite run; a thin SDK-owned report/gate script (`perf/report.py` or
`perf/gate.py`) computes p50/p95/p99 + median from the raw `stats.data`
arrays, prints the terminal table, writes the machine-readable results JSON
under `perf/results/`, and — when a baseline for the declared runner class
exists — applies the relative-median thresholds from `perf/thresholds.toml`
(read with stdlib `tomllib`; Python 3.12, zero new deps). Do **not** use
pytest-benchmark's own `--benchmark-compare-fail` machinery: it compares
against its `.benchmarks/` storage format, gates on min/mean expressions, and
has no notion of runner-class keys, suite-level defaults, loosen-only
overrides, or loud missing-baseline report-only behavior. The comparison logic
here is small (~100 lines) and is precisely the part D-IMPL-70 says must be
repo-owned and reviewed.

The other three suites bend pytest-benchmark's model deliberately: fabric-scale
and replay suites use `benchmark.pedantic()` with explicit rounds (scale-curve
iterations are seconds each, auto-calibration would blow the budget);
cross-process spawns the real MCP/peering subprocess once per session in a
fixture (mirroring `examples/04-cross-process/producer_child.py`), warms it,
then benchmarks client round-trips only. The synthetic generator is plain
seeded-`random.Random` Python in `perf/synth/`, emitting entities/observations
exclusively through the same L2/boot/factory surfaces `tests/conftest.py`
already uses, with its neutral ontology declared in YAML definition artifacts
under `perf/` per D-IMPL-28.

**Primary recommendation:** pytest-benchmark 5.2.3 for timing capture only;
everything downstream of the raw JSON (percentiles, terminal table, results
file, baseline gate) is one small repo-owned script so report and gate
provably read the same numbers (D-02/D-03).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Timing capture (warmup, rounds, GC control) | pytest-benchmark plugin | — | D-01 locked; battle-tested calibration |
| Percentiles + terminal table + results JSON | `perf/` repo-owned script | — | pytest-benchmark lacks p95/p99; single-pipeline rule (D-02/D-03) |
| Baseline comparison + gating | `perf/` repo-owned script | perf.yml (exit code) | D-IMPL-70 repo-owned reviewed logic; runner-class keying is bespoke |
| Fixture generation | `perf/synth/` | L2/factory surfaces in `/src` | No-Hardcoding: generator interprets artifacts; writes only via L2 |
| Cross-process endpoints under test | subprocess (real `/runtime` servers) | perf suite as client | D-15: honest transport numbers |
| CI orchestration | `.github/workflows/perf.yml` | Makefile targets | workflow_dispatch opt-in, mirrors live-legs.yml |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest-benchmark | 5.2.3 | Timing harness (warmup, calibration, GC disable, raw-timing JSON export) | D-01 locked; de-facto pytest benchmarking plugin `[VERIFIED: pip index versions + official docs pytest-benchmark.readthedocs.io]` |
| pytest | 9.1.1 (already pinned) | Test runner for perf suites | Existing project pin `[VERIFIED: pyproject.toml]` |
| tomllib | stdlib (Py 3.12) | Read `perf/thresholds.toml` | Zero-dependency TOML reading `[VERIFIED: stdlib since 3.11]` |
| random.Random / hashlib | stdlib | Seeded generator + rung checksums | Deterministic across platforms for the operations used `[VERIFIED: CPython docs guarantee]` |

No other new dependencies are needed. Do **not** add numpy for percentiles —
`statistics.quantiles(data, n=100)` or a two-line index computation on the
sorted raw timings suffices `[VERIFIED: stdlib]`.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pytest-benchmark | pyperf | Better statistical rigor, but no pytest integration; D-01 forecloses it |
| Custom gate script | `--benchmark-compare-fail=median:10%` | Built-in, but gates against `.benchmarks/` storage, no runner-class keys, no suite defaults/loosen-only overrides, no loud report-only mode — cannot satisfy D-10..D-13 |
| Custom gate script | github-action-benchmark | Popular CI action, but gh-pages-oriented, mean-based, auto-updating baselines — violates D-13 (never auto-record) |

**Installation:** add a `perf` optional-dependency group in `pyproject.toml`
(`perf = ["pytest-benchmark==5.2.3"]`) and fold it into `dev` so `pip install
-e ".[dev]"` keeps being the one command. Verify at install: `pip index
versions pytest-benchmark` (confirmed 5.2.3 current, 2026-08-01).

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| pytest-benchmark | PyPI | ~11 yrs | multi-M/mo | github.com/ionelmc/pytest-benchmark | not run (tool unavailable) | Approved — long-established, official docs on readthedocs, D-01-locked |

slopcheck was not installed in this environment; per protocol pytest-benchmark
is technically `[ASSUMED]`-provenance, but it is confirmed via its official
readthedocs documentation and PyPI listing and is user-locked by D-01, so no
checkpoint gate is warranted. No other new packages.

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─ make perf-micro ──┐
 make perf ─────────┼─ make perf-scale ──┼──► pytest -p benchmark  perf/suites/<suite>/
 (or perf.yml       ├─ make perf-xproc ──┤        │  --benchmark-json perf/results/<suite>.raw.json
  workflow_dispatch)└─ make perf-replay ─┘        │  (raw timings incl. stats.data)
                                                  ▼
        perf/synth/ generator ──(L2/factory paths only)──► fabric fixtures (session-scoped)
        (seed + rung checksums,                            + decision-record stream (D-30)
         ontology YAML artifacts)
                                                  ▼
                              perf/gate.py  ◄── perf/thresholds.toml (tomllib)
                              computes p50/p95/p99 + median per benchmark
                                    │
                    ┌───────────────┼──────────────────────────┐
                    ▼               ▼                          ▼
        terminal percentile   perf/results/<run>.json   gate verdict:
        table (D-02)          (gitignored, D-02)        baseline for CCF_PERF_RUNNER_CLASS?
                                                        ├─ yes → relative-median check → exit 0/1
                                                        └─ no  → LOUD "no baseline — not gated",
                                                                 exit 0 (D-13)
                              perf/baselines/<runner-class>.json (committed, median-only, D-12)
```

### Recommended Project Structure
```
perf/
├── README.md              # re-baseline ritual, runner-class key list (D-14)
├── conftest.py            # session fixtures: fabric per rung, subprocess endpoints
├── thresholds.toml        # suite defaults 10/10/25/15% + loosen-only overrides
├── baselines/
│   └── gh-ubuntu-24.04.json   # median-only + metadata (D-12); committed
├── results/               # gitignored (D-02)
├── gate.py                # report + gate, one pipeline (runnable as python -m)
├── synth/
│   ├── __init__.py        # generator API: build_fabric(rung), decision_stream(rung)
│   ├── generator.py       # seeded topology + temporal histories (D-27..D-30)
│   └── artifacts/         # neutral ontology YAML defs (D-09, D-IMPL-28 format)
└── suites/
    ├── micro/             # ~10–15 benchmarks (D-23, D-24, D-05)
    ├── scale/             # assembly + projection curves over 1k/10k/100k (D-26)
    ├── crossproc/         # MCP egress + peering round-trips (D-15)
    └── replay/            # replay ladder + byte-exact + curve-shape (D-16, D-21)
```
Add `perf` to `PYTHONPATH` in the Makefile perf targets (as `src:runtime` is
today) or make `perf/` a rootdir-configured pytest tree with its own
`pytest.ini`/`conftest.py` — keep it out of the default `pytest` collection so
`make test` never picks it up (D-04).

### Pattern 1: Micro-benchmarks with the `benchmark` fixture
```python
# Source: pytest-benchmark.readthedocs.io/en/latest/usage.html
def test_traversal_operator(benchmark, fabric_1k):
    op = make_traversal(...)          # built through factory paths
    result = benchmark(op.invoke, fabric_1k.graph_view)
    assert result is not None         # correctness sanity, never timing asserts
```
Run with `--benchmark-disable-gc --benchmark-warmup=on --benchmark-json=...`.
Auto-calibration is fine here (micro ops are µs–ms; the 2-minute budget holds).
Never write `assert elapsed < X` in any perf test — the gate script is the
only timing judge (D-IMPL-70 relative gating; absolute asserts are
flake-by-construction on shared runners).

### Pattern 2: Scale/replay suites with pedantic mode
```python
# Source: pytest-benchmark.readthedocs.io/en/latest/pedantic.html
@pytest.mark.parametrize("rung", [1_000, 10_000, 100_000])
def test_assembly_scale(benchmark, rung, synth_events):
    benchmark.pedantic(assemble_rung, args=(synth_events[rung],),
                       rounds=3, iterations=1, warmup_rounds=1)
```
Explicit `rounds` keeps the 3-minute suite budgets (D-25) predictable —
auto-calibration on a seconds-long callable would run far too many rounds.
Rung construction happens in session-scoped fixtures, **outside** the timed
callable (build once, measure assembly/projection separately — assembly
measurement needs a fresh graph per round, so use a setup callable via
`benchmark.pedantic(..., setup=fresh_graph)`).

### Pattern 3: Deterministic generator through L2/factory only
- One `random.Random(seed)` instance threaded through everything; document the
  seed in `perf/README.md` (D-08).
- Hub-heavy degree: draw hub count `h ≈ 1%` of entities; connect tail entities
  to hubs with probability weighted by hub index (Zipf-ish via
  `rng.choices(hubs, weights=[1/i ...])`) — deterministic, no numpy (D-27).
- Keep average degree constant: `edges = k * entities` (D-28).
- Emit events into L1/L2 exactly as `tests/conftest.py` and example 00 do —
  the generator produces *event streams* and *definition artifacts*, never
  graph rows. Grep-check: generator must not import graph internals.
- Per-rung shape assertion: pinned `(entity_count, edge_count, observation_count)`
  tuple + a stable checksum (e.g. sha256 over sorted entity URIs and edge
  pairs) asserted in a deterministic smoke test in `/tests` (D-04, D-08).
  Do **not** checksum floats or dict iteration order without sorting.

### Pattern 4: Cross-process latency measurement
- Session-scoped fixture spawns the real server subprocess (reuse
  `examples/04-cross-process/producer_child.py` wiring shape), waits for a
  readiness signal (poll the port / read a ready line from stdout — never
  `sleep(n)`), performs N warm-up round-trips, then yields a client.
- Benchmark the client call only: `benchmark(client.fetch_product, uri)`.
- Terminate the subprocess in fixture teardown with a timeout + kill fallback
  (existing example 04 already demonstrates the discipline).
- 25% threshold (D-20) absorbs localhost scheduler noise; still pin
  `--benchmark-min-rounds` high enough (≥50 round-trips) that the median is
  stable.

### Pattern 5: Replay-at-scale curve assertion
- Generator emits the decision-record stream (D-30); ladder rungs 1k/10k/100k
  records.
- Per rung: (a) assert byte-exact replay of a sampled decision (existing
  replay engine + example 06 patterns), (b) time replay via pedantic mode.
- Curve-shape guard: fit `t = a * n^b` over the three rung medians
  (log-log linear regression, stdlib `math`); assert `b <= 1.0 + ε`
  (documented-linear) — this is the primary PERF-03 evidence, the 15% median
  gate is secondary (D-21). Report the fitted exponent in the results JSON so
  Phase 14's PERFORMANCE.md can cite it.

### Pattern 6: The gate script (report + gate, one pipeline)
```python
# perf/gate.py — repo-owned, reviewed per D-IMPL-70
raw = json.load(open(raw_json))          # pytest-benchmark --benchmark-json output
for b in raw["benchmarks"]:
    data = sorted(b["stats"]["data"])    # ALL raw timings are present in this export
    p50, p95, p99 = pct(data, 50), pct(data, 95), pct(data, 99)
    median = b["stats"]["median"]        # same number the gate uses (D-03)
```
- Threshold resolution: `thresholds.toml` → `[suite.<name>] default = 0.10` +
  `[override."<benchmark_id>"] threshold = 0.15`; validate loosen-only
  (override ≥ suite default) at load time (D-22).
- Runner class from `CCF_PERF_RUNNER_CLASS` env (CI sets `gh-ubuntu-24.04`;
  Makefile defaults `local`); unknown/missing baseline file or missing
  benchmark entry → print `NO BASELINE — NOT GATED` per entry, exit 0 (D-13).
- Gate: `abs(current_median - baseline_median) / baseline_median > threshold`
  on **slowdowns** fails (decide and document whether large speed-ups also
  flag — recommend warn-only for speed-ups, they usually mean the benchmark
  broke; see Open Question 1).
- Baseline files carry `{"metadata": {date, commit, approved: "D-GATE ref"},
  "benchmarks": {id: median_seconds}}` (D-12).

### Anti-Patterns to Avoid
- **Absolute-time asserts in tests:** flake-by-construction on shared runners
  (D-IMPL-70 evidence: CodSpeed data shows ≥7% minimum gates needed on
  GitHub-hosted runners even for 1% false-positive tolerance).
- **Using pytest-benchmark `.benchmarks/` storage/compare as the gate:** wrong
  keying model; also `--benchmark-autosave` would effectively auto-record
  baselines, violating D-13.
- **Generator writing graph rows directly:** violates single-writer and the
  "no lint-exempted shortcuts" success criterion; only L2/factory paths.
- **Benchmarks in default pytest collection:** `make test`/`make ci` must never
  time anything (Phase-8 D-10). Keep `perf/` outside `testpaths`; the smoke
  test in `/tests` runs the suites with `--benchmark-disable` (runs each
  benchmarked callable exactly once as a plain test — purpose-built for this).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Warmup/calibration/GC/timer selection | custom timing loop | pytest-benchmark | Timer resolution calibration and GC interference handling are subtle and solved |
| Running benchmarks once for bitrot check | separate smoke harness | `pytest perf --benchmark-disable` | Built-in flag exactly matches D-04 |
| TOML parsing | regex/ini hacks | stdlib `tomllib` | In stdlib since 3.11 |
| Percentiles | numpy dependency | `statistics.quantiles` / sorted-index | Raw data is small; no new dep |

**Inversion — DO hand-roll the gate.** Baseline comparison is the one place
custom code is correct: every off-the-shelf comparator (pytest-benchmark
compare, github-action-benchmark, CodSpeed) fails at least one of D-10, D-12,
D-13, or D-22, and D-IMPL-70 explicitly wants this logic repo-owned and
reviewed. It is ~100 lines of pure stdlib.

## Common Pitfalls

### Pitfall 1: Expecting p95/p99 from pytest-benchmark's stats
**What goes wrong:** The stats block has min/max/mean/median/IQR/q1/q3 but no
p95/p99. **How to avoid:** always run with `--benchmark-json`; that export
includes complete raw timings (`stats.data`) — compute percentiles in
`gate.py`. `[CITED: pytest-benchmark.readthedocs.io/en/latest/usage.html —
"this will include the complete data (all the timings, not just the stats)"]`
**Warning sign:** any design that parses the terminal table.

### Pitfall 2: pytest 9 compatibility
**What goes wrong:** project pins `pytest==9.1.1`; pytest-benchmark 5.2.3's
declared pytest ceiling is unverified in this session. `[ASSUMED]`
**How to avoid:** first implementation task installs and runs one trivial
benchmark under the existing pin before building the suites; if incompatible,
that is a blocking finding (D-01 is locked to pytest-benchmark, so the
resolution would be a version adjustment, not a harness swap).

### Pitfall 3: Auto-calibration blowing the time budget on slow callables
**What goes wrong:** pytest-benchmark's calibrator runs many rounds; a 5-second
assembly rung could run for minutes. **How to avoid:** pedantic mode with
explicit `rounds`/`warmup_rounds` for scale/replay/crossproc; reserve
auto-calibration for the micro suite. Budget check: time each suite during
implementation against the D-25 split and shrink the top rung if needed (D-07
allows flexing 100k).

### Pitfall 4: Non-deterministic checksums
**What goes wrong:** checksums over dict order, `set` iteration, timestamps
from `now()`, or float formatting drift across platforms. **How to avoid:**
sort everything before hashing; all timestamps generated from the seed against
a fixed epoch; checksum integers/strings only.

### Pitfall 5: Measuring subprocess startup instead of transport
**What goes wrong:** first round-trips include server import/boot cost; median
is polluted on low round counts. **How to avoid:** readiness poll + explicit
warm-up round-trips in the fixture before yielding the client; high min-rounds.

### Pitfall 6: Baseline/benchmark ID drift
**What goes wrong:** parametrized benchmark IDs (e.g. `test_assembly_scale[10000]`)
change if a rung or param name changes, silently orphaning baseline entries
into "no baseline — not gated" forever. **How to avoid:** gate script reports
baseline entries with no matching current benchmark as a loud warning too
(both directions), so drift is visible in every run.

### Pitfall 7: The `run_coroutine_sync` benchmark and event loops
**What goes wrong:** benchmarking a helper that dispatches to a loop/executor
from inside pytest can deadlock or measure the wrong path depending on whether
a loop is running. **How to avoid:** benchmark it from a plain sync test
function (no asyncio plugin involvement) with a trivial coroutine, matching
the production call shape in `runtime/ccf_runtime/orchestration/common.py`.

## Code Examples

### perf.yml skeleton (mirrors live-legs.yml)
```yaml
# Source: .github/workflows/live-legs.yml pattern (D-11 / D-IMPL-70)
name: perf
on:
  workflow_dispatch:
    inputs:
      suite:
        description: "Suite to run (all|micro|scale|crossproc|replay)"
        default: "all"
        type: string
jobs:
  perf:
    runs-on: ubuntu-24.04          # pin the image, not -latest — the runner class key names it
    timeout-minutes: 30
    env:
      CCF_PERF_RUNNER_CLASS: gh-ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12", cache: pip }
      - run: python -m venv .venv && .venv/bin/pip install -e ".[dev]"
      - run: make perf SUITE=${{ inputs.suite }}
      - uses: actions/upload-artifact@v4
        if: always()
        with: { name: perf-results, path: perf/results/ }
```
Note: pin `runs-on: ubuntu-24.04` explicitly — `ubuntu-latest` migrating under
the key would silently invalidate the `gh-ubuntu-24.04` baselines.

### Makefile targets
```make
perf: perf-micro perf-scale perf-xproc perf-replay ## Full battery (~10 min, D-17)
perf-micro: ## Micro-benchmarks (operators, factory, gates, run_coroutine_sync)
	$(ENV) PYTHONPATH=src:runtime:perf $(PYTHON) -m pytest perf/suites/micro -q \
	  --benchmark-disable-gc --benchmark-json=perf/results/micro.raw.json
	$(ENV) $(PYTHON) perf/gate.py perf/results/micro.raw.json --suite micro
```
(gate.py exits nonzero on a gated regression; report-only otherwise — D-13.)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Absolute-time CI gates | Relative-median gates vs committed baselines, or instrumented measurement (CodSpeed-style) | ~2023+ | D-IMPL-70 already encodes this; 10–25% thresholds are ecosystem-consistent |
| pytest-benchmark 4.x | 5.x (5.2.3 current) | 5.0 dropped old pytest/Python support | Use 5.2.3 with Python 3.12 |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | pytest-benchmark 5.2.3 is compatible with pytest 9.1.1 | Pitfall 2 | Blocking at first install; resolve by adjusting the pytest-benchmark (or pytest) pin — verify as the first implementation step |
| A2 | pytest-benchmark raw JSON `stats.data` contains per-round timings sufficient for p95/p99 at chosen round counts | Pattern 6 / Pitfall 1 | If rounds too few for stable p99, raise min-rounds in the micro suite; docs confirm complete data is exported |
| A3 | `--benchmark-disable` runs each benchmark exactly once as a plain test (smoke-test mechanism) | Anti-patterns | If flag semantics differ, smoke test wraps callables directly; verify with `pytest --help` at install |

## Open Questions

1. **Should large speed-ups fail the gate or warn?**
   - What we know: D-19..D-22 define slowdown thresholds; a 10x "improvement" usually means the benchmark stopped measuring the real work.
   - Recommendation: warn loudly on improvements beyond the threshold, fail only on slowdowns; document in `perf/README.md`. Planner discretion — does not need Dave.
2. **Top-rung feasibility (100k entities through real L2 paths).**
   - What we know: D-07 allows flexing the rung; L2 throughput at 100k is unmeasured.
   - Recommendation: build the ladder bottom-up during implementation, time rung construction, and flex the top rung to fit the 3-minute scale budget; record the chosen sizes in `perf/README.md`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python venv (.venv) | all suites | ✓ | 3.12 (project standard) | — |
| pytest | perf harness | ✓ | 9.1.1 pinned | — |
| pytest-benchmark | D-01 harness | ✗ (not yet installed) | 5.2.3 on PyPI | none — add to dev extras (first task) |
| tomllib | thresholds.toml | ✓ | stdlib | — |
| GitHub Actions ubuntu-24.04 | perf.yml baseline runs | ✓ (live-legs.yml precedent) | — | local-only baselines until first dispatch |
| examples/04 subprocess wiring | crossproc suite | ✓ | in repo | — |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (+ pytest-benchmark 5.2.3 in perf tree only) |
| Config file | pyproject.toml `[tool.pytest.ini_options]` (perf tree gets its own rootdir config) |
| Quick run command | `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/ -q -k perf_smoke` |
| Full suite command | `make ci` (deterministic; perf battery via `make perf` only) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PERF-01 | Micro suite runs, reports p50/p95/p99 | perf + smoke | `make perf-micro`; smoke: `pytest tests/ -k perf_smoke` | ❌ Wave 0 |
| PERF-02 | Generator determinism (seed/checksum per rung) + L2-only construction | unit (deterministic, lives in `/tests`) | `pytest tests/perf_synth/ -q` | ❌ Wave 0 |
| PERF-02 | Scale curves produced for assembly + projection | perf | `make perf-scale` | ❌ Wave 0 |
| PERF-03 | Cross-process + replay suites run; byte-exact replay + curve exponent asserted | perf (correctness asserts are deterministic) | `make perf-xproc && make perf-replay` | ❌ Wave 0 |
| PERF-04 | Gate logic: threshold resolution, loosen-only validation, missing-baseline report-only, regression detection | unit (pure functions on fixture JSON — fully deterministic, belongs in `/tests`) | `pytest tests/perf_gate/ -q` | ❌ Wave 0 |

Key discipline: **gate.py's logic is unit-tested deterministically in `/tests`
with synthetic JSON fixtures** (fake baselines + fake results) — this is how
always-on CI validates PERF-04 without ever timing anything. Timing itself is
validated only by opt-in runs.

### Sampling Rate
- **Per task commit:** `make lint typecheck` + targeted `pytest tests/<new area> -q`
- **Per wave merge:** `make ci-core`
- **Phase gate:** `make ci` green + one full local `make perf` run (report-only, `local` runner class) + one `perf.yml` dispatch on `gh-ubuntu-24.04` to record the first Dave-approved baseline

### Wave 0 Gaps
- [ ] `perf/` tree scaffold (conftest, thresholds.toml, gate.py, synth/)
- [ ] `pytest-benchmark==5.2.3` added to extras + A1 compatibility check
- [ ] `tests/` smoke test running suites with `--benchmark-disable`
- [ ] `tests/perf_synth/` determinism tests; `tests/perf_gate/` gate-logic tests
- [ ] Makefile perf targets + `.gitignore` entry for `perf/results/`

## Security Domain

Low-exposure phase — no new network surfaces beyond localhost subprocesses, no
auth changes, no new user input paths.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes (thresholds.toml, baseline JSON) | Validate with typed parsing (tomllib + explicit schema checks / Pydantic `extra=forbid`, consistent with project contracts) |
| V2/V3/V4/V6 | no | Cross-process suite reuses example 04's existing (Phase-10 hardened) endpoints; no new auth code |

Threat notes: `perf.yml` is `workflow_dispatch` on a private repo — no
untrusted-PR code execution vector. Subprocess endpoints bind localhost only
(follow example 04). Baseline JSON is repo-committed and reviewed (D-IMPL-70),
so no untrusted deserialization.

## Project Constraints (from CLAUDE.md)

- **No-Hardcoding Rule (§6.4):** synthetic ontology entity kinds/relations live
  in YAML definition artifacts under `perf/synth/artifacts/`, interpreted by
  generator code — never as code constants (D-09 restates this).
- **Single-writer (§10):** generator emits events into L1/L2 only; no direct
  graph writes; "no lint-exempted shortcuts" is a phase success criterion.
- **Harness neutrality (§7.3):** no harness imports anywhere in `perf/`
  (nothing in this phase needs one).
- **Mechanism-not-values (§11):** thresholds/baselines are perf-infra config,
  not domain values — but keep them in `perf/*.toml|json` artifacts, not code.
- **§3.1 protocol:** phase ends with `/gsd-review`, triage, Dave approval,
  D-GATE entry; the first committed baseline itself needs Dave approval per
  D-IMPL-70.
- **Existing CI invariant lints** (`make lint` — CINV-01/02/03) must stay green
  over any new importable code; run them against `perf/` if the lint tool's
  scope includes it (check `tools/lints` scope during implementation).

## Sources

### Primary (HIGH confidence)
- pytest-benchmark official docs (readthedocs, v5.2.3) — usage, JSON export semantics, compare features, pedantic mode
- PyPI (`pip index versions pytest-benchmark`) — 5.2.3 current as of 2026-08-01
- Repo: `Makefile`, `.github/workflows/live-legs.yml`, `pyproject.toml`, `tests/conftest.py`, `examples/04-cross-process/`, `docs/DECISIONS.md` D-IMPL-70

### Secondary (MEDIUM confidence)
- D-IMPL-70's recorded ecosystem evidence (CodSpeed shared-runner variance data) — already Dave-reviewed

### Tertiary (LOW confidence)
- pytest 9 × pytest-benchmark 5.2.3 compatibility — flagged A1, verify at install

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — D-01 locked; version verified on PyPI + official docs
- Architecture: HIGH — repo patterns (live-legs.yml, Makefile, example 04) directly inspected
- Pitfalls: HIGH for JSON/percentile and determinism mechanics; MEDIUM for A1 compat

**Research date:** 2026-08-01
**Valid until:** ~2026-09-01 (stable domain; re-verify pytest-benchmark pin only)
