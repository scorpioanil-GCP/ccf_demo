---
phase: 21-requirement-ledger-reconciliation-what-is-actually-discharge
plan: 04
subsystem: testing
tags: [ledger, audit, citations, phase-16, retirement, two-sided-split, sabotage-controls]

requires:
  - phase: 21-requirement-ledger-reconciliation-what-is-actually-discharge
    provides: the strict parser, `refuse_unresolvable`, the pinned diff base, the `path.py::symbol` citation form, and the `D-17` anchored-citation concession proven under sabotage
provides:
  - the D-12 two-sided split, `21-DOCS-16-SPLIT.md`, one section per row with evidence on both sides and seven ruling questions for Dave
  - 18 reconciled Phase 16 `DOCS-` rows in both ledger channels — all eighteen unflipped, undropped, and none retired or built
  - all 54 audited rows carrying a verdict; the only `Pending` left anywhere is this phase's own ten `RECON-` rows
  - the phase's only ORPHANED limb, named and closed rather than left as work
  - a measured finding that an anchored line citation into `docs/DECISIONS.md` is weaker than `21-03` proved it to be
affects: [21-05, 21-06, 21-07]

tech-stack:
  added: []
  patterns:
    - "Pick a sabotage target by running the shipped predicate and requiring `False`, never by assuming a neighbouring line differs — `docs/DECISIONS.md` entries cross-cite each other's ids"
    - "A row whose limbs land on different sides takes `Partial` and its cell says which limb went which way, including a limb that is orphaned"
    - "A `Not built` row may still cite the machinery that shipped, provided the cell says the machinery guards something that has not happened"

key-files:
  created:
    - .planning/phases/21-requirement-ledger-reconciliation-what-is-actually-discharge/21-DOCS-16-SPLIT.md
    - .planning/phases/21-requirement-ledger-reconciliation-what-is-actually-discharge/21-04-SUMMARY.md
  modified:
    - .planning/REQUIREMENTS.md
    - .planning/STATE.md
    - .planning/ROADMAP.md
    - docs/surface/examples/RETIREMENT-COUPLINGS.md

key-decisions:
  - "Side C is nearly empty and that is the finding, not a failure of the audit: `RETIRED.md` retires the APPROACH and not the NEED, so an obligation about a need survives the rejection of the approach that was to satisfy it"
  - "`DOCS-18` is `Partial` and not `Orphaned` — one of its three limbs is orphaned by `D-IMPL-96`, the other two have live referents, and the vocabulary admits one word per cell"
  - "`DOCS-17` is `Not built` and its absence is a RULING (`D-IMPL-145` limb 2) rather than neglect; the 111/15/102 figures were re-measured today rather than carried"
  - "`DOCS-13` is `Partial` because Phase 20 shipped the legs limb and nobody shipped the pages limb — a row can be discharged by a phase that never named it"

patterns-established:
  - "Before trusting a sabotage that reported green, ask whether the mutation was VISIBLE to the checker; a control aimed at a cross-citing neighbour proves nothing"

requirements-completed: [RECON-01, RECON-02, RECON-04, RECON-05]

duration: 115min
completed: 2026-08-22
---

# Phase 21 Plan 04: Phase 16's Eighteen `DOCS-` Rows — Summary

**All fifty-four rows now carry a verdict, and the lane everyone expected to be a graveyard turned out to be mostly discharged work that nobody wrote down: ten `Complete`, five `Partial`, three `Not built` and — the result worth stating plainly — ZERO wholly `Orphaned`, because `RETIRED.md` retires the approach and not the need, so what died with Phase 16 was one limb of one row, the no-fabric-change assertion Dave himself revoked at `D-IMPL-96`.**

## Performance

- **Duration:** ~115 min
- **Tasks:** 3 of 3
- **Commits:** 3 task commits + this one
- **Tests added:** 0 — deliberately. `make gate-tools` is 406 + 189, unmoved from waves 2 and 3.

## Task Commits

