---
phase: 23-the-archive-move-retiring-the-ten-condemned-example-trees-wi
plan: 11
subsystem: the ledger verdict — DOCS-17 to Partial, the D-08 pin moved on the record, CLNT-17 untouched
tags: [DOCS-17, EXAM-01, CLNT-17, D-06, D-08, D-15, D-19, D-IMPL-189, D-IMPL-191, D-IMPL-193, D-IMPL-196, D-IMPL-197, D-IMPL-198, criterion-6, criterion-7, criterion-11, criterion-12, criterion-13, RECON-09]
requires:
  - 23-04 (the move; the state the verdict is a claim about)
  - 23-07 (the paired tests re-pointed at the archive)
  - 23-08 (the published includes and prose re-pointed)
  - 23-09 (the fourteen deleted make targets, which caused the D-08 movement)
  - 23-10 (the sweep schedule re-pointed at the archive)
provides:
  - DOCS-17 verdicted Partial in both channels, with the done-limb D-06 permits and not the one it forbids
  - the D-08 reference count re-measured at both ends and its movement recorded with from/to values
  - EXAM-01 re-pointed at the archive, closing the last red in tools/docs_tests
  - CLNT-17 proven byte-identical to efa0044 by content hash, before and after
  - a hand-edited STATE and ROADMAP with no writer invoked and no criterion touched
  - a current coupling report, regenerated last, in the venv
affects:
  - .planning/REQUIREMENTS.md
  - .planning/STATE.md
  - .planning/ROADMAP.md
  - .planning/phases/23-.../deferred-items.md
  - docs/surface/examples/RETIREMENT-COUPLINGS.md
tech-stack:
  added: []
  patterns:
    - hash the row's CONTENT, never `grep -n` output, so a line-number shift can neither masquerade as a change nor mask one
    - a figure is measured at execution time or it is not written; the plan text is not a source
    - a sabotage that catches nothing is recorded as catching nothing, not smoothed into the prose
key-files:
  created:
    - .planning/phases/23-.../23-11-SUMMARY.md
  modified:
    - .planning/REQUIREMENTS.md
    - .planning/STATE.md
    - .planning/ROADMAP.md
    - .planning/phases/23-.../deferred-items.md
    - docs/surface/examples/RETIREMENT-COUPLINGS.md
decisions:
  - "The D-08 pin is written as MOVED 111 -> 122 with from/to values and the cause named, not substituted. The plan's own task-2 verify pinned 111 and failed on a correct tree; gated against the measurement."
  - "The `19 of 31` and `2 execute` limbs were re-measured from the tree at both ends rather than accepted from D-IMPL-198, D-IMPL-195 or the orchestrator's brief. Both reproduce."
  - "The bare-directory prose `examples/external/00-hello-context` inside EXAM-01's own two cells was re-pointed alongside the two citations the gate names — same row, same defect, authorised file. The same stale spelling in DOCS-11, EXAM-04, ERGO-15 and CLNT-30 was NOT touched: not this plan's subject."
  - "The ROADMAP Phase 23 GOAL PROSE still reads `out of live CI` — the clause D-IMPL-191 ruling 4 amended. NOT edited: it is neither the progress row nor the Progress table. Carried as deferred item 9 with the exact edit named."
  - "S-RP3 recorded and NOT performed. Every state.*/roadmap.* writer corrupts these files whether or not it reports success (D-15)."
metrics:
  duration: one session
  completed: 2026-08-25
  commits: 3 task commits, plus this SUMMARY and the final report regeneration
---

# Phase 23 Plan 11: The Verdict, Written When The State Existed — Summary

`DOCS-17` reads **`Partial`** for the first time since it was minted. The cell
says which limb is done and which is owed, in the words `D-06` permits and not
the ones it forbids, and it NAMES what still exercises the archived trees with
figures measured this session.

**Every number below was measured in this session. Not one is inherited from the
plan text, from a decision entry, from a prior SUMMARY, or from the
orchestrator's brief — including the numbers the brief told me to expect.**

---

## The three commits

| # | Commit | What it did |
|---|--------|-------------|
| 1 | `e694374` | `DOCS-17` -> `Partial` in both channels; the naming figures; staleness defect 1; `EXAM-01` re-pointed |
| 2 | `79322fb` | The `D-08` pin recorded as MOVED `111 -> 122`, both channels; the `D-IMPL-189` 99/108 discrepancy named |
| 3 | `90f78a0` | `STATE.md` and `ROADMAP.md` hand-edited; deferred items 9 and 10 |

