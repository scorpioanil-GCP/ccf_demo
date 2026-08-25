---
phase: 23-the-archive-move-retiring-the-ten-condemned-example-trees-wi
plan: 09
subsystem: command-surface
tags: [DOCS-17, D-04, D-IMPL-195, CLNT-30, H-14, documented-commands-bijection, ungated-surface]
requires:
  - "23-08 (the published includes already re-pointed; docs-strict green)"
  - "23-01 (Dave's `delete-four` ruling on the live-leg targets)"
provides:
  - "a one-member `examples:` aggregate and fourteen fewer make targets"
  - "the documented-commands bijection green in both directions after the deletion"
  - "an honestly-described always-on ci.yml examples job"
  - "a repo front door whose links resolve and whose counts are true"
  - "the CLNT-30 historical marking amended for the archive move"
affects:
  - "Makefile, .github/workflows/ci.yml, .github/workflows/live-legs.yml"
  - "README.md, examples/external/README.md, archive/examples/external/00-hello-context/README.md"
  - "seven published pages under public/"
tech-stack:
  added: []
  patterns:
    - "positive-and-negative make probe (VAC-01 applied to `make -n`)"
    - "COMMIT-BEFORE-VERIFY (D-IMPL-166) for the shipped-example dirtiness guard"
key-files:
  created: []
  modified:
    - Makefile
    - .github/workflows/ci.yml
    - .github/workflows/live-legs.yml
    - README.md
    - examples/external/README.md
    - archive/examples/external/00-hello-context/README.md
    - public/tutorial/adopters-guide.md
    - public/tutorial/demo-walkthrough.md
    - public/how-to/bind-a-harness-adapter.md
    - public/how-to/run-agents-cross-process.md
    - public/how-to/grant-and-revoke-a-skill.md
    - public/how-to/compose-a-workflow-with-hitl.md
    - public/how-to/swap-the-artifact-store.md
    - tools/docs_tests/test_documented_commands_exist.py
decisions:
  - "The four live-leg targets deleted per D-IMPL-195 ruling 1 (`delete-four`), not chosen — read from 23-01-SUMMARY.md"
  - "`CCF_REQUIRE_HARNESSES` removed from the ci.yml examples job after measuring that nothing under `examples/` reads it"
  - "`live-legs.yml` keeps its path and `name:`; five out-of-scope documents reference it by path"
  - "The stale rendered-include finding (deferred item 7) is NOT fixed here — its files are outside this plan's files_modified"
metrics:
  duration: "~11 minutes of task execution (22:19–22:30), plus verification"
  completed: "2026-08-24"
  commits: 3
  tests_added: 0
  tests_removed: 0
---

# Phase 23 Plan 09: The Command Surface — Fourteen Targets Deleted and the Bijection Kept Green in Both Directions

Ten `example-0N`-family targets and four live-leg targets deleted from the
`Makefile` — definitions *and* `.PHONY` names — with the `examples:` aggregate
reduced to one member, the thirteen published `make example-*` strings that
named them repaired in the same wave, and the two CI workflows that outlived
them brought back into agreement with what they now run.

---

## THE TEN → FOURTEEN EXPANSION IS RULED, NOT SCOPE CREEP

**This plan deleted FOURTEEN make targets against a criterion that read TEN
until `D-IMPL-195` ruling 1 (Dave, 2026-08-24).** Flagged here because Dave
asked that it be flagged wherever it is acted on, so a reader who finds
fourteen deletions against a criterion they remember as ten can locate the
ruling instead of inferring that an executor overreached.

The four added, all four running a condemned tree:

| Target | Ran |
|---|---|
| `example-03-live-ollama` | `examples/03-harness-portability/run.py --mode live --provider ollama` |
| `example-03-live-anthropic` | `examples/03-harness-portability/run.py --mode live --provider anthropic` |
| `example-ext-00-live-anthropic` | `examples/external/00-hello-context/run.py --live --legs anthropic` |
| `example-ext-00-live-adk` | `examples/external/00-hello-context/run.py --live --legs adk` |

