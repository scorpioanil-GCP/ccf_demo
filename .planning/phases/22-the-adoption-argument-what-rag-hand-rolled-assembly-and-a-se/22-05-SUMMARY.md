---
phase: 22-the-adoption-argument-what-rag-hand-rolled-assembly-and-a-se
plan: 05
subsystem: phase verification and the phase record
tags: [DOCS-15, fabric-diff, per-member-pathspec, ci-six-legs, retirement-couplings, phase-record]
status: complete
requires:
  - .planning/phases/22-*/22-01-SUMMARY.md .. 22-04-SUMMARY.md (every figure in the record comes from one of them)
  - 951eb4a (the phase base — the `--no-ff` merge of `phase-21.1` to `main`)
provides:
  - .planning/STATE.md (the Phase 22 record — what shipped, the D-15 narrowing, the D-06 disposition, the two mid-phase rulings, the open residual)
  - the measured evidence for ROADMAP criteria 12, 13 and 15
affects:
  - docs/surface/examples/RETIREMENT-COUPLINGS.md (one row moved; `.planning/STATE.md` 11 -> 15)
  - .planning/phases/22-*/22-06-PLAN.md (the close gate reads this record)
tech-stack:
  added: []
  patterns: [per-member-pathspec-diff, chunked-foreground-test-leg, confined-diff-assertion]
key-files:
  created:
    - .planning/phases/22-.../22-05-SUMMARY.md
  modified:
    - .planning/STATE.md
    - docs/surface/examples/RETIREMENT-COUPLINGS.md
decisions:
  - "The CI legs were run BEFORE task 2's record write, so the record carries measured CI figures rather than promised ones; the report regeneration still follows the write, which is what D-15 requires"
  - "The test leg was partitioned into four chunks, not three, and coverage was proven by node-id SET EQUALITY as well as by the collected-count sum"
  - "Task 1 produced no file change by the plan's own instruction, so it has no commit of its own"
metrics:
  duration: ~85 min
  completed: 2026-08-23
  tasks: 3
  commits: 2 (+1 SUMMARY/report follow-up)
---

# Phase 22 Plan 05: The proof — Summary

The phase did what it said and nothing else, proven the two ways this repository
has learned to insist on: a **per-member** fabric diff with the misspelled-member
contrast recorded beside it, and **six CI legs at exit 0 in the foreground** with
the test leg chunked and its union proven equal to the whole suite.

`src` 142 tracked files / diff empty. `runtime` 71 / empty. `examples` 323 /
empty, and the example tree **set** identical at both ends. `make ci` green on
all six legs: **4105 passed / 118 skipped**, byte-for-byte the `D-GATE-21.1`
baseline.

**`D-06` is recorded as LANDED, not owed.** The plan was written before the
disposition was known; plan `22-03` shipped the stretch.

---

## What shipped

| Task | Name | Commit | Files |
| --- | --- | --- | --- |
| 1 | The per-member fabric diff, with each member proven to name something | (no commit — see below) | none |
| 2 | Hand-edit the phase record | `e7a6b40` | `.planning/STATE.md` |
| 3 | Regenerate the report last, then run all six CI legs in the foreground | `9311db4` | `docs/surface/examples/RETIREMENT-COUPLINGS.md` |

**Task 1 has no commit, and that is the plan's own instruction rather than an
omission.** Its action says in as many words: *"Write nothing to
`.planning/STATE.md` in this task beyond nothing at all — the record is task 2.
This task produces measurements for the SUMMARY."* It changed no file, so there
was nothing to commit; an `--allow-empty` commit would have put a record in
history that the tree does not carry. Its evidence is below and in the phase
record.

---

## Task 1 — the per-member fabric diff

### The base, proven before it was used

```
$ git rev-parse 951eb4a
951eb4a3e2d8e072ec7f059e372545753d415a25
exit=0
$ git merge-base --is-ancestor 951eb4a HEAD
exit=0
```

`HEAD` at the time of measurement: `15c900e`.

### One command per member, never one command naming all three

**`src`:**

```
$ git ls-files -- src | wc -l
142
$ git diff --stat 951eb4a -- src
[END OF OUTPUT] exit=0
```

