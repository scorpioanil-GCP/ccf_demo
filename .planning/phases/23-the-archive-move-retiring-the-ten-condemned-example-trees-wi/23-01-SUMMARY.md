---
phase: 23-the-archive-move-retiring-the-ten-condemned-example-trees-wi
plan: 01
subsystem: phase opening and base measurement
tags: [DOCS-17, phase-base, D-IMPL-195, retirement-schedule, live-leg-targets, criterion-13]
status: complete
requires:
  - phase: 22.1
    provides: the fail-closed retirement sweep this phase's criteria 9-11 rely on
provides:
  - the `phase-23` branch, cut from `main` at `b87fe58`
  - PHASE_BASE pinned and every Wave-1 base figure re-measured with its command
  - Dave's two pre-execution rulings recorded verbatim by option id, for 23-09 and 23-10 to read
  - three measured corrections to figures the plan and the research carried
affects:
  - 23-02 (its task 1 full-suite re-measure starts from the collect total pinned here)
  - 23-09 (reads the `delete-four` ruling)
  - 23-10 (reads the fourteen-row ruling)
  - every later plan (PHASE_BASE is the diff base for criteria 1, 13 and 14)
tech-stack:
  added: []
  patterns: [every-figure-carries-its-command, content-only-hash-not-position]
key-files:
  created:
    - .planning/phases/23-the-archive-move-retiring-the-ten-condemned-example-trees-wi/23-01-SUMMARY.md
  modified:
    - docs/surface/examples/RETIREMENT-COUPLINGS.md  # generated; +1 row for this summary
decisions:
  - "The coupling report is regenerated in this plan too, not only at the phase end: writing any .planning/ file staleness the report (Rule 3 deviation)"
  - "PHASE_BASE = b87fe58 (tip of main, 3 commits ahead of origin/main at efa0044)"
  - "Criterion 13's anchor is the ROW-ONLY hash 5bcc68ca..., not the broad `grep 'CLNT-17'` hash the plan specified — the broad form hashes 13 lines and criterion 12 will change one of them"
  - "The published-reference regex must NOT require a trailing slash: with it the figure is 105/102/3, without it the pinned 111/102/9"
requirements-completed: []
metrics:
  duration: ~35 min
  completed: 2026-08-24
  tasks: 3
  commits: 1
---

# Phase 23 Plan 01: Open the phase, pin the base, record the rulings — Summary

**`phase-23` cut at `b87fe58`; every Wave-1 base figure re-measured rather than
carried, with three of them coming back different from what the plan or the
research predicted; and Dave's two pre-execution rulings (`D-IMPL-195` rulings 1
and 2) recorded verbatim for plans 23-09 and 23-10 to read rather than
remember.**

**Tasks 2 and 3 were `checkpoint:decision` blocks in the plan as drafted. Dave
ruled both BEFORE execution.** Nothing was presented, nothing was asked, and no
option was selected by the executor. Both tasks were executed as what they now
are: a record-and-confirm.

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-08-24T18:02Z
- **Tasks:** 3 of 3
- **Tracked files modified:** 1 authored (`23-01-SUMMARY.md`) + 1 regenerated
  (`docs/surface/examples/RETIREMENT-COUPLINGS.md`, +1 row). Zero **source**
  files.

---

## PHASE_BASE

```
PHASE_BASE = b87fe58c3ee82333accc4eb5dbc8644a0bc8e72b
```

```bash
git checkout -b phase-23        # → Switched to a new branch 'phase-23'
git rev-parse --abbrev-ref HEAD # → phase-23
git rev-parse HEAD              # → b87fe58c3ee82333accc4eb5dbc8644a0bc8e72b
```

`b87fe58` is the tip of `main`: *"plan(23): D-IMPL-195 — three rulings applied;
criteria 3 and 12 amended"*. Per `CLAUDE.md` §2.2 phase work happens on a phase
branch and the merge to `main` happens at the `D-GATE-23` entry.

**`main` is three commits ahead of `origin/main`** (`git rev-parse origin/main`
→ `efa0044`). The three unpushed are `f56cfae`, `695a00e`, `b87fe58` — all
planning commits for this phase. Noted because criterion 13 pins `CLNT-17`'s
state at **`efa0044`**, not at `PHASE_BASE`; both were measured and they agree
(below).

