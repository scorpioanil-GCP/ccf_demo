---
phase: 17-client-access-ccf-client-and-the-transport-agnostic-first-ex
plan: 01
subsystem: tooling-and-gates
tags: [retirement-sweep, ci-gate, publish-scan, d-31, d-27, d-22]
requires: []
provides:
  - "a reproducible retirement sweep whose prune set is git's own ignore rules"
  - "a RETIREMENT_SCHEDULE naming Phase 17's condemned trees (wave 12, owner 17-08)"
  - "a current RETIREMENT-COUPLINGS.md — 227 rows / 69 files"
  - "make gate-tools, composed into make ci"
affects:
  - "17-08 — re-derives its retirement inventory from this sweep"
  - "every later Phase 17 plan — make ci now reaches tools/"
tech-stack:
  added: []
  patterns:
    - "ask git rather than maintain a second ignore-pattern parser"
key-files:
  created:
    - .planning/phases/17-.../deferred-items.md
  modified:
    - tools/retirement_sweep.py
    - docs/surface/examples/RETIREMENT-COUPLINGS.md
    - src/ccf/deployment/binder.py
    - src/ccf/halflife/assessment.py
    - src/ccf/halflife/debt.py
    - src/ccf/products/composition.py
    - src/ccf/products/request.py
    - Makefile
decisions:
  - "RETIREMENT_SCHEDULE wave integer continues the existing sequence (12) rather than restarting at Phase 17's own wave 6, because `wave` orders retirements against each other"
  - "ARTIFACT_DIRS demoted from authority to fast-prune/fallback; git check-ignore parity is now structural"
metrics:
  duration: ~75 min
  completed: 2026-08-15
---

# Phase 17 Plan 01: Retirement Sweep Repair and the tools/ Gate — Summary

Repaired the retirement sweep's reproducibility by pruning from git's own
ignore rules instead of a hand-maintained list, gave its schedule the trees
`17-08` will dispose of, cleared five whitepaper docstring leaks, and composed
the previously-invisible `tools/` suites into `make ci`.

**All three `tools/` suites are green: 544 passed / 0 failed (was 542 / 2).**

---

## Measurements

Every number below was taken in this session, in the worktree, with
`.venv/bin/python`. There is no bare `python` on PATH (`which python` → exit 1).

| Measurement | Before | After |
|---|---|---|
| `pytest tools/docs_tests tools/publish_scan_tests tools/lints/tests -q` | 2 failed, 542 passed | **544 passed, 0 failed** |
| `RETIREMENT-COUPLINGS.md` | 163 rows / 47 files | **227 rows / 69 files** |
| Files scanned by the sweep | — | 1633 |
| Two consecutive `--report` runs | — | **byte-identical** (empty `diff`) |
| Committed report vs fresh sweep | stale | **no diff** |
| `make lint` | 0 | **0** |
| `make typecheck` | 0 (196 files) | **0** (196 files) |
| `make gate-tools` | target did not exist | **0** |
| `make ci-core` | 3303 passed / **2 failed** / 118 skipped | 3303 passed / **2 failed** / 118 skipped |

The `ci-core` failures are **pre-existing and unrelated** — see Deviation 1.

---

## Deviations from Plan

### 1. `make ci-core` baseline was stale — 2 pre-existing failures (BLOCKING for the phase, not for this plan)

**Plan said:** *"`make ci-core` → 3305 passed / 118 skipped / 0 failed"*, measured
at `543eda0`, with the instruction *"If it does not, stop and dispute."*

**Measured, at `f1969c5` (phase-17 HEAD, my starting commit, before any of my
commits), via `git archive f1969c5` into a scratch tree so working-tree state
could not contaminate it:**

```
2 failed, 3 passed in 5.46s
FAILED tests/invariants/test_citation_coverage.py::test_the_unanchored_python_citation_population_cannot_regrow
FAILED tests/invariants/test_citation_coverage.py::test_the_held_back_thirteen_are_out_of_scope_by_ruling_not_by_accident
```

The identical two failures are present after my three commits; the full suite
reads 3303 passed / 2 failed / 118 skipped both before and after. **This plan
moves the number by zero.**

The offending citations live in files none of my commits touch
(`git diff f1969c5..HEAD --name-only` lists only the sweep, the report and the
five docstring modules). All three were introduced *after* the plan's baseline
commit `543eda0`, by `190d51b`, `f0467c1` and `0125c04`.

**Not fixed here, deliberately.** Both failures are ruling-scope questions, not
mechanical defects — the gate's own failure text says raising its ceiling
constant must be named in the commit message, and changing the held-back count
*"belongs in a decision entry, not in this constant."* Choosing either remedy
without a ruling is the ratchet-weakening these tests exist to prevent.
Logged as **DEF-17-01** in `deferred-items.md`; needs Dave or an owning plan.

### 2. The gitignore defect is real but reproduces via a different tree than the plan names