1. **Task 1: `21-DOCS-16-SPLIT.md`, the two-sided split** — `624ab9f` (docs)
2. **Task 2: `DOCS-07`..`DOCS-16` in both channels** — `6fb22fd` (feat)
3. **Task 3: `DOCS-17`..`21`, `DOCS-23`..`25`, and the regenerated coupling inventory** — `b00d529` (feat)
4. **This SUMMARY, the position files, and the regenerated inventory** — final commit (docs)

## The split totals

| Side | Rows | Which |
|---|---|---|
| **A — re-derived and satisfied** | **10** | `DOCS-07`, `-08`, `-09`, `-16`, `-19`, `-20`, `-21`, `-23`, `-24`, `-25` |
| **Split across sides** | **5** | `DOCS-10`, `-11`, `-12`, `-13`, `-18` |
| **B — still owed, referent exists** | **3** | `DOCS-14`, `-15`, `-17` |
| **C — orphaned** | **0 rows, 1 limb** | `DOCS-18` limb 1 |

Eighteen rows. `DOCS-22` was already `Complete` and is outside the 54.

## The eighteen verdicts

| Id | Verdict | Route | Load-bearing evidence |
|---|---|---|---|
| `DOCS-07` | Complete | 2 | `D-IMPL-94` anchored at `docs/DECISIONS.md:352`; a process row, and the cell says so |
| `DOCS-08` | Complete | 1 | `tools/publish_scan_tests/test_docstring_leaks.py::test_no_docstring_reproduces_whitepaper_body_text` — plus the `ci` composition stated in prose, because a `Makefile` cannot be cited |
| `DOCS-09` | Complete | 1 | `tests/examples/test_source_estate.py::test_the_generator_never_touches_the_context_graph`, and four siblings, one per limb |
| `DOCS-10` | **Partial** | 1 | `examples/s1-00-companies-over-revenue/deployment.py::connection` ships; the six-backend matrix does not exist |
| `DOCS-11` | **Partial** | 1 | `tests/examples/test_spine_separation.py::SECTION_ONE_GLOB` is `s1-*` — the gate covers two directories, and the row says *every* |
| `DOCS-12` | **Partial** | 1 | the examples ship and are gated; **no published page names a Section-1 example** |
| `DOCS-13` | **Partial** | 1 | `tests/examples/test_client_example_purity.py::REFUSED_IMPORTS` — three legs, `ccf` refused BY NAME; the pages limb is one paragraph |
| `DOCS-14` | **Not built** | 3 | no `examples/s3-` tree, no `example-s3-` target, no page |
| `DOCS-15` | **Not built** | 3 | the page does not exist in any form; both greps return zero |
| `DOCS-16` | Complete | 1 | `tools/docs_tests/test_advisory_discharge.py`, one named assertion and one refusal control per advisory |
| `DOCS-17` | **Not built** | 3 | all ten directories present; the absence is `D-IMPL-145` limb 2's quarantine |
| `DOCS-18` | **Partial** | 2 | limb 1 orphaned by `D-IMPL-96` at `docs/DECISIONS.md:356`; `tools/gates/` holds no module |
| `DOCS-19` | Complete | 1 | all four papercuts, each with its own gate; the `hasattr` twin is the one that matters |
| `DOCS-20` | Complete | 1 | `tests/crossproc/test_mcp_egress.py::test_the_tool_is_never_the_weaker_path` — a seven-scenario parity matrix |
| `DOCS-21` | Complete | 1 | both limbs of an *or*: gated **and** the residual pinned by a test named for the gap |
| `DOCS-23` | Complete | 1 | two unknown keys named **together in one refusal**, not one per round trip |
| `DOCS-24` | Complete | 1 | the R-1 family, whose load-bearing control is that the refusal does **not** over-reach |
| `DOCS-25` | Complete | 1 | pin-for-pin in manifest order, with a perturbation control proving it still discriminates |

**Route** is `D-17`'s: 1 = cite the guarding test, 2 = an anchored line citation into a ruling, 3 = a named absence with no citation obligation. **Sixteen of eighteen took route 1 or 3.** Route 2 was used twice, both times where the evidence genuinely IS a ruling.