**Dave's ruling was READ, not chosen.** The plan forbids picking a default and
requires escalation if the ruling is absent. `23-01-SUMMARY.md` carries the
selected option id verbatim — **`delete-four`** — at its "Task 2 — RULED"
section, with the ruling text quoted in full. Dave's stated reason is on the
record: *"Leaving them invites 'the teaching path.' Re-pointing into archive
keeps CI load on unsupported trees."* Both halves were implemented: the targets
deleted, and the workflow steps that invoked them dropped, so `live-legs.yml`
cannot go red on a missing target.

---

## What shipped, measured

Three task commits against the wave-8 head `6c2e004`:

| Commit | Task |
|---|---|
| `0ddceaa` | Fourteen definitions, fourteen `.PHONY` names, the one-member aggregate |
| `1adc35a` | The thirteen published strings, `ci.yml`, `live-legs.yml`, two Makefile comments, one control re-anchored |
| `3637abe` | `README.md`, the orphaned family charter, the `CLNT-30` marking |

14 files, +145 / −229.

### Task 1 — the Makefile

**Every figure below was measured in this session, not carried.**

| Measurement | Before | After |
|---|---:|---:|
| `grep -c '^example-' Makefile` | 25 | 11 |
| `make -n` reports "exists" for the fourteen | 14/14 | 0/14 |
| `make -n example-hw1-harness-clients` | exists | exists |
| `make -n examples` | exists | exists |
| `composed_examples(Makefile)` | 11 members | `{"example-hw1-harness-clients"}` |
| `phony_targets(Makefile) ∩ the fourteen` | 14 | `[]` |

**The probe is proven able to distinguish present from absent** (`VAC-01`
applied to a `make` probe: a probe that reports "gone" for everything reports
nothing). The survivor and the aggregate were probed in the same loop and both
report "exists"; the fourteen all report "gone".

`examples:` now reads:

```make
examples: example-hw1-harness-clients ## Run the network-free examples suite (one member since D-04), stopping on first failure
```

**No archive-form target replaces them.** `grep -nE '^example-archive|archive/examples' Makefile`
returns nothing.

**`example-s1-00` and `example-s1-01` are byte-identical to `PHASE_BASE`**
(`D-01`), proven two ways rather than eyeballed: the Makefile diff against
`b87fe58` contains **zero** changed lines mentioning `s1`, and a `sha256sum`
of each target's extracted body matches `git show b87fe58:Makefile`'s.

### Task 2 — the thirteen published strings

**Re-measured first (`D-19`), not carried from research.**
`git grep -nE 'make +example-' -- public/` returned **14 invocations across 8
pages**, **13 of them naming a target this plan deletes**. The fourteenth is
`public/how-to/run-agents-cross-process.md:202`, `make example-hw1-harness-clients`
— the survivor, and the one site that keeps the backward direction from being
unsatisfiable. Research's "15" counted `make examples` on
`demo-walkthrough.md:313` as a fifteenth; that string does not match
`make +example-` (no hyphen) and is not one of the thirteen.

**THE BIJECTION WAS WATCHED RED BEFORE GREEN, on the real tree.** With task 1
committed and no page yet repaired:

```
undefined_commands (10):
    make example-00 (public/tutorial/adopters-guide.md:44)
    make example-01 (public/tutorial/adopters-guide.md:159)
    make example-02 (public/how-to/grant-and-revoke-a-skill.md:28, public/tutorial/adopters-guide.md:219)
    make example-03 (public/how-to/bind-a-harness-adapter.md:29)
    make example-04 (public/how-to/run-agents-cross-process.md:35)
    make example-05 (public/how-to/compose-a-workflow-with-hitl.md:31, public/tutorial/adopters-guide.md:278)
    make example-06 (public/tutorial/adopters-guide.md:360)
    make example-07 (public/how-to/swap-the-artifact-store.md:30)
    make example-08 (public/tutorial/demo-walkthrough.md:21, public/tutorial/demo-walkthrough.md:313)
    make example-ext-00 (public/tutorial/adopters-guide.md:401)
```

