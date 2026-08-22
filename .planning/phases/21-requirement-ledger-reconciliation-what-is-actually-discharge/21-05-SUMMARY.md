---
phase: 21-requirement-ledger-reconciliation-what-is-actually-discharge
plan: 05
subsystem: testing
tags: [ledger, audit, work-list, verification-debt, counters, citation-drift]

requires:
  - phase: 21-requirement-ledger-reconciliation-what-is-actually-discharge
    provides: all 54 verdicts, the four lane SUMMARYs' closing-cost statements, the strict parser, the pinned diff base and the eleven-record UAT roster
provides:
  - `21-FINDINGS.md` — the five-section document Dave rules from
  - the D-11 work list: five `Not built` rows in two groups, four of them one knot
  - the D-13/D-20 roster of 27 `human_needed` items across 11 records, quoted verbatim
  - two corrected counters, one reported-not-guessed, each named with its OLD value
  - a worked instance of the citation-drift hazard, found inside this phase's own ruling
affects: [21-06, 21-07]

tech-stack:
  added: []
  patterns:
    - "A counter is corrected only when the prose beside it says what it counts and the parse can settle it; otherwise it is reported, with the ruling that would close it named"
    - "Re-resolve every cited line by grep at execution time — a line number written in a plan is stale by the time the plan runs"
    - "A dated log entry is corrected by appending, never by editing the entry that was true when written"

key-files:
  created:
    - .planning/phases/21-requirement-ledger-reconciliation-what-is-actually-discharge/21-FINDINGS.md
    - .planning/phases/21-requirement-ledger-reconciliation-what-is-actually-discharge/21-05-SUMMARY.md
  modified:
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
    - .planning/STATE.md
    - docs/surface/examples/RETIREMENT-COUPLINGS.md

key-decisions:
  - "The ROADMAP's `All **42**` is REPORTED, not corrected: its sentence claims to be the table's row count while the paragraphs beneath enumerate a defined subset summing to exactly 42 — the parse cannot settle which, and D-19(a) forbids guessing"
  - "`.planning/REQUIREMENTS.md`'s `Coverage:` counter IS settled by the parse, because its own explanatory sentence says it counts the traceability table's rows — so it is corrected, 94/94 → 143/143"
  - "The ROADMAP goal line reads `54 not-`Complete`` rather than `54 `Pending``: two of the 54 were never spelled `Pending`, which is the miscount the phase exists to correct"
  - "The stale `52` in STATE.md's older log entries is left alone — they are dated records of what was believed, corrected by the new entry rather than by rewriting history"
  - "The `progress:` block stays untouched and wave 1's note handing it to `21-05` is corrected: `21-CONTEXT.md` deferred it explicitly and `D-19` names three counters, none of them this one"

patterns-established:
  - "When a plan's acceptance criterion names a fence the phase's own deliverables live inside, assert the fence the shipped module defines and record the difference"

requirements-completed: [RECON-04, RECON-07, RECON-10]

duration: 75min
completed: 2026-08-22
---

# Phase 21 Plan 05: The Work List, the Verification Debt, and the Counters — Summary

**Dave can now rule from one document: five `Not built` rows with what closing each would cost, four of them tangled into a single knot he alone can cut; 27 verification items he alone can discharge, quoted verbatim and proven untouched by a diff rather than by anyone's word; and three counters, two corrected from a parsed figure and one reported rather than guessed — the third because a phase about honest counters does not get to invent the number it cannot measure.**

## Performance

- **Duration:** ~75 min
- **Tasks:** 2 of 2
- **Commits:** 2 task commits + this one
- **Tests added:** 0 — deliberately (`D-05`). `gate-tools` is 406 + 189, unmoved from waves 2, 3 and 4.

## Task Commits

1. **Task 1: `21-FINDINGS.md`** — `eedeefb` (docs)
2. **Task 2: the counter corrections + the regenerated inventory** — `587ff78` (docs)
3. **This SUMMARY, the position files, and the regenerated inventory** — final commit (docs)

## What the audit found, in one table