## The finding this plan owes the phase: a sabotage that reported green

`21-03` established the discipline — write an anchored line citation only after `_anchor_verdict` returns `True`, then watch one go red under deliberate mutation. Both were done here, and **the second one failed to fail.**

`D-IMPL-94`'s citation was re-aimed from `docs/DECISIONS.md:352` to `:356`, on the reasoning that `:356` holds `D-IMPL-96` and is therefore a wrong target. `python -m tools.lints --citations` stayed at **exit 0**.

The cause, measured rather than guessed: **`D-IMPL-96` cross-cites `D-IMPL-94` in its own body** — *"withdraws the premise of `D-13` and `D-14` in `D-IMPL-94`"* — so the token the anchor looks for is literally present at `:356` and `_anchor_verdict` returns `True`. Run against the shipped function:

| Line | `_anchor_verdict('D-IMPL-94', …)` |
|---|---|
| `:352` (the entry itself) | `True` |
| `:354` | `False` |
| `:356` (`D-IMPL-96`, which cites it) | **`True`** |

Re-aimed at `:354`, `cite02-anchor` went **RED**, naming the rule, the anchor and the lines, in **both** channels (`.planning/REQUIREMENTS.md:317` and `:32`). Restored byte-identical from a backup taken first, lint back to exit 0.

**Why this matters beyond one control.** `docs/DECISIONS.md` is an append-only log whose entries routinely cite each other's ids — `D-IMPL-96` cites `D-IMPL-94`, `D-IMPL-145` cites `D-27`, `D-IMPL-152` cites seven abandoned plans. An anchored citation into it is therefore checked more weakly than it appears: the check asks whether the token appears in the cited lines, not whether those lines are the entry. `21-03`'s sabotage happened to land on a line that did not carry its token and correctly went red; **had it landed on a cross-citing neighbour it would have reported green, and the citation would have been recorded as checked when the mutation was simply invisible.**

The rule for later waves: **choose the sabotage target by running `_anchor_verdict` and requiring `False`.** Do not assume a neighbouring entry differs.

## The three `Not built` rows, with their closing costs, lifted for `21-05`

### `DOCS-14` — Section 3 and its pages

> Closing `DOCS-14` means re-deriving the host-embedding and agentic-skilling demonstration against the surface that exists now rather than lifting Phase 16's abandoned Section-3 plan: in-process consumption, MCP egress, A2A admission and an ArtifactStore swap in one coherent worked example, plus the published pages, plus the plain statement that SDK agents are governed identity and are structurally barred from calling a model. **It is coupled to `EXAM-02` and cannot be sequenced independently of it** — both name the same missing Section-3 home, and both are `Not built` rather than `Orphaned` for the same reason. It also needs a ruling on whether the replacement keeps the `s3-` naming at all, since the section scheme was Phase 16's and Phase 16 is not resumable. The substance is not missing: `examples/04-cross-process` demonstrates cross-process consumption and admission, `examples/07-artifact-store-mcp` the store swap, `examples/02-skilling` the skilling channel — **but all three are among the nine `DOCS-17` condemns**, so this is coupled to the retirement in the same knot `EXAM-02` and `CLNT-17` sit in.

### `DOCS-15` — the adoption-argument page

> Closing `DOCS-15` means writing one published page that names RAG over a vector store, hand-rolled context assembly, and a semantic layer plus prompt templates, states what each lacks against **cited shipped mechanism**, uses the UBO question as its worked demonstration, and carries the passage-anchor honesty caveat. The UBO demonstration already exists in the tree — `examples/s1-01-hello-context-product`'s source estate answers it, gated five ways — so the page has a subject to point at rather than one to invent. **It is the cheapest of the three side-B rows and the one with the highest adoption leverage**, and it is coupled to nothing except the `s1-01` tree's survival, which `CLNT-17` proposes ending.

### `DOCS-17` — retiring `examples/00`–`08` and `external/00-hello-context`

