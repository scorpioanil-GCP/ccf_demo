---
phase: 21-requirement-ledger-reconciliation-what-is-actually-discharge
plan: 07
subsystem: testing
tags: [close-review, cross-ai-panel, sabotage-controls, ledger, gate, hitl]
status: complete

requires:
  - phase: 21-requirement-ledger-reconciliation-what-is-actually-discharge
    provides: the 54 + 10 verdicted rows, the standing check module, `21-FINDINGS.md` and `21-DOCS-16-SPLIT.md` — all written BEFORE this plan, so the ledger Dave approves is the ledger the panel read
provides:
  - the close-time cross-AI panel record against the SHIPPED artifacts, with per-reviewer outcome and three findings recorded AS REJECTED
  - the additive single-agent code review, which found two advisories the panel did not and performed every empirical verification
  - three blocking findings fixed in-phase, each with a standing control watched go red against the shipped function
  - `tracked_under` + `CONTROL 16` — a pathspec that names nothing is refused, so five emptiness assertions stop being one typo away from vacuous
  - `uncited_verdicts` + `CONTROL 17`/`17b` — a verdict resting on no citation is refused by name, which is the predicate that found `DCD-02` made standing
  - the `DOCS-06`/`DOCS-08` unguarded-`ci`-composition gap recorded in the document Dave rules from
affects: [22]

tech-stack:
  added: []
  patterns:
    - "A control must diff the CONSTANT the assertion it vouches for uses; a control aimed at a different constant proves the helper works and nothing about the claim"
    - "A refusal that only fires on a citation that IS written enforces nothing about the row that writes none — check the presence, not just the shape"
    - "A close-panel sabotage is run against the module AS IT SHIPPED as well as against the fix, so the record shows what the fix adds rather than only that it holds"
    - "A finding is verified against the tree before it is recorded OR acted on, and the rejected ones are recorded as rejected with the refuting evidence"
    - "Inline the source for the panel; a reviewer whose sandbox fails silently reviews nothing and still exits 0"

key-files:
  created:
    - .planning/phases/21-requirement-ledger-reconciliation-what-is-actually-discharge/21-CLOSE-REVIEWS.md
    - .planning/phases/21-requirement-ledger-reconciliation-what-is-actually-discharge/21-07-SUMMARY.md
  modified:
    - tools/docs_tests/test_requirement_ledger.py
    - .planning/phases/21-requirement-ledger-reconciliation-what-is-actually-discharge/21-FINDINGS.md
    - .planning/STATE.md
    - docs/surface/examples/RETIREMENT-COUPLINGS.md

key-decisions:
  - "The panel reviewed the SHIPPED artifacts with the source INLINED, not the plans and not paths — codex on this host returns exit 0 having reviewed nothing when its sandbox fails, and inlining is what made its findings checkable"
  - "Two reviewers found the same two holes independently, and both are this project's defect class — a check that passes for a reason unrelated to what it claims — inside this phase's own machinery"
  - "The per-row citation gate is ROSTER-SCOPED, because 79 rows outside the 54 carry the same pre-existing debt under `D-19`'s carve-out and a ledger-wide form would be red on landing for rows `D-11` forbids touching"
  - "Three findings were REJECTED with measured evidence rather than acted on; an unverified finding acted on is worse than no review"
  - "No `D-GATE-21`, no ROADMAP flip, no merge and no `RECON-09` amendment — those are the gate, and `T-21-41` is closing on a green review instead of Dave's ruling"

patterns-established:
  - "A phase's close panel is briefed on what is already known and pointed at what is ADJACENT to each, and the budget it saves is spent on the machinery rather than on re-deriving the findings"

requirements-completed: [RECON-09]

duration: 195min
completed: 2026-08-22
---

# Phase 21 Plan 07: The §3.1 Close Panel, the Single-Agent Review, and the Gate — Summary

**Three reviewers read the shipped check module and all 143 verdicted rows with the source inlined, and two of them walked independently into the same two holes — a pathspec that could be misspelled into vacuity while its own control watched a different constant, and a verdict resting on no citation at all, which is exactly how `DCD-02` survived five waves. Both are fixed with standing controls watched go red against the shipped function; a third blocking finding is a gap named in a wave hand-off that never reached the document Dave rules from; three further findings were rejected with measured evidence, and the phase now stops, because `D-GATE-21` is Dave's and nothing here creates it.**

