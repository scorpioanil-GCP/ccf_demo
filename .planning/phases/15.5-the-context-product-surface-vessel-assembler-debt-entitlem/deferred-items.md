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

## DI-15.5-03 — the entitled `Perspective` stops at the door

- **Found during:** plan `15.5-06`, tasks 1 and 3.
- **What:** all three exposed product doors now resolve a `Perspective` from
  the verified grant and refuse a caller not entitled to the requested class or
  to that role. What they do **not** do is forward the resolved perspective
  into the assemble-and-gate path: `ProductResolverProtocol` and
  `ExperienceProductResolverProtocol` are three-string seams
  (`tenant, product_class, version`), so the deployment's resolver constructs
  its own `Perspective` behind them. The door therefore guarantees the
  *refusal* leg but not that the served product was shaped under the
  perspective the door authorized.
- **Why deferred:** closing it reshapes both resolver Protocols to carry a
  `Perspective`, which touches `ApiDependencies`, `runtime/ccf_runtime/cli/local.py`,
  three doors, two crossproc test children, three examples and the HTTP test
  fixtures — roughly twenty call sites. Plan `15.5-06` does not scope it: its
  own `<interfaces>` block quotes the resolver seam unchanged at all three
  doors, and its success criterion ("Perspective is derived from the verified
  grant and never asserted by the caller") is met by the door-side resolution
  and refusal. Doing it inside `15.5-06` would also have collided with the
  `perspective`-shaped work in sibling wave-2 plans.
- **Where it is recorded in code:** the `context_product` handler docstrings in
  `runtime/ccf_runtime/mcp/egress.py` and `runtime/ccf_runtime/mcp/experience.py`
  both state where the value stops and why.
- **Owner:** **CLOSED AS UNOWNED — now owned by plan `15.5-15`** (`D-IMPL-108`,
  Dave, 2026-08-11). The seam is widened exactly once, carrying both the typed
  request contract and the authorized `Perspective`, rather than being reshaped
  twice. Dave named this *"the highest-priority structural debt for the later
  waves"* on 2026-08-11.

## DI-15.5-04 — `IntermediateCache` computes a key for a cache that cannot hit

- **Found during:** the `D-IMPL-107` perf investigation (wave 3), while profiling
  `perf/suites/micro/test_operators.py::test_composed_chain`.
- **What:** `ProjectionEngine.execute` invokes each operator key **exactly once**,
  so `IntermediateCache` can never hit — the cache is unreachable *by
  construction*, not by configuration. Yet `IntermediateCache.run` computes
  `content_hash(view)` on **every** invocation purely to build the lookup key.
  Measured at roughly **0.20 s of the benchmark's remaining 0.41 s** — about half
  the remaining time, spent constructing a key nothing will ever look up.
- **Why deferred (Dave's ruling, 2026-08-11):** making the hash lazy is
  behaviour-identical and the win is real, but the key's composition is
  `D-IMPL-36`'s and is documented as *"everything `Operator.apply` can observe"*.
  Narrowing **when** that key is computed is still a change to a ruled contract
  even though the final value is identical. Nothing in Phase 15.5 depends on the
  performance win, and `make perf-micro` is green as of wave 3. Taking it now
  would be an unnecessary mid-phase edit to a ruled surface.
- **The two facts a later reader needs:** the cache is currently **unreachable by
  construction**, and the hash is computed **unconditionally**. Either could
  change independently — if a future engine change makes the cache reachable, the
  unconditional hash stops being waste and this entry stops applying.
- **Owner:** a later performance pass. Low risk, well bounded, explicitly not
  Phase 15.5's.