> Closing `DOCS-17` means retiring all ten directories together with every published page that sources from them re-cut in the same change — **111 references across 15 published pages, 102 of them snippet includes, re-measured 2026-08-22 and unmoved from `D-IMPL-145`'s ruling-time count** — plus the make targets, the CI `examples:` job, the floor constants those trees feed, and the seam-obligation gate whose only surviving `refuse_bound_payload` witness is `examples/04-cross-process/producer_child.py`. **This is blocked on Dave and not on an executor.** `D-IMPL-145` limb 2 quarantined the group deliberately, in his ruling, because deleting it leaves 15 published pages sourcing from nothing with no replacement written; and plan `17-08` returned the `00`–`08` half of `D-27` to him as an undecided blocking checkpoint. **Coupled to `CLNT-17`**, which is `Not built` on the other half of the same disposition, and to `DOCS-14` and `EXAM-02`, whose replacement suites would have to exist first.

**Nothing on this list was started here.** `D-11` and the ROADMAP's out-of-scope paragraph forbid an executor closing a gap the audit discovers, and the pinned-base fence over `src/ runtime/ examples/ public/ tests/ pyproject.toml` is empty — which is the mechanical proof. `ls examples/` still lists all nine of `00-quickstart` through `08-e2e-demo`.

## The five split rows: which limb went which way

Each is `Partial`, and each cell names both limbs, so `21-05` can lift the owed half without re-deriving it.

| Row | Limb that shipped | Limb that did not |
|---|---|---|
| `DOCS-10` | config-resolved backend, no substrate branch, no credential in the tree | the six-backend `content_hash` CI matrix — `backends.yaml` declares one profile and `example-s1-00` is in no job |
| `DOCS-11` | the marker mechanism, gated in both polarities | its scope: `s1-*` only, two directories out of thirteen |
| `DOCS-12` | agent-free deterministic Section-1 examples | the published pages — zero pages name `s1-00` or `s1-01` |
| `DOCS-13` | three harness legs, `ccf` refused by name, exactly-three asserted | the published pages — one paragraph, no Section-2 page |
| `DOCS-18` | the full gate sweep (`make ci`) | limb 1 is **orphaned**; limb 3 is what Phase 21 is doing |

**`DOCS-12`, `-13`, `-14` and `-15` are short by the same thing** — a documentation surface for the examples that actually shipped. That is one ruling question, not four, and the split document asks it as one.

## The one orphaned limb, and why nothing else joined it

`DOCS-18` limb 1 asks for *"a mechanical no-fabric-change assertion carrying `D-13`'s single enumerated exception."* `D-IMPL-96` revoked ROADMAP criterion 10 outright and, in its own words, *"with it the elaborate machinery built to work around it: `D-13`'s single enumerated exception for `ProductClassDeclaration`'s docstring, plan 16-19's `gate_16.py` allowlist… and `D-14`'s two-limb bound."* Dave's stated reason: the rule *"has been used out of context."* The absence is checkable — `tools/gates/` holds no module at all. Building it now would re-instate a rule that was revoked, which is the definition of side C.

**Nothing else in the lane qualifies, and the reason is structural rather than lucky.** `RETIRED.md` is explicit that retiring Phase 16 retires the APPROACH and not the NEED. Every other row in the lane states a *need* — pages, examples, a matrix, a retirement — and a need does not die because the plan that was to satisfy it did. Only `DOCS-18` limb 1 states a property of the approach's own governance machinery, and that is the only limb the retirement took with it. **A reader expecting a fat side-C pile is expecting the wrong thing**, and this SUMMARY says so rather than manufacturing rows to fill it.

## The rows the ledger never recorded

Eight rows had real, shipped work that no channel of the ledger reflected. Worth naming because the pattern is the one the phase was commissioned over.

