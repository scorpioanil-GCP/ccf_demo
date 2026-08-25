# Deferred items — phase 23

Out-of-scope discoveries logged rather than fixed, per the executor's scope
boundary: an executor that closes a gap it discovers on the way past has turned
a planned wave into an unplanned one, and the fix ships without the decision it
needed.

## From plan `23-03`

**1. The `$schema` header gate is blind to a nested `artifacts/<subdir>/`, and
three shipped documents are in that blind spot today.**

`tools/check_schema_headers.py::ARTIFACT_GLOBS` matches one level under
`artifacts/`, so a document at `artifacts/<subdir>/*.yaml` is never discovered.
Measured on the pre-move tree:

```bash
# every file in the ten condemned trees whose FIRST line is a $schema header: 216
# of those, matched by examples/**/artifacts/*.yaml: 213
# NOT matched:
examples/03-harness-portability/artifacts/agents/agent-definition.yaml
examples/03-harness-portability/artifacts/agents/debt-profile.yaml
examples/03-harness-portability/artifacts/agents/policy-regime.yaml
```

All three carry `../../../../docs/schemas/…` headers and all three resolve
today, so nothing is currently wrong — but nothing is currently *checking*
either, and after the archive move all three need the same extra `../` as the
213 the gate does see, with the gate unable to say whether they got it.

- **Pre-existing.** Not caused by Phase 23; the glob has had this shape since
  plan `15-12`. Phase 23 only makes it consequential, because Wave 5's header
  repair will be gated by a check that cannot see three of its subjects.
- **Why it is not a one-character fix.** Deepening the pattern to
  `artifacts/**/*.yaml` puts `…/artifacts/agents` into
  `covered_artifact_directories`. Its parent is `…/artifacts`, which is not an
  example root (no `run.py`), so
  `tests/examples/test_artifact_schema_headers.py::test_every_covered_artifact_directory_sits_under_an_example_root`
  goes red on a correct tree. Closing the gap therefore means deciding what
  the bijection's right side means for nested artifact directories — a design
  call, not a widening.
- **Carried to Wave 5 as a caveat, not as work**: `23-05`'s header repair
  should repair all **216**, and should record that the gate's green covers
  213 of them.

**2. A lowered count floor is visible to exactly one thing, and it is the
wrong signal.**

Sabotage `S-F3` set `MINIMUM_IMPLEMENTATIONS` to `0`. The module itself passed
(17 passed) as the plan predicted. What the plan did *not* predict is that
`tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current`
FAILED — `tools/retirement_sweep.py::_floors` records each floor's value in the
coupling report, so lowering one makes the committed report stale.

- The detection is real but weak, and weak in a specific way: the message says
  *the report is stale*, not *a floor was lowered*. The reflex it invites is
  `retirement_sweep.py --report`, which turns it green and prints
  `floor 0, 14 witnesses, headroom 14` into a committed file nobody re-reads.
- **Not fixed here.** A gate that refuses a floor DECREASE would need to know
  the previous value, which means pinning floors in a second place — a real
  design decision about where the authority for a floor lives.

**3. The two scan roots in `tests/products/test_gate_two_call_shape.py` are
not as independent as their two constants suggest.**

`_plan_classes()` is derived from `SCANNED_TREES` and is consulted by
`_is_plan_construction`, so the binder scan — which reads
`BINDER_SCANNED_TREES` — depends on `SCANNED_TREES` as well. Measured under
sabotage `S-F2`: dropping `"examples"` from `SCANNED_TREES` alone cost the
binder scan one projecting body (14 → 13), even though `BINDER_SCANNED_TREES`
was untouched.

- **No defect today**, and no action owed by Phase 23: both constants were
  widened together, which is what the coupling requires. Recorded because a
  future reader widening one and not the other would get a partial result with
  no message saying why.

## From plan `23-04`

**4. The citation lint resolves a moved-away path by SUFFIX, so a stale
`examples/…` citation silently keeps passing after the archive move.**

