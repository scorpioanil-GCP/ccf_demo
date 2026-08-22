---
phase: 21-requirement-ledger-reconciliation-what-is-actually-discharge
plan: 06
subsystem: testing
tags: [ledger, audit, completeness-gate, sabotage-controls, recon-rows, ci]

requires:
  - phase: 21-requirement-ledger-reconciliation-what-is-actually-discharge
    provides: all 54 verdicts, the strict parser, the pinned diff base, `PHASE_OWN_ROSTER`, CONTROL 11, and the findings record Dave rules from
provides:
  - the standing completeness gate (`Check C`) — a frozen 54-member roster re-derived from the pinned base and compared id-for-id, never by length
  - verdicts for the phase's own ten `RECON-` rows, in both channels, written BEFORE the close panel
  - the `tests/`-untouched proof of `D-05`, with a control proving the comparison compares something
  - CONTROL 15 — a control written because a sabotage this plan specified reported GREEN for a measured reason
  - `DCD-02`'s status cell repaired: the one row in the ledger that carried a verdict and cited no file
  - `make ci` exit 0 with the generated coupling inventory regenerated last and committed
affects: [21-07]

tech-stack:
  added: []
  patterns:
    - "A frozen roster is verified by RE-DERIVING it from the pinned base and comparing id-for-id; a length check cannot see a swap and is itself the hardcoded count `D-21` forbids"
    - "A control anchored on a literal string is anchored on a SNAPSHOT of its subject — resolve the anchor at run time"
    - "When a specified sabotage reports GREEN, measure why before accepting it; then write the control that would have gone red"
    - "A control verifies its own subject reaches the branch under test: assert the victim is NOT already an offender before doctoring it"

key-files:
  created:
    - .planning/phases/21-requirement-ledger-reconciliation-what-is-actually-discharge/21-06-SUMMARY.md
  modified:
    - tools/docs_tests/test_requirement_ledger.py
    - .planning/REQUIREMENTS.md
    - .planning/STATE.md
    - .planning/ROADMAP.md
    - docs/surface/examples/RETIREMENT-COUPLINGS.md

key-decisions:
  - "`test_the_working_set_roster_has_fifty_four_members` was NOT written as specified: `D-21` forbids a standing check carrying a row count, and the plan's own acceptance criterion says the roster is named ids and no count is carried. The roster is re-derived from the strict parse at the pinned base and compared id-for-id instead — strictly stronger, because a length check cannot see a swap"
  - "`RECON-10` takes `Partial`, not `Complete`, against wave 5's `requirements-completed` claim: the row's own text says the three counters are CORRECTED, and one of the three was reported instead under `D-19`(a)"
  - "`RECON-09` takes `Partial` because `D-GATE-21` does not exist and cannot exist before Dave rules; writing `Complete` here would be the unearned tick the phase was commissioned to remove"
  - "`DCD-02`'s missing citations were REPAIRED rather than reported, because this is the last execution wave before the panel and the alternative was shipping a known criterion-3 violation"
  - "CONTROL 15 was added beyond the plan, because the plan's specified sabotage of `verdict_token` was measurably incapable of moving CONTROL 11"

patterns-established:
  - "A phase audits its own rows under the gate it imposes on the rows it audits, and does so before the close panel rather than inside the gate checkpoint"

requirements-completed: [RECON-01, RECON-02, RECON-03, RECON-05, RECON-06, RECON-08]

duration: 95min
completed: 2026-08-22
---

# Phase 21 Plan 06: The Completeness Gate, the Phase's Own Ten Rows, and Green CI — Summary

**The ledger can no longer lose a verdict in silence: a frozen roster of fifty-four named ids, re-derived from the strict parse at the pinned base and compared id-for-id rather than counted, now stands between this ledger and the state it was in when the phase began — and the phase's own ten rows were written into it before the close panel, under the same evidence bar, two of them `Partial` because a phase that grades itself `Complete` on work Dave has not yet approved has reproduced the defect it was commissioned to remove.**

## Performance

- **Duration:** ~95 min
- **Tasks:** 3 of 3
- **Commits:** 2 task commits + this one
- **Tests added:** 10 — all in `tools/docs_tests/`, none under `tests/`. The module went 35 → **45**; `gate-tools` leg 2 went 189 → **199**. `make test` is **4105 passed / 118 skipped**, byte-for-byte the wave-1 through wave-5 baseline, which is the mechanical proof that `D-05` held.