- **`DOCS-19`, `-20`, `-21`, `-23`, `-24`, `-25`** shipped in **Phase 16's own post-stop plans** — `16-22` through `16-31`, the ten that ran after the phase's example surface was rejected. `RETIRED.md`'s *"executed 6 of 21"* is true of the ORIGINAL plan set as of 2026-08-17; the ROADMAP's `16/16` counts the later ten. **Both are right about different sets, and neither is a contradiction.**
- **`DOCS-13`** shipped in **Phase 20**, which never named the row. A requirement can be discharged by a phase that has never heard of it, which is exactly why "was the plan executed" is the wrong test.
- **`DOCS-16`** shipped in `16-06` and its `requirements-completed` frontmatter said so; the ledger row stayed `Pending` regardless.

## Deviations from Plan

### 1. [Rule 1 — a wave-3 leftover asserted the opposite of a shipped verdict]

- **Found during:** Task 2, grepping the whole ledger for the lane's ids per the plan's own trap warning.
- **Issue:** `.planning/REQUIREMENTS.md`'s minting-provenance prose read **"Second, `DOCS-01..DOCS-06` stay Pending against Phase 14, deliberately"**. Plan `21-03` verdicted all six — five `Complete`, one `Partial` — so the file asserted `Complete` in two channels and `Pending` in a third, two hundred lines apart. Nothing mechanical caught it, and nothing mechanical would: the prose is not parsed by `traceability_rows`.
- **Fix:** Amended to say what the sentence was actually load-bearing for — **the PHASE column stays at 14** — with the amendment visible in the sentence itself and the original wording quoted, so the record of the correction survives.
- **Worth recording:** this is the **second** occurrence of trap 7a in this phase. `21-03` hit it on `CPS-03`'s third statement and warned `21-04` about it; the warning fired on wave 3's own leftover.
- **Commit:** `6fb22fd`

### 2. [Rule 1 — the verdict-lead reader refused a comma]

- **Found during:** Task 2, first ledger-module run after the edit.
- **Issue:** `DOCS-14` and `DOCS-15` were written `**Not built**, and the absence is…`. `VERDICT_LEAD` cuts the leading verdict at `(`, an em dash or a hyphen — a **comma is not a cut character**, so the token parsed to `''` and `vocabulary_offenders` reported both rows as carrying a verdict outside the vocabulary.
- **Fix:** Both rewritten to `**Not built** — the absence is…`, matching `EXAM-02`'s shipped shape. The checkbox channel keeps the comma form, which is correct: that channel is parsed for `[x]` only.
- **Not a defect in the reader.** The reader is right to be strict; the cell was wrong.
- **Commit:** `6fb22fd`

### 3. [Rule 1 — the citation checker caught my own prose, and it was right to]

- **Found during:** Task 3, first `refuse_unresolvable` run after the edit.
- **Issue:** A `DOCS-20` clause explained that the tool-name constant *"has no `path.py::symbol` form of its own."* The literal token was extracted as a citation and refused as a **BARE BASENAME** — `D-06` requires a full repo-relative path.
- **Fix:** Rephrased to *"the re-export binds no symbol there, so it has no citable definition site of its own."* **Rephrased rather than exempted:** naming a citation FORM is not naming a file, the checker cannot tell the difference, and that is the right way round — the alternative is an escape hatch that would admit a real bare basename tomorrow.
- **Commit:** `b00d529`

### 4. `DOCS-20`'s headline constant is not citable where the row lives

- **Found during:** Task 3, pre-verifying every candidate citation before writing any.
- **What was checked:** `runtime/ccf_runtime/mcp/egress.py::PRODUCT_REQUEST_TOOL` resolves to **zero** spans. A later phase moved the definition to `src/ccf/products/door.py` — because the calling side is `ccf.client.adapters.mcp_stdio` in `src/`, and `src/` cannot import `runtime/` — leaving a re-export behind.
- **Resolution:** Cited at the definition site, with the reason stated in the cell so a later reader is not left wondering why a row about the egress door cites `src/`. **Not a defect:** both modules' docstrings say the dotted reference resolves unchanged, and it does — the dotted form and the symbol-citation form are different things, and only the latter needs a binding.
- **How it was found:** all 39 candidate citations were run through the lint's own span resolver **before** a single one was written. Two failed — this one and a test name guessed rather than read. Both were corrected before the edit rather than after a red gate.