Ten distinct targets, thirteen sites. After the repairs: `undefined_commands`
**empty**, `undocumented_examples` **empty**, both non-vacuity preconditions
passing, `git grep -cE 'make +example-' -- public/` sums to **1** (the
survivor).

**The per-site choice, recorded per site.** There is no archive-form target to
point at (`D-04`), so every site is a prose repair rather than a substitution.
Every one took the same form — the direct
`PYTHONPATH=src:runtime python archive/examples/<tree>/run.py` invocation,
which is the spelling `23-08` already established at
`demo-walkthrough.md:18` and `:310` — but the surrounding sentence differed at
four of them and those four were rewritten rather than left:

| Site | Choice |
|---|---|
| `adopters-guide.md:44/159/219/278/360/401` | direct run form, in place, sentence unchanged (`Run: \`…\`.`) |
| `adopters-guide.md:9-13` | **rewritten** — "literal-included from an example the CI pipeline runs" was false for the make surface; now names `archive/examples/`, `D-04`, and `tests/examples/` as what still executes them |
| `adopters-guide.md:39-40` | **rewritten** — `make ci` no longer "runs … every example in this guide"; it runs the `tests/examples/` modules that execute them |
| `bind-a-harness-adapter.md:30` | direct run form **plus `--mode deterministic`**, because the deleted target carried that flag and dropping it would change what the reader runs |
| `compose-a-workflow-with-hitl.md:32`, `grant-and-revoke-a-skill.md:29`, `run-agents-cross-process.md:36`, `swap-the-artifact-store.md:31` | direct run form in the fenced block, lead-in unchanged |
| `demo-walkthrough.md:21` | **invitation removed** — `(or \`make example-08\`).` deleted; the fenced `archive/` command two lines above is the command |
| `demo-walkthrough.md:14-15` | **rewritten** — "the same run CI performs" kept but qualified, naming `tests/examples/test_e2e_demo_output.py` as the thing that performs it |
| `demo-walkthrough.md:313` | **rewritten** — "it also runs inside `make examples` and therefore `make ci`" was false the moment task 1 landed; replaced with the test module that does run it |

`make examples` on `demo-walkthrough.md:313` was left, as the plan directs, and
the sentence around it made true.

**`ci.yml` — the always-on examples job stays GREEN and is now honestly
described.** No step invoked any of the fourteen by name; the aggregate is the
only seam, and `make examples` exits 0 with one member (verified by running it —
three harness legs, one content address `5d7bfa4…`, exit 0). Five stale
descriptions rewritten: the job `name:` (`examples suite (00–07, reference
backends)` → `examples suite (hw1-harness-clients, reference backends)`), the
subprocess comment (04 and 07 have left the job; the surviving example spawns
MCP stdio children of its own), the `timeout-minutes: 20` comment, the run-step
name (`Run all eight examples` → `Run the network-free examples suite`), and the
block comment above the job.

**`CCF_REQUIRE_HARNESSES` — the question was CHECKED, not assumed, and the
answer decided it.** `grep -rn CCF_REQUIRE_HARNESSES examples/ src/ runtime/`
returns **nothing**. The name is read by `tests/conftest.py` (pytest only) and
by `archive/examples/03-harness-portability/run.py` — the example that has left
this job. The surviving example reads `CCF_HARNESS_PROMPT` and
`CCF_HARNESS_MODEL`, neither of which this var affects. It was therefore
**inert in a job whose only step is `make examples`**, and was removed with its
comment. This is the check the plan asked for rather than a doc fix wearing a
behaviour change as a hat.