`tools/lints/citations.py::resolve_cited` tries the literal path first and,
failing that, accepts a citation as a **suffix** of exactly one indexed repo
file. After the move, `examples/04-cross-process/producer_child.py` does not
exist — but `archive/examples/04-cross-process/producer_child.py` ends with
`/examples/04-cross-process/producer_child.py`, it is the only candidate, and
the citation resolves and is reported as *checked and passing*.

Measured, on the pre-move tree (`git archive HEAD~1`) against the post-move
tree, with the same checker and the `--base` flag proven live by an empty-tree
control (0 matched) and a `src`-only control (353 matched, 317 unresolvable):

```bash
PYTHONPATH=src:runtime .venv/bin/python -m tools.lints --citations --report --base <premove>
PYTHONPATH=src:runtime .venv/bin/python -m tools.lints --citations --report --base .
# both, byte-identical, all eight lines:
#   citations: 1762 matched in 1111 files (675 files exempt as dated records)
#     checked and passing: 1300   findings: 0   explicitly historical: 50
#     UNCHECKED — no anchor: 345  anchor not resolvable: 13
#     path ambiguous: 15          path unresolvable: 39
```

- **This is a SECOND, stronger hole than the one `D-07`/`D-IMPL-192` records.**
  That entry's measured case is a citation repointed at a *non-existent*
  `archive/…` path, which resolves to nothing and is therefore **unchecked**.
  This case is the mirror: a citation left at the *old* `examples/…` path,
  which resolves to the moved file and is therefore **checked and green**.
  Both are silent; only the second makes a green gate assert something false.
- **Consequence for `23-06`.** The four permitted `D-07` citation edits are
  still correct and still owed, but **no gate goes red if they are skipped**,
  and none goes red if they are made wrongly. `23-06` must not treat a green
  `make lint` as evidence that it made them.
- **Not fixed here.** Narrowing `resolve_cited` is a design call about what a
  suffix citation means — the fallback exists deliberately so `manifest.py`
  and `deployment/manifest.py` resolve — and tightening it would need a rule
  for when a citation's leading segment names a tree it must actually be in.
  That is the durable fix `D-IMPL-192` already backlogs, not a widening.

---

## Wave 5 (`23-05`) — three prose drifts nobody owns, and one that nobody may

**Not fixed here.** All four name paths the move relocated, none is a control,
and each sits in a file outside this plan's `files_modified`. Recorded rather
than fixed so `23-12` can rule on them with the population in front of it.

### 1. Five stale `examples/…` prose references inside `tests/examples/test_artifact_schema_headers.py`

```bash
grep -n 'examples/03-harness-portability/legs\|examples/external/00-hello-context\|examples/08-e2e-demo' \
  tests/examples/test_artifact_schema_headers.py | grep -v archive
#   55, 61, 62, 123, 519   (five lines; line 3 names plan 15-12's original scope and is history, not drift)
```

The module docstring and one control's docstring describe the tree in prose and
still say `examples/…`. The **constants** are re-pointed (this plan, task 2) and
every assertion is green; only the narration drifted. **This matters because no
later plan in the phase owns this module** — `grep -l test_artifact_schema_headers
.planning/phases/23-*/23-*-PLAN.md` returns `23-03` and `23-05` and nothing else.
Left alone because plan `23-05` scopes task 2 to *"the path strings only"*.

### 2. `examples/external/README.md:50` still lists `00-hello-context` as a resident

```bash
git ls-files examples/external   # examples/external/README.md   (the only survivor)
grep -n '00-hello-context' examples/external/README.md   # line 50, an index-table row
```

The tree moved to `archive/examples/external/00-hello-context`; the directory
it left behind keeps a README whose index table still lists it. `D-09` requires
the external example be *"marked historical"*, and this is the surviving half
of that surface. Not in any plan's `files_modified`.

### 3. Sixteen archived prose lines tell a reader to run a path that is gone

```bash
grep -rn 'python examples/' archive/examples/ | wc -l               # 16
grep -rn 'python examples/' archive/examples/*/[a-z]*.py \
  archive/examples/*/*/[a-z]*.py | wc -l                            # 6, in .py docstrings
```

