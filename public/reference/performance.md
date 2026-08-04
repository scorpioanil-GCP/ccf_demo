# Performance

CCF ships a performance battery that measures the fabric's load-bearing paths —
operators, factories, the validation gates, L2 assembly, projection, cross-process
transports, and decision replay.

This page publishes a **measured, approved baseline**. Every number below comes from
the committed baseline file itself, included verbatim; nothing on this page is
transcribed by hand, estimated, or projected. Read the
[claims boundary](#what-these-numbers-do-and-do-not-claim) before comparing these
figures to your own environment — they are not a portable performance guarantee.

## The measured baseline

Medians in seconds, keyed by benchmark id. Parametrized ids carry their ladder rung
(`[500]`, `[1000]`, `[100000]`) — the rung is part of the key, so changing a ladder
invalidates the baseline rather than silently re-scaling it.

```json
--8<-- "perf/baselines/local.json"
```

The `metadata` block records when the battery ran, at which commit, on which runner
class, and who approved the numbers. That approval is a precondition of publication,
not a formality — see the ritual below.

## What the suites measure

The battery is four suites, run through one report-and-gate pipeline.

| Suite | What it measures |
| --- | --- |
| `micro` | Individual operators (traversal, temporal, policy, similarity), the composed and sequential operator pairs, the agent and task factories, the three Context Product validation gates, and sync/async dispatch overhead. |
| `scale` | L2 context assembly and projection over a fabric-size ladder, so the shape of the growth curve is visible rather than a single point. |
| `crossproc` | Real localhost round-trips over MCP egress and peering — a subprocess is actually spawned, though spawn cost is excluded from the timings. |
| `replay` | Decision replay over a ladder of decision-history sizes, asserting byte-exact reproduction and a documented-linear growth curve. |

**Determinism.** The datasets are synthetic and fully deterministic: a fixed seed with
per-stream derivation, fixed ladder rungs, and checksum pins on the generated
topologies. A generator change that shifts a checksum is a deliberate dataset change —
it updates the pins and re-baselines every affected suite, because the old numbers
measured a different dataset.

**Gating model.** The gate compares the **current median against the approved baseline
median**, per benchmark, as a relative change. Suite thresholds are micro 10%, scale
10%, crossproc 25%, replay 15% — crossproc is looser to absorb localhost transport and
scheduler noise, and replay's percentage gate is secondary to that suite's own
byte-exact and curve-shape assertions. Per-benchmark overrides may only **loosen** a
suite default; a tighter override is rejected outright, so the reviewed default remains
the floor.

**Slowdowns fail; speed-ups warn.** Only a gated slowdown exits nonzero. A benchmark
that suddenly runs far faster usually stopped measuring the real work, so the gate
prints a loud warning and stays green for a human to investigate.

What the gate does **not** do: it does not compare against absolute targets, it does not
compare across runner classes, and it does not judge whether a number is *good* — only
whether it moved.

## Environment manifest

The numbers above are numbers *of* this environment:

| | |
| --- | --- |
| Runner class | `local` |
| Host | 20-core x86-64 Linux workstation (kernel 6.17) |
| Python | 3.12.3 |
| Commit | `8aefb2ad18b17c0596d0124378c0d40548cfc623` |
| Date measured | 2026-08-03 |
| Approved by | Dave, 2026-08-03 |
| Command | `make perf CCF_PERF_RUNNER_CLASS=local` |

Full-battery wall time was roughly five and a half minutes against a ten-minute budget,
distributed across the four suites. Per-suite budgets and the reference wall-time table
are maintained in `perf/README.md`.

Concurrent load during this run is disclosed rather than hidden: other work was resident
on the host, but load average stayed well below core count throughout and every suite
matched the previously recorded quiet-machine reference, so the run was judged
uncontended and approved as measured.

## What these numbers do and do not claim

- **Baselines are comparable only within a runner class.** Every baseline is keyed by
  runner class, and a run only ever gates against its own class. Numbers measured on
  `local` say nothing about a CI runner, a container, or your laptop.
- **Absolute times on shared runners are not a cross-environment comparison.** Hosted
  CI runners are noisy neighbours by construction. The battery is a *regression
  detector within an environment*, not a benchmark suite for ranking environments.
- **These are not throughput or capacity numbers.** No suite models concurrency,
  sustained load, or production data distributions. The datasets are synthetic and
  chosen for determinism, not realism.
- **Performance gating is opt-in.** Always-on CI never times anything and stays
  deterministic-only; the timed battery runs on explicit dispatch or locally. What
  always-on CI does run is an untimed bitrot smoke that executes every suite once, so
  the benchmarks cannot silently rot.
- **Regression-detection latency is bounded by ritual, not automation.** Because the
  battery is opt-in, a regression is caught when someone runs it — not the moment it
  lands. That is a deliberate trade against gating every merge on noisy timings.
- **A missing or unknown baseline never fails a run.** It reports loudly and exits
  zero, so a typo in a runner-class key can never gate your build against another
  machine's numbers.

## How these numbers change — the re-baseline ritual

**Nothing auto-records a baseline.** The gate has no write path to the baseline
directory, and that absence is asserted by a test against the gate's own source.
Recording or updating a baseline is a deliberate, reviewed, human-authorized act:

1. **Run the battery** on the target runner class.
2. **Review the results** — medians sane, no warning indicating a benchmark stopped
   measuring real work, wall times within budget. An implausible result stops the
   process here: a bad baseline is worse than no baseline, because everything
   downstream is compared against it.
3. **The maintainer approves** the run's numbers. A passing review is a precondition of
   approval, never a substitute for it.
4. **Write the baseline by hand** from the approved run's medians, in the documented
   schema, including the approval reference.
5. **Log the event** in the decision record: which run, which commit, which approval.
6. **Commit the baseline for review** like any other change.

The same ritual governs *re*-baselining after an accepted performance change. A gate
failure is never resolved by quietly refreshing the baseline — that would convert the
regression detector into a rubber stamp.