**`live-legs.yml` — all three sites, per the ruling.** The two jobs
(`examples-live-ollama`, `examples-live-anthropic`) that ran deleted targets are
**deleted**, with the now-unused `ollama_model` `workflow_dispatch` input, the
file-header comment block that named a deleted target (site 3, the one the
wave-1 correction added), and the `schedule:` note that explained
`if: github.event_name == 'workflow_dispatch'` guards on jobs that no longer
exist. `fluree-drift` — the `D-09` upstream-drift detector, unrelated to this
phase — is the only job left and is untouched. Verified: `yaml.safe_load` parses
the file, `jobs` is exactly `['fluree-drift']`, `on` is
`{workflow_dispatch, schedule[cron '0 7 * * 1']}`, **`grep -nE 'example-(00|…|ext-00)\b'`
returns nothing** and **no bare `examples/` path remains** — criterion 3 NEW's
*"`live-legs.yml` carrying no reference to a deleted target"* holds literally,
not just in spirit. The file **keeps its name and path**: five documents outside
this phase's scope reference `.github/workflows/live-legs.yml` by path
(`README.md`, the `Makefile`, `docs/PHASE_I5_GATE.md`,
`docs/09-ruling-batch-minicycle.md`, the coupling report), and renaming it would
trade one stale reference for five. That choice is stated in the file itself.

Two `Makefile` comments about `live-legs.yml` were repaired in the same commit:
*"`live-legs.yml`'s three jobs"* → *"one remaining job"*, and the `ci`
composition comment now names the three surviving
`example-hw1-harness-clients-live-*` targets as the live opt-ins.

### Task 3 — the ungated surfaces and the `CLNT-30` marking

**`README.md`, before and after, measured:**

| Grep | Before | After |
|---|---:|---:|
| markdown links `](examples/<moved>/)` | 8 | 0 |
| bare `examples/<moved>` tokens | 10 | 0 |
| `make example-*` strings | 11 | 0 |
| "all eight" / "eight examples" claims | 2 | 0 |
| relative link targets that resolve on disk | — | **15 of 15** |
| `archive/examples/*/run.py` commands that resolve | — | **8 of 8** |

The eight table links were 404s on GitHub the moment `23-04` landed. The
sentence *"`make examples` runs all eight in order — the same command CI runs"*
and the `make ci` comment *"all eight examples"* were both false the moment task
1 landed; both are gone. A new paragraph states that the eight live under
`archive/examples/`, why (`D-IMPL-189`, `D-IMPL-193`, `D-04`,
`D-IMPL-195` ruling 1), and that `tests/examples/` still executes them — so a
reader does not conclude the examples stopped working. The live-legs sentence
now names the three surviving `example-hw1-harness-clients-live-*` targets.

**`examples/external/README.md` — the family charter whose only member left.**
All three sites repaired: the band-map row now reads *"archived at
`archive/examples/external/00-hello-context`"*, the structural analog points at
`archive/examples/03-harness-portability`, and the `00`–`08` framing no longer
claims they are "unchanged". A blockquote states the orphaned state plainly —
the directory holds only this charter, the charter stays because it governs the
*family* and the band map is what a future `10`–`19` or `50+` example is written
against, and `H-14`'s marking obligation is discharged in the archived example's
own README rather than by deletion.

**`archive/examples/external/00-hello-context/README.md` — `CLNT-30`'s prose
obligation, which `D-IMPL-193` explicitly did NOT lift.** The marking **already
existed**, under the existing `## What this demonstrates` heading, written in
Phase 20 plan `20-07`, and both required clauses still read true: the
pre-Phase-17 HTTP-with-bearer-auth surface, and Phase 20's trio being canonical
going forward. What was stale was one clause — *"it stays CI-green under
`make example-ext-00`"*, a target this plan deleted. Amended **in place, under
the same existing heading**, so the seven-heading assertion never came near
failing (`grep -c '^## '` = **7** before and after; the three ext00 modules run
**57 passed**):