## Status: CLOSED

**Dave approved on 2026-08-22 and `D-GATE-21` is logged.** Task 1 (the panel, the review, the three fixes) landed at `4755d10`; task 2 (the gate) is recorded below. `RECON-09` was amended `Partial` → `Complete` **only after the entry existed**, which is the whole point of the row.

## Performance

- **Duration:** ~150 min
- **Tasks:** 1 of 2 (task 2 is the human gate)
- **Commits:** 1 task commit `4755d10` + this one
- **Tests added:** 6 — all in `tools/docs_tests/`, none under `tests/`. The ledger module went 45 → **51**; `gate-tools` leg 2 went 199 → **205**.

## The reviewer roster, and what each actually did

| Reviewer | Outcome |
|---|---|
| **gemini** | **Reviewed.** Cited real line numbers throughout. Two findings offered as blocking — **both rejected on verification**. Two advisories, one confirmed. |
| **codex** | **Reviewed, genuinely.** Every symbol and line it cited resolves. It emitted the bubblewrap warning this host always emits, but the source was inlined rather than referenced by path, so a silent sandbox failure could not empty its subject. Four blocking offered: two confirmed, one confirmed as advisory, one rejected. |
| **cursor** | **Reviewed** — the most thorough. Built an assertion-to-non-vacuity-anchor table covering every shipped gate. Declared "blocking: none", but two of its advisories are blocking under this phase's own bar and are promoted with its finding credited. |
| **claude** | **Not invoked** — the executing model, per §3.1 independence. The additive single-agent review is separate and is not a substitute. |

**182 KB inlined:** the whole check module with line numbers, all 143 traceability rows with their real file line numbers, and the whole of `21-FINDINGS.md`. The panel was briefed on the phase's five known defects and told **not to re-derive them**, and pointed at the defect class instead.

## Findings by disposition

| Disposition | Count | Ids |
|---|---|---|
| **Blocking, fixed in-phase** | **3** | `B-1`, `B-2`, `B-3` |
| **Rejected, recorded as rejected** | **3** | `R-1`, `R-2`, `R-3` |
| **Advisory, carried** | **7** | `A-1`..`A-8` (`A-6` is the substance of `B-3`) |

Two of the three blocking findings were reached **independently by two reviewers**. Two of the eight advisories (`A-7`, `A-8`) came from the single-agent review alone — neither is derivable from reading, both required running code or diffing against the pinned base.

## The three blocking findings

### B-1 — a misspelled pathspec and a clean tree are the same string

Five assertions say a tree is untouched by requiring `git diff --stat <base>..HEAD -- <spec>` to be `""`: `FABRIC` (criterion 12), `FENCE` (`D-11`), `UAT_RECORDS` (`D-13`/`D-20`), `PINNED_FILES` (`D-07`), `TESTS_TREE` (criterion 6, `D-05`). `fabric_diff` refused three ways an empty string lies and **not the fourth**: a pathspec matching nothing. `git` exits **zero** on `scr/`, on `tests-does-not-exist/`, on `tools/lints/citation.py`.

`CONTROL A` and `CONTROL 13` could not see it, because **both call `fabric_diff(base, CHANGED_TREE)`** and neither ever passes the constant the assertion it vouches for uses. `CONTROL 13` is named *`a_changed_tests_tree_would_be_detected`* and never mentions `tests/`.

**Measured both ways** — `TESTS_TREE` → `("tests-typo/",)`:

| module | result |
|---|---|
| as it shipped at wave 6 (`773775a`) | **45 passed, all green** — criterion 6's mechanical limb tests nothing and its control agrees |
| with the fix | **2 failed** — the new pathspec assertion *and* `test_no_test_was_written_to_manufacture_a_citation` itself |

**Fixed** by `tracked_under` (`git ls-files -- <spec>`) as a fourth refusal inside `fabric_diff`, plus `test_every_asserted_pathspec_names_a_tracked_subject` over all six constants resolved at call time, **`CONTROL 16`** on four *near-miss* spellings (each first shown to be the silent kind under raw `git diff`), and a positive twin requiring `fabric_diff(base, FABRIC)` to still return `""` — the guard must admit the empty result a clean tree gives while refusing the identical one a typo gives.

