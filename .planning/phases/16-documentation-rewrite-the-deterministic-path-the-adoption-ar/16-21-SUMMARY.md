---
phase: 16-documentation-rewrite-the-deterministic-path-the-adoption-ar
plan: 21
subsystem: testing
tags: [retirement-sweep, coupling-inventory, ast, gate, docs-17, python]

# Dependency graph
requires:
  - phase: 16-01
    provides: "the phase's scope rulings (D-IMPL-94) and the retirement schedule the sweep's owner map is derived from"
provides:
  - "tools/retirement_sweep.py — a re-runnable repo-wide sweep for live couplings to every path this phase retires, in all five shapes they take"
  - "docs/surface/examples/RETIREMENT-COUPLINGS.md — the checked-in inventory, 148 rows across 38 files, one owning plan per row, none unowned"
  - "tools/docs_tests/test_retirement_sweep.py — the standing gate over the sweep: CWD-independence, non-vacuity, both filter polarities, all four no-path-token shapes on synthetic modules, and the committed report matching a fresh render"
affects: [16-15, 16-17, 16-18, 16-02, 16-04, 16-12]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Detector-per-coupling-shape sweep with the target list, exclusions and owner overrides as module-level data"
    - "Empirical witness measurement: the module's own enumeration helper is restricted to one retiring path at a time and the assertion is executed, rather than inferred from a token"
    - "Classify-don't-drop liveness: live / documentary / survives, all three owned"

key-files:
  created:
    - tools/retirement_sweep.py
    - tools/docs_tests/test_retirement_sweep.py
    - docs/surface/examples/RETIREMENT-COUPLINGS.md
  modified: []

key-decisions:
  - "A hit inside a docstring or a comment is classified `documentary` and still gets a row and an owner, rather than being dropped — four of the fourteen files the sweep is required to find carry only hits of that shape, and each is already in an owning plan's files_modified"
  - "The owner of a count coupling is the plan retiring the LAST witness (the plan after which the floor takes its final value); the wave at which the floor FIRST breaks is measured separately and recorded in the row, because those are different questions and only reporting the first would mislead the last"
  - "tools/retirement_sweep.py excludes itself from assignment: its schedule names every retiring path by construction and must keep naming them, or the re-runs waves 8, 10 and 11 depend on stop being possible"
  - "Append-only records (.planning/, the decision log, per-phase gate records, per-plan surface-change records, the frozen ERGO-03 baselines) and CLAUDE.md are measured with hit counts but not assigned, via a named constant with a per-entry reason"
  - "The scanned-file count is deliberately absent from the report body, so an unrelated file addition does not make the inventory stale while a coupling change does"

patterns-established:
  - "Reachable-by-construction gate failure: the owner map has no fallback, so extending RETIREMENT_SCHEDULE's target list without assigning an owner produces an unowned row and a non-zero exit"
  - "Synthetic-tree shape proofs: every detector accepts an optional root so each coupling shape is proven under tmp_path rather than only observed at HEAD"
  - "Gate fixtures derive their paths from the schedule under test, so the gate contributes no rows to the sweep it gates"

requirements-completed: [DOCS-17]

# Metrics
duration: 78min
completed: 2026-08-10
---

# Phase 16 Plan 21: Repo-Wide Retirement Coupling Sweep Summary

**A re-runnable sweep measures 148 live couplings to the ten retiring examples and two published pages across the whole repository — 70 of them outside the three trees the phase's research inventory swept — assigns every one to an owning plan, and is itself gated for CWD-independence, non-vacuity, filter polarity and coverage of all four no-path-token shapes.**

## Performance

- **Duration:** ~78 min
- **Started:** 2026-08-10T00:00:00Z (worktree spawn)
- **Completed:** 2026-08-10
- **Tasks:** 1/1
- **Files created:** 3

## Accomplishments

### `tools/retirement_sweep.py` — five detectors, not one

The target list is `RETIREMENT_SCHEDULE`, a module-level tuple of
`Retirement(path, owner, wave)` covering the ten retiring example
directories, the twelve `tests/examples/` modules that retire with them, and
the two published pages. A later plan extends it without touching the walk —
and if it extends the target list without assigning an owner, the row comes
out unowned and the sweep exits non-zero, which is the safety property.

1. **Path tokens.** Python is read with `ast`. A `/`-chain such as
   `Path(__file__).resolve().parents[3] / "examples" / "04-cross-process"` is
   reconstructed and matched, so a *constructed* path is not invisible.
   Everything else is a line-oriented token pass, labelled coarser in the
   module docstring and in the report.