### Working tree at PHASE_BASE

```bash
git status --porcelain
# ?? references/CCF_SDK_DE_REQUIREMENTS.md
# ?? references/CP-SPEC-001_Counterparty_Reference_Snapshot_v2.md
# ?? references/Context_Product_Specification_Standard_v0-3.md
```

Exactly the three untracked `references/*.md` the plan predicted. Nothing else.

---

## Task 1 — the base measurements, each with the command that produced it

### Collected test total

```bash
.venv/bin/python -m pytest --collect-only -q 2>&1 | tail -3; echo "PIPE0=${PIPESTATUS[0]}"
# 4223 tests collected in 7.66s
# PIPE0=0
```

**4223.** Matches the ROADMAP figure — re-measured, not carried. `${PIPESTATUS[0]}`
used rather than `$?`, per the research's measurement hazard.

The expensive full-suite pass/skip re-measure is **plan 23-02's task 1** and was
deliberately not attempted here: background jobs die at ~10 minutes on this host
and a killed run is indistinguishable from a pass.

### The condemned set — 265 tracked files

```bash
git ls-files examples/00-quickstart examples/01-agent-basics examples/02-skilling \
  examples/03-harness-portability examples/04-cross-process examples/05-workflow-hitl \
  examples/06-decision-replay examples/07-artifact-store-mcp examples/08-e2e-demo \
  examples/external/00-hello-context | wc -l
# 265
```

**265 confirmed** — criterion 1's figure, and the plan's automated verify for
this task passes:

```bash
git rev-parse --abbrev-ref HEAD | grep -qx phase-23 && git ls-files <the ten trees> | wc -l | grep -qx 265
# AUTOMATED_VERIFY_EXIT=0
```

### The three published-reference figures — `D-08`'s pinned 111 / 102 / 9 across 15 pages

```bash
PAT='examples/(0[0-8]-[a-z0-9-]+|external/00-hello-context)'
git grep -nE "$PAT" -- public/ | wc -l                    # 111  total
git grep -nE "$PAT" -- public/ | grep -c -- '--8<--'      # 102  snippet includes
git grep -nE "$PAT" -- public/ | grep -vc -- '--8<--'     #   9  prose
git grep -lE "$PAT" -- public/ | wc -l                    #  15  pages
```

**111 / 102 / 9 across 15 pages — `D-08`'s pinned figure HOLDS at PHASE_BASE.**
Per-page, summing to 111:

| Page | refs |
|---|---:|
| `public/tutorial/adopters-guide.md` | 35 |
| `public/tutorial/demo-walkthrough.md` | 18 |
| `public/how-to/compose-a-workflow-with-hitl.md` | 15 |
| `public/how-to/run-agents-cross-process.md` | 11 |
| `public/how-to/bind-a-harness-adapter.md` | 7 |
| `public/how-to/grant-and-revoke-a-skill.md` | 7 |
| `public/how-to/swap-the-artifact-store.md` | 7 |
| `public/reference/artifacts/control-plane-artifacts.md` | 3 |
| `public/reference/artifacts/product-registration.md` | 2 |
| `public/reference/artifacts/agent-definitions.md` | 1 |
| `public/reference/artifacts/prompt-artifacts.md` | 1 |
| `public/reference/artifacts/skill-catalog.md` | 1 |
| `public/reference/artifacts/skill-grants.md` | 1 |
| `public/reference/artifacts/task-definitions.md` | 1 |
| `public/reference/artifacts/workflow-definitions.md` | 1 |

The 35 / 18 concentration matches `D-IMPL-189`'s own reading of the two heavy
pages.

**Contamination check — the `D-IMPL-195` ruling 3 regex defect, verified absent
here.** `D-IMPL-195` ruling 3 records that criterion 12's *"25 of 31"* came from
a regex `0[0-8]-[a-z]` that matched **inside** `s1-00-companies-over-revenue` and
the `hw1-` names. The pattern above anchors on the literal `examples/` prefix
immediately followed by a digit, so `examples/s1-…` and `examples/hw1-…` cannot
match. Proven rather than argued:

```bash
git grep -nE "$PAT" -- public/ | grep -cE 'examples/(s1|hw1)'
# 0
```