- the `make example-ext-00` clause removed;
- a new paragraph in the same blockquote stating the archive location, that
  `D-IMPL-193` clarified *"stays CI-green"* to mean **its tests keep passing**,
  naming `test_ext00_hardening.py`, `test_ext00_serve_output.py` and
  `test_ext00_fixture_schemas.py` as the three that still execute the tree, the
  direct run command, and — explicitly — that **the marking obligation was not
  lifted by the move**, so a reader who finds this README does not conclude a
  ratified requirement was quietly dropped;
- a broken link fixed on the way past: `[../README.md](../README.md)` resolved
  to nothing after the move. Re-pointed at
  `../../../../examples/external/README.md`, verified to resolve.

---

## Sabotage — every mutation watched, every restore byte-verified

Eight mutations. Each restored from a copy held **outside the tree**
(standing hazard 3 — `git checkout --` can destroy an uncommitted fix while
`git diff --quiet` reports success), and each restore confirmed with `cmp -s`
rather than assumed.

| # | Mutation | Prediction | Observed |
|---|---|---|---|
| S-M1 | `example-00` returned to `.PHONY` with no definition | *"nothing catches it until someone runs it"* | **PREDICTION WRONG, IN THE DANGEROUS DIRECTION** — see below |
| S-M2 | `example-archive-00` added instead of a clean delete | `make -n example-00` still fails; only a count assertion catches it | **CONFIRMED EXACTLY.** `make -n example-00` FAILS identically; `grep -c '^example-'` went 11 → 12 and the count assertion went red; the criterion-3 grep named the offending line |
| S-M3 | `examples:` prerequisite list emptied | `test_the_makefile_parses` precondition fails | **CONFIRMED.** `1 failed` — *"no example-\* prerequisites parsed from the examples: target"*, `composed_examples` = `set()` |
| S-B1 | one page's `make example-00` restored | forward direction fails naming target and page:line | **CONFIRMED**, and it named both: *"make example-00 (public/tutorial/adopters-guide.md:48)"*. Two further tests also reddened (the two that copy `adopters-guide.md` as a fixture) — unpredicted, recorded |
| S-B2 | the one published page documenting the survivor un-named | backward direction fails | **CONFIRMED** — *"these example targets run in CI but no published page names them … example-hw1-harness-clients"*. Also reddened `test_the_gate_refuses_an_undocumented_composed_example`, whose assertion is `offenders == ["example-99"]` and which now saw two — unpredicted, recorded |
| S-B3 | `examples:` emptied **and** every published `make example-*` removed | both directions pass vacuously; **both** non-vacuity preconditions fail | **HALF WRONG, and the half that is wrong matters** — see below |
| S-R1 | one `README.md` example link reverted to `examples/` | *"nothing fails"* | **CONFIRMED, against four independent gates** — see below |
| S-R2 | the `CLNT-30` historical marking deleted outright | *"the heading test may or may not fire — run it and record which"* | **NOTHING THAT READS CONTENT FIRED** — see below |

### S-M1 — the prediction was wrong, and the truth is worse

The plan predicted a leftover `.PHONY` name would go uncaught "until someone
runs it". Measured: **running it does not catch it either.**

```
$ make -n example-00
make: Nothing to be done for 'example-00'.
$ echo $?
0
```

A `.PHONY` declaration with no rule is a target that *exists* and does nothing.
`undefined_commands` dropped from 10 offenders to 9 — `example-00` vanished from
the list — and a reader following a documented `make example-00` gets **exit 0
and silence**, not `No rule to make target`. That is why step 2 of task 1 (the
`.PHONY` deletion the coupling report files **zero** rows for, because it matches
PATH tokens and `.PHONY` names TARGETS) was the single most likely silent miss
in this plan, and it is a stronger reason than the plan gave.

### S-B3 — only ONE of the two non-vacuity preconditions catches it

Both sides emptied:

```
undefined_commands   : []    <- forward direction PASSES
undocumented_examples: []    <- backward direction PASSES
composed_examples    : set()
```

