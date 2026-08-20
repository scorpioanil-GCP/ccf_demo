---
gsd_state_version: 1.0
milestone: v0.2
milestone_name: Performance, Documentation & Demonstration
status: executing
last_updated: "2026-08-20T08:55:00.000Z"
last_activity: >-
  2026-08-20 -- **PHASE 19 CLOSE REVIEW COMPLETE. AWAITING DAVE'S RULING AND `D-GATE-19`.**
  59 commits, `0fe0a22` -> `cff00ae` on `main`. FINAL GATE: `make ci` EXIT 0 --
  **4013 passed / 118 skipped / 0 failed**, 400 lint, 154 docs, nine examples,
  `mkdocs --strict` green, three validation gates pass. Tests 3901 -> 4013 (+112).
  **THE CLOSE FOUND A BLOCKER THE VERIFIER AND THE PANEL BOTH MISSED, AND IT WAS THE
  PHASE'S OWN DEFECT IN THE PHASE'S OWN NEW GATE.** `C-17`'s AST gate was ruled to prove
  no module under `src/ccf/client/adapters/` constructs the outcome. IT DID NOT. It matched
  only an import-bound `ast.Name` call or an attribute literally spelled
  `WireOutcome`/`DoorOutcome`, so THREE IN-TREE SPELLINGS SCORED ZERO: pydantic
  construction classmethods, relative imports, and subclassing. REPRODUCED END-TO-END BY
  THE ORCHESTRATOR BEFORE ANY FIX: an adapter spelling `WireOutcome.model_validate({...})`
  scored 0, PASSED the gate, passed `mypy --strict`, `ProductClient.ask` RAISED NOTHING,
  and the caller received another question's vessel (sentinel `expires_at` 2099-09-09
  observed). **`B0` WAS RE-OPENABLE IN-TREE WITH THE ENTIRE BUILD GREEN.** `WR-01`
  compounded it: the shipped prose credited `19-04`'s conformance obligation as covering
  the gap, and that control is INERT -- the tamper legs measure THE CLIENT's reaction to
  corruption, never the adapter's honesty, and both pass against a forging adapter.
  DAVE RULED OPTION A: fix the existing gate, TEST-FILE ONLY, no production code -- not a
  new gate, the current one made to do what `C-17` already required. AFTER: the forger
  scores 1 and the gate FAILS; relative import 1; subclass 1. The fix DERIVES
  `_CONSTRUCTING_FORMS = PYDANTIC_MODEL_FORMS - _SERIALIZING_FORMS`, naming only what it
  EXCLUDES, so a fourteenth pydantic spelling is counted automatically -- a
  hand-maintained positive list is the drift shape that produced the defect. `WR-01`
  is resolved BY THE FIX (`model_copy` is in that frozenset), not by prose.
  `git diff --stat b1c40f4..HEAD -- src runtime` IS EMPTY.
  **THE PANEL: FOUR REVIEWERS, THREE OF FOUR CONVERGED ON ONE FINDING**, verified
  empirically -- `wire.py` claimed an adapter cannot construct the outcome; it can, and
  re-labelling defeats BOTH checks. Three prose overclaims fixed (`2119ca6`), the
  structural-unbypassability question DEFERRED as `D-IMPL-162` on Dave's ruling because it
  is a different project. FOUR PANEL FINDINGS REJECTED, TWO OF THEM FABRICATED CITATIONS
  to files that do not exist -- ollama; gemini was grounded this run, a change from Phase 18.
  **A VACUITY WAS CAUGHT IN THE VERIFICATION CODE ITSELF**: the orchestrator's first probe
  of the re-labelling finding had an attack leg and a control producing BYTE-IDENTICAL
  subjects, so it proved nothing until rebuilt with distinguishable vessels. Recorded
  rather than hidden -- it is the phase's own defect class, in the code written to test it.
  **FOUR ITEMS REMAIN OPEN FOR DAVE, NONE FIXED IN-PHASE BY DESIGN:** `F-1` Phase 19 has
  NO ROADMAP SUCCESS CRITERIA (`roadmap.get-phase 19` returns `[]`); `F-2`
  `verify.key-links` CAN NEVER PASS (invalid-regex on escaped parens, marks links
  unverified WITHOUT RUNNING THEM); `F-3` the citation lint SILENTLY DROPS AMBIGUOUS
  BASENAMES (the two instances this phase introduced are fixed; the hole is open); and
  `WR-04` the declared single-copy axis count is understated -- `egress.py` names
  `asked_at` where §6.3 has FOUR axes and `WireRequest` echoes three fields, DEFERRED
  because it widens `C-10`'s undetected list, which `D-IMPL-156` records as CROSS-CHECKED
  AT FOUR ITEMS ACROSS TWO RECORDS -- a claim change, not a correction.
  `F-2` AND `F-3` ARE THEMSELVES CHECKS THAT CANNOT FAIL, one level up from `B0`.
  NEXT: **DAVE'S RULING AND `D-GATE-19`.** The §3.1 sequence is DISCHARGED -- execution,
  cross-AI panel (`19-CLOSE-REVIEWS.md`), single-agent review (`19-REVIEW.md`), every
  finding verified against the tree, blocking findings fixed in-phase
  (`19-CLOSE-FIXES-SUMMARY.md`).

  2026-08-20 -- **PHASE 19 EXECUTED. 8/8 PLANS, 6 WAVES, 52 COMMITS**, `0fe0a22` -> `cf47bf8`
  ON `main` -- NO PHASE BRANCH, on DAVE'S EXPLICIT RULING (2026-08-19, asked before Wave 1:
  there are no SDK consumers, so `main` carrying un-gated phase work costs nothing and history
  still permits carving a branch retroactively). This DIVERGES from CLAUDE.md 2.2 and MATCHES
  what Phases 18 and 18.1 actually did; recorded as `D-IMPL-161` rather than left as invisible
  drift. CLAUDE.md was NOT amended unilaterally.
  **`B0` IS CLOSED ON THE AXES MEASURED.** The two client-seam checks CAN NOW FAIL: the door
  emits the question it parsed and the address it computed, the adapter seam is
  `ask(WireRequest) -> bytes` so NO adapter constructs an outcome, and a crossed question and
  an altered vessel are each caught by a SINGLE-TRANSPORT client -- two assertions, one per
  transport, NEITHER NAMING A SECOND SUBJECT, which is the ROADMAP's own success sentence.
  **GATE AT `cf47bf8`: `make ci` EXIT 0** -- 3981 passed / 118 skipped / 0 failed, 400 lint,
  154 docs, nine examples, `mkdocs --strict` green. Tests 3901 -> 3981 (+80).
  **VERIFICATION `human_needed`, 63/63 must-haves, and it was established BY BREAKING THINGS,
  not by reading a green suite** -- a green suite is worthless evidence in this phase, since
  `check_outcome` was green throughout Phase 18 while comparing an object with itself. TEN
  properties broken in an out-of-tree `rsync` copy reached by `PYTHONPATH`, 43 control-reds
  observed, plus four direct probes. CONTROLS THAT COULD NOT BE MADE TO FAIL: NONE.
  **`C-18`'s RESIDUAL IS VERIFIED OPEN, NOT CLOSED** (`D-IMPL-159`): with `as_of=None` the
  CLIENT resolves the clock (`C-15`), so there is no second copy of the instant and a transport
  altering `asked_at` alone is UNDETECTED. That non-detection is a PASSING MEASUREMENT which
  itself goes red under the `C-02` sabotage, so it does not pass by accident. A tree-wide sweep
  found NO shipped prose overclaiming past that line.
  **FIVE DEFECTIVE CRITERIA WERE REPORTED RATHER THAN SATISFIED** across the eight plans --
  one satisfiable only by deleting the phase's own thesis paragraph, one already green at
  baseline, one VACUOUSLY green because the target sentence wrapped across two lines, one
  requiring an edit to append-only `DECISIONS.md`, one whose plan made it unsatisfiable.
  EVERY EXECUTOR FOUND ITS OWN PLAN MEASURABLY WRONG and said so.
  **THREE ITEMS ESCALATED TO DAVE, NOT FIXED IN-PHASE:**
  `F-1` PHASE 19 HAS NO ROADMAP SUCCESS CRITERIA -- `roadmap.get-phase 19` returns
  `success_criteria: []`, so the phase was gated on plan `must_haves` ALONE; criteria were
  deliberately NOT invented retroactively, which would have been its own vacuous check.
  `F-2` `verify.key-links` CAN NEVER PASS -- it reports `Invalid regex pattern` for any
  pattern with an escaped paren and marks the link unverified WITHOUT RUNNING IT; 6 of this
  phase's 12 links. That is the INVERSE of the defect this phase closes. All six checked by
  hand; all six hold.
  `F-3` THE CITATION LINT SILENTLY DROPS AMBIGUOUS BASENAMES -- a check that cannot fail, one
  level up from `B0`. Phase 19 pushed exactly TWO new stale citations through it; both are now
  FIXED at `cf47bf8`, re-anchored onto fully-qualified symbols so the lint actually checks
  them. The adjacency sweep hand-resolved all 16 dropped citations across 8 ambiguous
  basenames: one other (`product.py:330`) is stale and PREDATES this phase. THE HOLE ITSELF IS
  STRUCTURAL AND STILL OPEN -- documented at `ROADMAP.md` but not closable under `C-13`.
  TOOLING HAZARD, FOURTH DISTINCT HANDLER: `state.begin-phase` TRUNCATED `STATE.md`
  1046 -> 661 LINES at phase start while returning a clean success naming three fields, and
  wrote `total_plans 173 / completed_plans 184` -- completed exceeding total AGAIN. Backed up,
  diffed, restored, hand-edited. ALL ROADMAP checkboxes hand-edited; NO `state.*` or
  `roadmap.*` writer was allowed to run against either file for the whole phase.
  NEXT: **THE PHASE IS NOT CLOSED.** CLAUDE.md 3.1 requires, IN ORDER:
  `/gsd-review --phase "Phase 19" --all` (THE CROSS-AI PANEL, pointed at the SHIPPED CODE and
  given the known findings with instructions NOT to re-derive them) -> the single-agent code
  review -> VERIFY EVERY FINDING AGAINST THE TREE -> fix blocking findings in-phase -> present
  to Dave -> `D-GATE-19`. The panel is MANDATORY and the single-agent review NEVER substitutes.

  2026-08-19 -- **PHASE 19 PLANNED. 8 PLANS IN 6 WAVES**, committed `9356520` -> `751fb9a` ->
  `dacf067`. Research (`19-RESEARCH.md`, 1460 lines) MEASURED EVERY CLAIM AT HEAD `192c79d`
  rather than restating `19-CONTEXT.md`: the `B0` defect STILL HOLDS, blast radius is ~60-95 of
  4027 collected tests concentrated in five modules, `examples/` IS UNTOUCHED (`consume.py`
  speaks only `ProductClient.ask`), and `mypy` covers `src`+`runtime` ONLY -- so stale test
  annotations WILL NOT fail `make typecheck`.
  FOUR RULINGS TAKEN BY DAVE AT PLANNING, recorded as `C-15`..`C-18` in `19-CONTEXT.md`:
  `C-15` THE CLOCK DOES NOT MOVE (`C-13` stay-narrow governs; the false sentence in
  `src/ccf/client/client.py::ProductClient.ask` is AMENDED, and the client-side clock read becomes ITS OWN `D-IMPL` FOR A LATER
  PHASE); `C-16` BREAK CLEANLY -- `PRODUCT_REQUEST_TOOL` gains a REQUIRED argument, no
  deprecation window, one `D-IMPL` ruling both that and the `C-08` out-of-tree adapter break;
  `C-17` A NARROW AST GATE over `src/ccf/client/adapters/` only, mirroring `CLNT-06`;
  `C-18` THE TEMPORAL AXIS IS CROSS-CHECKED WHERE CHECKABLE and the residual DECLARED where it
  is not -- found by the plan-checker: because `C-15` keeps the clock client-side, a concrete
  `as_of` crosses the pipe TWICE (inside the echo, and as `asked_at` which the door answers
  against), so `B0`'s OWN FAILURE MODE SURVIVED ON THE THIRD AXIS of a comparison `C-03` calls
  total. The `as_of=None` residual is asserted as a PASSING TEST, not an `xfail`.
  TWO PLAN-CHECKER ROUNDS: round 1 found 4 BLOCKERS + 5 warnings + 3 info, round 2 found
  0 BLOCKERS + 4 warnings + 5 info, all 21 findings addressed across two revisions. EVERY
  BLOCKER WAS VERIFIED AGAINST THE TREE BEFORE BEING ACTED ON; none were rejected. The sharpest
  finding was NOT a code defect but a CHECK DEFECT: `19-02`'s criterion
  `grep -c "check_outcome" client.py == 0` WAS SATISFIABLE ONLY BY DELETING the paragraph in
  `src/ccf/client/client.py::ProductClient.ask` that states the phase's own thesis -- a criterion greenable only by
  violating project law, in the phase about checks that cannot fail. Now inverted into a GUARD
  (`grep -c "func:.*check_outcome" >= 2`), so deletion fails in wave 2 rather than going
  unnoticed until wave 5.
  TOOLING HAZARD OBSERVED AGAIN: `state.planned-phase` TRUNCATED `STATE.md` 1014 -> 660 LINES
  (`D-IMPL-154`/`155` class). Backed up, diffed, restored, hand-edited. `roadmap.annotate`
  handled the same way.
  NEXT: `phase-19` BRANCH DOES NOT EXIST -- create it before Wave 1 if CLAUDE.md 2.2's
  single-merge-at-gate discipline is to hold for the code. Then `/gsd:execute-phase 19`.

  2026-08-19 -- **PHASE 18.1 CLOSED AND GATED. `D-GATE-18.1` APPROVED BY DAVE**, recorded in
  `docs/DECISIONS.md`. NO MERGE REQUIRED -- the work landed on `main`. Gate HEAD `04cccc2`:
  `make ci-core` EXIT 0, 3909 passed / 118 skipped / 0 failed. Dave's ruling: the phase
  "answers the original complaint WITHOUT GROWING SURFACE AREA", and the close process
  "did its job: COARSE SABOTAGE WAS SHOWN TO BE INSUFFICIENT, and a proposed remedy that
  would itself have been VACUOUS was refused."
  TWO `D-IMPL` ENTRIES MINTED ON DAVE'S RULING so the carried tooling hazards STOP BEING
  INVISIBLE INHERITANCE rather than living only in SUMMARY and review files:
  `D-IMPL-154` (`tools/retirement_sweep.py --report` REWRITES A TRACKED FILE -- the help text
  is honest, THE FLAG NAME IS THE DEFECT; a later tools pass should split it `--check`/`--write`)
  and `D-IMPL-155` (A MISNAMED SURFACE FRAGMENT IS SILENTLY DROPPED, and the obvious remedy
  DELETES THE RECORD while every gate reports green -- 117 lines, four entries, counts falling
  727 -> 723, 20/20 tests green; a later gate should compare the fragment directory against the
  assembled document). BOTH REMAIN ADVISORY AND DEFERRED, not reopened as in-phase work.
  Codex's case-insensitive-filesystem claim REMAINS AN OPEN QUESTION, not a defect and not
  fixed -- Dave: "Correct."
  NEXT: Phase 19 (THE CLIENT-SEAM INTEGRITY CHECKS MUST BE ABLE TO FAIL) is FULLY DISCUSSED --
  `19-CONTEXT.md` exists with 14 decisions -- and NOT PLANNED. `/gsd:plan-phase 19`.

  2026-08-19 -- PHASE 18.1 CLOSE REVIEW RUN; THREE BLOCKING FINDINGS FIXED IN-PHASE. AWAITING
  DAVE'S RULING AND `D-GATE-18.1`. Gate measured at `04cccc2`: `make ci-core` EXIT 0,
  3909 passed / 118 skipped / 0 failed (+8 = exactly the eight tests added), 400 lint, 154 docs.
  THE PANEL (codex, cursor, gemini) WAS POINTED AT THE SHIPPED CODE, NOT THE PLANS, and was given
  the six already-known findings with instructions NOT to re-derive them -- so its budget went to
  what is ADJACENT. It found three real holes the 40/40 VERIFIER MISSED:
  (1) `D-18`'s predicate is `server == root_path OR root_path in server.parents` and BOTH tests
  fed only the SECOND limb -- removing the first left 752 TESTS GREEN. The mechanism was CORRECT
  (`server: deployment` IS refused); nothing HELD it. THE VERIFIER SABOTAGED `D-18` ENTIRELY
  (`if False:`), got two reds, and concluded it was held: A SABOTAGE AS COARSE AS THE WHOLE GUARD
  ONLY PROVES SOME TEST MENTIONS IT, NEVER THAT EACH BRANCH IS HELD. Same mechanism, same
  technique, DIFFERENT GRANULARITY, OPPOSITE ANSWERS.
  (2) A ROOT PATH CONTAINING A SPACE was diagnosed as the pre-migration two-token address, and the
  advice -- "drop it from the address and name the root alone" -- DESTROYS THE USER'S PATH
  (`/tmp/My Deployments/deployment` -> `mcp+stdio:/tmp/My`). Neither branch named quoting though
  the `mcp_stdio` module docstring already says quoting is the remedy. A NEW INSTANCE OF THE `B0b` CLASS in
  the phase whose own `D-08` cites `B0b`.
  (3) THE README CREDITED A TEST WITH A CHECK IT DOES NOT MAKE: repointing the documented mcp
  address at a nonexistent `OTHERDEPLOYMENT` in BOTH README and Makefile left ALL 17 PURITY TESTS
  GREEN. `D-15`'s observable rested on a property no gate held -- in the very document `C-1` was
  approved on. RULED BY DAVE: fix BOTH the gate and the prose, written against each other.
  ALL THREE FIXED AND EACH INDEPENDENTLY RE-SABOTAGED BY THE ORCHESTRATOR: the mutations that
  previously passed silently now fail (752 green -> 1 red; 17 green -> 1 red).
  THE SEVENTH INSTANCE WAS IN THE PROPOSED REMEDY FOR THE SIXTH. The review AND the orchestrator's
  brief both proposed `binding.partition(":")[2].partition(":")[2]` to extract the address; measured
  against real tokens it yields `""` for BOTH commands, so the assertion would have passed ON AN
  EMPTY SET. The executor measured it, REFUSED IT, and shipped a guarded splitter plus five
  parametrized vacuity controls instead.
  NOT ACTIONED, DELIBERATELY: Codex's only HIGH (a case-insensitive-filesystem bypass) COULD NOT BE
  VERIFIED ON THIS LINUX HOST, and Gemini asserted the opposite WITHOUT TESTING EITHER. Recorded as
  an OPEN QUESTION, not a defect. Gemini found nothing actionable. SEVEN CONFIRMED ADVISORIES are
  carried, un-fixed and fenced out of the close fixes as scope creep.
  ORCHESTRATOR PROCESS DEFECT, RECORDED AGAINST MYSELF: the verifier and the code reviewer were
  dispatched IN PARALLEL onto ONE WORKING TREE and both run sabotages that MUTATE SOURCE. They
  observed each other -- the verifier flagged a README reading `OTHERDEPLOYMENT` as possible
  injection; it was the reviewer's control. Both re-verified against `git show HEAD:` and neither
  acted on foreign state, and the tree ended byte-identical to HEAD, but THE ISOLATION WAS MINE TO
  PROVIDE. Sabotage-running agents must not share a working tree.

  2026-08-19 -- PHASE 18.1 EXECUTED, 5/5 PLANS, TREE GREEN END-TO-END. `make ci-core` EXIT 0
  at the close commit (3901 passed / 118 skipped / 0 failed, plus 400 lint and 154 docs), and
  re-verified after the tracking commit. THE PHASE IS NOT CLOSED -- CLAUDE.md 3.1 still owes the
  cross-AI panel against the SHIPPED CODE, the single-agent review, finding verification, Dave's
  ruling and `D-GATE-18.1`.
  WHAT SHIPPED: `server:` as a contained data key in `binding.yaml` (base = the deployment root's
  PARENT, with an INWARD-reaching value refused BY NAME -- `D-18`, the phase's one deliberate piece
  of new mechanism, recorded in `docs/surface-changes/18.1-04-...` and ruled in `D-IMPL-153`);
  the `mcp+stdio` address collapsed to ONE TOKEN, the deployment root, across 13 files in a single
  commit; `serve.py` cut 292 -> 197 lines with the boot moved to `compose.py` (137); and a README
  that states WHY a server is present before showing one. The client's command no longer names
  `serve.py` anywhere, and the two documented commands differ by exactly ONE TOKEN, the scheme.
  C-1 APPROVED BY DAVE'S OWN READ (2026-08-19), passage by passage; `README:186` was explicitly
  considered and LEFT UNCHANGED by that ruling. NO PROXY GATE WAS INVENTED FOR C-1 -- its
  unmeasurability was DEMONSTRATED, not asserted: the entire README frame was deleted and 381
  example tests stayed GREEN.
  THE PHASE'S LESSON, CONTINUING THE PROJECT'S ELEVEN AND NOW FIFTEEN: EVERY DEFECT FOUND WAS IN
  VERIFICATION MACHINERY OR IN PLANS, NEVER IN MECHANISM. Four checks shipped GREEN FOR THE WRONG
  REASON and only sabotage told the difference -- wave 2's distinctness assertion passed against
  two IDENTICAL message templates (every refusal interpolates the address, so identical templates
  still render differently); wave 3's vacuity control still produced a violation from a DIFFERENT
  rule after the count rule was weakened; wave 1 found a provisioning site so INERT that deleting
  it changed no output; and wave 4 found that a misnamed surface fragment is SILENTLY DROPPED.
  They share one shape: THE ASSERTION SAT BELOW A DISJUNCTION, so satisfying EITHER branch made it
  pass. Three plan acceptance criteria were also defective -- one that could not fail, and TWO
  case-sensitivity false-reds (`declared budget` vs `Declared budget`).
  TWO ORCHESTRATION RULINGS BY DAVE (2026-08-19): `D-08`'s rationale CORRECTED IN PLACE (it named
  the wrong fall-through message -- `is_dir()` is checked before `is_file()`, so a file-naming
  token reaches "is not a deployment root", not "no `binding.yaml` here"; the RULING is unchanged
  and was NOT reopened); and plan `18.1-04`'s executor wrote the ROADMAP narrowing itself, fenced
  to a content-only edit, verified afterward as 3 prose hunks with no checkbox or progress-cell
  edits.
  TWO ITEMS RECORDED AND DELIBERATELY NOT FIXED IN-PHASE, awaiting a ruling:
  (1) `tools/retirement_sweep.py --report` IS NOT READ-ONLY -- it rewrites the tracked report; its
  argparse help is honest, the defect is the FLAG NAME, and it caused one accidental mutation this
  phase. (2) A MISNAMED SURFACE FRAGMENT IS SILENTLY DROPPED WITH DATA LOSS ON THE OBVIOUS REMEDY:
  the red says "the assembled document is out of date", never "your fragment is misnamed", and
  re-running `make surface-changes` clears the red TOGETHER WITH THE RECORD -- 117 lines, four
  entries, register counts falling 727 -> 723, and all 20 surface tests green. Nothing compares the
  fragment directory against what was assembled.
  EXECUTED WITHOUT WORKTREE ISOLATION, deliberately (5 waves x 1 plan = no parallelism to buy, and
  `18.1-04` edits ROADMAP.md, which the worktree cleanup path would have silently reverted). NO
  `state.*` OR `roadmap.*` SDK WRITER WAS RUN AGAINST EITHER TRACKING FILE after the one at session
  start, which collapsed 113 lines and was restored from backup.

  2026-08-19 -- PHASE 18.1 EXECUTION STARTED. Five plans, five waves, strictly sequential
  (each wave holds exactly one plan and every plan depends on the one before it). RUNNING
  WITHOUT WORKTREE ISOLATION, deliberately: there is no parallelism to buy, and plan `18.1-04`
  lists `.planning/ROADMAP.md` in its own `files_modified` -- the worktree cleanup path backs
  ROADMAP.md up before the merge and restores it after, which would have SILENTLY DISCARDED
  that plan's intentional narrowing of the "ships no new SDK surface" claim (D-18). Executors
  are additionally instructed NOT to run any `state.*` or `roadmap.*` SDK writer: `state.begin-phase`
  was run once at the start of this session and COLLAPSED 113 LINES of `last_activity` and the
  whole `progress:` block into one line; it was restored from backup and the four fields it meant
  to set were applied BY HAND. The orchestrator is the single writer for both tracking files.

  2026-08-18 -- PHASE 18.1 PLANNED. FIVE PLANS IN FIVE WAVES, committed and gated. Research
  (`18.1-RESEARCH.md`, 1492 lines) and a pattern map were run and BOTH FOUND DEFECTS THE
  DISCUSSION HAD NOT: research swept the tree and found the two-token `mcp+stdio:` address in
  21 PLACES, not the 2 that were listed -- including
  `tests/examples/test_hw1_two_transports.py::test_the_mcp_leg_really_runs_the_examples_own_server_program`
  which UNPACKS THE ADDRESS INTO TWO NAMES and
  would raise `ValueError` the moment `D-05` lands, and `src/ccf/client/binding.py::split_binding` which is
  a SHIPPED REFUSAL MESSAGE that would start showing a shape that no longer parses (the `B0b`
  class, in the phase whose own `D-08` cites `B0b`). It also measured `make ci-core` RED AT HEAD
  for a cause unrelated to this phase (`6d6a99b` moved 14 Phase 16 plans to `abandoned/`;
  `RETIREMENT-COUPLINGS.md` stale by 26 planning-tree rows). TWO RULINGS BY DAVE, recorded as
  `D-18` and `D-19` in `18.1-CONTEXT.md`: (1) an INWARD-REACHING `server:` IS REFUSED BY NAME --
  parent-relative containment also accepts a value pointing back inside the root, which would let
  a third-party deployment hold two Python modules where `D-IMPL-141` A.3 grants one; this is
  THE PHASE'S ONE PIECE OF NEW MECHANISM, deliberately, so the "ships no new SDK surface" claim is
  NARROWED in the ROADMAP and the surface fragment, and a `D-IMPL-153` entry is owed;
  (2) THE PRE-EXISTING RED IS CLEARED AT WAVE 0 and swept again after the last SUMMARY, so a red
  gate during execution means a real regression rather than an ambiguous one.
  PLAN REVIEW RAN TWICE. Iteration 1 returned ONE BLOCKER: the third `declare_server` provisioning
  site was assigned to no task, because `18.1-PATTERNS.md` §5(b) claimed the copied deployment's
  parent "is exactly where `_stub_program` already writes" and TWO PLANS INHERITED THE ERROR. The
  tree says otherwise -- the callers pass DIFFERENT name arguments at every site
  (`"exits"` vs `"exits-root"`), so the parent is EMPTY. Five tests would have failed inside the
  irreducible 11-file grammar flip, and `:205` is `V-12`, THE HEALTHY-PATH NON-VACUITY LEG -- with
  the baseline broken, `V-07` WOULD HAVE PASSED FOR THE WRONG REASON, the exact defect `CLNT-12`
  exists to prevent. Also caught: an acceptance criterion that COULD NOT FAIL
  (`grep "server" | grep -c "RULED_OUT_KEYS"` returns 0 either way), and an instruction NOT to
  append to `docs/DECISIONS.md` on the false premise that it is a historical record -- it carries
  208 `D-IMPL-` references and `CLAUDE.md` §11/§12 name it the live decision log. §5(b) was
  corrected in place, `18.1-VALIDATION.md` now NAMES ALL THREE PROVISIONING SITES because the
  third was missed precisely because nothing named it. Iteration 2: NO BLOCKERS, 2 warnings +
  4 info, all closed by hand. Gates: requirements 5/5, DECISION COVERAGE 19/19.
  EVERY REVIEW FINDING WAS VERIFIED AGAINST THE TREE BEFORE BEING ACTED ON.

  2026-08-18 -- PHASE 18.1 INSERTED after Phase 18 (Dave): SIMPLIFY THE MCP EXAMPLE, CLIENT-SIDE
  ACCESS WITH THE SERVER OFF-STAGE. Dave, reading `examples/hw1-companies-over-revenue`: the
  server was `too overwhelming`, it was `not clear what the client had to implement`, and `the
  client is not responsible for setting up the MCP server, yet when the MCP example is called the
  client code references the server.py`. VERIFIED: the documented command puts the server program
  inside the client's `CCF_BINDING` and `consume.py` SPAWNS `serve.py` (`mcp_stdio.py:322`). MCP
  stdio has no listening endpoint, so THE SPAWN IS INHERENT AND IS NOT THE DEFECT -- the defect is
  that the spawn is the CLIENT'S BUSINESS in the reader's field of view. SCOPE, THREE CHANGES AND
  NO NEW MECHANISM: (1) `CCF_BINDING` names a DEPLOYMENT rather than a script, with the server
  command declared in `binding.yaml` AS DATA, so the reader's command never mentions `serve.py`;
  (2) `server/serve.py` (292 lines, ~180 of them deployment-value composition) is cut to a
  readable length into a SECOND `server/` MODULE -- never into `deployment/`, which `D-IMPL-141`
  A.3 forbids and `test_data_only_deployment.py` enforces; (3) THE README STATES THE FRAME in
  Dave's own terms -- the SAME CONTEXT PRODUCT reached A DIFFERENT WAY, why a server appears at
  all (the first example ran IN-PROCESS with the SDK and produced the product directly), and that
  HOW THE MCP SERVER WAS ASSEMBLED IS DELIBERATELY OUT OF SCOPE, covered later in the examples on
  ASSEMBLY OF CONTEXT PRODUCTS. A server appearing in a client-side example is NOT a scope
  violation; EXPLAINING it is.
  AN EARLIER DRAFT OF 18.1 WAS WITHDRAWN THE SAME DAY, and the reason is recorded because it is a
  pattern rather than an incident: it proposed shipping `mcp+http` AS A THIRD ADAPTER so the
  server could start independently. That was SDK TRANSPORT WORK WEARING AN EXAMPLE'S CLOTHES -- it
  would have put producer-side mechanism inside a deliberately CLIENT-SIDE phase, and Phase 19
  would have rewritten it immediately; the draft even recorded that rework as a `known cost` and
  recommended proceeding. Dave: *`We specifically stated we were going to focus on simplifying the
  client experience... The first examples were client-side and we would progress to server side
  (e.g. Context Product creation)... You continue to disregard my direction.`* THE RULE NOW
  WRITTEN DOWN: when an EXAMPLE is too complicated, the deliverable is a SIMPLER EXAMPLE, never
  new SDK surface -- and the sentence `known cost: the next phase will rewrite this` is a STOP
  SIGNAL, not a caveat. 18.1 is consequently INDEPENDENT OF PHASE 19: no seam change, so either
  order works. `A5` is NOT addressed and stays carried forward.
  ROADMAP WRITTEN BY HAND AFTER `phase.insert`: the handler wrote ONLY a stub detail section -- no
  Phases-list bullet and no progress row, the exact staleness that let Phase 17 run its entire
  life with no bullet and a `0/10` row. All three surfaces now agree, and Phase 18's progress row
  was corrected in passing (it read `AWAITING D-GATE-18` after the gate was granted and merged).
  STATE HANDLER FAILURE, SECOND INSTANCE THIS SESSION: `state.add-roadmap-evolution` returned
  `added: true` and CORRUPTED THE FILE ANYWAY -- 719 -> 562 lines, `status` flipped to
  `completed`, `last_activity` and `stopped_at` destroyed, and PROGRESS NUMBERS INVENTED
  (`total_plans: 160` with `completed_plans: 178`, impossible on its face). Restored from a
  pre-call backup and hand-edited, as with `state.record-session` earlier. DO NOT USE `state.*` OR
  `roadmap.*` WRITERS ON THIS FILE WITHOUT A BACKUP AND A DIFF.
  2026-08-17 (later) -- PHASE 19 CONTEXT GATHERED. `/gsd:discuss-phase 19` ran to completion on
  `main`; `19-CONTEXT.md` and `19-DISCUSSION-LOG.md` committed at `90f9822`. Phase 19 carries
  Phase 18's `B0` (D-IMPL-151) -- the two client-seam integrity checks that cannot fail. FOURTEEN
  DECISIONS captured as `C-01`..`C-14` (a namespace deliberately distinct from the client spec's
  `D-NN` and the log's `D-IMPL-NN`; `D-05`/`D-11`/`D-12`/`D-13` are REAL SPEC IDS and the draft
  collided with them before renumbering). THE LOAD-BEARING FOUR: (1) the door RE-STATES the
  question it resolved as a `WireRequest` echo at OUTCOME level, compared by total equality, with
  `as_of=None` echoed AS ASKED so the check is total on the default path; (2) THE ADAPTER SEAM IS
  RETYPED TO `ask(WireRequest) -> bytes` -- amending `D-11` and `CLNT-05` -- so `decode_outcome`
  moves onto the shipped path and no adapter constructs an outcome; (3) SYMMETRIC SERIALIZATION,
  so a producer-side door entry echoes WHAT IT PARSED and the check is live IN-PROCESS, not only
  where a pipe exists; (4) the conformance suite gains GENERIC TAMPER LEGS via a byte-corrupting
  wrapper -- possible only because the seam is now bytes -- so `official adapter` comes to mean
  `its integrity checks are demonstrably live`. Signing is OUT of scope and NO signature member is
  reserved: the restored claim is NON-ADVERSARIAL integrity, stated precisely, and `D-GATE-18`'s
  standing prose constraint is REPLACED BY A NARROWER TRUE SENTENCE rather than lifted. HTTP is
  RECONCILED NOT CONVERTED -- body stays the vessel, the echo joins the `X-CCF-*` siblings,
  `D-IMPL-126` stands verbatim. Scope held narrow on `B0` per `D-IMPL-146`. NOTE ON THIS FILE:
  `state.record-session` was invoked once, returned `recorded: false` -- and CORRUPTED THE FILE
  ANYWAY (656 -> 536 lines, `status` flipped to `completed`, `last_activity`/`stopped_at`/`progress`
  destroyed). Restored from a pre-call backup, verified byte-identical to HEAD, then hand-edited.
  The `progress:` block below is LEFT UNTOUCHED AND IS STALE: it predates Phase 18's close and
  Phase 16's retirement moving 14 plans out of discovery, and reconstructing those counts from
  memory rather than measurement is how the ROADMAP rows went wrong twice already. Recount from
  `.planning/ROADMAP.md` before trusting it.
  2026-08-17 -- PHASE 18 OPENED on the MCP transport (D-IMPL-147, Dave). Phase 17 remains CLOSED,
  GATED AND MERGED (D-GATE-17; `phase-17` merged --no-ff at b32348f after a green Actions run on
  the exact commit merged, run 31995656672 @ 44b1f758 -- the condition Dave set; merged `main`
  re-verified independently at ci-quick-suite exit 0, 3739 passed / 0 failed / 2 skipped / 172
  deselected). The roadmap ended at Phase 17, so the next phase was UNDEFINED rather than merely
  unplanned; four candidates were put to Dave and the MCP door + adapter was ruled, because the
  conformance suite was ALREADY WRITTEN to take a second subject and a single adapter cannot
  falsify a claim about adapters. Plan `17-10` LIFTED from Phase 17 into Phase 18 -- file moved,
  ID DELIBERATELY RETAINED as `17-10` (three shipped test docstrings and two immutable decision
  entries cite it; plan discovery is directory-scoped and prefix-agnostic, so the rename was
  unnecessary). Deferral banner AMENDED, not deleted. Branch `phase-18` cut from `main`. Four
  premises re-measured before the lift, all favourable -- see stopped_at. Two ROADMAP staleness
  defects corrected in passing: Phase 17 had NO BULLET in the Phases list at all, and its progress
  row read `0/10 -- Planned` through its entire execution, gate and merge.