2. **Count constants** — a module-level `MINIMUM_*` integer compared against
   `len(<scan>())` in a test body. Four found.
3. **Count scan functions** — the scan each floor bounds. Four found.
4. **Inline tree-witness assertions** — an assertion whose scan is written
   inline in a test body over a module-level scanned-tree tuple, with neither
   a floor constant nor a floor-backed scan function. One found, and its
   witness count is measured *by execution*: the module's own
   `_python_sources` is restricted to one retiring path at a time and the
   test is run. This is the only method that works, because the witness path
   appears in that module only inside a docstring, which the sweep's own
   liveness filter correctly classifies as not-live.
5. **Indirect executions** — a test under `tests/` that runs a suite, script
   or module outside `tests/` which resolves a retiring path. One found.

### The inventory

`docs/surface/examples/RETIREMENT-COUPLINGS.md`, byte-deterministic across
runs, no timestamps, no absolute paths.

| Measure | Value |
| --- | --- |
| Coupling rows | **148** |
| Files carrying at least one row | **38** |
| Rows outside `examples/`, `tests/examples/` and `public/` | **70**, across **21** files |
| Rows with no owning plan | **0** |
| Owners | 16-02 (13), 16-15 (21), 16-17 (30), 16-18 (84) |

All **fourteen** known-instance files from the plan's floor list are present,
at the exact lines the plan cites — including
`tests/conformance/test_harness_portability.py:58`,
`tests/conformance/test_a3_discharge.py:31`, `perf/suites/common.py:140`,
`tools/publish_scan_tests/test_publish_scan.py:180` and
`tests/cli/test_schema_export.py:60`.

The two rows the acceptance criteria single out:

- `tests/products/test_gate_two_call_shape.py:3139` —
  `inline-tree-witness`, witnesses **1**, sustained only by
  `examples/03-harness-portability`, owner **16-15** (wave 8), three waves
  earlier than the `MINIMUM_*` rows in the same file.
- `tests/perf_smoke/test_smoke.py:71` — `indirect-execution`, retiring path
  `examples/04-cross-process`, intermediate
  `perf/suites/crossproc/conftest.py`, owner **16-17** (wave 10). Filed
  against the test rather than the conftest, because the test is what
  `make ci` runs and where the build actually goes red.

### The gate — 22 tests

`tools/docs_tests/test_retirement_sweep.py` asserts the walk reads a
non-empty tree; that the sweep finds couplings at HEAD; that all fourteen
known files are found; that coverage is repo-wide; that both
`iter_source_files()` and the whole `sweep()` are byte-identical after
`monkeypatch.chdir(tmp_path)` (WR-04's exact failure); both docstring-filter
polarities on synthetic modules; **all four** no-path-token shapes on
synthetic `tmp_path` fixtures — including a shape-4 fixture whose two files
are asserted to carry no retiring-path token at all, so the fixture cannot
silently degrade into a token test; the negative case for shape 3 (an
assertion with headroom outside every retiring path is *not* a coupling);
zero unowned rows in both the sweep and the committed file; render
determinism; and that the committed report equals a fresh render, which is
what makes `--report && git diff` a usable gate for waves 8, 10 and 11.

The gate's synthetic fixtures build their paths out of `RETIREMENT_SCHEDULE`
rather than writing them as literals, so the gate contributes no rows to the
sweep it gates and cannot drift from the schedule it tests against.

## Findings beyond the hand-assembled floor

The plan called the fourteen-file list a floor, not a ceiling. Two rows it did
not carry:

**1. `tools/docs_tests/test_snippet_gate.py:39` — a fifth
`path-construction` coupling.** `SNIPPET_SOURCE = REPO_ROOT / "examples" /
"00-quickstart" / "run.py"`. Segmented, so a token pass over the file finds
nothing. Owner **16-18**, which already names the file in its
`files_modified` — so the schedule anticipated it even though the coupling
inventory had not measured it.

**2. All three `test_gate_two_call_shape.py` floors first go red at wave 8,
not wave 11.** Measured at HEAD:

| Floor | Value | Witnesses | Headroom | First break |
| --- | ---: | ---: | ---: | --- |
| `MINIMUM_GATE_CALL_SITES` | 9 | 9 | 0 | wave 8 (16-15) |
| `MINIMUM_PROJECTING_BODIES` | 11 | 11 | 0 | wave 8 (16-15) |
| `MINIMUM_RESOLVED_BINDER_SITES` | 11 | 11 | 0 | wave 8 (16-15) |
| `MINIMUM_IMPLEMENTATIONS` | 9 | 11 | 2 | wave 10 (16-17) |

Every witness of all four lies under a retiring example; none lies under
`src/` or `runtime/`. Deleting `examples/03-harness-portability` at wave 8
takes the first three from 9→8, 11→10 and 11→10 — below their floors. This
does **not** contradict the schedule owner (16-18 is the plan after which the
floors take their final value, and D-IMPL-94 limb 1 authorises the
re-flooring), and 16-15 already carries
`tests/products/test_gate_two_call_shape.py` in its `files_modified`. But
16-15 must now expect to re-floor, not only to retire the inline
tree-witness assertion. The number is measured on the tree *as it stands*:
waves 3-7 create new examples which may restore witnesses, which is precisely
why 16-15, 16-17 and 16-18 re-run the sweep rather than reading this snapshot.
Both facts are carried in the report's `Note` column on every count row.

## Deviations from Plan

### 1. [Rule 3 - Blocking] The docstring filter classifies rather than drops

- **Found during:** Task 1, while checking the fourteen-file floor against
  the tree.
- **Issue:** The plan specifies that a hit inside a docstring or on a comment
  line is "not a coupling" and that the gate must show a synthetic docstring
  module yielding *no row*. Measured against the tree, four of the fourteen
  files the same plan requires by name carry **only** docstring/comment hits:
  `tests/conformance/test_harness_portability.py` (58, 76),
  `tests/conformance/test_a3_discharge.py` (31), `perf/suites/common.py`
  (140) and `perf/synth/artifacts/controlplane.yaml` (3, a `#` comment). A
  filter that dropped them could not satisfy the fourteen-file criterion.
- **Fix:** Liveness became a three-valued classification —
  `live` / `documentary` / `survives` — carried in its own column. Documentary
  rows get an owner; the severity distinction lives in the column, which is
  what the distinction is for. Each of the four files is already named in an
  owning plan's `files_modified` (16-15 owns both conformance modules; 16-17
  owns `perf/suites/common.py` and `perf/synth/artifacts/controlplane.yaml`),
  so the classification agrees with work three plans have already accepted.
  The gate's polarity test asserts the strict property that matters: a
  docstring hit yields **no `live` row**, and the identical string in a
  `pathlib.Path(...)` call yields exactly one.
