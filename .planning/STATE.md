---
gsd_state_version: 1.0
milestone: v0.2
milestone_name: Performance, Documentation & Demonstration
status: executing
last_updated: "2026-08-22T23:40:00.000Z"
last_activity: >-
  2026-08-22 -- **PHASE 21 EXECUTION IS COMPLETE ON `phase-21`. `21-06` IS LANDED.**
  The phase does NOT close here: `21-07` is the SS3.1 close panel, the single-agent
  review and `D-GATE-21`, and Dave's ruling is the gate.
  **ALL 54 ROWS OF THE FROZEN WORKING SET CARRY A VERDICT**, counted by a STRICT parse
  and by membership against the Complete family rather than a string inequality:
  **38 `Complete`, 2 `Complete as ruled`, 9 `Partial`, 5 `Not built`, 0 `Orphaned`.**
  **THE PHASE'S OWN TEN `RECON-` ROWS CARRY VERDICTS TOO, AND THEY WERE WRITTEN BEFORE
  THE CLOSE PANEL** rather than inside the gate checkpoint -- so the ledger Dave approves
  and the ledger the panel reads are the SAME ledger. Eight `Complete`; two `Partial`,
  each naming its outstanding limb. `RECON-09` (close hygiene) cannot read `Complete`
  before `D-GATE-21` exists. `RECON-10` (the counters) is `Partial` because its own text
  says CORRECTED and one of its three was reported instead. Wave 5's SUMMARY frontmatter
  claimed `RECON-10` complete; the ledger verdict is against the row's text and says
  otherwise, deliberately. **ZERO `Pending` REMAINS ANYWHERE IN THE LEDGER.**
  The traceability table holds **143** rows -- 133 at the pinned base plus this phase's
  own ten -- a figure REPORTED from the strict parse, carried by no standing check
  (`D-21`).
  **THE `D-12` SPLIT IS REPORTED AND STILL UNRULED.** `21-DOCS-16-SPLIT.md` reports
  Phase 16's eighteen rows as ten already-satisfied, five split, three still owed and
  ZERO wholly orphaned, with one orphaned LIMB (`DOCS-18` limb 1, revoked by
  `D-IMPL-96`). All eighteen are unflipped, undropped, none retired and none built.
  **THE WORK LIST IS FIVE `Not built` ROWS IN TWO GROUPS AND FOUR OF THEM ARE ONE KNOT**
  -- `DOCS-17`, `CLNT-17`, `DOCS-14`, `EXAM-02`; `DOCS-15` stands nearly alone. Nothing
  on it was built (`D-11`), and the empty pinned-base fence is the mechanical proof.
  **ALL 27 `human_needed` ITEMS ACROSS 11 RECORDS** are named and quoted verbatim in
  `21-FINDINGS.md` SS3 and shown untouched by a diff over all eleven paths. `gsd-sdk
  query audit-uat` reports 24 across 9 because it filters on frontmatter `status:`;
  named, not fixed (`D-20`).
  **THE THREE COUNTERS, WITH THEIR OLD VALUES.** `.planning/REQUIREMENTS.md`'s
  `Coverage: 94/94` -> `143/143`, running totals extended. `.planning/ROADMAP.md`'s
  Phase 21 entry `52` -> `54` at three sites plus a lane list that did not sum to its own
  count. `.planning/ROADMAP.md` SSCoverage's `All **42**` REPORTED, NOT CORRECTED under
  `D-19`(a) -- it needs a ruling, and a marker at the site names it.
  **THE COMPLETENESS GATE IS NOW STANDING**, in `Check C` at the foot of
  `tools/docs_tests/test_requirement_ledger.py`: the working-set roster is re-derived
  from the strict parse at the pinned base and compared ID FOR ID (never by length --
  `D-21`), every roster row carries exactly one verdict, the phase's own roster is held
  to the same gate, and `tests/` is byte-identical to the base (`D-05`). The module is
  **45 tests**, up from 35; `gate-tools` is **406 + 199**, up from 406 + 189.
  **CONTROLS 10, 12, 13 AND 14 LANDED WITH IT. CONTROL 11 WAS NEITHER RE-ADDED NOR
  RENUMBERED** -- it shipped in wave 1 with the gate it falsifies. **CONTROL 15 WAS
  ADDED BECAUSE A SABOTAGE THIS PLAN SPECIFIED REPORTED GREEN**, and the reason was
  MEASURED rather than assumed: `doubled_verdicts` never calls `verdict_token`, and
  across all 143 cells the first bolded run equals the leading token, so the mutation
  was invisible to the entire module. CONTROL 15 makes it visible and goes red under it.
  That is the wave-4 lesson arriving inside this plan's own machinery.
  **ONE ROW WAS FOUND SHORT OF CRITERION 3 AND REPAIRED:** `DCD-02`'s status cell cited
  two plan numbers and no file. It read `Partial` at the pinned base, so every wave
  accepted it as already-verdicted and none re-read it. It now carries the four
  full-path symbol citations its own checkbox twin has carried since Phase 15.6.
  **`src/`, `runtime/` AND `tests/` ARE ALL DIFF-EMPTY** against the base pinned in
  wave 1, as are the wider `D-11` fence and `tools/lints/citations.py`.
  **NO GSD STATE OR ROADMAP WRITER WAS INVOKED** (`D-15`). Both files were backed up
  outside the tree, hand-edited, and diffed. The `progress:` block below stays
  deliberately untouched and byte-identical, for the reason wave 5 recorded.
  **THE PHASE IS AWAITING THE SS3.1 CLOSE PANEL AND `D-GATE-21`. IT IS NOT COMPLETE.**
  PRIOR CONTEXT FOLLOWS.
  2026-08-22 -- **PHASE 21 WAVE 5 IS LANDED. `21-05` IS COMPLETE, ON `phase-21`.**
  Two task commits `eedeefb` and `587ff78` plus the SUMMARY commit.
  **`21-FINDINGS.md` IS THE ONE DOCUMENT DAVE RULES FROM.** Five sections and nothing
  else: what the audit found, the work list, the verification debt, the counter
  corrections, and four observations that are adjacent and not this phase's to act on.
  **THE CENSUS ACROSS THE 54, BY STRICT PARSE AT WRITING TIME: 38 `Complete`, 2
  `Complete as ruled`, 9 `Partial`, 5 `Not built`, 0 `Orphaned`.** Two-thirds of the
  ledger's outstanding debt was work that had already shipped and was never ticked.
  Table row count 143 -- REPORTED, not carried by any check (`D-21`).
  **THE WORK LIST IS FIVE ROWS IN TWO GROUPS, AND FOUR OF THEM ARE ONE KNOT.**
  `DOCS-17`, `CLNT-17`, `DOCS-14` and `EXAM-02` cannot be sequenced apart: the
  replacements have to exist before the condemned trees can go, and the condemned trees
  are where the replacements' subject matter currently lives. Two questions inside that
  knot are Dave's alone -- the `00`-`08` half of `D-27`, and whether a Section-3
  replacement keeps the `s3-` naming at all. `DOCS-15` stands nearly alone and is the
  cheapest with the highest adoption leverage. Nothing on the list was built (`D-11`).
  **ALL 27 `human_needed` ITEMS ACROSS 11 RECORDS ARE NAMED, QUOTED VERBATIM AND SHOWN
  UNTOUCHED MECHANICALLY.** The roster was re-derived by parsing every
  `.planning/phases/*/[0-9]*-VERIFICATION.md` for a `human_verification:` block -- 16
  files match the glob, 11 carry the block -- and it matches `UAT_RECORDS` path for
  path. **THE 24-VS-27 DELTA AND ITS CAUSE ARE STATED, NOT SILENTLY DROPPED:**
  `gsd-sdk query audit-uat` filters on frontmatter `status:` and loses Phase 12
  (`status: passed`, 1 item, whose own prose reads `human_needed`) and Phase 18
  (`status: gaps_found`, 2 items). That is this phase's subject a THIRD time, in a third
  tool. `audit-uat`'s filter is NAMED, NOT FIXED (`D-20`, on `D-07`'s reasoning).
  Phase 15.1's two items were read from the SOURCE, not from `audit-uat --raw`, which
  returns the literal `">-"` for them -- a folded-scalar artefact in the query.
  **TWO COUNTERS CORRECTED, ONE REPORTED RATHER THAN GUESSED.**
  `.planning/REQUIREMENTS.md`'s `Coverage: 94/94` -> `143/143` with the running totals
  extended (101 / 123 / 133 / 143, each re-derived and 133 independently matching the
  pinned base). `.planning/ROADMAP.md`'s Phase 21 entry `52` -> `54` at three sites,
  and its lane list gains Phase 15.5 and Phase 15.6 so it sums to the count it states.
  **THE ROADMAP'S `All **42**` IS REPORTED, NOT CORRECTED** under `D-19` constraint
  (a): the sentence claims to be the traceability table's row count (143, never 42)
  while the two paragraphs beneath it enumerate a defined subset that sums to exactly 42
  and say outright that Phase 16's minting onward is not counted. The parse cannot
  settle which it means; correcting it needs a RULING -- is "v0.2 requirements" the
  whole table, or the milestone-definition set plus what inserted phases minted through
  15.1? A marker at the site says so and points at `21-FINDINGS.md` SS4.
  **EVERY COUNTER'S LOCATION WAS RE-RESOLVED AT EXECUTION TIME AND ONE HAD MOVED 38
  LINES.** `D-19` cited the `Coverage:` counter at `.planning/REQUIREMENTS.md:423`; it
  is at **461** today. The ROADMAP counter was 1946 when `D-19` was written and is
  **1959** now. The phase's own ruling carried a stale line citation while the phase was
  being executed -- the citation-drift hazard demonstrated on the phase that exists to
  name it. Locate by `grep`, never by a line number written in a plan.
  **NO GSD STATE OR ROADMAP WRITER WAS INVOKED AT ANY POINT IN THIS PLAN** (`D-15`,
  `D-IMPL-154`/`155`). Both files were backed up outside the tree, hand-edited, and
  `git diff` showed the intended replacement and nothing else. `roadmap.get-phase 21
  --raw` re-parsed to **14** criteria AFTER the hand-edit, one per unwrapped line.
  **THE `progress:` BLOCK BELOW IS STILL DELIBERATELY NOT TOUCHED.** Wave 1's
  `stopped_at` note handed it to `21-05`; that is wrong and is corrected here.
  `21-CONTEXT.md` DEFERRED it explicitly -- it is a GSD tooling limitation (the plan
  counter cannot see that Phase 16 was retired rather than executed), not a ledger row,
  and `D-19` names three counters, none of them this one. Guessing it is what
  `D-IMPL-174` forbids.
  **THE STALE `52` IN THE OLDER STATE ENTRIES BELOW WAS LEFT ALONE ON PURPOSE.** They
  are dated records of what was believed at the time, the same discipline
  `docs/DECISIONS.md` follows; the correction lives in this entry, not by rewriting
  history. The one at line 400 already carries `THE COUNT IS 54, NOT 52`.
  **NO TEST WAS WRITTEN AND NO NEW GUARD SHIPPED** (`D-05`). `gate-tools` is 406 + 189,
  unmoved from waves 2, 3 and 4. Nothing new to sabotage; the assertions this plan leans
  on shipped with their controls in waves 1 and 2, and CONTROL A -- which proves the
  eleven-record untouched-diff is not vacuous -- is a STANDING test that ran green here.
  **GATES:** `--citations` 0, `lint` 0, `typecheck` 0 (211 files), `gate-tools` 0
  (406 + 189), ledger module 35 passed, sweep + ledger 68 passed, `refuse_unresolvable`
  `[]`, channel disagreements `[]`, vocabulary offenders `[]`, doubled verdicts `[]`,
  identical id set in both channels across all 143 ids. Fabric, fence, the eleven UAT
  records and `tools/lints/citations.py` all diff-empty against the base.
  **NEXT: `21-06` -- the ten `RECON-` verdicts before the close panel, the completeness
  assertion, the position files and `make ci`.**
  PRIOR CONTEXT FOLLOWS.
  2026-08-22 -- **PHASE 21 WAVE 4 IS LANDED. `21-04` IS COMPLETE, ON `phase-21`.**
  Three task commits `624ab9f`, `6fb22fd`, `b00d529` plus the SUMMARY commit.
  **ALL FIFTY-FOUR ROWS NOW CARRY A VERDICT IN BOTH CHANNELS.** The only rows still
  reading `Pending` anywhere in the ledger are this phase's own ten `RECON-` rows,
  which are `21-06`'s. Nothing was flipped without evidence and no id was dropped:
  the strict parse reports an identical id set in both channels with zero
  disagreements, and every frozen roster is intact.
  **THE SPLIT IS `21-DOCS-16-SPLIT.md`: TEN `Complete`, FIVE `Partial`, THREE `Not
  built`, ZERO WHOLLY `Orphaned`** -- with ONE orphaned LIMB, inside `DOCS-18`.
  **THE THIN SIDE-C PILE IS THE FINDING, NOT A FAILURE OF THE AUDIT.** `RETIRED.md`
  retires the APPROACH and not the NEED, so an obligation about a NEED survives the
  rejection of the approach that was to satisfy it. What actually died is `DOCS-18`'s
  no-fabric-change assertion, and it died because `D-IMPL-96` REVOKED criterion 10 in
  Dave's own words -- *"it has been used out of context"* -- taking `D-13`'s
  enumerated exception and `gate_16.py` with it. `tools/gates/` holds no module. That
  limb is named ORPHANED in the cell so a later reader does not open it as work.
  **EIGHT ROWS HAD REAL WORK THE LEDGER NEVER RECORDED.** `DOCS-19`..`21` and
  `DOCS-23`..`25` shipped in Phase 16's OWN post-stop plans (`16-22`..`16-31`), and
  `DOCS-13`'s three harness legs shipped in PHASE 20 -- gated harder than the row
  asked, because `ccf` is REFUSED BY NAME for that root in a branch checked before
  the permitted-set test, so widening the set cannot admit it. `RETIRED.md`'s
  "executed 6 of 21" is true of the ORIGINAL plan set as of 2026-08-17; the ROADMAP's
  16/16 counts the later ten. Both are right about different sets.
  **A SABOTAGE THAT REPORTED GREEN AND SHOULD NOT HAVE -- THE ONE FINDING TO CARRY.**
  `D-IMPL-94`'s anchored citation was re-aimed from `docs/DECISIONS.md:352` to `:356`
  and `--citations` stayed at **exit 0**. The reason: `D-IMPL-96`, which lives at
  `:356`, CROSS-CITES `D-IMPL-94` in its own body, so `_anchor_verdict` still returns
  `True`. Re-aimed at `:354` -- a line that does not carry the token -- `cite02-anchor`
  went **RED in both channels**, then restored byte-identical. **An anchored line
  citation into `docs/DECISIONS.md` is weaker than it looks, because entries
  cross-cite each other's ids, and a control aimed at a cross-citing neighbour proves
  nothing.** `21-03`'s sabotage happened to land on a line that did not carry its
  token; had it landed on one that did, it would have reported the citation checked
  when the mutation was simply invisible. Later waves: pick the sabotage target by
  running `_anchor_verdict` and requiring `False`, not by assuming a neighbour differs.
  **`DOCS-17` IS BLOCKED ON DAVE, NOT ON AN EXECUTOR.** All ten condemned directories
  are in the tree, and that is a RULING rather than neglect: `D-IMPL-145` limb 2
  quarantined `examples/00`-`08` deliberately and plan `17-08` returned the `00`-`08`
  half of `D-27` undecided. Re-measured here rather than carried from the ruling:
  **111 references across 15 published pages, 102 of them snippet includes**, and zero
  published references to the `s1-*` trees. The figures have not moved. Coupled to
  `CLNT-17`, which is `Not built` on the other half of the same disposition.
  **A ROW WAS STATED IN A THIRD PLACE AGAIN, AND IT WAS A WAVE-3 LEFTOVER.** The
  minting prose still read *"DOCS-01..DOCS-06 stay Pending against Phase 14"* after
  `21-03` verdicted all six. Amended, with the amendment visible in the sentence, and
  the load-bearing claim (the PHASE column, not the STATUS column) preserved. Second
  occurrence of trap 7a in this phase. **Grep the whole ledger for a row's id before
  declaring it done.**
  **THE CITATION CHECKER CAUGHT MY OWN PROSE.** A `DOCS-20` clause naming the citation
  FORM was extracted as a BARE BASENAME citation and `refuse_unresolvable` refused it.
  Rephrased rather than exempted -- naming a form is not naming a file, and the
  checker cannot tell the difference, which is the right way round.
  **THREE SIDE-B ROWS GO ON `21-05`'S WORK LIST** with their closing costs written in
  `21-04-SUMMARY.md` so they need not be re-derived: `DOCS-14` (Section 3, coupled to
  `EXAM-02`), `DOCS-15` (the adoption-argument page) and `DOCS-17` (the retirement,
  coupled to `CLNT-17` and blocked on Dave). Plus the split limbs of `DOCS-10`, `-11`,
  `-12`, `-13` and `-18` limb 3. **The published-pages limb is the common thread**
  across `DOCS-12`..`-15`: four rows are short by the same thing.
  **NO TEST WAS WRITTEN, ANYWHERE, FOR ANY PURPOSE** (`D-05`). `gate-tools` is 406 +
  189, UNMOVED from `21-02` and `21-03`. This plan's three task commits touch exactly
  three paths: `.planning/REQUIREMENTS.md`, `21-DOCS-16-SPLIT.md` and the generated
  coupling inventory.
  **GATES:** `--citations` 0, `lint` 0, `typecheck` 0 (211 files), `test` 0 (4105
  passed / 118 skipped, 10m39s -- identical to waves 1, 2 and 3), `gate-tools` 0
  (406 + 189), ledger module 35 passed, sweep + ledger 68 passed,
  `refuse_unresolvable` `[]` over 112 citation tokens, channel disagreements `[]`,
  vocabulary offenders `[]`, doubled verdicts `[]`. Fabric, fence, the eleven UAT
  records and `tools/lints/citations.py` all diff-empty against the base. All nine of
  `examples/00-quickstart` through `08-e2e-demo` still present. **NEXT: `21-05` -- the
  work list, the 27 `human_needed` items, the observations and the three counter
  corrections.**
  PRIOR CONTEXT FOLLOWS.
  2026-08-22 -- **PHASE 21 WAVE 3 IS LANDED. `21-03` IS COMPLETE, ON `phase-21`.**
  Three task commits `16b6fe2`, `1b81927`, `73bc457` plus the SUMMARY commits.
  **THIRTY-SIX OF THE FIFTY-FOUR ROWS NOW CARRY A VERDICT IN BOTH CHANNELS.** The 14
  added here are `HARD-01`..`03` (Phase 9), `EXAM-01`..`03` (Phase 13), `DOCS-01`..`06`
  (Phase 14), `CPS-03` (15.5) and `DCD-02` (15.6). Zero `Pending` left in any of those
  five lanes. The 18 still `Pending` are ALL the Phase 16 lane and are `21-04`'s.
  **THE DOCUMENTATION LANE WAS NOT THE CITATION PROBLEM `21-02` FORECAST.** All six
  Phase 14 rows took `D-17` ROUTE 1 -- cite the guarding test -- so route 2 was used
  NOWHERE in that lane and route 3 nowhere either. The reason is structural and `21-04`
  should carry it: Phase 14 shipped pages PLUS A GATE PER CLAIM (publish scan,
  mkdocstrings strict-collection control, snippet gate, diagram bijection,
  documented-command bijection, OpenAPI drift control, per-advisory content gates) and
  gates are Python. Route 2 was spent where the evidence genuinely IS a ruling:
  `HARD-01`'s six-item batch and `DOCS-06`'s logged D-10 amendment.
  **EVERY ANCHORED LINE CITATION WAS RUN THROUGH THE SHIPPED `_anchor_verdict` BEFORE
  IT WAS WRITTEN AND REQUIRED TO RETURN `True`, NEVER `None`.** All 14 occurrences.
  A plain-word anchor returns `None` and the citation is UNCHECKED while looking
  checked -- the hazard `D-17` was ruled not to be a relaxation of. Then `D-IMPL-70`
  was deliberately re-aimed at `docs/DECISIONS.md:213` (which holds `D-IMPL-69`) and
  `--citations` went **RED at `cite02-anchor`**, naming row, anchor and lines; restored
  from a backup taken first.
  **`CPS-03` IS `Complete as ruled` (`D-IMPL-173`) IN ALL THREE PLACES THE ROW IS
  STATED -- NOT THE TWO THE PLAN NAMED.** The traceability table, the checkbox channel,
  and the CPS-lane EVIDENCE TABLE, which still opened `Pending by design` and is not
  parsed by `traceability_rows`, so nothing mechanical caught it or would have. Both
  `D-IMPL-113` and `D-IMPL-121` are cited in each, with the `by design, not by
  omission` clause intact. No seventh vocabulary word minted.
  **`EXAM-02` IS THE PLAN'S ONE `Not built`, AND IT IS `Not built` RATHER THAN
  `Orphaned` ON A MEASUREMENT:** `examples/s3-02-agentic-skills` is absent, no `s3-`
  example of any number is tracked, no `example-s3-` target exists, and Phase 16 was
  retired at `D-IMPL-152` before building the Section-3 suite -- BUT `RETIRED.md` says
  retiring the phase retires the APPROACH not the NEED, and the Phase-13 substance
  (`examples/01-agent-basics`, `02-skilling`, `05-workflow-hitl`, `06-decision-replay`)
  is still tracked and still in the `examples:` aggregate. The named home is missing,
  not the work. Work-list entry written in `21-03-SUMMARY.md` in the form `21-05`
  needs, WITH ITS COUPLING TO `CLNT-17` STATED -- the two cannot be sequenced apart.
  **THE THREE `EXAM` ROWS ARE JUDGED AGAINST THEIR `D-08` RE-HOMED TARGETS AND EACH
  CELL NAMES ITS TARGET** (`T-21-16`). Judging against examples `00`-`07`, which are
  still tracked and largely green, would have produced three `Complete`s and measured
  the wrong thing.
  **A NUMBER THAT HAD TO BE TAKEN TWICE, AND THE FIRST ONE WAS WRONG.** `DOCS-03`'s
  artifact-class coverage is **21 of 27** on the RENDERED tree with `--8<--` snippet
  includes resolved. Grepping page SOURCES gives **5 of 27** and is wrong -- the class
  ids arrive through the included worked-example artifacts. The cell carries 21 and
  says which count it is, so a later reader who greps `public/` and gets 5 knows they
  hold the wrong predicate. **Any figure this phase takes over `public/` must resolve
  includes first.**
  **TWO NAMED GAPS FOR `21-05` THAT ARE NOT `Not built` ROWS:** (1) `DOCS-06` --
  `docs-strict` IS a leg of `ci` and the workflow's `docs` job IS blocking, but **no
  test in this tree reads the `ci` target's composition or the workflow**, so the
  always-on limb is true by inspection and would not go red if a later edit dropped it;
  same shape as the `Makefile`-citation hole already in `deferred-items.md`.
  (2) `DOCS-03`'s six uncovered artifact classes, named in the cell.
  **`DCD-02` WAS CONFIRMED AGAINST THE TREE AND NOT REWRITTEN** -- `KycScenario`'s
  `debt_evidence` still ends `del view` / `return NO_DEBT_EVIDENCE`, unconditional,
  which is `D-IMPL-119` limb 3(b)'s omission path. Not one character changed.
  **THE CITATION LINT CAUGHT A RENAMED SYMBOL AGAIN, INSIDE THE WORK CORRECTING
  CITATIONS** -- `cite03-node-id` on a draft `DOCS-06` citation to
  `test_a2_the_maintainer_page_names_its_subject`. The citation was DROPPED rather than
  repaired: A-2 is the surface-toolchain page and was never `DOCS-06`'s subject, so the
  wrong name was downstream of wrong evidence. Second occurrence this phase.
  **NO TEST WAS WRITTEN, ANYWHERE, FOR ANY PURPOSE** (`D-05`). `gate-tools` is 406 +
  189, UNMOVED from `21-02` -- which is the mechanical proof. This plan's three task
  commits touch exactly two paths: `.planning/REQUIREMENTS.md` and the generated
  coupling inventory.
  **GATES:** `--citations` 0, `lint` 0, `typecheck` 0 (211 files), `test` 0 (4105
  passed / 118 skipped, 10m33s -- identical to waves 1 and 2), `gate-tools` 0
  (406 + 189), ledger module 35 passed, sweep + ledger 68 passed,
  `refuse_unresolvable` `[]` over 70 citation tokens, channel disagreements `[]`,
  vocabulary offenders `[]`, doubled verdicts `[]`. Fabric, fence, the eleven UAT
  records and `tools/lints/citations.py` all diff-empty against the base. The ten
  `RECON-` rows are untouched. **NEXT: `21-04` -- the Phase 16 lane, 18 rows, the
  hardest of the phase, and the one whose split Dave rules rather than the executor.**
  PRIOR CONTEXT FOLLOWS.
  2026-08-22 -- **PHASE 21 WAVE 2 IS LANDED. `21-02` IS COMPLETE, ON `phase-21`.**
  Three task commits `1a7a8b6`, `e190f28`, `6fa56f4` plus the SUMMARY commit.
  **TWENTY-TWO OF THE FIFTY-FOUR ROWS NOW CARRY A VERDICT IN BOTH CHANNELS** --
  `CLNT-01`..`CLNT-22`, zero `Pending` left in the lane. Twenty-one `Complete`
  (`CLNT-05` is `Complete as ruled`, against `D-IMPL-157`'s amended `-> bytes` seam)
  and ONE `Not built`. Every citation is a full repo-relative `path.py::symbol` that
  exists as written, and every one NAMES THE TEST that goes red on regression (`D-04`)
  -- so a tick means "it goes red if this regresses", not "someone looked once".
  **NO TEST WAS WRITTEN UNDER `tests/` AND NONE WAS WRITTEN ANYWHERE TO MANUFACTURE A
  NAME FOR `D-04`** (`D-05`). Every guarding test already existed.
  **THE ZERO-CITATION VACUITY GUARD LANDED, AND IT LANDED HONEST.** At the pinned base
  `citations_in_status_cells` returned ZERO tokens across all 133 status cells, which is
  why `21-01` withheld it; it went in during task 1 IMMEDIATELY AFTER the first eight
  rows' citations, in the same commit. Relocated, never weakened. With it:
  `test_the_scan_finds_citations_to_check` (the precondition -- carries NO count, per
  `D-21`) and `CONTROL 5b`. Module 33 -> 35 tests, `gate-tools` leg 2 187 -> 189.
  **THREE SABOTAGES, ALL AGAINST THE SHIPPED FUNCTION, ALL RESTORED FROM BACKUP.** The
  limb returning `[]` turns CONTROL 5b RED and nothing else. A blinded extractor with the
  guard intact turns 8 red. And -- the one worth keeping -- the WAVE-1 MODULE SHAPE
  reconstructed (extractor blinded AND the limb removed) turns the precondition RED while
  `test_every_cited_path_in_a_status_cell_resolves_as_written` stays GREEN over nothing.
  That third run exists because the plan's stated discrimination became UNSATISFIABLE once
  the guard shipped: the guard catches the same blindness, so both mechanisms fire. The
  honest version is to reproduce the prior shape and show what the new test adds.
  **`CLNT-17` IS THE PHASE'S FIRST NAMED ABSENCE, AND IT IS SPECIFIC (`D-10`):**
  `examples/s1-00-companies-over-revenue/` and `examples/s1-01-hello-context-product/` are
  both still tracked; `tests/examples/test_spine_separation.py` (14 functions, scoped
  `s1-*`) and `tests/examples/test_section_one_is_agent_free.py` both still ship and still
  enforce the shape rulings `D-25`/`D-26` suspended; `example-s1-00` and `example-s1-01`
  are still Makefile targets; the coupling inventory still files 58 rows against `17-08`.
  `17-08-SUMMARY.md` reads `status: blocked-at-task-3` -- DISPUTED ON A MEASUREMENT, not
  skipped: deleting `s1-01` removes the last shipped `examples/` call site of
  `refuse_request`, and `D-27`'s `00`-`08` half went back to Dave undecided. **NOT CLOSED
  HERE** -- `D-11` forbids it and the fence assertion proves it was not; the work-list
  entry is written in `21-02-SUMMARY.md` in the form `21-05` needs.
  **A CITATION FORM THE PLAN ASKED FOR IS UNUSABLE IN THIS FILE, MEASURED.**
  `.github/workflows/ci.yml:35` cannot be a status-cell citation: the lint's `CITATION`
  path group refuses a LEADING DOT, so the token that matches is `github/workflows/ci.yml`
  -- not a file in this tree -- and this phase's own `refuse_unresolvable` would refuse it,
  correctly. A `Makefile` has no suffix and matches nothing at all (already in
  `deferred-items.md`). So `CLNT-14` and `CLNT-16` cite the PYTHON that enforces the gate
  and state reachability in prose. **`21-03`/`21-04` will hit this harder** -- far more of
  the documentation lane's evidence lives in files the lint's path grammar cannot name.
  **GATES:** `--citations` 0, `lint` 0, `typecheck` 0 (211 files), `gate-tools` 0
  (406 + 189), `test_citation_coverage.py` 0 (the DCD-10 ceiling is unmoved -- every
  citation written here is `::symbol`, never an unanchored line citation). Fabric, fence,
  the eleven UAT records and `tools/lints/citations.py` all diff-empty against the base;
  the only `tools/` write is `test_requirement_ledger.py`. The ten `RECON-` rows are
  untouched. **NEXT: `21-03` -- the Phase 16 documentation lane, where the row claims are
  not testable behaviour.**
  PRIOR CONTEXT FOLLOWS.
  2026-08-21 -- **PHASE 21 WAVE 1 IS LANDED. `21-01` IS COMPLETE, ON `phase-21`.**
  Six commits `c51406b`..`845da98`. Nothing has a verdict yet, and that is the point:
  this plan built the machinery that guards the audit WHILE it happens.
  **THE `docs` JOB'S SHALLOW CHECKOUT WAS FIXED FIRST, BEFORE THE BASE WAS PINNED.** It is
  the job that runs `pytest tools/publish_scan_tests tools/docs_tests -q`, its checkout
  carried no `with:` block, and every pinned-base assertion this plan ships resolves a SHA
  that is absent from a depth-1 clone -- `git` exits 128 and `fabric_diff` raises BY DESIGN.
  Red from wave 1 for the whole phase, green locally, invisible until push. The `D-GATE-20`
  shallow-clone defect in a different job. Base pinned AFTER the fix at `c51406b`, so no
  untouched-tree assertion ever sees the workflow edit.
  **THE PHASE'S OWN TEN ROWS ARE IN THE LEDGER, IN WAVE 1, `Pending` IN BOTH CHANNELS.**
  Table 133 -> 143 rows, checkbox channel likewise, zero drift. `RECON-01`..`10` are NOT
  members of the 54-row working set; they are verdicted in `21-06`, BEFORE the close panel.
  Minted UNBOLDED, against the plan's action text and with its own parser requirement: the
  plan said `**Pending**` in one place and "a bare `Pending`" in two others, and bolding ten
  more would deepen the exact miscount this phase exists over -- `grep -c "| Pending |"`
  already misses `CPS-03` because its cell is bolded.
  **MEASURED WITH THE SHIPPED PARSER, NOT ESTIMATED:** 54 rows need a verdict under a
  MEMBERSHIP test against the Complete family; 56 under the literal `!= "Complete"` reading,
  which drags in `DCD-09` and `DCD-10` -- both already ruled on, both `[x]` in the other
  channel. Zero citation-shaped tokens exist in any status cell today, which is why the
  zero-CITATION guard is `21-02`'s and is RELOCATED, not weakened. Eleven
  `human_verification` records carry 27 items; `audit-uat` says 24 across 9 because it
  filters on frontmatter `status:` (`D-20`). The roster was re-derived by parse and agrees
  with RESEARCH SS7 exactly.
  **PER `D-21` NO STANDING CHECK CARRIES A ROW COUNT** -- verified with the guard the plan
  specifies, which returns 0. That constrained the writing: the guard matches
  `D-IMPL-172`-shaped tokens and `Makefile:138`-shaped citations as readily as
  `EXPECTED_ROWS = 143`, so every such reference lives in a column-0 comment.
  **ELEVEN NUMBERED CONTROLS PLUS TWO POSITIVE TWINS, EVERY MUTATION WATCHED RED against the
  SHIPPED function** and reverted from backup. Two are worth remembering. CONTROL A did not
  go red on its first run and the reason was not the module: `fabric_diff` compares COMMITS
  and is blind to the working tree. The `PINNED_FILES` sabotage PASSED the first time for the
  same reason -- the module was not yet committed -- and went red once it was. A control run
  at the wrong moment reports the wrong thing, which is this project's defect class arriving
  inside the machinery built to catch it.
  **FIVE PLAN DEFECTS FOUND AND FIXED IN-FLIGHT, all recorded in `21-01-SUMMARY.md`:** the
  future-import ordering (syntactically impossible as written); CONTROL 4's subject was
  refused by CONTROL 3's branch, so it would have passed with the suffix rule deleted;
  CONTROL 4b's subject matched neither citation pattern and could never have been extracted;
  the refusal ORDER the plan enumerates makes branches 3 and 4 unreachable; and the declared
  `citations_in_status_cells` signature cannot carry the `::` flag the suffix rule needs, so
  a companion was added rather than the signature changed.
  **NAMED, NOT FIXED,** in `.planning/phases/21-*/deferred-items.md`: `audit-uat`'s filter
  (`D-20`), the citation lint's two silent-drop holes (`D-07`, now mechanically pinned), and
  a stale `Makefile` citation to `.github/workflows/ci.yml:314` -- PRE-EXISTING, verified
  against the base's parent, and uncatchable because a `Makefile` has no suffix the citation
  lint scans.
  **GATES:** `make lint` 0, `make typecheck` 0 (211 files), `make test` 0 (**4105 passed /
  118 skipped**, 10m25s), `make gate-tools` 0 (406 + **187**, was 154), `--citations` 0.
  Fabric, scope fence, the eleven UAT records and `tools/lints/citations.py` all diff-empty
  against the base. **NEXT: `21-02` -- verdicts for the 22 `CLNT` rows, and the
  zero-CITATION guard it owes.**
  PRIOR CONTEXT FOLLOWS.
  2026-08-21 -- **PHASE 21 IS PLANNED. SEVEN PLANS, SEVEN SERIAL WAVES, ON `phase-21`.**
  Research -> pattern map -> plan -> THREE checker passes (10 findings -> 8 -> 5, all
  verified against the tree before action) -> two planner revisions -> a surgical
  advisory pass. Commits `0aa5bbd`..`637d997`. Coverage gates GREEN: `RECON-01`..`10`
  all carried, decision coverage 21/21, all seven plans structurally valid.
  **THE PHASE'S SUBJECT KEPT ARRIVING BEFORE THE PHASE.** Four separate count defects
  were found and ruled during planning, every one the same shape -- a number standing in
  for a set it never named: (1) `52` vs the strict parse's `54`, already ruled at the
  discuss sitting; (2) GSD's UI-phase detector firing on Phase 21 because `grep -iE`
  matched `form` inside *"in a form a reader can check"* -- treated as `--skip-ui`;
  (3) `gsd-sdk query audit-uat` reporting `24 human_needed items across 9 files` when the
  files carry `27 across 11`, because it FILTERS ON FRONTMATTER `status:` and drops Phase
  12 (`status: passed`, 1 item) and Phase 18 (`status: gaps_found`, 2 items) -- criterion
  11 AMENDED on Dave's ruling, `D-20`; (4) criterion 10 hardcoding `133 requirement ids`,
  which the phase's OWN wave-1 mint of ten `RECON-` rows falsifies -- criterion 10 AMENDED
  to drop the number entirely, `D-21`, whose binding consequence is that NO standing check
  in this phase carries a hardcoded count and every fixed set is a frozen roster of NAMED
  ids. `audit-uat`'s filter and the citation lint's ambiguous-basename hole are NAMED, NOT
  FIXED (`D-07`, `D-20`) -- tooling repair inside an audit phase.
  **THE CHECKER EARNED ITS KEEP TWICE OVER.** It reversed a planner judgement call that
  would have added the phase's own ten `RECON-` rows AFTER Dave's approval, inside a
  `checkpoint:human-verify` task -- ten rows entering the ledger carrying verdicts no
  panel, no review and no human ever saw, which is the ledger-debt pattern this phase was
  commissioned to end, one level up. Rows now mint in wave 1 and are verdicted in `21-06`,
  BEFORE the close panel. It also caught `.github/workflows/ci.yml`'s `docs` job -- the one
  that runs `tools/docs_tests` -- having NO `fetch-depth: 0`, which is the `D-GATE-20`
  shallow-clone defect repeating in a different job; the fix lands in `21-01` task 1 before
  the module does. And it caught the `D-21` guard against hardcoded counts being unable to
  detect `EXPECTED_ROWS = 143` -- reproduced empirically, widened, re-verified.
  **SEQUENCING IS THE PLAN'S SPINE:** `ci-core` must be green from wave 1, so every
  INVARIANT check (citation refusal, channel agreement, vocabulary, one-verdict-per-cell)
  lands in wave 1 where it is true of a partially-filled ledger, and the COMPLETENESS count
  lands LAST in wave 6. Measured: ZERO citation-shaped tokens exist in any status cell
  today, which is why the zero-citation vacuity guard had to move to wave 2.
  **NEXT: `/gsd:execute-phase 21`.** The phase FINDS and RECORDS; it builds nothing.
  Two untracked files Dave placed in `docs/` -- `CCF_SDK_DE_REQUIREMENTS.md` and
  `Context_Product_Specification_Standard_v0-3.md` -- are for a LATER phase and were kept
  out of every agent prompt and every commit.
  PRIOR CONTEXT FOLLOWS.
  2026-08-21 -- **PHASE 20 IS GATED. `D-GATE-20` IS APPROVED BY DAVE AND LOGGED IN
  `docs/DECISIONS.md`, AND `phase-20` IS MERGED TO `main`.** 51 commits, `9e4bd0e`..`921e3b9`.
  All TEN Success Criteria met -- authored one-per-line BEFORE execution, which is the first
  honouring of the forward-binding rule `D-GATE-19` minted. FIVE blocking findings were found
  at close and ALL FIVE are fixed in-phase, each with a STANDING sabotage control watched go
  red: `B-1`, `B-2`, `B-3` from the cross-AI panel and `CR-01`, `CR-02` from the additive
  single-agent review. FOUR panel findings were REJECTED and recorded as rejected. CARRIED,
  NOT REOPENED: four panel advisories `A-1`..`A-4` and NINE single-agent warnings
  `WR-01`..`WR-09` (the review frontmatter's `warning: 8` undercounts by one), of which
  `WR-08` continues the `D-IMPL-155` ambiguous-basename citation hazard. CI run `32534167036`
  at `921e3b9` GREEN on all four jobs. **NEXT: the requirement-ledger reconciliation --
  52 rows still read `Pending`, and the `progress:` block below is STALE for the same reason
  and is deliberately NOT guessed at here.**
  PRIOR CONTEXT FOLLOWS.
  2026-08-21 -- **PHASE 20 EXECUTION COMPLETE ON `phase-20`. AWAITING THE SS3.1 CLOSE PANEL
  AND `D-GATE-20`.** 8 plans / 8 serial waves / 25 tasks, `9e4bd0e`..`d9b3f5a`. THE CLAIM IS
  MEASURED, NOT ASSERTED: `consume.py` and three foreign-harness clients -- Google ADK, the
  Anthropic Agent SDK, LangGraph -- each print the SAME content address
  `5d7bfa49f5b3f65add25ea61220a191a91982f5ae97901e010b26c5ca8dc37f5`, each carrying the
  declared payload names, in 10.5s with NO live model call. CLAUDE.md SS7.3's "a harness
  that already speaks MCP needs no adapter for consumption" is now DEMONSTRATED against the
  current surface. Clients import harness + `mcp` + stdlib ONLY -- AST-verified by the
  orchestrator and gated by `test_client_example_purity.py` per-root permitted sets with
  `ccf` refused BY NAME. `CLNT-23..32` minted and discharged (TEN rows). `D-IMPL-163..169`.
  **DAVE RULED TWICE IN-FLIGHT.** (1) The WAVE-1 LAYOUT BLOCKER: `test_artifact_schema_headers.py`
  enforces a bijection -- every `examples/**/artifacts/` must sit under a directory containing
  `run.py` -- and `H-11` forbids a `run.py` at the example root, so an `artifacts/` dir there is
  ORPHANED BY CONSTRUCTION, and naming the runner `run.py` would make `runner/` a SECOND root
  demanding its own `artifacts/`. Ruled: both the declared input and the runner live in
  `runner/`, and the runner is `drive.py`. Plan repair across six plans, `dc2c214`.
  (2) **RULING 6**: the leg-2 prompt is DATA, and `cinv01a-prompt-shape` is TIGHTENED IN-PHASE
  (scope deliberately widened, recorded in the ROADMAP as ruling 6, `b4217e9`). The measured
  hole: `prompt_score` scores short realistic agent prompts 0-1 against `PROMPT_SCORE_THRESHOLD = 2`,
  so a hardcoded system instruction in an example client produced NO finding. Lowering the
  threshold to 1 was measured at 94 FALSE findings and STILL missed two of four shapes; the
  adopted fix is a DESTINATION ARM -- refuse prose that REACHES a model-instruction sink,
  following the value through local bindings and `os.environ.get` fallbacks. It surfaced TWO
  GENUINE pre-existing SS6.4 violations in `examples/external/00-hello-context/`, both
  remediated in-phase.
  **FOUR CHECKS THAT COULD NOT FAIL WERE FOUND AND CLOSED, THREE OF THEM BY THE EXECUTORS
  THEMSELVES.** (a) wave 5: `socket.create_connection` control passed with its patch REMOVED,
  because CPython's `create_connection` calls the OTHER patched name -- retargeted at an
  unresolvable `.invalid` host, upgrading the claim to "not even a name lookup". (b) wave 6:
  two control branches unreachable because a broader check fired first. (c) wave 7: a vacuous
  pass over a missing subject left two controls green. (d) wave 8: CONTROL 6 caught that a
  BROKEN `git diff` and a CLEAN one are indistinguishable -- without it the phase would have
  closed on two green emptiness assertions over a comparison that never ran.
  **ONE GUARD WAS NARROWED AND THE ORCHESTRATOR SENT IT BACK.** Wave 7 narrowed ext-00's
  `git status --porcelain` guard to untracked-files-only, justified by a red it saw during its
  own task. Measured post-commit: the verbatim form PASSES; commit-before-verify was the
  available remedy. Both arms restored over one `porcelain_entries` read, eight controls,
  twelve mutations all red. `D-IMPL-166` sets the general rule: A GUARD IS NEVER NARROWED TO
  ACCOMMODATE AN AUTHOR'S IN-FLIGHT WORKING TREE.
  GATE: `make ci` EXIT 0 -- **4083 passed / 118 skipped**, 406 lint, 154 docs. Tests
  4013 -> 4083 (+70). `examples/s2-01-external-consumers/` MOVED to
  `docs/retired/16-external-consumers/` with history; `examples/external/00-hello-context/`
  KEPT and marked historical IN PROSE under an existing heading (its `run.py` enforces seven
  `## ` headings by name and order). CRITERION 7 ASSERTED: `git diff 9e4bd0e..HEAD -- src/`
  EMPTY, with CONTROL 6/7 proving the assertion is not vacuous.
progress:
  total_phases: 19
  completed_phases: 17
  total_plans: 188
  completed_plans: 174
  percent: 93
stopped_at: >-
  PHASE 21 EXECUTION IS DONE; `21-07` -- THE SS3.1 CLOSE PANEL AND `D-GATE-21` -- IS
  NEXT. Branch `phase-21`, tree clean apart from Dave's two untracked `docs/` files.
  Six of seven plans are complete; `21-07` is the gate checkpoint and is not complete
  until Dave rules. **`21-07` ADDS NO LEDGER ROWS** -- every row it reviews was written
  before it, on purpose.
  **WHAT THE PANEL MUST BE GIVEN, PER `CLAUDE.md` SS3.1:** the SHIPPED CODE and the
  shipped ledger, not the plans -- those decisions are executed. Write it to
  `21-CLOSE-REVIEWS.md` so the pre-execution plan review survives. Brief it on the
  findings already known and tell it not to re-derive them; its budget is better spent
  on what is ADJACENT to each. Verify every finding against the tree before recording or
  acting on it, and record the rejected ones AS rejected -- this project has received
  confident, well-formatted, false findings twice.
  **DO NOT TOUCH THE FIVE `Not built` ROWS OR ANYTHING THEY NAME.** `D-11` holds to the
  end of the phase; the work list is Dave's to rule on and a later phase's to execute.
  **THE `progress:` COUNTERS ABOVE REMAIN DELIBERATELY UNTOUCHED**, for the reason wave
  5 recorded: `21-CONTEXT.md` deferred the block explicitly and `D-19` names three
  counters, none of them this one.
  **TWO THINGS DAVE MUST RULE ON THAT AN EXECUTOR CANNOT:** the `All **42**` counter's
  provenance question, and the four-row knot on the work list.
  **NEXT ACTION: run `/gsd-review --phase "Phase 21" --all`, then the single-agent
  review, then present to Dave.**
  PRIOR CONTEXT FOLLOWS.
  PHASE 21 WAVE 5 IS DONE; WAVE 6 (`21-06`) IS NEXT. Branch `phase-21`, tree clean apart
  from Dave's two untracked `docs/` files. `21-06` writes the ten `RECON-` verdicts -- the
  only rows still reading `Pending` anywhere in the ledger -- BEFORE the close panel, lands
  the completeness assertion `21-01` deliberately held back until every row was written,
  updates the position files by hand, and runs `make ci`. `21-07` is the SS3.1 close panel,
  the single-agent review and `D-GATE-21`.
  **DO NOT TOUCH THE FIVE `Not built` ROWS OR ANYTHING THEY NAME.** `D-11` holds to the
  end of the phase; the work list is Dave's to rule on and a later phase's to execute.
  **THE `progress:` COUNTERS ABOVE REMAIN DELIBERATELY NOT TOUCHED, AND WAVE 1'S NOTE
  HANDING THEM TO `21-05` WAS WRONG.** `21-CONTEXT.md` DEFERRED the `progress:` block
  explicitly -- it is a GSD tooling limitation, not a ledger row -- and `D-19` names three
  counters, none of them this one. Two of those three are corrected and the third is
  reported rather than guessed; that work is DONE and `RECON-10` is discharged in substance,
  awaiting only its verdict cell in `21-06`.
  **THE ONE THING `21-06` MUST NOT INHERIT AS AN ASSUMPTION:** no row count is carried by
  any check (`D-21`). 143 is a reported measurement, not a constant. Measure it.
  **NEXT ACTION: continue `/gsd:execute-phase 21` at `21-02`.**
  PRIOR CONTEXT FOLLOWS.
  PHASE 21 IS PLANNED AND READY TO EXECUTE. Branch `phase-21`, tree clean apart from Dave's
  two untracked `docs/` files. SEVEN plans, SEVEN serial waves -- serial because every audit
  plan writes `.planning/REQUIREMENTS.md`. Wave 1 `21-01` pins the base, fixes the `docs`
  job's shallow checkout, mints the phase's own ten `RECON-` rows and ships both standing
  checks with CONTROLS 1-9, 9b, 11 and A-C; waves 2-4 write verdicts (22 `CLNT`, then 14
  mixed, then Phase 16's 18 as a two-sided split); wave 5 the findings, work list, 27
  `human_needed` items and three counter corrections; wave 6 the completeness count and the
  untouched-fabric proof; wave 7 the SS3.1 close panel and `D-GATE-21`.
  `21-CONTEXT.md` now carries TWENTY-ONE decisions `D-01`..`D-21` -- `D-17`/`D-18`/`D-19`
  ruled by Dave after research, `D-20`/`D-21` after the checker passes.
  **WHAT AN EXECUTOR MUST NOT DO:** close a gap it discovers (`D-11`), write a test to
  manufacture a criterion-6 name (`D-05`), fix `tools/lints/citations.py` (`D-07`, now
  mechanically pinned by `PINNED_FILES`), fix `audit-uat` (`D-20`), flip or drop Phase 16's
  eighteen rows (`D-12`), discharge a `human_needed` item (`D-13`), backfill a `D-GATE`
  (`D-14`), touch `src/` or `runtime/` (criterion 12), or use `gsd-sdk query state.*` /
  `roadmap.*` (`D-15`). Regenerate `docs/surface/examples/RETIREMENT-COUPLINGS.md` LAST
  after every `.planning/` edit, the SUMMARY included -- it walks `.planning/` and reddens
  the docs gate on every planning commit.
  **NEXT ACTION: `/gsd:execute-phase 21`.**
  PRIOR CONTEXT FOLLOWS.
  PHASE 21 CONTEXT IS GATHERED; THE PHASE WAS READY TO PLAN. Work is on branch `phase-21`.
  `21-CONTEXT.md` carries SIXTEEN decisions `D-01`..`D-16`. **THE COUNT IS 54, NOT 52** --
  a strict parse of the traceability table returns 133 rows, 54 of them not-`Complete`;
  `grep -c "| Pending |"` misses `CPS-03` (bold `**Pending**`) and `DCD-02` (`**Partial**`),
  and the wrong figure had already reached `D-GATE-20`, the first ROADMAP draft of this
  phase and the progress report. The phase's own subject arrived before the phase did.
  ROADMAP Success Criteria AMENDED IN-SESSION before any planning: ten -> FOURTEEN,
  `roadmap.get-phase 21` confirms parsed count = 14. **THE SCOUT CHANGED THE PHASE SHAPE:**
  `.planning/REQUIREMENTS.md` is ALREADY inside `tools/lints/citations.py`'s `GATED_TREES`
  with NO `HISTORICAL_RECORDS` exemption, so a `path::symbol` citation written into a
  requirement row is resolved by machinery that already ships -- criterion 3 needs no new
  resolver. Phase 15.6's `DCD-02`..`DCD-12` rows are the adopted format AND the adopted
  verdict vocabulary. The ledger's two status channels (checkbox list + traceability table)
  measured at ZERO drift across all 133 ids and a standing check must keep them that way.
  **NEXT ACTION: `/gsd:plan-phase 21`.** The phase FINDS and RECORDS; it builds nothing.
  PRIOR CONTEXT FOLLOWS.
  PHASE 20 IS CLOSED AND PHASE 21 IS IN THE ROADMAP, UNPLANNED. Dave ruled three times at
  the Phase 20 close (2026-08-21): (1) the 52 `Pending` requirement rows get a ROW-BY-ROW
  reconciliation phase, not a wholesale tick; (2) the ten phases with no `D-GATE` entry are
  gated by their ROADMAP completion rows and are NOT backfilled -- logged as `D-IMPL-171`;
  (3) Phase 16's eighteen `DOCS-` rows are DEFERRED until the audit reports the split, in
  Dave's words *"tell me after the audit"*. Phase 21 is written into the ROADMAP BY HAND
  (bullet + detail section + progress row, `phase.add` not used per `D-IMPL-154`/`155`) with
  TEN Success Criteria authored one-per-unwrapped-line BEFORE execution; `roadmap.get-phase
  21` confirms parsed count = 10. **NEXT ACTION: `/gsd:discuss-phase 21`, then plan it.** The
  phase FINDS and RECORDS; it does not build what a `not-built` verdict surfaces -- that is a
  later phase and Dave's call.
  PRIOR CONTEXT FOLLOWS.
  PHASE 20 IS CLOSED. `D-GATE-20` is logged (append-only, at the end of `docs/DECISIONS.md`)
  and `phase-20` is merged to `main`. SS3.1 ran IN ORDER and the order mattered: execution ->
  cross-AI close panel against the SHIPPED CODE -> additive single-agent review -> every
  finding verified against the tree -> all five blocking findings fixed in-phase -> presented
  to Dave -> ruling -> gate entry -> merge.
  **THE ONE THING OWED NEXT IS THE REQUIREMENT-LEDGER RECONCILIATION, AND IT BLOCKS v0.2.**
  `.planning/REQUIREMENTS.md` carries 52 rows reading `Pending`: 21 Phase 17, 18 Phase 16,
  6 Phase 14, 3 Phase 9, 3 Phase 13, 1 Phase 18. Phase 20's own ten (`CLNT-23`..`CLNT-32`)
  are `Complete` and match the tree. **The eighteen Phase 16 rows are NOT bookkeeping** --
  Phase 16 was RETIRED (`D-IMPL-152`), not completed, and its 14 unexecuted plans live in
  `abandoned/`; `DOCS-07`..`DOCS-25` are obligations attached to an approach that no longer
  exists and they need a RULING (re-home onto a new phase, or formally drop), not a tick.
  The other 34 rows are most likely unreconciled bookkeeping against GATED phases, but that
  is a HYPOTHESIS TO BE VERIFIED ROW BY ROW AGAINST THE TREE, NOT AN ASSUMPTION TO ACT ON --
  only 12 of the 22 `CLNT-` ids are named anywhere in `docs/DECISIONS.md`. **DO NOT RUN
  `/gsd:complete-milestone`:** the plan counter reads 100% because it counts SUMMARY files
  against PLAN files and cannot see that a phase was retired rather than executed, which is
  this project's own recurring defect class -- a check that cannot report the thing it
  appears to report. ALSO OPEN: 24 `human_needed` verification items across 9 phases (11,
  13, 14, 15.1-15.4, 18.1, 19), all requiring Dave rather than an executor; the largest is
  Phase 11's first perf baseline, which needs a live GitHub Actions dispatch and a
  `D-IMPL-70` approval.
  PRIOR CONTEXT FOLLOWS.
  PHASE 20 IS EXECUTION-COMPLETE, THE CLOSE PANEL IS DONE, AND IT IS NOT GATED. Work is on
  branch `phase-20` (`9e4bd0e`..`7f59289`+), NOT on `main`.
  **STEP 1 OF SS3.1 IS COMPLETE.** The CROSS-AI CLOSE PANEL ran 2026-08-21 against the
  SHIPPED CODE and is committed at `7f59289` as
  `.planning/phases/20-.../20-CLOSE-REVIEWS.md` (356 lines, with a verbatim-reproduction
  appendix). Reviewers: gemini, codex, cursor; `claude` SKIPPED as the executing model.
  304 KB / 5,889 lines of committed source was INLINED into the prompt -- required,
  because codex reviews nothing at exit 0 on this host. Eleven findings claimed, EVERY ONE
  VERIFIED against the tree: THREE BLOCKING, four advisory, FOUR REJECTED (recorded as
  rejected).
  **THE THREE BLOCKING FINDINGS -- ALL FIXED 2026-08-21 (`08826ba`, `86142a0`, `ad3edb0`),
  each with a standing control verified RED under sabotage. Recorded below as found:**
  **B-1** `examples/hw1-harness-clients/runner/drive.py::marker_violations` vs
  `examples/hw1-harness-clients/runner/drive.py::observed_markers` vs
  `examples/hw1-harness-clients/runner/drive.py::CONSOLE_VOCABULARY`.
  `marker_violations` property 4 compares whole WORDS of a declared name against the chrome
  vocabulary; `observed_markers` matches by raw SUBSTRING; and `CONSOLE_VOCABULARY` OMITS
  `product`, a word all three legs print (`print("context product")`). PROVEN by running
  the shipped functions: names `product`, `text`, `ntex` are ACCEPTED by the marker guard,
  and an address-only leg then PASSES `payload_violations` -- CONTROL A's exact subject
  passing the check written to refuse it. LATENT, not live: the six current names in
  `runner/scenario-rows.yaml` are safe. Root cause: the vocabulary was sourced from
  `consume.py::main` + the runner, but the check greps the LEG's stdout.
  **B-2** `tools/lints/no_hardcoding.py::resolved_text`. The CINV-01a destination arm resolves
  `node.args[1]` ONLY, so `os.environ.get(k, default="...")` and `os.getenv(k,
  default="...")` ESCAPE it. PROVEN against `check_source`: positional FLAGGED, both
  keyword spellings NOT FLAGGED. Both spellings are valid Python (executed to confirm).
  This is one spelling of the exact "env var worn as a hat" shape ruling 6(b) minted the
  arm to refuse.
  **B-3** `examples/hw1-harness-clients/runner/drive.py::marker_violations`,
  `examples/hw1-harness-clients/runner/drive.py::payload_violations` and
  `examples/hw1-harness-clients/runner/drive.py::compare_addresses`. `marker_violations`, `payload_violations` and
  `compare_addresses` appear ONLY in `drive.py` -- no test imports or probes them. CONTROL
  A-F ran as ONE-SHOT mutation probes recorded in `20-03-SUMMARY.md:164-172`, not standing
  tests, unlike the purity gate (C-20-1..9) and the no-model guard (CONTROL 1-3) which both
  ship pytest controls. B-1 IS THE DIRECT CONSEQUENCE. **Whether a SUMMARY-recorded
  one-shot probe discharges `CLNT-12` IS A RULING FOR DAVE, not a thing to decide alone.**
  **ADVISORY (4):** A-1 `tools/lints/no_hardcoding.py::check_source` -- the message says a prompt is refused
  "not by how long it is" while `_is_prose_candidate` floors at `MIN_PROMPT_CHARS = 40`;
  the FLOOR is a documented measured knee (CONTROL 8) and is NOT the defect, the SENTENCE
  is. Only three-way consensus finding. A-2 `runner/model_stub.py` `seen` written and never
  read, which its own docstring at `:45` calls the `C-10` pattern this project refuses.
  A-3 `examples/hw1-harness-clients/runner/drive.py::reference_run` has no subprocess
  timeout while `examples/hw1-harness-clients/runner/drive.py::drive_leg` does.
  A-4 a leg timeout orphans the door grandchild -- already documented in situ at `:966-971`.
  **REJECTED (4), and why it matters:** codex quoted a docstring sentence that DOES NOT
  EXIST in the file it cited (`grep -n reference tests/examples/test_hw1_harness_clients_
  no_model.py` returns NOTHING) -- the fabricated-citation mode this project has rejected
  reviewer output for before. gemini's case-sensitivity scenario runs BACKWARDS through
  `_words` (`examples/hw1-harness-clients/runner/drive.py::_words`), which lowercases. Full rejection reasoning in the report.
  **NEXT ACTION, in this order:** (2) the SINGLE-AGENT code review (`/gsd-code-review`),
  ADDITIVE and never a substitute for the panel; (3) FIX B-1, B-2, B-3 IN-PHASE -- each
  fix carries its own standing sabotage control per `CLNT-12`, and B-1's fix must turn the
  appendix reproduction RED; (4) present deliverables + this report + the triage to Dave;
  (5) `D-GATE-20` and the merge to `main`. PANEL RELIABILITY OBSERVED THIS ROUND: cursor
  was the STRONGEST (both surviving blockers plus the seed of the third, accurate
  `path:line` throughout); codex DID read when source was inlined (95,655 tokens) but
  fabricated one citation; gemini found no fabricated symbols but reasoned backwards once.
  `make gate-tools` at `7f59289` is EXIT 0 (406 + 154) -- adding this report under
  `.planning/` did NOT stale the coupling inventory. No shipped code changed, so the
  executor's green `make ci` at `d9b3f5a` still stands.
  PRIOR CONTEXT FOLLOWS.
  PHASE 20 IS EXECUTION-COMPLETE AND NOT YET GATED. Work is on branch `phase-20`
  (`9e4bd0e`..`5c0cc24`), NOT on `main`. NEXT ACTION, per CLAUDE.md SS3.1 and in this order:
  (1) the CROSS-AI PANEL against the SHIPPED CODE -- `/gsd-review --phase "Phase 20" --all`
  -- written to a DISTINCT `20-CLOSE-REVIEWS.md` so the pre-execution plan reviews survive;
  (2) the single-agent code review, which is ADDITIVE and never a substitute; (3) VERIFY
  EVERY FINDING against the tree before recording or acting on it, and record rejected
  findings as rejected; (4) fix all blocking findings IN-PHASE; (5) present to Dave with the
  triage; (6) `D-GATE-20` and the merge to `main`.
  TWO RESIDUALS ARE CARRIED, NEITHER PAPERED OVER. (1) THE POST-SUMMARY REGENERATION WINDOW:
  GSD writes a plan's SUMMARY AFTER its tasks, so a final `tools/retirement_sweep.py --report`
  can be invalidated by that plan's own summary naming a retiring path. Measured at wave 8 --
  it added EXACTLY ONE row and skipping the step would have left `make ci` RED on a tree
  nobody else had touched. It is a HAND-RUN STEP, NOT A MECHANISM: the next phase's first
  plan must repeat it if it edits `.planning/**` before asserting `make ci`. The currency test
  was NOT exempted; if the hand-run proves insufficient that is a `D-IMPL` and a STOP.
  (2) The x86_64 `claude-agent-sdk==0.2.128` wheel bundling the `claude` CLI is UNVERIFIED
  from this aarch64 host. NO FALLBACK WAS BUILT and none should be -- a second leg-2 path CI
  never exercises is criterion 6's own failure mode. Confirm with one CI run or
  `pip download claude-agent-sdk==0.2.128 --platform manylinux_2_17_x86_64 --no-deps` and
  inspect the wheel for `_bundled/claude`. The README states the wheel bundles the CLI without
  qualifying by architecture; that is the sentence to correct if it resolves against us.
  **WHAT WAS ACTUALLY VERIFIED AT CLOSE, AND BY WHOM -- DO NOT RE-DERIVE, DO NOT OVERCLAIM.**
  The executor ran a FULL `make ci` to EXIT 0 at `d9b3f5a`: **4083 passed / 118 skipped**,
  406 lint, 154 docs. The ORCHESTRATOR verified, at HEAD, independently: `make gate-tools`
  EXIT 0 (406 + 154); `tests/examples` **456 passed / 37 skipped**; criterion 7 (`git diff
  9e4bd0e..HEAD -- src/` EMPTY); `s2-01` gone with exactly ONE `client_langgraph.py` under
  `examples/`; ten `CLNT-23..32` rows flipped; the ten Success Criteria still parsing as TEN
  after the ROADMAP hand-edit; and a live `make example-hw1-harness-clients` printing three
  legs plus the reference at one address with declared names and NO refusal line. THE
  ORCHESTRATOR DID NOT COMPLETE A FULL `make ci` ITSELF -- see the harness note below. The
  delta between the executor's green run and HEAD is ONLY `.planning/ROADMAP.md`,
  `.planning/STATE.md` and the regenerated inventory, and NO test under `tests/` reads
  `ROADMAP.md` or `STATE.md` (measured), so the untested surface is nil.
  **HARNESS LIMITATION, OPERATIONAL:** a full `make ci` CANNOT be completed in one tool call
  in this environment -- foreground Bash caps at 10 minutes and background jobs were KILLED
  at ~3 minutes, twice. A partial run reached lint OK, typecheck OK, suite 34% with ZERO
  failures before external `Terminated` (NOT a test failure). Do not read that termination as
  a red build. To verify the full suite, either run it OUTSIDE the agent harness, or run the
  components separately (`make lint`, `make typecheck`, `make test`, `make examples`,
  `make docs-strict`, `make gate-tools`). Also: NEVER pipe a long build through `tail` in a
  background job -- `tail` buffers until EOF, so a kill leaves an EMPTY log. Redirect to a
  file and read the file.
  **HOW TO BRIEF THE CLOSE PANEL.** Review the SHIPPED CODE, not the plans -- the plans
  already had FOUR review rounds (11 -> 7 -> 4 -> 0 findings) and those decisions are
  executed. Give the panel the findings ALREADY KNOWN and tell it NOT to re-derive them; its
  budget is better spent on what is ADJACENT. This phase's defect classes, for aiming it:
  (a) CHECKS THAT COULD NOT FAIL -- four found and closed, three by the executors sabotaging
  their own controls; (b) A GUARD NARROWED FOR A TRANSIENT REASON (`D-IMPL-166`); (c) GATES
  NOBODY CONSULTED -- the wave-1 `artifacts/` bijection and a docstring path silently
  acquiring a coupling row. REVIEWER RELIABILITY ON THIS HOST: `codex` has reviewed NOTHING
  at exit 0 when its sandbox fails -- inline the source for it and check it actually read
  something; `gemini` has FABRICATED symbols. Verify EVERY finding against the tree with a
  `path:line` before recording it, and record rejected findings AS REJECTED.
---

# STATE — CCF SDK

## Project Reference

**Core value:** Whitepaper fidelity — every load-bearing primitive in
`docs/CCF_Whitepaper_1-2.md` realized in code with its contracts, invariants,
and composition properties. Priority order: fidelity → general-purposeness →
harness neutrality → adoptability. `/home/parkave/ccf_code/CLAUDE.md` (rev 4)
is canonical for phases, review protocol, invariants, and decision log.

**Current focus:** **PHASE 19 — The Client-Seam Integrity Checks Must Be Able to
Fail.** Phase 18.1 is COMPLETE and GATED (`D-GATE-18.1`, Dave, 2026-08-19).
Phase 19 is DISCUSSED (`19-CONTEXT.md`, 14 decisions) but NOT PLANNED. Phase 18 is
complete; its focus text is preserved below for continuity.

**Prior focus (Phase 18):** **MCP Transport: the second door and the
portability proof.** Opened 2026-08-17 by `D-IMPL-147` (Dave), on branch
`phase-18`. One plan, four tasks, ready to execute; nothing part-done.
**Read `.planning/HANDOFF-2026-08-17.md` for the cold-start picture** — it is
accurate on everything except its "RESUME HERE" section, which said the next
phase was undefined; it now is. That handoff supersedes
`HANDOFF-2026-08-16.md`, which carries a SUPERSEDED banner.

The design of record is unchanged and this phase adds none:
`docs/superpowers/specs/2026-08-15-ccf-client-design.md` plus its Amendment 1 —
specifically §6 (*"an adapter is official when it passes"*), §9 (the sync-only
ruling, whose named revisit trigger **is this adapter**), and Amendment 1 §A
(the `D-28` rollout: *"the MCP door is fixed to produce it in this phase"*).
The pause spec
(`docs/superpowers/specs/2026-08-16-reference-plan-factory-and-debt-scorer.md`
plus Amendment A) is DISCHARGED.

**Why this phase and not another:** the conformance suite was already written to
take a second subject and says so in its own docstring, and a single adapter
cannot falsify a claim about adapters — the cross-adapter comparisons currently
degenerate to self-comparisons. The three rejected candidates and their reasons
are in `D-IMPL-147`.

## Current Position

Phase: **20 — Client Access from Three Harnesses (ADK, Anthropic Agent SDK, LangGraph)**
  ADDED 2026-08-20 (Dave, `/gsd-phase`). **SCOPE CONFIRMED AND ALL FOUR OPEN QUESTIONS
  RULED, 2026-08-20 — NOT YET DISCUSSED, NOT PLANNED.** Ten Success Criteria are in the
  ROADMAP entry already, per `D-GATE-19`'s forward-binding ruling, and Dave ruled they are
  **the gate target and are NOT to be expanded during planning**.
  RULINGS (all four, locked before planning, recorded in the ROADMAP entry):
  (1) **CI determinism — adopt the `examples/external/00-hello-context` replay pattern.**
  Seed or replay so all three legs are CI-GREEN BY DEFAULT, `--live` opt-in for a real
  populated deployment. **"Unrun" is REJECTED** (CLAUDE.md §9). **A live populated
  deployment must NOT be a CI requirement.** This is the load-bearing one; the rest are
  layout and hygiene. (2) **One directory, three clients** —
  `examples/hw1-harness-clients/` or similar, exact name settled at discuss, ONE README
  stating the frame. (3) **Duplicates** — the Phase 16 orphans in
  `examples/s2-01-external-consumers/` are quarantined or removed (no runner, no README,
  no `make` target); the Phase 13.1 clients under `examples/external/00-hello-context/`
  stay as historical externals OR are clearly marked pre-Phase-17 surface; **Phase 20's
  trio is canonical going forward.** (4) **Requirement lane — continue `CLNT-NN`**, no new
  prefix.
  (5) **The replay harness is COPIED into the new directory, NOT SHARED with
  `examples/external/00-hello-context/`** (Dave, 2026-08-20, answering the residual point
  that rulings 1 and 3 touch the same file — Phase 20 inherits the RUNNER DESIGN, replay
  by default with `--live` opt-in, not a shared implementation contract with a
  retired-vintage example). Coupling a canonical example to one just marked historical
  means a change for either risks breaking the other, and **Phase 20 must not break when
  `00-hello-context` ages out or is quarantined**. Duplicating a small harness is cheap;
  shared ownership across "canonical now" and "historical" is not. `00-hello-context`
  keeps its own copy. SETTLED for discuss unless a strong counter-measurement appears.
  Next action: `/gsd:discuss-phase 20`, proceeding AGAINST these rulings rather than
  re-opening them. If any ruling turns out to affect SDK surface rather than example
  layout, that is a `D-IMPL-NN` and a STOP, not a quiet widening.

Phase: **19 — The Client-Seam Integrity Checks Must Be Able to Fail (INSERTED).**
  **EXECUTING** — started 2026-08-19 from `0fe0a22` on `main`. 8 plans in 6 waves.
  NO PHASE BRANCH: Dave ruled on 2026-08-19 that the work lands directly on `main`,
  as Phases 18 and 18.1 did — there are no SDK consumers, so `main` carrying un-gated
  phase work costs nothing, and history still permits carving a branch retroactively.
  Wave plan: 1 `19-01` -> 2 `19-02` -> 3 `19-04`+`19-05`+`19-06` (parallel, worktrees)
  -> 4 `19-03` -> 5 `19-07` -> 6 `19-08`. Only wave 3 uses worktree isolation; `19-08`
  edits `.planning/ROADMAP.md` and MUST stay on the main tree because the worktree
  cleanup path backs up and restores tracking files across the merge.
  `state.begin-phase` TRUNCATED THIS FILE 1046 -> 661 LINES at phase start
  (`D-IMPL-154`/`155` class, fourth distinct handler). Backed up, diffed, restored,
  hand-edited. Its counters were again structurally impossible (173 total / 184 done).

Phase: **18.1 — Simplify the MCP Example: Client-Side Access, Server Off-Stage.**
  INSERTED 2026-08-18 (Dave). **COMPLETE AND GATED — `D-GATE-18.1` APPROVED
  (Dave, 2026-08-19).** 5/5 plans plus a close-fix set; 3 blocking findings found
  by the panel and fixed in-phase, each independently re-sabotaged. `make ci-core`
  exit 0 at `04cccc2`, 3909/118/0. No merge required — the work landed on `main`. ROADMAP entry, Phases-list bullet and progress row all written
  BY HAND — `phase.insert` produced only a stub detail section, and no `state.*` or
  `roadmap.*` SDK writer has been run against either file.
  **A CLIENT-EXPERIENCE PHASE THAT SHIPS NO NEW SDK SURFACE.** Three changes:
  `CCF_BINDING` names a DEPLOYMENT rather than a script (server command declared in
  `binding.yaml` as data), `server/serve.py` is cut to a readable length into a second
  `server/` module, and the README states the frame — THE SAME CONTEXT PRODUCT REACHED
  A DIFFERENT WAY, why a server appears at all (the first example ran in-process and
  produced the product directly), and that HOW THE SERVER IS ASSEMBLED IS DELIBERATELY
  OUT OF SCOPE until the Context Product assembly examples.
  THE FINDING: the spawn itself is inherent to MCP stdio and is NOT the defect; the
  defect is that it is the client's business in the reader's field of view.
  WITHDRAWN SAME-DAY: an earlier draft shipping `mcp+http` as a third adapter — SDK
  transport work inside a deliberately client-side phase, which Phase 19 would have
  rewritten. Independent of Phase 19 either way.
  **DISCUSSED 2026-08-18** — `18.1-CONTEXT.md` + `18.1-DISCUSSION-LOG.md` committed at
  `60f2bd3` on `main`; no phase branch, no plan, nothing executed. Seventeen decisions
  (`D-01`..`D-17`) plus one documentation constraint `C-1`.
  **ONE MORNING RULING WAS REOPENED BY DAVE AND REVERSED:** the server does **NOT** move
  into the deployment root. `server/` STAYS A SIBLING of `deployment/` at the example top
  level, and `binding.yaml`'s `server:` key resolves against the deployment root's
  **parent** — no `..`, absolute paths and symlink escapes still refused, so containment is
  enforced against a declared base rather than holed. Consequence: **`D-IMPL-141` A.3 needs
  no amendment and `assert_one_python_module` needs no rewrite** — both drop out of the
  phase, which is strictly less mechanism than the reversed ruling. Dave's reason:
  *"Server is temporary in this specific example because it is not the focus"*, and in
  practice a server is on another machine.
  **`C-1`, A CONSTRAINT ON THE WRITING:** *"Make sure not to generalize the documentation
  that servers will always be in deployment — they will not."* A sentence implying
  otherwise is a defect in this phase's own terms, in the README, `binding.yaml`'s header
  and `serve.py`'s docstring alike.
  Also settled: one-token `mcp+stdio:<root>` address with a named migration branch for the
  old two-token form and a targeted refusal when the token is a file; the adapter (not the
  loader) refuses a missing `server:` key, because the loader cannot know which transport
  is asking; `serve.py` keeps the door and a second `server/` module takes the composition;
  **no line budget** — the criterion is structural, one file one concern; the README's
  obsolete two-token paragraph is deleted for one sentence on the one-word difference.
  DEFERRED to the assembly examples: Dave's `client/` + `server/` top-level restructure.
  **PLANNED 2026-08-18.** Five plans, five waves, deliberately linear:
  `18.1-01` clears the pre-existing red and lands `server:` as a contained data key;
  `18.1-02` flips the grammar to one token across every site IN ONE COMMIT (the
  README↔Makefile character-identity gate forces it) and adds the four refusal controls;
  `18.1-03` cuts `serve.py` into `server/compose.py`; `18.1-04` writes the README frame,
  the surface fragment and the `D-IMPL-153` entry, and carries the `C-1`
  **`checkpoint:human-verify`** (`autonomous: false`); `18.1-05` re-sweeps after the last
  SUMMARY.
  **TWO RULINGS TAKEN AT PLANNING, `D-18` AND `D-19`** — see `18.1-CONTEXT.md`. `D-18`
  means **THE PHASE NO LONGER SHIPS ZERO NEW SDK SURFACE**: it ships ~4 lines of it on
  purpose, and the ROADMAP sentence plus the surface fragment must say so or a reviewer
  reads it as scope creep.
  **KNOWN AND DISPOSITIONED, NOT TO BE REDISCOVERED:** `make ci-core` is knowingly red
  from `18.1-03` to `18.1-05` (the `D-13` docstring trim moves the `serve.py:68` coupling
  row), and `test_the_committed_report_is_current` may also go stale on planning-tree rows
  THIS PHASE'S OWN SUMMARYs add. Both plans carry the diff-classification procedure: every
  changed row must be a `.planning/phases/18.1-*` row, anything else is a real regression.
  **TWO SUCCESS CRITERIA ARE REVIEW-ONLY, BY DESIGN:** `C-1` (documentation must not
  generalize that servers live in the deployment) and "is `serve.py` readable now" —
  `D-12` declines a line budget on purpose, and ~30% of that file is prose about itself,
  which moving composition out cannot shrink. Neither is machine-checkable and no proxy
  gate was invented for them.
  Next action: `/clear` then `/gsd:execute-phase 18.1`.

Phase: **19 — The Client-Seam Integrity Checks Must Be Able to Fail.** DISCUSSED,
  NOT PLANNED. `19-CONTEXT.md` + `19-DISCUSSION-LOG.md` committed at `90f9822` on
  `main`; no phase branch, no plan, nothing executed. Carries Phase 18's `B0` as an
  OPEN BLOCKING DEFECT (`D-IMPL-151`), explicitly reserved out of `D-GATE-18` and
  **not** accepted risk.
  WHAT IT FIXES, MEASURED IN-TREE RATHER THAN QUOTED: `DoorOutcome` carries no
  request identity (`src/ccf/products/door.py::DoorOutcome`), so both adapters fill `WireOutcome.request`
  from the object they were handed (`src/ccf/client/adapters/mcp_stdio.py::McpStdioAdapter`,
  `src/ccf/client/adapters/inprocess.py::InProcessAdapter`)
  and `src/ccf/client/client.py::ask` passes that SAME object as `sent` — `outcome.request != sent`
  is an object compared with itself. `content_address` is `sha256` of the very text
  the adapter passes on, so `verify_content_address` is `sha256(x) != sha256(x)`.
  `decode_outcome`, the one path reading both off sender-produced bytes, has NO
  SHIPPED CALL SITE.
  THE SHAPE OF THE FIX (14 decisions, `C-01`..`C-14`, in `19-CONTEXT.md`): the door
  re-states the question it resolved; the adapter seam becomes
  `ask(WireRequest) -> bytes` (AMENDS `D-11` AND `CLNT-05` — a `D-IMPL` entry is
  owed); the request is serialized too so the check is live in-process; the
  conformance suite gains generic tamper legs. Signing is OUT of scope; the restored
  claim is NON-ADVERSARIAL integrity and `D-GATE-18`'s prose constraint is replaced
  by a narrower true sentence, not lifted.
  Next action: `/clear` then `/gsd:plan-phase 19`.

Phase: **18 — MCP Transport.** EXECUTION COMPLETE (plan `17-10`, 4/4 tasks), §3.1
  CLOSE PROTOCOL DISCHARGED (cross-AI panel + depth pass in `18-CLOSE-REVIEWS.md`
  and `18-REVIEW.md`, every finding verified against the tree, four blocking
  findings closed in-phase, one — `B0` — deferred to Phase 19 as an OPEN BLOCKING
  DEFECT under `D-IMPL-151`). All four gates green at `a7264e3`: `ci-core` 3871
  passed / 118 skipped / 0 failed, `conformance` 67, `docs-strict` 0,
  `gate-tools` 400+154. **CLOSED, GATED AND MERGED** — `D-GATE-18` (Dave,
  2026-08-17); `phase-18` merged `--no-ff` into `main` at `e57c93c`, the merge
  commit referencing the gate. Merged `main` re-verified independently: all four
  gates exit 0, identical counts, so the merge introduced nothing.
  **`main` IS NOT PUSHED — 41 commits ahead of `origin/main`.** Pushing was not
  ruled and is Dave's call, as is the Actions run on `e57c93c` (no CI token in
  session; `~/ci_diag2.py` closes that loop).
  **THE GATE'S RESERVATION TRAVELS WITH THE MERGE:** it approves the portability
  claim and NOT a tamper-detection claim. `B0` — both client-seam integrity
  checks structurally unable to fail, because the adapters reconstruct the
  request echo instead of reading it off the wire — is an OPEN BLOCKING DEFECT
  carried to **Phase 19** by `D-IMPL-151`. Until Phase 19 lands, the SDK must not
  be described as detecting a transport that answered a different question, or a
  vessel altered in transit. Ten advisories also ride forward unclosed, `A5`
  among them: stdio auth is impersonation, not verification. The
  ROADMAP checkbox reads `[x]` and its row reads `1/1 — Complete`; that is
  accurate about PLANS ONLY and must not be read as a gate. Dave ruled the
  checkbox may stay (2026-08-17) provided this not-gated state stays explicit
  here. **CORRECTED 2026-08-17 (Phase 19 discuss):** the paragraph that stood
  here listed the §3.1 close protocol as *still owed* — the `D-IMPL-149` suite
  split, the cross-AI panel on shipped code, the single-agent review, finding
  verification, triage and Dave's ruling. **All of it has since been discharged**
  and is recorded in `18-CLOSE-REVIEWS.md`, `18-REVIEW.md` and `D-GATE-18`; the
  text was stale rather than wrong when written. Phase 18 IS closed and gated —
  what does not travel with the gate is the tamper-detection claim, which is
  Phase 19's job.
  Branch `phase-18`, cut
  from `main` @ `b32348f`. Plan:
  `.planning/phases/18-mcp-transport-the-second-door-and-the-portability-proof/17-10-PLAN.md`
  — the `17-10` name inside the phase-18 directory is **deliberate**; see
  `D-IMPL-147` and the banner in the file. Do not renumber it.
  Next action: none — Phase 18 is merged. See Phase 19 below.

Phase: 17 — Client Access. **CLOSED, GATED (D-GATE-17) AND MERGED TO `main`.**
  12 of 14 plans executed — 17-01…17-07, the mid-phase 17-03b Dave ruled in,
  17-11/-12/-13 (the pause), and 17-09 (the client example).
  `main` @ **`b32348f`**, pushed, clean. `phase-17` @ `44b1f75`, retained per
  CLAUDE.md §2.2.
  MERGED ONLY AFTER A GREEN ACTIONS RUN ON THE COMMIT ACTUALLY MERGED — run
  31995656672 @ `44b1f758`, all four jobs — which was Dave's condition.
  The merged `main` was then re-verified INDEPENDENTLY rather than inheriting
  the branch's result: `ci-quick-suite` 0 — 3739 passed / 0 failed / 2 skipped /
  172 deselected; `gate-tools` 0; lints 0; docs-strict 0; typecheck 0 (209
  files). Exit codes captured and BRANCHED ON, never through a pipe.
17-08 (the s1-00/s1-01 removal) and 17-10 (the MCP door + adapter):
  **DEFERRED OUT OF PHASE 17 by D-IMPL-146.** Not outstanding — both plan files
  carry a DEFERRED banner so an execute-phase run cannot pick them up. They move
  together to a later phase, where 17-08's blocker also gets its real fix (a
  producer-side example demonstrating `refuse_request` — see D-IMPL-146).

WHAT 17-09 SHIPPED, the artifact the phase was opened to produce:
  `examples/hw1-companies-over-revenue/` — `consume.py` at **78 lines** importing
  only stdlib, `ccf.client` and the adapter, beside an opaque `deployment/`
  holding **exactly ONE Python module** (`projection.py`) and three data files.
  Zero credentials. Against a populated deployment it prints the answer, the
  context debt, the content address, the replay reference and the expiry — and
  the address is stable across runs while `D_c` moves with the boundary, so the
  debt is measured rather than decorative. This is the direct answer to Dave's
  Phase 16 verdict on a 722-line example whose consumer imported the producer's
  `deployment.MANIFEST`.
Phase 16: STOPPED 2026-08-15, not gated. Post-mortem
  `.planning/HANDOFF-2026-08-15.md`. Its CI has been red for some time — the
  docs-gate half is diagnosed (stale retirement report, already fixed on
  phase-17); the tests half (exit 2 in ~45s, collection-error territory) is NOT.

WHAT THE PAUSE DELIVERED (2026-08-16, all three merged with SUMMARYs committed):
  17-11 `~ccf.products.debt_scorer.AssemblyDebtScorer` — the reference
    GraphView -> DebtAssessment adapter, row-selection choice STATED at the seam
    (rows that SURVIVED being read, with reason, consequence and override path).
    Plus `DeclaredFactor`, because the SDK has no measurement for C or S and a
    declared assumption must be distinguishable from a measurement in replay.
    11 sabotage controls, all observed failing.
  17-12 `binding.yaml` is DATA plus exactly ONE `module:attribute` reference.
    TWO refusal checks, because one would have been a precedent: `RULED_OUT_KEYS`
    refuses `resolver:`/`connection_factory:` BY NAME, and `looks_like_a_reference`
    refuses a reference-shaped value in ANY data position (key-name refusal cannot
    see one smuggled through `question.subject`). `REFERENCE_KEYS` is a
    one-element tuple ASSERTED to be one element. The fixture's 295-line
    `resolver.py` (five responsibilities) became a 127-line `projection.py` (one).
    D-IMPL-141 rewritten as RESOLVED.
  17-13 The reference scorer is the DEFAULT — in a HELPER,
    `~ccf.products.resolver.build_governed_resolver`, NOT on the class. Two
    measurements decided it: defaulting on the class would have grown
    GovernedResolver from 13 arguments to 17 (a default that enlarges its own
    seam is not a default), and a SHIPPED assertion
    (`test_no_constructor_argument_carries_a_default`) would have had to be
    weakened — this phase's signature defect, in the plan whose subject is
    inert defaults. Proven USED by EFFECT twice: the ScorerPins on a SERVED
    product, and two deployments differing in NOTHING but their λ_c table
    producing different freshness figures. A pin is a claim; a number that moves
    with its input is a measurement.
  THE ANSWER TO "what does defaulting mean when two of three factors are
    irreducibly the deployment's": THE DEFAULT IS THE MACHINERY, NEVER THE
    VALUES. 17-12's `debt:` block survives intact, all four fields, because none
    of the four is something a default may supply.

CI IS GREEN — CLOSED 2026-08-16. Run 31974549984 @ `763c846`:
  **completed / success, ALL FOUR JOBS** (examples suite, docs gate, lint +
  strict types, tests python 3.12). This is the FIRST fully green run this
  branch has ever had, and the first time the tests job ran to completion at
  all. What executed for the first time in the project's history: the quick
  suite (3695 tests), harness adapter conformance, and the FOUR SUBSTRATE LEGS
  (Postgres, Neo4j, Mongo, Fluree) plus coverage. They genuinely RAN rather
  than skipping — the job sets CCF_REQUIRE_POSTGRES/NEO4J/MONGO/FLUREE/
  HARNESSES, each of which turns a skip into a failure, so a green job with
  those set is positive evidence the legs hit real substrates.
  THE PIPELINE AND THE LOCAL GATE NOW AGREE, which is the property the
  hold-waves-6-7 ordering rule existed to protect.

  HOW IT GOT THERE, two fixes on top of the pause work:
  (a) D-IMPL-143 — `ci.yml` invoked a bare `pytest` while every Makefile target
      invokes `python -m pytest`; the `-m` form puts the cwd on sys.path and the
      console script does not. `tests/` has no top-level __init__.py, so pytest
      inserted each test file's own directory rather than the repo root and 13
      modules failed to collect. Red since at least 2026-08-10, never diagnosed,
      because every local reproduction ran through `make`. All seven pytest
      steps now CALL Makefile targets instead of restating them.
  (b) `763c846` — the frozen-baseline provenance test could NEVER pass in CI:
      actions/checkout defaults to fetch-depth 1, and a shallow clone's grafted
      root appears to introduce every file, so `git log -- <baseline>` returns
      HEAD's own subject. It now asks `git rev-parse --is-shallow-repository`.
      Latent for months, invisible because the job died at collection first.

NEEDS DAVE, NOT THE SESSION:
  (1) WHETHER TO START WAVES 6 AND 7. The 2026-08-16 spec closure unblocked
      them and the CI condition Dave set ("once we have a clear CI signal,
      green or a concrete failure log, we start wave 6") is now MET. The
      session did not start them. 17-08 and 17-09 are both checkpoint plans
      (autonomous: false), so they need Dave in the loop by construction.
  (3) RULED 2026-08-16 — D-IMPL-142. The three new public names are KEPT, all
      three, with reasons recorded: `DeclaredFactor` (mechanism that makes a
      declared factor auditable in replay), `build_governed_resolver` (the
      helper is the right place for defaults, not the class) and
      `DEBT_SCORER_INPUTS` (naming required inputs beats leaving them implicit).
      Dave also ratified the discipline: claiming them in surface-change
      fragments rather than shipping them silently is correct. NO REVERSALS.

RULED 2026-08-16 ON SEQUENCING (D-IMPL-142): waves 6 and 7 are unblocked by the
  spec's closure but HELD pending a clear phase-17 CI signal — "starting the
  deletion/quarantine waves while we still don't know whether the always-on
  pipeline agrees with the local gate is the wrong order." Once CI reports
  (green, or a concrete failure log), wave 6 starts.

CI STATE, corrected and current. An earlier claim in this session that the
  branch was "~180 commits ahead of the last push Actions saw" and that
  "nothing since 8e95139 is pushed" WAS WRONG — origin/phase-17 was at a11d097,
  which is 5 commits AHEAD of 8e95139, and only 24 commits were unpushed.
  `phase-17` HAS NOW BEEN PUSHED at `5e6f55e` (a11d097..5e6f55e, exit 0, zero
  unpushed) under Dave's authorization, so Actions is running against the tree
  that contains all three plans rather than one that predates them. main
  untouched. WHAT THE SESSION CANNOT DO, measured rather than assumed: no `gh`
  CLI, no token in the environment, none in homecams' .env. SSH auth to GitHub
  WORKS (so push and fetch are available) but SSH speaks only the git protocol —
  Actions status is a REST API needing a token. `~/ci_diag.py` exists, is
  read-only stdlib, and takes a token as argv[1]; the token needs TWO separate
  grants (repository access -> ccf_code, AND Repository permissions -> Actions:
  Read-only) and granting the first does not imply the second. SECURITY: do NOT
  paste a PAT into a session transcript — three were pasted on 2026-08-10 and
  still need revoking at github.com/settings/personal-access-tokens. Run
  ci_diag.py in a shell outside the session and paste only its OUTPUT.

WHAT CLOSED 2026-08-15, both verified by the orchestrator rather than relayed:
  (1) PROPERTY-NOT-SHAPE GATING — `phase-16` was red with 18 failures and no
      defective example. `tests/examples/test_spine_separation.py` hard-coded four
      example filenames; `tests/products/test_gate_two_call_shape.py` demanded a
      binder call whose premise HW-1 does not satisfy, and had NO compliant state
      for it — it demanded the call, and property (1) would have refused that same
      call as a tautology. Both rewritten to assert the properties their docstrings
      claim. 18 -> 0 with NO example modified, which was the whole thesis: HW-1
      already held every property both gates claimed to prove. D-IMPL-137 rules the
      binder demand conditioned on its premise, detected as a CONJUNCTION of the
      Control Plane (is `ccf.projection-requirements` registered) and the AST (does
      the code read one source), fail-closed in three places, ceilinged at ONE
      exempt deployment with no headroom.
  (2) THE SINGLE-FILE FORM — plans 16-27 … 16-31. `ccf_config.yaml` is now the SOLE
      DOCUMENTED authoring surface (D-IMPL-136 AMENDMENT); the multi-file loader is
      RETAINED INDEFINITELY and no other example converts — there is still NO BULK
      MIGRATION. HW-1 went from 10 config files / 99 non-comment lines to 2 files /
      48 lines, `manifest.yaml`'s 46-line index of itself deleted outright. THE
      CONTENT ADDRESS DID NOT MOVE (5cfee793…, before and after), which is the proof
      the conversion changed nothing but the file count. D-IMPL-139 accepts 48
      against the spec's ~30 target with the gap accounted line by line.

LESSON THAT GENERALIZES, and it held across both bodies of work: EVERY defect found
  was in the VERIFICATION or in the PLANS, never in the mechanism. The gate work
  shipped five defects of its own — a guard that never fired, a test asserting its
  helpers instead of its subject, a control that could not reach its own case, a
  property asserted in four places and controlled in none, and one sentence wrong
  three distinct ways across five attempts. The config plans carried a stale
  19-failure baseline that FOUR consecutive executors disputed correctly, two file
  inventories that omitted files their own gates then demanded, and two defects in
  a plan the orchestrator wrote (an unverified `tenant_id: absent` claim that was
  false, and a `do not touch produce.py` instruction when produce.py holds the boot
  call). The instruction that earned its keep: tell every executor to EXPECT its
  plan to be wrong and to dispute with a measurement rather than route around.

STATE-HANDLER WARNING STANDS: every `state.*` and `roadmap.*` writer has corrupted
  this file — FIVE confirmed instances, whether they report success or failure.
  This entry was hand-edited after an audit that counted SUMMARY files per phase
  (161 complete) and PLAN files with no SUMMARY (14 outstanding). Note SUMMARYs can
  EXCEED PLANs — 15.1 has 20 summaries against 10 plan files, because 15.1-11 …
  15.1-20 were planned and executed mid-phase during review rounds without a
  persisted PLAN file. So SUMMARY count is the reliable "completed" signal and a
  PLAN with no SUMMARY is the reliable "outstanding" one.

    PRIOR POSITION (15.5, retained for the reasoning below):
  merge `phase-16` → `main` with `--no-ff`, then `/gsd:plan-phase 15.6`.
  PHASE 15.6 RULED IN (Dave, 2026-08-11), BEFORE Phase 16 resumes: two explicit
  tracks — A closes the five carried defects (API-neutral), B closes D-IMPL-112's
  three named gaps (API-affecting; Observation gains identity, DebtAssessment
  gains evidence pointers, and the product content address moves a THIRD time).
  Gap 1 gets a RESEARCH SPIKE FIRST in the 15.5-01 shape. Scope B to the three
  gaps, not to the open question. D-IMPL-117 (Dave): SURFACE IMPACT IS ACCEPTED
  — the address move is an authorized cost, not a risk to design around — and
  Track B ships CARRYING MECHANISM, not judgement: the context product creator
  owns what a client needs, the SDK owes only the data structure and the API to
  populate and extract it. THE SPIKE'S PRIMARY QUESTION is therefore not 'can we
  avoid the address move' but 'are these fixed fields on the vessel, or declared
  content in the payload-schema shape?' — D-IMPL-97 puts governance in fixed
  structure and domain content in a declared schema, and debt evidence sits
  across that line. The branch carries BOTH
  15.5's 15 plans AND Phase 16's completed 6 — they share the branch by design
  (forked from main @ 06fea5c per CLAUDE.md §2.2, merge at the gate not before).
  Then re-read Phase 16's 15 remaining plans BEFORE resuming: the ones
  documenting the product contract and the delivery doors describe a surface
  that no longer exists. Resume Phase 16 at 7/21 against the corrected surface.
Status: Phase 15.6 COMPLETE and gated (D-GATE-15.6, Dave, 2026-08-13) — 13 plans,
  97 commits, gate observed at HEAD a95a038 (make ci exit 0, 3086 passed / 81
  skipped). Branch `phase-15.6` is NOT pushed and NOT merged; the --no-ff merge to
  `main` is the next action. Phase 15.5 is COMPLETE and gated (D-GATE-15.5, merged
  to main @ 29e1568). Phase 16 remains PARKED at 6/21.
  PRIOR STATUS (15.6 planning, retained for the reasoning below):
  Phase 15.6 PLANNED — ready to execute.
  Branch `phase-15.6` (cut from main @ f8fe3dd per CLAUDE.md §2.2; merge at the
  gate, not before; NOT pushed). Do NOT resume Phase 16 until 15.6 lands — 15.6
  moves the product content address a THIRD time, and moving it after ten
  examples exist regenerates ten while moving it now regenerates one. Phase 16
  has already been invalidated once by exactly this.
  PRIOR STATUS (15.5 planning, retained for the reasoning below):
  WHY 15.5 EXISTS: Dave's 2026-08-10 review of `examples/s1-01-hello-context-product`
  — *"today I would put an MCP server in front of the fluree database and run a
  query and return the results. What is the benefit of using CCF?"* Measured behind
  that: three of §6.3's NINE elements (freshness SLA, discovery, addressability)
  unimplemented while `contract.py` claims they live on `RegisteredProductClass`;
  `register_product_class` takes no payload schema so `payload` is an unchecked
  dict; `DebtAssessment` computed by `ccf.halflife.debt` and delivered nowhere;
  `Perspective` passed into `execute()` by the caller with nothing deriving it from
  the verified grant, and `build_egress_server` binding no authenticator at all.
  RULINGS RECORDED: `D-IMPL-95` (systems of record read-only to L1; CCF's graph is
  CCF-owned on the same substrate), `D-IMPL-96` (revokes "no fabric changed",
  withdrawing D-13, D-14 and 16-19's gate_16.py allowlist), `D-IMPL-97` (the vessel
  model + the assembler Protocol implemented by a declared agent; a WORDING
  correction to whitepaper §7.6, explicitly not a reversal). Dave separately ruled
  entitlement requires a fabric change. Numbering continues from `D-IMPL-98`.
  TWO STANDING RULINGS THE PHASE IMPLEMENTS RATHER THAN DECIDES, found by research
  and easy to re-litigate by accident: `D-IMPL-30` already resolved the contract
  element count as NINE (Assembly Mode included) and says every "eight" reference —
  CLAUDE.md §5's included — is editorial drift; `D-IMPL-31` already ruled the
  mixing-refusal rule (`expires_at = min(class MAX_TTL ceiling, derivation over
  constituent signal validities)` with constituent-validity floors that refuse
  assembly). Criterion 8 implements it; do not re-open either.
  THE HARD CONSTRAINT ON THE DEBT TRACK: `src/ccf/replay/engine.py::replay` raises
  `ReplayDivergence` when the rehydrated product's content address differs from the
  recorded one, and `ProjectionOutput` carries only `plan_id` and `payload`. Any
  field added to `ContextProductContract` must be reconstructible from the record,
  the class, or the projection output — debt is none of them, so debt-on-the-
  product-only breaks every replay. Plan 15.5-01 measures all four placements
  against the real tripwire BEFORE 15.5-05 asks Dave to choose.
  EIGHT OPEN QUESTIONS reach 15.5-05 unruled, enumerated with options and
  consequences in `docs/CONTEXT_PRODUCT_REVISION.md` §9-§10 and in the plan. Q1
  (typed per-class request contract) gates the most — it collapses the fixed-subject
  and fixed-instant defects into one design. Q3 (debt placement) and Q7 (whether
  entitlement makes debt per-principal, or dissolves the coupling entirely) gate the
  debt track. 15.5-05 presents all eight with a MEASURED COST column and recommends
  nothing.
  PLAN-CHECKER FOUND 3 BLOCKERS + 8 WARNINGS; all fixed at `6755fa8`, and all three
  blockers were verified against the tree before being acted on. B1: criterion 4
  says "every exposed door" but the plans missed
  `runtime/ccf_runtime/mcp/experience.py::build_experience_server`, the EXTERNAL front door serving
  `context_product(tenant, product_class, version)` — a phase whose founding
  complaint is "an MCP server in front of a database" was about to ship its own MCP
  front door ungated. Now covered, and the invariant test asserts its three-door
  table is EXHAUSTIVE over runtime's product-serving handlers, so a fourth door
  fails the suite. B2: `build_egress_server(*, server_name, resolver)` binds no
  `token_verifier` — while `runtime/ccf_runtime/mcp/experience.py::build_experience_server` passes one INTO the FastMCP
  constructor, so it cannot be retrofitted — meaning plan 06's entitlement check had
  no verified grant to key off and its threat model's "Bearer-token-authenticated"
  was false. Now a third required seam, with a behavioural acceptance criterion (a
  tokenless call against a recording entitlement source must leave the recorder
  empty) because a source-order assertion would pass against a server whose
  middleware was never installed. B3: plan 01's spike asserted tree-derived counts
  inside `testpaths=["tests"]`, which `make ci-core` must keep green from wave 1 —
  over counts eight later plans change, with no owner. Now asserts only facts no
  plan is scoped to change; 15.5-14 owns its retirement.
Progress: [###░░░░░░░] 15.5 planned 0/14 · Phase 16 at 6/21, parked
  OPEN, CI — FIRST CONTACT AFTER 826 UNPUSHED COMMITS. Pushing `phase-16` on
  2026-08-10 was the first time Phases 9-15.4 ever ran in GitHub Actions. Run
  31452318023 @ a328a1b9: 3 of 4 jobs GREEN (examples suite, lint+strict types,
  docs gate). The `tests (python 3.12)` job fails at the step **"Quick suite (no
  external substrates)"**. NOT YET DIAGNOSED — and note it does NOT reproduce
  locally: that exact command passed here twice, 2464 passed / 2 skipped, both with
  `CCF_REQUIRE_HARNESSES=1` alone and with CI's FULL substrate env
  (CCF_TEST_POSTGRES_DSN / NEO4J_URI / MONGO_URI / FLUREE_URL plus all four
  CCF_REQUIRE_*). Ruled out: harness-required flag turning skips into failures; the
  `ccf-demo-adapter` entry point (installed here too, exposing backend `demo`).
  Remaining candidates: a fresh `pip install -e ".[dev,neo4j,mongo]"` resolving
  different versions than this venv, or a test that behaves differently when the
  four service containers are actually REACHABLE (CI has them; this box does not).
  NEXT STEP: read the log. `~/ci_diag.py <token>` prints the run, the failing step
  and the log tail; it now strips the Authorization header on GitHub's redirect to
  Azure blob storage, which was the 401 that blocked the log fetch. The token needs
  BOTH repository access (Only select repositories -> ccf_code) AND Repository
  permissions -> Actions: Read-only; they are separate sections and granting the
  first does not imply the second.
  SECURITY: three fine-grained PATs were pasted into the 2026-08-10 session
  transcript. REVOKE ALL THREE at github.com/settings/personal-access-tokens.
  OPEN, 16-02 (2/3): MongoDB, Neo4j and PostgreSQL on the DGX all carry 16
  relationships with `ownershipPercent` on 9 EDGES (verified by direct query after
  two out-of-tree loader patches; backups under
  `/home/parkave/fluree/examples/fibo/.backups/`). FLUREE REMAINS UNLOADED at 4 of 9
  ownership pairs — there is no Fluree loader in that harness and it is NOT a
  missing line: RDF has nowhere to hang a qualifier on a triple, which is exactly
  why the source modelled ownershipPercent on the Party and every chain was one hop.
  CCF's own adapter solves it with the interposed-edge layout (`fluree_write.py`,
  15.3 §R5). Dave has not ruled write / leave / defer.
  OPEN, 16-05 (2/3): a human-verify gate on the spine/deployment split. Superseded
  in practice by 15.5 — do not close it until the vessel work lands, since the
  example's shape is what changes.
  MEASURED, do not re-derive: the example's own algorithm is 125 executable lines
  against 189 of spine choreography and 74 of wiring, and 55 of those 74 exist only
  to satisfy `DeploymentBinding` — a Protocol the example invented, calls "the
  adoption checklist", and CCF does not ship. All eight examples call
  `load_and_boot` identically; seven differ only in a filename. Timings (not
  regression-gated): boot 74.3 ms once per process; projection execute 8.68 ms per
  question; the replay append that gates delivery 0.29 ms; full example 347 ms — so
  a second question in a live service is ~10 ms, not 347.

## Performance Metrics

- Phases complete and gated: 8/8 — Phase I closed (D-GATE-I, 2026-07-31); v0.1.0 declared
- Requirements delivered: 31/46 mapped to gated phases — RSCH-01..04, DSGN-01..04,
  FEAS-01..04, FABR-01..09, CINV-01..04, AGNT-01..03, XPRC-01..03. **CINV-04 is
  partial**: two deferral skips (`hitl-action-capture`, `workflow-trace-capture`)
  remain active and are Phase 7's to flip.

- D-GATE entries logged: 6 (D-GATE-R, D-GATE-D, D-GATE-F, D-GATE-I.1, D-GATE-I.2, D-GATE-I.3)
- Test baseline on `main`: 987 passed / 2 skipped, mypy --strict clean (99 files), `tools.lints --all` exit 0

| Phase-Plan | Duration | Tasks | Files |
| ---------- | -------- | ----- | ----- |
| 04-01      | ~12 min  | 3     | 10    |
| 04-02      | ~20 min  | 3     | 14    |
| 04-03      | ~25 min  | 3     | 13    |
| 04-04      | ~35 min  | 3     | 16    |
| 04-05      | ~50 min  | 3     | 24    |
| 05-01      | ~35 min  | 3     | 16    |
| 05-02      | ~10 min  | 3     | 12    |
| 05-05      | ~6 min   | 1     | 7     |
| 05-06      | ~12 min  | 2     | 20    |
| 05-07      | ~8 min   | 2     | 3     |
| 07-01      | ~15 min  | 3     | 2     |
| 07-14      | 2 sess.  | 3     | 12    |
| 08-01      | ~10 min  | 2     | 4     |
| 08-02      | ~12 min  | 2     | 8     |
| Phase 08 P03 | ~15 min | 3 tasks | 6 files |
| Phase 08 P04 | 20min | 2 tasks | 6 files |
| 08-09      | ~10 min  | 2     | 8     |
| 08-10      | ~18 min  | 2     | 11    |
| 08-12      | ~12 min  | 2     | 4     |
| 08-13      | ~50 min  | 4     | 5     |

## Accumulated Context

### Roadmap Evolution

- Phase 13.1 inserted after Phase 13: External-Consumer Examples (MCP Egress): independent-harness agents consume CCF via MCP, zero client-side CCF imports — primary adoption path, demonstrated not asserted (Dave, 2026-08-02) (URGENT)
- Phase 13.2 inserted after Phase 13: external-example-hardening — post-execution cross-AI review re-checks for 13.1 (fixtures vs live SDK traffic, LLM tool-surface narrowing, byte-path probe, clean-runner install, .mcp.json verification) (URGENT)
- Phase 13.3 inserted after Phase 13: Review-Residual Hardening (URGENT)
- Phase 15.2 inserted after Phase 15.1: Substrate adapters and query pushdown; tiers 1+2 in scope, tier 3 designed-for
- Phase 16 edited 2026-08-09: status, goal, requirements, success_criteria — scope expanded to four sections (Phase 16 ships 1–3, Section 4 → Phase 17) per 16-CONTEXT.md D-01..D-12; ten Success Criteria added where the entry previously had none
- Phase 18.1 inserted after Phase 18: Simplify the MCP Example — Client-Side Access, Server Off-Stage. Client-experience scope, no new SDK surface: binding names the deployment, `serve.py` slimmed, README frames it as the same Context Product reached a different way with assembly deliberately out of scope. An `mcp+http`-adapter draft was written and withdrawn the same day as SDK work in an example's clothes (Dave, 2026-08-18) (URGENT)
- Phase 20 added after Phase 19 (`/gsd-phase`, Dave, 2026-08-20): Client Access from Three Harnesses — ADK, Anthropic Agent SDK and LangGraph agents reaching one Context Product over the Phase 18.1 MCP door, each printing it to the console. Continuation of the client-side arc; **no new SDK mechanism** (no transport, no adapter, no `ccf.client` change) and server assembly stays off-stage. Roadmap entry, Phases-list bullet and progress row all written BY HAND — `phase.add` produced only a stub detail section appended AFTER `## Coverage`, with no Phases-list bullet and no progress row (`D-IMPL-154`/`155` class, fifth distinct handler). Backed up and diffed: three pure insertions, zero deletions. **Ten Success Criteria authored ONE PER UNWRAPPED LINE BEFORE execution per `D-GATE-19`**; `roadmap.get-phase 20` confirmed parsed count = 10. Four open questions are named in the entry rather than decided by default (CI determinism for the three legs, one directory or three, the fate of the pre-17 and Phase-16-orphan duplicates, and the requirement lane). **ALL FOUR RULED BY DAVE THE SAME DAY, BEFORE PLANNING** — replay pattern with CI-green-by-default and no populated-deployment requirement; one directory with one README; orphans quarantined or removed and the 13.1 clients marked pre-Phase-17; `CLNT-NN` continues. Scope closed at the three clients; the ten criteria are the gate target and are not to be expanded during planning.

### Decisions

- CLAUDE.md is canonical; GSD phases map 1:1 to R/D/F/I (I sliced into I.1–I.5)
- Monorepo at `github.com/drcastillo/ccf_code` (provisional D-IMPL-10)
- Phase branches per CLAUDE.md §2.2 (`phase-r`, `phase-d`, `phase-f`, `phase-i1`..`phase-i5`); merge to `main` only at D-GATE
- Model mandates: Fable 5 high effort (Phases 1–3 / R, D, F); Opus 5 or Opus 4.8 high effort (Phases 4–8 / I)
- [Phase 02]: Entry ownership: single primary owner per INV key from pillar mapping; dual-pillar entries get See-also, never two owners
- [Phase 02]: Phase 2 planning docs carried from phase-r onto phase-d (Rule 3 — required for plan execution; planning metadata only)
- [Phase 02]: Batch 1 rulings (Dave, 2026-07-25, all AS RECOMMENDED): D-IMPL-01 Python 3.12+ sole target; 02 GraphStore Protocol + Postgres/SQLite; 03 SimilarityIndex + sqlite-vec; 04 ccf + ccf-runtime packages, async-first runtime/sync core; 05 multi-tenant first-class; 07 EmbedderProtocol; 08 Pattern-5 stage Protocols + reference pipeline; 09 LLMClientProtocol + Anthropic Citations adapter; 33 SignalEnvelope superset; 34 six-semantics storage Protocol w/ reader-writer split; 35 EntityResolutionStrategy Protocol; 37 boot-time register(); 38 OperatorParameterSet, no silent defaults; 39 MAX_TTL per class in Control Plane; 40 CAR scale/thresholds in Control Plane; 41 four-layer single-writer stack
- [Phase 02]: Batch 3 rulings (Dave, 2026-07-25, zero provisionals — marathon complete 49/49): 18 AS RECOMMENDED — D-IMPL-26 hybrid content-hash + versioned-URI addressing; 06 logical snapshots + touched-substate manifests; 17 in-SDK Workflow primitive + OrchestrationProtocol w/ LangGraph two-seam disambiguation; 20 HITLTransportProtocol typed queue, MCP primary + webhook notify-only; 27 substrate split by mutability; 36 deterministic intermediate cache; 44 ReHydrationRecipe + ColdSourceArchiveProtocol; 50 SDK-shipped fidelity lifecycle; 18 workflow state at Control Plane; 21 HumanPrincipalBinding via IdentityProvider family; 22 noun-verb CLI; 23 minimal HTTP skeleton, no L1 endpoint; 43 default human-gated closed loop; 30 nine contract elements, "eight" refs annotated as drift (incl. CLAUDE.md §5, per Dave's ruling); 31 two TTL granularities w/ derivation rule; 32 TrustScorer Protocol conjunctive; 42 prose taxonomy enum canonical; 48 Supervision Quality out of v0 scope. D-IMPL-47 REFINED: DebtFactorScorer Protocol + reference F/C/S computations PLUS evolvability — versioned scorers (scorer_id, scorer_version), Control-Plane-updatable class bindings, per-class custom override, replay pins scorer version in force. Full 12-member Phase I gate list RESOLVED
- [Phase 02]: Batch 2 rulings (Dave, 2026-07-25, zero provisionals): 13 AS RECOMMENDED — D-IMPL-28 YAML artifacts + Pydantic v2 schemas + Jinja2 prompt URIs; 11 single Agent class + Protocol-typed archetype bundles, no user subclassing; 14 LF A2A default WireProtocol + typed-HTTP fallback; 12 dynamic Control Plane skill catalog, four skill types; 19 ordered archetype composition w/ explicit conflict rules; 25 three seams mandatory, effects:unsupported = conformance-verified absence; 29 two-tier skilling governance; 13 five MCP edges via one client lib + egress server + separate ArtifactStore contract; 15 IdentityProvider Protocol, mTLS + detached JWS; 16 verify every inbound A2A product, no fast path; 45 TraceCorrelationHook + ExternalTraceProviderProtocol; 46 PassageCitationProvider Protocol. D-IMPL-24 DAVE'S OWN RULING: all three harnesses (Google ADK + Claude Agent SDK + LangGraph) ship v0 reference adapters. D-IMPL-49 REFINED: deterministic (perspective, product_class, selection_params) signature + DESIGN.md obligation to document swarm intent decomposition as orchestration-layer, named post-v0 extension

- [Phase 02]: DESIGN.md Appendix A granularity: subsection-level for §2A/§2B/§3/§6, chapter-level for §4/§5/§7; Appendix C (D-IMPL ruling index, 50 rulings) added so decision-log linkage is mechanically checkable
- [Phase 02]: D-GATE-D logged 2026-07-25 (approver Dave, zero provisionals; 5 blocking findings fixed in-phase, 7 advisory carried to Phase F); phase-d merged to main --no-ff — Phase F unblocked
- [Phase 04]: D-IMPL-52 logged (Dave, 2026-07-25): v0 examples suite is a horizontal mix of domains; example 00 + the I.1 slice fixtures are banking — replaces CLAUDE.md §9's single-neutral-domain rule (§9 amended in 04-01)
- [Phase 04]: D-12 scope amendment recorded on ROADMAP Phase 4 criterion 4 — I.1 ships ArtifactStore Protocol + file-backed dev impl only; the MCP-backed reference impl was added to Phase 6 success criteria so the deferral has a receiving deliverable
- [Phase 04]: Packaging shape — one v0 distribution ships both `ccf` (src layout) and `ccf_runtime` via `packages.find where = ["src","runtime"]`; chromadb confined to the `chroma` extra, never a core dep
- [Phase 04]: CI lint job is intentionally red on `phase-i1` until plan 04-02 lands `tools/lints` — D-07 forbids making the step non-blocking to hide the gap
- [Phase 04]: Assumption A1 resolved empirically — mypy 2.3.0 `--strict` flag surface is unchanged from the 1.x expectation
- [Phase 04]: Single-writer keyed on graph identity (database path), not one-boot-per-process — the invariant is one writer per graph; a process singleton would forbid multi-fabric hosting
- [Phase 04]: Operators are pure GraphView -> GraphView functions; the engine performs the single as-of read, so no state exists underneath an operator that could diverge between two composition orderings
- [Phase 04]: The engine records operators_invoked from execution, never from the plan's declaration — the L6 lineage strict-equality gate compares two independently produced sets or it compares nothing
- [Phase 04]: MAX_TTL is resolved from the Control Plane twice (product-class registration and gate time); no TTL number exists in /src (D-IMPL-39)
- [Phase 04]: Gate refusals are returned values; exceptions are reserved for broken deployments, so a bad product and a broken fabric are never reported the same way
- [Phase 04]: serve() is one expression because the replay append returns the delivery capability — there is no branch that reaches delivery without a recorded decision
- [Phase 04]: Similarity scores are integer percent; the canonical serializer refuses floats, so a float score could never enter a provenance chain replay compares byte for byte
- [Phase 04]: canonical.py normalizes models field-by-field rather than via model_dump() — dumping rebuilds set-valued fields as sets of dicts, making every claim in the fabric unhashable
- [Phase 04]: Every backend's GraphWriter class lives in ccf.graph._writer, never beside its reader — otherwise the CINV-02 lint guards a module while the real write path lives unguarded
- [Phase 04]: claim_id excludes lineage and observed_at — corroboration accumulates instead of manufacturing supersessions, and a claim stays addressable while its evidence grows
- [Phase 05]: D-05 content comparison uses version-normalized fingerprint (artifact_version blanked) so a bump alone never reads as a content change
- [Phase 05]: delegation_chain defaults to single-element NO_AGENT_DEFINITION chain; build_replay_record passes single-element originating-principal chain (I.2)
- [Phase 05]: Factory resolves ccf-artifact:// refs via Control Plane key {tenant}/{class}/{name}, matching URI version against each registered version's declared artifact_version/semver (content hashes also accepted); reads through Control Plane resolution only, never raw storage
- [Phase 05]: Agent seam failures (ConsumptionRefused, SkillNotBound, AgentConstructionError) are typed exceptions, not returned refusals — broken wiring, not expected artifact outcomes (I.1 refusal-vs-exception line)
- [Phase 05]: SkillCatalog stores only a key index; the registry stays the single source of skill entry content — discovery/resolution read the same audited versions as every Control Plane consumer (05-05)
- [Phase 05]: Skill bindings are pure descriptors in 05-05 (D-08) — no transport or resolution code for any of the four types until 05-06 dispatch
- [Phase 05]: build_replay_record gained optional agent_conditioning seam — agent-serialized dimension-4 conditioning recorded verbatim; None keeps I.1 behavior byte for byte (no contract change)
- [Phase 05]: Tier-1 governance envelope reads a `skill_governance` field (typed PolicyRegimeGovernance) from the policy-regime declaration — field name is mechanism schema; permitted scopes and the tier-2 flag are deployment YAML statements (05-06)
- [Phase 05]: Grant transitions audit as new grant_* AuditAction members through the one existing AuditLog — no parallel log type (05-06)
- [Phase 05]: NotYetBound is a typed RuntimeError for mcp/a2a dispatch (build lacks the transport; artifact is fine) — RESEARCH Open Question 2 resolution; tool dispatch returns a ToolInvocation value, the SDK executes no command (05-06)
- [Phase 05]: Agent holds bound_skills by reference to the GrantLedger's live view — grants/revocations take effect at invoke time without touching agent identity; ledger.grant_set_hash() returns the NO_GRANTS sentinel when empty, pure fn stays content_hash(frozenset) (D-07, 05-06)
- [Phase 05]: Gate package (docs/PHASE_I2_GATE.md) follows the I.1 D-17 format; discretionary in-phase choices recorded in the gate doc §4, not as D-IMPL entries; D-GATE-I.2 deliberately NOT logged pending Dave's approval (05-07)
- [Phase 07]: D-IMPL-60 (Dave, 2026-07-29): all three v0 SDKs get real OrchestrationProtocol drivers under `runtime/ccf_runtime/orchestration/<sdk>/` with bidirectional adapter-import ban; D-IMPL-17 cross-referenced, not edited (07-01)
- [Phase 07]: D-IMPL-61 (Dave, 2026-07-30): absent per-node exception ref = propagate-to-terminal — a defined, audited transition to a terminal `failed` state recorded in the trace; validation-error reading declined (let-it-fail stays expressible). Gates 07-04's exception-routing validator (07-01)
- [Phase 07]: D-IMPL-62 (Dave, 2026-07-30): HTTP/CLI HITL action door is submit-only with honest-contract hardening — `HitlActionReceipt` states `submitted` (type-closed) with real queue disposition; MCP in-process resolve-wiring is a ruled asymmetry; auth stays on T-07-24's residual entry (07-14)
- [Phase 07]: D-IMPL-63 (Dave, 2026-07-30): the two D-IMPL-21 identity-binding reference impls are explicit follow-up-phase scope; caller-supplied principal fields are the recorded v0 posture (07-14)
- [Phase 07]: D-IMPL-64 (Dave, 2026-07-30): webhook deferral REJECTED — the notify-only webhook HITL transport ships in v0 (`ccf.hitl.webhook`: injected `WebhookDeliveryProtocol`, typed refusals, no authority surface by construction) (07-14)
- [Phase 07]: D-IMPL-65 (Dave, 2026-07-30): composition-root debt-cascade wiring closes the I.4 gate; NAMED next-phase commitment — the engine will refuse an agent-node handoff with no bound debt assessment (07-14)
- [Phase 07]: fastapi==0.140.0 and httpx==0.28.1 are direct pins with stated reasons; CLI is stdlib argparse (no click/typer); ADK's `fastapi>=0.133` constraint interaction recorded for the gate (07-01)
- [Phase 08]: D-15 executed — `ccf hitl decide` removed tree-wide, `submit` is the one verb; DECISIONS.md entry dated 2026-07-30 (08-02)
- [Phase 08]: HITL HTTP door fails closed on non-TokenGrant grant objects (403 ERROR_INVALID_GRANT, never caller-principal fallback); refusal bodies carry typed `error_code` constants from `http_api/errors.py`, with `ERROR_SIGNED_BINDING_{REQUIRED,INVALID}` reserved for 08-03 (08-02)
- [Phase ?]: 08-03: HitlPolicy artifact (ccf.hitl-policy) with schema-validated signed_binding_required (default false); D-16 refusals typed at the transport and mapped to shared ERROR_SIGNED_BINDING_* constants at both HTTP and MCP doors; R1 closed with was-called assertions
- [Phase 08]: Example 07 store choice is a config artifact (`store.type`) interpreted by one factory seam; file root and MCP endpoint are env-templated so no path or port is committed; the MCP child interprets the same store_mcp.yaml auth block as the client factory, so credentials cannot drift (08-09)
- [Phase ?]: ADK migration taken over suppression: google.adk.workflow.Workflow usable at 2.5.0 (BaseAgent is BaseNode); D-08 allowlist carries the harness Workflow name-collision, allowlist path matching Rule-1-fixed (08-04)
- [Phase 08]: 08-12 — make ci finalized as ci-core + examples (the phase gate command, command-identical to the always-on Actions pipeline, D-10); live legs opt-in via live-legs.yml workflow_dispatch (Ollama model parameterized, default qwen3:0.6b; Anthropic secret-gated fail-fast) per D-11; push of phase-i5 flagged for Dave, not performed
- [Phase 08]: A3 closed with zero adapter change — the discharge test and example 03's Claude leg drive a genuinely SDK-parsed ResultMessage through seam 4; example 03's session runs over the adapter's own seam-1 carrier, and legs/deterministic.py imports all three harness SDKs unconditionally so a missing harness is a failure, not a skip (08-10)
- [Phase 08]: 08-13 — D-GATE-I logged (Dave, 2026-07-31): Phase I approved, v0.1.0 tagged on the main merge commit (358ba0d), push authorized and performed; review disposition X-1 fixed in-phase (composition-coverage row narrowed to the shipped_operators() test registry), C-4 rejected with rationale (README tracks CLAUDE.md mission wording)

### Todos

- Plan Phase 9 (`/gsd:plan-phase 9`) — includes surfacing the six-item D-IMPL ruling batch to Dave (HARD-01)
- Phases 10–14 gated: 10 on the Phase 9 rulings; 11 on the hardened surface + perf-governance ruling; 13 on Phase 10 (parallel to 11/12); 14 on 11+12+13 outputs + docs-toolchain/D-10 rulings

### Blockers

- ~~Phase 4 (Phase I.1) hard-gated on provisional resolution of D-IMPL-01..05, 11, 14, 17, 20, 24, 26, 28~~ — CLEARED 2026-07-25: all 12 gating IDs RESOLVED (batch 3 completed 17, 20, 26)
- Every phase gate requires Dave's approval + `D-GATE-<Phase>` entry; `/gsd-review` passing is necessary, never sufficient

## Session Continuity

Last action: 08-13 complete (2026-07-31) — Phase I gated and v0.1.0
declared: D-GATE-I logged, phase-i5 merged to main --no-ff, v0.1.0 tagged
on the merge commit, main/phase-i5/v0.1.0 pushed to origin per Dave's
authorization. Prior: 08-12 — examples suite
wired into CI per D-10/D-11 (EXAM-09, Task 1 f145f1e): ci.yml always-on
`examples` job (make examples, CCF_REQUIRE_HARNESSES=1, timeout-minutes
20, never continue-on-error) plus new live-legs.yml (workflow_dispatch
examples-live-ollama with parameterized small model; secret-gated
examples-live-anthropic with fail-fast); `make ci` finalized = ci-core +
examples. Full local sweep GREEN (Task 2 evidence-only): lint 0, mypy
clean (156 files), pytest 1339 passed / 0 skipped, all eight examples
exit 0, D-09 README/artifacts contract check 8/8 PASS.

Next action: v0 is declared — milestone complete. Post-v0 backlog:
Homecams-on-SDK rebuild, PyPI motion, perf baselines, replay-explorer /
graph-export CLI ideas. Observe the first Actions runs on origin for the
EXAM-09 observed-evidence record.

---

**2026-08-05 session resume.** Phase 15 (SDK Ergonomics) is executing at
18/21 plans; waves 1–11 merged to `main` at `5fbb8e0`, handoff saved at
`60a148b`, tree clean, no worktrees. Full checkpoint context — Dave's six
in-execution rulings, the `_register_closure` evidence for 15-19, the two
self-satisfying-assertion defects 15-21's audit must cite, and the
worktree/`.venv` operational notes — lives in
`.planning/phases/15-sdk-ergonomics-the-integration-surface/.continue-here.md`.
Remaining: wave 12 = 15-19 (example 05 workflow-HITL, autonomous),
wave 13 = 15-20 (external 00-hello-context, autonomous), wave 14 = 15-21
(phase close + Criterion 1 audit, **checkpoint — not autonomous**).
Gates green at handoff: 1908 passed/2 skipped, lint 0, typecheck 169 files,
ten examples, docs-strict, schema-headers.

Resume: `/gsd-execute-phase 15`

---

**2026-08-18 session resume.** Phase 18.1 discussion RESUMED mid-flight.
`.planning/phases/18.1-simplify-the-mcp-example-separate-the-server-from-the-client/18.1-DISCUSS-CHECKPOINT.json`
(untracked, written 11:55) holds one completed area — *Where the server command
is declared*, five questions ruled — plus one question of *The address grammar
after the change*. Locked so far: a bare `server:` key in `binding.yaml` holding
a single contained path (SDK still supplies the interpreter and still passes the
deployment root as `argv[1]`); `server/` moves INSIDE the deployment root as
`deployment/server/` so containment holds without an exemption; `D-IMPL-141` A.3
amended in writing AND its gate extended to walk the whole tree (exactly one
module at the deployment root, Python elsewhere only under the directory
`binding.yaml` declares); the two-token `mcp+stdio` address form REPLACED by one
token, refusal naming the migration. Remaining areas: *How simple is simple
enough for `serve.py`*, *What the README shows and what goes off-stage*.
Nothing planned, nothing executed; no phase branch. `main` clean and 41 commits
ahead of `origin/main` (push unruled).

**Discussion COMPLETE** — all four areas closed in the afternoon sitting, checkpoint
deleted, `18.1-CONTEXT.md` and `18.1-DISCUSSION-LOG.md` committed at `60f2bd3`. The
morning's server-residence ruling was reopened by Dave and reversed (see Current
Position). Nothing planned, nothing executed; no phase branch. `main` clean and now
43 commits ahead of `origin/main` (push still unruled).

Resume: `/gsd:plan-phase 18.1`
