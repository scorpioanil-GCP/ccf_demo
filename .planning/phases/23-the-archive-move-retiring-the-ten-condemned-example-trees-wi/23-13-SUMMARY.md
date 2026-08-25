---
phase: 23-the-archive-move-retiring-the-ten-condemned-example-trees-wi
plan: 13
subsystem: phase close — the CLAUDE.md §3.1 review protocol
tags: [close, cross-ai-panel, depth-pass, blocking-triage, criterion-10, two-channel-drift, own-defect-class]
status: complete
requires:
  - phase: 23-12
    provides: the eighteen-criterion evidence roll-up and the closing six-leg pipeline measurement
provides:
  - "23-CLOSE-REVIEWS.md — the close-time panel record, on the SHIPPED tree, distinct from any pre-execution plan review"
  - "three blocking findings fixed in-phase, each independently re-sabotaged"
  - "four false panel findings kept in the record AS REJECTED, with their refuting commands"
  - "the phase presented to Dave, and STOPPED"
affects:
  - "tools/docs_tests/test_retirement_sweep.py (criterion 10 actually discharged)"
  - ".planning/{ROADMAP,STATE,REQUIREMENTS}.md (four stale claims corrected)"
  - "docs/surface/examples/RETIREMENT-COUPLINGS.md (regenerated LAST)"
tech-stack:
  added: []
  patterns:
    - "per-tree coverage asserted rather than summed, with the count floor KEPT because it names a different diagnosis"
    - "close-time panel payload INLINED, with its own omissions enumerated as a finding"
    - "a rejected finding kept as rejected, with the command that refuted it"
key-files:
  created:
    - ".planning/phases/23-.../23-CLOSE-REVIEWS.md"
    - ".planning/phases/23-.../23-13-SUMMARY.md"
  modified:
    - "tools/docs_tests/test_retirement_sweep.py"
    - "tools/docs_tests/test_no_stale_example_paths.py"
    - "tools/publish_scan_tests/test_publish_scan.py"
    - "tests/examples/test_artifact_schema_headers.py"
    - ".planning/ROADMAP.md"
    - ".planning/STATE.md"
    - ".planning/REQUIREMENTS.md"
    - ".planning/phases/23-.../deferred-items.md"
    - "docs/surface/examples/RETIREMENT-COUPLINGS.md"
decisions:
  - "Criterion 10 was NOT discharged by the shipped control: its own named mutation could not turn it red. Fixed by asserting per-tree coverage; the count floor kept because a shrunken row set and a tree gone dark are different diagnoses."
  - "The `make ci` single-command deviation is CARRIED TO DAVE, not resolved. ~870s against a 600s foreground cap; backgrounding is the move criterion 15 exists to forbid."
  - "The panel payload's own omissions are recorded as deferred item 16, because two of the four false findings are directly attributable to one of them."
requirements-completed: []
metrics:
  duration: "one wave"
  completed: "2026-08-25"
  tasks: 3
---

# Phase 23 Plan 13: The §3.1 Close — Panel, Depth Pass, and a Criterion That Was Not Discharged

**Three reviewers, all proven to have read. Three blocking findings, all fixed
in-phase and re-sabotaged. Four confident, well-formatted, FALSE findings kept
in the record as false — two of them caused by my own payload. And criterion 10,
which the phase believed it had discharged, could not turn red on the mutation
its own text names.**

---

## THE HEADLINE: CRITERION 10 WAS NOT DISCHARGED

Criterion 10 reads:

> Archived paths **STILL COUNT** as live couplings, **proven by a control:
> suppressing an archived path's coupling row is watched RED**, so the sweep
> cannot go blind to the archive — the Phase 22.1 defect class arriving one tree
> over.

Against the shipped `tools/docs_tests/test_retirement_sweep.py::archive_sweep_problems`,
that sentence was **false**. Measured:

```
archive rows at HEAD: 131   scheduled archived trees: 10
per-tree row counts:  18 / 3 / 12 / 21 / 29 / 19 / 2 / 9 / 4 / 14

TEST A  21 rows, ALL from archive/examples/03-harness-portability   -> PASSES (empty) -- BLIND
TEST B  every one of that tree's 21 rows suppressed, 110 rows left  -> PASSES (empty) -- BLIND
```