### Criterion 13's anchor — `CLNT-17`'s row

```bash
# ROW-ONLY (the two DEFINING lines: checkbox channel + table channel), content only
git show efa0044:.planning/REQUIREMENTS.md \
  | grep -E '^- \[.\] \*\*CLNT-17\*\*|^\| CLNT-17 \|' | sha256sum
# 5bcc68caa9f6839df0d870aba10a4897114607995eb21ded0b13cccedc3ba084
```

**Criterion 13's anchor is `5bcc68caa9f6839df0d870aba10a4897114607995eb21ded0b13cccedc3ba084`.**

Reproduced identically at `PHASE_BASE` and in the working tree, so the row has
not moved between `efa0044` and `b87fe58`:

```bash
git show b87fe58:.planning/REQUIREMENTS.md | grep -E '^- \[.\] \*\*CLNT-17\*\*|^\| CLNT-17 \|' | sha256sum
# 5bcc68ca…  (identical)
grep -E '^- \[.\] \*\*CLNT-17\*\*|^\| CLNT-17 \|' .planning/REQUIREMENTS.md | sha256sum
# 5bcc68ca…  (identical)
```

The row's two defining lines are the checkbox channel (`- [ ] **CLNT-17**: …`)
and the table channel (`| CLNT-17 | Phase 17 | **Not built** …`), at positions
213 and 420 today. **Positions are recorded as observation, never as the anchor**
— criterion 13 means the row's TEXT, per `23-RESEARCH.md` §12.

**This anchor is NOT the one the plan specified.** See correction 1 below; the
plan's command produces a hash that criterion 12 is *required* to break.

---

## Task 2 — RULED. `delete-four`. Recorded verbatim; not re-asked.

**Selected option id, recorded verbatim:**

```
delete-four
```

**Dave's ruling, `D-IMPL-195` ruling 1, recorded verbatim:**

> **RULING 1 — THE FOUR LIVE-LEG TARGETS ARE DELETED, same treatment as the ten.
> Criterion 3 is AMENDED to enumerate FOURTEEN.** […] **They were in a gap:**
> criterion 3 ENUMERATED ten and these four were not among them, while the same
> criterion forbids an archive-form replacement, so neither leaving them nor
> re-pointing them was authorized. Dave: *"Leaving them invites 'the teaching
> path.' Re-pointing into archive keeps CI load on unsupported trees."* **The
> targets are deleted, AND the cron entries that invoke them are dropped or
> adjusted so `live-legs.yml` does not go red on a missing target** — a deleted
> target with a live workflow still calling it is a broken workflow, not a
> retirement. **CRITERION 3 OLD:** *all ten of `example-00`…`example-08` and
> `example-ext-00` are DELETED, not renamed.* **CRITERION 3 NEW:** the same ten
> PLUS the four live-leg targets above — fourteen in total — with
> `live-legs.yml` carrying no reference to a deleted target. **The amendment is
> named here rather than left implicit, because a ruling that changes what must
> be true must also change the criterion that gates it; otherwise the criterion
> passes while the work is unverified.**

### THE TEN → FOURTEEN EXPANSION IS RULED, NOT SCOPE CREEP

Flagged here, as Dave asked, so a reader who finds fourteen deletions against a
criterion they remember as ten can find the ruling rather than infer that an
executor overreached. The four added:

| Target | Runs (condemned tree) |
|---|---|
| `example-03-live-ollama` | `examples/03-harness-portability/run.py --mode live --provider ollama` |
| `example-03-live-anthropic` | `examples/03-harness-portability/run.py --mode live --provider anthropic` |
| `example-ext-00-live-anthropic` | `examples/external/00-hello-context/run.py --live --legs anthropic` |
| `example-ext-00-live-adk` | `examples/external/00-hello-context/run.py --live --legs adk` |

Re-measured at PHASE_BASE rather than carried:

```bash
grep -nE '^example-(03|ext-00)-live-[a-z]+:' Makefile
# 444:example-03-live-ollama:        448 recipe → examples/03-harness-portability/run.py
# 447:example-03-live-anthropic:
# 450:example-ext-00-live-anthropic:
# 453:example-ext-00-live-adk:
grep -nE 'example-(03|ext-00)-live' .github/workflows/live-legs.yml
# 6:# (`make example-03-live-ollama` — see examples/03-harness-portability/README.md
# 92:        run: make example-03-live-ollama
# 138:        run: make example-03-live-anthropic
grep -nE 'example-(03|ext-00)-live' README.md
# 61:| [`03-harness-portability`](…) | … | `make example-03` (live legs: `make example-03-live-ollama`, `make example-03-live-anthropic`) |
```

**Three `live-legs.yml` sites, not two.** The plan's decision block names `:92`
and `:138`; the comment at `:6` also names a target that is being deleted.
`23-09` must repair all three, and `23-RESEARCH.md` §6.6 already lists the `:6`
comment row, so this is a plan-text gap rather than a research gap.

### Confirmed carried downstream — `23-09`

`23-09-PLAN.md` carries a `<ruled-expansion>` block naming the amendment
explicitly, all four target names, the `live-legs.yml` obligation and the
`README.md` prose, and it instructs its own SUMMARY to name the expansion and
cite the ruling. Its `files_modified` includes `.github/workflows/live-legs.yml`.
Verified. **Nothing further is owed by this plan on task 2.**

---

## Task 3 — RULED. Re-point all fourteen to Phase 23. Recorded verbatim; not re-asked.

**Selected option id, recorded verbatim:**

```
Ownership of all FOURTEEN rows moves to Phase 23 (or to a single named
archive-quarantine plan id within it), and their paths STILL COUNT as couplings.
```

None of the three options the plan drafted (`keep-retired-owner`,
`new-owner-not-23`, `drop-fourteen`) was selected — Dave ruled a fourth
disposition, and the ruling text is authoritative over the option list.

**Dave's ruling, `D-IMPL-195` ruling 2, recorded verbatim:**

> **RULING 2 — THE FOURTEEN ORPHANED `RETIREMENT_SCHEDULE` ROWS ARE RE-POINTED
> TO PHASE 23 and their paths STILL COUNT as couplings.** Measured: the schedule
> holds 29 rows — 10 for the moved trees, 2 for the `s1` pair, 17 for neither; of
> those 17, three are `17-08`-owned and already disposed of by `D-IMPL-191`
> ruling 3, leaving **FOURTEEN owned by `16-15`/`16-17`/`16-18`, plans belonging
> to a phase `D-IMPL-152` RETIRED**: twelve `tests/examples/test_*.py` modules
> and `public/tutorial/adopters-guide.md` and
> `public/tutorial/demo-walkthrough.md`. None of the fourteen moves, and this
> phase deletes nothing, so they could neither be re-pointed to a mover nor
> honestly keep a retired owner. Ownership moves to Phase 23 (or to a single
> named archive-quarantine plan id within it). Dave: *"Blind or 'owner =
> abandoned plan' is worse than an honest Phase 23 owner. Same rule as the sweep
> table: archived path still counts."* **Deletion remains OWED for all fourteen**
> — re-pointing an owner is not discharging an obligation. **THE COUNT WAS
> CORRECTED BEFORE THE RULING, NOT AFTER.** The plan set put thirteen rows and
> eleven modules to Dave; the plan-checker and an independent measurement both
> returned fourteen and twelve. Only ten of the twelve match `test_*_output.py`,
> which is where the miscount originated. Ruling against the misstated set would
> have left `tests/examples/test_harness_portability_output.py` undisposed, and
> `D-19` forbids carrying an unre-measured figure into a decision.

### The fourteen, re-derived independently at PHASE_BASE

Measured against `tools/retirement_sweep.py::RETIREMENT_SCHEDULE` rather than
accepted from the ruling:

```bash
.venv/bin/python -c "
from tools.retirement_sweep import RETIREMENT_SCHEDULE as S
from collections import Counter
print(len(S), Counter(e.owner for e in S))"
# 29 Counter({'16-18': 18, '17-08': 5, '16-17': 4, '16-15': 2})
```

29 rows total. 24 owned by `16-15`/`16-17`/`16-18`; **10 of those 24 are the
moved trees themselves**, which `D-05` already disposes of. 24 − 10 = **14**:

| Owner | Wave | Path |
|---|---:|---|
| 16-15 | 8 | `tests/examples/test_harness_portability_output.py` |
| 16-17 | 10 | `tests/examples/test_cross_process_output.py` |
| 16-17 | 10 | `tests/examples/test_artifact_store_output.py` |
| 16-18 | 11 | `tests/examples/test_quickstart_output.py` |
| 16-18 | 11 | `tests/examples/test_agent_basics_output.py` |
| 16-18 | 11 | `tests/examples/test_skilling_output.py` |
| 16-18 | 11 | `tests/examples/test_workflow_hitl_output.py` |
| 16-18 | 11 | `tests/examples/test_decision_replay_output.py` |
| 16-18 | 11 | `tests/examples/test_e2e_demo_output.py` |
| 16-18 | 11 | `tests/examples/test_ext00_serve_output.py` |
| 16-18 | 11 | `tests/examples/test_ext00_fixture_schemas.py` |
| 16-18 | 11 | `tests/examples/test_ext00_hardening.py` |
| 16-18 | 11 | `public/tutorial/adopters-guide.md` |
| 16-18 | 11 | `public/tutorial/demo-walkthrough.md` |

**FOURTEEN rows / TWELVE test modules, and exactly TEN of the twelve match
`test_*_output.py`** — the miscount `D-IMPL-195` names, reproduced exactly. The
two that do not match are `test_ext00_fixture_schemas.py` and
`test_ext00_hardening.py`.

**The 29-row decomposition also reconciles**: 29 = 10 moved trees + 2 `s1` trees
+ 17 neither; of the 17, three are `17-08`-owned (`test_s1_00_output.py`,
`test_s1_01_output.py`, `test_s1_00_config_equivalence.py`), leaving 14. Worth
recording that **all five `17-08` rows are `s1`-related** — the two trees plus
those three test modules — so `D-IMPL-191` ruling 3's *"the `s1` pair's `17-08`
rows are left alone"* and `23-10-PLAN.md`'s *"leave the five `17-08` `s1` rows
completely alone"* describe the same set with no gap between them.

### Confirmed carried downstream — `23-10`

`23-10-PLAN.md` carries the ruling in bold at its task 2 — *"RULED `D-IMPL-195`
ruling 2: re-point all FOURTEEN to Phase 23 … and KEEP their paths counted as
couplings. Deletion remains OWED — re-pointing an owner discharges nothing"* —
names the twelve modules plus the two `public/tutorial/` pages, and carries the
`StopIteration` trap from `23-RESEARCH.md` §13.3 (the `WAVE_8` / `WAVE_10` /
`WAVE_11` import-time derivation on `startswith("examples/")`) as work to repair
BEFORE the table is re-pointed. Verified. **Nothing further is owed by this plan
on task 3.**

---

## Corrections — measured figures that came back different from the prediction

Recorded as corrections rather than smoothed over. All three are measurements
that falsified something the plan or the research carried.

### Correction 1 — criterion 13's anchor command in the plan hashes 13 lines, not 2, and criterion 12 is REQUIRED to break it

The plan's task 1 says to *"confirm the row occupies exactly two lines"* and to
take the anchor as
`git show efa0044:.planning/REQUIREMENTS.md | grep 'CLNT-17' | sha256sum`.
`23-RESEARCH.md` §12 says the same: *"`CLNT-17` occupies exactly two lines."*

**Measured: `grep 'CLNT-17'` returns THIRTEEN lines, not two.**

```bash
grep -c 'CLNT-17' .planning/REQUIREMENTS.md
# 13
grep -cE '^- \[.\] \*\*CLNT-17\*\*|^\| CLNT-17 \|' .planning/REQUIREMENTS.md
# 2
```

The row's two DEFINING lines are correct as a claim about the row. The other
eleven are **other rows that mention `CLNT-17` in their text** — `DOCS-09`,
`DOCS-15`, `DOCS-17`, `CLNT-16`, `CLNT-29`, `RECON-04` in the checkbox channel
and their table-channel counterparts.

**Why this is load-bearing rather than pedantic: `DOCS-17`'s own row is one of
the eleven, in BOTH channels.**