Plus this SUMMARY, and the report regeneration that must follow it.

---

## Criterion 12 — the verdict, and what the cell may claim

`D-IMPL-189` point 4 held this verdict back *"until the state exists on the
tree, and not before"*. The state exists: 265 files at `archive/examples/`,
proven a pure rename set at Wave 4.

The done-limb is worded as **`D-IMPL-191` ruling 4 AMENDED it** — *out of the
`examples:` aggregate* — and **NOT** *out of live CI*, which would have been
false on the day it was written. That is the `RECON-09` failure the criterion
exists to prevent: the difference between a verdict and a hope.

### What still exercises the archived trees, measured

| Figure | Measured this session | Method |
|---|---|---|
| tracked files under `tests/examples` | **31** | `git ls-files 'tests/examples/*'` |
| tests `tests/examples` collects | **521** | `pytest tests/examples --collect-only -q` |
| files naming a condemned tree | **19** of 31 | ten full tree names, any spelling |
| the same set at `PHASE_BASE` | **19**, and the file list is IDENTICAL | same grep at `b87fe58`; `diff` exit 0 |
| loading archived source in-process | **14** | `exec_module`/`runpy` AND an `archive` path in the module |
| SPAWNING A PROCESS against it | **2** | `D-IMPL-198` ruling 2's stated reading |

The two that spawn are `tests/examples/test_cross_process_output.py` — which
`exec_module`s `archive/examples/04-cross-process/run.py`, and *that* file opens
a real `subprocess.Popen` peer — and `tests/examples/test_ext00_hardening.py`,
whose `EXAMPLE_DIR` is `archive/examples/external/00-hello-context` and which
calls `subprocess.run` directly.

**Both were RUN, not assumed: 46 passed, 0 skipped.** A skipped test and a
passing test are indistinguishable in a total, which is criterion 8's point.

**The nineteenth file was nearly lost, and how it was found is worth recording.**
A path-string grep for `archive/examples/<tree>` finds **18**. The nineteenth,
`tests/examples/test_gate_two_divergence.py`, builds its path from segments:

```python
EXAMPLE = REPO_ROOT / "archive" / "examples" / "00-quickstart" / "run.py"
```

A grep for the slash-joined form is blind to it. The 19 is measured on the tree
NAMES in any spelling, which is why it reproduces at both ends.

**And the superseded `25 of 31` reproduced at NEITHER end**, confirming
`D-IMPL-198` ruling 2's stronger reading: it was not drift, it was wrong from
the start.

### The two staleness defects, both corrected on re-measurement

1. The cell claimed *"zero published references to the `s1-*` trees"*. **Measured
   7**, all on `public/concepts/answers-no-document-contains.md`, five of them
   `--8<--` includes. That is the same measurement `D-IMPL-190` ruling 1 limb (b)
   relies on, so the ledger and the decision log no longer contradict each other.
2. The pinned `111 references` — task 2, below.

### `make docs-strict`, run rather than inferred

