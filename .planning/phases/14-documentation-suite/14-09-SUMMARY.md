---
phase: 14-documentation-suite
plan: 09
subsystem: perf-and-docs
tags: [performance, baseline, DOCS-06, D-IMPL-70, D-IMPL-75, gate]
requires:
  - "perf battery (Phase 11) with gate.py, thresholds.toml, synth generator"
  - "public/reference/performance.md stub from 14-01"
  - "mkdocs + pymdownx.snippets + tools/publish_scan.py from 14-01"
provides:
  - "perf/baselines/local.json — the first committed, Dave-approved measured baseline"
  - "public/reference/performance.md — DOCS-06 published performance reference"
  - "D-IMPL-75 approval record (approver, date, runner class, commit)"
  - "suite-scoped benchmark-ID drift detection in perf/gate.py"
affects:
  - "every future perf run: a baseline now exists, so runs gate rather than report-only"
tech-stack:
  added: []
  patterns:
    - "whole-file snippet include so published numbers cannot drift from the committed file"
    - "human-gated artifact creation: no automated write path to perf/baselines/"
key-files:
  created:
    - perf/baselines/local.json
  modified:
    - public/reference/performance.md
    - perf/README.md
    - docs/DECISIONS.md
    - perf/gate.py
    - tests/perf_gate/test_gate.py
decisions:
  - "D-IMPL-75 baseline approved as measured; runner class `local`; ref `Dave, 2026-08-03, phase-14 wave-2 gate`"
  - "Drift-check scoping treats an unattributable benchmark id as in-scope, so detection is never weakened by a parse failure"
  - "The approval outcome extends the existing D-IMPL-75 entry rather than opening a duplicate ID"
metrics:
  duration: ~50 min (incl. ~5.5 min battery wall time)
  completed: 2026-08-03
---

# Phase 14 Plan 09: Performance Baseline and PERFORMANCE.md Summary

Ran the Phase 11 battery on runner class `local`, gated the numbers through Dave, committed the first measured baseline, and published `PERFORMANCE.md` as a whole-file include of that baseline — so every published number is the approved file by construction.

## What was built

**The baseline.** `perf/baselines/local.json` — 22 benchmark medians covering micro, scale, crossproc and replay, in the D-12 schema, with `metadata` carrying date, commit, runner class, and Dave's approval reference. Written by hand from the run's per-suite `*.results.json` medians; `gate.py` was given no write path.

**The page.** `public/reference/performance.md` with five sections: the measured baseline (a single whole-file snippet include), what the suites measure (methodology, determinism, gating model, speed-up policy, and an explicit statement of what the gate does *not* do), the environment manifest, a claims boundary, and the re-baseline ritual.

**The pointer.** `perf/README.md`'s Phase 14 section now names the published page, explains that it includes the committed baseline rather than the curve artifacts (those land under gitignored `perf/results/`), and records that a first baseline now exists.

## Measured results

| Suite | Budget | 2026-08-02 reference | This run |
| --- | --- | --- | --- |
| micro | ~2 min | 52 s | 53.2 s |
| scale | ~3 min | 207 s | 201.4 s |
| crossproc | ~2 min | 2.4 s | 2.35 s |
| replay | ~3 min | 65 s | 65.2 s |
| **total** | **~10 min** | 5 min 28 s | **~5 min 22 s** |

Plausibility review (ritual step 2): zero WARNs, no gated failures, replay flat across the 1k/10k/100k ladder with fitted exponent `b = -4.08e-05` inside the documented-linear bound. Every suite landed within a few percent of the quiet-machine reference.

**Contention disclosure.** Three executor agents were active on the 20-core host during the run. Load average stayed 0.86–2.24 and every wall time matched the quiet reference, so the run was judged uncontended. This was surfaced to Dave at the gate rather than presented as a clean baseline by omission; he approved the numbers as measured.

## Checkpoint