### B-2 — a verdict resting on no citation at all passed every gate

`RECON-02` reads `Complete` for criterion 3 — *every verdict other than `Not built` and `Orphaned` cites its evidence in the status cell*. The four tests it cites enforce a **different proposition**: given a citation, does it resolve, plus one **global** floor that some citation exists somewhere in the table.

Doctoring `HARD-02` to `**Complete** — asserted without evidence` and leaving every other row intact:

| checker | result |
|---|---|
| `refuse_unresolvable` | `[]` |
| `vocabulary_offenders` | `[]` |
| `unverdicted(working_set(...))` | `[]` |
| `channel_disagreements` | `[]` |

**That is how `DCD-02` survived five waves.** Wave 6 found it only by running criterion 3's predicate by hand across the roster, and its own SUMMARY says reading would not have found it. A predicate that has to be run by hand will not be run again.

**Fixed** by `uncited_verdicts` and `test_every_verdicted_roster_row_cites_its_evidence`, with **`CONTROL 17`** (green-before/red-after on `HARD-02`, doctored to a *fluent* cell because that is the shape a reader skims past) and **`CONTROL 17b`**, the discriminator: the **same** doctored cell must **pass** as `**Not built**` and **fail** as `**Complete**`, so `D-10`'s named-absence carve-out survives and the rule is not red-on-everything.

**Roster-scoped, deliberately.** Measured: **79 rows outside the 54** carry a Complete-family verdict and no citation — `CPS-`, `DCD-03`+, and `CLNT-23`..`32` — all ruled on in earlier phases, all under `D-19`'s carve-out, all forbidden to this phase by `D-11`. A ledger-wide form would be red on landing and narrowed on its first run, leaving the one place it can honestly hold enforced by nothing. That debt is carried as advisory `A-5` rather than smoothed over.

**Green on landing, retrofitting nothing:** all 64 rows this phase verdicted already cite.

### B-3 — a gap named in a hand-off never reached the document Dave rules from