**Plan said:** the sweep reads gitignored `.superpowers/sdd/**`.

**Measured:** `.superpowers` is not gitignored in this repository at all —
absent from `.gitignore`, from `.git/info/exclude`, and from any
`core.excludesFile`; `git check-ignore` exits 1 on it. On a fresh worktree
`test_no_gitignored_path_reaches_the_report` **passes**, which is why the
opening baseline was 2 failed rather than the plan's 3.

**The underlying defect is real, and I reproduced it.** `ARTIFACT_DIRS` had
drifted from `.gitignore` by five entries — `.mypy_cache/`, `build/`, `dist/`,
`perf/results/` and `__pycache__/`, all gitignored, none pruned. Writing one
file to `perf/results/` (a directory the perf battery writes on every run) put
a row in the inventory and turned the test red:

```
AssertionError: the sweep read gitignored paths, so the inventory is not reproducible:
    perf/results/run.json
```

After the fix, the same reproduction passes. That is the control for Task 1:
a divergent subject passed into the real assertion, not an edit-and-revert.

**Note for later readers:** this test is *environment-dependent by
construction* — it only fires when a gitignored directory happens to exist and
happens to contain a retiring-path token. It was green on a clean checkout and
red on a developer machine. The fix makes the sweep and the gate consult the
same authority (git), so they can no longer drift.

### 3. Task 1's acceptance criterion `grep "superpowers" REPORT` returns nothing — rejected as a bad criterion

The regenerated report contains 10 rows from `docs/superpowers/**`. Measured:
those are **4 tracked, non-ignored files** (`git ls-files docs/superpowers/`
→ 4; `git check-ignore` → exit 1). They are legitimately part of the tracked
tree and their rows are correct documentary couplings — now correctly owned by
`17-08`, since the schedule names `s1-00`/`s1-01`.

The criterion conflated `docs/superpowers/` (tracked docs) with the
`.superpowers/` it believed was gitignored. Suppressing tracked files from the
inventory would defeat the sweep's purpose.

### 4. The report was regenerated in Task 1's commit, not Task 2's

Task 1's acceptance criterion requires
`pytest tools/docs_tests/test_retirement_sweep.py -q` to exit 0, but that suite
contains the freshness test, which cannot pass until the report is regenerated
— work the plan assigns to Task 2. The criterion is unsatisfiable in isolation.
Regenerating in Task 1 keeps every commit green; Task 2 re-verified it.

### 5. `make ci` cannot be observed failing *because of* `gate-tools` while `ci-core` is red

`ci: ci-core examples docs-strict gate-tools` — make runs prerequisites in
order, so a red `ci-core` (Deviation 1) aborts before `gate-tools` is reached.
Running plain `make ci` with the sabotage in place would have exited non-zero
for the *wrong reason* and produced a **vacuous** control.

Used `make -k ci` so the run reaches `gate-tools`. Both exit codes recorded
below, and the log confirms the failure is attributed to `gate-tools`, not to
`ci-core`.

---

## The Task 3 sabotage control — and the named exception

**This is Phase 17's single edit-and-revert control, and it is deliberate.**
Every other Phase 17 control passes a divergent subject *into* a
root-parameterized assertion function. This one cannot: its subject is a
**`make` target composition** — whether `ci` depends on `gate-tools` and
propagates its exit code. There is no root, no argument and no seam to
parameterize, because the thing under test is a dependency edge in a Makefile,
not a function. So it is a **one-time observation**, and **the durable half
ships separately** as the standing structural assertion
`command grep -n "gate-tools" Makefile`, which is what a later CI run
re-checks. Do not generalize the exception: if you reach for edit-and-revert on
a subject that is a function, the subject is parameterizable and you have not
yet found the parameter.

**Sabotage:** `assert False, "SABOTAGE 17-01 Task 3 ..."` prepended to
`tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current`.

| Observation | Exit code |
|---|---|
| `make gate-tools`, sabotage in place | **2** — named `test_the_committed_report_is_current` |
| `make -k ci`, sabotage in place | **2** — `make: *** [Makefile:107: gate-tools] Error 1`; `Target 'ci' not remade because of errors` |
| `make gate-tools`, after revert | **0** |
| `git status --porcelain tools/`, after revert | empty (clean) |

The `make -k ci` log names the sabotaged test at line 279–280 and attributes
the failure to `Makefile:107: gate-tools` (line 287) — distinct from the
pre-existing `Makefile:68: test` failure at line 132. The composition fires.

**Standing structural assertion (the durable half):**

```
28:.PHONY: help install lint typecheck test ci-core ci examples gate-tools \
89:ci: ci-core examples docs-strict gate-tools ## Full local reproduction of the always-on pipeline (D-10)
105:gate-tools: ## Run the tools/ suites CI runs that `testpaths` excludes from `make test`
```