The check compared a row **count** against the number of scheduled archived
trees. Nine of ten trees could contribute zero rows and it returned empty. The
module's own docstring said the quiet part out loud — *"The per-tree coverage is
**recorded rather than asserted**"* — and nowhere recorded it.

**This is the phase's own defect class arriving inside the control commissioned
to prevent it.** A tool that reports clean because it did not look, one level up:
the *gate* on the sweep's blindness was itself blind.

Raised independently by **codex F-1** (BLOCKING), **cursor F-1/F-3** (advisory),
and the depth pass. Fixed at `d6cbca7`.

### The fix, and why the count floor stayed

Per-tree coverage is now asserted. **The count floor is kept**, because the two
clauses name different diagnoses — *a shrunken row set* versus *a tree gone
dark* — and a refusal that cannot tell them apart sends its reader to the wrong
place.

**Re-sabotaged in BOTH directions**, which is what proves neither clause is
decoration:

| Mutation | Prediction | Observed | Verdict |
|---|---|---|---|
| per-tree clause deleted, count floor kept | the two NEW cases go red; the four pre-existing stay green | **2 failed, 4 passed** — exactly the two new cases, on the `have ZERO coupling rows` fragment | **CORRECT** |
| count clause deleted, per-tree clause kept | the two pre-existing count cases go red | **2 failed, 4 passed** — the zero-rows and one-stray-row cases | **CORRECT** |

Backup held **outside the tree** and `diff` confirmed byte-identical after each
restore (standing hazard 2).

**The new control cannot go vacuous either:** its victim tree is derived from the
schedule and never spelled, it asserts the victim actually has rows, and it
asserts the surviving total stays **above** the floor — otherwise the count
clause fires first and the per-tree clause goes unproven.

### The retired escape clause

The docstring used to say *"a tree whose last reference is legitimately
discharged should not turn this red"*. That case cannot arise silently: deletion
is still OWED for every scheduled row (`D-IMPL-191` ruling 3), and a tree whose
last reference is genuinely discharged is a tree leaving the schedule — so the
row leaves `archived` with it and the clause stops applying by itself.

---

## THE PANEL — three reviewers, all PROVEN to have read

**The panel is the set of available external AI reviewers with the executing
model excluded.** It is not a command invocation.

**The payload was assembled BY HAND from the shipped subjects** — the default
`review.md` workflow gathers `*-PLAN.md` / `*-CONTEXT.md` / `*-RESEARCH.md` and
asks for a *plan* review, right before execution and wrong at close. A
hand-assembled close-time payload is **conforming, not a deviation**, and it is
said so in the record with every omitted subject named.

**117,567 bytes, nine subjects, INLINED** rather than pointed at, because
codex's `bwrap` sandbox on this host can exit 0 having read nothing.

| Reviewer | Exit | Bytes | Citations resolve? | Verdict |
|---|---:|---:|---|---|
| codex | 0 | 2,970 | 4 symbols, **all resolve**; quotes verbatim from the payload | **REVIEWED** |
| cursor | 0 | 7,766 | 7 symbols, **all resolve** | **REVIEWED** |
| gemini | 0 | 3,398 | 3 symbols + a byte-exact regex, **all resolve**; the one file it cited outside the payload **exists** | **REVIEWED**, with one extrapolation |

Neither of the two historically recorded failure modes fired: codex read, and
gemini invented no symbol. Its one weak finding is an *extrapolation from a real
quote*, not a fabrication — a distinction worth keeping because the remedy
differs.

---

## THE FOUR FALSE FINDINGS, AND WHOSE FAULT THEY WERE

Four of eleven distinct panel findings were false. **They are kept in
`23-CLOSE-REVIEWS.md` as rejected, with the commands that refuted them.**

**Two are directly my fault**, and that is the more useful half of this section:

- **REJ-2** — cursor said `ARTIFACT_GLOBS` ships without the membership-equality
  pattern the other widened roots got. It ships **exactly that pattern**, at
  `tests/examples/test_artifact_schema_headers.py::test_the_discovery_globs_reach_the_live_tree_and_the_archive`.
  **I did not inline that file.**