**`runtime`:**

```
$ git ls-files -- runtime | wc -l
71
$ git diff --stat 951eb4a -- runtime
[END OF OUTPUT] exit=0
```

**`examples`:**

```
$ git ls-files -- examples | wc -l
323
$ git diff --stat 951eb4a -- examples
[END OF OUTPUT] exit=0
```

All three `git diff --stat` invocations printed **nothing**. All three
`git ls-files` counts are greater than zero, so no member is a typo reporting
clean.

### The example tree SET, not only its contents

```
$ git ls-tree -d --name-only 951eb4a examples/ > base
$ git ls-tree -d --name-only HEAD      examples/ > head
base entries: 14   head entries: 14
$ diff base head
DIFF EXIT=0
```

The fourteen, verbatim: `00-quickstart`, `01-agent-basics`, `02-skilling`,
`03-harness-portability`, `04-cross-process`, `05-workflow-hitl`,
`06-decision-replay`, `07-artifact-store-mcp`, `08-e2e-demo`, `external`,
`hw1-companies-over-revenue`, `hw1-harness-clients`,
`s1-00-companies-over-revenue`, `s1-01-hello-context-product`.

**Run stronger than the plan asked, because the plan's command sees direct
children only.** `git ls-tree -d -r --name-only` over the same two revisions
enumerates **34 nested trees at each end**, `diff` exit 0. A tree created,
moved or removed *below* the first level would have been invisible to the
non-recursive form, and this phase's fence claim is about the whole subtree.

### The `srcX` sabotage, side by side with the real member

```
$ git ls-files -- srcX | wc -l
0
$ git diff --stat 951eb4a -- srcX
[END OF OUTPUT] exit=0
```

| Member | `git ls-files \| wc -l` | `git diff --stat 951eb4a -- <member>` |
| --- | --- | --- |
| `src` | **142** | empty |
| `srcX` | **0** | empty |

**What the contrast proves, in one sentence:** the diff alone cannot tell a
clean member from a member that does not exist — both print nothing — so the
`ls-files > 0` guard is the only thing standing between a one-key typo and a
green report, which is exactly what `VAC-01` and ROADMAP criterion 12 forbid
leaving unguarded.

Both halves run through the plan's own `<automated>` command:

```
$ bash -c 'set -e; git rev-parse 951eb4a >/dev/null; git merge-base --is-ancestor 951eb4a HEAD; for m in src runtime examples; do n=$(git ls-files -- "$m" | wc -l); test "$n" -gt 0 || { echo "pathspec names nothing: $m"; exit 1; }; d=$(git diff --stat 951eb4a -- "$m"); test -z "$d" || { echo "member dirty: $m"; echo "$d"; exit 1; }; done; echo "per-member fabric diff clean"'
per-member fabric diff clean
AUTOMATED EXIT=0

$ (the same command with srcX substituted for src)
pathspec names nothing: srcX
SABOTAGED EXIT=1
```

The guard refuses by name. It does not report clean.

### Nothing was written by this task

```
$ git status --porcelain
?? references/CCF_SDK_DE_REQUIREMENTS.md
?? references/CP-SPEC-001_Counterparty_Reference_Snapshot_v2.md
?? references/Context_Product_Specification_Standard_v0-3.md
```

Three untracked files under `references/`, all three present in the working
tree **before this phase began** (they are in the session's opening
`git status` snapshot). Not attributable to this plan and not committed by it.

---

## Task 2 — the phase record

**Edit method: hand-edited.** Read, edited by anchored string substitution with a
uniqueness assertion on the anchor, written back, then re-parsed as YAML.
**No `state.*` writer and no `roadmap.*` writer was invoked** (`docs/DECISIONS.md`
D-15). Backed up outside the tree first:
`sha256 0bf1f78896afe77e85e551fe2fb9be5d9d4effe112b22a1180a79b27f2ea1810`,
identical to the copy taken.

- `last_updated` `2026-08-23T16:15:00.000Z` → `2026-08-23T21:40:00.000Z`.
- `last_activity` gained a 166-line Phase 22 block at the head; the previous
  head entry was re-marked `PRIOR:` and is otherwise byte-unchanged.