e.g. the module docstring of
`archive/examples/04-cross-process/producer_child.py` — *"Run by `run.py`
as `python examples/04-cross-process/producer_child.py`"*. Task 1 was scoped to
*"only the `parents[N]` index; no other line in any of the four files moves"*,
and `D-04` deletes the `make` targets anyway, so the invitation-to-run prose is
arguably wrong in a second way. Untouched.

### 4. Three headered documents sit outside the header gate — **pre-existing, and NOT to be fixed here**

`archive/examples/03-harness-portability/artifacts/agents/{agent-definition,
debt-profile,policy-regime}.yaml` carry `$schema` headers (all three repaired by
this plan) but are **one level below** `ARTIFACT_GLOBS`' `*/artifacts/*.yaml`.
Pre-existing since plan 15-12. `tools/check_schema_headers.py::ARTIFACT_GLOBS` already
carries a note that deepening the glob *"would turn the bijection's right side red"*,
so this is a real decision, not a one-character fix. Already logged above by
plan `23-03`; repeated here only because this plan measured the exact three.

---

## Logged by plan 23-07

### 5. **BLOCKING FINDING, introduced by plan 23-06 and unreported there** — a Phase-20 fence goes RED on the `D-IMPL-192` permitted edit

`tests/examples/test_hw1_harness_clients_readme.py::test_criterion_seven_no_sdk_mechanism_ships_at_all`
runs `git diff --stat <phase-20-base>..HEAD -- src/` and asserts the result is
empty. It is not empty any more:

```bash
B=$(head -1 .planning/phases/20-client-access-from-three-harnesses-adk-anthropic-agent-sdk-a/20-BASE-COMMIT.txt)
git diff --stat $B..2256526^ -- src/    # EMPTY
git diff --stat $B..2256526  -- src/    #  src/ccf/products/bind.py | 2 +-
git diff --stat $B..HEAD     -- src/    #  src/ccf/products/bind.py | 2 +-
```

The bisect is exact: empty at `2256526^`, non-empty at `2256526` — plan
`23-06`'s first `D-07` citation edit. `23-06-SUMMARY.md` does not mention this
test; the wave verified its four edits against the resolver-seam gate and the
whole-tree run that would have surfaced it was not part of that plan.

**Why `D-11`'s "the scope fence is SAFE" (23-CONTEXT `code_context`) does not
cover it:** `D-IMPL-188` bounded the *`test_requirement_ledger.py`* assertions
to `base..951eb4a`. This assertion is a different one and is still `base..HEAD`,
unbounded, so every future commit is inside its window.

**Not fixed here, deliberately.** The test's own docstring instructs: *"A
non-empty result here is a **blocking finding to report**, never a reason to
narrow this assertion back to the client surface."* `D-IMPL-192` explicitly
authorised the edit that trips it, so the two documents now contradict each
other and the reconciliation is a ruling, not an executor's edit — bound the
window the way `D-IMPL-188` bound its twin, or record the permitted edit as an
allowance. **Dave's, and owed before the phase closes.**

### 6. Criterion 12's `25 of 31` does not reproduce — the measured figure is **19 of 31**

```bash
git ls-files tests/examples | wc -l                                      # 31
git grep -lE 'archive/examples/(00-quickstart|…|external/00-hello-context)|"archive" / "examples"' \
    -- tests/examples/ | wc -l                                           # 19
# and at PHASE_BASE, with the pre-move spelling, the same predicate:      19
```

`23-RESEARCH.md` §14.5 already flagged the figure as unverified by the
researcher. It is now measured, at `PHASE_BASE` and at `HEAD`, and it is 19.
`tests/examples` collects **519** (515 at `PHASE_BASE` plus wave 3's four named
additions). Plan `23-11` must write the measured figures into the `DOCS-17`
cell, not the carried ones.

### 7. A published page renders a bare `examples/` path from INSIDE an included body — and no witness in this phase can see it