Produced by the strict parse at execution time, not carried from any wave's SUMMARY.

| Verdict | Rows |
|---|---|
| `Complete` | 38 |
| `Complete as ruled` | 2 |
| `Partial` | 9 |
| `Not built` | 5 |
| `Orphaned` | **0** |
| **Total** | **54** |

**Two-thirds of the ledger's outstanding debt was work that had already shipped and was never ticked.** The traceability table holds **143** rows at writing time — a reported measurement, carried by no check (`D-21`) — of which the ten `RECON-` rows are this phase's own and outside the 54.

## The three counters — corrected, or reported and why

### 1. `.planning/REQUIREMENTS.md` — the `Coverage:` line — **CORRECTED**

| | |
|---|---|
| **OLD** | `Coverage: 94/94 v0.2 requirements mapped, each to exactly one phase.` |
| **NEW** | `Coverage: 143/143 v0.2 requirements mapped, each to exactly one phase.` |
| **Line in `D-19` / this plan** | `423` |
| **Line when re-resolved at execution** | **`461`** |
| **Why the parse settles it** | the counter's own explanatory sentence says *"Counted from the traceability table above by counting its rows"*. The table has 143 rows. The prose names the predicate, and the parse answers it. |

The running-total sentence beneath it was stale by the same four rounds of minting. **OLD:** *"56 rows before Phase 16's minting, 68 after, 82 after Phase 15.5's, 94 after Phase 15.6's."* **NEW:** the same four totals, extended by `101` after Phase 16's post-stop plans minted `DOCS-19`..`DOCS-25`, `123` after Phase 17's and Phase 18's `CLNT-01`..`CLNT-22`, `133` after Phase 20's `CLNT-23`..`CLNT-32`, and `143` once Phase 21 minted `RECON-01`..`RECON-10`.

Every total was re-derived family by family from the parse rather than carried, and one of them is a free check on the others: **133 independently matches the row count at the pinned base `c51406b`**, measured by parsing `git show <base>:.planning/REQUIREMENTS.md`.

### 2. `.planning/ROADMAP.md` §Coverage — `All **42**` — **REPORTED, NOT CORRECTED**

| | |
|---|---|
| **Value** | `All **42** v0.2 requirements mapped` — **unchanged** |
| **Line in `D-19`** | `1946` |
| **Line the plan predicted** | `1959` |
| **Line when re-resolved at execution** | **`1959`** |

**The sentence describes itself two incompatible ways and the parse cannot settle which one it means.**

- The first clause claims to be *"the figure `.planning/REQUIREMENTS.md`'s traceability table carries, counted from it rather than remembered."* The table holds 143 rows today and held 56 even before Phase 16's minting. It was never 42.
- The two paragraphs immediately beneath enumerate the figure as **21 + 21** — the 21 defined at milestone definition plus the 21 minted by inserted phases through Phase 15.1 — and the next line says outright that *"Phase 16 mints its own (DOCS-07..NN) at planning and is **not yet counted above**."* Those lists are internally consistent and sum to exactly 42.

So 42 is a **defined subset counted correctly, sitting under a sentence that mis-states its own provenance.** Replacing 42 with 143 would leave the number contradicting the breakdown one line below it; replacing the breakdown means ruling whether the ~101 rows minted since Phase 15.1 belong inside a count of *"v0.2 requirements"* — a milestone-scope question, not a parse result.

`D-19` constraint (a) governs exactly this: **a counter the strict parse cannot settle is reported, not guessed.** A marker was added at the site saying so, naming the ruling that closes it — *is "v0.2 requirements" the whole traceability table, or the milestone-definition set plus what inserted phases minted through 15.1?* — and pointing at `21-FINDINGS.md` §4. The marker is the only edit made in that section; the 42 and both halves are byte-identical.

### 3. `.planning/ROADMAP.md` — the Phase 21 entry's `52` — **CORRECTED, at three sites plus a lane list**