## Task Commits

1. **Task 1: the ten `RECON-` verdicts, `Check C`, and CONTROLS 10/12/13/14/15** — `f285ac2` (feat)
2. **Task 2: the position files, hand-edited** — `e0eeb0c` (docs)
3. **This SUMMARY and the regenerated coupling inventory** — final commit (docs)

## `make ci` — exit 0

| Leg | Result |
|---|---|
| `make lint` (`python -m tools.lints --all`) | **exit 0** |
| `make typecheck` (`mypy --strict`) | **exit 0** — 211 source files |
| `make test` | **exit 0** — **4105 passed / 118 skipped**, 636.74s |
| `make gate-tools` | **exit 0** — leg 1 **406**, leg 2 **199** (was 189) |
| `make examples` | **exit 0** |
| `make docs-strict` | **exit 0** — mkdocs build + `tools/publish_scan.py site` |
| **`make ci`** | **exit 0** |

Run in the foreground in one invocation and read in full rather than piped through `tail`. **The generated coupling inventory was regenerated LAST after every `.planning/` write and committed, then re-verified current after `make ci` returned.**

## The census, measured at execution time and not carried

Produced by the strict parse of the ledger as it stands, against the frozen roster.

| Verdict | Rows in the 54 | Rows in the phase's own ten |
|---|---|---|
| `Complete` | 38 | 8 |
| `Complete as ruled` | 2 | 0 |
| `Partial` | 9 | 2 |
| `Not built` | 5 | 0 |
| `Orphaned` | **0** | 0 |
| **Total** | **54** | **10** |

**My parse agrees with wave 5's, row for row, and it was run before anything was written** — the project note warned that a disagreement would mean one of us was wrong, so the check was made first rather than assumed. The traceability table holds **143** rows, a reported measurement carried by no check (`D-21`), and **zero rows anywhere in the ledger now read `Pending`**.

## The ten `RECON-` verdicts

Each row's predicate is its own text in `.planning/REQUIREMENTS.md` and the one-line statement on the ROADMAP's Phase 21 `**Requirements:**` line. Each verdict is written into **both** channels (`D-02`). Every citation below was run through the shipped resolver — path AND symbol — **before** a single one was written: 41 candidates checked, 0 refused.

| Id | Verdict | Load-bearing evidence |
|---|---|---|
| `RECON-01` | **Complete** | `test_every_row_in_the_working_set_carries_a_verdict`, `test_no_row_in_the_working_set_carries_two_verdicts`, `test_the_working_set_roster_is_exactly_the_strict_parse_at_the_pinned_base`, `WORKING_SET_ROSTER`, `COMPLETE_FAMILY` |
| `RECON-02` | **Complete** | `test_every_cited_path_in_a_status_cell_resolves_as_written`, `test_the_scan_finds_citations_to_check`, `test_no_test_was_written_to_manufacture_a_citation`, `test_control_13_a_changed_tests_tree_would_be_detected` |
| `RECON-03` | **Complete** | `refuse_unresolvable` plus CONTROLS 1, 2, 3, 4, 4b and 5b — five refusal branches, each with a control that reaches it |
| `RECON-04` | **Complete** | `test_the_scope_fence_holds`, `test_the_fabric_is_untouched` — the work list is `21-FINDINGS.md` §2 and the empty fence is the proof nothing on it was built |
| `RECON-05` | **Complete** | `test_every_row_in_the_working_set_carries_a_verdict`, `test_the_two_status_channels_agree` — the split is `21-DOCS-16-SPLIT.md`, all eighteen unflipped and undropped |
| `RECON-06` | **Complete** | `test_the_two_status_channels_agree`, `channel_disagreements`, CONTROL 6, CONTROL 7 |
| `RECON-07` | **Complete** | `test_the_human_needed_verification_records_are_untouched`, `test_the_uat_roster_matches_the_records_on_disk`, `UAT_RECORDS`, `derived_uat_records` |
| `RECON-08` | **Complete** | `test_the_fabric_is_untouched`, `test_the_scope_fence_holds`, `test_the_citation_lint_is_not_modified`, CONTROL A |
| `RECON-09` | **Partial** | `tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current` — criterion 13 discharged here; **criterion 14 outstanding: `D-GATE-21` does not exist** |
| `RECON-10` | **Partial** | `traceability_rows`, `verdict_token` — two counters corrected from the parse; **the third reported, not corrected** |