Plan `21-03` recorded *"TWO NAMED GAPS FOR `21-05`"*. The second (`DOCS-03`'s six uncovered artifact classes) reached `21-FINDINGS.md` §2. The first — `DOCS-06`/`DOCS-08`'s **unguarded `ci`-composition limb**, with a third instance in `CLNT-16` — reached the ledger cells and one SUMMARY and nowhere else. `grep` over `21-FINDINGS.md` returns nothing; it is not in `deferred-items.md` either.

That is `D-IMPL-170`'s prohibition — *a finding that lives only in a SUMMARY is not recorded* — and it is this phase's own subject one level up. **The verdicts are right and were not changed:** `ci` genuinely is `ci-core examples docs-strict gate-tools` and `gate-tools` genuinely runs both suites. What is missing is the guard, and closing it means a test that reads the `Makefile`, which is **building** (`D-11`).

**Fixed** by `21-FINDINGS.md` §5 observation 5. **Recorded, not closed.**

## The three rejected findings

| Id | Claim | Why rejected |
|---|---|---|
| **R-1** (codex) | *"the module never verifies a cited Python symbol; `client.py::DefinitelyMissingSymbol` passes"* | **Measured false at the repo level.** `.planning/REQUIREMENTS.md` is in the lint's `GATED_TREES` with `exemption_reason` `None`; `check_source` returns `cite03-node-id ... defines no 'DefinitelyMissingSymbol'`, and `[]` on the good symbol. `make lint` runs `--citations` and is exit 0. The module's opening docstring states the division of labour; codex read one half and inferred the other was absent. |
| **R-2** (gemini) | *"`fabric_diff` is blind to the working tree — the phase's primary defect class"* | **True, documented in the function itself, known since wave 1**, and not a defect: the assertions are about what the phase COMMITTED, every wave asserted `git status --porcelain` empty, and CI runs on a clean checkout. |
| **R-3** (gemini) | *"the completeness gate is blind to rows minted `Pending` after the rosters froze"* | **Mechanism reproduces; disposition wrong.** `VERDICT_VOCABULARY` admits `Pending` deliberately and says why: a future phase mints `Pending` at planning time. A gate refusing it would be red the moment the next phase is planned. Its reproduction command is also wrong — `make test` has `testpaths = ["tests"]` and never runs this module. The adjacent observation is carried as `A-1`. |

## Every mutation run at close

All against the **shipped** function, each restored byte-identical from a backup taken first, each run **after** the relevant edit was on disk.

| # | Mutation | Result |
|---|---|---|
| 1 | `if not tracked_under(paths):` → `if False:` | **RED** — `CONTROL 16`, alone |
| 2 | `TESTS_TREE` → `("tests-typo/",)` against the **wave-6** module | **GREEN, 45 passed** — the defect demonstrated |
| 3 | the same, against the **fixed** module | **RED** — the pathspec assertion *and* criterion 6's own |
| 4 | `uncited_verdicts` → `return []` | **RED** — `CONTROL 17` and `CONTROL 17b` |
| 5 | the `CITATION_EXEMPT_VERDICTS` skip removed | **RED** — `CONTROL 17b` and the shipped assertion |
| 6 | an evidence-free `**Complete**` against the **wave-6** checkers | **GREEN on all five** — the defect demonstrated |

## The ledger Dave approves is the ledger the panel read

`git diff 773775a..HEAD -- .planning/REQUIREMENTS.md` prints **nothing**, and so does the working-tree diff. **This plan added no row and changed no verdict.** 143 rows in the traceability table; the 54 and the phase's own ten all verdicted; zero `Pending` anywhere. Re-parsed with the shipped module at close time and agreeing with `21-FINDINGS.md` §1 exactly:

| Verdict | The 54 | The ten |
|---|---|---|
| `Complete` | 38 | 8 |
| `Complete as ruled` | 2 | 0 |
| `Partial` | 9 | 2 |
| `Not built` | 5 | 0 |
| `Orphaned` | **0** | 0 |

## `make ci` — every leg run separately and read in full

| Leg | Result |
|---|---|
| `make lint` | **exit 0** — 0 findings |
| `make typecheck` | **exit 0** — 211 source files |
| `make test` | **exit 0** — **4105 passed / 118 skipped**, 556.67s |
| `make gate-tools` | **exit 0** — leg 1 **406**, leg 2 **205** (was 199) |
| `make examples` | **exit 0** — three harness legs, one content address |
| `make docs-strict` | **exit 0** — mkdocs build + `publish_scan.py site` |

`make test` at **4105/118** is byte-for-byte the wave-1-through-6 baseline, which is the mechanical proof `D-05` held: the six tests added are all under `tools/docs_tests/`.

## Scope fence, re-asserted at the end of task 1

| Path set | committed diff vs pinned base | working tree |
|---|---|---|
| `src/ runtime/ examples/ public/ pyproject.toml` | empty | empty |
| `tests/` | empty | empty |
| `tools/lints/citations.py` | empty | empty |
| the eleven `*-VERIFICATION.md` records | empty | empty |

## Deviations from Plan

### 1. [Rule 2] The panel prompt was built by hand rather than by `/gsd-review`'s default flow

`$HOME/.claude/get-shit-done/workflows/review.md` gathers `*-PLAN.md`, `*-CONTEXT.md` and `*-RESEARCH.md` and asks for a **plan** review. `CLAUDE.md` §3.1 requires the close-time panel to read the **shipped code**, and the plan's own action text says so twice. The three reviewer invocations, their credentials and their model selection follow the workflow exactly; only the prompt payload differs, and it differs in the direction §3.1 mandates. Written to `21-CLOSE-REVIEWS.md` so the pre-execution plan reviews survive in their own files.

### 2. `21-DOCS-16-SPLIT.md` was reviewed by the single agent, not by the panel

It is named in the plan's subject list. It was left out of the 182 KB payload so the panel's budget went to the check module and the verdicts, which is where the defect class lives. It was reviewed in the additive pass instead, and it verifies: 18 rows, its proposed verdict agrees with the ledger on **all eighteen**, and its factual claims spot-check green against the tree — `Makefile:172` is `ci: ci-core examples docs-strict gate-tools`; zero `examples/s3-*` directories and zero `example-s3` targets; `SECTION_ONE_GLOB = "s1-*"`; `PRODUCT_REQUEST_TOOL` present in `runtime/ccf_runtime/mcp/egress.py`; `tools/gates/` holds **no module**, only a stale `__pycache__`, exactly as the document says; all ten `DOCS-17`-condemned directories still present. Stated as a deviation rather than left implicit.

### 3. [Rule 2] `CONTROL 17b` was added beyond the two the plan implies

A per-row citation rule that also refused `Not built` rows would be refusing the ledger's honest shape — `D-10` requires a named absence precisely because there is no file to point at — and would have been relaxed within a day. The discriminator asserts both halves on the **same** doctored cell, differing only in the verdict word.

### 4. Two untracked `docs/` files were left alone

`docs/CCF_SDK_DE_REQUIREMENTS.md` and `docs/Context_Product_Specification_Standard_v0-3.md` were untracked before plan `21-02` and are untracked still. **Pre-existing, reported, not touched** — the same disposition as every wave of this phase.

## No GSD state or roadmap writer was invoked

**Zero** invocations of any `gsd-sdk query state.*` or `roadmap.*` **writer** (`D-15`, `D-IMPL-154`/`155`). The only `gsd-sdk` call in this plan is `roadmap.get-phase 21 --raw`, a **read**, run **after** the hand-edit.

- `.planning/STATE.md` and `.planning/ROADMAP.md` were both copied outside the tree before any edit.
- **`.planning/ROADMAP.md` is byte-identical to its backup — this plan did not edit it at all.** The Phase 21 progress row stays as it was; flipping it is the gate.
- `.planning/STATE.md`'s diff is **100 insertions, 1 deletion** — the deletion is `last_updated`. The frontmatter re-parses with `yaml.safe_load` to all **8** top-level keys, and the `progress:` block is byte-identical to the backup, verified by diffing the block.
- `gsd-sdk query roadmap.get-phase 21 --raw` re-parses to **14** criteria after the hand-edit, one per unwrapped line.
- One folded-scalar line in the first draft began `0. Ledger module …` and matched the criterion-line guard; reworded, and the guard is back to **0 matches**.

## Threat Flags

None. This plan reads tracked repository files, invokes three external review CLIs, and writes markdown plus one test module under `tools/docs_tests/`. No package installed; the `pyproject.toml` emptiness assertion inside `FENCE` holds (`T-21-SC`).

Register coverage. **`T-21-39`** (a reviewer returning exit 0 having reviewed nothing) — source inlined rather than referenced by path, and each reviewer's output was checked for symbols and line numbers that resolve before it was counted as a reviewer; all three passed that test, which is worth recording because codex on this host frequently does not. **`T-21-40`** (a fabricated finding entering the record) — every finding verified against the tree first, and **three were rejected with the refuting evidence recorded**. **`T-21-41`** (closing on a green review instead of Dave's ruling) — no `D-GATE-21`, no ROADMAP flip, no merge, no `RECON-09` amendment; the checkpoint returns instead. **`T-21-42`** (a blocking finding fixed without a standing control) — `CONTROL 16`, `CONTROL 17`, `CONTROL 17b` plus two positive twins, six mutations watched, two of them run against the wave-6 module to show what the fix adds. `B-3` is a record-only fix and names why an audit cannot close its subject. **`T-21-43`** (a close-time fix breaching the scope fence) — re-asserted at the end of task 1 over five path sets, committed and working-tree. **`T-21-44`** (reviewer credentials) — `CODEX_API_KEY`, `CURSOR_API_KEY` and `GOOGLE_API_KEY` sourced from `/home/parkave/homecams_v2/.env`, which is not in this repository; no key is written into any tracked file, verified by `--citations` and by inspection of the commit.