- **Files:** `tools/retirement_sweep.py`,
  `tools/docs_tests/test_retirement_sweep.py`
- **Commit:** 21d9c45

### 2. [Rule 2 - Missing critical functionality] Scope exclusions are named data with reasons

- **Found during:** Task 1, first full run.
- **Issue:** A literal repo-wide walk assigns owners to `.planning/`,
  `docs/DECISIONS.md`, the four per-phase gate records, the twelve per-plan
  surface-change records, the 44 frozen ERGO-03 measurement fragments and
  `CLAUDE.md`. Every one is an append-only record that names retiring paths as
  *history*, or the project charter that no plan may edit. Assigning them
  would have told 16-18 to rewrite the decision log.
- **Fix:** `EXCLUDED_FROM_ASSIGNMENT`, a module-level tuple of
  `(prefix, reason)`. Excluded files are still measured; their hit counts and
  reasons appear in a **Measured but not assigned** section of the report, so
  the exclusion is a decision on the record rather than a silence. This is a
  scope decision, not row-closing: no row is removed from the inventory table,
  and the unowned disposition remains the only way a row closes without an
  owner (and it fires as a non-zero exit).
- **Files:** `tools/retirement_sweep.py`
- **Commit:** 21d9c45

### 3. [Rule 1 - Bug] The sweep detected itself, and its own schedule

- **Found during:** Task 1, after the first refactor changed the file's line
  numbers and the report churned.
- **Issue:** `RETIREMENT_SCHEDULE` names all 24 retiring paths as string
  literals, so the sweep filed 25 rows against itself telling 16-15/16-17/16-18
  to edit the schedule — which is exactly what they must not do, since the
  schedule has to keep naming what was retired for the re-runs to work. It
  also made the report churn on any line-number shift in the tool.
- **Fix:** `tools/retirement_sweep.py` is an entry in
  `EXCLUDED_FROM_ASSIGNMENT` with that reason stated. The gate module avoids
  the same problem structurally instead, by deriving its fixture paths from
  the schedule rather than writing literals.
- **Files:** `tools/retirement_sweep.py`
- **Commit:** 21d9c45

### 4. [Rule 1 - Bug] Two false-positive classes in the first implementation