Found at wave `23-08` while running the two re-pointed shell commands. The
two witnesses criterion 5 pits against each other — `mkdocs build --strict`
and `tools/docs_tests/test_no_stale_example_paths.py` — **both read page
SOURCES under `public/`.** Neither reads the *rendered* body a `--8<--` pulls
in. So a stale path living in the included file is published to the reader at
exit 0 on all four `docs-strict` steps.

Measured on the shipped tree, after this wave's re-point:

```
120 includes resolved across the published tree
  2 of them render a bare examples/ path;  4 stale lines in total

public/reference/artifacts/task-definitions.md:16
    -> archive/examples/05-workflow-hitl/artifacts/task-definition.yaml [+6]
       "# `examples/00-quickstart`."
public/tutorial/demo-walkthrough.md:304
    -> archive/examples/08-e2e-demo/run.py [+1]
       '"""examples/08-e2e-demo — raw data becomes governed context (DEMO-02).'
public/tutorial/demo-walkthrough.md:304
    -> archive/examples/08-e2e-demo/run.py [+4]
       '``PYTHONPATH=src:runtime python examples/08-e2e-demo/run.py`` (or'
```

Confirmed in the BUILT site, not only in the source:

```bash
grep -rho "examples/08-e2e-demo/run.py" site --include=*.html | wc -l   # 3
```

**The sharpest form of it:** `demo-walkthrough.md` now tells the reader to run
`archive/examples/08-e2e-demo/run.py` at lines 18 and 310 — both verified to
run — and then, at line 304, inlines a docstring telling them to run
`examples/08-e2e-demo/run.py`, which does not exist. The page contradicts
itself 286 lines apart, and every gate is green.

**Not fixed here, deliberately.** The fix is under `archive/examples/`, which
is outside this plan's `<files>`, and `run.py:1095` prints
`examples/08-e2e-demo: OK` as a run label — unasserted today
(`grep -rn "08-e2e-demo: OK" tests/` is empty) but a live output string.
Handed to `23-09`, which already owns the archive's prose obligations
(`CLNT-30`'s "marked historical") and the 13 `make example-*` strings on these
same pages.

**The durable fix is a third witness**, not a one-off edit: nothing checks the
*rendered* include body. That is a gate this repo does not have, and it is the
same shape as `D-IMPL-192`'s backlog item — a checked form whose check stops at
a boundary nobody noticed.

### 8. `tools/measure_examples.py` carries three stale `examples/…` references, two of them live — visible again, still nobody's to fix

**Found by plan `23-10`, by the floor rather than by reading.** Re-pointing the
schedule at `archive/examples/…` made `test_every_known_coupled_file_is_found`
go red naming exactly one file: `tools/measure_examples.py`. Its three
references had been rows all along, and they spell the pre-move form:

| Line | Text | Shape |
| --- | --- | --- |
| 261 | `a plan rewriting ``examples/01-agent-basics`` passes` | `docstring` (documentary) |
| 308 | `" (e.g. examples/01-agent-basics). Each example-rewrite plan"` | `string-literal` (**live** — argparse help) |
| 320 | `" examples/00-quickstart."` | `string-literal` (**live** — argparse help) |

All three name a directory that is no longer there. The tool's `--example`
argument advertises two paths a user cannot pass.

**Not fixed in `23-10`.** `tools/measure_examples.py` is not in this plan's
`files_modified`, and — more to the point — *fixing* it does not restore the
floor entry, because the floor asserts that the sweep FINDS the file. Editing
the help text discharges the coupling and drops the file off the floor by the
other route. That is a real gap in `KNOWN_COUPLED_FILES`' design (it cannot
tell "the sweep narrowed" from "the coupling was discharged"), and it is the
same shape as the `dissolution_problems` idiom already in the module for a
different subject.

**What `23-10` did instead** was make the sweep stop being able to lose the
reference: `Retirement.former_path` matches a moved tree at BOTH spellings.
**45 rows across 20 files** name a former spelling today — every one of them an
old-form reference that the re-point alone would have made invisible at exit 0.