## Known Stubs

None.

## What is deliberately NOT done, and must not be done without Dave's ruling

- the `D-GATE-21` entry in `docs/DECISIONS.md`
- the ROADMAP Phase 21 progress row flip to Complete
- the `RECON-09` `Partial` → `Complete` amendment in both channels — **its outstanding limb is `D-GATE-21` itself**
- the merge of `phase-21` to `main`, with a merge commit referencing the gate
- a final regeneration of `docs/surface/examples/RETIREMENT-COUPLINGS.md` as the last write before that merge

§3.1 step 3: *the review is necessary and never sufficient. Approval authority is Dave's alone.*

## Self-Check: PASSED

`21-CLOSE-REVIEWS.md` and this file both exist on disk. Task commit `4755d10` resolves in this repository and deletes nothing (`git diff --diff-filter=D` over it is empty). Re-verified after the last write: the ledger module is **51 passed**, `gate-tools` is 406 + 205, `--citations` is exit 0, `mypy --strict` is clean, all six `make ci` legs are exit 0, the `D-21` hardcoded-count guard over the module returns **0**, `grep -c` for each of `test_control_16_`, `test_control_17_` and `test_control_17b_` returns **1** (no control renumbered or duplicated), `grep -c skipif` returns **0**, and the committed coupling report is current.