- File 2053 → 2219 lines. **Eight frontmatter keys before and after** —
  `gsd_state_version`, `milestone`, `milestone_name`, `status`, `last_updated`,
  `last_activity`, `progress`, `stopped_at` — re-parsed with `yaml.safe_load`.

### Greppable acceptance checks

| Check | Result |
| --- | --- |
| `grep -c "D-06"` | **2** |
| `grep -c "cite03-node-id\|criterion 8"` | **9** |
| `grep -c "pub01-whitepaper-shingle"` | **2** |
| `grep -c "public/concepts/answers-no-document-contains.md"` | **1** |
| `grep -c "tools/docs_tests/test_adoption_wording.py"` | **2** |
| `grep -c "test_the_debt_figure_is_measured_and_not_constant"` | **1** |
| `grep -c "951eb4a"` | **7** |
| `DOCS-15` present in the parsed `last_activity` | **True** |

### Every numeric figure in the record, and where it came from

| Figure | Source |
| --- | --- |
| page 339 lines; 5 `## ` / 8 `### ` sections; 5 includes | re-measured this session; line count also `22-02-SUMMARY.md` |
| gate module 1052 lines, 24 tests; 7 floors / 3 assertions / 12 controls / 3 for D-06 | `22-03-SUMMARY.md`; re-measured this session |
| 24 `test_adoption_wording.py::` node ids collected inside `gate-tools` | measured this session |
| `examples/00`–`08` + `external/00-hello-context` references: 111 → 111 | measured this session; 111 is `22-CONTEXT.md` D-08's figure |
| `debt-profile.yaml` 15 shingle findings vs 0 on each of the five includes | `22-01-SUMMARY.md`, `22-02-SUMMARY.md` |
| `spine.py:gate` 15 findings, 149 body lines | `22-01-SUMMARY.md` |
| D-06: 22 node ids, 0 unresolvable paths, 0 missing symbols; module 21 → 24 | `22-03-SUMMARY.md` |
| ledger module 106 → 113; 113 vs `1 failed, 112 passed` residual measurement | `docs/DECISIONS.md` D-IMPL-188 + amendment; 113 re-measured this session |
| 149 ids at `951eb4a`, 149 now, diff empty | `22-04-SUMMARY.md` |
| 20 coupling rows naming the page; report 264 / 81 | `22-04-SUMMARY.md`; re-measured this session |
| `src` 142 / `runtime` 71 / `examples` 323; 14 and 34 trees | this plan, task 1 |
| CI: 211 files, 4105/118, 406 + 291, 4223, 1332/1082/870/939 | this plan, task 3 |
| `gate-tools` leg 2 266 → 291; test-defs 237 → 262 | 266 from the `D-GATE-21.1` record in `STATE.md`; 291 and both def counts measured this session |
| 15 sabotage mutations; controls 5, 6 and 8 vacuously green | `22-01`..`22-04` SUMMARYs + this plan's `srcX` |
| system interpreter 258 vs venv 264 | `22-04-SUMMARY.md`; **re-measured on this tree** (below) |

### ROADMAP untouched

```
$ git diff --stat HEAD -- .planning/ROADMAP.md
[nothing]
$ git diff --stat 951eb4a -- .planning/ROADMAP.md
 .planning/ROADMAP.md | 71 ++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 71 insertions(+)
$ git diff 951eb4a HEAD -- .planning/ROADMAP.md | grep -c '^-[^-]'
0
```

**71 insertions and ZERO deletions across the four Phase 22 planning commits**
(`edc2523`, `acbe632`, `8dfde2d`, `10046cb`). A criterion edit or renumber would
necessarily appear as a deletion; none exists. The fifteen Success Criteria stand
exactly as locked at the discuss sitting.

### Task 2's verification

```
$ PYTHONPATH=.:src:runtime .venv/bin/python -m tools.lints --all
LINTS EXIT=0
```