**What that does NOT do, said plainly so nobody reads it as item 7's fix:** the
`former_path` matching is invisible inside `archive/examples/**`, because those
files are now themselves under a retiring path and their references are dropped
as deleted-with-their-source (**248** such hits, up from 134). Item 7's two
stale lines — the fourth line of `archive/examples/08-e2e-demo/run.py`'s module
docstring, and line 6 of
`archive/examples/05-workflow-hitl/artifacts/task-definition.yaml` — are both
inside the archive and are still seen by nothing. **Item 7 is CARRIED
UNCHANGED**, with the same edits owed and the same durable fix: a third witness
that reads rendered include bodies.

**Owed to:** whichever plan re-points `tools/measure_examples.py`'s help text,
which must also decide what `KNOWN_COUPLED_FILES` should say once the coupling
is genuinely discharged rather than merely re-spelled.

---

## 9. `.planning/ROADMAP.md`'s Phase 23 GOAL PROSE still carries the clause `D-IMPL-191` ruling 4 amended (found at `23-11`)

**Not a Success Criterion, and not in `23-11`'s authorised subject.** Task 3 of
`23-11` authorises the Phase 23 *progress row* and the Progress table; it
forbids authoring, editing, renumbering or re-wrapping a criterion. The goal
prose is neither, so it is NAMED here with the edit owed rather than widened
into.

**The defect.** The phase-block goal paragraph reads:

> On completion `DOCS-17` is verdicted **`Partial`** for the first time, on the
> seam `D-IMPL-189` point 3 names: limb done — **out of live CI**, sources
> preserved under archive, includes re-pointed, strict build green; limb owed —
> full retirement and the re-cut against a replacement surface.

`D-IMPL-191` ruling 4 AMENDED exactly that clause — **OLD** *"out of live CI"*,
**NEW** *"out of the `examples:` aggregate ... and still exercised by the test
leg"* — for the measured reason that 19 of 31 `tests/examples` files still read
the archived sources and 2 still spawn a process against them. So `ROADMAP.md`
today asserts, in prose, the exact claim the ledger cell shipped at `23-11` is
forbidden to make. Criterion 12 is correct; the goal paragraph above it is not.

**A second, smaller instance in the same file.** `STATE.md`'s `## Current
Position` block still reads *"SIXTEEN Success Criteria LOCKED"* (there are
eighteen, per `D-IMPL-194`) and *"25 of 31 `tests/examples` files"* (measured 19
at both ends; `D-IMPL-195` ruling 3 and `D-IMPL-198` ruling 2). Both are
pre-planning text preserved as a dated record, which is defensible — but
neither says it is dated, and a reader arriving at the Position block gets a
figure two rulings out of date with nothing marking it.

**Owed edits, named:**

| File | What it says | What it should say |
| --- | --- | --- |
| `.planning/ROADMAP.md`, Phase 23 goal paragraph | `limb done — out of live CI` | `limb done — out of the `examples:` aggregate, sources preserved under archive and still exercised by the test leg` (`D-IMPL-191` ruling 4) |
| `.planning/STATE.md`, `## Current Position` Phase 23 entry | `SIXTEEN Success Criteria LOCKED` | `EIGHTEEN` (`D-IMPL-194`), or a date-stamp marking the sixteen as what was true at the sitting |
| `.planning/STATE.md`, same entry | `25 of 31 tests/examples files` | `19 of 31`, measured identical at `b87fe58` and at `HEAD` (`D-IMPL-195` r3, `D-IMPL-198` r2) |

**Owed to:** `23-13`, the §3.1 close, which is the plan that already owns the
phase record. **Nothing gates any of the three** — no test reads the goal
paragraph or the Position block, which is why they went two rulings stale
without a red.

---

## 10. Nothing gates a ledger cell's WORDING, and the two channels can carry different verdicts for the same row (measured at `23-11`)

Recorded because `23-11` predicted it, ran it, and confirmed it — and because a
later reader should not have to guess whether `D-06`'s wording constraint was
machine-enforced. It is not.