Unqualified module paths above are `tools/docs_tests/test_requirement_ledger.py`; the ledger itself carries the full repo-relative path on every citation, which is what `--citations` and `refuse_unresolvable` both check.

### Why two of the phase's own rows are `Partial`, and why that is the point

**`RECON-09`** asks for `make ci` exit 0 with the inventory regenerated last **and** a `D-GATE-21` entry logged on Dave's approval. The first limb is discharged in this plan. The second cannot be discharged by an executor at all — it is the gate. A `Complete` here would be a verdict written before the thing it claims exists, which is the precise defect the phase was commissioned over, reproduced by the phase inside its own ledger.

**`RECON-10`** says the three stale counters are *"CORRECTED rather than merely reported."* Two were. The third — the ROADMAP's `All **42**` — was **reported**, correctly and under `D-19`(a), because the sentence claims to be the traceability table's row count while the paragraphs beneath it enumerate a defined subset summing to exactly 42, and the parse cannot settle which it means. **Wave 5's SUMMARY frontmatter lists `RECON-10` under `requirements-completed`.** The ledger verdict disagrees with it deliberately: the verdict is taken against the row's own text, and the row's text says corrected. The outstanding limb is named in the cell and is a ruling for Dave, not work for an executor.

## Every control in the module, the mutation that made it red, and the result

The controls this plan added are in bold. The rest are re-stated from waves 1 and 2 with their landing wave, so the table is the module's whole control surface in one place rather than this plan's slice of it.