The two shipped assertions ran `2 passed`. Of the two preconditions,
`test_the_makefile_parses` went **red**; **`test_the_published_tree_names_commands`
stayed GREEN**, because it asserts that *some* `make <target>` invocation exists
anywhere in the published tree, and `make ci`, `make test`, `make docs` and the
rest satisfy it regardless of the example population.

**Standing observation for the close panel.** After this plan the backward
direction is trivially satisfiable — one member, one page — so this gate's
protection rests almost entirely on its non-vacuity floor, and that floor is
**one test, not two**. `test_the_published_tree_names_commands` is insensitive to
the `example-*` population entirely. This is criterion 16's shape for this gate,
and it is narrower than the plan assumed.

### S-R1 — `README.md` is unwatched, stated rather than assumed

The repo's front door on GitHub was reverted to a link that 404s, and **four
independent gates were run against it**:

| Gate | Result |
|---|---|
| `tools/publish_scan.py --pre-build` | exit 0 — blind (`README.md` is outside `public/`) |
| `tools/docs_tests/test_no_stale_example_paths.py` | 17 passed — blind |
| `python -m tools.lints --all` | exit 0 — blind |
| `test_documented_commands_exist.py` | 10 passed — blind |

Nothing fails. `README.md` and `examples/external/README.md` were repaired **by
judgement**, and the difference between *"researched and decided to leave"* and
*"never checked"* is what this paragraph exists to protect. The greps that verify
them are the four in the task-3 table above; `git grep -ln` confirms **no test or
tool under `tests/`, `tools/` or `perf/` reads `examples/external/README.md` at
all**.

### S-R2 — the `CLNT-30` prose obligation is UNGATED, and the one red is a false positive

The whole marking was deleted (`grep -ci historical` → **0**). Results:

- `test_the_readme_keeps_its_seven_template_headings` — **PASSED.** It counts and
  names `## ` headings; a blockquote inside a section is invisible to it.
- All three ext00 modules — **57 passed.**
- `tests/examples/test_hw1_harness_clients_retirement.py::test_no_tracked_file_under_the_historical_example_is_dirty`
  — **FAILED**, and **it is not evidence of anything.** It is `D-IMPL-166`'s
  `modified_tracked_violations` arm, a working-tree cleanliness guard. Proven a
  false positive by re-running it with the **correct, restored** marking in
  place and still uncommitted: **identical failure, identical message.** It
  cannot distinguish the marking's deletion from its authorship. After committing
  task 3 the module is **16 passed** (`D-IMPL-166`'s COMMIT-BEFORE-VERIFY
  discipline applied as the test's own message instructs, rather than the
  assertion being narrowed).

**Conclusion, recorded rather than glossed: no gate holds `CLNT-30`'s prose
obligation.** It survives on judgement and on this record.

---

## Deviations from Plan

### 1. [Rule 3 — blocking] `test_the_gate_refuses_an_undocumented_composed_example` re-anchored

- **Found during:** Task 2, running the plan's own `<verify>` command.
- **Issue:** the control mutates the Makefile text in memory with
  `.replace("examples: example-00", "examples: example-99 example-00", 1)`.
  Task 1 deleted `example-00` from the aggregate, so the replace became a no-op
  and the control's own guard fired: `AssertionError: the fixture did not take`.
- **Fix:** the injection now anchors on `"examples: example-"` rather than on
  any particular member, with a docstring paragraph recording why. **Nothing was
  weakened** — the control still asserts `offenders == ["example-99"]`, and it
  was watched red twice more during S-B2 and green after.
- **Why this is not scope creep:** the plan's task-2 `<verify>` is
  `pytest tools/docs_tests/test_documented_commands_exist.py -q`, which cannot
  pass otherwise. The module is not in `files_modified`; it is named here
  explicitly for that reason. **No test was added and none removed** — see the
  criterion 7 accounting below.