| Sabotage | Mutation | Result |
| --- | --- | --- |
| S-L2 | the `DOCS-17` cell rewritten to claim *out of live CI*, in BOTH channels | `tools/docs_tests/test_requirement_ledger.py` **114 passed**, `tools.lints --all` exit 0 |
| S-L3b | one PROSE character in the `CLNT-17` row (`the` -> `teh`) | **114 passed** — caught only by the content-hash anchor criterion 13 mandates |
| S-L4 | `DOCS-17` left `Not built` in the table channel while the checkbox channel reads `Partial` | **114 passed**, with the two channels openly disagreeing about one row's verdict |
| S-D8a | the `D-08` figure updated in one channel only | **114 passed**, lints exit 0 |
| S-D8b | the pin overwritten 111 -> 122 with the movement sentence deleted | **114 passed**, lints exit 0 |

`cell_verdicts` enforces *at most one verdict per cell*; nothing enforces *the
same verdict across the two cells of one row*. That is `R-alpha`'s neighbourhood
— a shape wider than what the module's criteria name — and it is the reason
criterion 6 says *"at both ends"* and criterion 12 names the forbidden wording:
both are judgement-enforced, by construction, today.

**Owed to:** nobody, until a phase is commissioned for it. A cross-channel
verdict-equality assertion is cheap and would close S-L4 and S-D8a at once; the
wording constraints (S-L2, S-D8b) are not mechanisable without a vocabulary
ruling of the kind `R-alpha` already waits on.

---

## Added at the §3.1 close (plan `23-13`)

Items 1-4 and 7-12 above stand as written. Items 5 and 6 remain RULED and
CLOSED. **Item 9 is now DISCHARGED** — all three edits it named were made at
`a8c3af9`, marked inline rather than silently, and its own closing observation
("Nothing gates any of them") is carried forward as the reason it went two
rulings stale.

| # | What | Owed |
|---|---|---|
| **13** | **NEW.** `tools/docs_tests/test_retirement_sweep.py::scheduled_path_problems` clause 4 rejects a `former_path` that RESOLVES, but not one swapped to a different spelling that also does not resolve. Measured: replacing every `former_path` with `former_path + "-typo"` costs **270 -> 225 rows and 13 source files**, and `scheduled_path_problems` returns EMPTY. The mutation IS watched — `test_every_known_coupled_file_is_found` goes red because `tools/measure_examples.py` is among the 13 lost — so this is a diagnosis gap, not a blindness | a fifth clause inside the predicate, so the refusal names its own cause instead of relying on a neighbouring floor. Raised by codex at the close and downgraded from BLOCKING by measurement |
| **14** | **NEW.** Nothing asserts a NON-EMPTY archive-side result on the REAL tree for either the artifact discovery or the lint walk. Both are held by set-equality membership plus synthetic-tree behavioural controls, which is why gemini's and cursor's stronger claims were REJECTED — but the narrow residue is true, and it is the same shape as the already-backlogged `D-IMPL-192` | a design call on standing real-tree non-vacuity floors, not a Phase 23 obligation. Written down here so the shape is not re-found a third time |
| **15** | **NEW.** The three re-pointed seam docstrings say the archived call sites "run in CI". Verified TRUE — `tests/examples/test_cross_process_output.py` spawns a process and `tests/examples/test_ext00_serve_output.py` exec_modules the archived source, both in the `test` job, with criterion 8's control proving each RUNS. But a reader checking the claim would look at `make examples` first and find nothing | one qualifying clause naming the `test` job, in whichever plan next touches those three docstrings. NOT taken here: criterion 14 fixes the `src`/`runtime` edit budget at FOUR and this would be a fifth |
| **16** | **NEW, and it is about this record rather than the tree.** The close-time panel payload was hand-assembled and SIX subject classes were left out of it — `tests/examples/`, `tests/lints/`, `tests/products/`, the 265 moved files, all of `public/`, and the phase's own plans. Two of the four false findings (`REJ-2`, `REJ-3`) are directly attributable to omission #1, and `REJ-1` is attributable to a census line in the payload that I measured wrongly | a close-time payload assembled from a derived subject list rather than by hand, for whichever phase closes next. The omissions are named in `23-CLOSE-REVIEWS.md` § 1 rather than left for a reader to infer |
