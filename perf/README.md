# CCF Performance Battery (`perf/`)

The perf battery is the SDK's opt-in performance surface (Phase 11;
PERF-01..PERF-04). It measures the fabric's load-bearing paths —
operators, factories, gates, L2 assembly, projection, cross-process
transports, and decision replay — through **one** report+gate pipeline
(`perf/gate.py`), and it **never joins always-on CI**: `make ci` never
times anything (D-IMPL-70). What always-on CI does run is the
deterministic bitrot smoke (`tests/perf_smoke`), which executes every
suite once with `--benchmark-disable` — the callables run, the
correctness asserts fire, nothing is timed (D-04).

## Running the battery

```
make perf            # full battery, ~10-minute budget (D-17)
make perf-micro      # operators, composed/sequential pair, factories, gates, dispatch
make perf-scale      # L2 assembly + projection curves over the rung ladder
make perf-xproc      # MCP egress + A2A/peering round-trips (real localhost subprocess)
make perf-replay     # replay-at-scale ladder: byte-exact + curve shape
```

Each target runs pytest-benchmark (raw JSON to gitignored
`perf/results/<suite>.raw.json`) and then `perf/gate.py`, which prints a
p50/p95/p99/median table, writes `<suite>.results.json`, and applies the
gate **only when a committed baseline exists** for the runner class in
force. With no baseline every row prints a loud `NO BASELINE — NOT
GATED` notice and the run exits 0 (D-13).

### Budget (D-17 / D-25) and measured wall times

Target: full battery ≈ 10 minutes, split micro 2 / fabric-scale 3 /
cross-process 2 / replay 3 minutes (D-25). Measured full `make perf` run
on the reference local machine (runner class `local`, 2026-08-02,
exit 0 report-only):

| Suite | Budget | Measured wall time |
| --- | --- | --- |
| micro | ~2 min | 52 s (includes the ~40 s session 1k-fabric build) |
| scale | ~3 min | 207 s (3:26; the 1k assembly rung at 2 rounds dominates) |
| crossproc | ~2 min | 2.4 s (subprocess spawn excluded from timings) |
| replay | ~3 min | 65 s |
| **total** | **~10 min** | **5 min 28 s** (`make perf`, including gate.py runs) |

The always-on bitrot smoke (`pytest tests/perf_smoke`) runs all four
suites untimed at the smallest ladder rungs in ~2.3 minutes, with a hard
300 s per-suite subprocess timeout (T-11-14).

## Runner-class keys (D-10)

Baselines are only comparable within a runner class. The key comes from
the `CCF_PERF_RUNNER_CLASS` environment variable and selects
`perf/baselines/<runner-class>.json`:

| Key | Meaning |
| --- | --- |
| `gh-ubuntu-24.04` | The opt-in GitHub Actions job (`perf.yml`). The key names the **pinned** image — the workflow uses `runs-on: ubuntu-24.04`, never a floating tag, so the class stays stable. |
| `local` | Developer machines; the Makefile default. |
| custom | `make perf CCF_PERF_RUNNER_CLASS=my-runner` — any key matching `[A-Za-z0-9._-]+` (T-11-02). |

An **unknown, missing, or invalid key selects no baseline and the run is
report-only** (exit 0, loud notice) — a typo can never gate against the
wrong machine's numbers.

## The re-baseline ritual (D-IMPL-70 — Dave-gated, manual)

**Nothing ever auto-records a baseline.** `perf/gate.py` has no write
path to `perf/baselines/` — that absence is source-asserted by
`tests/perf_gate`. Recording or updating a baseline is a deliberate,
reviewed act, per D-IMPL-70 ("repo-owned thresholds and baselines,
reviewed like code; baseline updates are Dave-approved"):

1. **Dispatch `perf.yml`** (Actions → perf → Run workflow) on the target
   runner class, or run `make perf` locally for the `local` class.
2. **Review the results artifact** (`perf-results-*` upload, or
   `perf/results/*.results.json` locally): medians sane, no WARNs that
   indicate a benchmark stopped measuring real work.
3. **Dave approves** the run's numbers (§3.1 authority — the review is a
   precondition, never a substitute).