| Control | Falsifies | Mutation applied to the SHIPPED function | Result |
|---|---|---|---|
| CONTROL A (w1) | all four emptiness assertions at once | `return completed.stdout` → `return ""` | RED |
| CONTROL B (w1) | an unresolvable base returning `""` | `if completed.returncode != 0:` → `if False:` | RED |
| CONTROL C (w1) | an empty base / empty path list | argument guards, exercised | GREEN by refusal |
| CONTROL 1 (w1) | an ambiguous bare basename | bare-basename branch removed | RED |
| CONTROL 2 (w1) | a *unique* bare basename | same | RED |
| CONTROL 3 (w1) | a path not in the tree | existence predicate → always true | RED |
| CONTROL 4 / 4b (w1) | `::symbol` on a non-Python path; a directory | existence predicate → always true | RED (4b); 4 GREEN by refusal on both subjects |
| CONTROL 5 / 5b (w1/w2) | a zero-row and a zero-citation parse | the guard swallows the empty parse | RED |
| CONTROL 6 / 7 (w1) | a verdict or an id in one channel only | `channel_disagreements` → `return []` | RED |
| CONTROL 8 (w1) | a misspelled header reported as clean | `traceability_rows` returns `[]` | RED |
| CONTROL 9 / 9b (w1) | a word outside the vocabulary; a LAST-bolded-run reader | `verdict_token` → last bolded run | RED (9b), **re-run in this plan and still RED, on 9b and four shipped assertions besides** |
| CONTROL 11 (w1) | a cell carrying two bolded verdicts | `doubled_verdicts` → `return []` | RED |
| **CONTROL 10** | a roster row returned to `Pending` passing unnoticed | `working_set` iterates an EMPTY roster | **RED** |
| **CONTROL 12** | a roster id deleted from the table, checked as 53 | same mutation | **RED** |
| **CONTROL 13** | the `tests/`-untouched assertion comparing nothing | (`fabric_diff` non-emptiness; CONTROL A's twin) | **GREEN, non-vacuously** |
| **CONTROL 14** | a phase-own row returned to `Pending` | `phase_own_verdicts` iterates an EMPTY roster | **RED** |
| **CONTROL 15** | a `verdict_token` that hunts for a verdict anywhere in the cell | `verdict_token` → first `**…**` run anywhere | **RED** |
| positive twin (w1) | a checker red on everything | — | GREEN on a real, ambiguous-basename path |
| `test_the_unmodified_document_passes` (w1) | attribution of every refusal | — | GREEN |

**Every mutation above was applied to the shipped function, observed, and reverted from a backup taken first.** CONTROLS 10 and 12 also verify their own subject reaches the branch under test — each asserts the victim is **not already** an offender on the real document before doctoring it, so a green-before/red-after pair is attributable to the mutation and to nothing else. That is the wave-1 lesson (a control whose subject is refused by an earlier branch tests nothing) made structural rather than remembered.

## The sabotage that reported GREEN, and what was done about it

The plan required: *"change `verdict_token` to return the first `**…**` run anywhere in the cell rather than the leading one; CONTROL 11 FAILS."* It was run. **CONTROL 11 stayed green, and so did every other test in the module.** Following the wave-4 rule — never accept a green sabotage without measuring why — two independent causes were measured:

1. **`doubled_verdicts` never calls `verdict_token`.** It reads `BOLDED_RUN` directly. CONTROL 11's entire subject is `doubled_verdicts`, so **no mutation of the token reader can move that control.** The criterion is unsatisfiable as written, not merely unmet.
2. **The mutation was invisible to the whole module, not just to CONTROL 11.** Across all 143 status cells, the first bolded run and the leading token are **identical on every row**, because every cell in this ledger opens with its verdict. There was no subject anywhere in the corpus on which the two readers differ.

Reporting that and moving on would have left a real hole: a `verdict_token` that hunts for a vocabulary word anywhere in the prose would find one in almost any honest sentence, and nothing in the module would have noticed. **`CONTROL 15` closes it** — it doctors a cell to read `shipped in wave five — **Complete**`, a shape the corpus does not contain, and asserts the refusal names the row. Under the shipped reader the leading token is the prose prefix, which is not in the vocabulary and is refused. Under the mutation it reads `Complete` and is accepted. Re-run: **CONTROL 15 RED, alone, and restored.**

This is the third time in this phase that a control has been found weaker than it looked, and the second time the cause was that the mutation was **invisible to the checker** rather than tolerated by it.

## `DCD-02` — the one row that carried a verdict and cited no file

Criterion 3 requires every verdict other than `Not built` and `Orphaned` to cite evidence the citation lint resolves. Measured across the 54 before anything was written, **exactly one row failed it**: `DCD-02`, whose status cell read `**Partial** (plans `15.6-05`, `15.6-06`)` — two plan numbers and a ruling id, and no file at all.

**Why no wave caught it.** The cell is **byte-identical to the pinned base**. `DCD-02` already read `**Partial**` before this phase started, so every wave's parse saw a row that already carried a verdict, and no wave re-read it against criterion 3. It is the same class as the leftovers waves 3, 4 and 5 each found — a statement that no parser reads — arriving from the other direction: a cell the parser *did* read, and passed, because the property it was short of was never asserted over it.

**Repaired, not reported.** The four `path::symbol` citations were lifted from this row's own checkbox twin, which has carried them since Phase 15.6, and the cell now says which plan added them and why. The verdict itself is untouched. This is the last execution wave before the panel; the alternative was shipping a known criterion-3 violation next to a `RECON-02` that said so.

## Deviations from Plan

### 1. [`D-21` takes precedence] The roster is verified id-for-id, not by length

- **Specified:** `test_the_working_set_roster_has_fifty_four_members` — *"the roster's length is 54."*
- **Why not:** `D-21`'s binding consequence is that **no standing check in this phase hardcodes a row count**, and it names the 54-member working set as one of the three places a frozen roster of named ids goes instead. The plan's own acceptance criterion agrees: *"per `D-21` the roster is named ids and no row count is carried."* The action text and the criterion disagree, and `D-21` is binding above both.
- **What shipped:** `test_the_working_set_roster_is_exactly_the_strict_parse_at_the_pinned_base` — the roster is re-derived by parsing `git show <base>:.planning/REQUIREMENTS.md` and compared **id-for-id**, plus an assertion that every roster id is still present in today's table. This is the idiom `test_the_uat_roster_matches_the_records_on_disk` already sets in the same module.
- **Strictly stronger, not a weakening:** a length check cannot see a **swap** — drop `CLNT-17`, add `CLNT-23`, and the number is unmoved. It also cannot see the roster drifting away from the parse that produced it. The re-derivation is additionally the non-vacuity proof: an empty derivation fails the comparison loudly instead of a roster assertion passing over a set nobody produced.

### 2. [Rule 3] CONTROLS 6, 9 and 11 were anchored on a string this plan deleted

- **Found during:** Task 1, first module run after the verdicts landed.
- **Issue:** all three doctored the literal `| RECON-10 | Phase 21 | Pending |`. Writing `RECON-10`'s verdict deleted that line, and `_doctored` refuses a non-unique anchor — so all three went red rather than silently doctoring nothing, which is `_doctored` working exactly as designed.
- **Fix:** a shared `_table_line(document_text, req_id)` helper resolves the row at run time and refuses if it matched zero rows or more than one. CONTROL 11 is **re-aimed, not renumbered and not re-added** — `grep -c "test_control_11"` is still 1.
- **The general lesson, recorded because it will recur:** a control anchored on a literal string is anchored on a *snapshot* of its subject. Resolve the anchor at run time and assert it is unique.

### 3. [Rule 2] CONTROL 15 was added beyond the plan

Covered in full above. The plan asked for a sabotage that could not, structurally, do what it claimed; the control that would have gone red was written instead of the finding being merely noted.

### 4. [Rule 1] `DCD-02`'s status cell was repaired

Covered in full above. Not authorised by the plan in so many words; in scope (`.planning/REQUIREMENTS.md` is this plan's file), additive, and the alternative was a knowingly-shipped criterion-3 violation.

### 5. [Rule 1] Wave 1's `test_every_recon_row_is_present_in_both_channels` asserted the opposite of this plan's job

- **Issue:** as landed, it asserted every `RECON-` row reads a bare `Pending` and is unticked — true for five waves and false the moment their verdicts were written. Wave 1's own docstring said plan `21-06` would turn these into verdicts, so the amendment is the one wave 1 anticipated.
- **Fix:** the Pending expectation is **retired, not relaxed** — what replaces it (`test_every_phase_own_row_carries_a_verdict` + CONTROL 14) requires the opposite and is stricter. What stays is the floor that outlives both states: the ids are in both channels and the channels agree about each one.

### 6. [Rule 1] `21-05-PLAN.md` was still unticked in the ROADMAP's plan checklist

- **Found during:** Task 2, checking the checklist against the progress count.
- **Issue:** wave 5 landed and wrote its SUMMARY but left its own checkbox unticked, so the checklist said 4 complete while the progress row said 5.
- **Fix:** ticked, alongside `21-06`. A one-character leftover, and the same shape as the ledger rows this phase exists over.

### 7. The module docstring and the `VERDICT_VOCABULARY` comment asserted the completeness gate was absent

- **Found during:** the whole-module sweep for statements the new code contradicts (project note 6, applied to code prose rather than to the ledger).
- **Issue:** the module docstring said the completeness count *"is deliberately NOT here … It belongs to the phase's last plan"*, and `VERDICT_VOCABULARY`'s comment said refusing a leftover `Pending` *"is deliberately not this module's job"*. This plan is that last plan, and it made both false.
- **Fix:** both amended to say what happened and when, keeping the reason the gate was withheld — a reader five waves from now needs to know why it landed late, not just that it landed.

### 8. Regeneration ran inside task commits 1 and 2, not only in task 3

- **Why:** the coupling inventory walks `.planning/`, so a task commit that edits the ledger and does not regenerate leaves `make gate-tools` red at that commit — against the `ci-core`-green-from-wave-1 contract. Regenerated after each task's last `.planning/` write, and again after this SUMMARY, which is the LAST write of the phase. Same disposition as waves 4 and 5.

### 9. Two `.md` files in `docs/` are untracked and were left alone

`docs/CCF_SDK_DE_REQUIREMENTS.md` and `docs/Context_Product_Specification_Standard_v0-3.md` were untracked before plan `21-02` and are untracked still. **Pre-existing, reported, not touched** — the same disposition as waves 2, 3, 4 and 5.

## No GSD state or roadmap writer was invoked at any point in this plan

Stated explicitly because it is a required output and because five distinct such handlers have corrupted the file they wrote in this repository (`D-15`, `D-IMPL-154`, `D-IMPL-155`).

- **Zero** invocations of any `gsd-sdk query state.*` or `roadmap.*` **writer**. The only `gsd-sdk` calls in this plan's entire shell history are `roadmap.get-phase 21 --raw` and `state.load` — both **reads**, both run **after** the hand-edits, never before.
- `.planning/STATE.md` and `.planning/ROADMAP.md` were each copied to a backup **outside the tree** before the first edit, edited by hand, and `git diff` inspected after each edit.
- `.planning/STATE.md`'s diff is **80 insertions and 1 deletion** — the deletion is `last_updated`, the intended replacement. The `progress:` block is **byte-identical**, verified by diffing the block against the backup. The frontmatter re-parses with `yaml.safe_load` to **all eight top-level keys**.
- The historic wave-5 `stopped_at` sentence was restored **verbatim** after an early edit changed one word of it. A dated log is corrected by appending, never by rewriting what was true when written.
- `.planning/ROADMAP.md`'s diff is **three lines**: the two plan checkboxes and the Phase 21 progress row. **No line beginning with two spaces and a criterion number appears in it**, checked mechanically.

## The success-criteria integrity check, run AFTER the hand-edit

`gsd-sdk query roadmap.get-phase 21 --raw` re-parses to exactly **14** criteria, one per unwrapped line, **after** the ROADMAP hand-edit — not before. This project has shipped two phases gated against a single parsed truth because a wrapped criterion became one line, so the assertion is worthless taken at the wrong moment.

## The CI checkout depth, on the job that actually runs this module

| Check | Result |
|---|---|
| `awk '/^  docs:/{f=1;next} f&&/^  [a-z_-]+:/{f=0} f' ci.yml \| grep -c "fetch-depth: 0"` | **1** |
| the same range form over the **`test`** job (singular) | **1** |
| `grep -c "fetch-depth: 0" .github/workflows/ci.yml` | **2** |

This matters more from this commit than it did from wave 1: `Check C` adds a **second** kind of pinned-base read — `git show <base>:.planning/REQUIREMENTS.md`, not just `git diff` — and `base_ledger_text` raises on a non-zero `git` exit for the same reason `fabric_diff` does. On a depth-1 clone both raise. The range form must **exclude** the start line; `awk '/^  docs:/,/^  [a-z]/'` evaluates its end pattern on the same record, collapses to the single line `  docs:`, and returns 0 for a correct workflow.

## Verification

| Check | Result |
|---|---|
| `pytest tools/docs_tests/test_requirement_ledger.py -q` | **exit 0** — **45** passed (was 35) |
| `pytest tools/docs_tests/test_requirement_ledger.py tools/docs_tests/test_retirement_sweep.py -q` | **exit 0** — 78 passed |
| `python -m tools.lints --citations` | **exit 0**, 0 findings |
| `mypy --strict tools/docs_tests/test_requirement_ledger.py` | **exit 0** |
| `make ci` | **exit 0** |
| `make gate-tools` | **exit 0** — leg 1 **406**, leg 2 **199** |
| `make test` | **exit 0** — **4105 passed / 118 skipped** — identical to every prior wave, the proof `D-05` held |
| rows in the working set carrying a verdict | **54 of 54**; **0** lacking one; **0** carrying two |
| rows reading a bare `Pending` anywhere in the ledger | **0** |
| `grep -c "| Pending |" .planning/REQUIREMENTS.md` | **0** |
| all ten `RECON-` rows, bolded vocabulary token, both channels | **yes** — 8 `Complete`, 2 `Partial` |
| `channel_disagreements` / `vocabulary_offenders` / `doubled_verdicts` | **`[]`**, **`[]`**, **`[]`** |
| `refuse_unresolvable(ledger_text())` | **`[]`** |
| candidate citations pre-verified before writing (path AND symbol) | **41 checked, 0 refused** |
| `grep -c "test_control_11" tools/docs_tests/test_requirement_ledger.py` | **1** — from plan `21-01`, neither duplicated nor renumbered |
| the `D-21` hardcoded-count guard over the module | **0 matches** |
| `grep -n "skipif"` in the module | **no match** |
| `gsd-sdk query roadmap.get-phase 21 --raw`, AFTER the hand-edit | **14** criteria, one per unwrapped line |
| `git diff -- .planning/ROADMAP.md \| grep -E "^[+-]  [0-9]+\. "` | **no match** |
| `git diff --stat <base>..HEAD -- tests/` | **empty** |
| `git diff --stat <base>..HEAD -- src/ runtime/ examples/ public/ pyproject.toml` | **empty**, every path |
| `git diff --stat <base>..HEAD -- tools/lints/citations.py` | **empty** |
| `git diff --name-only <base>..HEAD -- tools/` | only `tools/docs_tests/test_requirement_ledger.py` |
| `retirement_sweep.py --report` then `git diff --stat` on the report | **prints nothing** — the committed report is current |
| `git status --porcelain` after the final commit | only the two pre-existing untracked `docs/` files |
| STATE.md frontmatter after the hand-edit | **8 keys intact**, `progress:` byte-identical |

## What plan `21-07` inherits

- **A ledger with no `Pending` in it and a standing gate that keeps it that way.** `21-07` adds no ledger rows; every row it reviews was written before it, on purpose.
- **The close panel reviews the SHIPPED CODE and the shipped ledger, not the plans** (`CLAUDE.md` §3.1) — those decisions are executed. Write it to `21-CLOSE-REVIEWS.md` so the pre-execution plan review survives, brief it on the findings already known, and point it at what is **adjacent** to each.
- **Verify every finding against the tree before recording or acting on it**, and record the rejected ones as rejected. This project has twice received confident, well-formatted, false findings.
- **Two things Dave must rule on that no executor can:** the `All **42**` counter's provenance question, and the four-row knot on the work list (`DOCS-17` ↔ `CLNT-17` ↔ `DOCS-14` ↔ `EXAM-02`).
- **`D-11` holds to the end of the phase.** Nothing on the work list is `21-07`'s to start.
- **`RECON-09` closes at the gate, not before.** Its outstanding limb is `D-GATE-21` itself.

## Threat Flags

None. This plan reads tracked repository files and writes markdown and one test module under `tools/docs_tests/`. No credential, no network call, no external input, no package installed — `T-21-SC` stays true by the `pyproject.toml` emptiness assertion inside `FENCE`.

Register coverage. **`T-21-32`** (a completeness assertion passing over an empty roster) — closed three ways: the roster is a frozen constant re-derived from the pinned base and compared id-for-id, CONTROL 12 refuses a roster id missing from the table, and CONTROL 10 refuses a row returned to `Pending`; both were watched red under an empty-roster mutation of the shipped function. **`T-21-33`** (a cell carrying two verdicts read as one) — `verdict_token` is anchored at `^`, CONTROL 11 watches the doubled-cell refusal fire, and CONTROL 15 now covers the one weakening the corpus could not expose. **`T-21-34`** (a test written in-phase to manufacture a citation) — `fabric_diff(base, ("tests/",))` asserted empty, CONTROL 13 proves the helper produces output on a tree that genuinely differs, and `make test` at exactly the prior baseline is the independent corroboration. **`T-21-35`** (a GSD writer corrupting a position file) — no writer invoked at all; backups, hand-edits, diffs, a frontmatter re-parse, and 14 criteria re-parsed after the edit. **`T-21-36`** (a stale generated report at close) — regenerated last, committed, and re-verified current after `make ci` returned. **`T-21-37`** (a pinned-base assertion that cannot resolve its base in CI) — `fetch-depth: 0` confirmed on the `docs` job by a range form that excludes its start line, and on the `test` job; both new base reads raise on a non-zero `git` exit. **`T-21-37b`** (the phase's own rows entering the ledger unreviewed) — written in this plan, before the panel and before the gate, and held to it by `test_every_phase_own_row_carries_a_verdict` and CONTROL 14.

## Known Stubs

None.

## Self-Check: PASSED

The file this plan created exists on disk. Both task commits `f285ac2` and
`e0eeb0c` resolve in this repository. Re-verified after the last write: the
ledger module is 45 passed, the sweep and ledger modules together are 78 passed,
`--citations` is exit 0, `make ci` is exit 0, and the pinned-base diff over
`src/ runtime/ examples/ public/ tests/ pyproject.toml tools/lints/citations.py`
is empty on every path.

Five claims here were measured rather than asserted, because all five read
plausibly and could have been wrong.

- **The census across the 54** was re-parsed from the ledger before anything was
  written, precisely so that a disagreement with wave 5's figures would surface
  as a finding rather than as a silent inheritance. It agrees exactly.
- **The green sabotage was diagnosed with two independent measurements** — that
  `doubled_verdicts` does not call `verdict_token`, and that no cell in the
  ledger distinguishes the two readers — rather than explained away.
- **All 41 candidate citations were resolved through the lint's own symbol
  resolver before one was written**, not after a red gate.
- **Every sabotage was run against the shipped function and restored from a
  backup taken first**, and each was run *after* the relevant commit, because
  `git diff <base>..HEAD` compares commits and is blind to the working tree.
- **`DCD-02`'s shortfall was found by running criterion 3's predicate across the
  whole roster**, not by reading cells. Reading would not have found it: the
  cell is fluent, correctly verdicted, and cites two plan numbers that look like
  evidence until you try to open one.