- **REJ-1** — codex found the header comment's `216` contradicted my payload's
  census of `220`. The comment is right: 220 files *contain* the header string,
  **216 are artifact YAML documents** and four are READMEs quoting the
  convention. **I measured the census line wrongly before inlining it, and the
  reviewer reasoned correctly from a false premise I supplied.**

A payload defect is indistinguishable from a reviewer defect unless it is
checked. Both were found only by re-measuring, and both are recorded as
**deferred item 16**.

The other two: **REJ-3** (gemini's two BLOCKING claims that the discovery and
the lint walk go silent over the archive — measured, `discover(require_all=True)`
returns **10 archived directories against 1 live one**), and **REJ-4** (gemini
placing false capability prose in `docs/09-ruling-batch-minicycle.md`; the file
exists and carries two incidental mentions, nothing of the kind).

**REJ-4's adjacency was checked anyway, because that is what the finding was
worth** — all five documents referencing `live-legs.yml` examined. `README.md`
and the `Makefile` are accurate; `docs/PHASE_I5_GATE.md` names three deleted
`make` targets and is an append-only historical gate record, disposed of the way
the `D-GATE` entries are. **Recorded as a checked-and-clean, not as silence.**

---

## THE OTHER TWO BLOCKERS — both found only by the depth pass

`.planning/` was not in the payload, so neither was visible to the panel.

### B2 — the two-channel drift class arriving for real