```bash
sed -n '42p'  .planning/REQUIREMENTS.md | grep -o 'CLNT-17'   # CLNT-17   (DOCS-17 checkbox channel)
sed -n '336p' .planning/REQUIREMENTS.md | grep -o 'CLNT-17'   # CLNT-17   (DOCS-17 table channel)
```

Criterion 12 **requires** this phase to verdict `DOCS-17` `Partial` in both
channels. So the plan's broad hash would go RED as a direct consequence of doing
what criterion 12 mandates — an anchor that fails on correct work, which is the
same shape as criterion 18's defect one file over.

**Resolution:** criterion 13's anchor is the ROW-ONLY hash
`5bcc68caa9f6839df0d870aba10a4897114607995eb21ded0b13cccedc3ba084`, recorded
above with its command. It measures what criterion 13 means — *"`CLNT-17`'s row
is BYTE-IDENTICAL to its state at `efa0044`"* — and it is immune both to
position drift (no `-n`) and to criterion 12's required edit elsewhere in the
file.

The broad 13-line hash is recorded too, for the record and because it is the
figure the plan asked for:

```bash
git show efa0044:.planning/REQUIREMENTS.md | grep 'CLNT-17' | sha256sum
# ad572651859a8a57418813cfee0d75aa0a2cd6bc86e2dc60a97663e1e16f5138   (13 lines — DO NOT gate on this)
```

**`23-11` / `23-12` / whichever plan verifies criterion 13 must use
`5bcc68ca…`.** Using `ad572651…` will fail the phase for succeeding.

`23-RESEARCH.md` §12's own hash `f2839f8f…` is reproduced exactly by
`grep -n 'CLNT-17' … | sha256sum` on today's tree — confirming it is the
thirteen-line, position-inclusive form the research itself warned against using.

### Correction 2 — the published-reference regex must NOT require a trailing slash

The first measurement used `examples/(0[0-8]-…|external/00-hello-context)/`
with a trailing `/` and returned **105 / 102 / 3 across 15 pages** — includes
matched, prose short by six. Dropping the trailing slash returns the pinned
**111 / 102 / 9**.

Cause: six of the nine prose references name a tree directory with no trailing
slash — five *"Everything below is literal-included from `examples/0N-…`"* lines
plus `demo-walkthrough.md`'s *"a narrated walk through `examples/08-e2e-demo`"*.

Recorded because criteria 4 and 6 are gated on 102 / 9 / 15 and **a trailing
slash in the verification regex under-counts prose by six while leaving the
include count untouched** — i.e. it looks like a partially-correct measurement
rather than a broken one. Plans 23-07 and 23-12 should use the slash-free form
and keep the `examples/(s1|hw1)` contamination check beside it.

### Correction 3 — the `Makefile` line numbers in the plan's decision table are the recipe lines, not the target declarations

The plan's table gives `445 / 448 / 451 / 454`. Measured, the **declarations**
are at `444 / 447 / 450 / 453` and the **recipes** — which carry the condemned
path token, and are therefore what the sweep counts — are at
`445 / 448 / 451 / 454`. Both numbers are right about different lines. Noted so
`23-09` deletes the declaration-plus-recipe PAIR (two lines each, eight lines
total) rather than the recipe alone, which would leave four orphan target
headers.

### Not a correction, but a research finding that no longer holds — the base is GREEN, not RED

`23-RESEARCH.md` §1.1 reports *"the phase base is ALREADY RED on the `test` leg,
and the commit that made it red is the one that wrote criterion 14"* — measured
at `aefd072` as 1 failed / 4 passed in
`tests/invariants/test_citation_coverage.py`.

Re-measured at PHASE_BASE:

```bash
.venv/bin/python -m pytest tests/invariants/test_citation_coverage.py -q
# 5 passed in 14.70s
```

**GREEN.** `D-IMPL-194` records the fix at `c2a117c` — the `D-IMPL-192` text's
line-anchored Python citations converted to symbol form per `D-IMPL-114`, never
by raising the `D-IMPL-123` ceiling. That fix is in `PHASE_BASE`'s ancestry, so
§1.1's finding is discharged and no plan needs to carry it.