**Unplanned bonus observation.** Adding `gate-tools` shifted Makefile line
numbers, which the committed report records. `make gate-tools` immediately went
red on its own inventory going stale — the composition catching a real coupling
before I had even sabotaged it.

---

## What changed

### Task 1 — sweep reproducibility and schedule (`20fc0a7`)

- **New `git_ignored_entries()`** runs
  `git ls-files -o -i --directory --exclude-standard` once, at `REPO_ROOT`, and
  `iter_source_files()` prunes directories and files against it. This is the
  same authority `test_no_gitignored_path_reaches_the_report` asserts against,
  so the walk and the gate cannot drift. Fails open (empty set) when git is
  absent or the tree is not a checkout — a reporting sweep should widen, not
  abort.
- **`ARTIFACT_DIRS` demoted** to a fast pre-prune and non-git fallback, and
  widened by the five drifted entries. Its `#:` doc now records the measured
  `perf/results/` reproduction rather than asserting the list is complete.
- **`RETIREMENT_SCHEDULE` gains a wave-12 block owned by `17-08`** with all
  five paths, each confirmed to exist first (`ls -d` on all five succeeded).
  Wave 12 continues the existing 8/10/11 sequence rather than restarting at
  Phase 17's own wave 6, because `wave` orders retirements against each other
  for `_first_break` and the cross-wave check, and these are disposed of after
  every Phase 16 wave. No existing entry renumbered.
- **Nothing deleted** — `git status --porcelain` showed no deletions; the
  removal is `17-08`'s, per D-31.

### Task 2 — docstring leaks (`044bcc0`)

Each of the five modules carried **one contiguous verbatim run**; the multiple
shingle hits per file were overlapping ten-word windows over that single span,
not separate leaks. Citation kept, argument kept, prose replaced:

| Module | Hits | The span |
|---|---:|---|
| `src/ccf/deployment/binder.py` | 7 | the `FreshnessSLA` gloss (§6.3, `:1453`) |
| `src/ccf/halflife/assessment.py` | 15 | the D_c sentence (§7.7, `:2696`) |
| `src/ccf/halflife/debt.py` | 14 | the same D_c sentence |
| `src/ccf/products/composition.py` | 3 | Temporal Validation's refusal (§6.4, `:1483`) |
| `src/ccf/products/request.py` | 1 | *not a quotation* — the author's own aggregate/assemble sentence colliding with a ten-word whitepaper run; reworded to break the run while keeping Chapter 1's distinction |

No threshold lowered, no allowlist entry, no docstring deleted.
`git diff --stat tools/publish_scan_tests/` is **empty**. All five retain their
`§` citations (counts: 5, 16, 9, 5, 5). No paraphrase tripped
`cinv01a-prompt-shape`, so the §6.3 exemption mechanics were not needed.

### Task 3 — the gate (`860a474`)

`gate-tools` runs `.github/workflows/ci.yml:35` and `:314` verbatim under
`$(ENV_DOCS)` (the suites import `tools.*`, so the repo root must be on
`PYTHONPATH`). Composed into `ci`. `DOCS-08` remains Pending and unclaimed.

---

## Environment note

The worktree was **103 commits behind `phase-17`** at spawn (0 ahead, clean) —
`git merge --ff-only phase-17` brought it current before any work. It also had
no `.venv`; symlinked to the main checkout's interpreter, which is invisible to
git (`.gitignore:15`) and resolves `ccf` to the **worktree's** `src` under
`PYTHONPATH=src:runtime` (verified: `ccf.__file__` points inside the worktree),
so no measurement here reflects the main checkout's tree.

---

## Success criteria

| Criterion | Status |
|---|---|
| `tools/` suites → 0 failed | **met** — 544 passed |
| `make ci-core` unchanged | **met** — 3303/2/118 before and after; the 2 are pre-existing (DEF-17-01) |
| `RETIREMENT_SCHEDULE` names `s1-00` and `s1-01` | **met** — grep count 2 |
| Committed report equals a fresh sweep; two sweeps byte-identical | **met** — both diffs empty |
| `make ci` fails when a `tools/` test fails — observed | **met** — via `make -k ci`, exit 2 at `Makefile:107` |
| No example tree moved or deleted | **met** — no deletions in any commit |

---

## Known Stubs

None.

## Threat Flags

None. The plan's `T-17-01` (docstring disclosure), `T-17-02` (inventory
repudiation) and `T-17-03` (gate under-reporting) are all mitigated as
specified, each with a standing gate and none weakened.

## Self-Check: PASSED

- `tools/retirement_sweep.py` — FOUND
- `docs/surface/examples/RETIREMENT-COUPLINGS.md` — FOUND
- `Makefile` — FOUND
- `.planning/phases/17-.../deferred-items.md` — FOUND
- five `src/ccf/**` modules — FOUND
- commits `20fc0a7`, `044bcc0`, `860a474` — FOUND in `git log`