Task 2 was a blocking human gate. Execution stopped with nothing committed, the full candidate JSON and all wall times returned in the checkpoint message, and no page written. Dave approved on 2026-08-03 with reference `Dave, 2026-08-03, phase-14 wave-2 gate`, confirming runner class `local`. The committed baseline was then produced from the returned transcript verbatim — the battery was **not** re-run — so the committed file is exactly what was approved.

## Deviations from Plan

### Authorized scope addition

**1. [Authorized by Dave, 2026-08-03] Suite-scoped benchmark-ID drift detection**
- **Found during:** Task 1 verification, when the first-ever baseline made the behaviour observable.
- **Issue:** `gate.py` compared every baseline key against the current run's results. Because the committed baseline covers the whole battery while each `make perf-*` target gates one suite, a single-suite run reported the other three suites' entries as benchmark-ID drift — 9 spurious warnings for `make perf-micro`. Exit code stayed 0, but noise of that volume trains reviewers to ignore a load-bearing warning.
- **Disposition:** Reported at the checkpoint as a non-blocking finding. Dave ruled to fix in-phase rather than defer.
- **Fix:** `baseline_entry_in_scope()` attributes an id via its `suites/<name>/` prefix; the drift loop considers only in-scope entries. An id with no parseable owner stays **in scope**, so detection is never weakened by an id the function cannot attribute.
- **Test-first:** RED commit `34f82ca` (3 tests: no cross-suite noise, genuine in-suite drift still warns, unattributable ids stay visible) — 2 failed as intended. GREEN commit `d7f9a68`.
- **Files modified:** `perf/gate.py`, `tests/perf_gate/test_gate.py` — an addition to the plan's declared `files_modified`.

### Judgement calls

**2. D-IMPL-75 extended rather than duplicated.** A `D-IMPL-75` entry already existed, recording the pre-execution ruling *to run* a baseline. The approval outcome (approver, date, runner class, commit, wall times, review evidence, contention disclosure) was appended to that entry as a "Baseline recorded" paragraph rather than opened as a second entry under the same ID.

**3. Candidate baseline deliberately not committed pre-approval.** The plan says not to commit it; there is a second reason worth recording — `perf/baselines/local.json` is the file `gate.py` reads, so committing a PENDING candidate would have silently begun gating the repo against unapproved numbers. The numbers survived the checkpoint via the returned transcript instead.

## Verification

- `make perf-{micro,scale,xproc,replay} CCF_PERF_RUNNER_CLASS=local` — all exit 0.
- Confirming gate pass against the baseline — 22/22 PASS, no `NO BASELINE` notice, zero warnings across all four suites.
- `pytest tests/perf_gate tests/perf_synth -q` — 27 passed (perf_gate was 18, now 21); the source assertion that `gate.py` has no write path to `perf/baselines/` still holds.
- `make docs` — exit 0; `site/reference/performance/index.html` contains the baseline JSON including the commit SHA and approval reference.
- `tools/publish_scan.py site` — exit 0.
- `tools.lints --all` — exit 0.
- Page criteria: baseline path appears exactly once (the include), include carries no section suffix, 5 `##` sections, no `N.N ms|s` median in prose, runner class + Python version + commit SHA all named.
- `git ls-files --error-unmatch perf/baselines/local.json` — tracked.
- `git status --porcelain perf/results/` — empty; results stayed gitignored.

## Commits

| Hash | Message |
| --- | --- |
| `34f82ca` | test(14-09): failing tests for suite-scoped benchmark-ID drift detection |
| `d7f9a68` | fix(14-09): scope benchmark-ID drift detection to the suite that ran |
| `b03fcc9` | docs(14-09): publish PERFORMANCE.md from the approved local baseline (DOCS-06) |

## Known Stubs

None. The page publishes real approved numbers; no placeholder remains.

## Notes for the orchestrator

- STATE.md and ROADMAP.md were deliberately not touched.
- A baseline now exists, so perf runs gate instead of printing the D-13 report-only notice. Any future change to these numbers requires a fresh pass through the re-baseline ritual.
- The commit message bodies for `d7f9a68` were shortened after the tooling classifier rejected the longer versions; the full rationale lives in the code docstrings and in this SUMMARY.