progress:
  total_phases: 18
  completed_phases: 16
  total_plans: 180
  completed_plans: 166
  percent: 94
stopped_at: >-
  TWO PHASES ARE OPEN AND NEITHER IS PLANNED, AND THEY ARE INDEPENDENT OF EACH OTHER. BY ROADMAP
  ORDER the next action is `/clear` then `/gsd:plan-phase 18.1` (or `/gsd:discuss-phase 18.1`
  first, which is worth it: `how simple is simple enough` and the README's exact framing are
  gray areas planning should not invent). PHASE 19 IS ALSO READY and is FULLY DISCUSSED --
  `19-CONTEXT.md` exists with 14 decisions. EITHER ORDER IS SAFE: 18.1 as re-cut on 2026-08-18
  touches the example, `binding.yaml`, the adapter's binding-string parsing and the README --
  NOT the client seam -- so it does not collide with Phase 19's wire-shape change. (The earlier
  draft of 18.1 DID collide, which is one of the reasons it was withdrawn.)
  PHASE 19 IS DISCUSSED, NOT PLANNED. The NEXT ACTION is `/clear` then
  `/gsd:plan-phase 19` against
  `.planning/phases/19-the-client-seam-integrity-checks-must-be-able-to-fail-insert/19-CONTEXT.md`.
  No phase branch is cut yet and no plan exists. TWO RESIDUALS were left to planning ON PURPOSE:
  whether out-of-tree adapters get a deprecation window or break cleanly at the seam type change
  (pre-1.0 argues break), and where the producer-side door entry lives
  (`src/ccf/products/door.py` is the presumptive home, since `src/` cannot import `runtime/`).
  THE PHASE'S OWN SUCCESS SENTENCE, from the ROADMAP: a control that answers a DIFFERENT QUESTION
  must be caught by a SINGLE-TRANSPORT client, not only by the cross-adapter parity diff -- any
  proof requiring two subjects has not discharged it, because parity is blind by construction to a
  check broken identically on both.
  EVERYTHING BELOW THIS LINE IS THE PHASE 18 RECORD, SUPERSEDED AS TO NEXT ACTION ONLY.
  PHASE 18 WAS OPEN AND READY TO EXECUTE when this was written; it has since executed, gated
  (`D-GATE-18`) and merged (`e57c93c`). Nothing is part-done: the phase container was built this
  session and no task has run. The NEXT ACTION is `/gsd:execute-phase 18` on branch `phase-18`
  (cut from `main` at b32348f; `main` itself is untouched, pushed, clean and green).
  WHAT PHASE 18 IS: the MCP transport -- the second door and the portability proof. ONE plan,
  `17-10-PLAN.md`, FOUR tasks: (1) the egress tool stops hard-wiring `parameters={}` so a product
  class declaring a required parameter becomes reachable over MCP, with NO coercion guessing and
  NO wider than the HTTP door, proven by ONE shared case table run against BOTH doors; (2) the MCP
  door emits the canonical refusal envelope while a GOVERNANCE refusal (ProductEntitlementRefused)
  still RAISES -- that boundary is asserted so it reads as a decision rather than an omission;
  (3) `mcp+stdio` ships as the second official adapter, sync at the surface with the async client
  bridged internally, registered by ONE dict entry, constructing NO Result; (4) the adapter is
  bound into the conformance suite. Requirements CLNT-12, CLNT-15.
  THE PLAN FILE IS `.planning/phases/18-mcp-transport-the-second-door-and-the-portability-proof/17-10-PLAN.md`
  -- note the `17-10` NAME INSIDE THE PHASE-18 DIRECTORY. THAT IS DELIBERATE AND MUST NOT BE
  "TIDIED": three shipped test docstrings (tests/examples/test_client_example_purity.py, and
  tests/client/conformance/test_inprocess_conformance.py TWICE) and two IMMUTABLE decision entries
  (D-IMPL-146, D-GATE-17) cite `17-10` as a stable identifier per D-IMPL-144, and plan discovery is
  DIRECTORY-SCOPED and prefix-agnostic ("$PHASE_DIR"/*-PLAN.md) so the rename was never needed.
  The deferral banner was AMENDED to record the lift, not deleted -- same discipline the plan
  itself applies to the egress docstring: keep the reasoning, change the behaviour.
  FOUR PREMISES RE-MEASURED on `main` @ b32348f BEFORE the lift, so the phase starts on facts:
  (a) `mcp==1.28.1` IS ALREADY A DECLARED, PINNED DEPENDENCY and installed, so the plan's T-17-SC
  blocking human checkpoint for an [ASSUMED] package DOES NOT FIRE and no install is owed; (b) all
  seven referenced artifacts exist (suite.py 759L, inprocess 445L, egress 599L, plus binding,
  codec, refusal, test_inprocess_conformance); (c) TASK 3's HARNESS-LINT BOUNDARY QUESTION IS
  ANSWERED NEGATIVE, empirically -- src/ ALREADY imports `mcp` in FOUR modules (ccf.mcp.client,
  ccf.artifacts.mcp_store, ccf.signal.mcp_source, ccf.signal.mcp_envelope_map) and
  tools/lints/harness_imports.py denies a frozenset of HARNESS packages that does not contain MCP,
  because MCP is CCF's own integration surface (CLAUDE.md §7.1); the lint is green today with
  those imports, so the adapter's import is permitted and NO D-IMPL is owed; (d) 17-09, the former
  depends_on, is merged -- so `wave: 8, depends_on: ["17-09"]` became `wave: 1, depends_on: []`.
  TWO THINGS THE PHASE MUST BE WILLING TO FALSIFY RATHER THAN SATISFY: (1) `suite.py` MUST NOT
  CHANGE -- if binding a real second adapter requires editing it, the suite was not
  adapter-agnostic and that is a FINDING against 17-07, not a quiet edit; `git diff
  tests/client/conformance/suite.py` being empty is the claim. (2) The `parameters={}` hard-wiring
  has a RECORDED REASON (a flat tool-argument map cannot carry D-IMPL-103's nested declared types
  without guessing coercions, and a declared-parameter surface would make the tool wider than the
  HTTP door) -- that reason is a CONSTRAINT ON THE FIX, not an obstacle to it: AMEND the docstring
  paragraph, never delete it.
  STILL DEFERRED AND NOT LIFTED: 17-08 remains in the PHASE 17 directory under its D-IMPL-146
  banner, BLOCKED ON REAL WORK rather than sequencing -- `refuse_request` would have no surviving
  demonstration anywhere in examples/ once the s1 trees go, and
  tools/docs_tests/test_resolver_seam_obligations.py::test_both_seams_cite_both_call_sites requires
  TWO DISTINCT cited examples per seam with the cite-it-twice escape closed by design. The remedy
  is to WRITE a producer-side example, not to relax a gate -- and the same hazard sits on the OTHER
  refusal, because the quarantined 00-08 group holds the sole refuse_bound_payload call site.
  PHASE 16 IS RETIRED, NOT OPEN. Ruled 2026-08-17 (`D-IMPL-152`): retired, not paused, not
  parked, NOT RESUMABLE. It executed 6 of 21 plans and stopped when its example surface was
  rejected; Phase 17 restarted from the client side with `examples/hw1-companies-over-revenue`
  and Phase 18 added an MCP server to that same example, which is the direction of travel --
  evolve the working example outward on the client and context-production sides. The 14
  unexecuted plans are MOVED to `.planning/phases/16-*/abandoned/` so plan discovery stops
  counting them; they are history and a checklist, NOT a work queue, and nothing is executed
  from there. THE PLAN SET IS RETIRED; THE OBLIGATIONS ARE NOT DISCHARGED -- §9 examples 01-04,
  the adopters guide and `make ci`'s documented claim are still owed and must be RE-DERIVED
  against the surface that exists when each becomes current, never lifted from `abandoned/`.
  Earlier text anywhere in this file saying Phase 16 is parked, open, or should be resumed at
  7/21 is SUPERSEDED. See `RETIRED.md` in the phase directory.
  ROADMAP CORRECTIONS made this session, recorded because neither defect was introduced this
  session and both were load-bearing: PHASE 17 HAD NO BULLET IN THE PHASES LIST AT ALL (planned,
  executed, gated and merged with a detail section and a progress row but no entry), and its
  progress row read `0/10 -- Planned 2026-08-15` throughout. The absent-box case is NOT cosmetic:
  the Phase 14.1 note records that an unchecked box once made roadmap.analyze return
  next_phase: "14.1", routing auto-advance into a phase deliberately never planned. Also note the
  frontmatter's total_phases: 18 is now ACCURATE -- it was ahead of the roadmap until Phase 18 was
  written, and the discrepancy the last handoff flagged resolved itself rather than being fixed.
  ADVISORY, pre-existing and NOT fixed: at least ten `DECISIONS.md:NN` LINE-ANCHORED citations
  survive across the tree (lines 49, 227, 278-338), which contradicts D-IMPL-144's stable-ID rule.
  D-IMPL-147 was APPENDED at the end of the file specifically so no anchor shifted; a future
  insertion ANYWHERE ABOVE line 442 will silently stale them.
  KNOWN CONSEQUENCE, recorded not fixed: the example's headline command prints `0 of 0 assembled`,
  D_c 1.0000, fail_closed on a clean checkout, because D-32 forbids committing data to examples/
  and nothing populates a deployment. The MECHANISM IS HONEST -- the empty-assembly branch refusing
  a confident number about a graph that said nothing -- and no test depends on a populated
  deployment (464 passed after deleting both generated paths), so CI is unaffected.
  PROCESS ITEM to carry: a plan should not ship an artifact AND the gate that judges it. 17-09 did
  both; two outside reviewers found the detectors genuinely constrain the shape anyway ("detector
  quality is good; independence is not"), and the real shaping turned out to be elsewhere -- two
  coverage floors that gained headroom in-phase and were not re-raised.
  MEASUREMENT HAZARDS, all confirmed 2026-08-16, all of one family -- machinery that reports
  confidently wrong rather than failing: (a) `make ... | tail -N` REPORTS TAIL'S EXIT CODE, and
  echoing an exit code is not branching on it; the session reported a green tree that was red
  twice. Use `make X > log 2>&1; echo "EXIT=$?"` AND branch on it. (b) THE VENV'S EDITABLE INSTALL
  RESOLVES `ccf` TO THE MAIN CHECKOUT, so any worktree measurement without PYTHONPATH=src:runtime
  reads code the executor did not write. (c) RETIREMENT-COUPLINGS.md SWEEPS THE PLANNING TREE
  INCLUDING A PLAN'S OWN SUMMARY -- write the SUMMARY first, then re-sweep. (d) Actions' checkout
  is fetch-depth 1, and a shallow clone's grafted root appears to introduce every file; ask
  `git rev-parse --is-shallow-repository` rather than inferring from an empty log.
  ADVISORY FINDINGS carried out of the phase unfixed and enumerated in HANDOFF-2026-08-17.md and
  in 17-CLOSE-REVIEWS.md / 17-REVIEW.md: the per-module budget gate, the client exception taxonomy
  leaking past TransportError, `_parse` swallowing SyntaxError under a `# pragma: no cover` that
  admits the branch never ran, the documentation-only credential posture on `connection:`, the
  purity gate admitting any ccf.client.* submodule, the projection docstring overclaim, the
  required[0] positional assumption, load_reference mutating sys.path, and `question.asked_at` now
  optional and read by nothing.
  SECURITY, OUTSTANDING AND DAVE'S: revoke the three fine-grained PATs pasted into the 2026-08-10
  transcript, plus any created 2026-08-16, at github.com/settings/personal-access-tokens.
  THE PHASE'S LESSON, at ELEVEN instances and unchanged: every defect found was in VERIFICATION
  MACHINERY or in PLANS, never in mechanism -- a check that stops checking, or one that keeps
  reporting green while verifying the wrong thing. They share a shape: treating ABSENCE OF A
  FAILURE SIGNAL as PRESENCE OF A SUCCESS SIGNAL. The correct model has three states -- pass, fail,
  and DON'T KNOW -- and the bug is collapsing "don't know" into "pass". Two rules now written into
  the code they govern: a floor is only a floor while it equals the count, and the plan that adds a
  witness is the plan that must raise it; and a mirror asserted in a comment is not a mirror.
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