Five claims here were measured rather than asserted, because all five read plausibly and could have been wrong.

- **Each reviewer was checked for evidence it actually read the source** before being counted as a reviewer, rather than being trusted on exit code. This host has produced a clean exit-0 review of nothing.
- **The two headline defects were reproduced against the module as it shipped at wave 6**, not only against the fix, so the record shows the failure rather than only the remedy.
- **Three findings were refuted by running the tool the reviewer claimed was absent** — `check_source` for R-1 — rather than by argument.
- **The per-row citation gate was measured green over both rosters before it was written**, so it is not a standard retrofitted onto a phase that failed it, and the 79 out-of-scope rows were counted rather than estimated.
- **The ledger was diffed against wave 6's commit** to establish that the panel and the approver see the same document, which is the whole reason the ten `RECON-` rows were verdicted before this plan rather than inside its checkpoint.

---

# Task 2 — the gate

## Dave's ruling

Approval granted 2026-08-22. His summary of the result, verbatim:

> *"Phase 21 did what an audit phase is for: it made the ledger match the tree, found the checks that could not fail, fixed them in-phase, and refused to invent work or paper over gaps. Two-thirds of the 'outstanding' debt was already shipped and never ticked. That is a real result."*

Every item in the gate package was accepted: the 54-row audit, `B-1` and `B-2` as fixed in-phase, `B-3` as *"Recorded, not closed — correct under D-11"*, the three rejections as *"Correctly rejected with evidence"*, the seven advisories as *"Correctly carried"*, the scope fence as holding, and the test count as *"Good proof no citation-manufacturing tests were added"*.

## The three rulings, logged as new entries

| Entry | Ruling |
|---|---|
| **`D-IMPL-175`** | Phase 16's eighteen `DOCS-` rows take the split's proposed verdicts **as written** — ten `Complete`, five `Partial`, three `Not built`, zero wholly `Orphaned`. `DOCS-18` limb 1 *"**Stays closed.** Do not re-open."* |
| **`D-IMPL-176`** | All five `Not built` rows stay on the work list — *"Do not drop any in this gate."* Sequenced: `DOCS-15` first; replacements before removals; the `00`–`08` half of `D-27` still Dave's with the quarantine standing. **And the new ruling nobody had logged: `s3-` is NOT a required naming scheme** — *"Phase 16 is not resumable … the obligation is the content, not the old section label."* Published pages across `DOCS-12`/`13`/`14`/`15` are **one workstream, not four**. |
| **`D-IMPL-177`** | *"v0.2 requirements"* in the ROADMAP §Coverage sentence means the milestone-definition set plus what inserted phases minted through 15.1 — **the 42 the breakdown enumerates, not the 143-row table.** Number unchanged; descriptive clause corrected in one line; the wave-5 unsettleable marker removed. |

**`D-GATE-21`** follows them at `docs/DECISIONS.md:510`.

## What changed at the gate, and nothing else did

| File | Change |
|---|---|
| `docs/DECISIONS.md` | four entries **appended**, nothing edited — `D-IMPL-175`, `-176`, `-177`, `D-GATE-21` |
| `.planning/REQUIREMENTS.md` | **`RECON-09` only** — `Partial` → `Complete` in both channels, `[ ]` → `[x]`. `git diff` is 2 insertions / 2 deletions and the only ids in it are `RECON-09`'s two lines. **No row added.** |
| `.planning/ROADMAP.md` | exactly **three hunks** — the `21-07` plan checkbox, the Phase 21 progress row (`6/7` → `7/7 + close-fixes`, Complete, `2026-08-22 (D-GATE-21)`), and the §Coverage block |
| `.planning/phases/21-*/21-FINDINGS.md` | §2 gains Dave's sequencing, the `s3-` ruling and the one-workstream ruling, quoted verbatim |
| `.planning/STATE.md` | the gate recorded; `progress:` block byte-identical |
| `docs/surface/examples/RETIREMENT-COUPLINGS.md` | regenerated **last** |