`.planning` is in the citation lint's `GATED_TREES`, so every `path::symbol`
citation written into the record resolves. The record carries no `path.py:LINE`
citation (`D-IMPL-114` / `D-IMPL-123`'s ceiling of zero).

```
$ pytest tools/docs_tests/test_requirement_ledger.py -q
113 passed in 10.48s
$ git status --porcelain src/ runtime/ examples/ public/
[nothing]
```

---

## Task 3 — the report, then the six legs

### Ordering, and the one deviation in it

The plan's task 3 runs the regeneration first and the CI legs second. **The CI
legs were in fact run before task 2's record write**, then the report was
regenerated after it. The reason: the phase record has to state the CI result,
and a record written before the run would be stating a number nobody had
measured — the exact defect this project treats as a repudiation risk
(`T-22-29`). What the plan's ordering actually protects is that the
**regeneration follows the last `.planning/` write**, and that is preserved:
regeneration ran after `e7a6b40`, and once more after this SUMMARY. `gate-tools`
— the leg that carries `test_the_committed_report_is_current` — was **re-run
after the write and the regeneration** and is green.

### The regeneration, and the CONFINED diff

```
$ .venv/bin/python -c "import joserfc; print('joserfc OK')"
joserfc OK
$ PYTHONPATH=.:src:runtime .venv/bin/python tools/retirement_sweep.py --report
wrote docs/surface/examples/RETIREMENT-COUPLINGS.md
264 coupling rows across 81 files (146 rows outside the three swept trees); 1896 files scanned
SWEEP EXIT=0
```

| | Coupling rows | Files |
| --- | --- | --- |
| Committed at plan start (`15c900e`) | **264** | 81 |
| After this regeneration | **264** | 81 |

The count did not fall, so the silent-drop trap did not fire.

**The diff, verbatim and entire:**

```
diff --git a/docs/surface/examples/RETIREMENT-COUPLINGS.md b/docs/surface/examples/RETIREMENT-COUPLINGS.md
index 0d98a83..677d030 100644
--- a/docs/surface/examples/RETIREMENT-COUPLINGS.md
+++ b/docs/surface/examples/RETIREMENT-COUPLINGS.md
@@ -328,7 +328,7 @@ Append-only records and documents no plan in this phase may edit. They name reti
 | `.planning/PROJECT.md` | 1 | the phase's own planning tree — not shipped, not published |
 | `.planning/REQUIREMENTS.md` | 103 | the phase's own planning tree — not shipped, not published |
 | `.planning/ROADMAP.md` | 21 | the phase's own planning tree — not shipped, not published |
-| `.planning/STATE.md` | 11 | the phase's own planning tree — not shipped, not published |
+| `.planning/STATE.md` | 15 | the phase's own planning tree — not shipped, not published |
 | `.planning/ledgers/16-config-consolidation.md` | 1 | the phase's own planning tree — not shipped, not published |
 | `.planning/milestones/v0.1-ROADMAP.md` | 6 | the phase's own planning tree — not shipped, not published |
```

**Every changed line classified against the two-subject allowlist:**

| Changed line | Section | Subject | Verdict |
| --- | --- | --- | --- |
| `-\| .planning/STATE.md \| 11 \| …` | *Measured but not assigned* | `.planning/STATE.md` | **ALLOWED** |
| `+\| .planning/STATE.md \| 15 \| …` | *Measured but not assigned* | `.planning/STATE.md` | **ALLOWED** |

The containing section was resolved by reading the nearest preceding heading
above line 328: `319: ## Measured but not assigned`. And the negative check:

```
$ git diff -U0 -- docs/surface/.../RETIREMENT-COUPLINGS.md | grep -E '^[-+][^-+]' \
    | grep -cE 'examples/|tests/examples/|public/|src/|runtime/|tools/'
0
```

**Zero changed lines name a forbidden subject.** The diff is not byte-empty and
was never asserted to be: task 2 wrote `.planning/STATE.md`, which is a sweep
subject with a committed row, so a byte-identical gate would have been
unsatisfiable on a correct tree. It moved because the record cites the tree more
often than the file it replaced did — 11 references → 15.

```
$ pytest tools/docs_tests/test_retirement_sweep.py -q
33 passed in 20.86s
```

### The system-interpreter trap, re-measured on this tree

Not inherited from `22-04-SUMMARY.md` — run again here, because criterion 13's
*"in the venv"* clause is only worth as much as the measurement behind it:

```
$ PYTHONPATH=.:src:runtime /usr/bin/python3     tools/retirement_sweep.py
258 coupling rows across 81 files (140 rows outside the three swept trees); 1896 files scanned
SYS EXIT=0
$ PYTHONPATH=.:src:runtime .venv/bin/python     tools/retirement_sweep.py
264 coupling rows across 81 files (146 rows outside the three swept trees); 1896 files scanned
VENV EXIT=0
```

**Six rows dropped silently, at exit 0.** Same tree, same command, same second.

### The six legs — every one in the foreground

Which signal came from where, in one sentence: **`<automated>` covered
`make lint`, `make typecheck`, `make gate-tools`, `make examples` and
`make docs-strict` (five legs, one `set -e` chain, exit 0 in 3m01s), and the
test leg was run as FOUR separate foreground `pytest` invocations recorded
individually below** — it is deliberately not in `<automated>`, because a single
`make test` is the exact shape that reports a pass for a job killed at ten
minutes. Every leg below was **also** run individually in the foreground first,
so each has its own exit status rather than inheriting one from a chain.

| # | Leg | Command | Exit | Headline |
| --- | --- | --- | --- | --- |
| 1 | lint | `make lint` | **0** | no violations |
| 2 | typecheck | `make typecheck` | **0** | `Success: no issues found in 211 source files` |
| 3 | test | four chunked `pytest` invocations | **0** ×4 | **4105 passed / 118 skipped** |
| 4 | gate-tools | `make gate-tools` | **0** | `406 passed` + `291 passed` |
| 5 | examples | `make examples` | **0** | eleven examples; three harness legs at one content address |
| 6 | docs-strict | `make docs-strict` | **0** | all four steps |

```
$ time bash -c 'set -e; make lint; make typecheck; make gate-tools; make examples; make docs-strict'
real  3m1.639s
AUTOMATED EXIT=0
```

#### The test leg, chunk by chunk

Environment identical to the `test` target: `PYTHONPATH=src:runtime` and
`CCF_REQUIRE_HARNESSES=1`. No chunk backgrounded; no chunk piped through `tail`
in a background job; the longest is 5m24s and the four are disjoint.

| Chunk | Paths | Passed | Skipped | Wall | Exit |
| --- | --- | --- | --- | --- | --- |
| A | `agents assembly authz cli client conformance contracts controlplane` | 1273 | 59 | 98.08s | **0** |
| B | `crossproc deployment examples gates graph` | 1023 | 59 | 187.47s | **0** |
| C | `halflife harness hitl http_api integration invariants lints mcp operators peering perf_gate perf_smoke perf_synth` | 870 | 0 | 324.69s | **0** |
| D | `products projection properties replay signal_layer skills spikes workflow` + the four root `tests/test_*.py` | 939 | 0 | 30.17s | **0** |
| | **total** | **4105** | **118** | | |

**4105 passed / 118 skipped is byte-for-byte the `D-GATE-21.1` baseline**, which
is the mechanical proof this phase changed no behaviour. `22-03` added 24 tests
under `tools/`, which `[tool.pytest.ini_options] testpaths = ["tests"]` excludes
from `make test` — they run under `gate-tools` — so an unmoved baseline is the
expected shape here, and it was checked rather than assumed.

#### The chunk arithmetic — the blocking criterion

```
$ PYTHONPATH=src:runtime CCF_REQUIRE_HARNESSES=1 .venv/bin/python -m pytest --collect-only -q
4223 tests collected in 6.39s
```

| Chunk | Collected |
| --- | --- |
| A | 1332 |
| B | 1082 |
| C | 870 |
| D | 939 |
| **sum** | **1332 + 1082 + 870 + 939 = 4223** |
| full suite | **4223** |

Equal. And the run itself closes: 4105 passed + 118 skipped = **4223**.

**Proven stronger than the arithmetic, because a sum can be right while the
membership is wrong.** Two chunks could double-count one directory and omit
another and still sum to 4223. So the collected **node ids** were compared as
sets:

```
full collected node-ids : 4223
chunk union node-ids    : 4223
chunk union DEDUPED     : 4223      <- equal to the line above, so the chunks are pairwise disjoint
$ diff full_ids union_ids
SET DIFF EXIT=0
```

The four chunks are a genuine partition of `testpaths`, not four overlapping
samples that happen to add up.

#### `gate-tools` includes the new module

```
$ pytest tools/publish_scan_tests tools/docs_tests --collect-only -q | grep -c 'test_adoption_wording.py::'
24
```

| | leg 1 (`tools/lints/tests`) | leg 2 (`tools/publish_scan_tests tools/docs_tests`) |
| --- | --- | --- |
| At `951eb4a` | 406 | **266** (cited: the `D-GATE-21.1` record in `STATE.md`; `22-01-SUMMARY.md` measured the same 266 at the phase start) |
| Now | 406 | **291** |

The rise is +25 and it is accounted for exactly, by an independent measurement
that does not depend on the cited figure:

```
$ git grep -c '^def test_' 951eb4a -- tools/docs_tests tools/publish_scan_tests   -> 237
$ git grep -c '^def test_' HEAD     -- tools/docs_tests tools/publish_scan_tests   -> 262
$ diff <(git ls-tree -r --name-only 951eb4a …) <(git ls-tree -r --name-only HEAD …)
> tools/docs_tests/test_adoption_wording.py
```

**Exactly one file was added** — the wording gate, +24 defs — and exactly one
existing file changed its def count: `test_requirement_ledger.py` 93 → 94, which
is `D-IMPL-188`'s `test_the_pinned_diff_ceiling_resolves`. 237 + 24 + 1 = 262.
No other gate-tools module moved.

#### Re-run after the record write

```
$ make gate-tools        (after e7a6b40 and after the regeneration)
406 passed in 7.71s
291 passed in 53.25s
GATE-TOOLS EXIT=0
```

### Fence checks at the end of the task

```
$ git status --porcelain src/ runtime/ examples/ public/
[nothing]
$ git status --porcelain
?? references/… (the three pre-existing untracked files)
```

---

## The two mid-phase rulings, and why they are in the record

The plan for this wave was written before either existed, so they are recorded
here as well as in `STATE.md`. **A phase record that omits two of Dave's rulings
is not a record.**

`D-IMPL-188` and its **AMENDMENT** (`docs/DECISIONS.md`; commits `59de8ae`,
`33835f2`, `d894eb0`, `78069c3`). Phase 22's first commit turned
`test_the_scope_fence_holds` RED on a correct tree: `fabric_diff` hardcoded
`..HEAD`, so **five** untouched-tree assertions in
`tools/docs_tests/test_requirement_ledger.py` compared their pinned base against
`HEAD` and therefore forbade every future commit under `src/`, `runtime/`,
`examples/`, `public/`, `pyproject.toml` and `tests/`, forever. Dave ruled twice
— four assertions, then the fifth on residual 1 — and bound all five to Phase
21.1's close `951eb4a3e2d8e072ec7f059e372545753d415a25`.

**Consequence for this plan's own proof, stated so a close verifier does not
misread it:** `tools/docs_tests/test_requirement_ledger.py` and the two pin
files under `.planning/phases/21-…/` **changed during this phase**. That change
is RULED and is not a fence breach. This plan's per-member diff covers `src`,
`runtime` and `examples` — the three members the phase claims are untouched —
and all three are empty. `tools/` is not one of them and was never asserted
empty by this phase. No plan in waves 2–5 edited that module.

### The open residual, carried and not closed

**Nothing asserts that a bounded assertion actually READS the pin.**
`test_the_pinned_diff_ceiling_resolves` proves the pin is *sane*; nothing proves
it is *used*. Verified both ways: deleting the ceiling argument from
`test_no_test_was_written_to_manufacture_a_citation` leaves the module at **113
passed**, while deleting it from `test_the_scope_fence_holds` **is** caught
(**1 failed, 112 passed**), because Phase 22 has since written under `public/`.
The bound proves itself only where the tree has since moved. Closing it needs an
assertion over the module's own source shape, a class of check the module does
not have. Recorded as residual 2 on the `D-IMPL-188` amendment; carried, not
closed. Residual 3 — nothing stops a future executor **advancing** the ceiling
to go green — is a governance question Dave has already flagged for the
`D-GATE-22` sitting.

---

## `D-06` — LANDED

Recorded here because this plan's must-have was written before the disposition
was known and asks for an *owed* section. **There is none to write, and its
absence is the correct outcome.**

Plan `22-03` shipped the per-claim symbol resolver in task 3 (`3ed8403`):
`tools/docs_tests/test_adoption_wording.py::test_every_published_node_id_resolves`,
with its non-vacuity floor `test_the_published_tree_carries_node_ids_to_resolve`
and its control
`test_control_12_a_renamed_symbol_and_a_missing_file_are_both_refused`, taking
the module from 21 tests to 24. Measurement, from `22-03-SUMMARY.md`: **22 node
ids across the published tree, all on the new page; 0 unresolvable paths, 0
missing symbols.** ROADMAP criterion 15's naming obligation fires only when the
stretch does not land.

---

## Two gate findings carried out of wave 4

Both are recorded in the phase record; neither is exposed today.

1. **A row checked by only one of the two checkers is half checked.** The ledger
   gate's `refuse_unresolvable` checks the cited **path** exists; the citation
   lint checks the **symbol** exists. A node id mutated to a nonexistent symbol
   left `test_requirement_ledger.py` green at 113 and reddened only
   `tools.lints --all`. Both run in `ci-core` — the gate through
   `make gate-tools`, the lint through `make lint` — so the guarantee is whole
   in CI; the division is worth stating where a later reader finds it.
2. **The system-interpreter trap**, re-measured above: 258 rows at exit 0
   against the venv's 264.

---

## Gates

| Gate | Result |
| --- | --- |
| `make lint` | exit **0** |
| `make typecheck` | exit **0** — 211 files |
| the chunked test leg (4 foreground invocations) | exit **0** ×4 — 4105 passed / 118 skipped |
| `make gate-tools` | exit **0** — 406 + 291 (re-run after the record write: 406 + 291) |
| `make examples` | exit **0** |
| `make docs-strict` | exit **0** |
| `PYTHONPATH=.:src:runtime .venv/bin/python -m tools.lints --all` | exit **0** |
| `pytest tools/docs_tests/test_requirement_ledger.py -q` | **113 passed** |
| `pytest tools/docs_tests/test_retirement_sweep.py -q` | **33 passed** |
| `git status --porcelain src/ runtime/ examples/ public/` | prints nothing |
| `git diff --stat HEAD -- .planning/ROADMAP.md` | prints nothing |

---

## Deviations from Plan

### Auto-fixed

**1. [Rule 3 — Blocking] The CI legs were run before task 2's record write**

- **Found during:** Task 2 drafting.
- **Issue:** The plan orders task 2 (write the record) before task 3 (run CI),
  but the record's own required contents include the CI result. Following the
  order literally would have written a green into the phase record before
  anybody had produced it — `T-22-29`'s harm exactly.
- **Fix:** Ran all six legs in the foreground first, wrote the record with the
  measured figures, then regenerated the report (which is the part of task 3's
  ordering that D-15 actually constrains) and **re-ran `make gate-tools`** after
  both, since that leg carries `test_the_committed_report_is_current`.
- **Files modified:** none beyond the plan's declared set.
- **Commit:** `e7a6b40`, `9311db4`.

**2. [Rule 2 — the proof was weaker than the claim] Four chunks, not three, and
the union proven by set equality rather than by the sum alone**

- **Found during:** Task 3 planning of the chunk partition.
- **Issue:** The plan's acceptance criterion is that the chunk collected counts
  **sum** to the full count. A sum is satisfiable by a partition that
  double-counts one directory and omits another of the same size — the same
  defect class as a whole-tuple pathspec diff.
- **Fix:** Collected the node ids of each chunk and of the full suite, compared
  them as **sets** (`diff` exit 0) and checked that de-duplicating the union
  changes nothing, which proves disjointness. The sum is recorded as the plan
  requires and the set equality is recorded beside it. Four chunks rather than
  three so no invocation approaches ten minutes; the longest is 5m24s.
- **Files modified:** none.
- **Commit:** n/a (measurement).

**3. [Rule 2 — the plan's tree-set command sees one level] The recursive
directory-set comparison was run as well**

- **Found during:** Task 1.
- **Issue:** `git ls-tree -d --name-only <rev> examples/` lists direct children
  only, so a tree created, moved or removed below the first level would satisfy
  it.
- **Fix:** Ran the plan's literal command (14 = 14, `diff` exit 0) **and** the
  recursive form (34 nested trees = 34, `diff` exit 0). Both recorded.
- **Files modified:** none.
- **Commit:** n/a (measurement).

### Not fixed — nothing escalated

No Rule 4 situation arose. No CI leg failed, so the *"do not fix another phase's
defect"* clause was never reached. Nothing under `src/`, `runtime/`,
`examples/`, `public/` or `tools/` was modified by this plan, and
`.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md` and `docs/DECISIONS.md` were
not touched.

---

## Threat Flags

None. This plan ships no runtime surface, no network-reachable code, no request
handler and no authentication path; it writes two documents and reads the tree.

---

## Known Stubs

None.

---

## Tracking deferred to the orchestrator

`.planning/ROADMAP.md`'s Phase 22 plan checkboxes and its progress table are the
orchestrator's to update by hand (`D-15`). This plan did not touch that file.
Requirement rows are already discharged: `DOCS-15` reads `Complete as ruled` in
both channels as of `cbe702a`, and no `requirements.mark-complete` was run in
this wave either.

**The phase is NOT complete after this plan.** `22-06` is the wave-6 gate on the
`21.1-10` precedent: it does not run the cross-AI panel, it refuses to let the
phase be reported complete until the panel has run on the SHIPPED tree with the
source inlined and its findings verified against the tree, it carries the
blocking checkpoint at which Dave rules, and it logs `D-GATE-22` and regenerates
the coupling report afterwards — which is the regeneration that finally satisfies
ROADMAP criterion 13's *"LAST"*, not the one below.

---

## Self-Check

- `.planning/STATE.md` — FOUND; 2219 lines; 8 frontmatter keys; the Phase 22
  block is the head of `last_activity`.
- `docs/surface/examples/RETIREMENT-COUPLINGS.md` — FOUND; 264 rows / 81 files.
- `.planning/phases/22-…/22-05-SUMMARY.md` — FOUND (this file).
- Commits resolve in `git log`: `e7a6b40`, `9311db4`.
- `git status --porcelain src/ runtime/ examples/ public/` prints nothing.

## Self-Check: PASSED

---

## The terminal regeneration — after this SUMMARY was written

`22-05-SUMMARY.md` is itself an `os.walk` subject, so a report regenerated
before it is stale at the moment the plan closes. Same command, same
interpreter:

```
$ PYTHONPATH=.:src:runtime .venv/bin/python tools/retirement_sweep.py --report
wrote docs/surface/examples/RETIREMENT-COUPLINGS.md
264 coupling rows across 81 files (146 rows outside the three swept trees); 1897 files scanned
SWEEP EXIT=0
```

**264 rows / 81 files, unchanged. `git diff` is EMPTY this time** — writing this
SUMMARY added a scanned file (1896 → 1897) but no coupling row and no *Measured
but not assigned* row, so the committed report was already current. Byte-identical
is an acceptable outcome of the confinement check; it was never the completion
condition, and the first regeneration's diff (`.planning/STATE.md` 11 → 15) is the
one that had to be classified. Forbidden-subject changed lines: **0** — trivially,
since there are no changed lines at all.

```
$ pytest tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current -q
1 passed in 9.51s
```

**This is the last regeneration of the phase's SHIPPED DELIVERABLES — it is NOT
ROADMAP criterion 13's "LAST".** Plan `22-06` writes `docs/DECISIONS.md` and
further `.planning/` files after this point and regenerates the report again as
its own final action; **that** is criterion 13's LAST. A close verifier reading
only this section would discharge criterion 13 here and never check `22-06`.