4. **Manually write `perf/baselines/<runner-class>.json`** from the
   approved run's `<suite>.results.json` medians, in the D-12 schema:

   ```json
   {
     "metadata": {"date": "YYYY-MM-DD", "commit": "<sha>", "approved": "<ref>"},
     "benchmarks": {"<benchmark_id>": <median_seconds>}
   }
   ```

   Benchmark IDs are the pytest node IDs including parametrized rungs
   (e.g. `test_assembly_scale[500]`) — rung values are baseline keys, so
   changing a ladder invalidates the baseline (Pitfall 6).
5. **Log the event in `docs/DECISIONS.md`** (which run, which commit,
   Dave's approval date).
6. **Commit the baseline for review** like any other change.

The same ritual applies to *re*-baselining after an accepted performance
change: gate failures are never fixed by silently refreshing the
baseline.

## Thresholds review rules (D-19..D-22)

`perf/thresholds.toml` is the entire threshold policy, reviewed like
code:

- Suite defaults (relative-median): **micro 10%, scale 10%, crossproc
  25%, replay 15%**. Crossproc is looser to absorb localhost transport
  and scheduler noise (D-18/D-20); replay's % gate is secondary to the
  suite's own byte-exact and curve-shape asserts (D-21).
- Per-benchmark overrides are **loosen-only** (D-22): an override must be
  ≥ its suite default, and must carry a comment documenting the noise
  rationale. `gate.py` rejects a tighter override with a typed load
  error. Tightening happens by lowering the suite default — the reviewed
  default remains the floor.

## Speed-up policy

**Beyond-threshold improvements WARN, never fail.** A benchmark that
suddenly runs 10x faster usually stopped measuring the real work
(11-RESEARCH.md Open Question 1); `gate.py` prints a loud WARN so a
human investigates, but the run stays green. Only gated **slowdowns**
exit nonzero.

## Determinism: seed, ladders, checksum pins (D-08)

- **Seed:** `PERF_SEED = 20260801` (`perf/synth/generator.py`);
  per-stream RNGs are seeded `PERF_SEED + rung` (+1 events, +2
  decisions). The generator is fully deterministic at every rung.
- **Fabric-scale ladder in force: `(500, 1000)`** — a D-07 flex from the
  pinned (1k, 10k, 100k), because L2 ingestion runs ≈5 ms/envelope on
  the reference SQLite path (10k ≈ 7 min/round, 100k > 1 hour), and
  rungs below ~400 hang the generator's unique-edge sampler
  (`hub_count × tail_count ≥ 3 × rung` with hubs at 1% of entities).
  Widening the ladder back up is a future budget call once ingestion
  throughput improves — and requires re-baselining.
- **Replay history ladder: exactly 1k/10k/100k decision records**, base
  records from `decision_stream(100_000)` (10k records) replicated with
  a deterministic replica index for the top rung (D-07 flex — the
  1M-entity topology takes >5 minutes to generate).
- **Checksum pins:** `tests/perf_synth` pins the 1k/10k topology
  checksums (1k `6c79a33f…`, 10k `24ff0e66…`); any generator change that
  shifts a checksum is a **deliberate dataset change** — update the pins
  in the same commit, state why, and re-baseline every affected suite
  (the old baselines measured a different dataset).
- **Smoke knob:** `CCF_PERF_SMOKE=1` collapses the scale and replay
  ladders to their smallest rung; it exists solely for the always-on
  bitrot smoke and must never be set for a timed/gated run.

## Lint and typecheck scope

`perf/` is deliberately **outside** the invariant-lint and typecheck
scopes: `tools.lints` `LINTED_TREES = ("src", "runtime", "examples")`
and `[tool.mypy] files = ["src", "runtime"]` do not include `perf/` (or
`tests/`). The perf tree still honors the load-bearing disciplines by
construction — values live in `perf/synth/artifacts/*.yaml` (D-09,
No-Hardcoding §6.4) and all ingestion goes through `handle.worker.ingest`
(single-writer §10) — but the CI lints do not mechanically enforce them
here. Extending lint scope to `perf/` is a future decision, not an
accident of omission.

## Phase 14 pointer

Phase 14's `PERFORMANCE.md` links to (and partially includes) this
document as the canonical description of the measurement methodology and
the re-baseline ritual (D-14). Curve artifacts intended for it land in
`perf/results/replay.curve.json` (fitted replay-growth exponent) and the
per-suite `*.results.json` files.