| Site | OLD | NEW |
|---|---|---|
| `:47` (commissioning bullet) | `each of the 52 gets a verdict` | `each of the 54 gets a verdict` |
| `:47` (the same bullet's lane list) | six lanes summing to **52** — `21 against Phase 17, 18 against Phase 16, 6 against Phase 14, 3 against Phase 9, 3 against Phase 13, 1 against Phase 18` | eight lanes summing to **54**, adding `1 against Phase 15.5, 1 against Phase 15.6` |
| `:1888` (goal line) | ``give every one of the 52 `Pending` requirement rows`` | ``give every one of the 54 not-`Complete` requirement rows`` |
| `:1890` (rationale) | `the ledger reads 52 outstanding` | `the ledger reads 54 outstanding` |

All three line numbers re-resolved to **exactly where the plan said** — `47`, `1888`, `1890` — which is worth recording alongside the one that moved 38 lines, because it shows the drift is not uniform and cannot be predicted.

**One wording change beyond a digit swap, and it is deliberate.** The goal line read *"52 `Pending` requirement rows"*. Writing *"54 `Pending`"* would have been false: **two of the 54 were never spelled `Pending`** — `CPS-03` was `**Pending**` in bold and `DCD-02` was `**Partial**`, which is precisely why `grep -c "| Pending |"` returned 52. Correcting the digit while keeping the word would have preserved the miscount's cause inside the sentence that corrects its effect. It now reads `not-`Complete``, the phrase criterion 1 and the commissioning bullet already use.

## The citation-drift hazard, demonstrated on the phase that exists to name it

`D-19` cites the `Coverage:` counter at `.planning/REQUIREMENTS.md:423`. **It is at `461` today — 38 lines of drift, accumulated across this phase's own four waves of edits to the file the ruling points into.**

The plan anticipated the ROADMAP half of this and instructed that the §Coverage counter be located by `grep` at execution time rather than by any number written in the plan or in `D-19`. It did not anticipate that the *other* counter, cited by line in the same ruling, would drift further. Both were re-resolved by `grep`; neither line number written anywhere was trusted.

**The general form, which is this phase's subject arriving inside the phase's own governing ruling:** a line citation is a snapshot of a tree, and a ruling that carries one is stale the moment the file grows above it. `D-19` itself flagged the ROADMAP citation as *"the citation-drift hazard this phase exists to name"* — and then carried a second one that was already staler.

## The 24-vs-27 `human_needed` delta, and its cause

`gsd-sdk query audit-uat` reports **24 items across 9 files**. The files carry **27 across 11 records**.

**The cause is a filter.** The query filters on each record's frontmatter `status:`, so it drops two records that hold undischarged `human_verification:` blocks under a different status:

- **Phase 12** — `status: passed`, 1 item, whose own prose one screen below reads *"**Status:** human_needed (all automated checks passed; one subjective legibility check remains)"*.
- **Phase 18** — `status: gaps_found`, 2 items, the `human_verification:` key at line 74.

**This is the phase's own subject a third time, in a third tool.** `grep -c "| Pending |"` said 52 where a strict parse says 54. `grep -vc "| Complete |"` says 56, because a string inequality is not a membership test. Now a query that appears to report all of something reports only the subset its filter admits. Criterion 11 was amended from *"the 24 `human_needed` verification items across 9 phases (11, 13, 14, 15.1–15.4, 18.1, 19)"* to *"all 27 across 11 phase records"* on Dave's ruling (`D-20`).

**The roster was re-derived, never taken from the query.** Globbing `.planning/phases/*/[0-9]*-VERIFICATION.md` matches **16** files; **11** carry a `human_verification:` block. Item counts, parsed from the YAML rather than counted by eye: 11→1, 12→1, 13→1, 14→2, 15.1→2, 15.2→2, 15.3→5, 15.4→5, 18→2, 18.1→3, 19→3. **Sum: 27.** The derivation matches `UAT_RECORDS` path for path and matches `21-RESEARCH.md` §7's corrected table with nothing to report.

**Phase 15.1's two items were read from the source, not from the query.** `audit-uat --raw` returns the literal string `">-"` for their `name`, `expected` and `why_human` — a folded-scalar artefact in the query, not in the record. Parsed from the file, both items are intact and are quoted verbatim in `21-FINDINGS.md` §3.

**`audit-uat`'s filter is named, not fixed**, on `D-07`'s reasoning: tooling repair inside an audit phase surfaces defects elsewhere that then need their own fixes, and the phase stops being an audit.

**The untouched claim is mechanical.** `tools/docs_tests/test_requirement_ledger.py::test_the_human_needed_verification_records_are_untouched` diffs all eleven paths against the pinned base and requires empty — widened from nine under `D-20` consequence (c). It ran green here, and `CONTROL A` — the standing test proving that assertion is not vacuous — ran green alongside it.

## No GSD state or roadmap writer was invoked at any point in this plan

Stated explicitly because it is a required output of this plan and because five distinct such handlers have corrupted the file they wrote in this repository (`D-15`, `D-IMPL-154`, `D-IMPL-155`).

- **Zero** invocations of `gsd-sdk query state.*` or `gsd-sdk query roadmap.*` **writers**. The only `gsd-sdk` call in this plan's entire shell history is `gsd-sdk query roadmap.get-phase 21 --raw`, a **read**, run twice to re-parse the criteria after the ROADMAP hand-edits.
- `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md` and `.planning/STATE.md` were each copied to a backup **outside the tree** before the first edit, edited with the Edit tool only, and `git diff` inspected after each edit.
- Every diff showed the intended replacement and nothing else. No edit was reverted, because none produced an unintended line.
- `.planning/STATE.md`'s frontmatter was re-parsed with `yaml.safe_load` after the edits: **all eight top-level keys present**, `progress:` byte-identical, and `last_updated` the only top-level key changed.

## The success-criteria integrity check, run AFTER the hand-edit

`gsd-sdk query roadmap.get-phase 21 --raw` re-parsed to exactly **14** criteria, one per unwrapped line, **after** both ROADMAP hand-edit passes — not before. This project has shipped two phases gated against a single parsed truth because a wrapped criterion became one line, so the assertion is worthless taken before the edit.

`git diff -- .planning/ROADMAP.md` touches **no line beginning with two spaces and a criterion number**, checked mechanically with `grep -E "^[+-]  [0-9]+\. "` over the diff.

## Deviations from Plan

### 1. [Rule 3 — an acceptance criterion names a fence the phase's own deliverable lives inside]

- **Found during:** Task 1 verification.
- **Issue:** Task 1's last acceptance criterion asserts `git diff --stat <base>..HEAD -- src/ runtime/ examples/ public/ tests/ tools/ pyproject.toml` prints nothing. It **cannot** print nothing: `tools/docs_tests/test_requirement_ledger.py` is the standing-check module plan `21-01` landed, it is criteria 4 and 5's own deliverable, and it is 1267 insertions inside `tools/`.
- **Fix:** Asserted the fence the shipped module actually defines — `FENCE = ('src/', 'runtime/', 'examples/', 'public/', 'pyproject.toml')` plus `tests/`, which the module asserts separately — and asserted `tools/` narrowly: `git diff --name-only <base>..HEAD -- tools/` returns **exactly one path**, that module, and `tools/lints/citations.py` is diff-empty (`D-07`). All four hold.
- **Why this is the honest reading rather than a weakening:** the criterion's purpose is that the audit changed no shipped mechanism. A test module that exists to police the audit is not shipped mechanism, and excluding it wholesale would have hidden any *other* `tools/` edit. Naming the one permitted path is stricter than the criterion as written could be.

### 2. [Rule 2] The ROADMAP's `All **42**` got a marker, not just a mention in the findings record

- **Found during:** Task 2(b).
- **Issue:** `D-19` and the plan both permit reporting the counter rather than correcting it, with the reason recorded in `21-FINDINGS.md` §4. But a reader of `.planning/ROADMAP.md` alone would still meet a sentence whose first clause is false, with nothing at the site to say the audit had examined it and found it unsettleable. That is the "leftover prose contradicting a verdict" defect class this phase has now hit three times (`CPS-03`'s third statement in wave 3, wave 3's own minting leftover in wave 4).
- **Fix:** A marker paragraph immediately beneath the sentence, stating that it was examined under `D-19` and reported rather than corrected, why the two halves of the sentence disagree, which clause to read as false, and the one ruling that would close it. **The `42` and both enumeration paragraphs are byte-identical**; the marker is additive.

### 3. The goal line's wording changed beyond the digit

- **Found during:** Task 2(b).
- **Issue:** `.planning/ROADMAP.md:1888` read *"every one of the 52 `Pending` requirement rows"*. The plan says to replace the `52` with `54`. Doing only that yields *"54 `Pending` rows"*, which is false — 53 of the 54 read `Pending` and one reads `**Partial**`, and a second was `**Pending**` in bold, which is the exact reason the naive grep said 52.
- **Fix:** ``54 not-`Complete` requirement rows``, matching criterion 1 and the commissioning bullet. Recorded because it is a wording change the plan did not authorise in so many words, made to avoid writing a new false statement in the act of correcting an old one.

### 4. STATE.md's stale `52`s were found and deliberately left alone

- **Found during:** the whole-file sweep for every count this plan touched (project note 6).
- **What was found:** `.planning/STATE.md` states `52` at lines 266, 309, 400, 416 and 433.
- **Disposition:** **Left alone, on purpose.** `last_activity` is a dated running log — each entry is a record of what was believed at its own moment, with `PRIOR CONTEXT FOLLOWS.` separating them — and the same discipline `docs/DECISIONS.md` follows applies: correct by appending, never by editing the entry that was true when written. Line 400 already carries `**THE COUNT IS 54, NOT 52**`. The correction lives in the new wave-5 entry at the top. Rewriting the history would have destroyed the record of *when* the miscount was believed, which is the phase's own evidence.

### 5. Wave 1's `stopped_at` note handed `21-05` a counter the phase had already deferred

- **Found during:** the STATE.md update.
- **Issue:** `21-01`'s `stopped_at` block reads *"Counter corrections belong to `21-05` and `RECON-10`, produced by the strict parse"* about the `progress:` block. `21-CONTEXT.md`'s deferred list **explicitly puts the `progress:` block out of scope** — *"it is a GSD tooling limitation, not a ledger row"* — and `D-19` names three counters, none of them this one.
- **Fix:** `progress:` left byte-identical, and the contradiction resolved in writing rather than silently: the new `stopped_at` says wave 1's note was wrong, names the deferral that governs, and says which three counters `D-19` actually means. Guessing the block is what `D-IMPL-174` forbids.

### 6. `docs/DECISIONS.md`'s `D-IMPL-174` still carries the pre-correction values, correctly

- **Found during:** the same sweep.
- **Disposition:** `docs/DECISIONS.md:506` quotes `94/94`, `All **42**` and `52` as the counters stood when the ruling was made. The log is append-only and exempt from the citation lint precisely because its citations are dated snapshots. **Not edited.**

### 7. Two `.md` files in `docs/` are untracked and were left alone

- **Found during:** every `git status` in this plan.
- **Disposition:** `docs/CCF_SDK_DE_REQUIREMENTS.md` and `docs/Context_Product_Specification_Standard_v0-3.md` were untracked before plan `21-02` and are untracked still. **Pre-existing, reported, not touched** — the same disposition as waves 2, 3 and 4.

## Why no sabotage control appears in this plan, and what stands in for one

`D-05` forbids writing a test here and this plan wrote none, so **there is no new checker to sabotage.** Saying "the guards passed" without saying that would leave a reader assuming a control was skipped.

What this plan's claims actually rest on, and where each was watched go red:

| Claim | Guard | Sabotaged in |
|---|---|---|
| the eleven `human_verification` records are untouched | `test_the_human_needed_verification_records_are_untouched` + `CONTROL A` (proves it is not vacuous) | wave 1 — `PINNED_FILES` re-aimed, RED |
| no counter edit disturbed the table | `test_the_two_status_channels_agree`, `channel_disagreements` | wave 1 — `CONTROL 6`, `CONTROL 7`, RED |
| the audit changed no shipped mechanism | `test_the_fabric_is_untouched`, `test_the_scope_fence_holds` | wave 1 — `CONTROL A`, RED |
| the citation lint is unmodified (`D-07`) | `test_the_citation_lint_is_not_modified` | wave 1 — RED, naming the path |

The one lesson this plan re-applied rather than re-proved: **a control run at the wrong moment reports the wrong thing.** `git diff <base>..HEAD` compares commits and is blind to the working tree, so every fence assertion in this plan was run *after* the relevant commit, never before.

## Verification

| Check | Result |
|---|---|
| `pytest tools/docs_tests/test_requirement_ledger.py -q` | **exit 0** — 35 passed |
| `pytest tools/docs_tests/test_requirement_ledger.py tools/docs_tests/test_retirement_sweep.py -q` | **exit 0** — 68 passed |
| `python -m tools.lints --citations` | **exit 0** |
| `make lint` | **exit 0** |
| `make typecheck` | **exit 0** — 211 source files |
| `make gate-tools` | **exit 0** — leg 1 **406**, leg 2 **189**; both unmoved, the mechanical proof no test was added |
| `make test` | **exit 0** — **4105 passed / 118 skipped**, 10m37s — identical to the wave-1, wave-2, wave-3 and wave-4 baselines |
| `refuse_unresolvable(ledger_text())` | **`[]`** |
| `channel_disagreements` / `vocabulary_offenders` / `doubled_verdicts` | **`[]`**, **`[]`**, **`[]`** |
| identical id set in both channels | **True**, across all **143** ids (measured, not carried — `D-21`) |
| `roadmap.get-phase 21 --raw` re-parsed AFTER the hand-edits | **14** criteria, one per unwrapped line |
| `git diff -- .planning/ROADMAP.md \| grep -E "^[+-]  [0-9]+\. "` | **no match** — no criterion line rewrapped |
| `21-FINDINGS.md` section headings | **5**, `## 1.` through `## 5.` |
| the verification-debt table | **11** rows summing to **27**; every path exists on disk |
| the eleven paths vs `derived_uat_records()` and `UAT_RECORDS` | **set-equal**, both ways |
| `grep -c "hello-ccf" 21-FINDINGS.md` | **1** |
| `grep -Ec "v1\b\|for now\|future enhancement\|placeholder\|will be wired later"` | **0** |
| `grep -c '">-"' 21-FINDINGS.md` | **0** |
| §1 contains `54`, `56`, `143` and `133` with the difference explained | **yes** |
| §3 contains `24` and `27`, names `status:`-filtering, cites `D-20` | **yes** |
| `grep -c "94/94" .planning/REQUIREMENTS.md` | **1** — the correction record's own quote of the OLD value, inside the amended sentence |
| `grep -c "each of the 52 gets a verdict" .planning/ROADMAP.md` | **0** |
| `grep -c "All \*\*42\*\* v0.2 requirements mapped" .planning/ROADMAP.md` | **1** — the carve-out is recorded, at the site and in `21-FINDINGS.md` §4 |
| `git diff --stat <base>..HEAD -- src/ runtime/ examples/ public/ tests/ pyproject.toml` | **empty**, every path |
| `git diff --stat <base>..HEAD -- tools/lints/citations.py` | **empty** |
| `git diff --name-only <base>..HEAD -- tools/` | only `tools/docs_tests/test_requirement_ledger.py` (plan `21-01`'s) |
| `git diff --diff-filter=D --name-only` per task commit | **no deletions** |
| STATE.md frontmatter after the hand-edit | **8 keys intact**, `progress:` byte-identical, only `last_updated` changed among top-level keys |
| `git status --porcelain` after the final commit | only the two pre-existing untracked `docs/` files |

`make ci-core` is `lint typecheck test gate-tools`. Each leg ran individually rather than as one command, because a full pipeline cannot complete inside this harness's foreground call budget and `make test` alone runs past ten minutes.

## What plans `21-06` and `21-07` inherit

- **The ten `RECON-` rows are the only `Pending` left anywhere in the ledger.** `21-06` writes their verdicts before the close panel. `RECON-04`, `RECON-07` and `RECON-10` are discharged in substance by this plan and await only their cells.
- **No row count is carried by any check.** 143 is a measurement taken at writing time. `21-06` measures it again rather than inheriting it (`D-21`).
- **One open ruling this plan surfaced and could not close:** is *"v0.2 requirements"* the whole traceability table, or the milestone-definition set plus what inserted phases minted through Phase 15.1? The ROADMAP's `All **42**` cannot be corrected until Dave answers it, and the marker at the site says so.
- **Four observations for the close package**, in `21-FINDINGS.md` §5: `DEMO-03`'s re-homing note pointing at a file that is not in the tree; the citation lint's two silent-drop holes, both open and named; the ten phases with no `D-GATE` entry, ruled and closed at `D-IMPL-171`; and a shipped docstring at `tools/docs_tests/test_resolver_seam_obligations.py:38-41` asserting a CI fact that `Makefile:138` contradicts.
- **`D-11` holds to the end of the phase.** Nothing on the work list is to be started by `21-06` or `21-07`.

## Threat Flags

None. This plan reads tracked repository files and writes markdown. No credential, no network call, no external input, no package installed — `T-21-SC` stays true by the `pyproject.toml` emptiness assertion inside `FENCE`.

Register coverage: `T-21-25` (a GSD writer corrupting `ROADMAP.md`) — closed by hand-edits with backups and diffs, and by the fact that no writer was invoked at all. `T-21-26` (an assumed replacement counter) — closed by reporting the one the parse could not settle. `T-21-27` (three counters silently changed) — closed by `21-FINDINGS.md` §4, which names each with its OLD value. `T-21-28` (a counter edit disturbing the table) — closed by the identical id set across both channels, measured after the edits. `T-21-28b` (a rewrapped criterion) — closed by re-parsing to 14 after the edit and by the diff carrying no criterion line. `T-21-29` (a stale generated inventory) — closed by regenerating last, twice, after each `.planning/` write. `T-21-30` (discharging a `human_needed` item) — closed by the eleven-path empty diff. `T-21-30b` (a roster from a filtered query) — closed by re-deriving from the records and stating the delta.

## Known Stubs

None.

## Self-Check: PASSED

Both files this plan created exist on disk. Both task commits `eedeefb` and
`587ff78` resolve in this repository. Re-verified after the last write: the
ledger module is 35 passed, the sweep and ledger modules together are 68 passed,
`--citations` is exit 0, `make lint`, `make typecheck` and `make gate-tools` are
each exit 0, and the pinned-base diff over `src/ runtime/ examples/ public/
tests/ pyproject.toml tools/lints/citations.py` is empty on every path.

Five claims in this document were measured rather than asserted, because all five
read plausibly and could have been wrong.

- **The 27-item roster and its per-record counts** were parsed from the eleven
  records' YAML, not read across from `21-RESEARCH.md` §7 and not taken from
  `audit-uat`. The parse and the research table agree, with nothing to report.
- **The `133` in the corrected running-total sentence** was taken by parsing
  `git show c51406b:.planning/REQUIREMENTS.md`, so it is an independent check on
  the family-by-family arithmetic rather than a restatement of it.
- **Both re-resolved line numbers** came from `grep -n` run at execution time.
  The 38-line drift on `.planning/REQUIREMENTS.md:423` → `:461` is the finding
  that resulted; had the plan's number been trusted, the edit would have landed
  in the wrong place or not at all.
- **The 14-criteria re-parse** was run after the ROADMAP hand-edits, not before,
  because a control taken at the wrong moment reports the wrong thing.
- **`.planning/STATE.md`'s frontmatter** was re-parsed with `yaml.safe_load`
  after both edits and compared key by key, because this repository's tracking
  files have been corrupted by writers that reported success.