- **Commit:** `1adc35a`.
- **Worth keeping:** the control's non-vacuity guard *caught its own fixture
  breaking*. That is the guard doing exactly the job the phase argues for.

### 2. [Rule 1 — bug] The `../README.md` link in the archived ext00 README

- **Found during:** Task 3, checking every relative link in a file this plan owns.
- **Issue:** the move left `[../README.md](../README.md)` resolving to
  `archive/examples/external/README.md`, which does not exist.
- **Fix:** re-pointed at `../../../../examples/external/README.md`, verified to
  resolve. In scope — the file is in `files_modified`.
- **Commit:** `3637abe`.

### 3. Two `Makefile` comments about `live-legs.yml`

Repaired in task 2 rather than task 1 (both describe workflows). *"`live-legs.yml`'s
three jobs"* → *"one remaining job"*; the `ci` composition comment now names the
three surviving live opt-ins. `Makefile` is in `files_modified`.

---

## Criterion 7 — the accounted delta for this wave

**ZERO tests added. ZERO tests removed. Measured by node-id set equality, not by
a total** (`D-IMPL-196`, amended by `D-IMPL-198` ruling 1):

```
tools/docs_tests   @6c2e004: 276 node ids   @HEAD: 276   diff: IDENTICAL
tests/examples     @6c2e004: 521 node ids   @HEAD: 521   diff: IDENTICAL
```

Collected in a detached read-only worktree at `6c2e004` and diffed line-for-line
against `HEAD`, so this is set equality on names rather than agreement on a
count. One test was **modified** (deviation 1) and it kept its node id.