Exit 0 on all four steps, in the foreground, `EXIT=$?` taken without a pipe
(research §14's measurement hazard: `... | tail` reports the pipe's status, and
this phase's primary witness cannot afford that).

---

## Criterion 6 — the `D-08` pin moved, and the cell says so

| | total | includes | pages |
|---|---|---|---|
| `b87fe58`, old prefix, slash-free | **111** | 102 | 15 |
| `HEAD`, `archive/examples/` prefix | **122** | **102** | **15** |
| old prefix still under `public/` | **0** | — | — |

The page SET is identical at both ends (`diff` exit 0). The include population
did not move at all. **The eleven new references are `python` invocation lines
under `PYTHONPATH=src:runtime`** — one each on five how-to pages and six on the
adopters' guide — that replaced the fourteen `make example-*` commands criterion
3 deleted. Prose paths went 9 -> 20. The movement is a by-design consequence of
criterion 3, and the cell states it as moved with FROM and TO values per `D-19`
and `D-IMPL-174` rather than substituting the number.

**The wave-1 correction was honoured and it mattered.** The old-prefix regex
must not require a trailing slash. It does not here; the 111 reproduces exactly.

**`D-IMPL-189`'s own scope figures are NAMED, not corrected.** *"99 snippet
includes and 108 prose paths"* does not match the tree and never did; 102 + 9 =
111 is what `21-04` measured and what `D-08` pins. `docs/DECISIONS.md` is
append-only and was not touched.

### THE PLAN'S OWN TASK-2 VERIFY PINNED 111 AND FAILED ON A CORRECT TREE

Run verbatim:

```
PLAN VERIFY FAIL — measured 122, plan text says 111
```

Criterion 6's own subject — a pinned figure quoted forward instead of measured —
arriving inside the task commissioned to close it. The second limb of the same
verify (`archive/examples` appearing at least twice in the ledger) passes at 4.
Gated against the measurement, and recorded here rather than reconciled quietly.

---

## Criterion 13 — `CLNT-17`, and what actually guards it

```
git show efa0044:.planning/REQUIREMENTS.md | grep -E '^- \[[ x]\] \*\*CLNT-17\*\*|^\| CLNT-17 \|' | sha256sum
grep -E '^- \[[ x]\] \*\*CLNT-17\*\*|^\| CLNT-17 \|' .planning/REQUIREMENTS.md | sha256sum
```

`5bcc68caa9f6839df0d870aba10a4897114607995eb21ded0b13cccedc3ba084` at `efa0044`,
before every edit, and after every edit and every sabotage. The row still reads
`Not built` and its box is still unticked. Content-hashed, never `grep -n` — the
line numbers moved when nothing above the row did, but a hash of positions would
have been a different check.

**No plan, task, ledger cell or commit message in this wave assigns `CLNT-17`
any verdict, limb or disposition.** Its two framing questions stay raised and
expressly not ruled.

---

## The sabotages: six run, FOUR caught nothing

Every one restored byte-identically, with `git diff --quiet` before moving on.

| # | Mutation | Prediction | OBSERVED |
|---|---|---|---|
| S-L1 | one channel of `EXAM-01` left un-repointed | fails naming the other | **CAUGHT** — 1 failed / 113 passed. **Prediction CORRECTED:** the refusal names the ROW and the PATH, never the CHANNEL. Identical message with either channel broken |
| S-L2 | the cell rewritten *out of live CI*, both channels | nothing fails | **CONFIRMED** — 114 passed, `tools.lints --all` exit 0 |
| S-L3 | one character in the `CLNT-17` row | the anchor fails | **CAUGHT** by the anchor (and, incidentally, by four ledger tests) |
| S-L3b | a PROSE-only character (`the` -> `teh`) | (added by me) | **NOT CAUGHT** by the ledger gate — 114 passed. Only the anchor sees it |
| S-L4 | `DOCS-17` `Partial` in one channel, `Not built` in the other | run it and record | **NOT CAUGHT** — 114 passed with the two channels openly disagreeing about one row's verdict |
| S-D8a | the `D-08` figure updated in one channel only | nothing fails | **CONFIRMED** — 114 passed, lints exit 0 |
| S-D8b | the new figure written without saying it moved | nothing fails | **CONFIRMED** — 114 passed, lints exit 0 |

### S-L3b is mine, and it is the one that matters

S-L3 changed `Not built` to `Not  built`, which broke the verdict token and so
reddened four ledger tests. Taken at face value that reads as *"the ledger gate
guards the `CLNT-17` row"*. **It does not.** S-L3b changes one word of prose and
the module is 114 GREEN. The content-hash anchor criterion 13 mandates is the
ONLY thing that sees an arbitrary edit to that row — which is precisely why the
criterion mandates it rather than trusting the suite.

### S-L2, S-D8a and S-D8b, said plainly

`cell_verdicts` enforces *at most one verdict per cell*. **Nothing enforces the
same verdict across a row's two cells, and nothing whatsoever reads a cell's
WORDING.** `D-06`'s constraint and `D-19`'s moved-pin obligation are
judgement-enforced, today, by construction. The value of tasks 1 and 2 is that a
human measured numbers, wrote them in two places, and said why they changed. No
gate held them there, and this record says so rather than implying otherwise.

Tabulated as deferred item 10.

---

## The `D-11` scope fence, run rather than trusted

`D-IMPL-188` bounded Phase 21's five untouched-tree assertions to `951eb4a`, so
this phase's 265-file write under `examples/` falls after the ceiling. Confirmed
by RUNNING the module in full — **114 passed** — at every step of this wave, not
by reading the note. Phase 22 was bitten here only because the window was then
`..HEAD`.

The fabric fence also holds: `git diff b87fe58..HEAD -- src/ runtime/
pyproject.toml` is **exactly the four `D-IMPL-192` path-string lines** across
three files, 4 insertions / 4 deletions, `pyproject.toml` untouched.

---

## Criterion 7 — the `tests/examples` accounted delta, re-measured

`D-IMPL-198` ruling 1 made this limb an accounted delta and forbade quoting it
from any entry *"including this one"*. Test-function name sets extracted at both
ends and compared:

| | count |
|---|---|
| `def test_*` under `tests/examples` at `b87fe58` | **442** |
| the same at `HEAD` | **448** |
| **LOST (in base, not in head)** | **0** |
| ADDED | **6**, all named below |

```
tests/examples/test_artifact_schema_headers.py::test_the_gated_roots_are_the_live_tree_and_the_archive
tests/examples/test_artifact_schema_headers.py::test_the_discovery_globs_reach_the_live_tree_and_the_archive
tests/examples/test_artifact_schema_headers.py::test_the_discovery_finds_an_archived_artifact_directory
tests/examples/test_artifact_schema_headers.py::test_the_discovery_ignores_an_artifact_directory_outside_both_roots
tests/examples/test_hw1_harness_clients_readme.py::test_the_pinned_diff_ceiling_resolves
tests/examples/test_hw1_harness_clients_readme.py::test_control_7c_an_empty_ceiling_refuses_instead_of_meaning_head
```

Four are Wave 3's; two are `D-IMPL-197`'s. **515 + 6 = 521**, which is what
`--collect-only` reports. Every file under `tests/examples` is `M` — none
created, none deleted. The roster reconciles exactly and the lost-set is empty.

**This plan added ZERO tests and removed ZERO tests.** Its whole delta is
`.planning/` prose and one generated report. Named explicitly, because criterion
7 is now an accounted delta and *an addition nobody named is a finding at
`23-12`, not a pass*.

---

## Criterion 11 — the report, regenerated LAST, in the venv

Interpreter recorded: **`/home/parkave/ccf_code/.venv/bin/python`, 3.12.3**.

Order held: task 1 -> task 2 -> `STATE`/`ROADMAP`/deferred items -> **this
SUMMARY** -> regeneration. Confirmed clean under `.planning/` and `public/`
before the authoritative run.

| # | Mutation | Prediction | OBSERVED |
|---|---|---|---|
| S-RP1 | regenerate under `/usr/bin/python3` | six rows silently dropped at exit 0 | **PREDICTION CORRECTED — it no longer drops silently.** The sweep **REFUSES**: exit **1**, *"1 subject(s) could not be examined, so this count is not a measurement of coupling — it is a measurement of what happened to load"*, naming `tests/products/test_gate_two_call_shape.py [import] ModuleNotFoundError: No module named 'joserfc'`, **and the report was NOT written**. That is `D-GATE-22.1`'s fail-closed fix working on the exact input it was built for |
| S-RP2 | write under `.planning/` after regenerating | the currency test goes red | **CONFIRMED** — green immediately after regeneration, red after one appended line, restored |
| S-RP3 | invoke a `state.*` writer | fields dropped, file corrupted | **RECORDED, NOT PERFORMED** (`D-15`) |

**A distinction the S-RP1 run makes easy to get wrong.** The currency test was
red during that experiment — but because `.planning/` had moved since the last
regeneration, not because of the system interpreter. The system run wrote
nothing. Two different reds that look the same, which is the same
indistinguishability `test_the_committed_report_is_current` has in general: **it
cannot tell a stale schedule from a stale snapshot**, and it was red for BOTH
the true `DOCS-17` cell and S-L2's false one. Its green at the final commit is a
currency claim and nothing more.

### The obligation `23-12` and `23-13` inherit, explicitly

`tools/retirement_sweep.py` walks `.planning/`. **Any further write under
`.planning/` or `public/` — including a SUMMARY, a STATE edit, or a close
report — makes the committed report stale and it must be regenerated again, in
the venv, before the phase closes.** Wave 8 got this wrong and left a red; Wave
10 had to regenerate twice.

---

## `D-15` — hand-edited, and what that cost

**No `state.*` and no `roadmap.*` writer was invoked in this wave.** All three
files were copied outside the tree before editing and diffed after.

**`STATE.md`**: one timestamp line changed; 85 lines PREPENDED to `stopped_at`
with the mid-phase checkpoint preserved beneath a `PRIOR` marker. Frontmatter
re-parsed after the edit — **8 keys, unchanged key set, `progress` intact,
`last_activity` byte-length identical at 112426**. Exactly ONE deletion in the
whole diff.

**`ROADMAP.md`**: **ONE LINE** changed, the Phase 23 progress row, `0/13` ->
`11/13`. File line count identical at 2299 before and after.

- **The criteria block is byte-identical to the pre-edit backup**, all eighteen
  present, **each on ONE line**, zero continuation lines inside the block. That
  is the hazard that shipped 15.3 and 15.4 gated against a single truth.
- Against `PHASE_BASE` the block differs at **exactly two lines, 7 and 12** —
  the orchestrator's `D-IMPL-196`/`D-IMPL-197`/`D-IMPL-198` amendments applied at
  the checkpoint. **Recorded as a RULED difference, not repaired.** The plan's
  verification line *"the eighteen Success Criteria are byte-identical to
  `PHASE_BASE`"* is therefore superseded by the rulings that landed after the
  plan was written.

---

## Carried forward, with the edits named

**Item 7** (three waves) and **item 8** (from Wave 10) CARRIED UNCHANGED. Neither
`archive/examples/08-e2e-demo/run.py`, nor
`archive/examples/05-workflow-hitl/artifacts/task-definition.yaml`, nor
`tools/measure_examples.py` is in this plan's `files_modified`. Not widened into.

**Item 9, NEW.** `.planning/ROADMAP.md`'s Phase 23 **goal prose** still reads
*"limb done — out of live CI"* — the clause `D-IMPL-191` ruling 4 AMENDED. The
file therefore asserts, in prose, the exact claim the cell shipped here is
forbidden to make. Criterion 12 is correct; the paragraph above it is not.
`STATE.md`'s `## Current Position` block similarly still reads *"SIXTEEN Success
Criteria"* (there are eighteen) and *"25 of 31"* (measured 19 at both ends).
**Not edited** — none is the progress row or the Progress table, and task 3
forbids touching a criterion. Three edits named in `deferred-items.md`, owed to
`23-13`. **Nothing gates any of the three**, which is why they went two rulings
stale without a red.

**Item 10, NEW.** The five sabotages that caught nothing, tabulated with their
commands and results.

**And a ledger-wide residual, named and not acted on.** `examples/external/00-hello-context`
still appears in the pre-move spelling in `DOCS-11`, `DOCS-15`, `EXAM-04`,
`ERGO-15` and `CLNT-30`. The ledger gate does not flag them (their occurrences
are not file-shaped citations in a status cell), and re-pointing rows this plan
does not name would be scope this plan does not have. `EXAM-01`'s own two cells
were re-pointed in full — the two citations the gate names AND the two
bare-directory prose mentions in the same row — because that row IS the plan's
subject.

---

## Gates at this SUMMARY

| Gate | Result |
|---|---|
| `tools/docs_tests/test_requirement_ledger.py` | **114 passed** (was 113 passed / 1 failed at wave start) |
| `tools/docs_tests` (whole tree) | **286 collected** |
| `tools/docs_tests/test_retirement_sweep.py` | **57 collected** |
| `tests/examples` | **521 collected**; the two executors 46 passed / 0 skipped |
| `tools.lints --all` | exit **0** |
| `make docs-strict` | exit **0**, four steps, foreground |
| `CLNT-17` content hash vs `efa0044` | **EQUAL** |
| `src/ runtime/ pyproject.toml` vs `b87fe58` | the four `D-IMPL-192` lines, nothing else |

**The EXAM-01 red — the one the brief named as mine, the last one standing — is
CLOSED.** `tools/docs_tests` had 285 passed / 1 failed at wave start; the only
remaining red at this SUMMARY is
`test_the_committed_report_is_current`, which is red BY CONSTRUCTION until the
regeneration that must follow this commit, and which criterion 11 requires to be
last.