### 5. Two `.md` files in `docs/` are untracked and were left alone

- **Found during:** every `git status` in this plan.
- **Disposition:** `docs/CCF_SDK_DE_REQUIREMENTS.md` and `docs/Context_Product_Specification_Standard_v0-3.md` were untracked before plan `21-02` and are untracked still. **Pre-existing, reported, not touched** — same disposition as waves 2 and 3, and for the same reason.

## Verification

| Check | Result |
|---|---|
| `pytest tools/docs_tests/test_requirement_ledger.py -q` | **exit 0** — 35 passed |
| `pytest tools/docs_tests/test_requirement_ledger.py tools/docs_tests/test_retirement_sweep.py -q` | **exit 0** — 68 passed |
| `python -m tools.lints --citations` | **exit 0**, 0 findings |
| `make lint` | **exit 0** |
| `make typecheck` | **exit 0** — 211 source files |
| `make test` | **exit 0** — **4105 passed / 118 skipped**, 10m39s — identical to the wave-1, wave-2 and wave-3 baselines |
| `make gate-tools` | **exit 0** — leg 1 **406**, leg 2 **189**; both unmoved, the mechanical proof no test was added |
| `refuse_unresolvable(ledger_text())` | **`[]`** over **112** citation tokens in status cells |
| `channel_disagreements` / `vocabulary_offenders` / `doubled_verdicts` | **`[]`**, **`[]`**, **`[]`** |
| all 18 Phase 16 `DOCS-` ids present in BOTH channels | **yes** — none flipped without evidence, none dropped |
| rows carrying a non-`Pending` verdict | **54 of 54** |
| rows still `Pending` anywhere in the ledger | **10** — every one a `RECON-` row, this phase's own, `21-06`'s |
| verdicts vs `21-DOCS-16-SPLIT.md`, compared mechanically | **zero mismatches** across all eighteen |
| `grep -c "^\| DOCS-" 21-DOCS-16-SPLIT.md` | **18** |
| `grep -c "^## DOCS-" 21-DOCS-16-SPLIT.md` | **18** |
| deferral-language grep on the split document | **0** |
| `ls examples/` | all nine of `00-quickstart` … `08-e2e-demo`, plus `external/` — **nothing retired** |
| `_anchor_verdict` on both anchored citations, before writing | **`True`**, never `None` |
| sabotage: `D-IMPL-94` re-aimed at `:356` | **exit 0 — NON-DISCRIMINATING**, because `D-IMPL-96` cross-cites it. Recorded, not hidden |
| sabotage: `D-IMPL-94` re-aimed at `:354` | **`cite02-anchor` RED** in both channels; restored byte-identical |
| `git diff --stat <base>..HEAD -- src/ runtime/ examples/ public/ tests/ pyproject.toml` | empty, every path |
| `git diff --stat <base>..HEAD -- tools/lints/citations.py` | empty |
| `git diff --name-only <base>..HEAD -- tools/` | only `tools/docs_tests/test_requirement_ledger.py` (plan `21-01`'s) |
| `git diff --name-only` over this plan's three task commits | exactly three paths |
| `git status --porcelain` after the final commit | only the two pre-existing untracked `docs/` files |

`make ci-core` is `lint typecheck test gate-tools`. Each leg was run individually rather than as one command, because a full pipeline cannot complete inside this harness's foreground call budget and `make test` alone took 10m39s.

## The coupling inventory's movement, and why it was expected

`docs/surface/examples/RETIREMENT-COUPLINGS.md` was regenerated after the last `.planning/` write of each of task 3 and this SUMMARY. The measured delta on the first regeneration:

- `.planning/REQUIREMENTS.md`: **41 → 98** coupling rows. Naming the nine `examples/` directories in `DOCS-17`'s status cell, and the rest across `DOCS-11`, `-12`, `-13` and `-14`, is exactly the edit the plan predicted would move this row.
- `21-DOCS-16-SPLIT.md` appears with **35** rows, for the same reason.

Both are the report doing its job. `--report` writes despite its name (`D-IMPL-154`), and `git status --porcelain` was checked after each regeneration to confirm only the paths this plan owns had moved.

## What plans `21-05`..`21-07` inherit

- **All 54 verdicts.** `21-06`'s completeness assertion now has a tree it can be true of; only the ten `RECON-` rows are left, and they are `21-06`'s own.
- **Three side-B work-list entries** with their closing costs already written, and their couplings stated: `DOCS-14`↔`EXAM-02`, `DOCS-17`↔`CLNT-17`↔`D-27`, and `DOCS-15` standing nearly alone.
- **Five split rows' owed limbs**, each named in its own cell, so the work list can lift half a row without re-reading the tree.
- **One ruling question that is four rows wide** — the published-pages limb of `DOCS-12`, `-13`, `-14` and `-15`.
- **A correction to `21-03`'s sabotage discipline**, which is the most transferable thing here: an anchored citation into `docs/DECISIONS.md` is only as strong as the sabotage that tested it, and a sabotage aimed at a cross-citing neighbour tests nothing. Require `_anchor_verdict` to return `False` on the target before trusting the control.
- **A reminder that a row can be stated in a third place** — twice now in this phase, and the second time it was the previous wave's own leftover.

## Threat Flags

None. This plan reads tracked repository files and writes markdown. No credential, no network call, no external input, no package installed — `T-21-SC` stays true by the `pyproject.toml` emptiness assertion inside `FENCE`. `T-21-19` (a row marked satisfied on the strength of an executed plan rather than a referent) was live across the whole lane and every side-A verdict carries a citation into the CURRENT tree, never into a SUMMARY alone — which is how `DOCS-13` came to be `Partial` despite Phase 20 shipping it well, and how `DOCS-10` came to be `Partial` despite `16-07`'s plan describing both limbs. `T-21-20` (an absence asserted but not shown) was live on all three `Not built` rows and all five `Partial` rows; every one names a path. `T-21-21` (retiring `examples/00`–`08` because `DOCS-17` says so) was live at the most tempting moment of the phase, and `ls examples/` plus the empty fence are the proof it did not happen. `T-21-22` (dropping an id to make a count work) is closed by the identical id set in both channels. `T-21-23` (the split document and the cells drifting apart) was asserted mechanically rather than by eye: all eighteen verdicts were compared against the split document's summary table and reported zero mismatches.

## Known Stubs

None.

## Self-Check: PASSED

All six files this plan created or modified exist on disk. All three task
commits `624ab9f`, `6fb22fd` and `b00d529` resolve in this repository.
Re-verified after the last write: the ledger module is 35 passed, the sweep and
ledger modules together are 68 passed, `--citations` is exit 0, `make lint`,
`make typecheck`, `make test` and `make gate-tools` are each exit 0, and the
pinned-base diff over `src/ runtime/ examples/ public/ tests/ pyproject.toml
tools/lints/citations.py` is empty on every path.

Four claims in this document were checked rather than asserted, because all four
read plausibly and could have been wrong.

- **The `:356` sabotage's non-discrimination** was measured against the shipped
  `_anchor_verdict`, not inferred from the lint's exit code: `True` at `:352`,
  `False` at `:354`, `True` at `:356`. The middle value is what made the second
  attempt a real control.
- **`DOCS-17`'s 111 / 15 / 102 figures** were re-measured on this tree rather
  than carried from `D-IMPL-145`, because a stale coupling count is exactly the
  kind of number that survives a year unchallenged. They have not moved.
- **All eighteen verdicts were compared to the split document mechanically**,
  by parsing both files, rather than read across by eye.
- **All nine `examples/00`–`08` directories were listed after the final task
  commit**, not before it, because the row that condemns them was being written
  in the same commit and a check taken at the wrong moment reports the wrong
  thing.