**Consequence for every later Phase 23 plan and for this one:** the ceiling is at
zero and holds. **No line-anchored Python citation may appear anywhere this
phase writes** — `.planning/` is in the gate's scope (that is how
`.planning/ROADMAP.md:2212` was caught). This summary uses `path.py::Symbol`
throughout; the `Makefile`, `live-legs.yml` and `REQUIREMENTS.md` line numbers
above are not Python targets and are out of `D-IMPL-123`'s scope.

---

## What this plan did NOT do, by design

- **No tracked SOURCE file was modified.** Nothing under `src/`, `runtime/`,
  `examples/`, `public/`, `tests/`, `tools/` or `Makefile` was touched — the
  plan's `must_haves` truth. The two files in the phase diff are this summary
  and the generated coupling report.
- **No criterion was authored, renumbered or edited.** The set is EIGHTEEN and
  LOCKED (`D-GATE-19`, `D-IMPL-174`), and criterion 3's ten→fourteen and
  criterion 12's 25→19 amendments were already written into
  `.planning/ROADMAP.md` at `b87fe58` by `D-IMPL-195`. Verified by reading, not
  assumed.
- **No `CLNT-17` disposition of any kind.** The row is untouched, `Not built`,
  and its anchor recorded so a later plan can prove it stayed that way.
- **No `state.*` or `roadmap.*` writer was invoked** (`D-15`).
- **No full-suite run.** That is 23-02 task 1, in foreground chunks.
- **No `public/` write, so no include or prose re-point.** That is Waves 4-7.

`docs/surface/examples/RETIREMENT-COUPLINGS.md` **was** regenerated — see the
deviation below. The prediction in this section's first draft (that a plan
writing only a summary would not move the report) was wrong and is corrected
there rather than removed.

---

## Deviations from Plan

**Tasks 2 and 3 were executed as record-and-confirm rather than as
`checkpoint:decision`.** The plan carries both an authoritative `<ruling>` block
and the superseded `<action>Present the decision below to Dave` text from the
draft. Dave ruled both before execution (`D-IMPL-195`, 2026-08-24, pre-execution
— nothing had run). Re-asking a settled ruling is a defect, so the `<ruling>`
blocks governed and the decision blocks were treated as historical context for
what the ruling resolved. No option was presented and none was selected by the
executor.

**Task 3's ruling does not match any of the three drafted option ids.** Dave
ruled a disposition the plan did not offer — Phase 23 ownership with the paths
still counted — so the ruling text is recorded verbatim in place of an option id,
and `23-10-PLAN.md` already carries that text rather than an id. Recorded rather
than forced into the nearest option.

**One plan-text gap found and recorded, not fixed here:** the task 2 decision
block names two `live-legs.yml` sites; there are three (`:6` is a comment naming
a deleted target). `23-09` owns the repair and `23-RESEARCH.md` §6.6 already
lists all three.

### Rule 3 (blocking issue, auto-fixed) — the coupling report went stale the moment this summary was written, and the plan predicted it would not

The plan's `files_modified` is empty and its `<verification>` predicts the phase
diff names only `23-01-SUMMARY.md`. **Measured, that prediction is false and
cannot be made true.**

`docs/surface/examples/RETIREMENT-COUPLINGS.md` is generated by
`tools/retirement_sweep.py::sweep`, which walks `.planning/` among other trees.
This summary names the ten condemned trees **36 times** — unavoidably, since it
enumerates the four live-leg recipes and the fourteen schedule rows — so the
committed report went stale as soon as the file existed:

```bash
.venv/bin/python -m pytest tools/docs_tests -q
# FAILED tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current
# 1 failed, 269 passed
```

Regenerated **LAST**, **in the venv**, after the only `.planning/` write, per
criterion 11 and the standing rule:

```bash
.venv/bin/python tools/retirement_sweep.py --report
# wrote docs/surface/examples/RETIREMENT-COUPLINGS.md
# 267 coupling rows across 81 files (146 rows outside the three swept trees); 1926 files scanned

git diff --stat docs/surface/examples/RETIREMENT-COUPLINGS.md
#  docs/surface/examples/RETIREMENT-COUPLINGS.md | 1 +
```

The delta is exactly one row, and it is this summary's own:

```
| `.planning/phases/23-…/23-01-SUMMARY.md` | 36 | the phase's own planning tree — not shipped, not published |
```

Green after:

```bash
.venv/bin/python -m pytest tools/docs_tests -q      # 270 passed
.venv/bin/python -m pytest tests/invariants -q      # 183 passed
```

**Precedent, checked rather than assumed:** every planning commit already on
this phase does the same — `f56cfae` (report +4/-2), `695a00e` (+11), `b87fe58`
(+4/-2) all carry the regenerated report alongside the `.planning/` write. So
this is the established pattern for this repo, not a novel liberty.

**Carried forward for every later Phase 23 plan:** a plan whose `files_modified`
omits the coupling report but which writes any `.planning/` or `public/` file
will leave the tree red. Criterion 11's *"regenerate LAST"* is not only about the
final commit — it applies at every commit that writes a swept tree.

No Rule 1 or Rule 2 auto-fixes were needed. No Rule 4 situation arose.

---

## Verification

```bash
git rev-parse --abbrev-ref HEAD
# phase-23
git diff b87fe58..HEAD --name-only
# .planning/phases/23-…/23-01-SUMMARY.md
# docs/surface/examples/RETIREMENT-COUPLINGS.md      (generated, +1 line — see deviation)
```

Against the plan's `<verification>` block:

- [x] `git rev-parse --abbrev-ref HEAD` is `phase-23`
- [~] `git diff PHASE_BASE..HEAD --name-only` names `23-01-SUMMARY.md` **plus the
      regenerated coupling report**. The plan predicted one file; it is
      mechanically two, because the report walks `.planning/` and this summary
      names the condemned trees 36 times. Recorded as a deviation, not smoothed
      over. Zero **source** files modified, which is the plan's actual
      `<success_criteria>` wording.
- [x] `PHASE_BASE` sha recorded — `b87fe58c3ee82333accc4eb5dbc8644a0bc8e72b`
- [x] collected total recorded — 4223, with command
- [x] 265 recorded, with command; automated verify exits 0
- [x] 111 / 102 / 9 / 15 recorded, with commands and per-page breakdown
- [x] criterion 13's content-only anchor recorded with the exact command used —
      `5bcc68ca…`, and the plan's specified command recorded separately as
      unsuitable, with the measurement showing why
- [x] both of Dave's rulings recorded verbatim, with the downstream plans
      confirmed to carry them

Against the plan's `<success_criteria>`:

- [x] Phase branch open, `PHASE_BASE` pinned and recorded
- [x] Dave's ruling on the four live-leg targets recorded — `delete-four`
- [x] Dave's ruling on the fourteen orphaned schedule rows recorded — verbatim
- [x] Zero tracked source files modified

---

## Key links for the next plans

| From | To | Via |
|---|---|---|
| this summary | `23-02` | PHASE_BASE `b87fe58` and collect total 4223 |
| this summary | `23-09` | `delete-four` — fourteen targets, `live-legs.yml` at three sites, `README.md:61` |
| this summary | `23-10` | the fourteen `RETIREMENT_SCHEDULE` rows, enumerated, owner → Phase 23, still counted |
| this summary | whichever plan gates criterion 13 | anchor `5bcc68ca…`, **not** `ad572651…` |
| this summary | `23-07` / `23-12` | the slash-free published-reference regex and its contamination check |

---

## Self-Check: PASSED

Every claim above re-verified against the tree rather than against this
document.

```bash
[ -f .planning/phases/23-…/23-01-SUMMARY.md ]                    # FOUND
git log -1 --name-only --format=%h                               # this plan's commit, both files
git diff --name-only b87fe58 -- src/ runtime/ examples/ public/ tests/ tools/ Makefile pyproject.toml
                                                                 # EMPTY — the scope fence held
.venv/bin/python -m pytest tools/docs_tests -q                   # 270 passed
.venv/bin/python -m pytest tests/invariants -q                   # 183 passed
```

**`.planning/STATE.md` and `.planning/ROADMAP.md` were deliberately NOT
touched.** `D-15` makes both hand-edit-only and forbids any `state.*` or
`roadmap.*` writer; this repo's practice is to hand-edit them once at
phase-execution completion, not per plan. Plan 23-13 (or whichever plan closes
execution) owns that write. Recorded here so a reader can tell "left by
decision" from "forgotten" — the distinction this project exists to protect.
