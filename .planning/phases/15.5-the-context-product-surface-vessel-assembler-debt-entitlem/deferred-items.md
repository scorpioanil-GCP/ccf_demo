# Phase 15.5 — deferred items

Out-of-scope discoveries logged rather than fixed, per the executor scope
boundary (only issues *directly caused by* a task's own changes are auto-fixed).

## DI-15.5-01 — `make perf-micro` gate is red at the phase's base commit

**Found during:** plan `15.5-01`, task 2 (assumption A8, the pre-change perf
baseline).
**Discovered at:** `3df4e91` (`chore(15.5): mark phase execution started`), on a
worktree that changed no `src/`, `runtime/` or `perf/` file.

`make perf-micro CCF_PERF_RUNNER_CLASS=local` exits 1. Two benchmarks fail
against `perf/baselines/local.json`, and **neither is on the Context Product
surface**:

| Benchmark | Median | Baseline | Δ | Band |
|---|---|---|---|---|
| `suites/micro/test_dispatch.py::test_run_coroutine_sync_overhead` | 3.264e-05 s | 2.928e-05 s | **+11.48%** | 10% |
| `suites/micro/test_operators.py::test_composed_chain` | 1.22429 s | 0.368903 s | **+231.87%** | 10% |

All three `test_gates.py` benchmarks — the ones a fourth validation gate or a
new vessel field would move — **PASS** with headroom (see
`docs/CONTEXT_PRODUCT_RULING_EVIDENCE.md` § Q5/A8).

**Why it is deferred rather than fixed:** the `local` runner-class baseline is a
machine-specific committed artifact (`perf/baselines/local.json`), and
re-baselining it is a reviewed event under PERF-04 owned by whoever runs the
battery on the machine of record. Plan `15.5-01` is forbidden to touch `src/`,
`runtime/` or `examples/`, changed no operator, and did not cause either
regression.

**Consequence the phase must carry:** plans `15.5-07` and `15.5-09` are
instructed to measure their post-field / post-gate medians against this
baseline. They must read the *per-benchmark* verdicts for
`suites/micro/test_gates.py::*` rather than the gate's exit code, because the
exit code is already 1 for reasons that predate the phase. A plan that treats
`make perf-micro` exiting 0 as its acceptance criterion will never pass on this
machine.

**Verified by the orchestrator at wave-1 close:** both `15.5-07` and `15.5-09`
carry `make perf-micro` *inside* their `<automated>` verification blocks, which
require exit 0, while their prose success criteria permit recording and
escalating an excess. The two readings contradict each other. Carried into the
`15.5-05` ruling package rather than resolved by re-baselining, because both
plans explicitly forbid a silent re-baseline.

**Owner:** unassigned. Candidate: plan `15.5-14`'s close-out sweep, which
already owns the retirement decision for the `15.5-01` spike module.

## DI-15.5-02 — `make example-s1-01` does not exist

- **Found during:** plan `15.5-04`, task 1 (reading the example's docstrings).
- **What:** `examples/s1-01-hello-context-product/run.py` tells the reader to
  run the example with `make example-s1-01`, and plan `15.5-13`'s checkpoint
  task 4 uses `make example-s1-01` as its automated verification. No such target
  exists in the `Makefile` — `grep -n "s1" Makefile` returns nothing. The
  aggregate `examples` target (`example-00` … `example-08`, `example-ext-00`)
  does not include `s1-01` either, so the example runs in no CI job.
- **Why deferred:** adding the target and wiring it into `examples` changes what
  `make ci` runs, which is outside plan `15.5-04`'s three-file scope (an example
  added to the always-on aggregate is a CI-surface change, not a deletion).
- **Owner:** plan `15.5-13` rewrites this example and needs the target for its
  own verification step; it is the natural place to add it. If `15.5-13` is
  descoped, this becomes a phase-close finding.