## The amendment held to the gate it imposes

`RECON-09`'s new cell was written **after** `D-GATE-21` existed and was then put through every standing check the phase built:

| Check | Result |
|---|---|
| table rows | **143** — unchanged, no row added |
| `channel_disagreements` | `[]` |
| `vocabulary_offenders` | `[]` |
| `doubled_verdicts` | `[]` |
| `refuse_unresolvable` | `[]` |
| `uncited_verdicts` over both rosters | `[]` — **the gate this plan added, applied to this plan's own edit** |
| `unverdicted` over the 54 / over the ten | `[]` / `[]` |
| frozen working-set roster vs the strict parse at the pinned base | **identical id-for-id** |
| the phase's own ten | **9 `Complete`, 1 `Partial`** |

`RECON-10` stays `Partial` **deliberately**. `D-IMPL-177` settles the counter, but the row's verdict is taken against its own text — *the three counters are CORRECTED* — as that text stood while the phase ran, and at that time the third was correctly reported rather than guessed. Amending it here would be back-dating a verdict onto a ruling that did not exist when the work was done, which is the defect the phase exists over. Closing it is a future phase's business, and `D-IMPL-177` is what that phase would cite.

## `make ci` at the merge commit

| Leg | Result |
|---|---|
| `make lint` | **exit 0** — 0 findings |
| `make typecheck` | **exit 0** — 211 source files |
| `make test` | **exit 0** — **4105 passed / 118 skipped** |
| `make gate-tools` | **exit 0** — leg 1 **406**, leg 2 **205** |
| `make examples` | **exit 0** |
| `make docs-strict` | **exit 0** |

## Deviations from Plan — task 2

### 5. [Rule 1] A fabricated cross-reference was caught in my own gate entry before it was committed

The first draft of `D-GATE-21` read *"Per `D-IMPL-183`'s ancestor `D-21`"*. **`D-IMPL-183` does not exist** — the log ends at `D-IMPL-177` after this sitting. It was found by a check written for the purpose: every `D-IMPL-NN` and `D-GATE-NN` token in the four new entries was extracted and required to match an existing entry heading. Thirteen ids checked, one missing, corrected to plain `D-21` before the commit. **`docs/DECISIONS.md` is exempt from the citation lint** — it is an append-only log whose citations are snapshots — so nothing in the toolchain would have caught it. This is the third distinct instance in this phase of a reference that looks checkable and is not, and it is recorded because it happened *inside the entry that closes the phase about exactly this*.

### 6. The anchored citation into `docs/DECISIONS.md` was measured weak again, and said so in the row

`RECON-09` cites `D-GATE-21` at `docs/DECISIONS.md:510`. Before writing it, the citation was run through the lint's `check_source` at the correct line **and at a deliberately wrong one**. Both returned `[]` — because `D-IMPL-176` and `D-IMPL-177` sit on the neighbouring lines and **cross-cite `D-GATE-21` in their own `Related:` clauses**, so `_anchor_verdict` returns `True` there too. That is wave 4's finding reproducing on this plan's own citation. Rather than pretend the anchor is load-bearing, the row says so in its own cell and names the id as the thing that actually locates the entry in an append-only log. The row's criterion-3 obligation is discharged by its **symbol** citation, which the resolver does check.

### 7. The `progress:` block and the milestone `status:` were left alone

`21-CONTEXT.md` deferred the `progress:` block explicitly — it is a GSD tooling limitation (the plan counter cannot see that Phase 16 was retired rather than executed), `D-IMPL-174` names three counters and none is this one, and Dave's gate authorization does not reach it. Byte-identical to the pre-plan backup, verified by diffing the block.

## Self-Check: PASSED — re-run after the merge

`D-GATE-21` present in `docs/DECISIONS.md`; `D-IMPL-175`, `-176`, `-177` present; every `D-IMPL`/`D-GATE` id cited by the four new entries resolves to a real entry heading. `RECON-09` reads `**Complete**` in the traceability table and `- [x]` in the checkbox list. The ROADMAP Phase 21 progress row reads Complete with `2026-08-22 (D-GATE-21)`, and `roadmap.get-phase 21 --raw` still parses **14** criteria. `.planning/STATE.md` frontmatter re-parses to all eight keys. The coupling report is current. `main` contains the phase.
