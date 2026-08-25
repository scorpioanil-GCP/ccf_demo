---
phase: 23-the-archive-move-retiring-the-ten-condemned-example-trees-wi
plan: 10
subsystem: the retirement sweep re-pointed at the archive, and the control that stops it going blind
tags: [DOCS-17, D-IMPL-195, D-IMPL-191, D-IMPL-196, D-IMPL-198, D-05, criterion-9, criterion-10, retirement-schedule]
requires:
  - 23-04 (the move; the ten trees' new owner)
  - 23-01 (Dave's fourteen-row ruling, recorded verbatim)
provides:
  - a Retirement table pointing at the archive and owned by live Phase 23 plans
  - an assertion that every scheduled path resolves on disk
  - an assertion that the sweep's row set actually reaches the archive
  - two-spelling matching, so a moved tree cannot lose its pre-move references
affects:
  - tools/retirement_sweep.py
  - tools/docs_tests/test_retirement_sweep.py
tech-stack:
  added: []
  patterns:
    - predicate-takes-its-subject-as-an-argument (so a control can point it at a synthetic input)
    - anti-vacuity clause INSIDE the predicate, never in the caller
    - one clause per failure mode; a second clause kept for the look of it is removed
key-files:
  created: []
  modified:
    - tools/retirement_sweep.py
    - tools/docs_tests/test_retirement_sweep.py
    - .planning/phases/23-.../deferred-items.md
decisions:
  - "Owners: the ten moved trees -> 23-04 (the plan that moved them); the fourteen unmoved rows -> 23-10 (the single named archive-quarantine owner D-IMPL-195 ruling 2 permits). Deletion remains OWED for all twenty-four."
  - "Wave integers UNCHANGED at 8/10/11/12 — the relative order did not change, and renumbering risks the same import-time StopIteration class the re-point itself risked."
  - "The WAVE_* predicate was WIDENED (examples/ kept, archive/examples/ added) rather than re-derived from the owner — the s1 rows still live under examples/ and a future unmoved row at waves 8/10/11 must not re-break collection."
  - "S-13c answered by measurement: the two assertions are NOT redundant. Narrowing the walk root separates them."
  - "S-16v(c) found a redundant clause in this plan's own work; it was removed, not kept."
metrics:
  duration: one session
  completed: 2026-08-24
  commits: 3 (2 task + 1 report regeneration after the SUMMARY)
---

# Phase 23 Plan 10: The Table Points At The Archive, And The Sweep Can No Longer Lose It — Summary

Re-pointed the retirement schedule at `archive/examples/…` and owned it to live
Phase 23 plans; disarmed the import-time trap **before** the re-point could fire
it; and closed criterion 10 with two assertions aimed at the exact gap the
researcher named — a schedule that has gone stale about the tree while the tool
reports a confident total at exit 0.

**Everything below is MEASURED in this session. No figure is inherited from the
plan text, from a decision entry, or from a prior wave's summary.**

---

## What criterion 10's gap actually was, reproduced before it was closed

S-13, run against the module as task 1 left it and **before** task 2's
assertions existed:

- revert the ten rows' `path` to their old `examples/…` spelling, change
  nothing else
- the sweep prints **384 coupling rows across 117 files at EXIT 0** over ten
  directories that are not on disk
- **46 of the module's 47 tests PASS**

The one red was `test_the_committed_report_is_current`, and it is *not* a
catcher here: it is red whenever the report has not been regenerated, so it
cannot tell a stale schedule from a stale snapshot. Nothing else looked.

After task 2, the same mutation is caught twice and named ten times:

```
AssertionError: the schedule is SILENT about the archive — no path under
archive/examples/ — a resolution check whose subject set contains no moved tree
cannot demonstrate the property it was written for …;
examples/03-harness-portability is scheduled (owner 23-04, wave 8) and is NOT on disk;
examples/04-cross-process is scheduled (owner 23-04, wave 10) and is NOT on disk;
…  [all ten, each with its owner and wave]
```

---

## Task 1 — the table

**Commit `b6ecc05`.**

### The import-time repair went FIRST, and the trap was watched firing

Watched, in this order, before any fix:

| Measurement | PHASE_BASE (`b87fe58`) | Ten paths re-pointed, predicate untouched |
| --- | --- | --- |
| `pytest test_retirement_sweep.py --collect-only -q` | **47 tests collected** | **0 tests collected, 1 error** (`StopIteration` at line 86) |
| pytest exit code | 0 | **2** |
| `pytest tools/docs_tests -q` | 276 collected | **`Interrupted: 1 error during collection`, `1 error in 0.54s`** |

**A correction to the plan's prediction, recorded rather than smoothed over.**
The plan warned that *"the danger is that a summary line reads as clean."* On
this host it does not: pytest INTERRUPTS at exit 2. The real danger is the
adjacent one — the other **275** tests in `tools/docs_tests` also did not run,
and the tail of that output shows `1 error` and **no failures**, which is what a
reader scanning for `FAILED` will find.

**Approach chosen:** widen the predicate. `EXAMPLE_DIR_PREFIXES = ("examples/",
"archive/examples/")`, consumed by a new `_example_dir_for_wave(wave)` helper.
`examples/` is **kept**, not replaced, for two stated reasons: the five `17-08`
`s1` rows still live under `examples/` (`D-05`), and a later wave adding an
unmoved tree at waves 8/10/11 must not re-break collection. The alternative —
re-deriving the three fixtures from the owner — was rejected because it couples
a *fixture* to an *ownership* decision that `D-IMPL-195` ruling 2 shows is
exactly the field most likely to be re-ruled.

### The re-point

Ten rows now name `archive/examples/…` and are owned by **`23-04`**, the plan
that performed the move. The fourteen rows that did NOT move — twelve
`tests/examples/` modules and `public/tutorial/adopters-guide.md` and
`public/tutorial/demo-walkthrough.md` — are owned by **`23-10`**, this plan, as
the *single named archive-quarantine plan id* `D-IMPL-195` ruling 2 permits.
Dave's ruling, applied exactly as selected and not re-asked: *"Blind or 'owner =
abandoned plan' is worse than an honest Phase 23 owner. Same rule as the sweep
table: archived path still counts."* **Deletion remains OWED for all
twenty-four rows**; re-pointing an owner discharges nothing, and this is stated
in the constant's own comment rather than only here.

**Wave integers UNCHANGED at 8, 10, 11, 12**, with the reason recorded in the
comment: the field orders retirements against each other for `_first_break` and
the cross-wave check, the relative order of these rows did not change, and
renumbering would alter that ordering for no gain while risking the same
`StopIteration` class. The comment also records that the wave integers no longer
track the retired Phase 16 plan numbering — and did not before this re-point
either, since wave 12 already belonged to Phase 17.

**The five `17-08` rows are byte-identical to `PHASE_BASE`**, proven rather than
asserted:

```
$ diff <(git show b87fe58:tools/retirement_sweep.py | grep '17-08') \
       <(grep '17-08' tools/retirement_sweep.py)
$ echo $?
0
```

**Every one of the 29 scheduled paths was checked to exist on disk before being
listed** — and, per task 2, is now asserted to.

### Two defects the re-point itself produced, both caught by this module's own floors

Neither was found by reading. Both are recorded because a plan that only reports
what it intended did not look.

**(1) `tools/measure_examples.py` dropped off `KNOWN_COUPLED_FILES`.**
`test_every_known_coupled_file_is_found` went red naming exactly one file. Its
three rows — lines 261, 308 and 320, **two of them `live`** argparse help
strings — spell `examples/01-agent-basics` and `examples/00-quickstart`. Those
references did not stop existing and did not stop being coupled to the tree; the
tree moved out from under a spelling nobody re-pointed. **The floor was not
edited.** Closed instead with `Retirement.former_path`: a moved tree is matched
at BOTH spellings, for lookup (`retiring_paths`, `_entry_for`) only, never for
containment (`containing_retirement` still asks only about `path`, because
nothing lives at the former location).

Measured consequence: **45 coupling rows across 20 files** name a former
spelling. Every one is a real old-form reference that the re-point alone would
have made invisible at exit 0.

**(2) Two spellings of one tree DOUBLE-COUNTED.** `archive/examples/04-cross-process`
*contains* `examples/04-cross-process`, so both matched the same characters.
Measured: the two synthetic single-reference fixtures each returned **2 rows
where they assert 1**, and the repo-wide total read **315**. `text_hits` has
carried a substring-suppression rule since it was written; `python_hits` never
needed one until now. Added there, longest-first so the longer spelling is filed
and the shorter suppressed.

**Also repaired:** `test_shape_4_the_indirect_execution_is_detected` built its
synthetic runner as `parents[1] / seg[0] / seg[1]` — a silent two-segment
assumption. With a three-segment retiring path it built `archive/examples`,
which retires nothing, and the test failed **on its own fixture** (`0 == 1`)
rather than on the detector. It now joins every segment, at the column the
enclosing `textwrap.dedent` requires.

### Task 1 sabotage log

Every mutation restored byte-identically and confirmed with `cmp` against a
copy held outside the tree.

| # | Mutation | Prediction | Observed | Verdict |
| --- | --- | --- | --- | --- |
| S-W1 | re-point paths, revert the `WAVE_*` predicate | `StopIteration` at collection; module collects 0 | **0 collected, 1 error, pytest exit 2**; whole `tools/docs_tests` run interrupted | **CAUGHT**, prediction corrected: loud, not silent — but it takes 275 other tests with it |
| S-10 | delete the `archive/examples/02-skilling` row | report-currency sees a row-count drop; floor *may* fire | **1 failed / 46 passed** — report currency only; floor did NOT fire | **CAUGHT**. Correction: the count went **UP**, not down — files inside a de-scheduled tree stop being deleted-with-their-source, so their references become rows |
| S-11 | narrow the walk root to `src/ccf/graph` | `test_the_sweep_finds_couplings_at_head` and `test_the_coverage_is_repo_wide` fail | **5 failed / 42 passed**: walk floor, known-coupled floor, repo-wide coverage, two-owner check, report currency. **`test_the_sweep_finds_couplings_at_head` PASSED** | **CAUGHT — by different tests than predicted.** The couplings floor survives because `count_coupling_rows`, `inline_tree_witness_rows` and `indirect_execution_rows` append independently of the walk |
| S-12 | `RETIREMENT_SCHEDULE = ()` | walk floor PASSES, couplings floor FAILS | **the module does not COLLECT** (`StopIteration`), so neither floor can be observed through pytest. Observed in-process instead: walk floor **passes** (1937 > 100), couplings floor **fails** (0 rows) | **PREDICTION WRONG in form, right in substance.** The distinction the plan asked me to record is real but only visible in-process — which is precisely why task 2's controls use a SYNTHETIC schedule rather than mutating the real one |

---

## Task 2 — criterion 10's control

**Commit `1e33b47`.**

Two predicates, each taking its subject as an **argument** so a control can
point it at a synthetic input, and each with its anti-vacuity clause **inside**
the predicate rather than in the caller.

**`scheduled_path_problems(schedule)`** — the schedule's own comment, quoted in
the docstring so the assertion is visibly that comment's enforcement rather than
a new rule: *"Each path was confirmed to exist before being listed — the
unowned-row gate is fail-closed, and a schedule naming a path that is not there
is the same class of defect as one that omits a path."* Three clauses:

1. the schedule names no archived tree (the **silence** case — a table that
   stops naming ten directories reports clean about them just as effectively as
   one that names them wrongly, and clause 2 alone would be satisfied by
   deleting the ten rows outright);
2. a scheduled `path` that does not exist;
3. a `former_path` that **does** exist — the row has stopped describing the
   tree, either because the move was undone or because the field was
   "corrected" to a live path.

**`archive_sweep_problems(schedule, rows)`** — `D-IMPL-191` ruling 3 says an
archived path continues to count; this asserts the walk actually reaches it. The
floor is tied to the schedule (`len(archive_rows) >= len(archived)`), never to a
constant. Measured at the time of writing: **131 rows** name an archived path,
**all ten** archived trees are named, against a floor of **ten**. Per-tree
coverage is recorded, not asserted — a tree whose last reference is legitimately
discharged should not turn this red.

### S-13c, answered by measurement rather than argument

The plan asked whether assertion (2) is redundant once (1) exists, and said to
record the answer either way. **It is not redundant**, and the proof is a
mutation that separates them:

| Mutation | assertion (1) resolution | assertion (2) archive-swept |
| --- | --- | --- |
| S-13 — ten rows reverted to the old spelling | **FAILS**, naming all ten | **FAILS** on the silence clause |
| S-13b — one row to `archive/examples/00-quickstart-old` | **FAILS**, naming that one | passes |
| walk root narrowed to `src/` | **passes** — the table is still correct | **FAILS**: `2 coupling rows … against 10 archived trees` |

One is about the **table**, the other about the **walk**. Only the third row of
that table shows it, and it would not have been found by reasoning about the
predicates.

### The redundancy the sabotage DID find — in this plan's own work

**S-16v(c):** deleted the `if not schedule` early return from
`archive_sweep_problems` and **every control stayed GREEN**. An empty schedule
contains no archived path either, so the emptiness guard was detecting nothing
the next clause was not already detecting. A second check kept for the look of
it, shipped inside the plan that forbids exactly that.

Both predicates' copies were collapsed into `_no_archived_tree(schedule)` — one
clause, two diagnoses — because *"empty"* and *"names only survivors"* are
different states to find a schedule in and send a reader to different places.
Re-run afterwards, each disarming reddens exactly its own case:

| # | Mutation | Observed |
| --- | --- | --- |
| S-16v(a2) | remove the no-archived-tree clause from `scheduled_path_problems` | **2 failed** — the EMPTY case and the s1-ONLY case, and nothing else |
| S-16v(c2) | remove it from `archive_sweep_problems` | **2 failed** — the EMPTY case and the s1-ONLY case |
| S-16v(d) | collapse `_no_archived_tree`'s two messages into one | **2 failed** — both EMPTY cases, proving the two-message shape is load-bearing rather than decorative |
| S-13d | weaken the floor from `len(archived)` to a constant `1` | **1 failed** — only the ONE-STRAY-ROW case | 

**S-13d is what makes the floor a floor.** The ONE-STRAY-ROW control (one
archive row against ten scheduled archived trees) was added *because* a `>= 1`
assertion would otherwise have passed every control in the module while nine of
the ten trees went unseen. Both controls assert the message **fragment**, not
merely that some problem was reported: four clauses sharing one `assert
problems` is four clauses of which any one may have silently stopped working.

**One artefact worth naming:** under S-13, a third test also reddened —
`test_control_the_resolution_check_refuses_a_broken_schedule[a former_path that
resolves …]`. With the ten rows' `path` reverted to equal their `former_path`,
the control's synthetic setup no longer produces a distinguishable case. That is
the sabotage disturbing the control's fixture, not the control failing to work.

---

## Criterion 7 — the accounted delta (`D-IMPL-196`, amended by `D-IMPL-198`)

**Node ids LOST against `PHASE_BASE`: ZERO.** Measured by collecting the module
at `b87fe58` (both files restored from git, collected, restored from copies held
outside the tree) and `comm`-ing the sorted node-id sets:

```
base=47  head=57
LOST (in base, not at head):   (empty)
```

**Ten node ids ADDED, every one named.** Four new `def test_`, of which two are
parametrized:

| Node id | What it is |
| --- | --- |
| `test_every_scheduled_path_resolves_on_disk` | criterion 10 assertion (1) |
| `test_the_sweep_reaches_the_archive` | criterion 10 assertion (2) |
| `test_control_the_resolution_check_refuses_a_broken_schedule[an EMPTY schedule … -tuple-EMPTY]` | non-vacuity: empty schedule |
| `test_control_the_resolution_check_refuses_a_broken_schedule[an s1-ONLY schedule … -_s1_only_schedule-SILENT]` | non-vacuity: the silence case |
| `test_control_the_resolution_check_refuses_a_broken_schedule[one archived path re-pointed to a near miss-_one_missing_path_schedule-NOT on disk]` | S-13b's shape, as a standing control |
| `test_control_the_resolution_check_refuses_a_broken_schedule[a former_path that resolves … -_former_path_resolves_schedule-pre-move spelling]` | clause 3 |
| `test_control_the_archive_sweep_check_refuses_a_blind_sweep[an EMPTY schedule … -tuple-head-EMPTY]` | non-vacuity: empty schedule |
| `test_control_the_archive_sweep_check_refuses_a_blind_sweep[an s1-ONLY schedule … -_s1_only_schedule-head-SILENT]` | non-vacuity: the silence case |
| `test_control_the_archive_sweep_check_refuses_a_blind_sweep[a sweep that produced no rows at all-<lambda>-none-did not look at]` | real schedule, empty row set |
| `test_control_the_archive_sweep_check_refuses_a_blind_sweep[ONE stray archive row against ten scheduled archived trees-<lambda>-one-against 10 archived trees]` | the floor is TIED to the schedule (S-13d) |

**Zero tests removed.** `diff` of the `def test_` name lists between
`PHASE_BASE` and `HEAD` shows four additions and no deletions.

**`tests/examples` collects 521** — unchanged, and this plan wrote nothing under
`tests/`.

**Note on the plan's task-1 done criterion.** It required the collected count to
be *identical* to `PHASE_BASE`. After task 1 alone it **was 47**, measured. Task
2 adds guards deliberately, which is what `D-IMPL-196` replaced the absolute pin
to permit; the accounted-delta form is what is discharged here.

---

## Measurements at the close

All in the venv (`D-19`, criterion 13), all re-run after the last commit.

| Measurement | Before (`72bb32c`) | After |
| --- | --- | --- |
| Coupling rows / files / files scanned | 384 / 117 / 1937 | **270 / 83 / 1937** |
| Rows outside the three swept trees | 256 across 86 | **142 across 52** |
| Hits dropped as deleted-with-their-source | 134 | **248** |
| Rows naming an `archive/examples/…` path | 0 | **131**, across all **10** archived trees |
| Rows naming a pre-move spelling | n/a | **45 across 20 files** |
| Rows by owner | 16-02 10, 16-15 39, 16-17 67, 16-18 187, 17-08 81 | **16-02 10, 17-08 81, 23-04 167, 23-10 12** |
| `UNASSIGNED` rows | 0 | **0** |
| Unexaminable subjects | 0 | **0** |
| Schedule rows / distinct spellings matched | 29 / 29 | **29 / 39** |
| `test_retirement_sweep.py` collected | 47 | **57** |
| `tests/examples` collected | 521 | **521** |
| `make gate-tools` leg 1 (`tools/lints/tests`) | 415 | **415** |
| `make gate-tools` leg 2 (`publish_scan_tests` + `docs_tests`) | 329 (2 failed) | **339 (2 failed)** |
| `python -m tools.lints --all` | exit 0 | **exit 0** |

**The 384 → 270 drop is accounted, not mysterious.** The archive trees are now
themselves retiring paths, so a file under `archive/examples/**` referencing
another retiring path is dropped as deleted-with-its-source. That is the count
that rose from 134 to **248**. The two figures move together and their sum is
stable.

**Scope fence, per member.** `git diff b87fe58..HEAD -- src/ runtime/ pyproject.toml`
is **exactly the four lines plan 23-06 was authorised for** —
`runtime/ccf_runtime/mcp/egress.py` 1/1, `runtime/ccf_runtime/mcp/experience.py`
2/2, `src/ccf/products/bind.py` 1/1. `pyproject.toml` untouched. The two task
commits touch **only** `tools/retirement_sweep.py` and
`tools/docs_tests/test_retirement_sweep.py`.

---

## Deviations from Plan

### 1. [Rule 2 — missing critical functionality] `Retirement.former_path`

- **Found during:** task 1, by `test_every_known_coupled_file_is_found`.
- **Issue:** the re-point alone made the sweep stop reporting three references
  in `tools/measure_examples.py` — two of them `live` — that had not stopped
  existing. Left alone this is the sweep going blind in the same commit that was
  written to stop it going blind.
- **Fix:** two-spelling matching for a moved tree, lookup only. 45 rows across
  20 files now depend on it.
- **Why not the alternatives:** deleting the floor entry is the reflex the
  hazard brief warns against; re-pointing `tools/measure_examples.py` is a third
  file the plan does not authorise **and** would drop the file off the floor by
  the other route anyway (the floor asserts the file is FOUND, so discharging
  the coupling loses it too).
- **Files:** `tools/retirement_sweep.py`. **Commit:** `b6ecc05`.

### 2. [Rule 1 — bug] substring double-counting in `python_hits`

- **Found during:** task 1, by two synthetic fixtures returning 2 rows where
  they assert 1.
- **Issue:** `archive/examples/04-cross-process` contains
  `examples/04-cross-process`; both matched the same characters. Repo-wide total
  read 315.
- **Fix:** the substring-suppression rule `text_hits` already carried, added to
  `python_hits`. **Commit:** `b6ecc05`.

### 3. [Rule 1 — bug] the shape-4 fixture's two-segment assumption

- **Issue:** the synthetic runner joined `seg[0] / seg[1]` only, so a
  three-segment retiring path made it build `archive/examples`. The test failed
  on its own fixture rather than on the detector.
- **Fix:** join every segment, at the dedent-safe column. **Commit:** `b6ecc05`.

### 4. [deliberate, against the plan's letter] the report IS regenerated here

The plan's task 2 says *"Do NOT regenerate `docs/surface/examples/RETIREMENT-COUPLINGS.md`
in this plan"* and names `test_the_committed_report_is_current` as expected-red,
owned by `23-11`. **The executor brief overrides this**, requiring the report to
be regenerated **after** the SUMMARY commit, with the CHANGED sweep, and its
test verified green. That is also what wave `23-09` actually did. Both orderings
satisfy criterion 11's "LAST" requirement at the level of the wave; the brief's
is stricter about *whose* sweep renders it, which matters more here than
anywhere else because this plan modified the sweep. Regenerated in commit
`c9b95b4`, after the SUMMARY.

### 5. [redundancy removed rather than kept] the emptiness clause

Recorded above under S-16v(c). The plan explicitly asked for this to be reported
as a finding rather than papered over.

---

## Threat Flags

None. This plan added no network surface, no auth path, no file-access pattern
and no schema at a trust boundary. `T-23-39` through `T-23-43` are all
`mitigate` and all discharged:

| Threat | How it is discharged, measured |
| --- | --- |
| `T-23-39` schedule → tree repudiation | `test_every_scheduled_path_resolves_on_disk`; S-13 watched naming all ten, S-13b naming one |
| `T-23-40` import-time derivation DoS | predicate repaired first; collected count measured 47 → 57 with **zero** node ids lost |
| `T-23-41` tampering with the `s1` rows | `diff` against `PHASE_BASE` exits 0 |
| `T-23-42` the fourteen unowned rows | `D-IMPL-195` ruling 2 applied exactly; no default chosen |
| `T-23-43` a check that passes over nothing | seven non-vacuity controls, four of them proven by disarming the clause they vouch for |
| `T-23-SC` package installs | none attempted |

---

## Carried forward, NOT closed

**Deferred item 7 is CARRIED UNCHANGED.** Both stale-path witnesses read page
SOURCES; neither reads the RENDERED body a `--8<--` include pulls in. The edits
owed remain `archive/examples/08-e2e-demo/run.py:4`,
`archive/examples/05-workflow-hitl/artifacts/task-definition.yaml:6`, plus the
`run.py:1095` output string a fixer must decide about. **This plan's
`former_path` matching does NOT reach them** — those two files are inside the
archive, and references from inside a retiring path are dropped as
deleted-with-their-source. Said plainly so nobody reads two-spelling matching as
item 7's fix. The durable fix is still a third witness over rendered include
bodies, which this repo does not have.

**New deferred item 8** logged in `deferred-items.md`:
`tools/measure_examples.py`'s three stale references, and the design gap in
`KNOWN_COUPLED_FILES` that it exposed — the floor cannot tell *"the sweep
narrowed"* from *"the coupling was discharged"*, which is the same shape as the
`dissolution_problems` idiom already in the module for a different subject.

**Not in scope, not touched:** the sweep's known source blind spot
(`D-IMPL-194`) — no rows are filed for `public/tutorial/adopters-guide.md`,
`public/tutorial/demo-walkthrough.md` or the `tests/examples/test_*_output.py`
modules as SOURCES. Confirmed still present and still backlog.

**Expected red at the moment of the SUMMARY commit, resolved immediately after:**
`test_the_committed_report_is_current`. **`tools/docs_tests/test_requirement_ledger.py::test_every_cited_path_in_a_status_cell_resolves_as_written`
(EXAM-01) is red and is NOT this plan's** — it is owned by plan `23-11` and was
red before this plan began.

---

## Self-Check: PASSED

Verified after the SUMMARY commit — see the appendix appended below.