**A carried figure is corrected here.** The orchestrator's briefing recorded
`tools/docs_tests` as *"274 passed, ONE failure"* (275). Measured at `6c2e004`
itself: **275 passed, 1 failed — 276 collected.** The one failure is
`test_requirement_ledger.py::test_every_cited_path_in_a_status_cell_resolves_as_written`
(EXAM-01, plan `23-11`'s), left untouched as instructed.

---

## Verification

| Check | Result |
|---|---|
| `pytest tools/docs_tests/test_documented_commands_exist.py -q` | **10 passed** |
| `pytest tools/docs_tests -q` | 274 passed, 2 failed — see note |
| `make docs-strict` | **exit 0 on all four steps** |
| `make examples` | **exit 0** — three legs, one content address `5d7bfa4…` |
| `make lint` / `python -m tools.lints --all` | **exit 0** |
| `pytest tests/examples/test_ext00_{serve_output,hardening,fixture_schemas}.py` | **57 passed** |
| `pytest tests/examples/test_hw1_harness_clients_retirement.py` | **16 passed** (post-commit) |
| `make -n examples` | succeeds |
| `make -n` on the fourteen | all fourteen fail |
| `make -n example-hw1-harness-clients` | succeeds |
| `git diff b87fe58..HEAD -- src/ runtime/ pyproject.toml` | **exactly the four lines from plan `23-06`** |
| `git diff b87fe58..HEAD -- Makefile` \| grep `s1` | **0 changed lines** |

**The two `tools/docs_tests` failures.** One is EXAM-01, expected still-red and
plan `23-11`'s. The other is `test_retirement_sweep.py::test_the_committed_report_is_current`,
which is red **by design at this point in the wave**: standing hazard 6 requires
the coupling report be regenerated **after** this SUMMARY is committed, because
the sweep walks `.planning/` and this SUMMARY is itself a coupling source. Wave
8 regenerated before committing its SUMMARY and left that test red. The
regeneration and its re-verification follow this commit.

**The four permitted `src/`/`runtime/` edits, verified rather than assumed:**

```
runtime/ccf_runtime/mcp/egress.py     | 2 +-
runtime/ccf_runtime/mcp/experience.py | 4 ++--
src/ccf/products/bind.py              | 2 +-
```

Four changed lines, every one an `examples/…` → `archive/examples/…` docstring
repoint from plan `23-06`. Nothing this plan wrote is in the fence.

---

## Handed forward — deferred item 7, verified and NOT fixed here

The orchestrator handed this wave a blocking-class finding logged by `23-08`:
**both stale-path witnesses read page SOURCES; neither reads the RENDERED body
a `--8<--` include pulls in.** Verified independently against the current tree,
not taken on report:

```
$ grep -rho "examples/08-e2e-demo/run.py" site --include=*.html | wc -l
3
```

Two sources, both still stale after this wave:

| Source | Line | Text | Pulled in by |
|---|---:|---|---|
| `archive/examples/08-e2e-demo/run.py` | 4 | ``` ``PYTHONPATH=src:runtime python examples/08-e2e-demo/run.py`` (or ``` | `public/tutorial/demo-walkthrough.md:305` (whole-file include) |
| `archive/examples/05-workflow-hitl/artifacts/task-definition.yaml` | 6 | `` # `examples/00-quickstart`. `` | `public/reference/artifacts/task-definitions.md:16` |

**The sharpest form is now sharper.** `demo-walkthrough.md` tells the reader to
run `archive/examples/08-e2e-demo/run.py` at lines 18 and ~313 — both verified
to run, and line 313's surrounding sentence was rewritten by *this* wave — and
then at line 305 inlines a docstring telling them to run
`examples/08-e2e-demo/run.py`, which does not exist. The page contradicts itself
across ~290 lines and every gate is green.

**NOT FIXED, and the reason is a scope boundary rather than a judgement about
the defect.** Neither `archive/examples/08-e2e-demo/run.py` nor
`archive/examples/05-workflow-hitl/artifacts/task-definition.yaml` is in this
plan's `files_modified` frontmatter. The orchestrator's instruction was explicit:
*"IF your plan does not authorise editing that file, do NOT widen scope on your
own judgement — record it, name the exact edit that is owed, and hand it
forward."*

**The exact edits owed:**

1. `archive/examples/08-e2e-demo/run.py:4` — in the module docstring, change
   `python examples/08-e2e-demo/run.py` to
   `python archive/examples/08-e2e-demo/run.py`.
2. `archive/examples/05-workflow-hitl/artifacts/task-definition.yaml:6` — in the
   header comment, change `` `examples/00-quickstart` `` to
   `` `archive/examples/00-quickstart` ``.

**And one live output string a fixer must decide about, not edit blind:**
`archive/examples/08-e2e-demo/run.py:1095` prints `examples/08-e2e-demo: OK` as
a run label. `grep -rn "08-e2e-demo: OK" tests/` is empty — unasserted today —
but it is stdout a reader sees, and it is the same stale spelling.

**The durable fix is a third witness**, not two string edits: nothing in this
repo reads the *rendered* body of an include. That is the same shape as
`D-IMPL-192`'s backlog item — a checked form whose check stops at a boundary
nobody noticed — and it is a gate this repository does not have.

---

## Findings for the close panel

1. **A `.PHONY` name without a rule makes `make <target>` exit 0 silently**
   (S-M1). Stronger than "nothing catches it until someone runs it": running it
   does not catch it either. Ten such names would have shipped had task 1's step
   2 been missed, and the coupling report files **zero** rows for `.PHONY`.
2. **The documented-commands gate's non-vacuity floor is ONE test, not two**
   (S-B3). `test_the_published_tree_names_commands` is insensitive to the
   `example-*` population, and the backward direction is now trivially
   satisfiable with a single member.
3. **`README.md` and `examples/external/README.md` are watched by nothing** —
   four gates run against a planted 404 and all four green (S-R1); no test or
   tool reads the charter at all.
4. **`CLNT-30`'s prose obligation is ungated** (S-R2). The only red under
   deletion was a working-tree dirtiness guard, proven a false positive by
   reproducing it with the correct marking in place.
5. **Deferred item 7 is still open** and is a gate-shaped gap, not two typos.

## Self-Check: PASSED