- **Found during:** Task 1, reviewing the first generated report.
- **Issue:** (a) The indirect-execution detector walked *up* to the nearest
  existing parent directory when an import or argv token did not resolve, so
  every `perf.synth.*` import became a claim on `perf/suites/crossproc` and
  every `tools.*` import a claim on `tools/docs_tests/test_snippet_gate.py` —
  six spurious rows. (b) A multi-line string constant was reported at the line
  the quotes open, so a docstring hit sixty lines in was filed at line 1 and
  only the first occurrence in each constant was reported at all.
- **Fix:** (a) Resolution is now exact — the token must name an existing
  directory or module, with the failure recorded in the function docstring.
  (b) Every occurrence is reported, at
  `node.lineno + value.count("\\n", 0, index)`. Both fixes are what make the
  report's line numbers match the plan's citations exactly.
- **Files:** `tools/retirement_sweep.py`
- **Commit:** 21d9c45

### 5. [Rule 3 - Blocking] The report no longer records the scanned-file count

- **Found during:** Task 1, writing the "committed report is current" gate.
- **Issue:** Recording the exact number of files walked made the inventory
  stale — and `make ci` red — every time *any* unrelated file was added to
  the repository, including by the three plans executing in parallel.
- **Fix:** The count is printed by the command and asserted by the gate
  (`> 100` files, non-empty coupling set), but is not in the report body. What
  makes the report stale is a change to a coupling, which is what later waves
  must re-measure. The reason is stated in the report's own Summary section.
- **Files:** `tools/retirement_sweep.py`
- **Commit:** 21d9c45

## Verification

| Check | Result |
| --- | --- |
| `tools/retirement_sweep.py --report` exit code | 0 |
| Two consecutive `--report` runs byte-identical | yes (`diff -q` clean) |
| Fourteen known-instance files present | 14/14 |
| `grep -c "inline-tree-witness"` | 2 (shape table + row) |
| `grep -c "indirect-execution"` | 2 (shape table + row) |
| `grep -c "UNASSIGNED"` | **0** |
| Rows outside the three swept trees | 70 across 21 files |
| `pytest tools/docs_tests/test_retirement_sweep.py -q` | 22 passed |
| `python -m tools.lints --all` | exit 0, no findings |
| `python -m mypy` (project scope) | Success, 186 files |
| `mypy --strict` on the two new modules | Success, 0 errors |
| `git diff --stat -- src/ runtime/` | empty |
| `git status --porcelain` | only this task's three files |

## Deferred Issues

Three pre-existing failures in the gate-checker suites, confirmed to predate
this plan (`git status` shows no modification to any tracked file) and already
owned:

- `tools/publish_scan_tests/test_docstring_leaks.py::test_no_docstring_reproduces_whitepaper_body_text`
  — the 20 shingle hits against `ProductClassDeclaration`. Owner **16-04**
  under D-IMPL-94 / D-13's single enumerated exception.
- `tools/docs_tests/test_snippet_gate.py::test_the_unmodified_source_builds_clean`
  and `::test_a_deleted_section_marker_fails_the_strict_build` — a missing
  `ontology` snippet section. Owner **16-04** under D-IMPL-94 Q-8, which
  commits `make ci` to gaining these three suites once they are green.

Not fixed here: out of this plan's scope boundary, and 16-04 is executing in
parallel on exactly these files.

## Notes for the next plans

- **16-15 (wave 8)** owns 21 rows. Beyond the inline tree-witness assertion it
  already expects, the three `test_gate_two_call_shape.py` floors are measured
  at zero headroom with a witness under `examples/03-harness-portability` —
  re-run the sweep before deleting and read the `Note` column.
- **16-17 (wave 10)** owns 30 rows, including the always-on
  `tests/perf_smoke/test_smoke.py` indirect execution. Its `files_modified`
  does not list that file; the row records why it is filed there anyway.
- **16-18 (wave 11)** owns 84 rows, including
  `tools/docs_tests/test_snippet_gate.py:39` — already in its
  `files_modified`, now measured.
- **16-12** owns the `Makefile` composition that puts `tools/docs_tests` into
  `make ci`; this gate joins the always-on path there.
- Re-run with
  `PYTHONPATH=.:src:runtime .venv/bin/python tools/retirement_sweep.py --report`
  and diff. `test_the_committed_report_is_current` fails on a stale snapshot,
  so the diff is enforced rather than remembered.

## Self-Check: PASSED

- `tools/retirement_sweep.py` — FOUND
- `tools/docs_tests/test_retirement_sweep.py` — FOUND
- `docs/surface/examples/RETIREMENT-COUPLINGS.md` — FOUND
- Commit `21d9c45` — FOUND