`DOCS-01`'s channel-1 cell claimed the adopter's guide *"teaches `make
example-00`, `-01`, `-02`, `-05`, `-06` and `-ext-00`"*. Criterion 3 **deleted**
those targets; Wave 8 re-pointed the guide to direct `archive/examples/`
invocations.

```
grep -c "make example-" public/tutorial/adopters-guide.md   ->  0
```

**Both channels were checked and only channel 1 was false.** Channel 2 says
*"teaches the example trees `DOCS-17` condemns"*, which is still true.
`test_requirement_ledger.py` reads **114 passed** across the false state and the
corrected one alike — **S-D8a/S-D8b, arriving on a row nobody was watching.**

### B3 — three edits owed to this plan by name, unmade

`deferred-items.md` item 9 assigned three edits to `23-13`, and its own closing
sentence is the finding: *"Nothing gates any of them — which is how they went
two rulings stale without a red."*

| Claim | Observed | Ruling it contradicted |
|---|---|---|
| `.planning/ROADMAP.md` **goal prose**: *"limb done — out of live CI"* | 1 hit | `D-IMPL-191` r4 — and **criterion 12 forbids the shipped cell from saying it** |
| `.planning/STATE.md`: *"SIXTEEN Success Criteria"* | 1 hit | `D-IMPL-194` — eighteen since before Wave 1 |
| `.planning/STATE.md`: *"25 of 31"* | 1 hit | `D-IMPL-195` r3 — **19**, re-measured 19 at `PHASE_BASE` and 19 at `HEAD` |

All three corrected at `a8c3af9`, **marked inline rather than made silently**.

**Guarded during the edit, by measurement:** `CLNT-17`'s row hash
`5bcc68ca…` identical before and after (criterion 13); `DOCS-17`'s cells
byte-identical in **both** channels (criterion 12); **all eighteen criterion
lines byte-identical**; 155 numbered lines still parse **one per line**.

---

## THREE PIECES OF PROSE THIS PHASE'S OWN MOVE MADE FALSE

Advisory, fixed in-phase at `2044ec1`. No mechanism changed. Found by a
mechanical absence/future-tense sweep of every changed file — **19 candidates
read in context, 3 false, 16 accurate historical statements left alone.** This is
the population a diff-scoped review structurally cannot see, because the
sentences sit hundreds of lines from any edit.

| Where | The false sentence | Measured |
|---|---|---|
| `test_no_stale_example_paths.py::test_a_correctly_re_pointed_archive_path_yields_no_offenders` | *"The repo has no `archive/` yet"* | ten trees since Wave 4. The synthetic root is **KEPT** with a stronger current reason: it is the only way to hold the precondition that the STRIPPED form must not exist, now that `examples/` still holds four survivors |
| `test_artifact_schema_headers.py::test_the_discovery_globs_reach_the_live_tree_and_the_archive` | *"because the archive does not exist"* | `discover(require_all=True)` -> **10 archived / 1 live** |
| `test_publish_scan.py::test_the_existing_roots_are_still_admitted` | *"nothing that was permitted moved"*, witnessing `examples/00-quickstart/run.py:boot` | **a control witnessing a subject SWAPPED rather than removed** — the phase's own category-3 question answered against itself. Re-pointed at two witnesses confirmed present on disk |

---

## THE PROOF FIRED ON ME

Re-deriving chunk 4 at this HEAD with `ls -d tests/*/` collected **1143** against
Wave 12's 1184:

```
sum = 1007 + 1056 + 986 + 1143 = 4192      full = 4233      SHORT BY 41
```

**The sum property caught it immediately.** Cause: `ls -d tests/*/` returns
directories only, and **41 tests live in files directly under `tests/`** —
`test_smoke.py`, `test_surface_completeness.py`, `test_surface_drift.py`,
`test_surface_shape_capture.py`.

The same defect class the phase spent itself hunting — *a subject the walk did
not reach* — arriving in the close's own measurement machinery. Recorded rather
than silently corrected, because **the proof working is the evidence that
criterion 15 is not ceremony.**

---

## THE PIPELINE, RE-RUN IN THE FOREGROUND AFTER EVERY FIX

`make -n ci` re-printed at this HEAD is the **same ten commands** Wave 12
recorded — the leg set did not change.

| Leg | Exit | Measured |
|---|---:|---|
| `lint` | **0** | `tools.lints --all`, silent |
| `typecheck` | **0** | `Success: no issues found in 211 source files` |
| `test` | **0** | four **foreground** chunks: **4115 passed / 118 skipped / 0 failed**; `4115 + 118 = 4233` = the full `--collect-only` total. Unchanged from Wave 12 — this plan's three test-file edits are docstrings and witnesses, not new `tests/` cases |
| `gate-tools` | **0** | **415** + **341**. The `341` is `339 + 2`: **the two new B1 control cases, each named to this plan.** No addition is unaccounted |
| `examples` | **0** | exactly one example; three harness legs at one content address `5d7bfa49f5b3…`; `legs compared 3` |
| `docs-strict` | **0** | four steps, each exit code read **with no pipe**: 0 / 0 / 0 (`Documentation built in 3.48 seconds`) / 0 |

**Coverage proof re-taken at this HEAD, all three properties:**
`1007+1056+986+1184 = 4233` = full; set-equality **both directions 0**; all six
pairwise intersections **0**.

---

## Deviations from Plan

### 1. `[Rule 3 — blocking]` B1: criterion 10 was not discharged, and the plan could not complete around it

The plan's task 2 requires every blocking finding fixed in-phase and
independently re-sabotaged. This one changed shipped verification mechanism
(`archive_sweep_problems`), which is more than a review plan usually authorises
— but §3.1 is explicit that blocking findings are fixed **inside** the phase,
and a criterion left undischarged is exactly a blocking finding. Full account
above. Commit `d6cbca7`.

### 2. `[Rule 2 — missing critical correctness]` B2 and B3 touched `.planning/` tracking files

Three of the four corrections were **owed to this plan by name** (deferred item
9). The fourth (`DOCS-01`) was found here. Editing the requirement ledger and
the roadmap is outside a review plan's usual subject, so each edit was
constrained and then **measured**: `CLNT-17` byte-identical, `DOCS-17` both
channels byte-identical, all eighteen criteria byte-identical, criteria still
one per line, ledger gate 114 passed. Commit `a8c3af9`.

### 3. NOT A DEVIATION, said out loud anyway: the panel payload was hand-assembled

`CLAUDE.md` §3.1 explicitly permits it. **Every omitted subject is named** in
`23-CLOSE-REVIEWS.md` § 1, and the omissions are carried as deferred item 16
because two false findings are traceable to one of them.

### 4. CARRIED TO DAVE, NOT DECIDED: `make ci` was not run as one command

The pipeline measures **≈870 s** against a **600 s** foreground tool cap. The
only way to fit it whole is to background it — **exactly what criterion 15
exists to forbid**, because a killed background run is indistinguishable from a
pass. Wave 12 reproduced that: a chunk killed at 25 s returned `137` to a direct
`wait`, printed **zero** pytest summary lines, and read as `0` through a pipe.

Discharged as its own ten foreground commands with `make -n ci` printed as proof
the ten are complete. **This is Dave's to rule on, and this plan does not rule
on it.**

---

## Triage

| Verdict | Count | Ids |
|---|---:|---|
| BLOCKING — fixed in-phase, each re-sabotaged | **3** | B1, B2, B3 |
| ADVISORY — fixed in-phase | **3** | ADV-FIX-1/2/3 |
| ADVISORY — carried (deferred items 13–16) | **4** | ADV-1..4 |
| NOT NEW (restates a briefed known finding) | **1** | gemini F-4 |
| REJECTED as false | **4** | REJ-1..4 |

**Zero unfixed blocking findings. No blocking finding required a ruling Dave has
not made, so no new `D-IMPL-NN` is opened and the phase does not stop on one.**

---

## Were the panel and the depth pass disjoint? NO — and it is recorded, not smoothed

Phase 22's close proved them disjoint by measurement. **This close did not
reproduce that.**

- **B1 was found by BOTH**, and *first by the panel*.
- **B2, B3 and DP-2** were the depth pass's alone — `.planning/` and the
  tracking files were not in the payload.
- **ADV-FIX-1 and ADV-FIX-3** were the panel's alone (cursor).
- **All four rejections** were the panel's alone.

The honest reading: the panel's convergence *raised confidence* in a finding the
depth pass would have reached anyway, and the depth pass found the drift the
panel could not see because those files were not given to it. **They overlapped
on the one thing both could see** — which is an argument for a wider payload
next time, and it is written down as deferred item 16.

---

## Known Stubs

**None.** No hardcoded empty value, placeholder string or unwired component was
introduced by this plan. The three test-file edits are docstrings and witness
paths; the one mechanism edit adds an assertion.

---

## Threat Flags

**None.** No network endpoint, auth path, file-access pattern or schema at a
trust boundary was created or modified. The threat register's five mitigations
(T-23-55..59) are each discharged in `23-CLOSE-REVIEWS.md`: the payload was
inlined and every reviewer's reading proven (T-23-55); every finding verified
before being recorded or acted on, with rejections kept (T-23-56); the payload
enumerated as shipped subjects with omissions named (T-23-57); no `D-GATE-23`
entry and no merge (T-23-58); the close is its own plan and its own wave
(T-23-59). T-23-SC stands accepted — no package was installed.

---

## What this plan did NOT do, deliberately

- **No `D-GATE-23` entry.** Approval authority is Dave's alone.
- **No merge of `phase-23` to `main`, and no push.**
- **No `ROADMAP.md` phase-complete marking.**
- **No `state.*` or `roadmap.*` GSD writer invoked** — every tracking edit was
  made by hand (standing hazard 5).
- **No ruling on the `make ci` deviation.** Carried.
- **`CLNT-17` and the `s1` pair untouched**, proven by hash rather than by
  intent.

---

## Self-Check: PASSED

Every claim above checked against the tree rather than asserted.

| Claim | Command | Result |
|---|---|---|
| `23-CLOSE-REVIEWS.md` exists and is non-empty | `test -s …` | **FOUND** |
| `23-13-SUMMARY.md` exists | `test -f …` | **FOUND** |
| the four commits exist | `git log --oneline --all \| grep` | **FOUND** ×4 — `d6cbca7`, `2044ec1`, `a8c3af9`, `928ed8e` |
| no anchored `path.py:LINE` citation in either document | `grep -nE '…\.py:[0-9]+'` | **NONE** in both — `D-IMPL-114`/`D-IMPL-123` ceiling of ZERO held |
| `CLNT-17` byte-identical | content hash before/after | `5bcc68ca…` = `5bcc68ca…` |
| the eighteen criteria byte-identical | per-criterion sha256 | **all eighteen identical** |
