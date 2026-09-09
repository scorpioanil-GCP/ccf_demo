---
gsd_state_version: 1.0
milestone: v0.2
milestone_name: Performance, Documentation & Demonstration
status: executing
last_updated: "2026-09-09T00:25:00.000Z"
last_activity: >-
  **PHASE 24.10 IS EXECUTED — all five plans, five waves, 22 commits on `phase-24.10`, tip `0a7d5495`. NOT pushed, NOT merged, NO `D-GATE`. Awaiting Dave's evaluation of the build.** **THE STOP-RULE VERDICT IS TERMINAL STATE B: cp-05 CANNOT use the canonical SDK path.** Plan 05 drove cp-05's shipped declarations, unmodified, through `GovernedResolver` and got a served product describing a family of **0** over an L3 holding 77 entities and 100 relationship claims — every universal gate green, content address minted, replay record filed. Not a thinner answer than cp-05's; a confidently wrong one. Plan 04 ran the same experiment on `s1-01` and also reached terminal state B. So `R-03`'s escalation branch fires on measured evidence, exactly as Dave framed it: *"If substantial parallel governance code still survives, then we have earned an API redesign with real evidence."* **No redesign was started (`D-25`); cp-05 was not rewired; the fence held — `git diff` against the phase base shows `examples/` untouched apart from `s1-01/spine.py`, which `D-IMPL-282` (4) ruled OPEN.** WHAT LANDED AND WORKS: `R-12` the `replay:` Control Plane section, declared AND consumed (`D-06`); `R-11` the deployment-supplied product gate at the ruled execution point with a seventh `GateRefusal` sibling — exercised live on cp-05's path in both directions; `R-09` discharged as REUSE, no new Protocol declared and none proposed (`SignalSourceProtocol` already answered it — `D-IMPL-277` resolved by discoverability), with the 77/100 evidence reproducing against the live remote estate and its drift guard green. `plan_factory` and `debt_scorer` behaved as ordinary extension points; all four hand-composed spine constructs were replaced. WHAT BLOCKS ADOPTION: six absent seams, each executable as `xfail(strict=True)` carrying its finding id, so the day a seam lands the test XPASSes and fails loudly rather than rotting — `24.10-F-06` (the resolver builds its operator registry with no `similarity_index_version`, stopping at step 4 of its own nine-step composition, so a class using one of the whitepaper's four operator categories cannot be served at all), `F-07` (Pi executed with no seeds while the replay engine seeds from the request — two subjects pin identically; an SDK correctness defect independent of any example, reproducing `DI-15.5-07` on the canonical path), `F-08`, `F-09`, `F-11` (no seam for per-request operator-parameter binding: unbridged 0, bridged 77), `F-12` (boot admits a request-contract declaration the builder refuses three frames down). TWELVE FINDINGS, `24.10-F-01` … `F-12`; `F-13` was deliberately NOT minted, the wave-5 executor refusing to re-mint `F-07` and make one defect look like two. ONE IN-PHASE REGRESSION was found and closed inside the phase: `F-03`, wave 1 registering `ccf.replay-binding` in `SDK_ARTIFACT_CLASSES` with no round-trip case, tripping that module's own vacuity guard (`tests/controlplane` was 179 green at the phase base); closed at `c870fa16`, insertions only, guard untouched. `F-10` is that `s1-01` had been dark behind 33 strict xfails for three phases — un-quarantined, assert/test count identical at 147 before and after, and now 39 passed with the local Fluree leg up. FINAL GATE, measured by the orchestrator across the WHOLE tree in five chunks: **7,329 passed, 8 failed — and all eight are pre-existing, each verified red at the phase base `20499786` in a detached worktree** (`CLAUDE.md` unchanged-since-base, also red on `main`; `test_surface_completeness` = `F-01`, `R-01`/`R-10` shipped fragments named `r01-*.md`/`r10-*.md` that `fragment_paths()`'s `[0-9]*-*.md` glob cannot see, and both rows are ruled untouched; five cp-05 `tests/examples` reds preserved as evidence under `D-IMPL-261`; and the `tools/docs_tests` UAT-roster red). `make lint` rc 0, mypy clean over 218 files. NO cross-AI panel and NO criteria lock — `D-IMPL-280` (4) rules both out for this phase by name, a recorded departure from `D-GATE-19` that a future phase does not inherit. Next free decision id `D-IMPL-285`.

  **PHASE 24.9 IS DISCUSSED AND DESIGNED — `D-IMPL-270` (Dave, 2026-09-06 23:39 MST): the phase EXISTS as a SMALL, REAL PHASE, six rulings, `1A 2A 3A 4A` plus one refinement.** Phase 24.9 did NOT exist at the start of the sitting (`init.phase-op` returned `phase_found: false`; no reference in DECISIONS, ROADMAP or STATE); the sitting decided whether it should, on the evidence of `.planning/PROOF-INVENTORY.md`. Dave, verbatim: *"24.9 should exist as a small, real phase. The subject is proof infrastructure, and that is exactly where I want the criteria lock and gate discipline rather than a casual tooling chore. Keep it to the three core items plus opportunistic migration only where needed to prove the harness."* **THE THREE CORE ITEMS:** (i) fix `24.8-C-03` by NARROWING the `CLAUDE.md` claim — *"Do not generalize a one-off lifetime bug into a fence-expiry framework, and do not retire the check entirely if a precise durable invariant can be stated"*; (ii) promote `_scratch_egress` to ONE tested sabotage harness; (iii) unify the real-tree guard under ONE canonical mechanism. **THE REFINEMENT DAVE ADDED UNPROMPTED, and what makes this a phase not a refactor:** *"the shared harness should not merely centralize the five-step scratch-import pattern. It should make the proof HARDER TO MISUSE than the local copies were. In particular, the harness must fail if the requested mutation did not actually alter the scratch source, and its real-tree guard should come from one canonical mechanism/roster rather than conventionally named local tests."* **FENCE:** `tests/` and `tools/` OPEN; **`src/` CLOSED** (Dave: *"C-02 belongs to a phase that legitimately opens `src/`"*), `runtime/` CLOSED by the same logic; `examples/` frozen (`D-IMPL-261`), `tests/examples/` quarantine-only (`D-IMPL-263`). **EXPLICITLY OUT:** P-6 (the ~70 `ast` sites) stays UNMEASURED; `24.8-C-02` stays OPEN for the next phase that opens `src/`; `24.8-C-01` untouched; bulk migration of the 40 call sites; any fence-expiry framework. **THE INVENTORY WAS RE-MEASURED BEFORE ANY QUESTION REACHED DAVE, AND ONE COUNT WAS WRONG:** P-2 was reported as 14 modules under 2 names; the tree holds **16 defining modules under 4 names** (10/4/1/1), measured without a prefix assumption — **the document arguing that this naming split yields confidently wrong roster answers was itself handed one by it.** Two further modules CITE a guard in prose without defining one, so a naive `grep -rln` returns 18 and over-counts by two: defining roster 16, mentioning roster 18. P-1 confirmed at 46 sites / 40 test modules in `tests/` (+1 in `tools/`) with a zero-hit positive control; P-3 confirmed at population ONE. Corrected at `13c8bc39`, merged `--no-ff` to `main` at `309f125e` per ruling (4). **THE CENTRAL DESIGN FINDING, FOUND WHILE SCOUTING AFTER THE RULING AND NOT ANTICIPATED BY THE INVENTORY:** the 16 guards use **THREE mechanisms** — byte-snapshot (~10), git status/diff (4), predicate re-run (2) — and **the name does not predict the mechanism** (`test_present_tense_sweep` is named `control` and uses byte-snapshot; `test_operator_tier_differential` is named `control` and uses git). **TWO guards carry explicit reasoned arguments AGAINST the git mechanism four others use** — `test_refusal_envelope.py`: *"A blanket `git status` check would go red for a developer with any unrelated uncommitted edit under `src/` — a guard that fails on correct work teaches people to ignore it"* — so unifying naively on git would REGRESS a documented decision. Also found: `_scratch_egress` **already carries** `assert mutated != source, "the sabotage did not take"` at line 970, so it already satisfies the refinement's first half. **NO CRITERIA — `D-GATE-19` holds:** authored at the planning sitting after research and the pattern map, LOCKED with a pinned digest BEFORE Wave 1. NOT researched, NOT planned. No `phase-24.9` branch yet — it forks at planning from the commit carrying this sitting, per 24.8's `8567d683` pattern. **Next:** `/clear`, then `/gsd-plan-phase 24.9`. Next free id `D-IMPL-271`. ROADMAP entry hand-authored (checklist + `### Phase` section); STATE head hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.8 IS CLOSED — `D-GATE-24.8` (Dave, 2026-09-06 20:34 MST): BUILD APPROVED; the §3.1 CROSS-AI PANEL IS SKIPPED BY BUILD-EVALUATION RULING (`D-IMPL-269`).** Dave, verbatim: *"The result is exactly what this phase was supposed to do: one ruled traversal semantic, one function changed, red-before/green-after proof on the same cases, agreement across all seven backends, and no movement in the surrounding contracts, replay, adapters, examples, or other operator families. I see no reason to reopen the mechanism."* **THE PANEL SKIP IS A PROPORTIONALITY RULING, NOT A REJECTION OF PANELS** — verbatim: *"Review effort should scale with unresolved architectural uncertainty and implementation breadth, not run automatically because a phase reached its end."* For 24.8 both are low: the mechanism was ruled before implementation, the AST shows one changed definition of 29, the differential is proven on both sides of the phase boundary, all seven backends agree, and the surrounding surface is proven unmoved — so *"running another six-bundle panel now is more likely to generate another proof-of-proof tail than to materially increase confidence in a two-file, one-function semantic correction."* The staged `24.8-PANEL/` packet REMAINS in the tree as evidence the review was available and deliberately not invoked. This is the SECOND consecutive skip by ruling (`D-IMPL-266` for 24.7); each is a per-phase judgment on that phase's evidence and **neither establishes a default**. No single-agent code review was required by this gate either. **THREE CARRIES, ALL OPEN, EACH WITH A NAMED DESTINATION:** `24.8-C-01` unresolved-reference observability — deferred exactly as designed, no change; `24.8-C-02` the stale `src/ccf/graph/protocols.py` MODULE DOCSTRING version claim — carried as a DOCUMENTATION / API-SURFACE item to the next phase that owns that file or the next cleanup sitting, and when fixed it must *"describe the actual current semantics/version rather than simply bumping a number mechanically"*; `24.8-C-03` (NEW ID assigned at the gate) the `CLAUDE.md` `PHASE_BASE` pin — carried BY ID to the next PROOF/TOOLING CLEANUP SITTING and **EXPLICITLY NOT accepted as a permanent standing red**, because it is *"a defect in proof machinery created by 24.6: a constant was pinned and then invalidated by that same phase's later edit."* **TWO GENERAL LESSONS PRESERVED AT DAVE'S INSTRUCTION.** (1) On pinning: *"if the thing being pinned is legitimately mutable project governance, a raw constant may be the wrong proof mechanism."* (2) On where risk lives — the phase's most transferable finding, since across five waves roughly ten defects surfaced and EVERY ONE was in proof machinery while NONE was in the mechanism: *"When semantics are ruled before coding, mechanism risk collapses; verification machinery becomes the higher-risk surface."* Design consequence, verbatim: *"We should spend less effort generating layers of novel verification and more effort making a smaller number of proof instruments simple, reusable, and themselves testable."* **WHAT SHIPPED:** an edge endpoint carrying no entity claim in the view is an *unresolved reference* — legal persisted state, never a walk start, never a hop, consuming no depth, no placeholder ever manufactured; `_bounded_walk` builds the entity universe, endpoint-closes, then walks (mechanism (i), `D-IMPL-268`); `docs/GRAPH_QUERY_SEMANTICS.md` at 1.3.0 with a `GQ-35` entry, amended LINE-NEUTRALLY. Whole-phase source footprint TWO files, ONE changed definition of 29, identifier delta `['closed', 'universe']`. Criterion 13 red-before/green-after on the SAME 23 ids with the red observed on an EMPTY source diff. Four legs measured, zero deferred; differential green on ALL SEVEN `BACKEND_PARAMS`; example rosters md5-identical. Digest `4bf8e226…` reproduced equal to the pin AND the lock's own control value reproduced byte for byte. Ledger row `CP04-G-28` -> `FIXED-24.8`. Next: `phase-24.8` merged `--no-ff` to `main` and pushed. Next free id `D-IMPL-270`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.8 EXECUTED — 7/7 PLANS, ALL 23 CRITERIA RE-MEASURED, AWAITING DAVE'S REVIEW AND THE §3.1 PANEL (2026-09-06 20:05 MST, `phase-24.8`).** G-28 is CLOSED: an edge endpoint carrying no entity claim in the view is an *unresolved reference* — legal persisted state, never a walk start, never a hop, consuming no depth — and `_bounded_walk` now builds the entity universe, endpoint-closes, THEN walks (mechanism (i), `D-IMPL-268`). **The phase's entire source footprint is two files** (`src/ccf/operators/categories.py`, `src/ccf/graph/fallback.py`); an AST comparison of all 29 definitions in `categories.py` shows EXACTLY ONE changed definition, and the whole-phase source identifier delta is `['closed', 'universe']`. **Criterion 13's before/after on the SAME 23 node ids:** batch A `11 failed, 262 passed` -> `284 passed`; batch B `12 failed, 61 passed, 48 skipped` -> `135 passed, 48 skipped`. The reds were observed on a tree whose `git diff 8567d683 -- src runtime` was EMPTY, which is what makes them observations about the SHIPPED walk rather than artifacts of a half-applied fix. Plan 07 re-measured BOTH ENDS by running the base package in a detached worktree with the loaded module path printed: base answers `{A,B}` on G1 and `{A,B,C,D}` at G3 depth 2 where the shipped tree answers `{A}` and `{A,C,D}`. **Four legs measured, ZERO NOT MEASURED**; the differential is green on ALL SEVEN `BACKEND_PARAMS`; all four `tests/examples/` rosters md5-IDENTICAL to baseline. `content_hash(GraphQuery)` proven unmoved by RUNNING the base package against the merged corpus, not inferred from an empty diff. Gates: `make lint` rc 0, `make typecheck` Success 217 files, `make product-gates` 5 trees / 58 declared / 58 executing. **Criteria digest `4bf8e226…4630` REPRODUCED equal to the pin, and the lock's own appended-character control `a4f5f891…` reproduced byte for byte** — so the block is provably the block that was pinned, independently of the digest. Ledger row `CP04-G-28` moved OPEN -> **`FIXED-24.8`**. **PANEL STAGED, NOT INVOKED** — `24.8-PANEL/` holds 6 files with the source INLINED (both changed `src/` files whole), three parts each under the 128KB argv cap with distinct read-proof tokens and a stdin-only rule; zero `API_KEY=`; no `24.8-CLOSE-REVIEWS.md`. The §3.1 panel is DAVE'S to trigger and has NOT run. **THREE CARRIES, ALL OPEN, NONE FIXED IN-PHASE:** (1) the `CLAUDE.md` pin — RED and PRE-EXISTING, proven by RUNNING the test at `8567d683` where it fails identically; it pins `CLAUDE.md` against `1022ad59` while the file moved at `4683f245`, the 24.6 close; criterion 20 forbids a `CLAUDE.md` edit; Dave's three options are re-point the pin, accept a standing red, or fold it into the deferred §9 cleanup sitting. (2) `24.8-C-02`, NEW — the `src/ccf/graph/protocols.py` MODULE DOCSTRING claims a CURRENT rendering at "semantics version 1.0.0", three amendments stale; it is not among the nine sites in RESEARCH § Priority 6 item 4, so criterion 17 does not reach it, and criterion 19 requires `protocols.py` to carry an EMPTY diff, so touching it would VIOLATE a locked criterion; surfaced, not fixed. (3) `24.8-C-01` — observability, deferred by ruling, untouched by design. **TWO BASELINE GAPS STATED, NOT DISCOVERED LATER:** plan 03's § Baseline covered batches A/B/C and the four legs but NOT `tests/invariants` or the top-level surface gates, the partition where cross-plan reds land here (orchestrator ran it: 1 failed, 1108 passed, the one red being the carried `CLAUDE.md` pin); and § Baseline's citation figures are for `382b072b`. **CITATION CENSUS, SETTLED BY MEASUREMENT AFTER THE ORCHESTRATOR BRIEFED A WRONG NUMBER:** 393 at `382b072b`, 419 at the wave-1 merge `f657b5a7`, **431 on the shipped tree** — so plan 05's `+26` was right for ITS tree and plan 07's `+38` is right for the SHIPPED tree; the orchestrator passed plan 05's figure on without its "which tree" qualifier, propagating the very trap plan 05 had warned about, and plan 07 re-measured and reported the difference instead of adopting it. **PLAN-INSTRUMENT CORRECTION, NO RE-PIN OWED:** criterion 15's `_walk` grep was UNSCOPED in plans 04/05/06/07 — it also matched the FUNCTION NAME `test_direction_and_admission_compose_on_the_descendant_walk()`, making the `= 0` assertions UNSATISFIABLE (base 5 unscoped, 4 call-scoped); eight sites re-derived to the call-scoped form; NO locked criterion names a grep, so the digest is UNCHANGED. **ORCHESTRATOR-CAUSED RED, FOUND AND FIXED:** the wave-1 tracking commit reddened the unanchored-Python-citation ratchet; measured 0 such cites at `8567d683`, 1 at `382b072b` (a 24.8 PLANNING commit), 2 after the orchestrator's — both IN-PHASE regressions, both repaired per `D-IMPL-114` WITHOUT raising the ceiling. **THE PHASE'S MOST TRANSFERABLE FINDING:** across five waves EVERY defect landed in PROOF MACHINERY, never in mechanism — plan 01 found its own plan's action and acceptance contradicting each other; plan 02 found criterion 15 unsatisfiable; plan 03 reported three research-vs-measured differences and adopted none; plan 05 caught its own sabotage masking 91 failures because the inserted line contained the token being searched for; plan 06 self-reported FOUR defects in its own verification code; plan 07 self-reported TWO more; the orchestrator reddened a CI gate twice and briefed one wrong number. The mechanism — one ruled decision, one changed function — held throughout. Next: Dave reviews; the §3.1 cross-AI panel on the SHIPPED code; then triage, `D-GATE-24.8`, merge `--no-ff` to `main`, push. Next free id `D-IMPL-269`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.8 WAVE 3 COMPLETE — THE CONFORMING WALK VERIFIED ON ALL SEVEN BACKENDS (2026-09-06 19:33 MST, `phase-24.8` at `7f5ffa3f`).** Plan 06 ran alone on the main tree. **Four legs MEASURED, zero NOT MEASURED**, each exactly `+7 passed` and the `+7` is exactly that leg's seven differential ids — 28 ids, all passed; with batch B's sqlite/memory/demo/postgres the new operator-tier differential is green on ALL SEVEN `BACKEND_PARAMS`. All four `tests/examples/` rosters are **md5-identical** to their baselines, not merely `comm -3`-empty. An AST comparison of all 29 definitions in `categories.py` shows **exactly one definition changed — `_bounded_walk`** — and the phase's entire source identifier delta is `['closed', 'universe']`. `content_hash(GraphQuery)` was PROVEN not to move by running the BASE tree's own `ccf` package against the merged corpus (identical aggregate `75b9b4e41804acd2`), not inferred from an empty diff. Seven gate lines green. **BOTH CARRIES HONORED:** carry 1 re-measured — 49 shared postgres/fluree ids, 46 skip-on-postgres / xfail-on-fluree, so an aggregate comparison would have manufactured up to 46 FALSE regressions; carry 2 — plan 06 made no citation-census claim at all, recorded as deliberately not re-derived, so the 26-cite growth was never at risk. **THE ONE RED IS CARRIED, AND WAS CLASSIFIED BY MEASUREMENT:** `test_determination_authority_disclosure_delivery.py::test_the_document_is_unchanged_since_the_phase_base` on the `CLAUDE.md` parametrization fails IDENTICALLY when run at `8567d683`; it pins `CLAUDE.md` against `1022ad59` while `CLAUDE.md` last moved at `4683f245` (the 24.6 close). Criterion 20 forbids a `CLAUDE.md` edit, so it is CARRIED. Three options at the close, for Dave: repoint the pin, accept a standing red, or fold it into the deferred CLAUDE.md §9 cleanup sitting. **FOUR INSTRUMENT DEFECTS, ALL IN PLAN 06'S OWN VERIFICATION CODE, ALL CAUGHT BY THEIR OWN CONTROLS AND RECORDED RATHER THAN QUIETLY CORRECTED:** a fabricated control block with an invented count (measured 7, written 6); an AST sabotage that failed to fire because it planted only a comment; a prose classifier that called `__all__ = ["answer"]` prose because the line contains a string; and a definition count taken from arithmetic that was wrong by one. Separately one base measurement errored on a worktree path artifact and its number was DISCARDED rather than substituted — using it would have made the growth read 178 instead of 144. This is the fifth consecutive wave in which the phase's defects landed in proof machinery rather than in mechanism. Next: Wave 4 = plan 07 alone on the MAIN tree — close evidence, all 23 criteria re-measured with command/output/control, the criteria digest reproduced, ledger row `CP04-G-28` -> `FIXED-24.8`, carries `24.8-C-01` and `24.8-C-02` left OPEN, the §3.1 panel packet STAGED NOT RUN. The orchestrator regenerates `docs/surface/examples/RETIREMENT-COUPLINGS.md` as the FINAL action after the last tracking write. Next free id `D-IMPL-269`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.8 WAVE 2 MERGED — ALL 23 REDS GREEN ON THE SHIPPED WALK (2026-09-06 18:55 MST, `phase-24.8` at `ba47f8e6`).** Plans 04 and 05 complete, merged `--no-ff`, worktrees removed. The before/after criterion 13 exists to produce is now on the record: batch A `11 failed, 262 passed` -> `284 passed`; batch B `12 failed, 61 passed, 48 skipped` -> `135 passed, 48 skipped` (batch B grown by `test_similarity_index.py` per plan 06); batch C 39 and the golden replay 7 unchanged. Plan 04 landed mechanism (i) — universe, close, then walk — as ONE executable line of shape change; `ADMISSION_PREDICATE` and the `if not forward:` line each still count 1 and are byte-identical; no `ccf.graph.fallback` import; `class map is not a hop` 2 -> 0; five copy-and-mutate sabotages RED with `git status --short -- src/` empty after each. Plan 05 took `docs/GRAPH_QUERY_SEMANTICS.md` to 1.3.0 LINE-NEUTRALLY (746 -> 808, all 62 in the appended `GQ-35` entry; heading roster diff empty; clause hunks sum 20 = 20) and re-derived the three bare-`_walk` oracles to `fallback.answer`. Gates on the merged tree: `make lint` rc 0, `make typecheck` Success (217 files), `make product-gates` 5 trees / 58 declared / 58 executing rc 0; `examples/` fence EMPTY; criterion 19's `backends`+`reader.py`+`protocols.py` diff EMPTY; source changed by the whole phase is exactly `src/ccf/graph/fallback.py` and `src/ccf/operators/categories.py`. **Full `tests/invariants` + top-level surface partition (NOT covered by plan 03's baseline — a baseline gap to state at close): 1 failed, 1108 passed.** That one red is `test_determination_authority_disclosure_delivery.py::test_the_document_is_unchanged_since_the_phase_base[CLAUDE.md]` and is PROVABLY PRE-EXISTING — both its inputs (`CLAUDE.md` and the test module) are byte-identical to the fork point `8567d683`, and `CLAUDE.md` last changed at `4683f245`, the 24.6 close itself; the test's own message says criterion 27 leaves the revision to Dave. 24.8 criterion 20 forbids a `CLAUDE.md` edit, so it is CARRIED, not fixed. **ORCHESTRATOR SELF-INFLICTED RED, FOUND AND FIXED:** the wave-1 tracking commit `f657b5a7` added a line-anchored Python citation to `.planning/STATE.md` and reddened `tests/invariants/test_citation_coverage.py::test_the_unanchored_python_citation_population_cannot_regrow` (ceiling 0, found 2). Measured: 0 such cites at `8567d683`, 1 at `382b072b` (added by a 24.8 PLANNING commit), 2 after mine — so BOTH were in-phase regressions, not carries. Fixed per `D-IMPL-114` without raising the ratchet: mine converted to the `path.py::Symbol` form, the planning-era one (a record ABOUT correcting a line number) reworded so the number stays visible as prose and is no longer a citation. Gate re-run 5 passed; STATE.md length unchanged. **NEW CARRY `24.8-C-02` (for a ruling after the phase, sibling to `24.8-C-01`):** the `src/ccf/graph/protocols.py` MODULE DOCSTRING claims the query contracts render the vocabulary "(semantics version 1.0.0)" — a CURRENT-rendering claim, three amendments stale. It is NOT among the nine sites in RESEARCH § Priority 6 item 4 (that roster names `protocols.py::TraversalSpec`'s docstring, an arrival note that stays true), so criterion 17 does not reach it; criterion 19 requires `protocols.py` to carry an EMPTY diff, so touching it would violate a locked criterion. Plan 05 surfaced it rather than fixing it — correct. **CARRY FOR PLAN 06 (from plan 05):** `24.8-LEGS.md` § Baseline cite figures (393/49/12/19/244) were measured at `382b072b`; the merged tree carries 26 MORE citations from this phase's own new test modules (419/51/17/23/260) — compare against the right tree or the phase will appear to have drifted 26 cites. **CARRY FOR PLAN 06 (from plan 03):** of the 49 postgres/fluree overlap ids, 46 are skip-on-postgres / xfail-on-fluree — `comm -3` PER LEG under matching env (postgres with `CCF_TEST_FLUREE_URL` unset), never against the 184-id aggregate. Next: Wave 3 = plan 06 alone on the MAIN tree (batches, four legs, controls). Next free id `D-IMPL-269`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.8 WAVE 1 MERGED — RED BY DESIGN, OBSERVED ON UNMODIFIED SOURCE (2026-09-06 18:19 MST, `phase-24.8` at `881f543d`).** Plans 01, 02 and 03 complete and merged `--no-ff`; both executor worktrees removed. **23 reds on the merged tree with `git diff 8567d683 -- src runtime` EMPTY** — the failures are observations about the SHIPPED `_bounded_walk`, not a half-applied fix (criterion 13). Batch A `11 failed, 262 passed` (10 in `test_traversal_unresolved_reference.py` + the `[traversal.typed-neighborhood]` idempotence red) = plan 02's predicted roster node-for-node. Batch B `12 failed, 61 passed, 48 skipped` — 3 functions x `[sqlite|memory|demo|postgres]` in `test_operator_tier_differential.py`; every message names "operator tier", none names "query tier", and `test_substrate_differential.py` has ZERO failures (criterion 14 holds: adapters already agree with the fallback on the dangling shape with no adapter change). Batch C 39 passed and the golden replay 7 passed, both equal to plan 03's baseline; `tools.lints --all` rc 0; the `examples/` fence empty. Plan 03 measured ALL FOUR legs (none NOT MEASURED), found NO pre-phase red, and its 184-id `tests/examples/` roster is entirely 24.7 `D-IMPL-264` quarantine or env skip with zero traversal/`GQ-*`/depth ids. **CARRY FOR PLAN 06:** of the 49 postgres/fluree overlap ids, 46 are skip-on-postgres / xfail-on-fluree — `comm -3` PER LEG under the same env (postgres with `CCF_TEST_FLUREE_URL` unset), never against the aggregate. **PLAN-INSTRUMENT CORRECTION (orchestrator, 2026-09-06):** plan 02 found criterion 15's `grep -rn "_walk(" | grep -v "_bounded_walk("` is UNSCOPED — it also matches the function name `test_traversal_direction.py::test_direction_and_admission_compose_on_the_descendant_walk`, so the `= 0` assertions in plans 05/06/07 were UNSATISFIABLE (base reads 5 unscoped, 4 call-scoped). Eight sites in plans 04/05/06/07 re-derived to the call-scoped `grep -rnE '(^|[^_a-zA-Z0-9])_walk\('`; verified satisfiable (tree-wide scoped = 4 today: 3 direction + 1 admission; plan 04 clears 1, plan 05 clears 3). No locked criterion names a grep, so the criteria digest is UNCHANGED and no re-pin is owed. Plan 02's own record left as executed. Next: Wave 2 = plan 04 (mechanism (i)) || plan 05 (1.3.0 amendment), both worktrees off `881f543d`. Plan 04 must turn 23 ids green (12 + 11), read from the two SUMMARY rosters, not a count. Next free id `D-IMPL-269`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.8 PLANNED — 7 plans / 4 waves from the 23 locked criteria, checker PASSED after one revision (2026-09-06 13:40 MST, `phase-24.8`); NOT EXECUTED, awaiting Dave's GO.** Round 1: 2 blockers + 10 warnings, every one verified against the tree before acting — B-1 criterion 15's instrument was false by construction (research's F-2 roster missed THREE bare `_walk` oracles in `test_traversal_direction.py` :250/:308/:768; plan 05 now re-derives them to `fallback.answer`); B-2 the "annotate on exclusion" sabotage was unconditional and could not red the twin-provenance instrument (now conditional, asserted through the instrument's own helper). Round 2: 0 blockers, 2 one-line warnings fixed by hand (plan 05 hunk arithmetic wording; plan 06 base count 27→26 — verify rosters, not counts). Waves: 1 = 01 ‖ 02 (worktrees) ‖ 03 (main tree, legs); 2 = 04 ‖ 05; 3 = 06 (main); 4 = 07 (close evidence, panel STAGED not run, retirement report last). **The wave-1 merge is RED by design** — plans 01/02 commit the differential and the in-process module unmarked so the red is OBSERVED on the shipped walk (criterion 13); plan 04 turns them green. Criteria digest `4bf8e226…` unchanged. Decision-coverage gate skipped (no D-NN in CONTEXT form); gap report = whole-milestone table, none mapped here. Next: `/gsd-execute-phase 24.8` on `phase-24.8` after Dave's GO. Next free id `D-IMPL-269`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.8 — 23 CRITERIA LOCKED BY DAVE; MECHANISM (i) RULED — `D-IMPL-268` (2026-09-06 12:34 MST, `phase-24.8`).** Lock as drafted (option a); criterion 4 conforms by close-then-walk inside `_bounded_walk` — *"shared semantics, not necessarily a shared helper function"*, no public promotion of the fallback predicate; the differential must prove DEPTH AND CYCLE consequences, not only membership (carried into planning verbatim in `24.8-CRITERIA-LOCK.md`, not an amendment). Digest pinned `4bf8e226…` with controls (wrap 0/control 1, parser 23, appended-char control differs, lint rc 0, every id covered). Verbatim in `24.8-RULINGS.md` §5. **Planner and checker run next; no plan yet.** Next free id `D-IMPL-269`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.8 — RESEARCHED, VALIDATION AND PATTERN MAP WRITTEN, 23 CRITERIA DRAFTED — AWAITING DAVE'S LOCK (2026-09-06 12:35 MST, `phase-24.8` forked from `main` at `8567d683`, pushed).** `/gsd-plan-phase 24.8` ran as the GO to planning. Research (`604c6554`): G-28 measured, not described — operator tier `{A,B}` vs query tier `{A}` on G1 depth ≥ 2 with `admitted=None`, G3 depth 2 `{A,B,C,D}` vs `{A,C,D}`; 10 of 42 (graph, question) pairs diverge, all six adapters live and 252/252 pushed rows byte-identical to the fallback; eight-walk roster; no per-node depth anywhere; `canonical_bytes(GraphView)` is the one rendering; NO frozen-example test expected to change color; NO stop-and-return findings; three disclosures (F-1 corpus has no G-28 case, F-2 the existing oracle is bare `_walk`, F-3 the shipped walk is not idempotent). `24.8-VALIDATION.md` (`529ed440`). Pattern map: 11 files / 11 analogs, 7 conflicts — two corrected the draft criteria before commit (lint rule is `cite01-resolves`; the curated pin is a `<=` subset assertion, strengthened not re-derived) and one corrected a line cite (`test_traversal_direction.py`, line 535 — research said line 531). **23 criteria DRAFTED one-per-line in ROADMAP (parser 23, wrap detector 0 with control 1, lint rc 0, D-01..D-08/P-1/P-2/24.8-C-01/CP04-G-28 all covered); NOT LOCKED — the lock is Dave's, and the criterion-4 mechanism ((i) close-then-walk recommended vs (iii) shared predicate) is his call at the lock.** No plan written; the planner runs after the lock (`D-GATE-19`). Next free id `D-IMPL-268`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.8 DESIGNED — `D-IMPL-267` (2026-09-06 11:29 MST, `main` after `D-GATE-24.7` at `11247a95`).** `/gsd-discuss-phase 24.8` ran as the design sitting with G-28 as the sole problem: the tree was read first (query tier endpoint-closes before walking — `fallback.py::answer` → `_endpoint_closure` → `_walk`, five pushed adapters held byte-identical; operator tier `categories.py::_bounded_walk` does not, and with `admitted_entity_classes=None` walks THROUGH a claim-less URI to the claimed nodes beyond it, spending depth; `GRAPH_QUERY_SEMANTICS.md` 1.2.0 silent on the operator tier; no test), then Dave's own eight questions went as ONE batch with options and recommendations; he took all eight and sharpened four. Rulings: a dangling endpoint is an UNRESOLVED REFERENCE (legal state, not a traversal member); membership requires an entity claim; no placeholder; exclusion is a traversal semantic (silent) with observability DEFERRED as carry `24.8-C-01`; equivalence is BYTE-IDENTICAL CANONICAL RESULT (semantic result first, then canonical rendering — not internal bytes); one rule for anchors and neighbors; an excluded endpoint consumes NO depth and lies on no path or cycle; family semantics, not an adapter flag — "construct the admitted entity universe first; endpoint-close edges against that universe; then walk", the operator conforms, a new operator-vs-query differential. Two principles verbatim (P-1 state ≠ traversal universe; P-2 execution-path invariance). Files: `24.8-RULINGS.md` (verbatim), `24.8-CONTEXT.md`, `24.8-DISCUSSION-LOG.md`; ROADMAP 24.8 → DISCUSSED AND DESIGNED, NO CRITERIA. CLAUDE.md §9 cleanup stays deferred by Dave. **Next: `/gsd-plan-phase 24.8` — research MEASURES the divergence (minimal graph, both operators vs fallback vs a pushed adapter, depth 1 and 2), enumerates every walk implementation, names the shared canonical rendering and D-07's observable; criteria authored and LOCKED before Wave 1 (`D-GATE-19`); then plans; the phase branch `phase-24.8` forks from `main` at planning.** Next free id `D-IMPL-268`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.7 CLOSED — `D-GATE-24.7` (2026-09-06 10:45 MST, `phase-24.7`; merge `--no-ff` to `main` and push follow this commit).** Dave's build evaluation APPROVED at `8547bd77` (`D-IMPL-266`: panel SKIPPED BY BUILD-EVALUATION RULING — a ruled deviation from §3.1, packet at `24.7-PANEL/` staged and unrun; one single-agent review scoped to the 28 criteria, `D-IMPL-264`/`265`, G-26/G-33; F-A accepted, F-B/F-C non-blocking, F-D a research-denominator miss). The review (`24.7-REVIEW.md`, 3 sabotages restored) returned exactly two items, both verified against the tree and ruled by Dave (§12: *"1a, 2a"*): CR-01 — criterion 2's refusal named the parameter but not the offending default — FIXED at `daeb8710` (message renders `name=default`; test asserts the pair outside pydantic's echo; old message reds it); criterion 18's text listed "/ class declaration" among the trigger pins against am.3 — AMENDED as ONE physical line and RE-PINNED (`D-IMPL-264` am.4; digest `2a63ce90ebf325b3…` supersedes `594aaaf8…`; wrap 0/control 1; parser 28; superseded text preserved in the lock file Amendment 2). Re-measured on the fixed tree: A 2830/1 (carried), B 913/90s, C 570/127s/224 deselected/80xf, D 1850/1 deselected = 6686; lint 0, mypy 217, docs-strict 0, product-gates 58/58, gate-tools 460 · 339/1 (F-E) · 29; regeneration idempotent; FF-01/FF-02 carried as future findings. ROADMAP: checklist [x], progress row Complete, STATUS line closed — all by hand. **Next: merge `--no-ff` to `main`, push `main` and `phase-24.7`; then the next SDK phase per the ledger — 24.8 Traversal Semantics (G-28) is DIRECTION BANKED, its discuss sitting comes first (`D-GATE-19`). CLAUDE.md §9 cleanup (the three example categories of `D-IMPL-265`) is the deferred sitting with Dave.** Next free id `D-IMPL-267`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.7 — EXECUTION COMPLETE, 12/12 PLANS; STOPPED FOR DAVE'S BUILD EVALUATION (2026-09-06 07:50 MST, `phase-24.7` at the wave-8 tip, pushed).** 11 (main tree, base `ad8dc5a9`): `24.7-CLOSE-PREP.md` — ALL 28 CRITERIA HOLD on the shipped tree, each with command, verbatim output and control (sabotages 13, 14, 18 re-executed red and restored); digest `594aaaf8…` reproduces, `112e77b7…` reproduces on `5a493cc5`, wrap detector 0/control 1, gsd parser 28; suite lint 0, mypy 217, A 2830/1, B 913/90s, C 570/127s/224 deselected/80xf, D 1850/1 deselected = 6686 by id, gate-tools 460 · 340/1 · 29, docs-strict 0 — the only reds the two carried pre-phase reds by full node id; FINAL LEGS postgres 193/68s/80xf, fluree 223/85xf, red roster none, xfailed union 162 = Q-A ∪ Q-B by `comm`; `CP04-G-26` DISCHARGED (criteria 1–11), `CP04-G-33` DISCHARGED (12–18); carry rows `24.7-C-01`, `24.7-C-02` OPEN; `24.7-LEGS.md` § Final; `24.7-PANEL/` STAGED (README, known-findings K1–K8, prompt, 9 stdin bundles under the argv cap with read-proof tokens) — NO REVIEWER INVOKED. Close-record findings for Dave: F-A `D-IMPL-265`'s module-level marks deselect 40 green ids beside the 185 red; F-B criterion 21's lock-time grammar predates `D-IMPL-265` (its verbatim instrument prints exactly the twelve `pytestmark` lines); F-C plan 09's literal sabotage 2 fires nothing (K4); F-D RESEARCH's roster walk skipped `perf/` and `archive/`. ROADMAP progress row → 12/12 EXECUTED, NOT Complete. **Per Dave's GO (§9) and `pause-after-the-product-is-built`: NO code review, NO verifier, NO panel, NO `phase.complete`, NO `D-GATE-24.7` until he has evaluated the build. Next: Dave reads `24.7-CLOSE-PREP.md` and the SDK diff (`git diff 6a019322..HEAD -- src runtime`) → decides whether the panel is useful → then §3.1 in order (panel via stdin from `24.7-PANEL/`, single-agent review, verify every finding, fix blocking in-phase) → `D-GATE-24.7` → merge `--no-ff` to `main`.** Next free id `D-IMPL-266`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.7 — WAVE 7 MERGED: `D-IMPL-265` LANDED IN THE HARNESS; ONLY THE TWO CARRIED REDS REMAIN (2026-09-06 07:10 MST, `phase-24.7`; 11/12 plans).** 12 (main tree, base `18e83c25`): `archived` marker registered; `--run-archived` + a deselection hook in `tests/conftest.py`; guard `tests/lints/test_archived_examples_non_gating.py` (classifier = archive path expression AND load/spawn call AND a program entry point `run.py`/`serve.py`/`producer_child.py` — the third kind forced by `test_demo_generator.py` and `test_ext00_fixture_schemas.py`, which load archive HELPERS and stay non-runners; red-before named exactly the twelve; planted unmarked runner → red, reverted → green); the twelve runners + the `crossproc` perf parameter marked (+1 line each; `test_smoke.py` +10/−1 with the `24.7-C-02` comment). **Measured correction to the plan's number: the twelve modules collect 224 ids, not 184 — 40 green tests inside them also exercise archived source; module-level marking deselects 225.** By `comm`: roster − deselected = 0 (every red id left the denominator); deselected − roster = the 40, all inside the twelve modules, enumerated by id in `24.7-LEGS.md` § Archive. Orchestrator's reading: their purpose is also exercising the archive, so this sits inside the ruling as written; noted for Dave, not re-marked per test. Evidence preserved: `--run-archived` over the twelve + param → `2 failed, 40 passed, 183 errors`, the 185 red ids = the 24.7-10 roster both ways. Whole tree on `7f12e2c9`: A 2830/1 (carried `[CLAUDE.md]`), B 913/90 skipped, C 570/127 skipped/**224 deselected**/80 xfailed, D 1850/**1 deselected** = 6686 collected (`6461/6686 (225 deselected)`); lint 0, mypy clean, product-gates 58/58, gate-tools 460 · 339/1 (F-E) · 29; retirement report regenerated. **Criterion 25 is now measurable. Next: plan 11 (wave 8) — close evidence, all 28 criteria re-measured, final legs, panel packet STAGED and NOT run — then Dave's build evaluation BEFORE any panel/review/D-GATE.** Next free id `D-IMPL-266`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.7 — `D-IMPL-265` RULED: `archive/examples/` IS RETIRED HISTORY, NOT A COMPATIBILITY CONSUMER; PLAN 12 ADDED, PLAN 11 → WAVE 8 (2026-09-06 06:45 MST, `phase-24.7`).** Dave, verbatim in `24.7-RULINGS.md` §10 and `docs/DECISIONS.md`: *"No archived source is modified to accommodate 24.7. Tests whose only purpose is exercising those retired examples are removed from the release-gating denominator or explicitly marked archived/non-gating. HW/CP examples remain the supported example and diagnostic surfaces."* Not the `D-IMPL-261` freeze either — three categories: supported examples/probes (`examples/hw-*`, `cp-*`), retired history (`archive/examples/*`, no compatibility maintenance), SDK tests (must stay current). Caution: do not delete the archive. Mechanism chosen after measuring (a move would strand path cites in seven `public/` pages, the retirement sweep and the stale-path gate; the twelve modules share no `tests/conftest.py` fixture): registered `archived` marker + module-level `pytestmark` on the twelve runners and on the `crossproc` perf-smoke parameter + a root-conftest hook deselecting `archived` items unless `--run-archived` + a `tests/lints/` guard that refuses an unmarked archive runner. Carry row `24.7-C-02` (perf `crossproc` suite has no supported server child) OPEN. `24.7-12-PLAN.md` written (wave 7, depends on 10); plan 11 now wave 8, depends on 12; ROADMAP plan list/wave text/progress row hand-edited (12 plans / 8 waves). **Next: dispatch plan 12 on the main tree → gate → plan 11 → build evaluation with Dave BEFORE panel/review/D-GATE.** Next free id `D-IMPL-266`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.7 — WAVE 6 MERGED; PAUSED BEFORE PLAN 11 FOR DAVE'S `archive/` RULING (2026-09-06 00:40 MST, `phase-24.7`; 10/11 plans).** 10 (main tree, base `57ef987b`): regeneration idempotent on the merged tree; export roster from the manifest diff against `6a019322` — 6 added, 0 removed, 5 reshaped, plus 3 names the manifest cannot see, ALL claimed by fragments (unclaimed: none; five surface/schema modules 100 passed); hash transparency — exactly one new defaulted `CCFContract` field (`ArgumentDomain.members`), on both rosters, no edit needed; criterion 24 — all 41 builder + 15 recorder roster ids present by AST walk, counts derived per file, the two intentional absences under `pytest.raises(TypeError)`, roster gaps carried (`perf/suites/replay/conftest.py` present-but-unrostered; `archive/` never walked); the six named assertion tests pass with their controls. Whole tree in the foreground on `6de3aff2`: lint 0, mypy clean (217), product-gates 58/58, docs-strict 0, gate-tools 460 · 340/1 (F-E) · 29; A 2830/1 (carried `[CLAUDE.md]`), B 913/90 skipped, C 610/127 skipped/80 xfailed/**1 + 183**, D 1843/**1**; collected 6679 = 2831 + 1003 + 1001 + 1844 reconciled at the ID level. **Criterion 25 does not hold and cannot until Dave rules on `archive/`: the ONLY reds beyond the two carried pre-phase reds are the 184 archive-class ids in twelve `tests/examples/` modules + `tests/perf_smoke::…[crossproc]`, one cause, the 12 `build_replay_record` calls under `archive/examples/` (00..08 `run.py`, `04-cross-process/producer_child.py`, `external/00-hello-context/serve.py`) that omit `resolution=`; 0 red at the phase base.** Options (unchanged): (1) `archive/examples/` frozen like `examples/` — quarantine ~184 ids across 13 modules, sources untouched; (2) `archive/` is SDK scaffolding — re-derive the 12 sites, no test touched (size favors this). **Plan 11 (close evidence, all 28 criteria re-measured, panel packet STAGED not run) is NOT dispatched — its criterion-25 measurement would be provisional. Resume: Dave rules → the ruled edit lands as a `D-IMPL-265` commit → `/gsd-execute-phase 24.7` runs plan 11 → build evaluation with Dave BEFORE any panel/review/D-GATE.** `phase-24.7` pushed. Next free id `D-IMPL-265`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.7 — WAVE 5 MERGED (2026-09-06 00:10 MST, `phase-24.7`; 9/11 plans).** 08 (main tree, base `08843227`): legs BEFORE — postgres 69 failed + 9 errors, fluree 1 failed + 36 errors = 114 distinct ids, EXACTLY two cause texts: the builder `TypeError` (71: cp-00 27, s1-00 8, s1-01 36) and the shadow-`intent` `ValidationError` (43: cp-01 12, cp-02 17, cp-03 13, cp-04 traversal 1; 39 of them also carry the masked builder cause); no third cause, nothing outside `tests/examples/`, no STOP. 114 strict xfails naming `D-IMPL-264` and the cause (155 marker lines: two fully-red parametrized functions carry one decorator for 5 and 4 ids); plan 05's 48 cp-04 reasons AMENDED — `--runxfail` shows the construction refusal now fires at `assembler.py` ahead of the D-08 site, masking D-08 and the recorder path. AFTER: postgres 193/68 skipped/80 xfailed, fluree 223/85 xfailed, 0 failures/errors; `comm -3` empty at 80=80, 85=85, 162=162 (Q-A ∪ Q-B). RESEARCH correction carried: `test_cp_01_output.py::test_an_unresolvable_anchor_fails_closed` reasoned red under D-01 is GREEN (never constructs the contract) — left unmarked. Fence: `examples/`, `archive/`, `src/`, `runtime/`, census/cycles, tracking files all diff-empty. Chunk C on the marked tree: 610 passed/127 skipped/80 xfailed/**1 failed + 183 errors** — ALL twelve archive-class modules (`test_quickstart_output` 9, `test_agent_basics_output` 17, `test_skilling_output` 18, `test_harness_portability_output` 13, `test_cross_process_output` 13, `test_workflow_hitl_output` 37, `test_decision_replay_output` 34, `test_artifact_store_output` 10, `test_e2e_demo_output` 19, `test_ext00_serve_output` 11, `test_gate_two_divergence` 2, `test_ext00_hardening` 1) = 184 ids + `tests/perf_smoke::…[crossproc]`; none in any roster, none ever in a leg's red roster. **The `archive/examples/` ruling is still owed (options in the wave-4 head; size favors re-deriving the 12 sites). Criterion 25 (chunks 0 failed beyond the two carried reds) CANNOT hold until it is ruled; plan 10 proceeds on rosters/exports and RECORDS the archive class as awaiting ruling; plan 11 waits for the ruling.** Next free id `D-IMPL-265`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.7 — WAVE 4 MERGED (2026-09-05 23:45 MST, `phase-24.7`; 8/11 plans). THE ARCHIVE QUESTION IS LARGER THAN PLAN 06 STATED.** 07 (worktree, base `8dbfb35a`): `ccf.products.request_schema` — the canonical render deriving `enum` and `minimum`/`maximum` from `ArgumentDomain`, NO consumer anywhere in `src/`/`runtime/` (carry row `24.7-C-01` OPEN; fence diff over `runtime/ccf_runtime/{mcp,http_api,cli}` empty); the shadow-`intent` refusal at construction and `refuse_intent`; `GovernedResolver.resolve` judges intent against the declared discovery set (absent = unjudged, declared empty = serves none), pinning the deciding class declaration; four sabotages executed and reverted; all seven frozen declarations confirmed to construct on the unchanged tree first. 09 (worktree): `ReplayResolutionClaimMismatch` + `_verify_resolution_claim` — a marker record is refused iff a pinned binding, resolved at its EXACT version, is a `ProductRequestContract` or `PolicyConstraint`; class-declaration pin proven NOT a trigger; legacy sentinel exempt, golden `13bd250` byte-identical; the plan's literal "drop the legacy exemption" sabotage fires nothing (the sentinel is not JSON, so the shape guard exempts it twice) — the sabotage D-12 forbids (read the sentinel AS a marker) reds exactly the legacy test. Merge `9dddbade` (the two generated docs conflicted, regenerated once, idempotent). Full gate: lint 0, mypy clean (217 files), product-gates 58/58; A 2830/1 (carried `[CLAUDE.md]`), B 913/90 skipped, C 610 passed/127 skipped/2 xfailed/**70 failed + 192 errors**, D 1843/**1** (the archive perf smoke); gate-tools 460 · 340/1 (F-E) · 29. **Chunk C classified by module: 205 × the missing-`resolution` TypeError. Plan 08's roster: `test_cp_00_output` 18+1, `test_cp_00_recipe_steps` 8, `test_cp_01/02/03_output` 12/17/13 (grown by the shadow-`intent` construction refusal plan 07 predicted), `test_cp_04_traversal` 1 (same cause), `test_s1_00_output` 8. OUTSIDE every roster — the ARCHIVE class, all one exception: `test_quickstart_output` 9, `test_agent_basics_output` 17, `test_skilling_output` 18, `test_harness_portability_output` 13, `test_cross_process_output` 13, `test_workflow_hitl_output` 37, `test_decision_replay_output` 34, `test_artifact_store_output` 10, `test_e2e_demo_output` 19, `test_ext00_serve_output` 11, `test_ext00_hardening` 1, `test_gate_two_divergence` 2, plus `tests/perf_smoke::…[crossproc]` — ~193 ids exercising the 12 `archive/examples/` builder sites (00..08 `run.py`, `producer_child.py`, ext-00 `serve.py`); 0 of them red at the phase base (chunk C was 874/127/0 errors there).** The wave-3 record said "two ids"; it counted FAILED and not ERROR. **Dave's ruling still owed, options restated with the true size: (1) `archive/examples/` frozen like `examples/` — leave the 12 sites, quarantine ~193 ids across 13 test modules (one outside `tests/examples/`); (2) `archive/` is SDK scaffolding — re-derive the 12 sites (a 12-line mechanical edit), the ~193 ids go green with no test touched. The size now favors (2); it is still his call because it names which side of the freeze `archive/` sits on.** Wave 5 (plan 08) proceeds on its own roster and must NOT touch the archive modules. Next free id `D-IMPL-265`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.7 — WAVE 3 MERGED, TRANSIENT CLOSED; ONE FENCE QUESTION FOR DAVE (2026-09-05 23:05 MST, `phase-24.7`; 6/11 plans).** 06 (worktree, base `304e3caa`): 26 builder sites/17 files + 12 recorder sites/8 files re-derived to the explicit state; all 41 + 15 RESEARCH § Priority 1 ids present by AST walk; every recorder site states `no-resolution-step`; plus one builder site on NO roster (`perf/suites/replay/conftest.py` — RESEARCH never walked `perf/`) re-derived and reported outside the counts (plan 10 carries the roster gap); one `.replace()` in `test_harness_trace.py`'s byte-identity test as its own comment prescribes. Merge `f67bece3`. Full gate on the merged tree: lint 0, mypy clean, product-gates 58/58; A 2786/2 (the carried `[CLAUDE.md]`; and a citation-coverage red that was MY wave-2 STATE edit citing a child server by line — corrected in this edit to the `::symbol` form), B 907/90 skipped, C 616 passed/127 skipped/2 xfailed/**64 failed + 192 errors**, D 1843/**1 failed**; gate-tools 460 · 339/2 · 29. In-phase fix committed: plan 04's `ResolutionNotApplicable` docstring quoted a §7.10 sentence and tripped the publish-scan shingle gate — paraphrased, 53 green. Chunk C reds: 242 × the missing-`resolution` TypeError in `test_cp_00/01/02/03_output.py` + `test_s1_00_output.py` — plan 08's roster, quarantine batch B (wave 5), evidence not repair — plus ONE outside every roster: `tests/examples/test_ext00_hardening.py::test_the_d15_fallback_works_with_every_client_leg_deselected`, which runs `archive/examples/external/00-hello-context/serve.py`. Chunk D's one red is the same class: `tests/perf_smoke/test_smoke.py::test_suite_runs_untimed[crossproc]` spawns `archive/examples/04-cross-process/producer_child.py`. An AST walk of `archive/` finds 12 builder sites without `resolution=` (00..08 `run.py`, the producer child, ext-00 `serve.py`); only those two are exercised by tests. **STOP-AND-RETURN (plan 06): no ruling names `archive/` on either side of the `D-IMPL-263` fence.** Options put to Dave: (1) treat `archive/examples/` as frozen like `examples/` — leave the sources, strict-xfail the two test ids naming `D-IMPL-264` D-10, assertions unchanged (recommended; it is what the freeze means); (2) treat `archive/` as SDK scaffolding — re-derive the 12 sites. Under (1) plan 08's roster grows by `test_ext00_hardening.py` and one id in `tests/perf_smoke/test_smoke.py` (outside `tests/examples/`). **Wave 4 (07 ‖ 09) does not depend on the answer and proceeds; plan 08 (wave 5) waits for it.** Next free id `D-IMPL-265`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.7 — WAVE 2 MERGED (2026-09-05 22:20 MST, `phase-24.7`; 5/11 plans). THE 38-SITE TYPEERROR TRANSIENT IS LIVE — no full suite until wave 3 (plan 06) merges.** 04 (worktree, base `b1637ec0`): `ResolutionNotApplicable` + reason vocabulary; `build_replay_record(..., resolution=)` required, `None` and pre-serialized refused by name; three seam signatures lose `= None`; both boundary denials `refused-before-resolution`; sentinel stays the field default (D-12 controls diff-empty); mypy walked 1 → 2 → 0 errors exactly at the predicted sites; AST count 26 builder sites/17 files + 12 recorder sites/8 files = 38, left untouched. 05 (main tree): legs BEFORE on the wave-2 base — postgres 2 failed, fluree 18 failed + 30 errors = 48 cp-04 ids, ALL `'ResolutionOutcome' object has no attribute 'parameter'` at `assembler.py:329` (41 direct, 7 through the MCP door); 48 strict xfails naming `D-IMPL-264` am.1; AFTER postgres 271/68 skipped/2 xfailed, fluree 260/48 xfailed, before-ids = xfailed-ids by `comm` (§ Q-A). Merge `35a23c53`, no conflict, regeneration idempotent. Partial gate on the merged tree: lint 0, mypy clean, product-gates 58/58, surface gates + smoke 47, retirement report current (59). Directed run over invariants/replay/authz/products/hitl/workflow/http_api/mcp/conformance/integration/crossproc: 2813 passed, 107 failed, 397 errors — classified by exception: 502 `missing 1 required keyword-only argument: 'resolution'` (501 builder, 1 recorder), 45 child servers that never announced readiness, every one dying at `tests/crossproc/servers/mcp_egress_child.py::build_servable_product` (a plan-06 site the A2A producer children import), and the 1 carried `[CLAUDE.md]` red. Nothing outside the expected class. No stop-and-return. **Next: Wave 3 = plan 06 alone (re-derive the 38 sites to the explicit state); then the full A/B/C/D chunks.** Next free id `D-IMPL-265`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.7 — WAVE 1 MERGED (2026-09-05 22:05 MST, `phase-24.7`; 3/11 plans).** Plans 01 ‖ 02 ran in worktrees forked from `main` and fast-forwarded to the base `9a2e4bcf`; plan 03 ran on the main tree (legs need `.venv` + docker). 01: `ArgumentDomain.members` (one shape, exact typed membership, four sabotage controls), ninth reason `not-in-domain` with the set in `detail` only, both hash rosters, schema/surface regenerated. 02: `ResolutionOutcome` at all six exits + both `resolve` methods (D-08); refusal branch records the partial resolution and bindings (D-07, red-first, sabotage-red). 03: `24.7-LEGS.md` § Baseline — postgres 273/68 skipped, fluree 308, red roster none, 428 node ids over 18 modules (RESEARCH rosters identical by id). Merge at `5b32caaa` (the only conflict: the two generated docs, regenerated on the merged tree, idempotent). Post-merge on the merged tree: lint 0, mypy clean; A 2783/1 (the carried `[CLAUDE.md]` red), B 900/90 skipped, C 872/127 skipped/**2 failed**, D 1842; gate-tools 460 · 339/2 (F-E carried; the retirement report was stale after plan 03's planning commits — regenerated, 59 green) · 29. **The 2 chunk-C reds are `test_cp_04_seams.py` × 2: the frozen assembler reads `.parameter` off `ResolutionOutcome` (`assembler.py:329`) — plan 02's predicted consequence, EVIDENCE for plan 05, not repaired.** No stop-and-return from any executor. **Next: Wave 2 (04 ‖ 05) forked from the post-wave-1 tip; remember the 38 TypeErrors between the wave-2 and wave-3 merges are expected — no full suite there.** Next free id `D-IMPL-265`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.7 — GO TO EXECUTION GIVEN (Dave, 2026-09-05 20:16 MST, `24.7-RULINGS.md` §9); NOT STARTED — Dave cleared context first.** Plans at `5e933119`, GO at `24ede250`, `phase-24.7` pushed, tree clean. **Resume on `phase-24.7` with `/gsd-execute-phase 24.7`, Wave 1 (plans 01 ‖ 02 ‖ 03).** The execution rule, his words: *"SDK issue discovered → classify first. Frozen-example red → evidence, not repair work. New architectural ambiguity → stop and return to me. Mechanical implementation detail under an existing ruling → proceed."* Executors obey mechanically: *"Between Waves 2 and 3, the 38 type errors are expected evidence of the explicit builder/recorder change. They are not a regression to fix locally. Do not restore a default, infer non-applicability, or modify a frozen example/test assertion to remove them. Plan 6 owns their re-derivation."* Plan 11 STAGES the panel packet and does NOT run it — Dave evaluates the build first. Worktree discipline: fork each wave from the wave's expected base (fast-forward first), no `.venv` in a worktree, regenerate generated docs once per wave merge, run tests/invariants after every merge, hand-edit STATE/ROADMAP (no `state.*`/`roadmap.*` writer). Next free id `D-IMPL-265`. PRIOR HEAD FOLLOWS.
  **PHASE 24.7 PLANNED — 11 plans / 7 waves, checker PASSED (2026-09-05 19:45 MST, `phase-24.7`); NOT EXECUTED.** Planner ran from the 28 locked criteria; the checker found 3 blockers + 11 advisories; Dave ruled the three that were his as `D-IMPL-264` am.3: criterion 24 AMENDED to bind to the rosters (15 recorder sites in 9 files, not 14) and RE-PINNED — digest `594aaaf8…` supersedes `112e77b7…` (which reproduces on `5a493cc5`); the intent refusal PINS the deciding class declaration and D-11 replay inference narrows to request-contract + constraint pins; the declared intent set rides in `detail` under disclosure; plan 07 depends on plan 06 (waves shift). Revision applied by the same planner; re-check VERIFICATION PASSED (two wording notes fixed by hand in plan 09). gsd decision-coverage gate SKIPPED (0 trackable — it does not parse this CONTEXT's decision format); orchestrator's own script measured all 28 criteria and every D-00..D-13/P-1/P-2/`24.7-C-01`/G-26/G-33 in `must_haves`. Waves: 1 = 01‖02‖03 (contract core; D-08 + D-07 red-first; legs baseline); 2 = 04‖05 (explicit builder+recorder+boundary; cp-04 D-08 quarantine); 3 = 06 (SDK test re-derivation); 4 = 07‖09 (render + intent invariant; D-11 replay check); 5 = 08 (quarantine B); 6 = 10 (rosters/exports/chunks); 7 = 11 (close evidence, panel STAGED). Known transient between the wave-2 and wave-3 merges (26 + 12 sites TypeError) — never a full suite there, never a restored default. **Next: present the plans to Dave; `/gsd-execute-phase 24.7` ONLY on his go; build evaluation BEFORE panel/review/D-GATE.** Next free id `D-IMPL-265`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.7 — RESEARCHED, AMENDED, 28 CRITERIA LOCKED (2026-09-05 18:29 MST, `phase-24.7`).** Research (`b0150cf9`) came back BLOCKED on four findings, each verified against the tree and ruled by Dave as `D-IMPL-264` am.1: F-1 the intent invariant (absence of a discovery declaration = unjudged; a declared set is authoritative; declared empty = serves none); F-2 four frozen rungs (cp-01..cp-04 declare `intent` as an argument) quarantined, never repaired; F-3 explicitness crosses the recorder seam (both `record()` signatures lose `=None`); F-5 D-02 refined to representation-without-delivery — canonical SDK render, NO new MCP/HTTP surface, carry row `24.7-C-01`. VALIDATION.md and PATTERNS.md written; criterion 16 corrected on the pattern map (the assembler mints no record). The one pre-existing citation red was this session's own STATE cite — converted at `fd3951a5`. 28 criteria LOCKED by Dave (am.2), digest `112e77b754318672…` pinned in `24.7-CRITERIA-LOCK.md` with its controls; three planning instructions carried verbatim (repair the SDK, not the example suite; criterion 24 never overrides 21/22/26; stop and return on any new architectural decision). **Next: the planner runs from the locked criteria → plan-checker → plans presented; NO execution until plans are reviewed.** Next free id `D-IMPL-265`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.7 DESIGNED — `D-IMPL-264` (2026-09-05 16:18 MST, `main`).** `/gsd-discuss-phase 24.7` ran as the design sitting: four areas, thirteen questions in one batch (Dave: no wizard), every recommendation taken (Q1..Q13 all a), plus his two principles — P-1 *the request contract is the authority for legal values; schemas and discovery advertise, never define*; P-2 *`not applicable` is an explicit governed fact with a reason; missing resolution information is an internal integrity failure*. G-26: `ArgumentDomain` gains an enumerated shape (one shape only, exact match, any primitive type, default a member), the render DERIVES `enum`, top-level `intent` judged against `ProductDiscovery.intents` and an arguments-level `intent` refused at construction; new reason `not-in-domain`; legal set always advertised. G-33: participated = the resolution step ran (the SDK's own resolver at `src/ccf/products/resolver.py::GovernedResolver.resolve` records mid-resolution refusals with NO resolution — the live case); refusal PAIRED with partial resolution; builder REQUIRES an explicit resolution or typed not-applicable marker; enforced at construction AND verified at replay against PINNED state; old records untouched; cp-00..cp-03 reds ACCEPTED as quarantined evidence, never edited. Files: `24.7-RULINGS.md` (verbatim), `24.7-CONTEXT.md`, `24.7-DISCUSSION-LOG.md`; ROADMAP 24.7 status → DISCUSSED AND DESIGNED, NO CRITERIA. **Next: `/gsd-plan-phase 24.7` — research measures the tree, criteria are authored and locked BEFORE Wave 1 (`D-GATE-19`), then plans; nothing has run yet. Stopped here per Dave.** Next free id `D-IMPL-265`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASES 24.7 AND 24.8 BANKED — `D-IMPL-263` (2026-09-05 15:51 MST, `main`).** Dave chose Option 1 at 15:21: 24.7 = Request/Replay Hardening (G-26 enumerated request-contract domains + G-33 fail-closed replay completeness); 24.8 = Traversal Semantics (G-28); cp-05 follows both, number unassigned. cp-04 FROZEN through both (his freeze paragraph verbatim on both ROADMAP entries). Fence: `src/`+`runtime/` OPEN, `examples/` CLOSED, `tests/examples/` ONLY to quarantine/xfail an existing test the SDK work turns red — never assertion, expected value, fixture, data or semantics; a quarantined test keeps its original assertion, names the causing gap/decision, and is un-quarantined and rerun unchanged when the gap closes. **DIRECTION BANKED IS NOT PHASE DESIGNED:** the G-33 invariant is ruled; its representation, API shape, validation point, compatibility behavior and what "participated" means are NOT — they are the 24.7 design sitting's subject. Two ROADMAP `### Phase` sections + checklist + progress rows written by hand with NO criteria (`D-GATE-19`). The two stale `.continue-here.md` files (24.4, 24.5) STAY — both cited by decisions/close records; Dave's condition. **Next: `/gsd-discuss-phase 24.7` opened as the DESIGN SITTING with Dave and STOPPED there — no researcher, no criteria, no planner until he has ruled the semantics.** Next free id `D-IMPL-264`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **cp-04 SDK GAP LEDGER BUILT AND APPROVED — `D-IMPL-262` (2026-09-05 14:50 MST, `main`, pushed).** Built after the merge from
  evidence only (36 rows: 3 OPEN, 11 FIXED-24.5, 2 FIXED-24.5→24.6, 11 FIXED-24.6, 4 ESTATE, 5 NOT-A-GAP); NO code, example, test,
  config, transcript or publication changed. Dave read it end to end: G-14 requirement corrected in his words (default 3, 6 was the
  measured ceiling-in-error, max 100); G-26 RULED fix (enumerated `ArgumentDomain`, not Policy `allowed_set`, not a validation
  language); G-28 RULED SDK defect for the next TRAVERSAL-owning phase, not bundled; G-33 RULED SDK gap under his conditional replay
  invariant. Scope by SDK ownership: request/replay hardening = G-26 + G-33; traversal = G-28; no cp-04 edits or reruns during
  either; ESTATE rows left alone. **Phase numbers NOT assigned — the open question for Dave** (and where cp-05 sits). No ROADMAP
  entry until he numbers them. Next free id `D-IMPL-263`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.6 CLOSED — `D-GATE-24.6` APPROVED AS-IS; `D-IMPL-261` RESETS THE EXAMPLE LIFECYCLE (2026-09-05 14:20 MST, `phase-24.6`).**
  Dave, at the resume sitting: the examples are probes, not repair targets; the 48-hour loop was cp-04 republished three times with a
  panel/review/correction cycle after each. Ruled: `D-IMPL-261` (his rule verbatim, five paragraphs; cp-00..cp-04 FROZEN as diagnostic
  specimens; no republish or re-pin inside an SDK phase; the cp-04 SDK gap ledger built AFTER the merge from existing evidence only with
  OPEN / FIXED-24.6 / ESTATE-LIMITATION / NOT-A-GAP, NO fixes while building it, brought to Dave BEFORE the next SDK phase is scoped) and
  `D-GATE-24.6` (*"Approve 24.6 for close and merge as-is. The final cp-04 publication is accepted as the last publication performed under
  the pre-D-IMPL-261 process"*; the ledger is NOT a merge condition; known findings carried, not cleaned up). Short invariant added to
  CLAUDE.md §9. ROADMAP 24.6 marked Complete by hand (checklist, STATUS line, progress row). Merge `--no-ff` to `main` and push of BOTH
  `main` (5 unpushed planning commits) and `phase-24.6` (102 behind origin) follow this commit. **Next:** the cp-04 SDK gap ledger →
  Dave reads it → next SDK phase scoped. Next free id `D-IMPL-262`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.6 — CORRECTION PASS UNDER `D-IMPL-260` DONE (2026-09-05 12:20 MST, `phase-24.6`, NOT pushed, NOT merged).**
  Dave HELD the gate at 09:56 MST ("I need you to do better than this") and ruled the ten close questions as implementation
  corrections under existing rulings — recorded verbatim as `D-IMPL-260`. Every item is fixed, measured and committed:
  `635e8d3a` (P-I override attempts on refused requests reach the record; P-J `resource` normalized below `full`; P-D the
  deciding role on dimension 4; P-E verified and carried; P-F `bound.source`/`policy_id`/`reason` suppressed below `full`;
  P-G `ParameterBound.reason`), `b08c4b4d` (P-B experience resource through the door translation; P-C `govern_absence`),
  `f4277b49` (P-A: the door releases only a `ServedProduct` or a recorded, disclosed envelope — `UngovernedResolverResult`),
  `9d514646` (P-H cp-04's fulfilled record carries `request_resolution`; `CFT-G19` minted with `criterion_phase`, watched RED),
  `b71bbbd8` + `118a1435` (cp-04 transcript re-pinned — one hunk, P-H — page rebuilt and REPLACED IN PLACE at `f20ed519…`,
  live copy proven before and after; cp-01 untouched, empty diff). Final tree whole: A 2726 / B 900+90 / C 874+127 / D 1842
  = 6559 collected; legs fluree 308, postgres 273+68, neo4j 22, mongo 24; lint 0; mypy clean; product-gates 58/58; digest
  `c0fdc4f4…` UNMOVED (no criterion amended). ONE pre-phase gate-tools red (F-E) carried as recorded. Records:
  `24.6-CORRECTION-PASS.md` (a section per item), CLOSE-PREP Addendum D + `D-GATE-24.6 — DRAFT, updated after the
  correction pass`, PUBLICATION rebuild section. **Next:** Dave's APPROVE → `D-GATE-24.6` in DECISIONS.md → merge `--no-ff`
  to `main` → push → regenerate RETIREMENT-COUPLINGS last. Next free id `D-IMPL-261`. Hand-edited; no `state.*`/`roadmap.*`
  writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.6 — §3.1 CLOSE SEQUENCE COMPLETE UP TO DAVE'S GATE (2026-09-05 09:25 MST, `phase-24.6` at `026f7d36`, NOT pushed, NOT merged).**
  Build evaluation DONE (Dave: cp-01 APPROVE + F-1 carried; cp-04 APPROVE; phase APPROVE TO CLOSE subject to evidence and gates). Cross-AI
  panel RUN on a 14-bundle packet rebuilt from the fixed tree (`24.6-CLOSE-REVIEWS.md`: 42/42 runs read-proofed; 8 fixed, 9 rejected with the
  rejecting line, 6 carried). Single-agent review RUN (`24.6-REVIEW.md`: 3 carried, 1 rejected, 6 docstrings corrected; schemas regenerated).
  Close-time fix commits `ea695396` (F-C ×5), `a90a8df9` (panel ×7 + docstring), `066f6c06` (egress address-surface identity), `61a4b97a`
  (docstrings), `026f7d36` (schemas). Final tree whole: A 2691 / B 900+90 / C 873+127 / D 1840 (4 schema-export reds → fixed, 118 re-run)
  = 6521 collected; leg-fluree 308, leg-postgres 273+68, lint 0, mypy clean, digest `c0fdc4f4…` unmoved. ONE pre-phase red (gate-tools, F-E).
  **TEN questions for Dave, none disposed** (CLOSE-PREP `D-GATE-24.6 — DRAFT, updated`): P-I criterion-10 override attempts on refused requests;
  P-J criterion-22 `resource` key presence (the phase's own instrument excluded it); P-A release without mint/disclosure for non-reference
  resolvers; P-B/P-C/P-D/P-E/P-G/P-H/P-F; plus F-D/E/F/G/J carried. **Next:** Dave rules → `D-GATE-24.6` in DECISIONS.md → merge `--no-ff` to
  `main` → push → regenerate RETIREMENT-COUPLINGS last. Next free id `D-IMPL-260`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.6 EXECUTED AND BUILD-EVALUATED — F-C fixed in-phase at `ea695396`; panel + review next (2026-09-05 07:05 MST).**
  Plan 15's close evidence (`d466d4f7`) found FIVE in-phase reds on `make leg-fluree` (cp-04's fluree-marked modules; base green): two gates
  written against the pre-`24.6-08` shell (`CFT-G18` (b) read both candidate IRIs off the shell; `CFT-G06` read the declared prose and a
  `400` off it), FastMCP 1.28.1's `Error executing tool <name>: ` prefix on the opaque id, an order-dependent assembler identity (a seams
  control evicted 5 of 8 bare modules and left `compose` stale), and a `build_resolver` call missing `refusal_recorder=`. All five fixed as
  tests aligned to ruled mechanism, no assertion weakened, two new controls; `leg-fluree` 308 passed rc=0, chunk C 873/127, collected 6517,
  lint 0. Recorded as `24.6-CLOSE-PREP.md` Addendum A with a new finding F-J (the published cp-04 page inlines two of the changed test
  modules — republish or accept, Dave's call). **Dave's build evaluation (05:38–05:40 MST) recorded verbatim in A.4:** cp-01 APPROVE with
  F-1 carried as a measured capability difference (AssemblyOutcome carries the identity; cp-01's replay record does not; cp-04's does);
  cp-04 APPROVE; **Phase 24.6 APPROVE TO CLOSE subject to plan 15's evidence and the normal close gates**; no example changes from the
  review. Legs ran on LOCAL containers (`ccf-fluree-15-3`, `ccf-neo4j-test`, `ccf-mongo-test`, testcontainers postgres) — plan 13 F-2 resolved.
  **Next:** rebuild the panel packet from `ea695396`, run codex + cursor + gemini over stdin (read-proof, 0-byte re-run), the single-agent
  review, verify every finding, fix blocking in-phase, then present triage → `D-GATE-24.6` → merge `--no-ff` to `main`. Not pushed.
  Next free id `D-IMPL-260`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.6 EXECUTED — close prep complete; build evaluation, panel, review and D-GATE-24.6 owed (2026-09-05 13:20Z, wave 12 / plan 15 on `phase-24.6`).**
  Every instrument the 36 criteria name was run on the shipped tree and recorded in `24.6-CLOSE-PREP.md` with its command, verbatim output and control.
  Lock: `BLK | wc -l` 38, criteria 36, detector 0 (planted-wrap control 1), sha `c0fdc4f4…` (Amendment 3, `D-IMPL-257`) with the appended-char control
  `fbccc2e9…` and all four historical controls reproducing on their own commits (`014dcd64…`@`a1ce6cdb`, `c3224bb4…`@`64d9e905`, `eba17d45…`@`4da5a80d`);
  gsd parser 36 (a READ, no writer); ledger 21/21; plan coverage 21/21 rows + 36/36 criteria, both directions. Suite 6515 collected; four FOREGROUND chunks
  2688 / 899+90 / 871+127 / 1840 sum EXACTLY to 6515; `make lint` 0, `make typecheck` clean (216), `make product-gates` 57/57, `make docs-strict` 0
  (it IS in `ci` — Makefile:195 — the "not in ci" premise was wrong and is recorded as a rejected instrument), citation coverage 5 passed.
  Legs on LOCAL containers: postgres 271/0, neo4j 22/0, mongo 24/0. **`make leg-fluree` 5 FAILED / 301 passed** — all five IN-PHASE, all in cp-04 modules
  no wave collected (fluree-gated), measured GREEN (68 passed) at base `1022ad59` in a throwaway worktree against the same container:
  `test_cp_04_anchor.py::test_cft_g18_b_the_tool_carries_the_ambiguity_as_a_governed_refusal` and
  `test_cp_04_payload.py::test_cft_g06_as_of_is_refused_not_supported_at_tier` (criterion 21's minimal disclosure meeting cp-04's declared teaching
  gates), `test_cp_04_two_callers.py::test_both_callers_resolve_to_the_same_assembler_module`, `::test_a_serve_path_refusal_…` (FastMCP now prefixes the
  opaque id) and `::test_the_resolver_assembles_under_the_perspective_it_was_handed` (`build_resolver()` missing the required `refusal_recorder=`).
  NOTHING was fixed there and no assertion was weakened — three of the five turn on what a published, Dave-evaluated product should TEACH, which is his.
  One red WAS fixed in-plan (Rule 1, `1f70aa85`): `tests/contracts/test_hash_transparency.py::test_the_marked_fields_in_the_tree_are_exactly_the_ticked_table`
  — `D-IMPL-259` ticked one of two hash-transparency rosters; departure control fired, restored `cmp`-identical. Fence by SET equality: 1 arrival
  (`artifacts/source-vocabulary.yaml`, plan 13's `ad41352b`, in its SUMMARY roster and not its PLAN roster) and 3 departures (`question.yaml`,
  `server/egress-door.yaml`, `test_cp_04_gates_declaration.py`) — all plan 13's, all inside the substantive fence, LISTED never subtracted; planted-file
  control fires. Sabotage roster 20 → 49 over 71 modules, 3 paired renames, no unpaired departure; the six lock-named and five delivery-boundary sabotages
  all PASS (19 passed). Criterion 36: 22 entitling door sites, 20 bind a recorder, 2 are the deliberate check-removal sabotages on scratch copies; archive
  sites listed (hello-context re-measured at `serve.py:793`, not the planning note's `:788`); 0 recorder/writer calls in either transport tree; exactly one
  `except ProductEntitlementRefused`, in `authz/delivery_boundary.py:313`. Panel packet STAGED ONLY — 39 bundles, 4,680,010 B, stdin never argv, `cat -n`
  numbered, read-proof planted mid-payload in `bundle-14`, known findings briefed with two adjacency questions; **no reviewer invoked**, so
  `24.6-CLOSE-REVIEWS.md` and `24.6-REVIEW.md` do not exist. Criterion 35 reads `packet ready; panel and review owed after the build evaluation`.
  Nine findings for Dave (F-A..F-I), each a question with its measurement, none a disposition (`D-IMPL-227`). `24.6-VALIDATION.md` Status column filled
  (38 rows). `D-GATE-24.6` DRAFT written into `24.6-CLOSE-PREP.md` — measured facts and questions only, with every not-done step named as not done.
  Next free id `D-IMPL-260` (max DEFINED 259; the mention-counting reader returns the `D-IMPL-9999` decoy and is recorded as rejected).
  **NEXT: present the build to Dave. Do NOT run the panel, draft a gate, mark anything complete, merge or push before he has evaluated it.**
  Hand-edited; no state.*/roadmap.* writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.6 EXECUTING — waves 1–11 of 12 done; plan 14 COMPLETE, both pages PUBLISHED IN PLACE (2026-09-05 05:20 MST, resumed session on `phase-24.6`).**
  Wave 11 (plan 14, `autonomous: false`): cp-04's transcript captured on the shared estate (Dave: Fluree up on `192.168.4.76:8090`, 4.1.4;
  `fibo-v2` at `t=5296`), diffed hunk by hunk (6 hunks, each attributed: `@1.0.2`, lane `1.1.0`, depth/cost lines, findings roster, policy
  version off `booted.pins`) and re-pinned at `5f0c4d5a`; README/summary/CP-SPEC-004 §B.4/§B.4.1 present tense; cp-01 diff EMPTY, page byte-identical;
  `24.6-PUBLICATION.md` at `fd81cb45`. **At the checkpoint Dave ruled `D-IMPL-259`:** publish approved CONDITIONAL on the F-3 fix — `MAX_DEPTH=0`
  was served (plan 13 deleted `argument_bounds`, the floor of 1 went with the 6) → a floor of 1 declared ON THE REQUEST CONTRACT through the SDK
  (`ArgumentDomain`, `ProductRequestContract.argument_domains`, `below-minimum`/`above-maximum`, domain step LAST in `refuse_request`), NOT a
  Policy Constraint and NOT the old example-local check; shipped at `958a12e0` (sabotages: declaration deleted → 1 red, domain step removed → 4 red;
  112 request-contract tests; 39 live traversal tests, `0` refused as data / `1` served; re-capture byte-identical; one throwaway `cp04-*` branch on `ccf`).
  Premise corrections flagged in `D-IMPL-259`, not absorbed: the declared default is **3** (Dave wrote "remains 6"); above 100 stays `constraint-refusal`.
  F-1 (replay-carriage sentence on cp-01/02/03): Dave — leave them alone, carry as measured/unresolved. Published by the orchestrator on Dave's written
  approval (*"Publish both pages in place at the two re-resolved IDs"*): cp-04 `f20ed519-…` (sha `708d1134…`, page names `958a12e0`), cp-01 `6edeeba9-…`
  (sha `1a24c649…`); the publish tool refused each until the live copy was read in full; post-publish gallery: only the two rungs dated today, decoys
  `c0f12122-…`/`ee54f990-…` untouched. Record at `4f1e88b1`; `24.6-14-SUMMARY.md`; plan 14 ticked BY HAND; digest `c0fdc4f4…` reproduced (36/0/control
  fires); `RETIREMENT-COUPLINGS.md` regenerated last. **Next:** wave 12 (plan 15, close evidence) incl. `make leg-fluree`/`leg-postgres` in full
  against the shared estate (plan 13 F-2), the PRE-PHASE `gate-tools` red (plan 12 F-1) and the 258-FIXES F-1/F-2 still for Dave; then Dave's build
  evaluation BEFORE panel/review. Next free id `D-IMPL-260`. Hand-edited; no `state.*`/`roadmap.*` writer ran; not pushed. PRIOR HEAD FOLLOWS.
  **PHASE 24.6 EXECUTING — waves 1–10 of 12 done plus the `D-IMPL-258` fix MERGED (2026-09-05 04:10 MST, resumed session on `phase-24.6`).**
  The 258 fix (limbs (2) and (5)) was found complete but UNCOMMITTED in its worktree at session start; verified there (1951 passed,
  the one red = the clean-tree guard, uncommitted files), committed `41bb1907`, merged `--no-ff` as `ea1af296` onto plan 13's tip, generated
  docs regenerated byte-identical. Merged-tree gates: `make lint` 0; `make typecheck` clean (216); chunks A/B/C/D = 2664 + 899 + 868 + 1839
  passed, 0 failed; `make gate-tools` 460 then 339 passed + 2 failed (the PRE-PHASE roster red, plan 12 F-1; and the stale generated
  retirement report — regenerated in this commit). The owed `24.6-D-IMPL-258-FIXES.md` written (F-1: a class pinning NO request contract
  but declaring a default stays servable — widen or leave, for Dave; F-2: the `full` reading, for confirmation).
  **STOP FOR DAVE before wave 11 (plan 14, `autonomous: false`):** (i) plan 13 F-2 — the local Fluree container is down; may
  `make example-cp-04` / `leg-fluree` / `leg-postgres` run against the shared estate (14 prior `cp04-*` branches on the `ccf` ledger)?
  plan 14's transcript diff needs that run; (ii) plan 13 F-1 — no gate id minted for the depth-and-cost obligation (33 collides with
  24.4's `CFT-G13`); (iii) 258-FIXES F-1/F-2 above; (iv) the pre-phase `gate-tools` red. Then `/gsd-execute-phase 24.6` resumes at
  wave 11 (plan 14: build, diff, stage, re-resolve ids, publish on Dave's word), wave 12 (plan 15 close evidence), then Dave's build
  evaluation BEFORE panel/review. Next free id `D-IMPL-259`. Hand-edited; no `state.*`/`roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.6 EXECUTING — waves 1–10 of 12 done (plans 01–13, 16), 2026-09-05 03:30 MST, `/gsd-execute-phase 24.6` on `phase-24.6`.**
  **`D-IMPL-258` (Dave, 03:09, mid-phase, verbatim in `docs/DECISIONS.md`): five findings ruled** — absence is a governed fact, not a
  versionless artifact (08 F-1 shape kept); the `policy_bindings` leak is CLOSED in 24.6 and BLOCKS the gate (fix dispatched in a
  worktree from `0969ab03`: suppress in the disclosed shell below `full`, inverted controls at HTTP and MCP, real bindings kept in
  replay; `full` reading flagged for confirmation); the HTTP `403→404` shell is intentional and recorded as BREAKING in the 24.6-09
  fragment; archive bindings kept, narrowly; plan 04's undeclared-default check moves from resolution time to registration/boot.
  Plan 13 (cp-04, ~6h): depth 8 SERVED, 101 refused by name `constraint-refusal` authority `technical` from capability `fluree/fibo-v2`;
  cp-04 `raise AssemblyRefused` 12→3; seals `205ae065→fad6e55d`, `838afbb0→79733117` re-hashed LIVE; lane 1.1.0, assembler @1.0.2.
  13 F-1 for Dave: no gate id minted for the depth-and-cost obligation — cp-04's roster keys on a bare integer `criterion` and 33 is
  already 24.4's `CFT-G13`; needs a `criterion_phase` key or a number. 13 F-2: `make leg-fluree`/`leg-postgres` NOT run (local
  container down; shared estate carries 14 `cp04-*` branches on the `ccf` ledger from prior phases — acceptable to run there?).
  Next: merge the 258 fix onto plan 13's tip, gates, then wave 11 (plan 14, the publish checkpoint).
  Wave 9 (11‖12) merged clean, no conflicts. Merged-tree check: 1981 + 2020 + 800 passed, 16 xfailed (plan 12's declared cp-04 debt
  table, RED-when-fixed proven), 1 failed — `tools/docs_tests/test_requirement_ledger.py::test_the_uat_roster_matches_the_records_on_disk`,
  PRE-PHASE (the 24.5 record grew `human_verification:` at `ceab40fd` 2026-09-02; roster last edited Phase 23.1; both predate `1022ad59`),
  in `make gate-tools`, for Dave (plan 12 F-1). Plan 12 F-3: L-09's site list drifted (24 measured occurrences, 16 pairs, all cp-04) —
  plan 13 works from the measured set. Next: wave 10 (plan 13, cp-04 rebuild).
  Single-plan waves on the main tree (Opus, CLAUDE.md §3); waves 6 and 8 in worktrees cut from the wave base, merged `--no-ff` from
  the manifest only. Wave 8 (09‖10‖16) conflicted on ONE shared test (`tests/invariants/test_mcp_role_separation.py`: all three doors
  widened the same assert to accept `govern_entitlement(`; plan 16's copy kept — it adds the transitive check) and on the three
  generated files (regenerated by tool, never merged by hand). **Merged-tree check after wave 8: 1245 + 2100 + 460 passed, 0 failed;
  `make lint` rc 0; `make typecheck` clean (216 files).** ROADMAP ticks and this file hand-edited; no `state.*`/`roadmap.*` writer.
  **Open for Dave, accumulated (all recorded in the plan SUMMARIES, none red):** (a) 08 F-1 — the absent-entitlement-policy pin
  `ProvenanceSource(kind=artifact, version=None)` the plans specified for dim 2 is UNBUILDABLE under `D-IMPL-26`; shipped
  `policy=None` with the consulted key recorded three other ways; three options measured; doors 09/10/16 follow that shape. (b) 08
  F-2 → 09 F-1 → 10: `policy_bindings` distinguishes an unauthorized principal from a nonexistent subject at EVERY disclosure
  level (by value and by key presence) — a live D-27 channel, measured, excluded from the ruled comparison and pinned by its own
  test; cheapest close is one entry in `INDISTINGUISHABLE_BELOW_FULL`; across an A2A boundary it is a real channel. (c) 09: the
  HTTP entitlement `403 {error_code,message}` is now `404` with the envelope body — a breaking wire change. (d) 16 F-1 / 10: three
  `archive/examples/**` server sites bound `refusal_recorder=` so the archive's tests stay green (00-hello-context, 04-cross-process
  producer_child, plan 09's 05/06) — keep or revert pending the archive's disposition. (e) 04 F-1; 05 `restored_surfaces`; 07 F-1
  (`CLNT-02` partially superseded); 02's Conflict members; stale `c3224bb4` digest text in every plan's output block (tree right at
  `c0fdc4f4…`). `D-IMPL-257` (fence widened narrowly, Amendment 3) is applied and lint has been 0 since. Next: wave 9 (11‖12).
  Next free id `D-IMPL-258`. PRIOR HEAD FOLLOWS.
  **PHASE 24.6 IS PLANNED UNDER `D-IMPL-256` — 16 plans, 12 waves, criteria 36 (2026-09-04 evening, branch
  `phase-24.6`, pushed).** Dave ruled the three delivery-boundary questions BEFORE Wave 1 rather than at close:
  (1) MCP standing-resource denials are RECORDED under a resource-request identity at the determination instant;
  (2) an entitling door without a recorder is UNAVAILABLE for all governed requests — the three builders refuse at
  CONSTRUCTION (`UnrecordableDeliveryBoundaryError`), no warn-and-serve, no denial-branch posture, no residual
  channel; (3) the experience server's three entitlement paths get the same shell-and-replay treatment, narrowly
  (new plan 16, wave 8, 09‖10‖16 disjoint). He added the DELIVERY-BOUNDARY REPLAY INVARIANT as criterion 36 (every
  governed determination reaches the replay writer before the response is released; replay belongs to the
  determination, never to HTTP/MCP — a governed step `govern_entitlement` in `runtime/ccf_runtime/authz/` owns
  determination → mint → disclosure and the doors only encode). CRITERIA-LOCK Amendment 2: criteria 24/25/35
  amended, 36 added, digest re-pinned `014dcd64…` (`c3224bb4…`@`64d9e905` and `eba17d45…`@`4da5a80d` are the
  controls). Scoped checker on the fold-in: 1 blocker (plan 16's invariant test asserted a wave-8 tree only plans
  09/10 produce → moved to plan 11 Task 3, wave 9) + 1 warning (dim 2 must pin the entitlement policy that DECIDED
  a foreign-tenant request, not the deployment's) — both sent to the planner; the authz/ placement of the governed
  step ruled consistent. cp-04's door binds in plan 10 (not 13); plan 14 is the publish checkpoint; plan 15 the
  close evidence with the three questions retired as ruled. **Next: verify the last planner commit by hand, push,
  present; then Dave's line-by-line review if he wants it; then `/gsd-execute-phase 24.6`.** Next free id
  `D-IMPL-257`. Hand-edited; no `state.*` or `roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.6 IS PLANNED AND CHECKED (2026-09-04, /gsd-plan-phase 24.6, branch `phase-24.6` at `2baf78f5`).**
  Plan checker ran three iterations: 5 blockers + 5 warnings → 1 + 2 → 0 + 3; the last three warnings applied
  by the planner at `2baf78f5` and verified by hand (the 24.5.1 precedent), no fourth pass. The substantive
  fixes: a `RefusalRecorderProtocol` / `ReplayRefusalRecorder` seam on `GovernedResolver` so door-level
  entitlement denials mint a five-dimension record (Q13, am.2 (4) "replay reference behavior"); cp-04's own
  record carries assembler identity; hw1's door bound with one keyword (inside criterion 1's fence); a door
  that entitles WITHOUT a recorder warns at construction and fails closed on the denial branch (the 503
  precedent) — with one residual channel at that misconfigured door stated truthfully and measured. Closing
  gates: 15/15 plans structurally valid; same-wave overlap 0 (06‖07, 09‖10, 11‖12); no `state.*`/`roadmap.*`
  writer in any plan; digest `c3224bb4…` reproduces; all 35 criteria and 21 ledger rows carried by plan
  `requirements`. **Three questions for Dave land in plan 15's `## Findings for Dave` at EXECUTION, not now:**
  (a) mint the standing-resource denial at the entitlement audit's instant or leave it unrecorded; (b) should
  an entitling door with no recorder refuse every request instead; (c) the experience server entitles on three
  paths with no catch — same treatment, and in which phase. **Next: Dave reviews criteria + plans; then
  `/gsd-execute-phase 24.6` (plan 01 first; plan 14 is the publish checkpoint; panel and review after Dave's
  build evaluation).** Next free id `D-IMPL-256`. Hand-edited; no `state.*` or `roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.6 IS PLANNED (2026-09-04, /gsd-plan-phase 24.6, branch `phase-24.6`).** Dave ruled the five ledger
  questions (`D-IMPL-255`); 35 criteria LOCKED one per line before any plan (`4da5a80d`, digest `eba17d45…`), then
  Amendment 1 after the planner and before Wave 1 (digest re-pinned `c3224bb4…`): criteria 1/17's "18 cp-00..03
  sites" corrected to 14 (a false count I carried from research prose into the question Dave ruled on —
  `D-IMPL-255` correction 1; disposition unaffected) and five `::symbol` cites to symbols the phase deletes recast to
  prose so criterion 35's lint stays green (probe-proven). **15 plans in 12 waves** (`24.6-01..15-PLAN.md`,
  `95886103`), ruled order preserved; plan 14 is the one `autonomous: false` (the two publishes); plan 15 the close
  evidence + panel packet. Discretionary names fixed in the plans: `ccf.policy-constraint` / `policy_constraints`
  section, `ProductRequestContract.defaults`, `ServeObligations.default_debt_tolerance`, kinds `tolerance-exceeded` /
  `constraint-refusal` / `policy-resolution-conflict` / `subject-unavailable`, disclosure `minimal|reasoned|full`,
  `TraversalDepthCapability`. Plan checker next; then Dave reviews plans; then `/gsd-execute-phase 24.6`.
  Next free id `D-IMPL-256`. Hand-edited; no `state.*` or `roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.6 PLANNING IN PROGRESS — LEDGER BUILT, CRITERIA NOT LOCKED, FIVE ITEMS OPEN FOR DAVE (2026-09-04,
  /gsd-plan-phase 24.6, branch `phase-24.6`).** Dave reviewed CONTEXT/RULINGS remotely and ruled GO with four
  amendments (`D-IMPL-253` am.2: D-01 provenance generalized, D-12 emptiness alone does not determine Debt,
  D-15 classification rule is his and mechanical, D-27 consumer-observational equivalence) and three planning
  disciplines (am.3: exhaustive ledger before criteria; criteria test architectural properties — same request +
  same governed state + same asked_at → same determination/authority/disclosure/replayable response; order
  preserved). Research `b8dafc93` measured the tree at `1022ad59`: 21 carry rows, 28 raise sites (22 governed /
  1 failure / 5 AMBIGUOUS in cp-04 `deployment.py`), both doors traced, 71 SDK test functions on the
  re-derivation surface, 8 CONTEXT contradictions (appended note). Pattern map `8ae0b570`. **`24.6-LEDGER.md`:
  21 rows L-01..L-21, every B-01..B-14 / LC-01..05 / 245(a)(b) with a disposition in Dave's words or `OPEN`.**
  **OPEN FOR DAVE before criteria lock (§H):** (1) fence over the 18 cp-00..03 governed raise sites; (2) what
  evidence establishes a legitimately empty universe (SDK ships no number); (3) LC-04/LC-05 deferred by ruling;
  (4) republish cp-01 or generator only; (5) the five AMBIGUOUS sites as two questions. CLAUDE.md invariants vs
  `D-IMPL-254`: no contradiction measured. **Next: Dave rules §H → criteria locked one per line + digest →
  planner → checker.** Next free id `D-IMPL-255`. Hand-edited; no `state.*` or `roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.6 IS DISCUSSED (2026-09-04, /gsd-discuss-phase 24.6).** First question ruled before the menu: `D-IMPL-252` —
  24.6 is the SDK gap phase, NOT cp-05 (cp-05 is the rung after, number unassigned); ROADMAP entry written by hand at
  `501fd70a`. Then 28 rulings in prose with numbered options (menus declined; format switched at Dave's request),
  recorded verbatim at `D-IMPL-253` and mapped D-01..D-28 in `24.6-CONTEXT.md`: policy-constraint layer as its own
  Control Plane artifact with provenance on every parameter; defaults on the request contract; `debt_ceiling` renamed,
  `tolerance-exceeded` kind; computed-empty served (empty fabric IS computed — hw1 negative test re-derived); every
  refusal gets a full five-dimension replay record; `RefusalEnvelope` extended additively; identity refusal returned
  for governed determinations only; doors: no known refusal → 500, standing MCP resource body is the shell, no tool
  error for governed denial; cp-04: 6 deleted as bound, 100 is technical, findings carry depth/cost, lane → 1.1.0,
  republish in-phase; whole B-01..B-14 roster through the phase; no suppression-silent kind; whitepaper untouched.
  **Pattern for design: internal truth / governing authority / permitted disclosure are three representations.**
  NO criteria yet (`D-GATE-19` — at planning, one per line, before Wave 1). **Next: `/gsd-plan-phase 24.6`.**
  Next free id `D-IMPL-255` (`D-IMPL-254` = the Determination → Authority → Disclosure → Delivery invariant; `24.6-RULINGS.md` verbatim). Hand-edited; no `state.*` or `roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.5.1 IS CLOSED — `D-GATE-24.5.1` (Dave, 2026-09-04), disposition option 3.** The pause below ended
  with `D-IMPL-251` (the delivery boundary: refusal of fulfillment, not of response; C1=A C2=B C3=B C4=A C5=B;
  policy-constraint layer → 24.6) and `D-IMPL-240` am.2 / `D-IMPL-242` am.1. Closed on the implemented and
  reviewed state; `R-2`/`R-3`/`CR-01`/`CR-03` carried by ruling; the live cp-04 page is HISTORICAL EVIDENCE, not
  current guidance, until 24.6 rebuilds it. Carry roster B-01..B-14 in the gate entry. **First question for the
  next sitting: `D-IMPL-244` named 24.6 as cp-05; the boundary work is routed to "24.6" — whether cp-05 slides.**
  Merged `--no-ff` to `main` at `cd5a1bbb` and pushed. **Next free id `D-IMPL-252`.** Hand-edited; no `state.*`
  or `roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  **PHASE 24.5.1 WAS PAUSED BEFORE GATE (Dave, 2026-09-04).** Example reconciliation exposed an unresolved
  question concerning the boundary between fabric-enforced delivery constraints and consumer-determined
  fitness for purpose. No further back-correction proceeds until that boundary is resolved. A read-only
  investigation (no code, no plan, no criteria change, no publication) produces a research memo; nothing
  else in 24.5.1 is rewritten or reinterpreted until it is complete. Tree at `2dca6030`; the panel
  (`24.5.1-CLOSE-REVIEWS.md`) and single-agent review (`24.5.1-REVIEW.md`) are recorded and unacted-on
  beyond R-1; `D-GATE-24.5.1` is NOT approvable. Hand-edited; no `state.*` writer ran. PRIOR HEAD FOLLOWS.
  PHASE 24.5.1 WAVE 4 DONE (2026-09-03, /gsd-execute-phase 24.5.1): plan 07 `52c25c39..49227802` — `24.5.1-CLOSE-PREP.md`: criteria 1–22 and 24 hold on the shipped tree with every control fired; suite 5069 collected = 1404 + 956 + 978 + 1731 in four proven foreground chunks, 0 failed; legs postgres 262 / fluree 290 / neo4j 22 / mongo 24; lint 0, mypy clean, gates 57/57, ceiling green, docs-strict 0; the `D-GATE-24.5` hw1 red GONE by name; digest `2fd94c13…` on the tree and at `65bacb51`, three superseded digests reproduced at their commits. Criterion 23's `make gate-tools` was NOT green: the pre-existing UAT-roster red (question 9) and a NEW red plan 07 found in `tools/product_gates_tests` (`CP04_IDS` frozen at sixteen, red since plan 05 declared `CFT-G18`). **Dave ruled both pre-Wave-5 questions, `D-IMPL-248`:** cp-04's snapshot `ledger_t = 5112` IS the census read (`expected.yaml` closed; publish as built); `CP04_IDS` amended in-phase at `781f0304` — seventeen with a hole at 17, 28 passed, the one `tools/` edit of the phase. Open for the gate: question 9 (pre-existing docs red), question 11 (`make gate-tools` stops at its first failing suite), and plan 07's other findings as written. **Wave 5 next: plan 08 (pages rebuilt; cp-04's FIRST publish; a blocking human-action checkpoint at Task 2 — this session holds the artifact tool, so the orchestrator can publish on Dave's word).** **Next free id `D-IMPL-249`.** Hand-edited; no `state.*` or `roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  PHASE 24.5.1 WAVE 3 DONE (2026-09-03, /gsd-execute-phase 24.5.1): plans 03 and 06 executed sequentially on the main tree — 03 `a758d6e3..d7146e15` (cp-01/02/03 transcripts re-pinned with exactly one added `assembled by …@1.0.1` line each; every quoted block re-captured; six READMEs/summaries present tense, criterion-15 grep 0; CP-SPEC-001/002/003 findings CLOSED/SUPERSEDED by dated note, `CPR-G08` normative rows updated with the superseded text quoted; roster amended by dated note for three version-test docstrings that spelled the deleted class), 06 `5d9ce530..a7373943` (cp-04 recorded lies corrected in place, door unchanged, zero `assert` lines moved; README/summary present tense; CP-SPEC-004 §F.4 findings 1/2/5/6/9 closed by note; `CFT-G18` in the gate tables, `CFT-G17` stays withdrawn; transcript re-pinned 850 → 851 lines; `CFT-G16`/`G15` measured GREEN live on Fluree — seals `205ae065…`/`838afbb0…` unmoved; retirement report regenerated last, byte-identical). **Post-wave gate:** chunk A 1404, chunk C 858 (delta chunks; B/D read nothing Wave 3 touched), `make lint` 0, checker 57/57, `test_citation_coverage.py` green, criteria digest `2fd94c13…` unmoved, closed trees and every `ccf_config.yaml`/`expected.yaml` diff-EMPTY vs `ad56c816`. Known pre-existing red unchanged (`test_requirement_ledger.py` UAT roster, deferred item 1). **Findings plan 06 named for 07/08, none ruled:** the cp-04 page's snapshot says `ledger_t = 5112` (census read) beside a transcript captured at estate head 5296 — fixing needs an `expected.yaml` edit (criterion 3 forbids) or a ruling that the snapshot's `ledger_t` IS the census read → plan 08 carries it to Dave BEFORE cp-04's first publish; `run.py::…except AssemblyRefused` comment still says "no member for `not_supported_at_tier`" (off-roster, page embeds it); criterion 5's plain grep over cp-04 reaches the two preserved `ParameterNotSupported` controls through the rebuilt page (cannot be 0 there); the spec's `CFT-G17` token count is 10 (was 5) by the ordered "remains withdrawn" clauses and `test_cp_04_gates_declaration.py`'s "five times" docstring is stale; cp-04 refusals print on STDERR, cp-01/02/03 on STDOUT. **Wave 4 next: plan 07 (close instruments on the shipped tree); then Wave 5 plan 08 (pages, first cp-04 publish — carries a blocking human checkpoint).** Hand-edited; no `state.*` or `roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  PHASE 24.5.1 WAVE 2 DONE (2026-09-03, /gsd-execute-phase 24.5.1): plans 02, 04, 05 executed sequentially on the main tree (no worktree) — 02 `febd72ba..681e4ada` (cp-01/02/03: dead branch deleted, assembler 1.0.1 with the lane at 1.0.0, assembled-by line; cp-01 refuses a Policy-removed record under `Reading confirmed: WIDE`, SUMMARY line 66; cp-03 green-by-spelling inverted), 04 `8f98ec04..8d536a34` (hw1: declared `runner/signal-batch.yaml` + `runner/seed.py` through the single writer, store ignored, both transports succeed byte-identically, D_c 0.4271 forced_llm, empty-fabric refusal kept as a negative test), 05 `7a89d0f5..f69fe75f` (cp-04: `head_t_of` name+branch, `AnchorAmbiguityRefusal` returned as data, `CFT-G18` declared and executing, `CFT-G17` absent, 1.0.1; retirement report regenerated last, byte-identical on re-run). **Post-wave gate, foreground, four chunks:** A 1403 passed + 1 failed, B 866, C 858 (the hw1 red of `D-GATE-24.5` is GONE), D 1731; `make lint` 0; checker 57/57; closed trees diff-EMPTY vs `ad56c816`. The one red was the citation-coverage ceiling on the section's OWN line cites (6 already at `0e678fd1`, measured; 7 after Amendment 2) — Dave: **"Amendment 3 now"** (`D-IMPL-247`, `65bacb51`): seven cites → `path.py::Symbol`, ceiling module 5 passed, digest RE-PINNED `174c8ee7…` → `2fd94c13eca542f3be67305864743dde232e34e18ec39e225f994aec4b09bdc8` (wc 26, numbered 24, parse 24, detector 0), plan 07 re-pinned. **Known pre-existing red, NOT ruled:** `tools/docs_tests/test_requirement_ledger.py::test_the_uat_roster_matches_the_records_on_disk` (inputs `cae7297c`/`14c28ea6` predate the phase; `deferred-items.md` item 1, for plan 07). Executors flagged for plan 06/07: `expected.yaml::census.ledger_t_read_at` must be re-measured (name+branch → 1 row, not 4); `test_cp_04_seams.py::lei_identity_violations` still says `resolve_anchor` returns the FIRST binding inside a message. **Wave 3 next: plans 03 then 06, sequential, both `autonomous: false`.** **Next free id `D-IMPL-248`.** Hand-edited; no `state.*` or `roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  PHASE 24.5.1 WAVE 2 UNGATED (2026-09-03, /gsd-execute-phase 24.5.1): Dave ruled both open items at the sitting, `D-IMPL-246` (`b4d3b91f`): (1) plan 02 Task 2's reading of `D-IMPL-245` (4) is **CONFIRMED WIDE** — the not-visible principal is refused exactly as the no-grant principal; `CPR-G02`/`CPR-G04` move to the refusal shape; the §B.4 lapsed exclusion stays served; plan 02's SUMMARY carries `Reading confirmed: WIDE`. (2) the `make lint` red is **AMENDED NOW**: the five citation findings (ROADMAP `:3133,3158,3161,3169,3172`) corrected in Amendment 1's marked form as CRITERIA-LOCK **Amendment 2**; `make lint` 5 → 0; the criteria digest is RE-PINNED `8af1d381…` → `174c8ee7336be9d231d667cc87d55aea67295bbe725f06d2368ab28623008db4` (wc 26, numbered 24, parse 24, detector 0 unchanged); BASELINES §7 addendum; plan 07 re-pinned (both superseded digests labeled). Closed trees still diff-EMPTY vs `ad56c816`. **Wave 2 starts now: plans 02 → 04 → 05, sequential on the main tree, no worktree.** **Next free id `D-IMPL-247`.** Hand-edited; no `state.*` or `roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  PHASE 24.5.1 WAVE 1 DONE, WAVE 2 GATED (2026-09-03, /gsd-execute-phase 24.5.1): plan 01 executed on the main tree (no worktree; the wave order is sequential by plan-checker ruling) — `ad93eeec` (`24.5.1-BASELINES.md` 522 lines, `24.5.1-LEDGER-CANDIDATES.md` LC-01..LC-05, every number pasted output with its control firing and restored) and `70368f21` (SUMMARY, the one ROADMAP plan-01 tick, retirement report regenerated last and byte-identical). Spot-checked: closed trees (`src runtime examples tests Makefile`) diff-EMPTY vs `ad56c816`; criteria digest `8af1d381…` unchanged after the tick; parse 24, detector 0; no `state.*`/`roadmap.*` writer ran. Three measured values differ from the plan's expected text and are recorded as measured (`.gitignore` page line is 40 not 10; `build_replay_record` at `src/ccf/replay/record.py::build_replay_record` (the two line-range cites that stood here — lines 788 to 803 versus 772 to 786 of `record.py` — were recast to the `::Symbol` form `D-IMPL-114` rules on 2026-09-04 after plan 24.6-03 moved the lines; struck text still parses, so the old tokens are not kept); the CONTEXT sentence wraps `:179-180`). BASELINES §3 notes two of the 20 present-tense hits (`cp-01/summary_explanations.md:11` "still open", `:306` "cannot express") are ordinary English the instrument still counts — plan 03 must reword them. **POST-WAVE GATE: `make lint` is RED with 5 citation findings, ALL in the `### Phase 24.5.1:` ROADMAP section planning added by hand (lines 3133, 3158, 3161, 3169, 3172; four inside the digest-locked criteria block), NONE from Wave 1 (the section did not exist at `ad56c816`, where lint was 0; Wave 1's only ROADMAP change is the tick).** The lock record allows only "a dated marked amendment"; whether to amend now (Amendment 2, re-pin the digest in CRITERIA-LOCK / BASELINES §7 / plan 07) or carry the red to close is Dave's. **OPEN FOR DAVE BEFORE WAVE 2 (unchanged):** plan 02 Task 2's reading of `D-IMPL-245` (4) — `Reading confirmed: WIDE` or `NARROW` (NARROW is a STOP-and-replan). **Next free id `D-IMPL-246`.** Hand-edited; no `state.*` or `roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  PHASE 24.5.1 IS PLANNED (2026-09-03, /gsd-plan-phase 24.5.1): research measured the tree (`24.5.1-RESEARCH.md`, `dc3e7f82`) and found three contradictions with the sitting's text; Dave ruled each at planning — `D-IMPL-245` am.1 (assembler version is TRANSCRIPT evidence; replay carries none; PATCH `1.0.1` only where the assembler materially changes; `run.py` prints `assembled by <id>@<version>`; replay carriage is a 24.6 row), am.2 (hw1 seeded by an example-local pre-boot seed program under `runner/` over a committed declared signal-batch artifact through the single writer; store never committed; `src/`, `runtime/`, `binding.yaml`, the adapter untouched), am.3 (cp-04's identical dead branch deleted too; `produce.py` control class kept; one bump). **24 success criteria LOCKED at planning, one per line, BEFORE any plan and BEFORE Wave 1 (`D-GATE-19`)** — `3f51b184`; criterion 19 amended in the marked form to `CFT-G18` (`CFT-G17` is the id Dave withdrew 2026-08-31) at `db54c4f1`; digest `8af1d38143925ed1d12b65f71f423a4d3c323c7f0c0ac4f11ccb97905ca81603` (`24.5.1-CRITERIA-LOCK.md`; gsd parse 24/24 — the parser needs the header to end with a colon, and 24.4/24.5 parse as 0 for that reason); commit `f5dd3227` falsely claimed a re-pin and is corrected on record. **8 plans in 5 waves, 22 tasks** (`24.5.1-01..08-PLAN.md`, `25b3c43a` → revised `9ccb24fa`, `5d965654`, this commit); plan checker 3 iterations: 3 blockers + 7 warnings → 0 + 8 → 0 + 1 (the last fixed by hand: `Reading confirmed: NARROW` is a STOP). Waves: 1 = plan 01 (baselines, instruments, `24.5.1-LEDGER-CANDIDATES.md`); 2 = 02 cp-01/02/03 code+tests, 04 hw1, 05 cp-04 code+tests (sequential on one tree); 3 = 03 and 06 prose/specs/transcripts (sequential); 4 = 07 close instruments; 5 = 08 pages (cp-04 is a FIRST publish) + panel packet. Page URLs: cp-02 `cad5d5f0…`, cp-03 `cd055c9c…`, cp-04 none. **OPEN FOR DAVE BEFORE WAVE 2:** plan 02 Task 2's reading of `D-IMPL-245` (4) — suppression silence covers the NOT-VISIBLE principals (`PRIN-KYC-004`, `PRIN-TRD-003` take the same Policy-removed path as the no-grant `PRIN-NONE-000`), so `CPR-G02`/`CPR-G04` move to the refusal shape (`Reading confirmed: WIDE`); a `NARROW` answer is a stop-and-replan, not an execution branch. **Next free id `D-IMPL-246`.** **Next:** Dave reviews criteria + plans + that question; then `/gsd-execute-phase 24.5.1` (plan 01 first). Hand-edited; no `state.*` or `roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  PHASE 24.5.1 IS DISCUSSED (2026-09-03, /gsd-discuss-phase 24.5.1): Dave ruled all four gray areas in one message, recorded verbatim at `D-IMPL-245` and mapped in `24.5.1-CONTEXT.md` D-01..D-09 — product lane stays 1.0.0, `ASSEMBLER_VERSION` → 1.0.1 where refusal behavior changed; hw1 seeded with a deterministic artifact batch, the empty-fabric refusal kept as a negative test, harness clients untouched; transcripts/pages regenerated, README/summaries present-tense, CP-SPEC §F.4 findings preserved and closed by dated note; cp-01 `CPR-G08` REFUSES (suppression-silent), cp-04 ambiguous anchor → `AnchorAmbiguityRefusal`. Criteria NOT yet written (one per line at planning, `D-GATE-19`). Hand-edited; no `state.*` writer ran. **Next free id `D-IMPL-246`.** **Next:** `/gsd-plan-phase 24.5.1` against `24.5.1-CONTEXT.md`; criteria before Wave 1. PRIOR HEAD FOLLOWS.
  PHASE 24.5.1 IS SCHEDULED AND BANKED (`D-IMPL-244`, Dave, 2026-09-03): the return trip — re-version cp-01/02/03 and hw1 on the fixed SDK, correct every recorded lie; examples OPEN, `src/`+`runtime/` CLOSED; Phase 24.6 = cp-05 follows its gate. NOT discussed, NOT planned, no criteria (`D-GATE-19`). ROADMAP bullet, detail section (roster by source) and progress row added BY HAND; branch `phase-24.5.1` from `main` at `ad56c816`. **Next free id `D-IMPL-245`.** **Next:** `/gsd-discuss-phase 24.5.1` — read `.planning/phases/24.5.1-the-return-trip/.continue-here.md` first; criteria one per line before any plan. PRIOR HEAD FOLLOWS.
  **PHASE 24.5 IS CLOSED. `D-GATE-24.5` APPROVED BY DAVE, 2026-09-03, ENTERED IN `docs/DECISIONS.md` AFTER `D-IMPL-241` am.1.** Gate condition, his words: *"24.5 can gate after one in-phase map and four carries."* The map: `24.5-FIX-03` (`17a1de3f`) — the HTTP product door answers 400 for a `product-request-violation` envelope, mapped by kind (RED before / GREEN after / RED with the map dropped / restored). The carries, his words: R1 dangling-edge divergence → *"Ledger row on the next product rung, not a 24.5.1"*; R2 standing MCP resource → *"Shape already ruled"*; R4 serve-time pin window → *"Carry to L-02"*; `canonical.py` unclaimed by construction → *"a D-GATE sentence, not a second override"*. WR-02 interval kept as the whole complement of [0, 1] plus non-finite (*"Negatives-only would let 1.5 coerce 409s"*). Findings 1–9 as drafted; WR-01/WR-03 advisory-open. **Suite at `17a1de3f`:** 5045 collected = 1404 + 956 + 954 + 1731, four foreground chunks a proven partition; 4838 passed / 206 skipped / 1 failed = hw1 (`D-IMPL-242`, owned by `24.5.1`) — NOT suite-green by ruling; legs postgres 255 / fluree 285 / neo4j 22 / mongo 24; lint 0; mypy 211 clean; examples 5 / archive 0 vs base; digest `cfa493af…` reproduced. ROADMAP phase bullet and 18 plan lines ticked and the progress row rewritten BY HAND; this file BY HAND; no `state.*` or `roadmap.*` writer ran. Merged to `main` with `--no-ff` citing `D-GATE-24.5`; `RETIREMENT-COUPLINGS.md` regenerated last. **Next free id `D-IMPL-244`.** **Next:** the ladder's next rung is Dave's to name; `24.5.1` (hw1 rebuild, cp-04 stale comments, R1's ledger row on the next product rung) is open; `D-IMPL-221` (cp-02's phase) predates this phase. PRIOR HEAD FOLLOWS.
  WR-02 CLOSED, CRITERION 3 DISCHARGED, §3.1 PANEL RUN (2026-09-03, Dave's close sitting, phase-24.5 at `fcd01bd1`): in his order — `24.5-FIX-02` (`b6879c3c`: a `debt_tolerance` outside [0, 1] or not finite is refused BY NAME at the request boundary as `product-request-violation` / `not-a-proportion`, the sixth reason member, appended; never a coerced 409; no new gate type; `effective_debt_ceiling` unchanged; sabotage: acceptance of -1 restored → 6 RED, restored → green); criterion 3 by dated OVERRIDE (`cae7297c`: the 11-line `assembler.py` hunk is the `L-11` widening plan 07 owned; its `files_modified` now names the file; instrument at HEAD: 28 changed, one unclaimed BY CONSTRUCTION = `canonical.py`, the CR-01 close-time fix with no plan frontmatter); the four executor leftovers RECORDED in `24.5-VERIFICATION.md`'s appended dispositions; suite re-read at `cae7297c`: 5039 collected = 1404 + 955 + 954 + 1726 (four foreground chunks, a proven partition), 1 red = hw1 (`D-IMPL-242`) proven by deselection, legs postgres 255 / fluree 285 / neo4j 22 / mongo 24 green, lint 0, mypy clean, criteria digest `cfa493af…` reproduced, examples 5 / archive 0 vs base; then the CROSS-AI PANEL on that tree (`24.5-CLOSE-REVIEWS.md`, `fcd01bd1`): codex + cursor + gemini over six stdin-inlined bundles, each smoke-tested on a planted marker, one 0-byte gemini run re-run not counted; FIVE fixed in-phase (pin-error docstring lie + `replay()` Raises; two FAIL-OPEN branches in `check_product_gates.py`, RED-before/GREEN-after/RED-under-sabotage; two stale 'undirected' docstrings; a forward∧admitted composition test); ELEVEN rejected with evidence (the float-bypass finding all three reviewers raised falls to one measurement — a float is `type-mismatch` at the payload step — and is pinned as a control; three fabricated/inverted gemini quotations named); SEVENTEEN recorded. After the fixes chunk A 1404 / chunk B 866 green (collected now 5040). **Findings for Dave** are in `24.5-CLOSE-PREP.md`'s addendum (fifteen, of which four NEW from the panel need a ruling or a carry: staged-vs-pushed divergence on dangling edges (pre-existing, measured), the standing MCP resource's missing refusal channel (ruled shape), the HTTP status table beyond 409, the serve-time pin window). WR-01 and WR-03 remain advisory-open. **Next free id `D-IMPL-244`.** **Next:** present to Dave → his rulings on the addendum → `D-GATE-24.5` → merge `--no-ff` to `main` → regenerate `RETIREMENT-COUPLINGS.md` last. Hand-edited; no `state.*` or `roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  CR-01 CLOSED ON THE TREE (2026-09-02 evening, phase-24.5 at `555909ad`): `D-IMPL-243` + amendments 1 and 2, `D-IMPL-240` am.1, `D-IMPL-241` am.1 all ruled by Dave and written BEFORE each edit. Shipped: `ccf_hash_transparent` three-state mark, `_normalize` omits at sentinel, `canonical_generation_mismatch` refusal declared-scope in `replay()` (never `resolve_artifact`; the fifteen pre-243 record fields named on the replay roster only), CINV-06 lint with a COMMITTED 130-name base roster measured at 13bd250 (`--check` identical), 9 ticked rows + 7 amendment-2 ticks marked, golden 13bd250 record replays at HEAD on both legs. Consequences measured then ruled: cp-04 seals RESTORED to base (examples/ vs base = four gates.yaml + expected.yaml comment-only), archive pin BACK to 51f85386 (archive/ vs base 0 modified). Suite: ladder 837 passed / 116 skipped / 1 failed = hw1 (`D-IMPL-242`); lint 0; mypy clean; one pre-existing docs-test roster red logged in deferred-items.md (not fixed). **Next free id `D-IMPL-244`.** **Next sitting (Dave):** WR-02 (refuse a negative debt_tolerance by name at the request boundary; sabotage by restoring acceptance of -1), criterion 3 (`src/ccf/agents/assembler.py`: dated override if on a named ledger id, else revert), executor leftovers recorded not absorbed, then §3.1 panel on THIS tree (`24.5-CLOSE-REVIEWS.md`), then `D-GATE-24.5`. Hand-edited; no `state.*` or `roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  PHASE 24.5 IS EXECUTED, NOT CLOSED (2026-09-02, /gsd-execute-phase 24.5): 18/18 plans in 8 waves at `ceab40fd`, every plan with a SUMMARY; Waves 2/3/5/6 in worktrees merged `--no-ff`, Waves 1/4/7/8 on the main tree. Three post-merge integration fixes (`4614e6e` elided citation, `04945e0` a two-path fragment claim, `05c7b0c2` the admission-record schema, `ff903bd9` the shape-capture allowance). Two rulings at the Wave 6 boundary: `D-IMPL-241` (archived e2e transcript pin moved ONCE, one line, archive 265/0D/0R/1M) and `D-IMPL-242` (L-24 returned half REFUSES; hw1 red carried to 24.5.1). Return trip (`24.5-FLIP-ROSTER.md`, committed BEFORE any test edit): CPR-G05 FTS-G05 OFS-G06 flipped and rewritten; CFT-G16 the ruled re-seal; CFT-G15 GREEN; hw1 the one non-limitation red. Suite: 4975 collected, 4768 passed / 206 skipped / 1 failed (hw1, D-IMPL-242) -- NOT suite-green by ruling. `src/`+`runtime/` 27 files; `examples/` exactly five (four gates.yaml + cp-04 expected.yaml); criterion 28 digest cfa493af reproduced with a firing control. Code review `24.5-REVIEW.md`: 1 critical (CR-01: sentinel-default fields move every content hash `canonical.py::_normalize` renders -- pre-phase persisted replay records with a traversal step now DIVERGE; reproduced 5aab0c9f -> ef583667), 3 warnings (WR-02 reproduced: a negative request tolerance is accepted), 5 info. Verification `24.5-VERIFICATION.md`: gaps_found 24/27 -- the unrun §3.1 panel, one unclaimed file (`src/ccf/agents/assembler.py`, plan 07 plan-instructed) under criterion 3, CR-01 needing a ruling; criterion 16 UNCERTAIN (six co-occurrence edges). Findings for Dave are in `24.5-CLOSE-PREP.md` (D-GATE DRAFT, nine items) and the REVIEW. **Next free id `D-IMPL-243`.** **Next:** Dave evaluates the build; then §3.1 close on the shipped tree: cross-AI panel (`24.5-CLOSE-REVIEWS.md`, stdin-inlined payload per CLOSE-PREP), CR-01 ruling (a D-IMPL entry), WR-02 disposition, criterion-3 override, then `D-GATE-24.5`. Hand-edited; no `state.*` or `roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  PHASE 24.5 IS PLANNED (2026-09-02, /gsd-plan-phase 24.5): 18 plans in 8 execution waves, 43 tasks, in
  `.planning/phases/24.5-sdk-gap-catch-up-cp-00-through-cp-04/24.5-01..18-PLAN.md`. Ledger-id union across the
  plans = the 23-id set exactly (18 Wave-1 + 3 Wave-2 + L-18, L-49; arrivals none, departures none). Research
  measured the tree and put three rulings to Dave, recorded at `D-IMPL-240` BEFORE any edit: (1) criterion 25 has
  ONE named exception -- cp-04's two `perspective_content_addresses` re-sealed in the same commit as the L-02
  lineage-pin edit, `CFT-G16` on the flip roster by id (every `ProductLineage` field moves every content address;
  `canonical.py::_normalize` renders all fields); (2) L-01's pin is a JSON-LD claim read at `ledger@t:N` fed to the
  fallback (the Cypher route ignores every pin form, measured live); (3) L-14's ceiling is class-declared and a
  request may only tighten it. L-23 is CUT under criterion 18's own branch (precedence already true of the tree).
  Plan checker ran 3 iterations + 1 scoped re-check: 15 -> 9 -> 3 -> 0 issues; every finding verified against the
  tree before acting; one planner finding REJECTED (an unscoped digest instrument -- the scoped awk over the
  `### Phase 24.5:` section reproduces the pinned cfa493af... on the working tree and at 13bd250). Ordering:
  plan 01 (criterion 4, names D-IMPL-239 in its commit subject) first; Wave 2 = plans 13/14/15; return trip 16;
  close prep 17. `24.5-VALIDATION.md` nyquist_compliant. **Next free id `D-IMPL-241`.** **Next:**
  `/gsd:execute-phase 24.5` -- plan 01 must be the first commit. Hand-edited; no `state.*` or `roadmap.*`
  writer ran. PRIOR HEAD FOLLOWS.
  PHASE 24.5 IS DISCUSSED AND ITS CRITERIA ARE LOCKED (2026-09-02, Dave, at /gsd-discuss-phase 24.5). The
  ledger `24.5-LEDGER.md` holds 49 rows by id (`24.5-L-01`..`L-49`), collected from every source and re-measured
  at `13bd250`; Dave ruled the RULE (`D-IMPL-236`: SDK -> fix in 24.5; estate / tier / tooling / 223-new-class ->
  not 24.5) and the roster is the fence: WAVE 1 = 18 ids {L-01..04, L-05, L-06, L-08..13, L-16, L-21, L-22, L-23
  (conditional), L-27, L-28}; WAVE 2 = 3 ids {L-14, L-24, L-26}, unlocked by `D-IMPL-237` (224 AMENDED for Wave 2
  only, Dave's words verbatim) and `D-IMPL-238` (run_gates membership as shipped = FIVE tokens / TWO runners by
  name; 102 limb 3 = no PAYLOAD gate). `D-IMPL-239` rules cp-01/02/03 onto the one-document roster (criterion 4,
  before Wave 1's first SDK edit). L-29 DROPPED to D-09; L-46 WITHDRAWN (false premise reached Dave -- 24.2 already
  has its row and D-GATE-24.2 -- his answer NOT applied); L-47 corrected by appended entry: cp-01 is 24.2, not 24.1.
  `CFT-G15` will NOT flip (estate) -- the brief's example was wrong; criterion 24 names it GREEN. Return trip
  RULED: re-run cp-01..04 UNCHANGED, flip roster by id, rewrite ONLY flipped test assertions; no version / README /
  seal / page change in 24.5; `24.5.1` is the one rebuild follow-on iff the roster is non-empty. ROADMAP: 28
  criteria LOCKED one per line (continuation-line detector proven on a planted wrap), block sha256
  cfa493afedfa8c1a1a22b3fbaa8eee0f2fd964a76202e0ae4e9196a6f5ec45b5; two marked amendments (cp-01 label; Phase 24
  gate count -> five by name). Branch `phase-24.5` from tag `phase-24.5-base` = `13bd250`. Examples CLOSED except
  criteria 12, 13, 25. **Next free id `D-IMPL-241`** (`D-IMPL-240` written at planning 2026-09-02). **Next:** `/gsd:plan-phase 24.5` against `24.5-CONTEXT.md`
  and `24.5-LEDGER.md`; two waves; Wave 2 cannot start before 237/238 (already in the log). Hand-edited; no
  `state.*` or `roadmap.*` writer ran. PRIOR HEAD FOLLOWS.
  PHASE 24.5 IS COMMISSIONED AND BANKED (D-IMPL-235, Dave, 2026-09-02): the comprehensive SDK gap catch-up for
  cp-00 through cp-04. Direction only -- NOT discussed, NOT planned, no criteria (D-GATE-19). Next action is
  /gsd-discuss-phase 24.5, whose FIRST deliverable is a ledger sitting with no code. src/ and runtime/ are OPEN
  in 24.5. One ruling open: is D-IMPL-224 amendable if 24.4-D-31 is a fix-row. Read the phase's
  .continue-here.md first. Next id D-IMPL-236. PRIOR HEAD FOLLOWS.
  2026-09-01 -- **PHASE 24.4 IS CLOSED. `D-GATE-24.4` APPROVED BY DAVE, 2026-09-01, ENTERED IN
  `docs/DECISIONS.md` AFTER `D-IMPL-234`.** Everything SS3.1 orders ran in order on the SHIPPED
  TREE: cross-AI panel (`24.4-CLOSE-REVIEWS.md` SS1-SS10; findings 1-5 fixed under sabotage naming
  their own gate id and restored; six rejected with evidence) -> single-agent review
  (`24.4-REVIEW.md`, 16 findings) -> Dave's disposition -> `24.4-FIX-05` (CR-01 serve-path
  `SystemExit` -> `AssemblyRefused`; WR-05; WR-01; CR-02's 409 claim removed from ALL THREE artifacts
  that carried it, one test reads all three) -> SS12 of the close record -> the gate. **RULED at the
  gate:** family-scope guards STAY `SystemExit` -- *"deployment/binding, not caller data; same
  discriminator as unset env / mis-authored config."* **THE SUITE SENTENCE, PER THE CARVE:** nine of
  ten `make ci` legs rc=0; pytest **4664 passed / 45 skipped / 1 failed = 4710** collected, three
  foreground chunks proven a partition; the 1 is
  `test_the_one_document_exemption_has_not_spread`, carved by `D-IMPL-234` and NOT suite-green --
  cp-01/02/03's exemption claims remain UNRULED. Ratchets: unanchored citations 0; gates 16;
  `observed_red` null 0; `src/`+`runtime/` changed files 0 (control: `examples/` 24). Gaps
  `24.4-D-26`..`24.4-D-37` recorded, none closed. 17 deferred rows. **Next free id `D-IMPL-235`.**
  ROADMAP ticked and progress row rewritten BY HAND; this file edited BY HAND; no `state.*` or
  `roadmap.*` writer ran. Merged to `main` with `--no-ff` citing `D-GATE-24.4`. **Next:** the ladder's
  next rung is Dave's to name; cp-01/02/03's exemption claims (`D-IMPL-234`) and `D-IMPL-221`'s
  cp-02 history are the open items that predate this phase.
  PRIOR: 2026-09-01 -- **PHASE 24.4 IS BUILT, NOT GATED. All 14 plans complete, the build was EVALUATED
  by Dave against his own five-check gate and ALL FIVE HELD, and his FIVE RULINGS are logged at
  `D-IMPL-233` and now APPLIED through the phase record.** **NOTHING IS CLOSED.** There is no
  `D-GATE-24.4`, nothing is marked complete, `ROADMAP.md` carries no phase tick, and the CLAUDE.md
  SS3.1 close panel has NOT run. Dave: *"Do not treat 14/14 plans as a close. No `D-GATE` until that
  run plus SS3.1."* The run is done; the panel is next, and it reviews the **SHIPPED TREE** rather
  than the plans -- write it to `24.4-CLOSE-REVIEWS.md`, inline the source over stdin (codex can exit
  0 having read nothing, and a single argv string caps at 128KB), brief it on the known findings, and
  verify every finding against the tree before recording it.
  **THE FIVE RULINGS, AND WHAT EACH ONE MOVED.** (1) **Criterion 37 amended a SECOND time** --
  `resources/list` -> `[]`, `resources/templates/list` -> the URI template, a read still refuses
  `ProductNotServable`; *"enumerable in `resources/list`"* STRUCK; the shipped check asserting BOTH
  listings stays; `24.4-D-34` unchanged. (2) **The `mkdocs.yml` cp-04 comment DELETED** -- `grep -c
  'cp-04' mkdocs.yml` is now **0** against a positive control of **1** for `docs_dir`, and the file is
  diff-EMPTY against the phase base. Plan 13's verify line no longer requires it; the measurement
  moved to `deferred-items.md` item 11, a document a human reads and no check consults. Dave: *"A
  `grep -q cp-04` that passes on a comment is an idle gate."* (3) **Cycle 2 RECORDED, not served** --
  `24.4-D-37`, an ESTATE gap of `24.4-D-32`'s class; `CFT-G15` asserting the unreachability is correct
  and stays; **no seventeenth gate**, the roster stays SIXTEEN. (4) **The three first-sabotage passes
  are ADVISORY**, with the lesson recorded as a CLOSE NOTE and no new mechanism: *criterion-shaped
  sabotage can still miss; a sabotage counts only when the gate goes RED naming its OWN id and the
  tree is restored.* (5) **The gap roster is ELEVEN under RENAMED ids**, `24.4-D-26`..`24.4-D-36`.
  **THE IDS ARE `24.4-D-NN` NOW, AND THE MAPPING IS STATED ONCE.** Dave: *"Stop using bare `D-26` in
  this phase's record - those ids already mean Phase 17."* Measured, roster not count: a bare
  `D-26` grep over `docs/DECISIONS.md` matches SIX entry lines -- `D-IMPL-145`, `D-IMPL-176`,
  `D-IMPL-199` (Phase 17) and `D-IMPL-226`, `D-IMPL-232`, `D-IMPL-233` (24.4). The LIVE records were
  normalized; the completed SUMMARYs and other dated snapshots were deliberately NOT rewritten, and
  `D-IMPL-232` AMENDMENT 1 carries the mapping a reader resolves them against.
  **ONE QUESTION IS OPEN AND IT IS DAVE'S: does criterion 49's roster extend from ELEVEN to TWELVE?**
  Ruling 3 folds cycle 2 into the 24.4 gap list; ruling 5, in the same message, enumerates that list
  as exactly eleven. Both cannot be mechanical without a twelfth id. `24.4-D-37` is recorded OUTSIDE
  the roster; criterion 49 is NOT extended and nobody wrote that he approved twelve (`D-IMPL-227`).
  **MEASURED AT THIS SITTING, each against a control shown to move:** `tests/examples` **787 passed /
  113 skipped** rc=0; `tests/invariants/test_citation_coverage.py` **5 passed** rc=0 with the ratchet
  watched go **0 -> 1 -> 0** under a planted line-anchored citation and the tree restored;
  `tools.lints --all` rc=0, with a planted harness import in `src/` driving it to rc=1 naming
  `cinv02-harness` and back to rc=0 on removal; `make docs-strict` rc=0; **16** gate ids enumerated
  `CFT-G01`..`CFT-G16` with **0** `observed_red` null and **0** `CFT-G17`; `src/` and `runtime/`
  diff-EMPTY across `92761e0..HEAD` against a positive control showing `examples/` moved **24** files
  in the same window -- and it is recorded that a misspelled `srcc/` pathspec diffs empty EXACTLY like
  a clean one, which is why that control exists. **`.planning/ROADMAP.md` was NOT touched by this
  session** -- the orchestrator owns it and had already amended criteria 37 and 49 and both plan
  checklist rows. **`src/` and `runtime/` were NOT touched.** STATE.md was hand-edited only, backed up
  before every stage; no `gsd-sdk query state.*` or `roadmap.*` writer was invoked.
  PRIOR: 2026-09-01 -- **PHASE 24.4's BUILD IS DONE AND THE PHASE IS PAUSED FOR DAVE. 14 of 14 plans
  complete.** `example_delivery.md` sections 1 and 11: Dave evaluates the built product HIMSELF
  before any close panel, `D-GATE` or completion mark. **NOTHING IS CLOSED** -- no `D-GATE-24.4`
  exists, `ROADMAP.md` is untouched, no milestone is marked complete, and no close panel has run.
  **The product:** `examples/cp-04-corporate-family-tree`, rung 04 and the first of Tier 2 -- the
  ladder's first two-store product, first graph traversal, first over MCP, three ontology roles.
  **SIXTEEN gates** `CFT-G01`..`CFT-G16`, every one observed RED under its own id, declared as DATA
  under a closed schema; `CFT-G17` stays WITHDRAWN and must never be minted. **`D-IMPL-232` records
  all ELEVEN gaps `24.4-D-26`..`24.4-D-36` and closes NONE of them** -- note the plan text said eight and the
  ROADMAP bullet said six; criterion 49 says eleven, and the lag is recorded rather than reconciled.
  **`src/` and `runtime/` are diff-EMPTY across `92761e0..83953e8`**, asserted by
  `tests/examples/test_cp_04_phase_record.py` against pinned base and ceiling files, with the
  instrument proven able to report a change and `srcc/` refused by name. Measured at the pause:
  `tests/examples` **769 passed / 113 skipped** rc=0, `tools.lints --all` rc=0, unanchored Python
  citations **0** against a ceiling of 0, gate ids **16** with **0** still null.
  **FIVE THINGS NEED DAVE and none was decided here** -- (1) criterion 37's amended wording names
  `resources/list` where the shipped door lists the URI only under `resources/templates/list`; a
  wording amendment to a ruled criterion, the THIRD criterion in this phase found wrong against the
  tree; (2) whether the `mkdocs.yml` cp-04 COMMENT stays, given that plan 13's `grep -q 'cp-04'`
  now passes on it rather than on a nav entry; (3) cycle 2 is unservable -- zero external in-edges
  and no member carries an LEI -- a plan-versus-estate discrepancy of `24.4-D-32`'s shape; (4) three
  gates passed their own sabotage as their criteria worded them (`CFT-G05`, `CFT-G16`, `CFT-G10`),
  all three rewritten BEFORE shipping so the shipped count is zero; (5) the plan-text lag above.
  PRIOR: 2026-09-01 -- **PHASE 24.4 IS EXECUTING -- 8 of 14 plans complete, `24.4-09` IN FLIGHT at a
  `/clear` boundary.** `main` = `7fc1bb4`. **READ
  `.planning/phases/24.4-corporate-family-tree-cp-04-first-multi-store-product-fluree/.continue-here.md`
  FIRST** -- it carries the in-flight state, the one OPEN question, wave 8's constraints and the
  anti-patterns. **SIXTEEN gates** `CFT-G01`..`CFT-G16` (`CFT-G17` withdrawn), **THREE** ontology
  roles, gaps **`D-26`..`D-36`** recorded and none closed, **zero** files under `src/` or `runtime/`
  across the whole phase. Baseline to print as NUMBERS: forbidden files 0, unanchored citations 0,
  gate ids 16. **Dave rulings this session: `D-IMPL-225` through `D-IMPL-231`** -- Gate 1 approved
  with three amendments; one envelope per node with `relationship_rules: []`; a **retraction**
  (`227`) of a ruling never made, with wave 4's work reverted; jurisdictions `{NL, US-DE}` closed;
  policy admitting on **observed family membership** with jurisdiction served and never inherited;
  `D-36` plus **SERVE** on context debt; and `D_c` gated on **identity dispute**, not on a missing
  Postgres row. **OPEN, needs Dave:** whether `--role` survives -- keep only if two roles yield a
  different `content_address`, else drop it and say so in the README. **The unanchored-citation
  ratchet went 1 -> 41 during this phase and is now 0**; it can only be read as a number.
  PRIOR: 2026-09-01 -- **PHASE 24.4 IS EXECUTING.** Criteria LOCKED before planning at `a80c81e`
  (forty-nine, D-GATE-19). Fourteen plans in twelve waves at `6b752e4`, revised at `f734668`
  (six plan-check blockers + seven warnings) and `e1c2e47` (role-1 strike folded through).
  **Ontology role 1 STRUCK and `CFT-G17` WITHDRAWN** (Dave, ruling A, `853ccc9`): the product
  carries THREE ontology roles and SIXTEEN gates. Two independent blockers, both measured --
  `D-32` the ESTATE gap (no LEI-bearing anchor reaches a node outside the 7-class profile
  within depth 3) and `D-33` the MECHANISM gap (`GQ-10` types traversal on EDGES only; no
  node-class admission filter exists), recorded at `e8cb3c7`. Refused by name: a second anchor
  whose only class variation is `Guarantor` on the root, a positive-property restatement
  (tautology over a class-homogeneous population), and projecting `person_role`'s 44
  `ten_percent_owner` rows onto `owns` -- Dave: *"changing the fixture so a sentence stays
  true."* SMCI headline untouched: 22 nodes, both cycles, depth 3, ceiling 6, 722 edges.
  **Wave 2 is Gate 1 and BLOCKS for Dave** (CP-SPEC-004). Wave 12 pauses again.
  **`state.begin-phase` CORRUPTED STATE.md this session** -- 2517 lines to 1653, 864 lost, while
  reporting success. Restored byte-identical from a pre-call backup and hand-edited since.
  Do not call a `state.*` writer on this file without backing it up first.
  PRIOR: 2026-08-31 -- **PHASE 24.3 IS CLOSED; 24.2 AND 24.2.1 ARE GATED RETROSPECTIVELY; TIER 1 OF
  THE CONTEXT PRODUCT LADDER IS COMPLETE.** `D-GATE-24.3` at `5dfdd8d`; `D-GATE-24.2` and
  `D-GATE-24.2.1` APPROVED on Dave's inspection -- the success criterion was his inspection,
  ruled explicitly. All four rungs closed: cp-00 (24.1/24.1.1), cp-01 (24.2), cp-02 (24.2.1),
  cp-03 (24.3). Tree clean, `origin/main` = `92761e0`.
  **THE TWO SDK-SURFACE QUESTIONS THAT HAVE GATED PHASE 24 PLANNING SINCE 2026-08-25 ARE NOW
  RULED.** **`D-IMPL-223` -- FOUR SCHEDULING CLASSES, FOREVER, AS THE SCHEDULER; the Standard's
  eight names are SPEC VOCABULARY.** `OperatorCategory` (`src/ccf/operators/base.py:60`) is a
  plan-order class carrying INV-CH7-26/28, not a synonym for a Standard name -- so *"the name
  Enrich is absent from `src/`"* and *"I cannot schedule this work"* are DIFFERENT FAILURES and
  only the second is an SDK hole. Measured BEFORE the ruling: `Enrich`, `Similarity`, `Evaluate`
  and `Federate` have **ZERO** uses across the whole ladder, and cp-01/cp-02/cp-03 each invoke
  exactly **ONE** L4 operator (`Policy`) -- **no example was ever blocked by a missing operator,
  so none is rewritten.** `OperatorCategory` stays CLOSED for v0, no user-extensible categories,
  and it is NOT opened in 24.4; users extend by novel KEY through the `Operator` Protocol and
  `OperatorRegistry.register`, never by novel CATEGORY. **`D-IMPL-212` STAYS OPEN**, deferred to a
  product that cannot run in the four slots rather than closed by ruling. A reading was RAISED AND
  REFUSED BY NAME: registering an attribute batch as `category="traversal"` because its scheduling
  resembles a walk -- Dave: *"the name still teaches the wrong thing, and cp-03 already chose L2
  assembly for that work."*
  **`D-IMPL-224` -- PRODUCT GATES ARE A DECLARED ARTIFACT PLUS A CI COVERAGE CHECK**, not a
  serve-time type. NO `ProductGate` Protocol in 24.4; the Standard's extra three gates are
  DECLARED PRODUCT GATES, never new members of `run_gates`. Checker scope is the `cp-*` ladder
  ONLY -- `hw1-*` and `s1-*` declaring zero product gates stay legal.
  **THE "3 VERSUS 6 GATES" PREMISE WAS FACTUALLY WRONG AND IS CORRECTED WITH MEASURED
  IDENTITIES.** `src/ccf/products/gates.py` defines FIVE gate identity tokens across TWO runners:
  `run_gates` (`:426`) runs empty-operator, lineage STRICT EQUALITY, TTL bounds and
  `refuse_attestation` (`:213`); `run_federated_gates` (`:507`) runs empty-operator, lineage
  ATTRIBUTABILITY and TTL bounds. `refuse_attestation` returns `None` when `attestation is None`
  (`:240`), so its enforcement is CONDITIONAL. `D-IMPL-102` limb 3 is QUOTED IN FULL rather than
  characterized, because its heading (*"No fourth gate is added to `run_gates`"*) and its
  explanatory clause (*"not joined by a payload gate"*) DIFFER IN SCOPE; which reading governs is
  left **OPEN** and is NOT decided by `D-IMPL-224`.
  **THE GATE SEAM IS THE REAL EXTENSION GAP, AND IT HAD ALREADY FAILED SILENTLY AT SCALE.** FORTY
  product-level gates across four products carry ZERO SDK expression -- declared in artifacts,
  referenced in example code only as COMMENTS, executed by hand-written pytest linked by naming
  convention alone. cp-03's own test docstring records the failure: *"Before this module existed,
  none of the fourteen ran at all."* Contrast `run_gates`, defended by `_GATE_TOKEN`, the
  `_ServableProductMeta` metaclass and `GateBypassError`. **The population with the most semantic
  weight had the least structural support.**
  **A MEASUREMENT OF MINE WAS WRONG AND WAS CAUGHT BEFORE IT REACHED A DOCUMENT.** A first
  instrument keyed on FUNCTION NAME reported cp-00 0/8, cp-01 0/9, cp-02 0/9 -- but cp-01 and
  cp-02 name their tests by BEHAVIOR and cite the gate id in the docstring; only cp-03 puts the id
  in the function name. Re-measured on id presence: cp-00 **1/8**, cp-01 **8/9**, cp-02 **9/9**,
  cp-03 **15/15**. **Docstring presence is an UPPER BOUND, not proof of an executing assertion** --
  neither figure may be quoted as coverage, and the checker must require an EXECUTING test, never
  `id in file`. THREE PRODUCTS USE THREE DIFFERENT LINKING CONVENTIONS, which is exactly why the
  link must be DECLARED DATA WITH CLOSED KEYS rather than inferred by grep.
  **DEBT, NOT A REOPENED GATE** (Dave, verbatim: *"Finding under 24.4. Do not reopen
  D-GATE-24.1."*): cp-00 carries SEVEN declared gates with no test-file presence (`IH-G01`,
  `IH-G02`, `IH-G03`, `IH-G05`, `IH-G06`, `IH-G07`, `IH-G08`) and cp-01 carries ONE (`CPR-G08`),
  inside phases closed by `D-GATE-24.1` and `D-GATE-24.2`. Carried as a finding under 24.4, the
  same pattern as `D-IMPL-221` and cp-02's missing phase home.
  **PHASE 24.4 IS ANCHORED, NOT PLANNED** -- `corporate-family-tree` (cp-04): first Tier 2 rung,
  first MULTI-STORE product, first GRAPH TRAVERSAL, and the LADDER'S FIRST MCP DOOR. All four
  ontology roles in scope (constrain the walk, served in the product, drive the projection,
  validate the assembly). Assembler STANDALONE with two thin callers -- `run.py` in-process and
  `server/serve.py` over `build_egress_server` -- so the standalone property is DEMONSTRATED by
  two callers sharing one module, not asserted. A2A explicitly deferred to a later example.
  Fluree `fibo-v2` is build-ready at `ledger_t = 4,560`, the first rung with a real
  `graph_snapshot_at` anchor (`D-IMPL-218`). **NO SUCCESS CRITERIA ARE WRITTEN** -- `D-GATE-19`
  locks them at the discuss sitting -- **24.4 Success Criteria lock at the discuss sitting
  (`D-GATE-19`)**, and that is the only precondition. `D-GATE-24.3` is APPROVED and closed.
  **NOT RE-MEASURED THIS SESSION, AND NAMED AS STALE RATHER THAN INCREMENTED:** the `progress:`
  block below still reads `total_phases: 31 / completed_phases: 29 / percent: 94` from the Phase
  23.1 gate. Phases have closed since and 24.4 has been added, but the figures are NOT corrected
  here because `D-19` and `D-IMPL-174` require a RE-MEASURE FROM THE TREE, not an increment, and
  no re-measure was run this session. PRIOR:
  2026-08-28 -- **PHASE 24.1.1 IS CLOSED AND APPROVED. `D-GATE-24.1.1` LOGGED, MERGED TO
  `main --no-ff`, PUSHED.** Seven waves, eleven commits. All SEVENTEEN criteria met, locked
  before Wave 1 and verified one-per-line by a CONTINUATION-LINE DETECTOR beside the count; the
  criteria block's sha256 at the close is **BYTE-IDENTICAL** to the pin taken before Wave 1.
  **`D-59` and `D-60` are CLOSED.** `make ci` green on all ten legs, chunked FOREGROUND,
  partition proven on COLLECTED counts: 1708 + 1515 + 1086 = **4,309**, run to **4,191 passed /
  118 skipped**.
  **THE `src/` FENCE HELD AS A NAMED ROSTER JUDGED BY SET EQUALITY** -- exactly
  `deployment/operators.py`, `agents/assembler.py`, `replay/record.py`, re-asserted AFTER the
  close-time fixes. **AND IT MOVED ONCE, ON THE RECORD, BEFORE AN EDIT** (`D-IMPL-214`):
  criterion 9's amendment required any extra module to be enumerated first, research found the
  two-module fence could not hold, and the fence was widened by exactly one with Reading A
  refused by name. **The fence did not quietly move -- it was moved deliberately and in public.**
  **THE CLOSE PANEL EARNED ITS KEEP THREE TIMES.** 238 KB inlined on stdin, nine invocations
  rc=0, read-proofs cursor 8/8 and gemini 6/6 against controls 0/2 and 0/1. **THREE REVIEWERS
  INDEPENDENTLY FOUND ONE ROOT DEFECT**: a refusal block validated as *parsing* and then stored
  VERBATIM, so one refusal admitted a FAMILY of blocks -- a replay-determinism defect inside
  criterion 9's own machinery. **THE PHASE'S WHOLE SUBJECT WAS UNGATED**: every control read
  `signature.parameters` and none read `return_annotation`, so narrowing the Protocol's return
  type left the ENTIRE SUITE GREEN until the panel said so. And **the phase's own public record
  cited a green over a set that excludes its subject** -- *"mypy clean over 211 source files"* as
  evidence about `examples/`, which mypy never reads. **SEVEN BLOCKING FIXED IN-PHASE; FIVE
  REJECTED AND RECORDED AS REJECTED** -- gemini resolved 6/6 citations and got five claims wrong.
  **A resolved citation says a reviewer LOOKED, not that it UNDERSTOOD.**
  **CRITERION 9 IS MET AS RULED, NOT ABSOLUTELY**, the qualifier in its own row: the caller who
  never calls the minter still writes a well-formed FALSE record. Named in four places.
  **SEVEN FOR SEVEN** -- the class appeared in the phase's own machinery in every wave, including
  a criteria extractor that swept all 21 phase blocks and would have compared 210 against 210 at
  the gate and PASSED, a partition proof anchored on a directory listing, and stale
  `__pycache__` TWICE making a correct tree look broken.
  **A STATE.md CORRUPTION WAS CAUGHT AND REVERSED AT THIS GATE.** A GSD state writer rewrote
  this file at 16:30 -- `status: executing` -> `completed`, the ENTIRE `last_activity` history
  including the `D-GATE-24.1` record and its PRIOR chain DELETED, and a `progress:` block
  injected whose own numbers are incoherent (262 completed plans of 243 total). It was swept
  into `52bab3c` by a `git add -A`. Restored from `phase-24.1.1-base` and re-hand-edited; the
  twelve-entry PRIOR chain and the `D-GATE-24.1` record are verified present. **`D-15` is not
  advice: no `state.*` writer, and diff every planning file before committing it.**
  **DAVE'S GATE RULINGS BEYOND APPROVAL (`D-IMPL-216`):** do NOT restructure `cp-00` at close --
  the example refuses BEFORE its identity checks where the SDK does identity first, and
  correcting it is example data-flow that criterion 16 fences; inheritor is the next CP example.
  And NO hygiene phase now -- the four tooling findings stay recorded and unclosed on the
  `DOCS-`/tools lane. *"They are real; they are not what 24.1.1 was for."*
  **NEXT:** nothing scheduled. `D-58`'s obligation is discharged. PRIOR:
  2026-08-27 -- **PHASE 24.1 IS CLOSED AND APPROVED. `D-GATE-24.1` IS LOGGED, THE BRANCH IS
  MERGED TO `main --no-ff`, AND WAVE 11 RAN CLAUDE.md §3.1 IN ORDER WITHOUT MERGING ITS
  STEPS.** All NINETEEN criteria met. `src/` and `runtime/` diff-empty against
  `phase-24.1-base` **re-asserted AFTER the close-time fixes**, because a criterion asserted
  before a fix was asserted against a different tree. `make ci` GREEN, all ten commands rc=0.
  **THE PANEL WAS THREE REVIEWERS x THREE INLINED BUNDLES, NINE INVOCATIONS, ALL rc=0.**
  450 KB inlined rather than pointed at; the close record NAMES every subject that went to no
  reviewer. Each proven to have read by resolving its own citations against a negative
  control -- codex **9/10**, cursor **10/10**, gemini **10/10**, every control **0/2**.
  **SEVEN BLOCKING FINDINGS FIXED IN-PHASE, FIVE REJECTED AND RECORDED AS REJECTED.** Every
  blocker was one shape: *a claim that was true when written and went false without anything
  going red, because none of them is gate-shaped.* A specification fan-out of **52** where the
  Wave-1 probe measured **51** and measured no estate-wide maximum at all -- the 52 traced to
  `24.1-01-PLAN.md:245`, **written BEFORE the probe that contradicted it**. A step timing of
  **"~344 ms by subtraction"** occurring **exactly once in the whole phase record**, in that
  cell, where the table's own numbers give **258**. Front matter calling §G unwritten in a
  document whose §G is present. A Control Plane artifact asserting *"the refusal is the
  deployment's own code"* when **no such code exists**.
  **THE MOST VALUABLE RESULT OVERTURNED A PANEL FINDING RATHER THAN ADDING ONE, AND BY
  SABOTAGE RATHER THAN BY READING.** cursor said the criterion-2 gate could stay green while
  every `sdk_mechanism` in the recipe was fiction. Mechanism right -- the test reads that
  field **zero** times. Conclusion wrong -- `tools/lints/citations.py` scans `.yaml` and gates
  them: a fabricated symbol moved the lint **rc=0 -> rc=1** naming file, line and symbol,
  while the test stayed **9 passed**. **Acting on the finding would have added a redundant
  assertion.** Beside it, the caution the close earned: **a resolved citation is NOT a correct
  finding** -- gemini resolved 10/10 and still inverted the sense of its cited text twice, and
  a third reviewer's refutation of that claim was ALSO wrong by an over-narrow grep. Three
  instruments, one passage, three different misreadings; the passage is compliant.
  **THE CLASS TURNED UP IN THE CLOSE'S OWN MACHINERY -- TENTH CONSECUTIVE WAVE.** The `make
  ci` partition proof was WRONG FIRST: it compared the chunks against `ls -d tests/*/` and
  printed `IDENTICAL` while the sum was **4,250** against a collection of **4,291**. **41
  tests live in `tests/*.py` and the check never looked at files** -- and they were
  `test_smoke`, `test_surface_completeness`, `test_surface_drift` and
  `test_surface_shape_capture`, exactly where a documentation-only phase's regressions land.
  Corrected against the COLLECTED COUNT, which a directory listing cannot fake: 1699 + 1514 +
  1078 = **4,291**, run to **4,173 passed / 118 skipped**. A second instrument error caught in
  flight: the criterion-1 front-matter check searched `head -30` of a front matter running to
  line **114** and reported the row ABSENT -- **the document was right and the check was
  wrong**, and the corrected check carries a control proving a fabricated row is not matched.
  **AND THE REVIEW TOOLING FAILED SILENTLY BEFORE IT SUCCEEDED:** the first nine invocations
  returned **rc=126 in 0 seconds with 0-byte outputs** -- `Argument list too long`, because
  Linux caps a single argv string at 128 KB regardless of the 2 MB `ARG_MAX`. **Read through a
  pipe, or not read at all, that is indistinguishable from three reviewers finding nothing.**
  Fixed on stdin, each smoke-tested first.
  **CRITERIA RE-ASSERTED WITH THE MECHANICAL AND DOCUMENTARY CLAIMS SPLIT, NEVER COLLAPSED:**
  16/17/19 RE-RUN; 1/9/11 RE-READ because a fix touched their subject; 10/12/13/14/18 PROVEN
  UNTOUCHED by path-scoped diff. *"All nineteen re-asserted"* is deliberately not written.
  **DAVE'S FOUR RULINGS AT THE GATE:** approve and merge `--no-ff`; **`D-IMPL-213`** confirms
  the scoped SDK phase for **`D-59`/`D-60` ONLY** -- the other two SDK gaps and the three
  tooling blinds stay recorded and unclosed; **NO fail-closed refusal in `cp-00`** (24.1's
  no-build posture stands; refusal-as-data is `D-59`/`D-60` work, not a close-time feature
  sneak); push. **NEXT:** the `D-58`/`D-IMPL-213` short SDK phase. PRIOR:
  2026-08-27 -- **BLOCKER A IS CLOSED BY RULING (`D-66`, Dave) AND `make ci` IS GREEN
  EXCEPT FOR ONE GENERATED REPORT AWAITING ITS REGENERATION. WAVE 10 IS UNPARKED AND
  WAVE 11 CAN START.** Dave ruled Option 1 -- `cp-00` onto the one-document exemption --
  **in a sharper form than was offered**: the bound is now a NAMED ROSTER judged by SET
  EQUALITY, not a ceiling raised to 2. A bare count was refused as the same defect class
  the phase had just spent two waves on: *"next claimant is silent if someone deletes a
  name from the list and the count stays 2."*
  `MAXIMUM_ONE_DOCUMENT_DEPLOYMENTS` and `MAXIMUM_SDK_SUPPLIED_DEPLOYMENTS` are RETIRED
  as counts, replaced by
  `tests/products/test_gate_two_call_shape.py::RULED_ONE_DOCUMENT_DEPLOYMENTS` and
  `tests/products/test_gate_two_call_shape.py::RULED_SDK_SUPPLIED_DEPLOYMENTS`, both
  `frozenset[str]`, sharing ONE predicate
  `tests/products/test_gate_two_call_shape.py::_roster_problems`. **THREE FAULTS ARE NOW
  REPORTABLE WHERE A CEILING SAW ONE**: arrival, departure, and the SWAP that holds the
  cardinality while moving the membership -- `D-65`'s *right count, wrong member*, which a
  ceiling cannot see by construction. **EMPTY IS RED**: the predicate reports every ruled
  member as departed on an empty claim set, so a detector that has stopped matching cannot
  read as compliance.
  **EVERY HALF WAS WATCHED FAILING, NOT ASSERTED.** Drop `cp-00` from the roster -> red
  naming it as an arrival; add a phantom name -> red naming it as a departure; gut the
  predicate to `return []` -> BOTH controls red. Restored **101 passed**, from 99 passed /
  2 failed. The premise-detector test keeps a LITERAL roster on purpose and the sabotage
  PROVED the independence -- dropping `cp-00` from the constant left that test green,
  which is exactly why the two must not share a source.
  **THE LEGS NOBODY RAN WERE RUN.** `tests/products` + `tests/invariants` **674 passed /
  0 failed**. Full `make ci` re-measured chunked FOREGROUND, `make -n ci` printed first as
  proof the ten commands ARE the recipe, and the test chunks proven a PARTITION: 1699 +
  1524 + 1068 = **4,291** collected, disjoint paths, run to **4,173 passed / 118 skipped**
  with every exit code read unpiped. **9 of 10 CI commands rc=0.** The tenth is
  `docs/surface/examples/RETIREMENT-COUPLINGS.md` stale at 287 -> 288 rows, which is the
  GENERATED report reacting to this session's own `.planning/` writes -- regenerated LAST,
  by design.
  **THE CITATION RATCHET CAUGHT THE RENAME AND CAUGHT EXACTLY IT**: two `cite03-node-id`
  findings, `.planning/STATE.md` and the handoff, both citing the retired symbol; nothing
  else in the tree. `docs/DECISIONS.md` and `.planning/phases/*` are EXEMPT as dated
  records, so the historical `D-IMPL-137`/`139`/`146` entries still say *"ceilinged at
  one"* -- true when written, and not falsified to suit the rename. Both live citations
  RE-POINTED with the superseded name kept beside them. `tools.lints --all` rc=1 -> rc=0.
  **ONE STALE ARITHMETIC CLAIM CORRECTED IN PASSING**: the `MINIMUM_RESOLVED_BINDER_SITES`
  comment said *thirteen* projecting bodies with `s1-00` the sole abstainer. Measured:
  **fourteen** bodies, twelve readable sites across ELEVEN files, **three** abstainers
  (`s1-00` and `cp-00` under `D-IMPL-137`, `hw1` under `D-IMPL-141`). True when written,
  false once `cp-00` landed. PRIOR:
  2026-08-27 -- **PHASE 24.1 WAVE 10'S FOUR TASKS ARE COMPLETE AND THE WAVE IS PARKED ON
  ONE DAVE DECISION. `make ci` IS RED WITH ONE FAILURE LEFT AND IT IS NOT THIS PHASE'S
  DOING.** Thirteen foreground commands, every exit code read UNPIPED, criterion 19's four
  conditions each named and satisfied, and the test chunks proven a PARTITION of all 4,291
  tests three ways. Result at wave end: **3 failed / 4,170 passed / 118 skipped**; after
  the orchestrator closed Blocker B, **1 failure class remains (2 assertions)**.
  **BOTH FAILURES PRE-DATED THIS WAVE AND SURVIVED NINE WAVES FOR ONE REASON: every wave
  measured `tests/examples` ALONE.** `tests/products` and `tests/invariants` were never run
  all phase. That is the `D-65` shape at the level of the GATE ITSELF -- a green that was
  green about a subset nobody restated.
  **BLOCKER B WAS THE ORCHESTRATOR'S AND IS CLOSED AT `4cb235e`.** The citation ratchet
  (`D-IMPL-114`: cite `path.py::Symbol`, never a line number) fired on `.planning/STATE.md`
  line 18, which arrived at `6d32ccd` -- the Wave 9 tracking commit -- inside a sentence
  ABOUT the danger of a citation that resolves and is wrong. Now cites
  `tests/examples/test_section_one_is_agent_free.py::SECTION_ONE_GLOB`; symbol resolves at
  line 120, control a fabricated variant returns 0.
  `tests/invariants/test_citation_coverage.py` **3 failed -> 5 passed**. Noted beside it:
  `tools.lints --citations` exits **0** on the same subject the ratchet FAILS on, because
  one declines to check what the other counts -- **an eighth finding, TOOLING.**
  **BLOCKER A IS DAVE'S AND IS THE ONE THING WAVE 11 WAITS ON.**
  `tests/products/test_gate_two_call_shape.py::RULED_ONE_DOCUMENT_DEPLOYMENTS` -- which
  was `MAXIMUM_ONE_DOCUMENT_DEPLOYMENTS = 1` when this paragraph was written, *"no
  headroom, on purpose ... a second deployment claiming it cannot arrive without an edit
  here."* The citation is RE-POINTED and the superseded name kept beside it rather than
  the sentence rewritten. `cp-00` is the second claimant, with `s1-00`. **THE ORCHESTRATOR DISPUTES THE
  EXECUTOR'S FRAMING OF THE PRECEDENT.** The executor cited `D-IMPL-146` (*"do NOT raise the
  ceiling"*) as if it were a standing prohibition. It is not: in `146` Dave refused to raise
  because **the DETECTOR was wrong** -- a second deployment had arrived by a code shape the
  detector did not recognise, and the fix was to teach it and SPLIT the exemptions, which is
  why `MAXIMUM_SDK_SUPPLIED_DEPLOYMENTS` exists as a separate constant today. **Here the
  detector is RIGHT**, and the proof is that the second failing assertion is a **ROSTER, not
  a count** -- it names `['examples/cp-00-institutional-holders',
  'examples/s1-00-companies-over-revenue']` -- and `cp-00` takes the SAME route as `s1-00`
  with no SDK-supplied variant anywhere in its tree. No third route to split off, no
  detector bug. **OPTION 1 (orchestrator's recommendation): raise to 2 and NAME `cp-00` in
  the commit message**, which is what the constant's own comment instructs; touches `tests/`
  only so criterion 16 stays intact. **OPTION 2: give `cp-00` a second Control Plane
  document**, which undoes the *"whole Control Plane in one document"* teaching point `D-51`
  ruled, and is a BUILD in a phase whose posture is that it builds nothing.
  **`D-64` IS DISCHARGED IN HALVES, AND THE MEASURED HALF CONTRADICTS THE SPEC'S OWN
  DECLARED ENVELOPE.** 40 calls against the live estate; instrument NAMED beside the numbers
  as Dave required -- 40 calls and why not 20 or 60, `perf_counter_ns` (monotonic, with a
  250 ms control per population), nearest-rank percentiles, and a call bounded as ONE
  `assemble` INCLUDING the DB connect and the fabric boot, EXCLUDING process start and the
  spec print. **p50 10.1 s, p95 11.8 s -- 11.8x the 1,000 ms p95 envelope the spec declares
  for itself.** ATTRIBUTED rather than merely reported: step 1, the database read, is
  **101 ms against its 120 ms budget -- that budget HOLDS**; step 2, writing 1,748 rows
  through the fabric's single writer, is **9,896 ms against 380 ms**. The spec already said
  step 2 dominates and already named the remedy (materialize per issuer-and-quarter); it was
  right in KIND and wrong by **16x** in SIZE, so its remedy is now evidence-backed rather
  than asserted. Control: serving **83x** more rows costs **5%** more time, which puts the
  cost in the WRITE and not in the projection. **COST IS LEFT OPEN WITH AN OWNER AND NO
  DOLLAR FIGURE WAS INVENTED**, exactly as `D-64` requires. What WAS measured: zero model
  tokens per call (structural, gated) and 2.93 CPU-seconds, against a meter control reading
  300.0 ms for a spin and 0.1 ms for a sleep.
  **`D-65` GAINS A CLAUSE FROM THIS WAVE'S OWN MACHINERY -- ELEVENTH CONSECUTIVE WAVE.** The
  first criteria check produced a **FALSE STOP** on a block that had not changed by a byte
  (a detector rebuilt from prose instead of running the bound one, plus a stray newline
  strip) -- and **the positive control beside it AGREED WITH WAVE 1 EXACTLY**, which read as
  proof the reader was correct. It was not: that control is built in a way that DISCARDS THE
  VERY BYTE the measurement turns on, so it returns the same answer whether the reader is
  right or wrong. **A positive control must be able to SEE the thing the measurement depends
  on, or its agreement is worth nothing** -- a control that cannot discriminate is not a weak
  control, it is a second broken instrument agreeing with the first. PRIOR:
  2026-08-27 -- **PHASE 24.1 WAVE 9 COMPLETE. THE PRESSURE TEST HAS ITS RECORD AND THE
  TREE IS FULLY GREEN AGAIN.** `24.1-PRESSURE-TEST.md` written (§§1-6), the three
  inherited ledger rows re-pointed in BOTH channels, the named non-goals probed, and
  `D-IMPL-212` appended OPEN. **THE LAST DELIBERATE RED SIGNAL IS CLOSED:**
  `tools.lints --all` **rc=1 with exactly 2 `cite03-node-id` findings -> rc=0 with none**,
  measured unpiped at both ends and read by finding NAME rather than exit code; the
  orchestrator re-ran it independently and got **rc=0**. Both citations sat at
  `.planning/REQUIREMENTS.md:36` and `:330`, both meant the spine-separation gate's glob,
  and both now cite `tests/examples/test_spine_separation.py::SPINE_GLOBS`. **The
  blind-replace trap was avoided**: `SECTION_ONE_GLOB` still EXISTS, in a different file
  (`tests/examples/test_section_one_is_agent_free.py::SECTION_ONE_GLOB`), so a mechanical
  substitution would have
  produced two citations that RESOLVE and are WRONG. Control: a fabricated symbol seeded
  into a `.planning/` file drove both `--citations` and `--all` to rc=1 naming it, and
  removing it returned rc=0.
  **THE VERDICT: THE DERIVATION HELD. NO DRIFT (`D-05`).** Six of the Standard's eight
  operator names carry SDK mechanism at a named layer; **`Enrich` is genuinely absent** and
  `Evaluate` exists only as Π -- which AGREES with the published page `D-63` accepted, and
  the two must not drift apart. **`cp-00` needed ZERO new SDK operators.** `src/` and
  `runtime/` are diff-empty against `phase-24.1-base` (142 and 71 tracked files), measured
  after `git rev-parse --verify` returned rc 0 -- with an unresolvable-ref control showing
  rc 128 AND EMPTY OUTPUT that a `test -z` check would have silently accepted.
  **THE REGISTER, SPLIT: FOUR SDK-SIDE — all seam ergonomics, none algebra — and THREE
  TOOLING, which `D-05` does not read.**
  **WAVE 9 CORRECTED AN ERROR IN THIS FILE THAT WAS THE ORCHESTRATOR'S, NOT AN
  EXECUTOR'S.** The Session Continuity resume block written at the top of this session
  named the fourth SDK-side member as *"the CI `run.py` gate finding now discharged by
  `D-51`"*. That finding was DISCHARGED and was never SDK-surface: the real fourth is
  Wave 3's **empty-operator gate is two different assertions sharing one name** (spec §F.4
  item 4). The COUNT of four was right; the MEMBER was wrong, which is the more dangerous
  shape because the total audits clean. Corrected in place, with the superseded text named
  rather than deleted.
  **TENTH CONSECUTIVE WAVE TO FIND A DEFECT INSIDE ITS OWN MACHINERY**, and this one is a
  counting instrument that CANNOT FIRE: both candidate-gap reproduction commands published
  in `24.1-RESEARCH.md` return **0 hits**, because they escape `-E` alternation as `\|`,
  which matches a LITERAL PIPE. Corrected forms return **9** and **4**. A later reader
  re-running the published form would have read absence as confirmation from an instrument
  that never fired -- the same shape as Wave 6's rc=0 lint control.
  **`D-IMPL-212` IS APPENDED AT 212, NOT 203**, against the plan's own `<done>` line: 202-211
  are RESERVED candidates and 203 is already *"Closed operator vocabulary vs four canonical
  categories"* -- this record's own subject. PRIOR:
  2026-08-27 -- **PHASE 24.1 WAVE 8 COMPLETE AND ITS BLOCKING HUMAN GATE IS DISCHARGED
  (`D-63`, Dave).** Both `D-28` documents shipped: `examples/cp-00-institutional-holders/
  README.md` (419 lines, the seven template headings, the MECHANICS) and
  `public/concepts/the-first-context-product.md` (263 lines, six `--8<--` includes and
  ZERO transcribed code, the ARGUMENT). `docs-strict` **0/0/0/0 on all four steps**, each
  run as its own foreground command with the exit code read unpiped, and `make -n
  docs-strict` printed first to prove those four ARE the whole recipe. Wave 7's deliberate
  README red is CLOSED: `test_cp_readme_template.py` **4 failed -> 10 passed**;
  `tests/examples` **532/4/38 -> 537 passed / 0 failed / 37 skipped**, collected 574 both
  times, and 532 + 4 + 1 = 537 reconciles exactly (the skipped empty-parameter case became
  a real test -- that arithmetic is the control, and the dispatch's expected 536 was wrong).
  **THE HUMAN HALF WAS CARRIED TO DAVE RATHER THAN DEFERRED.** He was remote and could not
  run the example, open the files or run `mkdocs serve`. The orchestrator ran
  `make example-cp-00` against the LIVE estate itself, rendered both documents, pulled the
  published page out of the STRICT BUILD'S OWN OUTPUT so every excerpt on it arrived by
  include, and set `produce.py` beside `deployment.py` **UNLABELLED** -- the plan asks
  whether the boundary is legible *without being told*, so labelling the panes would have
  destroyed the test. Ruling: *"Love the docs and the html page. Accepted."*
  **ALL FOUR FLAGGED READINGS STAND**, and one of them is a PUBLISHED POSITIONING CLAIM
  rather than a style call: the Standard->SDK operator mapping stays **MEASURED** against
  the plan's wording, so a public page now states that **`Enrich` has no SDK expression** --
  three map 1:1, three land elsewhere, `Evaluate` exists only as Pi. Surfaced to Dave AS a
  positioning call before he accepted.
  **THE FIFTH FLAGGED ITEM WAS SETTLED BY MEASUREMENT, NOT BY RULING.** The README quotes
  `D_c ~= 0.56 at 148 days` from `ccf_config.yaml`'s written-out arithmetic, because the
  executor had no DSN and correctly refused to present arithmetic as observation. The
  orchestrator ran it: **`D_c` = 0.5582**, `F` = 0.4729, at exactly 148 days
  (`report_period` 2026-03-31 -> 2026-08-26). **21 holders served against 21 from an
  independent SELECT**, with a control at `MIN_POSITION=500000000` returning **39**. The
  figure is CONFIRMED rather than accepted.
  **A SEVENTH FINDING, AND IT IS TOOLING FOR THE THIRD WAVE RUNNING** (`D-04`, recorded,
  NOT closed, deliberately OUTSIDE `D-05`'s drift list): **nothing that ships gates
  criterion 9's four dataset statements** -- `grep -rl 'fact about any real company' tools/
  tests/` returns **0 files**, against controls of **3** files where the statements live and
  **53** for the No-Hardcoding Rule, so the search works. The executor's guard ran at wave
  time and was NOT committed; its shape is written into `deferred-items.md` to be rebuilt.
  **THE SDK-SIDE COUNT IS STILL FOUR** -- Waves 6, 7 and 8 each found a TOOLING defect, and
  conflating the two lists would manufacture a `D-05` drift verdict out of three lint gaps.
  **ONE ORCHESTRATOR NEAR-MISS, RECORDED BECAUSE IT WOULD HAVE BROKEN THIS WAVE'S OWN GATE:**
  the review page was first written to `public/_review/` -- inside the published surface,
  which is default-deny-by-existence, where an unregistered file fails `mkdocs build
  --strict` on `validation.nav.omitted_files`. Caught before commit, moved to the session
  scratchpad, and `docs-strict` steps 1 and 3 re-run to **exit 0** on the moved tree.
  Nothing under `public/` changed. PRIOR:
  2026-08-27 -- **PHASE 24.1 WAVE 7 COMPLETE. THREE GATES ARMED, ONE REFUSED IN
  WRITING, AND A DELIBERATE RED WINDOW IS OPEN.** `tests/examples` **508 -> 532
  passed**, 4 failed, 38 skipped -- orchestrator re-ran the whole module in the
  FOREGROUND and got 532 exactly, matching the executor's claim. **THE 4 FAILURES ARE
  DELIBERATE AND WAVE 8 CLOSES THEM**: `test_cp_readme_template.py` was written with a
  LIVE subject and no stub, so it is RED until `cp-00` has a README. **`tools.lints
  --all` IS ALSO DELIBERATELY RED -- rc=1, EXACTLY 2 findings**, both `DOCS-11` ledger
  channels (`.planning/REQUIREMENTS.md:36` and `:330`) citing the renamed
  `::SECTION_ONE_GLOB`; the constant is now
  `tests/examples/test_spine_separation.py::SPINE_GLOBS` and **plan 24.1-09 Task 2
  closes it** -- verified by the orchestrator against 24.1-09-PLAN.md, which names
  `DOCS-11` and the stale citation explicitly. **`make ci` IS THEREFORE RED BETWEEN
  WAVES 7 AND 9 BY DESIGN, WITH BOTH CLOSERS NAMED. THIS IS NOT A BROKEN TREE.**
  Criterion 19 requires it green at the GATE commit, which is Wave 10's obligation.
  **CRITERION 15 IS DISCHARGED THE HARD WAY.** The control's first draft went red for
  the WRONG REASON -- `NameError: SPINE_GLOBS is not defined` -- which is precisely the
  failure the criterion exists to catch, so it was restaged: rename the glob to
  `("s1-*",)`, watch the ASSERTION fail naming the tree it does not reach, then add
  `"cp-*"` as the ONLY edit between red and green. The control rediscovers a
  marker-stripped copy THROUGH `split_examples` rather than handing it to the
  predicate, so it proves glob -> discovery -> refusal end to end.
  **`D-24` IS DISCHARGED WITH TEETH RATHER THAN PROSE.** Beyond a docstring section and
  a comment on the constant, `test_widening_this_glob_to_cp_would_break_the_example`
  runs the REAL predicate over the `cp-*` tree and asserts it DOES refuse -- 2 of 4
  modules on `ccf.agents`, against 0 of 9 for `s1-*`. The glob was actually widened and
  watched producing 8 failures naming `assembler.py` and `run.py`. If `cp-00` ever
  stops importing `ccf.agents`, that test fails and tells the reader to RE-DECIDE
  rather than delete it.
  **A SIXTH RECORDED FINDING, AND LIKE THE FIFTH IT IS TOOLING, NOT THE SDK'S SURFACE**
  (`D-04`, recorded in `deferred-items.md`, NOT closed): nothing shipped checks any
  EXAMPLE for an LLM-client import -- a planted `import anthropic` in `examples/` draws
  ZERO findings from `tools.lints --all`. It nearly produced a false reading the other
  way: `--all` is rc=1 right now for the unrelated citation window, so the EXIT CODE
  proves nothing there and only the finding-NAME count does. 18 modules across four
  live example trees stay unchecked; reaching them would be a RETROFIT, which `D-07`
  forbids. Control: the same planted import inside `examples/cp-00-institutional-
  holders` gives 6 failed / 6 passed, while `examples/s1-01-hello-context-product`
  leaves the gate at 12 passed -- so the instrument detects coverage where it exists.
  **`split_examples(...)[0]` REALLY DID DRIFT** from `s1-00` to `cp-00` (alphabetical),
  breaking a CORRECT control that needs `scenario/provision.py`, which only `s1-00`
  ships. Repointed BY NAME; the control that the repoint was necessary is that
  reverting it fails naming the missing file. **15 SABOTAGES, ALL WATCHED RED**, each
  with a DISTINCT named failure rather than general redness. The executor also
  self-corrected two of its own instruments: a baseline read from `/tmp` reported 17
  and 8 because both modules resolve `REPO_ROOT` from `__file__` and the copies sat at
  the wrong depth (real values 22 and 16, after which the suite delta reconciles
  exactly), and one sabotage produced a collection error from a syntax slip rather than
  a measurement. **NINTH CONSECUTIVE WAVE TO FIND ITS OWN DEFECT CLASS INSIDE ITS OWN
  MACHINERY.** PRIOR:
  2026-08-27 -- **PHASE 24.1 WAVE 6 COMPLETE. THE EXAMPLE HAS A COMMAND AND CI HAS
  SOMETHING IT CAN HONESTLY ASSERT.** `make example-cp-00` is `.PHONY`, carries a help
  line, and is deliberately NOT a prerequisite of the always-on `examples:` aggregate
  (`D-08` precedent: a networked substrate puts an example outside it). Against the LIVE
  estate it serves **21** holders at the demonstration threshold and **39** at
  `MIN_POSITION=500000000` -- two different content addresses, and the 21 equals Wave 1's
  independent SELECT sweep by a different route. The CI leg is a `pytest.mark.postgres`
  module that stands up `postgres:16` ITSELF and seeds it from
  `tests/examples/fixtures/cp_00_13f_schema.sql` + `cp_00_13f_rows.sql` -- **`D-27`: the
  fixture is SEEDED BY THE TEST, never committed as a database.** `tests/examples`
  **485 -> 508 passed**, skips unmoved at 37, and 508 - 485 = **23** is exactly the two
  new modules' collected count (orchestrator re-measured independently: 23 for both
  modules, **14** for one alone -- the control that makes 23 a measurement rather than a
  coincidence). **ELEVEN SABOTAGES, ALL WATCHED RED**, two of them unplanned and the more
  valuable for it: a band filter seeded into the oracle reproduces `D-61`'s under-count
  signature (14 -> 11), and nudging the exactly-at-threshold value one unit makes §F
  marker 14's gate untestable in precisely the way that marker warned.
  **`D-62` IS DISCHARGED** -- §E.2's debt bands stop reading `[TBC]`, §D.2 step 1's
  prose cell no longer claims "no SDK symbol", and §F markers 13, 14 and 16 are CLOSED,
  each keeping its row so the sentence that raised it still points somewhere.
  **A FIFTH RECORDED FINDING, and it is in the TOOLING rather than on the SDK's own
  surface** (`D-04`, `D-56` -- classified, NOT closed): the plan asserted
  `tools/lints/no_hardcoding.py` would refuse a threshold-plus-LEI dict in `tests/`, and
  the executor's FIRST control returned rc=0 -- a passing report from an instrument that
  never fired. Measured rather than concluded: `RULE_TREE_SCOPE` does include `tests`, so
  the SCOPE claim is right, but `_is_numeric_table` requires a strict numeric MAJORITY,
  so a 2-entry dict pairing an int with a string is 1-of-2 and never trips; a 3-entry
  numeric table returns rc=1. **This is the eighth consecutive wave to find its own
  defect class inside its own machinery.**
  **TWO RESIDUES DELIBERATELY LEFT OPEN, NAMED RATHER THAN GUESSED:** §E's surviving
  `[TBC]` is marker 4, the issuer-identity refresh cadence -- the archive publishes none,
  its owner is the SOURCE-ESTATE owner and not any wave of this phase, and guessing it is
  the §0.2 defect the document rates worse than an honest gap; and **§F marker 15, the
  MEASURED p50/p95 latency and per-call cost**, which §F.2 assigns to *"the wave that
  runs the assembly"* -- Waves 5 and 6 both ran it and NOBODY HAS MEASURED A LATENCY.
  §G's Lifecycle row now names marker 15 as the one certification evidence still owed.
  **`cp-00` IS GREEN, WHICH IS THE CONDITION `D-58` ATTACHES TO THE SHORT SDK PHASE** for
  `D-59`/`D-60` (assembler-refusal-as-data + deployment operator registration). That
  phase is now SCHEDULABLE and is still NOT 24.1's to run (`D-04`). One orchestrator
  correction: the summary's frontmatter claimed a `~4 h` duration; actual dispatch-to-
  return was 2,224,352 ms = **37.1 min**, corrected at `f83bd0a`. PRIOR:
  2026-08-26 -- **PHASE 24.1 WAVE 5 COMPLETE. THE EXAMPLE RUNS END TO END AND THE RED
  `make ci` GATE IS GREEN.** `deployment.py`, `assembler.py` and `run.py`. The three
  numbers Wave 4 computed by hand BEFORE this code existed are the three the run
  produces -- F 0.4729, C 0.9342, D_c 0.5582 -- and the served count at the
  demonstration threshold is 21, equal to Wave 1's independent SELECT sweep by a
  different route. `test_artifact_schema_headers.py` **1 failed/29 passed -> 30
  passed**; `tests/examples` **484+1F -> 485 passed**. `D-51` discharged: the printed
  entry point is `run.py`, the gate was NOT widened and `artifacts/` NOT renamed.
  `D-47`/`D-48` discharged: step 1 is an EXAMPLE-SUPPLIED `Operator`, category
  `traversal`, registered and resolved back out of an `OperatorRegistry`, returning the
  winner's SUBGRAPH -- no scalar, no new category, nothing in `src/`. The example is the
  first ever to implement `ccf.agents.assembler::ContextAssemblerProtocol`.
  **TWO MORE SDK-SIDE FINDINGS, both RECORDED and NOT CLOSED (`D-04`)**, taking the
  phase's running total to FOUR: (1) `build_operator_registry` dispatches on artifact
  TYPE and raises for anything it does not recognise, so a deployment's own operator has
  no path into the registry the projection plan resolves against -- the registry is open,
  the composition path in front of it is not (use-case agnostic, a remedy would be
  ADDITIVE); (2) `ContextAssemblerProtocol.assemble` is typed to return `AssemblyOutcome`
  and nothing else -- 7 fields, `extra=forbid` -- so a conforming assembler receiving a
  governed `ProductRequestViolation` can only RAISE, in a codebase whose stated posture
  is that a refusal is DATA (a remedy is NOT additive). **FOUR DEVIATIONS, all reported:**
  the `run.py` name (`D-51`, and plans 06/07/08/11 still say `consume.py` and are owed the
  rename); `artifacts/assembly-recipe.yaml` step 1's mechanism column corrected from
  `none`, which `D-47` does not allow and no later plan owns; the plan's
  `issuer_match_band` filter clause REJECTED, because the spec, the probe and
  `expected.yaml` all rule NO band filter and one would have been a silent 6.6%
  under-count; and two forced arguments on `envelopes`. **FOUR SPEC RESIDUES nobody
  owns**, including `D-52`'s -- §E.2 still reads `[TBC]` for the bands -- and §F marker
  13, which this wave MEASURED at C_attributes = 1748/1748 = 1. 40 measurements, each
  with a control. PRIOR:
  2026-08-26 -- **PHASE 24.1 WAVE 4 COMPLETE.** The fabric half of
  `examples/cp-00-institutional-holders`: `ccf_config.yaml` (the whole Control Plane in
  one document, booting against the real loader with three seeded controls refused),
  `backends.yaml` (a variable NAME plus a remedy, and a per-run path recipe -- no host,
  port, path or credential, against a seeded sweep control that returns 1),
  `artifacts/ttl.yaml`, `artifacts/question.yaml`, `artifacts/expected.yaml`, and
  `produce.py` -- seven ordered marker regions, closed, no eighth, silent, importing
  clean, naming no table, column, entity, artifact key, substrate, parameter name or
  number. `python -m tools.lints --all` **rc=0**, against a seeded fabricated symbol
  that returns rc=1. `src`/`runtime` diff-EMPTY per member vs `phase-24.1-base`,
  each proven NON-EMPTY under a seeded line. Nineteen criteria, contiguous, zero
  continuation lines, against a scoped deletion control returning 18 missing=[12].
  TWO deviations, both reported: a SIXTH artifact (`ttl.yaml`) because the SDK has no
  slot for the TTL ceiling's value, and a `gated` field on `Assembled` so the
  assembly-recipe's step-6 witness can reach its subject. PRIOR:
  2026-08-25 -- **PHASE 23.1 IS CLOSED. `D-GATE-23.1` IS LOGGED AND v0.2 IS DISPOSITIONED.**
  Eight plans in eight serial waves, 31 commits from `PHASE_BASE` `cb6a744`, merged to
  `main --no-ff` naming the entry. **All NINETEEN Success Criteria met** and all nineteen
  byte-identical to the phase base by sha256 -- execution authored, edited, renumbered and
  re-wrapped NOTHING. **THE PHASE BUILT NOTHING**: `src`/`runtime`/`examples` diff-empty per
  member, `tests/` byte-identical, `archive/examples/` still 265 with D and R filters empty.
  **13 open rows -> 11**: 2 Discharged, 10 Deferred to v0.3, 1 Dropped. All 27 packet items
  dispositioned. `D-IMPL-199`/`200`/`201` logged. **`complete-milestone` IS BLOCKED FOR A
  STRUCTURAL REASON, NOT A FAILURE** -- tooling and ledger disagree on "done": dispositioned
  rows still read open to `audit-open` (14) and the requirements check (136/149) while
  `roadmap.analyze` reports 100%. Dave acknowledged the 14 at close. **DELETION STAYS OWED**
  with no target date. PRIOR: 2026-08-25/26 -- **PHASE 23.1 IS EXECUTED AND STOPPED AT ITS GATE, AWAITING DAVE'S
  RULING. `D-GATE-23.1` IS NOT WRITTEN, `phase-23.1` IS NOT MERGED AND NOT PUSHED, and
  `complete-milestone` HAS NOT RUN.** Eight plans in eight serial waves on branch
  `phase-23.1` from `PHASE_BASE` `cb6a744`. All thirteen open requirement rows carry a
  disposition; all 27 human-verification packet items carry a final disposition; the
  `D-27` keep-quarantined ruling is logged as `D-IMPL-201`; ten decision candidates are
  renumbered to `202`-`211`; Phase 23's criterion 15 carries `D-GATE-23`'s
  chunked-foreground reading as an explicitly marked amendment.
  **DAVE'S FOUR RULINGS OF 2026-08-25 ARE APPLIED (plan `23.1-08`).** (1) `DOCS-18` and
  `DCD-02` -- verdict `Partial` beside disposition `Discharged` -- flipped to `Complete`
  in BOTH channels with both boxes ticked; **the open-row count MEASURED at 11**, down
  from 13, with two positive controls returning 12 and naming the injected row.
  (2) The **14** `audit-open` items are **ACKNOWLEDGED AT CLOSE, BY NAME** -- 4 UAT gaps
  (Phases 11, 13, 14, 15.3) and 10 verification gaps (11, 13, 14, 15.1, 15.2, 15.3,
  15.4, 18, 18.1, 19) -- **with the structural reason RECORDED rather than papered
  over: the tooling and the ledger disagree about what "done" means.** Dispositioned
  rows still look OPEN to `audit-open` (which reads each record's frontmatter `status:`)
  and to the requirements check (which counts unticked boxes), while `roadmap.analyze`
  reads DISK and reports **100 percent**. Three channels, three answers. Phase 23.1
  **deliberately did not rewrite nine closed phases' frontmatter to satisfy a counter**.
  `complete-milestone` does NOT run inside this phase (criterion 18's name-the-reason
  branch) and there is **NO silent force-complete**. (3) `D-IMPL-144` migrate-when-
  touched: the `:235` and `:356` anchors rode through the `DOCS-17` and `DOCS-18` lines
  this phase rewrote -- **measured as FOUR occurrences, not two**, because the ledger
  carries each row in two channels -- all four migrated, **residual RECORDED at 38 ->
  34 rather than the set claimed done** (Dave's stated 36 assumed one occurrence per
  anchor; the difference is named, not made to agree). (4) The plan counter re-measured
  from the tree and hand-corrected, never incremented -- see `progress.measured`.
  **THE CLOSE-TIME CROSS-AI PANEL RAN AGAINST THE SHIPPED TREE WITH THE SOURCE INLINED**
  (`23.1-CLOSE-REVIEWS.md`): codex, cursor and gemini, each PROVEN to have read by
  resolving its own citations against the files on disk against a negative control --
  7/7, 8/8 and 6/6. **Three blocking findings, all fixed IN-PHASE**; eight advisory; two
  gemini prose claims REJECTED as fabrications with the refuting commands recorded. The
  additive single-agent depth pass ran separately and found the verdict/disposition
  coherence class NOWHERE ELSE in the 149 rows. `make ci` re-run in full, chunked and
  FOREGROUND, ten legs all exit 0. **ONE LINE OF SHIPPED CODE CHANGED and it is named
  for Dave**: `CONTROL 9b`'s expected verdict constant in
  `tools/docs_tests/test_requirement_ledger.py`, which pinned `DCD-02`'s verdict to
  `Partial` and which ruling 1 moved. PRIOR: 2026-08-25 -- **PHASE 23.1 AND PHASE 24 ARE ON THE ROADMAP. NOTHING IS IN FLIGHT.**
  Dave supplied the Phase 24 requirements (Context Production) and RULED THE SEQUENCING:
  **the v0.2 close-out runs BEFORE Phase 24**, which is why it is numbered `23.1` and not
  `25`. Phase 23.1 carries **NINETEEN** Success Criteria, LOCKED in the ROADMAP entry
  before planning per `D-GATE-19`; it BUILDS NOTHING. Phase 24 carries **NO criteria and
  that is deliberate** -- `D-GATE-19` locks them at the discuss sitting, which follows
  `D-GATE-23.1`. **TWO SDK-SURFACE IMPACTS FOUND AND RAISED TO DAVE, BOTH UNRULED**: the
  Context Product Specification Standard's closed EIGHT-operator vocabulary against the
  SDK's FOUR categories (`src/ccf/operators/categories.py`), and its SIX universal
  validation gates against the SDK's THREE where `D-IMPL-102` limb 3 has ALREADY RULED
  that no fourth joins `run_gates`. One apparent impact CHECKED AND REJECTED: nine-vs-eight
  contract elements is already resolved by `D-IMPL-30` in favour of NINE and `AssemblyMode`
  ships. The other eight candidates in `CCF_SDK_DE_REQUIREMENTS.md` are NOT VERIFIED and
  must not be quoted as findings; all ten collide with logged ids (log at `D-IMPL-198`,
  `199` is the next free). **THAT ANCHOR IS WITHDRAWN AS STALE (`e75a1f3`) AND CORRECTED
  IN PLACE, superseded value named rather than overwritten (`D-19`, `D-IMPL-174`):**
  Phase 23.1 has since consumed `199` (`D-IMPL-199`), `200` (`D-IMPL-200`) and `201`
  (`D-IMPL-201`), so the next free id is **`202`**, and `23.1-06` renumbered the ten
  candidates to **`202`-`211`** on Dave's ruling. **The collision claim itself STANDS** --
  all ten proposed ids `D-IMPL-30`..`D-IMPL-39` were taken; only the next-free anchor moved. Dave lifted the do-not-query-the-vault constraint for the
  Context Product rollout. PRIOR: 2026-08-25 -- **PHASE 23 IS CLOSED. `D-GATE-23` IS LOGGED AND THE ARCHIVE MOVE IS DONE.**
  Thirteen plans in thirteen serial waves on branch `phase-23`, **76 commits** from
  `PHASE_BASE` `b87fe58`, merged to `main --no-ff` naming the entry. **All EIGHTEEN
  Success Criteria met**, locked before Wave 1 per `D-GATE-19` and amended ONLY by ruling --
  `D-IMPL-192`/`194` pre-planning, `D-IMPL-196`/`197`/`198` at the mid-phase checkpoint.
  Sixteen criteria byte-identical to the phase base, proven per criterion by sha256; 7 and 12
  differ at exactly the two ruled amendments. **NOT ONE CRITERION LINE WAS AUTHORED, EDITED,
  RENUMBERED OR RE-WRAPPED BY EXECUTION.**
  **265 FILES AT `archive/examples/`, 58 LEFT UNDER `examples/`, AND NOTHING DELETED** --
  proven a pure rename set in the STRONG form (265 `R100`, 0 D/A/M, 0 insertions and 0
  deletions). The weaker `R=265 D=0 M=0` form was REJECTED in-phase because
  `--diff-filter=M` cannot fire on a renamed path and so passes on a file that moved AND was
  edited. 111 published references re-pointed across 15 pages (102 includes + 9 prose paths),
  proven a pure prefix substitution by REVERSING it to byte-identical. Fourteen make targets
  deleted with their `.PHONY` names and the two `live-legs.yml` jobs that invoked them.
  `DOCS-17` verdicted **`Partial`** in both channels in the wording `D-IMPL-191` ruling 4
  constrained it to -- *out of the `examples:` aggregate*, NOT *out of live CI* -- written in
  the archive phase when the state existed on the tree and not before (`D-IMPL-189` point 4).
  **THE SS3.1 CLOSE FOUND THREE BLOCKING DEFECTS AND ALL THREE ARE FIXED IN-PHASE**, each
  re-sabotaged after the fix. **`B1` IS A LOCKED CRITERION THAT WAS NEVER ACTUALLY
  DISCHARGED.** Criterion 10 reads *"suppressing an archived path's coupling row is watched
  RED, so the sweep cannot go blind to the archive"* -- and against the shipped control that
  was FALSE. `archive_sweep_problems` ASSERTED a row-count floor while only DOCUMENTING
  per-tree coverage in its docstring. Measured: suppressing **every one of the 21 rows** for
  `archive/examples/03-harness-portability` left 110 rows against a floor of 10 and the
  predicate returned EMPTY -- green over a tree it did not look at. **Nine of ten trees could
  have gone dark silently.** The phase's own defect class, a tool that reports clean because
  it did not look, arriving INSIDE the control written to prevent it -- the same shape
  `D-GATE-22.1`'s panel found one phase earlier. Fixed at `d6cbca7`: per-tree assertion, count
  floor KEPT for its different diagnosis, two new controls watched RED before green, and
  counter-sabotage in the other direction proving both clauses independently load-bearing.
  **The orchestrator verified it independently rather than reading the report** -- neutering
  the per-tree clause turns exactly 2 controls red while the count floor stays green.
  `B2`: a live ledger cell claimed the adopter's guide teaches six `make` commands this phase
  deleted; zero of the six survive. `B3`: three corrections a prior wave EXPLICITLY ASSIGNED
  to the close had never been made -- the ROADMAP goal prose still carried the clause
  `D-IMPL-191` ruling 4 forbids, and this file's Position block still said *"SIXTEEN criteria"*
  and *"25 of 31"* after both were amended. **NOTHING GATED ANY OF THE THREE, WHICH IS HOW THEY
  WENT TWO RULINGS STALE WITHOUT A RED.**
  **THE PANEL READ THE SHIPPED TREE AND ITS FAILURES ARE RECORDED AS FAILURES.** codex, cursor
  and gemini (`claude` excluded), source INLINED, briefed on the known findings and asked for
  what is ADJACENT. Every symbol each reviewer cited was checked against the tree before it was
  counted as a review. Eleven findings: 3 blocking fixed, 3 advisory fixed, 4 advisory carried,
  **4 REJECTED with refuting evidence**. **TWO OF THE FOUR REJECTIONS WERE THE EXECUTOR'S OWN
  PAYLOAD OMISSION AND ARE RECORDED AS SUCH, NOT AS REVIEWER ERROR** -- the file carrying the
  guard was left out, so both reviewers correctly concluded from what they were given that it
  was missing. codex `F-1` and cursor `F-1`/`F-3` converged INDEPENDENTLY on `B1`.
  **A DEFECT THE PHASE'S OWN WAVES MISSED AND THE CLOSE CAUGHT: `make ci` WAS RED FROM WAVE 10
  TO WAVE 12 AND TWO WAVES REPORTED GREEN.**
  `tests/invariants/test_citation_coverage.py::test_the_unanchored_python_citation_population_cannot_regrow`
  failed on a `path.py:LINE` citation Wave 10 wrote into its own `deferred-items.md`, against
  `D-IMPL-123`'s ceiling of zero. Waves 10 and 11 ran `tools/docs_tests`, `gate-tools` and
  targeted modules and ran NEITHER `tests/invariants` NOR `make ci`; **the orchestrator
  repeated the error and reported a clean tree to Dave on the same partial measurement, and
  corrected it on the record.** Fixed by CONVERSION to `path.py::symbol` form (`D-IMPL-114`),
  never by raising the ceiling -- the Phase 21.1 wave 9 precedent.
  **DAVE BLESSED THE CHUNKED FOREGROUND FORM OF `make ci` as an allowed satisfaction of
  criterion 15 on this host**, under four conditions all met here: `make -n ci` proves the
  chunk list IS the full recipe; every constituent command runs in the FOREGROUND with its
  exit code recorded; the deviation is NAMED in the gate entry; and criterion 15's existing
  coverage proof is discharged (1007+1056+986+1184 = 4233, both set-equality directions empty,
  all six pairwise intersections zero). Expressly NOT allowed: backgrounding the whole pipeline
  and treating a kill as unknown-or-pass, claiming *"make ci green"* without naming the
  chunking, and silent substitution. Dave's intent, recorded verbatim so the next phase does
  not re-litigate it: *"criterion 15 forbids UNOBSERVED full runs (background kill ~= pass). It
  does not require a single process if the machine cannot hold a 14.5-minute foreground job."*
  **A FOLLOW-UP UPDATING CRITERION 15's TEXT IS OWED AND IS NOT DISCHARGED**; until it lands,
  `D-GATE-23` is the governing statement.
  **GATES AT THE GATE COMMIT**, six legs exit 0, each FOREGROUND with its exit code read
  without a pipe: `test` **4115 passed / 118 skipped / 0 failed**; `gate-tools` **415 + 339**;
  `docs-strict` 0 across four steps; `examples` running exactly one target; `lint` 0. Full
  collection **4233**. Criterion 7 discharged as the ACCOUNTED DELTA (`D-IMPL-196`, amended by
  `D-IMPL-198` ruling 1): 4223 -> 4233 with **LOST-UNRECOVERED ZERO** and ten additions each
  reconciled to the wave that named it; `tests/examples` 515 -> 521, lost-set empty; **gated on
  no literal at any point**. Criterion 14: **8 changed lines** across 3 files under `src/` +
  `runtime/`, four authorized edits both sides, `pyproject.toml` DIFF-EMPTY.
  **CARRIED BY DAVE'S RULING, EXPLICITLY NOT BLOCKING:** four advisory findings; deferred items
  7-10 with exact edits named, item 7 (no witness reads the RENDERED body a `--8<--` include
  pulls in; the durable fix is a third witness this repo does not have) now carried by six
  waves; the deletion half of `D-27`; the two `CLNT-17` framing questions, RAISED AND EXPRESSLY
  NOT RULED, `CLNT-17` content-hashed EQUAL at both ends and still `Not built`; and
  `DOCS-14`/`EXAM-02`'s replacement surface. **DELETION REMAINS OWED FOR EVERY SCHEDULED ROW**
  (`D-IMPL-191` ruling 3).
progress:
  total_phases: 37
  completed_phases: 34
  total_plans: 257
  completed_plans: 257
  percent: 92
  measured: "**RE-MEASURED AT THE PHASE 24.4 GATE, 2026-09-01, by hand, stated FIRST;
    everything below is PRESERVED HISTORY.** total_plans 257 = `*-PLAN.md` at depth 1 under
    `.planning/phases/*/` (control `*-PLANN.md` = 0); completed_plans 257 = those with a
    `*-SUMMARY.md` beside them. total_phases 36 = `### Phase` sections in ROADMAP.md;
    completed_phases 34 = `- [x] **Phase` checklist ticks, with 1 unticked and the checklist
    one entry SHORT of the sections (the four-places drift, known). percent left at 94 because
    the milestone's DOCS debt (`D-IMPL-176`) is unchanged, not because it was computed. **OPERATIVE RE-MEASURE AT THE PHASE 23.1 GATE, 2026-08-25/26 by
    plan `23.1-08`, stated FIRST and alone; everything below it is PRESERVED HISTORY.**
    RE-MEASURED FROM THE TREE, NOT INCREMENTED (Dave, 2026-08-25: *re-measure and
    hand-correct; do not increment*). **total_plans 225** = `*-PLAN.md` at depth 1 under
    `.planning/phases/*/`; **completed_plans 225** = those with a matching `*-SUMMARY.md`
    beside them. Positive controls beside the figures: `*-PLANN.md` returns **0** and
    `*-SUMMARYY.md` matches **0**, so a match is a match and not a glob that saw nothing;
    a known-present probe (`23.1-07-PLAN.md`) is matched and a known-absent probe
    (`23.1-99-PLAN.md`) is not. **UNMATCHED PLANS: NONE.** `23.1-08-SUMMARY.md` closes
    the last of the three that were in flight. **SUPERSEDED VALUE NAMED rather than
    overwritten silently (`D-19`, `D-IMPL-174`): completed_plans 222 -> 225.** The 222
    below was measured by `23.1-06` and was already stale by three then and by one at
    `23.1-07`, which measured 224; the figure written here is `23.1-08`'s own
    measurement with its own controls, NOT `23.1-07`'s figure plus one. Summary files
    re-measured with it: **245** at depth 1, **20** of them with no matching PLAN, which
    is still why `gsd-sdk query progress.bar` reports an impossible 245/225 -- it counts
    summaries against plans. Depth-2 plans still EXCLUDED and named: 14 under Phase 16
    `abandoned/` and 13 under Phase 15.2 `void-plans-pre-D-IMPL-87/`; every depth
    returns 252. **percent stays 93**: it is 28 of 30 PHASES, not 225 of 225 plans, and
    Phase 23.1 is NOT gated until Dave rules -- `gsd-sdk query roadmap.analyze` reports
    `completed_phases 29 / progress_percent 100` because it reads DISK and counts the
    phase now being closed as already complete, which is a THIRD channel disagreeing
    with this one and with the ROADMAP checklist's `- [ ] Phase 23.1`. That
    disagreement is criterion 18's subject and is named in `23.1-GATE-MEASUREMENTS.md`
    R-7 rather than resolved by moving a number here.
    **THE PARAGRAPH BELOW IS PRESERVED HISTORY FROM `23.1-06` AND ITS FIGURES ARE
    SUPERSEDED.**
    **OPERATIVE RE-MEASURE, 2026-08-25 by `23.1-06`, stated FIRST and alone
    because token presence is not token force -- everything below this paragraph is
    PRESERVED HISTORY and two of its sentences are WITHDRAWN in place.** Re-measured
    from the tree, NOT incremented (Dave, 2026-08-25: *re-measure and hand-correct; do
    not increment*). **total_plans 225** = `*-PLAN.md` files at depth 1 under
    `.planning/phases/*/`; **completed_plans 222** = those with a matching
    `*-SUMMARY.md` beside them. Positive controls recorded beside the figures: the
    misspelled suffix `*-PLANN.md` returns **0** and `*-SUMMARYY.md` matches **0**
    plans, so a match is a match and not a glob that saw nothing; a known-present
    probe (`23.1-05-PLAN.md`) is matched and a known-absent probe (`23.1-06-PLAN.md`)
    is unmatched. **The THREE unmatched plans are NAMED rather than rounded up, and
    all three are IN FLIGHT: `23.1-06`, `23.1-07`, `23.1-08`** -- this wave and the two
    after it, so completed_plans is EXPECTED to trail total_plans by exactly three
    until Phase 23.1 closes. **What the depth-1 rule deliberately EXCLUDES, named so
    the count is not read as a tree-wide total:** 27 further `*-PLAN.md` files sit one
    level deeper -- 14 under Phase 16 `abandoned/` (retired, `D-IMPL-152`, history and
    not a work queue) and 13 under Phase 15.2 `void-plans-pre-D-IMPL-87/`. Counting
    every depth returns 252. **SUPERSEDED VALUES NAMED rather than overwritten
    silently (`D-19`, `D-IMPL-174`): total_plans 217 -> 225, completed_plans 216 ->
    222.** `23.1-05` measured 225/221 the day before; the one-plan delta is
    `23.1-05-SUMMARY.md` itself, written after that measurement was taken. Summary
    files re-measured with it: **242** at depth 1 (was 236), **20** of them with no
    matching PLAN, which is still why `gsd-sdk query progress.bar` reports an
    impossible 242/225 -- it counts summaries against plans. **percent stays 93**: it
    is 28 of 30 PHASES, not 222 of 225 plans.
    **THE METHOD SENTENCE BELOW IS WITHDRAWN AND RE-MEASURED HERE (criterion 19).**
    It asserted `28 = ls -d .planning/phases/*/ and ### Phase sections in ROADMAP.md,
    which agree`. Those two channels **no longer agree and no longer read 28**:
    measured 2026-08-25, **30** `### Phase ` detail sections against **29** phase
    directories. The set comparison in both directions names the single genuine
    difference: **Phase 24 has a ROADMAP entry and no directory**, because it is
    banked and not planned -- and **no Phase 24 directory is manufactured to make the
    two channels agree**, which would be the same defect criterion 10 forbids one file
    over. One further difference is an INSTRUMENT artefact and is named so it is not
    read as a third phase: a naive string compare also reports `9` against `09`,
    because the Phase 9 directory is zero-padded and the heading is not; normalised,
    the delta is Phase 24 alone. Control: a fabricated phase number `99` appears in
    neither channel.
    ---- PRESERVED BELOW AS SUPERSEDED HISTORY, NOT DELETED ----
    2026-08-25 -- counted from the tree, not incremented. Superseded values,
    named rather than overwritten silently: total_phases 27, completed_phases 27,
    total_plans 204, completed_plans 204. Method **[WITHDRAWN 2026-08-25 -- see the
    OPERATIVE RE-MEASURE at the head of this block; the two channels no longer
    agree and no longer read 28]**: 28 = `ls -d .planning/phases/*/`
    and `### Phase ` sections in ROADMAP.md, which agree; 217 = `*-PLAN.md` files;
    216 = those with a matching `*-SUMMARY.md`. THE ONE EXCEPTION IS NAMED rather
    than rounded up: `22-06-PLAN.md`, Phase 22's CLOSE plan, has no SUMMARY -- the
    close work itself was done and `D-GATE-22` is logged, so the gap is the missing
    artifact, not missing work. **[EXCEPTION RETIRED 2026-08-25 -- `22-06-PLAN.md`
    NOW HAS A SUMMARY. The one exception this block named was CLOSED by Phase 23.1
    plan `23.1-05`, which wrote `22-06-SUMMARY.md` RETROACTIVELY from the Phase 22
    close record with its authorship stated in the file (ROADMAP criterion 10,
    Outcome A). The superseded wording is left above rather than deleted. The plan
    counter was NOT the reason for the write and is named as not the reason: the
    figures were 221 of 225 AFTER it, still short.]** There are also 236 SUMMARY files, 20 of them with no
    matching PLAN (`*-CLOSE-FIXES-`, `*-REVIEW-FIXES-`, `18-D-IMPL-149-`, `17-03b-`
    and similar), which is why `gsd-sdk query progress.bar` reports the impossible
    236/217 -- it counts summaries against plans. percent stays 100 because every
    PHASE is complete; it is not 216/217.
    SUPERSEDED 2026-08-25 by the ROADMAP additions: total_phases 28 -> **30** and percent
    100 -> **93** (28 of 30), because Phase 23.1 and Phase 24 are now entries and neither
    is complete. Re-measured with CORRECTED instruments and a sabotage control that goes
    RED: checklist / detail / progress = **30 / 30 / 30**, both set deltas empty in BOTH
    directions. TWO FALSE FINDINGS were produced and discarded on the way there, both from
    my own regexes reporting ABSENCE: one required a trailing period after a phase number
    (`| 15.5` has none) and one disallowed a `~~strikethrough~~` prefix (Phase 14.1's
    bullet is struck through as superseded). The first is the EXACT error recorded against
    a prior session and repeated here. Neither row nor bullet was ever missing."
stopped_at: >-
  Between phases. 24.4 closed and merged at d81d759; 24.5 banked at D-IMPL-235 with a ROADMAP entry, a phase
  directory and a .continue-here.md; nothing in flight. Resume with /gsd-discuss-phase 24.5. PRIOR FOLLOWS.
  **PHASE 24.4 IS CLOSED -- `D-GATE-24.4` APPROVED (Dave, 2026-09-01) and merged to `main`
  `--no-ff`.** Nothing is in flight. The next rung of the Context Product ladder is Dave's to name.
  Open items that PREDATE this phase and are not its debt: cp-01/02/03's one-document exemption claims
  are unruled (`D-IMPL-234` carves the one red test to them); `D-IMPL-221`'s cp-02 history. The
  phase's own 17 deferred rows live in `deferred-items.md`. Next free decision id `D-IMPL-235`.
  PRIOR:
  **PHASE 24.4 IS PAUSED AFTER ITS BUILD, AWAITING DAVE'S EVALUATION OF THE PRODUCT.** 14 of 14
  plans complete. The stop is the DELIVERABLE, not a blocker: `example_delivery.md` sections 1 and
  11 put the pause after the build and before any close panel, `D-GATE` or completion mark, and
  Dave validates that `examples/cp-04-corporate-family-tree` runs from a cold shell himself.
  **Nothing is closed** -- `docs/DECISIONS.md` has no `D-GATE-24.4` entry (0 entry-opening lines,
  against a control of 1 for `D-GATE-24.3`), `ROADMAP.md` is untouched, no milestone is marked
  complete. **The next event is Dave's evaluation.** He resumes with "approved" for the close
  protocol, or with what to fix. **Five items need his ruling and none was decided by the
  executor:** criterion 37's wording versus the measured `resources/list`; whether the
  `mkdocs.yml` cp-04 comment stays; cycle 2's unservability; the three gates that passed their own
  sabotage as worded (all rewritten before shipping); and the plan text that named eight gaps
  where criterion 49 names eleven. See `## Current Position` above and `24.4-14-SUMMARY.md`.
  PRIOR: **PHASE 24.1: WAVES 1-10 OF 11 DONE. WAVE 10 IS PARKED ON EXACTLY ONE DAVE DECISION AND
  WAVE 11 CANNOT START UNTIL IT LANDS.**
  **THE DECISION -- BLOCKER A.** `tests/products/test_gate_two_call_shape.py`
  `MAXIMUM_ONE_DOCUMENT_DEPLOYMENTS = 1`, no headroom BY DESIGN so a human rules on each
  addition. `cp-00` is a genuine second claimant beside `s1-00`. **Option 1 (recommended):
  raise to 2, NAME `cp-00` in the commit message** -- the constant's own comment instructs
  exactly this, and it touches `tests/` only so criterion 16 survives. **Option 2: give
  `cp-00` a second Control Plane document** -- undoes `D-51`'s one-document teaching point
  and is a BUILD. **DO NOT accept the executor's citation of `D-IMPL-146` as a standing
  prohibition**: `146` refused a raise because the DETECTOR was wrong; here the detector is
  right and the failing assertion is a ROSTER that names both claimants. Two assertions in
  that one module are the ONLY remaining `make ci` failures.
  **DO NOT RE-DERIVE ANY COUNT FROM THIS BLOCK (`D-65`).** It is a cached measurement.
  Re-enumerate from the tree: findings from
  `.planning/phases/24.1-*/deferred-items.md` and `24.1-PRESSURE-TEST.md` §4.1;
  gate state from `make ci` chunked in the FOREGROUND; criteria from `ROADMAP.md`
  `### Phase 24.1`. **A roster of ids, never a cardinality.**
  Gates at `4cb235e`: `tools.lints --all` **rc=0**; `tests/examples` **537 passed / 0 failed
  / 37 skipped**; `docs-strict` **0/0/0/0**; `tests/products` + `tests/invariants` **2
  assertions failing, both Blocker A**. `src/` and `runtime/` diff-empty against
  `phase-24.1-base` (142 and 71 tracked files) -- the phase built NOTHING in the SDK, which
  is the point. Findings recorded and NONE closed; the SDK-side roster is the ONLY list
  `D-05` reads for drift and it is **FOUR: empty-operator-gate-two-assertions (Wave 3),
  `ProductClassDeclaration` MAX_TTL seconds (Wave 4), `build_operator_registry`
  deployment-operator seam (Wave 5, `D-59`), `ContextAssemblerProtocol.assemble` return type
  (Wave 5, `D-60`)** -- verify that roster against the tree before quoting it.
  **AFTER BLOCKER A: re-run `make ci` chunked foreground, re-assert criterion 19, then Wave
  11 = CLAUDE.md §3.1 close (cross-AI panel `--all` -> single-agent review -> verify EVERY
  finding -> fix blocking in-phase -> present to Dave), which STOPS FOR DAVE.** `D-58`'s
  short SDK phase for `D-59`/`D-60` is schedulable AFTER this phase. PRIOR STATE AT WAVE 8:
  **PHASE 24.1 IS EXECUTING ON BRANCH `phase-24.1`. WAVES 1-8 OF 11 ARE COMPLETE.**
  **Wave 8's BLOCKING human gate is DISCHARGED (`D-63`, Dave, 2026-08-26).** **NEXT:
  Waves 9 and 10, both autonomous; Wave 11 (§3.1 close) STOPS FOR DAVE.** ONE deliberate
  red signal remains and **WAVE 9 TASK 2 OWNS IT**: `tools.lints --all` rc=1 with exactly
  2 `DOCS-11` findings, `.planning/REQUIREMENTS.md:36` and `:330`, citing the renamed
  `::SECTION_ONE_GLOB` -- re-point both at
  `tests/examples/test_spine_separation.py::SPINE_GLOBS`. The README red is CLOSED.
  `tests/examples` stands at **537 passed / 0 failed / 37 skipped**; `docs-strict`
  **0/0/0/0**. Criterion 19 wants `make ci` green at the GATE commit = Wave 10.
  Running total: **SEVEN** recorded findings, none closed -- **FOUR on the SDK surface**
  (the only number `D-05` reads for drift) and **THREE in TOOLING**, from Waves 6, 7 and 8
  respectively. `cp-00` is green, so `D-58`'s short SDK phase for `D-59`/`D-60` is
  SCHEDULABLE after this one. **STILL UNRULED: §F marker 15** -- measured p50/p95 latency
  and per-call cost, owed by *"the wave that runs the assembly"*. Orchestrator recommends
  **Wave 10** and needs the ruling BEFORE Wave 10. PRIOR STATE AT WAVE 7:
  **PHASE 24.1 IS EXECUTING ON BRANCH `phase-24.1`. WAVES 1-7 OF 11 ARE COMPLETE.**
  **NEXT: Wave 8, AND IT STOPS FOR DAVE** -- the docs wave (`D-28`: a deep example
  README **and** a published page, both, because Dave chose both explicitly). **DO NOT
  BE ALARMED BY A RED TREE AT THIS POINT: `make ci` IS DELIBERATELY RED BETWEEN WAVES
  7 AND 9 AND BOTH SIGNALS HAVE A NAMED CLOSER** -- 4 `test_cp_readme_template.py`
  failures that WAVE 8 turns green by writing the README, and `tools.lints --all` rc=1
  with exactly 2 `DOCS-11` citation findings that **WAVE 9 TASK 2** turns green by
  re-pointing `.planning/REQUIREMENTS.md:36` and `:330` at
  `tests/examples/test_spine_separation.py::SPINE_GLOBS`. Criterion 19 wants green at
  the GATE commit, which is Wave 10. `tests/examples` stands at **532 passed / 4
  failed / 38 skipped**. Running total: **SIX** recorded findings, none closed --
  **FOUR on the SDK surface** (the number `D-05` reads for drift) and **TWO in
  TOOLING**. `cp-00` is green, so `D-58`'s short SDK phase for `D-59`/`D-60` is
  SCHEDULABLE after this one. **UNRULED AND WAITING: §F marker 15** -- measured p50/p95
  latency and per-call cost, owed by *"the wave that runs the assembly"*; Waves 5 and 6
  both were and nobody measured a latency. Orchestrator recommends **Wave 10**; Dave's
  call. PRIOR STATE AT WAVE 6:
  **PHASE 24.1 IS EXECUTING ON BRANCH `phase-24.1`. WAVES 1-6 OF 11 ARE COMPLETE.**
  **NEXT: Wave 7** (the three structural gates, and the one `cp-*` must deliberately
  stay OUTSIDE with the reason WRITTEN INTO the test -- `D-23`/`D-24`). Waves 7, 9 and
  10 are autonomous; **Wave 8 (docs: deep README + published page, `D-28`) and Wave 11
  (§3.1 close: cross-AI panel -> single-agent review -> Dave) STOP FOR DAVE.** Wave 6's
  pre-wave key-links check reports both of Wave 7's links unverified -- EXPECTED, both
  name files Wave 7 itself creates, which step 7b says to skip. Running total: **FIVE**
  recorded findings, none closed; `cp-00` is green so `D-58`'s short SDK phase for
  `D-59`/`D-60` is now schedulable, AFTER this phase. **UNRULED AND WAITING: §F marker
  15** -- measured p50/p95 latency and per-call cost, owed by *"the wave that runs the
  assembly"*, which Waves 5 and 6 both were. Nobody has measured a latency; whether a
  remaining wave takes it is Dave's call. PRIOR STATE AT WAVE 3:
  **PHASE 24.1 IS EXECUTING ON BRANCH `phase-24.1`. WAVES 1-3 OF 11 ARE COMPLETE.**
  Base tag `phase-24.1-base` = `d50924c` (= `main`). Nineteen Success Criteria LOCKED
  before planning (`D-GATE-19`); criterion 3 carries a MARKED amendment. The spec
  `examples/cp-00-institutional-holders/spec/CP-SPEC-000-institutional-holders.md` is
  COMPLETE to the Standard (front matter + SSA-SSG) and `artifacts/assembly-recipe.yaml`
  carries the SSD table as data with one runtime witness per step. **NEXT: Wave 4.**
  Waves 4-7 are autonomous; **Wave 8 (docs) and Wave 11 (SS3.1 close) STOP for Dave.**
  `src/` and `runtime/` are diff-empty against the base and MUST STAY SO -- the phase
  builds nothing in the SDK; gaps are RECORDED, never closed (`D-04`). Forty-six
  decisions `D-01`..`D-46` in `24-CONTEXT.md`; **ids are STABLE and never renumbered**
  (`D-31`), and that file QUOTES ITS OWN SUPERSEDED TEXT inside corrections, so anchor
  on the operative sentence rather than a grep hit (`D-32`). New decision entries start
  at `D-IMPL-212` -- `202`-`211` are reserved candidates. PRIOR STATE:
  **PHASE 23.1 IS CLOSED, GATED AND MERGED. NOTHING IS IN FLIGHT.** `D-GATE-23.1` logged
  2026-08-25 (Dave). **NEXT ACTION: discuss and plan Phase 24 (Context Production)** -- it
  starts on this gate, per Dave. Its criteria are NOT written and that is deliberate
  (`D-GATE-19` locks them at the discuss sitting). **TWO SDK-SURFACE QUESTIONS GATE ITS
  PLANNING AND ARE DAVE'S:** the closed EIGHT-operator vocabulary against the SDK's FOUR
  categories, and the standard's SIX universal validation gates against the SDK's THREE
  where `D-IMPL-102` limb 3 has already ruled no fourth joins `run_gates`. **DO NOT run
  `complete-milestone`** -- blocked for the structural reason named in `D-GATE-23.1` -- and
  **NEVER run `new-milestone` before it**. **OWED, NAMED, NOT FIXED:** the shipped
  `channel_disagreements` blind spot (four rows, five waves; fixing it is BUILDING), the
  four Dave-owned reading items `#2`-`#5` (NOT dischargeable at `D-GATE-24`), the
  `D-IMPL-144` residual at 34, and DELETION for every scheduled row. PRIOR STATE:
  **PHASE 23.1 IS THE NEXT PHASE AND IT IS NOT YET PLANNED. NOTHING IS IN FLIGHT.**
  Its NINETEEN Success Criteria are LOCKED in the ROADMAP entry (`dcd8cad` + the criterion
  19 follow-up) and were written BEFORE planning per `D-GATE-19`. Two of Dave's rulings are
  RECORDED there rather than re-litigated: `D-27`'s `00`-`08` half is **KEEP-QUARANTINED
  for v0.2** (criterion 7 LOGS it, does not make it, and DELETION STAYS OWED), and the four
  `[run]` packet items split with `#1` reserved to Dave by `D-13`/`D-IMPL-70` and `#10`
  needing GitHub Actions output this session cannot fetch. **Phase 24 (Context Production)
  starts as soon as `D-GATE-23.1` lands** -- Dave confirmed this explicitly. NEXT ACTION:
  `plan-phase 23.1`. PRIOR STATE:
  **PHASE 23 IS CLOSED, GATED AND MERGED. NOTHING IS IN FLIGHT.**
  `D-GATE-23` logged 2026-08-25 (Dave). Branch `phase-23`, `PHASE_BASE` `b87fe58`, **76
  commits**, merged to `main --no-ff` naming the entry. `D-GATE-21`, `D-GATE-21.1`,
  `D-GATE-22` and `D-GATE-22.1` remain in force and are not amended.
  **THE MOVE IS DONE AND NOTHING WAS DELETED.** 265 files at `archive/examples/`, 58 under
  `examples/` (`s1-00`, `s1-01`, `hw1-companies-over-revenue`, `hw1-harness-clients`).
  **DELETION IS STILL OWED for every scheduled row** (`D-IMPL-191` ruling 3) -- an archived
  path CONTINUES to count as a live coupling, which is what the re-pointed sweep enforces.
  **WHAT A NEXT SESSION MUST NOT DO.** Do NOT run `complete-milestone`. The v0.2 milestone is
  NOT done even though every ROADMAP phase reads checked: `DOCS-07`..`DOCS-19` remain
  undischarged against retired Phase 16, `Not built` rows are still owed, and 27
  `human_needed` items are named and not discharged.
  **OPEN FOR DAVE, CARRIED PAST THIS GATE BY HIS OWN RULING:** the DELETION half of `D-27`;
  the two `CLNT-17` framing questions, RAISED AND EXPRESSLY NOT RULED (content-hash EQUAL at
  both ends, still `Not built`); `DOCS-14`/`EXAM-02`'s replacement surface; and deferred items
  7-10 in
  `.planning/phases/23-the-archive-move-retiring-the-ten-condemned-example-trees-wi/deferred-items.md`
  with their exact edits named.
  **THE OWED FOLLOW-UP FROM THIS GATE.** Criterion 15's TEXT should be updated in a small
  follow-up so a later phase inherits the chunked-foreground reading from the criterion rather
  than from `D-GATE-23`. Until that lands, `D-GATE-23` is the governing statement, and its four
  conditions bind: `make -n ci` proves the chunk list IS the full recipe; every constituent
  command runs FOREGROUND with its exit code recorded; the deviation is NAMED wherever it is
  used; and criterion 15's coverage proof is discharged. Backgrounding the whole pipeline,
  claiming *"make ci green"* without naming the chunking, and silent substitution are all
  expressly refused.
  **SIX STANDING HAZARDS, recorded so a later session does not re-derive them.** (1) THE
  CITATION LINT IS GREEN AND FALSE on stale paths via a suffix fallback -- `tools.lints --all`
  at exit 0 is NOT proof a path exists. (2) TESTS GO QUIET RATHER THAN RED in at least six
  distinct ways found in this phase: a `.PHONY` name with NO RULE exits 0 printing *"Nothing to
  be done"*; an out-of-range `--8<--` line slice renders an EMPTY code block at exit 0
  (`check_paths: true` guards a missing file and a missing named section and guards a line
  range NOT AT ALL -- the workaround is REJECTED, do not reinstate it); an empty diff from a
  broken command is indistinguishable from a clean tree; an empty schedule kills pytest
  collection so a sabotage cannot be observed at all; a misspelled pathspec and a clean tree
  are the same string; and a predicate that SUMS where it should quantify PER MEMBER reports
  clean over a member it never examined (`B1`, this phase). (3) `git checkout --` CAN DESTROY
  AN UNCOMMITTED FIX while `git diff --quiet` reports success -- back up OUTSIDE the tree.
  (4) BACKGROUND BASH DIES AT ~8-10 MINUTES on this host and a killed run looks EXACTLY like a
  pass; run long legs FOREGROUND, chunked, with coverage proven. (5) `ccf` is
  editable-installed, so a broken `parents[N]` cannot fail and no gate in this repo can witness
  that class. (6) **REGENERATE `docs/surface/examples/RETIREMENT-COUPLINGS.md` LAST, in the
  venv, after EVERY `.planning/` write including SUMMARYs** -- the sweep walks `.planning/`,
  and this ordering was got wrong twice in this phase.
  **PROCESS RULES THAT HELD AND MUST KEEP HOLDING.** `.planning/STATE.md` and `ROADMAP.md` are
  **HAND-EDIT ONLY** (`D-15`); no `state.*` or `roadmap.*` writer was invoked in any wave of
  this phase. ROADMAP success criteria **PARSE ONE PER LINE** -- a wrapped criterion becomes a
  separate verification truth. Never write an anchored `path.py:LINE` citation; use
  `path.py::symbol` (`D-IMPL-114`), because the anchored form is what made `make ci` red for
  three waves against `D-IMPL-123`'s ceiling of zero.
---

# STATE — CCF SDK

## Project Reference

**Core value:** Whitepaper fidelity — every load-bearing primitive in
`docs/CCF_Whitepaper_1-2.md` realized in code with its contracts, invariants,
and composition properties. Priority order: fidelity → general-purposeness →
harness neutrality → adoptability. `/home/parkave/ccf_code/CLAUDE.md` (rev 4)
is canonical for phases, review protocol, invariants, and decision log.

**Current focus:** **NOTHING IS IN FLIGHT.** Phase 23 is CLOSED, GATED, MERGED and
PUSHED (`D-GATE-23`, Dave, 2026-08-25; `5a96628` on `origin/main`), and **there is
no Phase 24** — the ROADMAP defines none. What is open is not a phase but a work
list, and it is enumerated in `## Current Position` below rather than duplicated
here: the 13 open requirement rows, the 27-item human-verification packet, the
DELETION half of `D-27`, the two unruled `CLNT-17` framing questions,
`DOCS-14`/`EXAM-02`'s replacement surface, criterion 15's owed text, and deferred
items 7-10. **`complete-milestone` is REFUSED** — v0.2 is not done.

**CORRECTED 2026-08-25. This block read *"Current focus: **PHASE 19 — The
Client-Seam Integrity Checks Must Be Able to Fail**"* and had done since Phase 19
— through the gates of 19, 20, 21, 21.1, 22, 22.1 and 23, seven phases in which
the field naming the current focus named a phase that had already closed. It is
the same two-places-one-fact defect as the `## Current Position` block corrected
in the same sitting, and it survived longer because nothing in this repo compares
this field to the frontmatter. The superseded text is preserved immediately below,
demoted rather than deleted.**

**Prior focus (Phase 19):** **The Client-Seam Integrity Checks Must Be Able to
Fail.** Phase 18.1 is COMPLETE and GATED (`D-GATE-18.1`, Dave, 2026-08-19).
Phase 19 is DISCUSSED (`19-CONTEXT.md`, 14 decisions) but NOT PLANNED. Phase 18 is
complete; its focus text is preserved below for continuity. *(Phase 19 has since
been planned, executed and gated; this paragraph is the record of what was current
when it was written, not a live statement.)*

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

**PHASE 24.10 IS EXECUTED — NOT pushed, NOT merged, NO `D-GATE`. Dave's evaluation of the build is what is owed next.** Five plans, five waves, 22 commits on `phase-24.10`, tip `0a7d5495`, working tree clean.
**STOP-RULE VERDICT — TERMINAL STATE B.** Dave's rule: *"When cp-05 can use the canonical SDK path without rebuilding fabric behavior itself, the phase stops."* It cannot. Plan 05 drove cp-05's shipped declarations unchanged through `GovernedResolver` and got a product describing a family of **0** over an L3 holding 77 entities and 100 relationship claims, every universal gate green. Plan 04 reached the same terminal state on `s1-01`. `R-03`'s escalation branch fires on measured evidence; **no redesign was started (`D-25`)** and cp-05 was not rewired — its adoption remains the post-phase step.
**Landed:** `R-12` (declared AND consumed), `R-11` (gate at the ruled point, seventh `GateRefusal`, exercised live on cp-05's path both directions), `R-09` (**REUSE** — no new Protocol declared or proposed; 77/100 reproduces against the live remote estate with its drift guard green).
**Blocking adoption:** six absent seams as `xfail(strict=True)` with finding ids — `F-06` (resolver stops at step 4 of nine for any similarity-using class), `F-07` (Pi unseeded vs. replay seeded — two subjects pin identically; an SDK correctness defect independent of any example), `F-08`, `F-09`, `F-11` (unbridged 0 / bridged 77), `F-12`.
**Findings `24.10-F-01` … `F-12`** (twelve; `F-13` deliberately not minted). One in-phase regression, `F-03`, found and closed at `c870fa16`. `F-10`: `s1-01` was dark behind 33 strict xfails for three phases — now 39 passed with the local leg.
**Final gate (orchestrator-measured, whole tree, five chunks): 7,329 passed, 8 failed — every one pre-existing and verified red at the phase base `20499786` in a detached worktree.** `make lint` rc 0; mypy clean, 218 files.
**No panel, no criteria lock** — `D-IMPL-280` (4) rules both out for this phase by name. Next free id `D-IMPL-285`.

**PHASE 24.10 IS DISCUSSED — `D-IMPL-281` (scope, order, boundary) and `D-IMPL-282` (the four gray areas), both
Dave, 2026-09-08, on `phase-24.10`. NOT planned, NOT executed. Nothing pushed, nothing merged, `main` unmoved.**
Four bounded rows in ruled order — **`R-12` → `R-11` → `R-09` → `R-03`** — each earning itself against real cp-05
evidence. `R-01` (`eb455c74`) and `R-10` (`80e38c6f`) are already-completed 24.10 work and are NOT re-planned.
**The fence, Dave verbatim:** *"No cp-05 source, transcript, expected artifact, or published page is modified during
Phase 24.10; cp-05 declarations and measured estate behavior may be used as test inputs to prove the SDK changes."*
`src/`, `runtime/`, `tests/` OPEN; cp-05 CLOSED; cp-00–cp-04 frozen (`D-IMPL-261`); **`examples/s1-01-hello-context-product/`
ruled OPEN** as `R-03`'s target (`D-IMPL-282` (4)). **NO criteria lock, NO review panel, NO proof framework** — a
recorded departure from `D-GATE-19` (`D-IMPL-280` (4)); the stop rule is the phase's test: *"When cp-05 can use the
canonical SDK path without rebuilding fabric behavior itself, the phase stops."* The scout's find that shaped the
phase: `examples/s1-01-hello-context-product/spine.py` is 617 lines and references `GovernedResolver` zero times —
the SDK's own teaching example for the seam bypasses it exactly as cp-05's 2,553-line spine does.
**Resume with `/gsd:plan-phase 24.10`.** Read `24.10-RULINGS.md` (governing verbatim) then `24.10-CONTEXT.md`.
Next free decision id `D-IMPL-283`. Test baseline on this branch: 2,599 passed across `tests/deployment` +
`tests/replay` + `tests/products` + `tests/invariants`, one red (`CLAUDE.md` unchanged-since-phase-base) that also
fails on `main` and is out of scope; `make lint` green.

**PHASE 24.6 — CORRECTION PASS DONE; OWED: DAVE'S APPROVE → `D-GATE-24.6` → MERGE → PUSH (2026-09-05 12:20 MST, `phase-24.6`).**
The §3.1 sequence ran whole (build evaluation, cross-AI panel, single-agent review, every finding verified) and Dave HELD
the gate for one correction pass (`D-IMPL-260`, 09:56 MST). The pass is done: ten ruled items fixed and measured with
controls (`24.6-CORRECTION-PASS.md`), `CFT-G19` minted, the cp-04 page rebuilt from the final tree and replaced in place
(`24.6-PUBLICATION.md`), the suite whole at 6559 collected in four proven chunks, all four legs green, lint/typecheck/
product-gates green, the criteria digest `c0fdc4f4…` unmoved. One PRE-PHASE `gate-tools` red (F-E) is carried exactly as
recorded and never called green. Carried by ruling into the next phase: cp-01's F-1 (measured capability difference),
F-E, P-E's audit clock read. **Resume by presenting `24.6-CLOSE-PREP.md`'s `D-GATE-24.6 — DRAFT, updated after the
correction pass` to Dave; on APPROVE write `D-GATE-24.6` (next id `D-IMPL-261`), merge `--no-ff` to `main`, push.**
The paragraphs below are the record as it stood at earlier sittings.

**PHASE 24.6 IS EXECUTED — all 12 waves done (plans 01–16), 2026-09-05, on `phase-24.6`; NOT pushed, NOT merged.**
Criteria locked at 36 (`24.6-CRITERIA-LOCK.md`, Amendment 3 digest `c0fdc4f4…` reproduces on the close tree, with all
four historical controls). Mid-phase rulings: `D-IMPL-256` (before Wave 1), `D-IMPL-257` (Wave 5, fence widened narrowly
for citation maintenance), `D-IMPL-258` (Wave 10, five findings; fix merged `ea1af296`), `D-IMPL-259` (Wave 11, cp-04
`max_depth` floor of 1 on the request contract; shipped `958a12e0`). Both rung pages are PUBLISHED IN PLACE: cp-04
`f20ed519-…`, cp-01 `6edeeba9-…` (`24.6-PUBLICATION.md`). Close evidence is `24.6-CLOSE-PREP.md`: suite 6515 collected in
four proven chunks with 0 failed; lint/typecheck/product-gates/docs-strict/citation green; legs postgres 271/0, neo4j
22/0, mongo 24/0. **NOT green:** `make leg-fluree` 5 failed / 301 passed — five IN-PHASE reds in cp-04 modules no wave
collected (base `1022ad59` runs the same three modules 68 passed); and one PRE-PHASE `gate-tools` red. Nine findings
carried for Dave (F-A..F-I), none with a disposition. **Owed, in order: Dave's build evaluation, then the cross-AI panel
(packet STAGED, 39 bundles, no reviewer invoked), then the single-agent review, then `D-GATE-24.6`.** Next id
`D-IMPL-260`. **Resume by presenting the build to Dave — do NOT run the panel, draft a gate, or mark anything complete
first (`pause-after-the-product-is-built`).** The paragraphs below are the record as it stood at earlier sittings.

**PHASE 24.6 IS DISCUSSED — `D-IMPL-252` (not a product rung) and `D-IMPL-253` (28 rulings), Dave, 2026-09-04.**
Context at `.planning/phases/24.6-sdk-gap-phase-the-delivery-boundary-realized-refusal-as-a-go/24.6-CONTEXT.md`;
alternatives in `24.6-DISCUSSION-LOG.md`. `src/`+`runtime/` OPEN; `examples/` only where an SDK change makes a rung
stale (cp-04). The ledger (B-01..B-14 + `LC-01..05` + two `D-IMPL-245` rows) is the FIRST deliverable, no code
before it. Criteria at planning (`D-GATE-19`). Next id `D-IMPL-255`. **Resume with `/gsd-plan-phase 24.6`.**
The paragraph below is the record as it stood before this sitting.

**PHASE 24.5 IS COMMISSIONED — `D-IMPL-235` (Dave, 2026-09-02) — AND NOTHING OF IT IS BUILT.** It is the
comprehensive SDK gap catch-up for cp-00 through cp-04: ledger sitting first (no code), fix-rows clustered
into at most two waves, `src/`+`runtime/` OPEN for the first time on the ladder, close by re-running
cp-01..04 and reading which limitation-gates flip RED. Direction is banked in ROADMAP `### Phase 24.5` and
`.planning/phases/24.5-sdk-gap-catch-up-cp-00-through-cp-04/.continue-here.md`; criteria are written at
the discuss sitting (`D-GATE-19`). **One ruling open:** whether `D-IMPL-224` ("no `ProductGate` type in
Phase 24" -- the container) is amendable if `24.4-D-31` is a fix-row. Next id `D-IMPL-236`. **Resume with
`/gsd-discuss-phase 24.5`.** The paragraph below is the record as it stood at the 24.4 gate.

**PHASE 24.4 IS CLOSED. `D-GATE-24.4` APPROVED (Dave, 2026-09-01).** Built, evaluated (five-check
gate held on live fixtures), paneled on the shipped tree, reviewed, fixed, gated, merged `--no-ff`.
`src/` + `runtime/` 0 files changed; gaps `24.4-D-26`..`24.4-D-37` recorded and none closed. Pytest
4664 / 45 / 1 -- the 1 is the `D-IMPL-234` carve and is NOT suite-green. Family-scope guards stay
`SystemExit` by ruling. Next id `D-IMPL-235`. Nothing is in flight; the next rung is Dave's call.
Everything below this paragraph is the record as it stood before the gate.

**PHASE 24.4 IS BUILT, NOT GATED. THE BUILD WAS EVALUATED AND DAVE'S FIVE-CHECK GATE HELD ON
LIVE FIXTURES. HIS FIVE RULINGS ARE LOGGED AT `D-IMPL-233` AND APPLIED.** 14 of 14 plans have
SUMMARYs. `main` is ahead of `origin/main`; the tree is clean. **Nothing is closed:**
`docs/DECISIONS.md` holds no `D-GATE-24.4`, `.planning/ROADMAP.md` is not ticked for this phase,
no milestone is marked complete, and **no close panel has run.**

**THE EVALUATION IS DONE.** All five of Dave's checks held, run against the live fixtures rather
than reproduced from a document: 22 nodes at `205ae065...`; `MAX_DEPTH=2` and `MAX_DEPTH=4`
sealing to DIFFERENT addresses; `MAX_DEPTH=8` refused BY NAME at the ceiling of 6 and never
clamped; `AS_OF` refused `not_supported_at_tier`; and 22 subtree nodes of which 2 resolve in the
attribute store and 20 resolve to NO row and STAY IN THE TREE. Dave: *"If those five hold on your
machine, the build is the product you asked for."*

**WHAT COMES NEXT IS THE CLAUDE.md SS3.1 CLOSE PANEL, AGAINST THE SHIPPED TREE.** Dave: *"Do not
treat 14/14 plans as a close. No `D-GATE` until that run plus SS3.1."* The run is done; the panel
is not. It reviews the **shipped code**, not the plans -- those are already executed. Write it to
`24.4-CLOSE-REVIEWS.md` so any pre-execution plan review survives. **Inline the source over
stdin:** on this host `codex` can exit 0 having read nothing (its `bwrap` sandbox fails silently)
and a single argv string caps at 128KB, where an over-long payload dies rc=126 with 0 bytes and
reads exactly like a clean empty review. Brief the panel on the findings already known and point
it at what is ADJACENT to each. **Verify every finding against the tree before recording or acting
on it, and record the rejected ones as rejected.** Then triage blocking vs advisory, fix blocking
in-phase, present to Dave, and only then `D-GATE-24.4`.

**THE ONE OPEN QUESTION, AND IT IS DAVE'S: does criterion 49's roster extend from ELEVEN to
TWELVE?** Ruling 3 folds *cycle 2 is not askable* into the 24.4 gap list; ruling 5, in the same
message, enumerates that list as exactly eleven, `24.4-D-26` through `24.4-D-36`. Both cannot be
mechanical without a twelfth id. It is recorded as **`24.4-D-37`, OUTSIDE the roster**, at
`D-IMPL-232` AMENDMENT 2. Criterion 49 is NOT extended, nothing is renumbered, and nobody wrote
that he approved twelve (`D-IMPL-227`, silence is not assent).

**RULING 4's CLOSE NOTE, to be read before the panel runs:** *criterion-shaped sabotage can still
miss; a sabotage counts only when the gate goes RED naming its OWN id and the tree is restored.*
`CFT-G05`, `CFT-G16` and `CFT-G10` each passed the sabotage their own criterion worded, from three
unrelated causes with one shape -- each was reading a RECORD OF THE INTENT rather than the EFFECT.
All three were rewritten before shipping, so the shipped count is ZERO. **A note, not a mechanism:
no new test, no new lint, no new gate. Dave said so in terms.**

**WHAT TO RUN, if the product is to be exercised again, in order:** `make venv`; export the two connection variables the README's Run-it
section names; `make -s example-cp-04`; then `MAX_DEPTH=2` and `MAX_DEPTH=4` (the content
addresses must DIFFER); then `MAX_DEPTH=8` (must be REFUSED BY NAME at the ceiling of 6, never
clamped); then `AS_OF=2026-01-01` (must be refused `not_supported_at_tier`); then read
`examples/cp-04-corporate-family-tree/summary_explanations.md`; then build and open the page with
`.venv/bin/python examples/cp-04-corporate-family-tree/page/build_page.py`.

**THE FIVE ITEMS THAT WERE WAITING ON DAVE ARE ALL RULED, at `D-IMPL-233`, and applied. The
paragraph below is kept as the record of what was carried to him and what each item actually was.
(1) RULED -- criterion 37 amended a second time; `resources/list` -> `[]` and the
`resources/templates/list` wording stands; the shipped both-listings check stays. (2) RULED -- the
`mkdocs.yml` comment is DELETED and plan 13's verify line freed; the measurement moved to
`deferred-items.md` item 11. (3) RULED -- cycle 2 is RECORDED, not served: `24.4-D-37`, outside
criterion 49's roster, with the roster question left OPEN to Dave. (4) RULED -- advisory, with a
close note and no new mechanism. (5) RULED -- the roster is ELEVEN under RENAMED `24.4-D-NN` ids.
The original text, preserved:**

**FIVE ITEMS WERE WAITING ON DAVE and none was decided by the executor.** (1) **Criterion 37's
amended wording is wrong against the tree** -- it says the product resource is *"enumerable in
`resources/list`"*, and measured at an MCP client `resources/list` returns `[]` while
`resources/templates/list` returns the URI template, because a placeholder URI registers as a
TEMPLATE. Substance and `24.4-D-34` are unchanged and the shipped check asserts BOTH listings. This is
the THIRD criterion in this phase found wrong against the tree, and amending a ruled criterion is
Dave's (`D-IMPL-222`). (2) **The `mkdocs.yml` cp-04 nav entry could not be made** -- `docs_dir` is
`public/` and the render is git-ignored, so a nav entry aborts `make docs-strict`; cp-00..cp-03
carry none either and no locked criterion requires one. The measurement was recorded as a COMMENT
in `mkdocs.yml`, so plan 13's `grep -q 'cp-04' mkdocs.yml` now passes on the comment rather than
on a nav entry -- a token present in both the compliant and the violating case. Whether the
comment stays is Dave's. (3) **Cycle 2 is unservable** -- `expected.yaml` gives
`cycle_2.external_in_edges: 0`, `into_cycle_2: 0`, and all six members carry `lei: null`, so it can
be reached neither as a subtree nor asked for as an anchor; plan 11 asserted the unreachability
instead. Criterion 39 speaks of SERVED nodes so it is discharged, but it is a plan-versus-estate
discrepancy of `24.4-D-32`'s shape. (4) **Three gates passed their own sabotage when written as their
criterion worded it** -- `CFT-G05`, `CFT-G16` and `CFT-G10`, from three unrelated causes, each
caught and rewritten BEFORE shipping, so the shipped count of gates that passed their first
sabotage is ZERO. (5) **The plan text lagged its own criterion** -- plan `24.4-14`'s objective
names eight gaps and its ROADMAP checklist bullet names six; criterion 49 as amended names
ELEVEN, `24.4-D-26`..`24.4-D-36`. All eleven are recorded at `D-IMPL-232`; the lag is written down rather
than reconciled away, and criterion 49 was NOT amended.

**MEASURED AFTER THE RULINGS WERE APPLIED, 2026-09-01, each against a control shown to move:**
`tests/examples` **787 passed / 113 skipped** rc=0; `tests/invariants/test_citation_coverage.py`
**5 passed** rc=0, with the ratchet watched go **0 -> 1 -> 0** under a planted line-anchored
citation and the tree restored; `tools.lints --all` rc=0, driven to rc=1 naming `cinv02-harness`
by a planted harness import in `src/` and back to rc=0 on removal; `make docs-strict` rc=0;
`grep -c 'cp-04' mkdocs.yml` **0** against a positive control of **1** for `docs_dir`; **16** gate
ids enumerated `CFT-G01`..`CFT-G16` with **0** `observed_red` null and **0** `CFT-G17`; `src/` and
`runtime/` diff-EMPTY across `92761e0..HEAD` against a positive control showing `examples/` moved
**24** files in the same window, and it is recorded that a misspelled `srcc/` pathspec diffs empty
EXACTLY like a clean one, which is why that control exists.

**MEASURED AT THE PAUSE, before the rulings, each with a positive control** (`D-IMPL-232`,
`24.4-14-SUMMARY.md`): `tests/examples` **769 passed / 113 skipped** rc=0; `tools.lints --all` rc=0; unanchored Python
citations **0** against a ceiling of 0, with the ratchet watched go 0 -> 1 -> 0 under a planted
citation; **16** declared gate ids with **0** still `null` and `CFT-G17` absent; `src/` and
`runtime/` both diff-EMPTY across `92761e0..83953e8`, against a positive control showing
`examples/` moved 24 files in the same window and a `srcc/` pathspec refused by name.

---

**WHAT IS BELOW HERE IS SUPERSEDED and is kept rather than overwritten** (`D-19`, `D-IMPL-174`).

**PHASE 24.3 IS CLOSED. TIER 1 OF THE CONTEXT PRODUCT LADDER IS COMPLETE. PHASE 24.4 IS
ANCHORED BUT NOT PLANNED, AND ITS BUILD HAS NOT STARTED.** `origin/main` = `92761e0`, tree
clean. All four Tier-1 rungs are gated: cp-00 (`D-GATE-24.1`, `D-GATE-24.1.1`), cp-01
(`D-GATE-24.2`), cp-02 (`D-GATE-24.2.1`), cp-03 (`D-GATE-24.3`).

**WHAT THIS SESSION CHANGED, 2026-08-31.** The two SDK-surface questions that had gated
Phase 24 planning since 2026-08-25 are RULED -- `D-IMPL-223` (four scheduling classes as the
scheduler; the Standard's eight names as spec vocabulary; `OperatorCategory` closed for v0;
`D-IMPL-212` stays OPEN) and `D-IMPL-224` (product gates are a declared artifact plus a CI
coverage check; no `ProductGate` Protocol in 24.4; the Standard's extra gates are declared
product gates, never new members of `run_gates`). Phase 24.4 is anchored in `ROADMAP.md`
WITHOUT Success Criteria, per `D-GATE-19`'s forward binding.

**WHAT IS NEXT.** The 24.4 DISCUSS SITTING IS DONE (2026-08-31, commit `3a54af0`) --
`24.4-CONTEXT.md` and `24.4-DISCUSSION-LOG.md` are written and committed. Four areas
were ruled: temporal posture, traversal shape and cycles, the MCP door, and the gates
artifact plus its timing. **Next is `/gsd:plan-phase 24.4`**, where the Success
Criteria lock (`D-GATE-19`). **Phase 24.5 is NAMED but NOT scoped** -- the gate-coverage
checker plus the cp-00/cp-01 backfill; its criteria lock at its own sitting.
**SIX SDK GAPS were recorded and NOT closed** (`D-26`..`D-31` in `24.4-CONTEXT.md`),
per `D-04`: the Fluree adapter floors but cannot pin, `graph_snapshot_at: datetime` vs
an int `t`, `@iso:` searching backdatable event time, the adapter docstring collapsing
three time axes into two, and the MCP resource URI being unable to address a
parameterized product. `D-GATE-24.3` is APPROVED and closed; a
precondition naming it was written here 2026-08-31 and STRUCK the same day (Dave) -- *"a
precondition whose subject is closed can never fire -- same class as an empty-population
check."*
Carried into 24.4 as a FINDING, not a reopened gate: cp-00's seven declared gates with no
test-file presence and cp-01's one (`CPR-G08`).

**THE `progress:` BLOCK IN THE FRONTMATTER IS STALE AND IS NAMED AS SUCH RATHER THAN
INCREMENTED.** It still reads the Phase 23.1 gate figures; `D-19` and `D-IMPL-174` require a
re-measure from the tree, and none was run this session.

---

**EVERYTHING BELOW THIS LINE IS PRESERVED HISTORY** from the Phase 24.1 execution window and
is NOT the current position. It is retained because this file's convention is to name a
superseded value rather than overwrite it silently (`D-19`, `D-IMPL-174`).


**PHASE 24.1 IS EXECUTING. WAVES 1-10 OF 11 COMPLETE AND UNPARKED -- `D-66` CLOSED BLOCKER A -- ON BRANCH `phase-24.1`. WAVE 11 (THE CLAUDE.md 3.1 CLOSE) IS THE ONLY THING LEFT.**
Phase 24 is an UMBRELLA; 24.1 is its first buildable unit -- one Context Product
example (institutional holders above a caller-chosen threshold, SEC 13F in
`ccf_dataprep` Postgres, Assembly Mode 1) built to PRESSURE TEST the SDK's surface
against the Context Product Specification Standard. **The Standard defines what the
SDK must implement; where the SDK cannot express what a conforming spec orders, that
gap is RECORDED here and closed in a SEPARATE phase.** Expectation is FEW OR NO gaps,
because the spec derived from the SDK's own requirements -- so a long gap list is a
DRIFT signal, not a normal outcome (`D-05`). Through Wave 8: **SEVEN** recorded
findings, all under `D-04` and NONE CLOSED. **The SDK-side count is still FOUR**,
all four seam-ergonomics rather than algebra -- which is what `D-05` actually reads
for drift, and four is a normal outcome. **The fifth, sixth and SEVENTH are all in
TOOLING, not the SDK** (Wave 6's lint numeric-majority blind spot; Wave 7's
unchecked LLM-import coverage on examples; Wave 8's ungated dataset statements),
and that separation is load-bearing: a tooling blind spot is not a gap in what the
fabric can express, and merging the lists would manufacture a drift verdict out of
three lint holes.
**WAVE 8: BOTH `D-28` DOCUMENTS SHIPPED, AND THE BLOCKING HUMAN GATE IS DISCHARGED
(`D-63`, Dave, 2026-08-26).** `README.md` 419 lines under the seven template headings
(the MECHANICS) and `public/concepts/the-first-context-product.md` 263 lines with six
`--8<--` includes and ZERO transcribed code (the ARGUMENT). `docs-strict` **0/0/0/0**,
each step foreground and unpiped, `make -n docs-strict` printed first to prove the four
ARE the recipe. Wave 7's deliberate README red CLOSED: `test_cp_readme_template.py`
**4 failed -> 10 passed**; `tests/examples` **537 passed / 0 failed / 37 skipped**, and
532 + 4 + 1 = 537 reconciles exactly against a collected-574 control.

**THE HUMAN HALF WAS CARRIED TO DAVE RATHER THAN DEFERRED, AND THAT IS THE REUSABLE
PART.** He was remote; the checkpoint assumes a terminal. The orchestrator ran
`make example-cp-00` against the live estate, rendered both documents, took the
published page from the STRICT BUILD'S OWN OUTPUT so every excerpt on it arrived by
include, and set `produce.py` beside `deployment.py` **UNLABELLED with a reveal** --
the plan asks whether the boundary is legible *without being told*, so labelled panes
would have destroyed the test. **ALL FOUR FLAGGED READINGS STAND.** One is a PUBLISHED
POSITIONING CLAIM, not a style call, and was surfaced as such before acceptance: the
operator mapping stays **MEASURED** against the plan's wording, so a public page now
states **`Enrich` has no SDK expression** -- three of eight map 1:1, three land at
other layers, `Evaluate` exists only as Pi.

**THE FIFTH FLAGGED ITEM WAS SETTLED BY MEASUREMENT RATHER THAN BY RULING**, which is
the better outcome. The README's `D_c ~= 0.56 at 148 days` was written-out arithmetic
from `ccf_config.yaml`; the executor had no DSN and correctly refused to present it as
observation. The live run returns **`D_c` = 0.5582, `F` = 0.4729 at exactly 148 days**
(2026-03-31 -> 2026-08-26), **21 holders served against 21 from an independent
SELECT**, control at a different threshold **39**. CONFIRMED, not trusted.

**WAVE 8'S SEVENTH FINDING IS TOOLING FOR THE THIRD WAVE RUNNING** (`D-04`, NOT
closed): nothing that ships gates criterion 9's four dataset statements --
`grep -rl 'fact about any real company' tools/ tests/` returns **0 files** against
controls of **3** (where they live) and **53** (No-Hardcoding), so the search works.
The guard ran at wave time and was NOT committed; its shape is in `deferred-items.md`.
**AND ONE ORCHESTRATOR NEAR-MISS WORTH KEEPING:** the review page was first written to
`public/_review/`, inside the default-deny-by-existence published surface, where an
unregistered file fails `mkdocs build --strict` on `validation.nav.omitted_files` --
it would have broken the very gate just verified green. Caught before commit, moved to
the scratchpad, `docs-strict` steps 1 and 3 re-run to **exit 0**.

**WAVE 7: THREE GATES ARMED, ONE REFUSED IN WRITING -- AND A DELIBERATE RED WINDOW
IS OPEN THAT IS NOT A BROKEN TREE.** `tests/examples` **508 -> 532 passed**, 4 failed,
38 skipped, re-run in the FOREGROUND by the orchestrator and matching the executor's
claim exactly. **BOTH RED SIGNALS ARE INTENTIONAL AND BOTH HAVE A NAMED CLOSER:**
(1) `test_cp_readme_template.py` is RED on 4 tests because it was written against a
LIVE subject with NO STUB -- **Wave 8 writes the README and turns it green**; and
(2) `tools.lints --all` is rc=1 with **exactly 2** findings, both `DOCS-11` ledger
channels (`.planning/REQUIREMENTS.md:36` and `:330`) citing the renamed
`::SECTION_ONE_GLOB` -- the constant is now `test_spine_separation.py::SPINE_GLOBS`,
and **plan 24.1-09 Task 2 closes it**, verified against that plan rather than taken on
the executor's word. **`make ci` IS RED BETWEEN WAVES 7 AND 9 BY DESIGN.** Criterion
19 requires it green at the GATE commit -- Wave 10's obligation, not a regression.

**CRITERION 15 WAS DISCHARGED ONLY AFTER ITS CONTROL FAILED FOR THE WRONG REASON.**
The first draft went red with `NameError: SPINE_GLOBS is not defined` -- red, but not
red about coverage, which is exactly the confusion the criterion exists to prevent.
Restaged: rename the glob to `("s1-*",)`, watch the ASSERTION fail naming the tree it
does not reach, then add `"cp-*"` as the ONLY edit between red and green. The control
rediscovers a marker-stripped copy THROUGH `split_examples` rather than handing it
straight to the predicate, so it proves glob -> discovery -> refusal, not just the
predicate. **`D-24` HAS TEETH, NOT PROSE:**
`test_widening_this_glob_to_cp_would_break_the_example` runs the REAL predicate over
the `cp-*` tree and asserts it DOES refuse -- **2 of 4** modules on `ccf.agents`
against **0 of 9** for `s1-*` -- and the glob was actually widened and watched
producing 8 failures naming `assembler.py` and `run.py`. If `cp-00` ever stops
importing `ccf.agents`, that test fails and tells the reader to RE-DECIDE rather than
delete the exemption. **15 sabotages, all watched RED, each with a DISTINCT named
failure rather than general redness.**

**WAVE 7'S SIXTH FINDING IS AGAIN IN THE TOOLING** (`D-04`, in `deferred-items.md`,
NOT closed): nothing shipped checks any EXAMPLE for an LLM-client import -- a planted
`import anthropic` under `examples/` draws ZERO findings from `tools.lints --all`. It
nearly produced a false reading in the other direction, because `--all` is rc=1 right
now for the unrelated citation window, so the EXIT CODE proves nothing and only the
finding-NAME count does. Control: the same planted import inside `cp-00` gives 6
failed / 6 passed while `s1-01` leaves the gate at 12 passed, so the instrument does
detect coverage where it exists. 18 modules across four live example trees stay
unchecked; reaching them would be a RETROFIT, forbidden by `D-07`.

**WAVE 6: THE EXAMPLE HAS A COMMAND, AND `D-62` IS DISCHARGED.**
`make example-cp-00` is `.PHONY`, help-lined, and deliberately OUTSIDE the always-on
`examples:` aggregate. Against the live estate: **21** holders at the demonstration
threshold, **39** at `MIN_POSITION=500000000`, two different content addresses, and
the 21 equals Wave 1's independent SELECT sweep by a different route. The CI leg is a
`pytest.mark.postgres` module that stands up `postgres:16` ITSELF and seeds it from
`tests/examples/fixtures/cp_00_13f_{schema,rows}.sql` -- **`D-27`: the fixture is
SEEDED BY THE TEST, never committed as a database**, so a schema change breaks the
test loudly instead of drifting. `tests/examples` **485 -> 508 passed**, skips
unmoved at 37; 508 - 485 = **23** = the two new modules' collected count, re-measured
independently by the orchestrator against a control (**14** for one module alone).
**ELEVEN SABOTAGES, ALL WATCHED RED.** `D-62`'s three residues are closed -- §E.2's
debt bands drop `[TBC]`, §D.2 step 1's prose no longer claims "no SDK symbol", and
§F markers 13, 14 and 16 are CLOSED, each KEEPING ITS ROW so the sentence that raised
it still points somewhere. **TWO RESIDUES LEFT OPEN AND NAMED RATHER THAN GUESSED:**
§E's surviving `[TBC]` is marker 4, the issuer-identity refresh cadence, whose owner
is the SOURCE-ESTATE owner and not any wave of this phase; and **§F marker 15, the
MEASURED p50/p95 latency and per-call cost**, which §F.2 assigns to *"the wave that
runs the assembly"* -- Waves 5 and 6 both ran it and **nobody has measured a
latency**. §G's Lifecycle row now names marker 15 as the one certification evidence
still owed. **`cp-00` IS GREEN, which is the condition `D-58` attaches to the short
SDK phase** for `D-59`/`D-60`; that phase is now SCHEDULABLE and is still NOT 24.1's
to run (`D-04`).

**WAVE 6'S FIFTH FINDING IS IN THE INSTRUMENT, AND IT WAS CAUGHT BY ITS OWN CONTROL.**
The plan asserted `tools/lints/no_hardcoding.py` reaches `tests/`, so a threshold-plus-
LEI dict there is the same violation as one in library code. The executor's FIRST
control returned **rc=0** -- a passing report from an instrument that never fired.
Measured rather than concluded: `RULE_TREE_SCOPE["no-hardcoding"]` DOES include
`tests`, so the scope claim is right; what is narrower than the plan's sentence is
`_is_numeric_table`, which requires a strict numeric MAJORITY -- a 2-entry dict
pairing an int with a string is 1-of-2 and never trips, while a 3-entry numeric table
returns **rc=1**. **RECORDED, CLASSIFIED, NOT CLOSED** (`D-04`; `D-56` says it does
not qualify for close-as-you-go -- it blocks no example from being honest).

**Wave 5's two.** (1) `ccf.deployment.operators::build_operator_registry` dispatches
on the declared parameter artifact's TYPE against four known SDK classes and raises
for anything else, and the Mode 1 spine hands it the whole mapping -- so a deployment
that supplies its own `Operator` has no path into the registry `ProjectionEngine`
resolves the plan against. Measured with four controls: the builder refuses the
operator AND its parameter set; the same builder registers the two declared artifacts;
`OperatorRegistry.register` accepts the operator directly and reads `traversal` off it;
and it refuses a category outside the four. `D-48` says *"registered through the open
`OperatorRegistry`"* -- the REGISTRY is open, the COMPOSITION PATH in front of it is
not. Taken rather than worked around: the operator is registered into the deployment's
OWN registry and applied at L1, where `D-44`/`D-50` place step 1, and the served
lineage still names exactly the two operators the class declares. (2)
`ccf.agents.assembler::ContextAssemblerProtocol.assemble` returns `AssemblyOutcome`
and nothing else -- SEVEN fields, `extra=forbid`, measured, with an eighth named
`refusal` raising `ValidationError` -- so a conforming assembler that receives a
governed `ProductRequestViolation` can only RAISE. The SDK's own reference assembler
never meets this because it HOLDS Pi's already-computed output; an assembler that runs
the spine is the first thing standing where the violation arrives. Both classified
use-case agnostic (`D-08`); the first ADDITIVE, the second NOT (`D-10`). **RECORDED,
NOT CLOSED, NEITHER PROPOSED** (`D-04`). **Wave 4's is that
`ccf.controlplane.artifacts::ProductClassDeclaration` carries `max_ttl_key` and NO
field for the ceiling's SECONDS** -- measured, an extra key is refused
`extra_forbidden` against a control that constructs cleanly -- so `D-43`'s Control
Plane obligation had to be declared in a deployment-owned artifact
(`examples/cp-00-institutional-holders/artifacts/ttl.yaml`) rather than in the one
Control Plane document. **RECORDED, NOT CLOSED** (`D-04`).

**WAVE 4'S RED `make ci` IS GREEN AT WAVE 5, BY `D-51` AND BY THE FILE NAME ALONE.**
Dave ruled the resolution Wave 4 recommended: the printed entry point is named
`run.py`, beside `artifacts/`. Measured unpiped -- `test_artifact_schema_headers.py`
**1 failed/29 passed -> 30 passed**, and `tests/examples` **484 passed + 1 failed ->
485 passed, 37 skipped**. The gate was NOT widened, `artifacts/` was NOT renamed, and
nothing in `src/` or `runtime/` was touched. **Plans 24.1-06, -07, -08 and -11 still
name `consume.py` and are owed the rename**; nothing else about them changes.

**SUPERSEDED, NAMED RATHER THAN DELETED:**

**WAVE 4 FOUND `make ci` RED, AND IT PREDATED WAVE 4.** `git log
--diff-filter=A` pins `examples/cp-00-institutional-holders/artifacts/` to
**`313d1c0`** (Wave 3): the tree has an `artifacts/` directory and no `run.py`
beside it, which
`tests/examples/test_artifact_schema_headers.py::bijection_violations` refuses.
Measured three ways -- directory absent (29 passed), Wave-3-only (1 failed), Wave-4
(the SAME single failure). Three resolutions are named in the phase's
`deferred-items.md`; **none is Wave 4's to pick**, because each reaches into a file
list Wave 4 does not own. Criterion 19 requires `make ci` green at the GATE commit,
so this is a phase-close blocker rather than a wave blocker.

**SUPERSEDED, NAMED RATHER THAN DELETED:**

**PHASE 23.1 IS CLOSED, GATED AND MERGED. PHASE 24 (CONTEXT PRODUCTION) IS NEXT AND IS NOT
PLANNED.** `D-GATE-23.1` approved by Dave 2026-08-25. v0.2's open surface is DISPOSITIONED
rather than completed, and that distinction is the phase's actual finding: 11 rows remain
open by verdict while every one carries an explicit disposition naming who inherits it.
`complete-milestone` is blocked because the tooling reads disposition as incompletion.
**This block is written at the same commit as the frontmatter above, deliberately** -- the
recorded failure mode of this file is the pair going out of step.

**SUPERSEDED, NAMED RATHER THAN DELETED:**

**PHASE 23.1 (THE v0.2 CLOSE-OUT) IS THE NEXT PHASE. IT IS NOT PLANNED AND NOTHING IS
IN FLIGHT.** Written 2026-08-25 after Dave supplied the Phase 24 requirements and ruled
the sequencing. **NINETEEN Success Criteria are LOCKED** in the ROADMAP entry, before
planning, per `D-GATE-19`'s forward binding. **THE PHASE BUILDS NOTHING** -- no SDK
mechanism, no fabric change, no new example; it adjudicates the 13 open requirement rows
and the 27-item human-verification packet and it records. **Phase 24 (Context Production)
follows immediately on `D-GATE-23.1`**, with its description banked and NO criteria yet,
deliberately. Two SDK-surface impacts stand UNRULED and gate Phase 24's planning: the
closed EIGHT-operator vocabulary against the SDK's FOUR categories, and the SIX universal
validation gates against the SDK's THREE with `D-IMPL-102` limb 3 forbidding a fourth.

**This block is written at the same commit as the frontmatter above, deliberately.** The
recorded failure mode of this file is exactly the pair going out of step -- it read
*"NOT APPROVED AND NOT CLOSED"* for a full day while its own frontmatter said closed.

**SUPERSEDED, NAMED RATHER THAN DELETED:**

**PHASE 23 IS CLOSED, GATED, MERGED AND PUSHED.**
  **CORRECTED 2026-08-25 (post-gate). This block read: *"PHASE 23 IS EXECUTED AND
  PRESENTED TO DAVE. IT IS NOT APPROVED AND NOT CLOSED,"* and named HEAD `97a1823`,
  **74 commits**, `main` still AT `b87fe58`, nothing merged or pushed, and
  `grep -c "D-GATE-23" docs/DECISIONS.md` = **0**. Every one of those was TRUE when
  written and FALSE by the time of this edit. The frontmatter above was updated at the
  gate and this block was not, so THE FILE CONTRADICTED ITSELF FOR A DAY -- header
  saying closed, body saying not approved. Nothing gated the pair, which is how it
  went a full ruling stale.**
  All **13 of 13** waves landed on `phase-23`. **COMMIT COUNT RE-MEASURED rather than
  inherited:** the frontmatter's *76 commits* was true when written and the branch grew
  by one afterwards (the `D-GATE-23` entry itself). Measured at the merge:
  `git rev-list --count --no-merges b87fe58..5a96628` = **77** branch commits, plus the
  merge commit = **78** reachable; the merge's second parent IS `5e9deb4`, so that is
  the `phase-23` tip. `D-GATE-23` **LOGGED** 2026-08-25 (Dave) at `5e9deb4` --
  `grep -c "D-GATE-23" docs/DECISIONS.md` = **1**. Merged to `main --no-ff` at
  **`5a96628`**, the merge commit naming the entry. **PUSHED to `origin/main`
  2026-08-25 ON DAVE'S EXPLICIT INSTRUCTION** -- the merge sitting did not authorise a
  push, so it was HELD for a day rather than assumed; `origin/main` was at `efa0044`,
  is now at `5a96628`, and `main` is **0 commits ahead**. Approval authority is Dave's
  alone and `/gsd-review` passing is necessary, never sufficient (`CLAUDE.md` §3.1).
  **WAVE 13 -- the §3.1 close.** Cross-AI panel on the SHIPPED tree with the source
  INLINED (117,567 bytes, nine subjects): codex, cursor, gemini, all three PROVEN to
  have read (every cited symbol resolves; every quote traces to the payload). Record
  in `23-CLOSE-REVIEWS.md`, a file distinct from any pre-execution plan review. The
  additive single-agent depth pass ran separately and is recorded separately.
  **THREE BLOCKING FINDINGS, all fixed in-phase and independently re-sabotaged.**
  **B1 -- CRITERION 10 WAS NOT DISCHARGED.** Its own words are *"suppressing an
  archived path's coupling row is watched RED"*; against the shipped
  `archive_sweep_problems` that was FALSE. Suppressing all 21 coupling rows for
  `archive/examples/03-harness-portability` left 110 rows against a floor of 10 and
  the predicate returned EMPTY. The phase's own defect class -- a tool that reports
  clean because it did not look -- INSIDE the control commissioned to prevent it.
  Fixed by asserting per-tree coverage; count floor KEPT (different diagnosis);
  re-sabotaged in BOTH directions (2 failed / 4 passed each way).
  **B2 -- the two-channel drift class arriving for real:** `DOCS-01`'s channel-1 cell
  claimed the adopter's guide teaches six `make example-*` targets this phase DELETED;
  measured **0**. Only channel 1 was false; 114 green across both states.
  **B3 -- deferred item 9's three edits, owed to `23-13` BY NAME and unmade:** the
  ROADMAP goal prose still said *out of live CI*, STATE said *SIXTEEN criteria* and
  *25 of 31*. All corrected, marked inline.
  Plus THREE advisories FIXED (prose the move falsified), FOUR carried (deferred
  items 13-16), ONE recorded NOT NEW, and **FOUR REJECTED AS FALSE with their
  refuting commands kept** -- two of the four traceable to MY OWN payload omissions.
  **SIX LEGS AT EXIT 0 after the fixes**, every one in the foreground: lint 0;
  typecheck 211 files; test **4115 / 118 / 0** as four chunks proven three ways;
  gate-tools **415 + 341** (339 + the two new B1 controls, each named); examples one
  target three legs one address; docs-strict 0 on four steps. Coupling report
  regenerated LAST and verified TWICE.
  **`make ci` was AGAIN not run as one command** (~870s vs a 600s cap; backgrounding
  is what criterion 15 forbids) -- carried to Dave and **SINCE DECIDED**.
  **CORRECTED 2026-08-25 (post-gate): this line read *"CARRIED TO DAVE, NOT DECIDED."***
  `D-GATE-23` **BLESSES the chunked-foreground form** as an allowed satisfaction of
  criterion 15 on this host, under four conditions all met here: `make -n ci` proves
  the chunk list IS the full recipe; every constituent command runs FOREGROUND with its
  exit code recorded; the deviation is NAMED wherever it is used; and criterion 15's
  coverage proof is discharged. Expressly refused: backgrounding the whole pipeline and
  treating a kill as unknown-or-pass, claiming *"make ci green"* without naming the
  chunking, and silent substitution. **CRITERION 15's TEXT IS STILL OWED and NOT
  DISCHARGED** -- until that follow-up lands, `D-GATE-23` is the governing statement and
  a later phase inherits the reading from the gate entry, not from the criterion.
  **CLNT-17 hash `5bcc68ca...` equals the `efa0044` pin.** Sixteen criteria
  byte-identical to `PHASE_BASE`; 7 and 12 amended BY RULING at decision commits.
  **NEXT, as this line read BEFORE the gate: *"Dave's ruling. On approval -- and only
  then -- `D-GATE-23` is logged and `phase-23` merges `--no-ff` to `main` naming the
  entry."* THAT HAPPENED, and the push followed a day later on instruction.**
  **WHAT IS ACTUALLY NEXT: NOTHING IS IN FLIGHT AND THERE IS NO PHASE 24.** Do **NOT**
  run `complete-milestone` -- v0.2 is NOT done even though every ROADMAP phase reads
  checked. **THE OPEN-ROW FIGURE IS MEASURED HERE, and it CORRECTS a wrong number this
  session put in front of Dave before the file was touched.** A progress report earlier
  today said *"45 not-`Complete` requirement rows"*; **45 was produced by
  `grep -c "Not built\|Partial\|Pending" .planning/REQUIREMENTS.md`, which counts LINES
  CONTAINING those words -- including evidence prose that merely discusses a verdict --
  and is not a row count at all.** The instrument was wrong, not the ledger. Counted as
  rows: `grep -c "^- \[ \]"` = **13** open requirement bullets against **136** checked,
  and they are named rather than summarised -- `DOCS-03`, `DOCS-10`, `DOCS-11`,
  `DOCS-12`, `DOCS-13`, `DOCS-14`, `DOCS-17`, `DOCS-18`, `EXAM-01`, `EXAM-02`,
  `EXAM-03`, `DCD-02`, `CLNT-17`. **A SECOND INHERITED FIGURE IS CORRECTED WITH IT:**
  the frontmatter above says *"`DOCS-07`..`DOCS-19` remain undischarged"*; measured
  against the tree, `DOCS-07`, `-08`, `-09`, `-15`, `-16` and `-19` now read checked, so
  the surviving `DOCS-` set is the eight listed above. The frontmatter is left as
  written -- it is the record of the gate -- and this is the correction to it. And the
  27-item
  `.planning/phases/22.1-*/22.1-HUMAN-VERIFICATION-PACKET.md` is assembled and awaiting
  Dave. **THE PACKET AND THE TOOL DISAGREE AND THE PACKET IS THE AUTHORITY:** the packet
  says *27 items across 11 records*, while `gsd-sdk query audit-uat` returns **24 items
  across 9 files** -- it filters on record frontmatter status, so two records it cannot
  see are two records it reports nothing for, which is the `22.1` defect class arriving
  in the counter that measures `22.1`'s own output. Do not take the 24. **OWED AND UNSTARTED:** criterion 15's text; the DELETION half of `D-27`; the
  two `CLNT-17` framing questions, RAISED AND EXPRESSLY NOT RULED; `DOCS-14`/`EXAM-02`'s
  replacement surface; deferred items 7-10.
  **TWO DEFECTS WERE FOUND WHILE MAKING THIS CORRECTION, reported to Dave, deferred one
  commit, and are now BOTH FIXED. This paragraph is kept as the record of the sequence,
  updated rather than deleted.** (1) `## Project Reference` ABOVE read *"Current focus:
  **PHASE 19**"* and had done since Phase 19 -- through SEVEN closed phases. **FIXED**;
  the superseded paragraph is demoted there to *"Prior focus (Phase 19)"*. (2) Phase 23
  had a `## Phase Details` section and a progress-table row but NO BULLET in the
  ROADMAP's `## Phases` checklist -- the identical omission already recorded against
  Phase 17. **FIXED.**
  **A CLAIM MADE ABOUT (2) WAS WRONG AND IS WITHDRAWN HERE.** The commit that fixed it
  said *"`roadmap.analyze` reported 27 phases with Phase 23 INVISIBLE to it. Measured
  after: 28."* **THE BEFORE WAS NEVER MEASURED.** The 27 came from this file's own
  hand-written `progress:` block, not from the tool, and the refuting evidence is in the
  same tree: Phases 13.2 and 13.3 ALSO had no checklist bullet and `roadmap.analyze` saw
  both, so it reads the `### Phase ` DETAIL SECTIONS and a missing bullet never hid
  anything from it. The bullet was still owed; the reason given for it was not measured.
  **A SWEEP FOR THE SAME CLASS THEN FOUND FOUR MORE, ALL FIXED IN THE SAME SITTING.**
  The ROADMAP states its phase set in THREE places and this file in a FOURTH, and
  nothing compares any pair. Measured: **28** detail sections, **26** checklist bullets,
  **25** progress-table rows. (3) **13.2 and 13.3 had no checklist bullet** -- added,
  with their `D-IMPL-171` no-gate status named. (4) **13.2, 13.3 and 15.4 had no
  progress-table row** -- added; the table skipped 15.3 straight to 15.5. (5) **This
  file's `progress:` block was wrong in three of four fields** -- 27/27/204/204 against
  a measured 28/28/217/216. (6) **`22-06-PLAN.md`, Phase 22's CLOSE plan, has NO
  SUMMARY** while `D-GATE-22` is logged -- the close work was done, the artifact was
  never written; recorded, not manufactured. **[CLAIM SUPERSEDED 2026-08-25 and
  corrected in place by `23.1-06` under criterion 19, the finding-as-recorded preserved
  above: `22-06-SUMMARY.md` NOW EXISTS.]** `23.1-05` wrote it RETROACTIVELY from the
  Phase 22 close record, with its retroactive authorship stated in the file and with
  what it deliberately does NOT contain -- duration, per-task narration, deviations --
  named, because those are unknowable now. ROADMAP criterion 10, Outcome A. It was NOT
  written to make a counter agree, and the measurement says so: the plan figures read
  221 of 225 after the write and were still short.
  **AN EARLIER SPELLING OF THE (4) MEASUREMENT WAS ALSO WRONG and is named so the
  figure is not trusted on its first form:** it reported 15.5 and 15.6 as missing rows
  too, because the regex required a period after the phase number and those two rows are
  written without one. Re-measured with the period optional: 15.4 alone. **FIVE
  MEASUREMENT ERRORS IN ONE SITTING, EVERY ONE IN THE INSTRUMENT AND NONE IN THE
  MECHANISM** -- the 45-row grep, the `head`-exit-code check, the unmeasured 27, this
  regex, and the 27 propagated into a commit message. That is the standing lesson of
  this file's `B1`, arriving in the housekeeping that documents it.
  PRIOR -- the phase entry as discussed, preserved rather than rewritten:
Phase: **23 — The Archive Move: Retiring the Ten Condemned Example Trees Without
  Deleting Them (INSERTED).** ADDED 2026-08-24 by hand (`D-15`) at `efa0044`, **DISCUSSED
  2026-08-24, NOT PLANNED.** Performs `D-IMPL-189`'s archive-with-repoint as the allowed
  intermediate state for `DOCS-17`, which becomes **`Partial`** for the first time.
  **Scope was CORRECTED mid-sitting from TWELVE trees to TEN**, before planning and before
  any criterion was written, because Dave asked whether the `s1` pair was the client-side
  work just completed — it is not; that is `hw1-*`, and `s1-00` is the PREDECESSOR
  `hw1-companies-over-revenue` rebuilt. **`CLNT-17` is EXCLUDED and stays `Not built`.**
  **EIGHTEEN Success Criteria LOCKED at the sitting** (`D-GATE-19`, `D-IMPL-174`), each ONE
  LINE, verified sequential with zero continuation lines. **CORRECTED at the close,
  2026-08-25: this block said SIXTEEN.** Sixteen was the count when this paragraph was
  written; criteria 17 and 18 were AMENDED IN by `D-IMPL-194` before Wave 1, and the set
  has been eighteen for the whole of execution. Nothing gated the figure. Six rulings logged as
  `D-IMPL-190` and `D-IMPL-191`; **two AMEND `D-IMPL-189`** — point 1 (the paired tests
  STAY under `tests/`, so the **4105 / 118** baseline holds) and point 3 (the done-limb
  says *out of the `examples:` aggregate*, NOT *out of live CI*, because **19 of 31**
  `tests/examples` files still read the archived sources and 2 still execute them —
  **CORRECTED at the close, 2026-08-25: this block said 25 of 31.** `D-IMPL-195` ruling 3
  amended the figure to 19 and criterion 12 with it: the 25 was produced by a regex
  (`0[0-8]-[a-z]`) that matched inside `s1-00-companies-over-revenue` and the `hw1-`
  names. Wave 11 re-measured **19 at `PHASE_BASE` and 19 at `HEAD`**, so the superseded
  25 reproduced at neither end). Each
  amendment names the old clause and the new one per the `D-IMPL-188` policy.
  **Why this phase and not another:** it is the ONLY retirement work unblocked today.
  Both outstanding rulings govern DELETION — `D-27`'s `00`–`08` half is Dave's and
  undecided, and `D-IMPL-176` point 2 requires `DOCS-14`/`EXAM-02` first — and nothing is
  deleted here. It is also the first movement `DOCS-17` has had since it was minted, and
  clears **ten of the eleven** members of the always-on `examples:` job.
  **NEXT: `/gsd:plan-phase 23`.** Criteria are locked; do not author any retroactively.

**PRIOR POSITIONS FOLLOW — preserved, not rewritten.** The chain below is a
dated record of what was current at the time, the same discipline
`docs/DECISIONS.md` follows; corrections live in the entry above, never by
editing history.

Phase: **22 — The Adoption Argument: What RAG, Hand-Rolled Assembly and a Semantic
  Layer Lack (INSERTED).** ADDED 2026-08-23 by hand (`D-15`), **DISCUSSED AND PLANNED 2026-08-23 --
  SIX PLANS IN SIX SERIAL WAVES, READY TO EXECUTE.** Takes up the Phase 21 work list in the order `D-IMPL-176` sequenced
  it: *"DOCS-15 first -- cheapest, highest adoption leverage, one page, subject already
  gated in `s1-01`. Only coupling is that tree's survival under CLNT-17."* Fifteen
  decisions in `22-CONTEXT.md`; fifteen Success Criteria locked in the ROADMAP entry
  BEFORE planning per `D-GATE-19`. **The page is a Concepts page titled for the
  QUESTION, not for any rival** -- a title naming RAG would promise exactly the
  assertion `D-02` bars the body from making, and the new gate would then be policing a
  claim the title had already made. It cites `s1-01` for the UBO demonstration and the
  client surface (`ccf.client`, `hw1`) for the hand-rolled-assembly contrast, which is
  about the SEAM and not the graph; it adds NOTHING to the `00`--`08` trees' 102
  includes that `DOCS-17` must re-cut; and it is a declared `CLNT-17` DEPENDENCY --
  `s1-01` cannot be removed until this page is re-pointed or its demonstration
  re-homed, which lands mechanically as coupling rows owned by `17-08` rather than as a
  note somebody has to remember. Coverage is locked to a DEFAULT, not discussed: exactly
  the three alternatives `DOCS-15` names and no fourth, and the staleness claim rests
  only on what `s1-01` already measures -- `examples/s1-02-freshness-and-debt` is NOT
  invented here.
  **PLANNING CLOSED 2026-08-23 AFTER FOUR CHECKER ROUNDS AND THREE REVISIONS**
  (`8dfde2d`, `7c2432d`, `79e959d`, `00428f9`). Issue count fell 10 -> 8 -> 5 -> 0
  blockers; the loop never stalled, it hit its 3-iteration maximum with one blocker
  left and **Dave authorised one extra pass rather than force-proceeding**, ruling:
  *"Handing the executor a named instruction is exactly an unwatched condition... Do
  not force-proceed with a known hole in the module that refuses ungrounded claims."*
  **EVERY BLOCKER THE LOOP FOUND WAS IN THE PROOF MACHINERY, NEVER IN THE PAGE** --
  the phase's own defect class, four times, in the phase whose subject is honest
  citation. (1) The `debt-profile.yaml` include fails `make docs-strict`: 15
  `pub01-whitepaper-shingle` findings against 0 on every include the page keeps,
  because the file quotes the whitepaper and the scan reads the RENDERED site with
  tags stripped and no allowlist. Dropped; `expected.yaml`'s declared `debt_signal_*`
  and `debt_weak_factor` carry criterion 11 instead. (2) The coupling report stales
  the moment the page is written and `test_the_committed_report_is_current` runs in
  WAVE 1 -- and the terminal byte-identical assertion would have stopped the last
  plan ON A CORRECT TREE, demonstrated live when the planner's own edits moved
  exactly two `.planning/` row counts. Replaced by a diff CONFINED to
  `.planning/STATE.md` and `.planning/phases/22-*`. (3) `CAVEAT_CONTRACT` was matched
  against `Paragraph.text`, which `strip_markup` strips of backtick code spans --
  `.raw` sees 10 `D-IMPL-NN` paragraphs, `.text` sees 6 -- so the floor proving
  non-vacuity was itself vacuous and would have gone RED on a correct page. (4) **THE
  GATE REFUSED THE CAVEAT CRITERION 6 REQUIRES**: `sentences_claiming_passage_extraction`
  flagged *"no shipped pipeline produces passage anchors from documents"* as an
  offender, because it matched the SHAPE of an extraction claim without reading
  whether the sentence asserts or denies it. The denial-exemption limb that fixes it
  then had a hole of its own -- a denial at offset 0 exempted the whole sentence, so
  *"No shipped pipeline produces passage anchors, though CCF does extract them from
  documents"* passed clean. **THE LIMB NOW HAS THREE CONDITIONS AND THREE MUTATIONS,
  ONE PER CONDITION**: vocabulary, ordering, and a contrastive pivot between the
  denial and any later extraction verb. Measured, not argued: both smuggle sentences
  flip to REPORTED, the criterion-6 caveat stays EXEMPT (`so` is not a pivot), and
  across all 43 published pages **0 paragraphs change verdict**.
  Final shape: **6 plans, 6 serial waves**, `22-06` NON-AUTONOMOUS carrying the
  CLAUDE.md §3.1 close on the `21.1-10` precedent -- a separate plan rather than a
  task so the counter reads 5/6 and a finished `22-05` cannot READ as a finished
  phase. `22-03` ships 7 non-vacuity floors, 11 controls, 7 sabotage runs across 9
  mutations. Coverage 15/15 criteria and 15/15 `D-NN` in frontmatter `must_haves`.
  `src/`, `runtime/` and `examples/` absent from every `files_modified`.
  **CARRIED, NOT BLOCKING (checker W-1, worth closing before wave 6):** `22-06` task
  1 has no floor requiring that ANY reviewer succeeded -- a record honestly reading
  "codex FAILED, cursor FAILED, gemini FAILED" satisfies all eight checks and records
  eight PASSes. The phase's own check-vacuity class, inside the plan written to gate
  it. Mitigated only by the blocking checkpoint that follows, which is the
  reviewer-diligence pattern §3.1 rejects.
  **BRANCH RULED BY DAVE 2026-08-23, BEFORE EXECUTION: NO PHASE BRANCH. EVERYTHING
  ON `main`.** Verbatim: *"put everything on main now before I execute the phase."*
  This is a deliberate departure from CLAUDE.md §2.2, which puts phase work on a
  phase branch with the merge at `D-GATE-<Phase>` -- Phase 22 has no `phase-22`
  branch and will have no merge commit referencing `D-GATE-22`. A later reader must
  NOT read the missing branch as an error. Planning was pushed at `10046cb`;
  `main` == `origin/main`, 8 commits, planning artifacts and the regenerated coupling
  report ONLY -- `src/`, `runtime/` and `examples/` absent from the whole range,
  verified by name before the push.
  **STILL OPEN AND OWED TO DAVE:** (a) checker W-1 above -- `22-06`'s panel gate
  passes on an all-FAILED reviewer record. (b) The
  criterion 3 / criterion 8 reading for the prose-cited client seam is STATED in the
  page, the `DOCS-15` ledger cell and the phase record, each with a STOP if it reads
  as a widening -- deliberately not decided, per `D-10`: *"a scope question for Dave,
  not a quiet widening."*
  Next action: `/gsd:execute-phase 22`.

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

---

**2026-08-26 session resume.** Phase 24.1 is EXECUTING on branch `phase-24.1`,
**waves 1-5 of 11 complete**, tree clean at `010b854`, nothing in flight, no
checkpoint and no `HANDOFF.json`. Waves 6-11 have PLANs and no SUMMARYs — that is
the expected shape mid-phase, not an interrupted execution. The `consume.py` ->
`run.py` rename `24.1-05`'s summary left owed against plans 06/07/08/11 was
DISCHARGED at `010b854` (8 occurrences patched, **0 remain**, verified by grep on
all four files at resume). Dave's 2026-08-26 rulings `D-54..D-62` are appended to
`24-CONTEXT.md`: the threshold-and-batch rule for when an SDK gap gets closed
(`D-54..D-58`), no `issuer_match_band` filter (`D-61`, so Wave 6 does not restore
one), and **Wave 6 additionally owns the spec residues** (`D-62`) — no orphan
`[TBC]` cell survives it.

Carried, unclosed by design (`D-04`): **FOUR** SDK-side findings recorded and none
closed. **CORRECTED 2026-08-27 — plan `24.1-09` caught this block naming the fourth
member wrongly, and it was the orchestrator's error, not an executor's.** The four are:
(1) Wave 3's **empty-operator gate is two different assertions sharing one name** — the
SDK's refuses a product that *declares* no operators, the Standard's refuses an operator
that *returns* an empty set (spec §F.4 item 4; any SDK-side fix would be a FOURTH gate,
forbidden by `D-IMPL-102` limb 3); (2) Wave 4's `ProductClassDeclaration` MAX_TTL-seconds
slot; (3) Wave 5's `build_operator_registry` type-dispatch (`D-59`); (4) Wave 5's
`ContextAssemblerProtocol.assemble` return type (`D-60`). **SUPERSEDED, NAMED RATHER THAN
DELETED:** this block previously listed *"the CI `run.py` gate finding now discharged by
`D-51`"* as the fourth. That finding was DISCHARGED and was never SDK-SURFACE, so counting
it kept the total right by luck while naming the wrong member. The authority is
`24.1-PRESSURE-TEST.md` §4.1/§4.3 and `D-IMPL-212`. Per
`D-54..D-58` the batchable pair (assembler-refusal-as-data + deployment operator
registration) opens as a SHORT SDK phase AFTER cp-00 is green — not inside 24.1.

Resume: `/gsd:execute-phase 24.1` (wave 6 next)

---

**2026-08-28 session resume (evening).** Phase 24.1.1 is CLOSED, merged to `main`
`--no-ff` and pushed (`D-GATE-24.1.1`, `2367da0`). Tree clean. **One UNPUSHED
commit: `633d3ad`** — `EXAM-06`'s third clause, minted as `D-IMPL-218` in both
ledger channels. Push is UNRULED; it was offered at the end of the prior sitting
and Dave asked to save state instead. No `HANDOFF.json`, no `.continue-here`, no
PLAN without a SUMMARY, no interrupted agent, zero pending todos.

**`## Current Position` above is STALE** — it still reads *"PHASE 24.1 IS
EXECUTING... WAVE 11 IS THE ONLY THING LEFT"* when 24.1 and 24.1.1 are both
closed. The frontmatter `last_activity` is current; the prose section was not
rewritten at the 24.1.1 close. Flagged to Dave at resume, not silently rewritten.

Three things owed, carried from the prior sitting:
1. Rule on pushing `633d3ad`.
2. **The 2026-08-28 15:27 analysis is on disk NOWHERE** — the tier-1
   buildability findings and which product is CP #1 exist only as a one-line
   trace in the session-memory daily file. No candidate-set document exists in
   `.planning/`. Dave must restate before the next product is built.
3. **Mint the per-request-assembly rule as a real `D-IMPL`.** *"Context products
   are assembled per request, never precomputed"* is cited by `D-IMPL-218` but
   lives only in `.planning/FUTURE-CONTEXT-PRODUCTS.md`, a file whose own header
   reads NOT SCHEDULED / placeholder. That is why it was miscited as
   `D-IMPL-137` once.

**Nothing is scheduled after 24.1.1.** Phase 24 is an umbrella whose entry is
DESCRIPTION BANKED, NOT PLANNED with no success criteria by design (`D-GATE-19`
binds criteria to the discuss sitting). The next unit is a discuss sitting for
the next rung of the Context Production ladder.

Resume: `/gsd:discuss-phase 24.2` (after Dave restates the CP candidate analysis)

---

**2026-08-28 save-state (19:00, at Dave's request before clearing).**

**Where we are: the estate was surveyed end to end, and the ladder's first rung is
NOT build-ready.** Nothing has been built this session; it was all reconnaissance,
and it changed the answer to "what do we build next."

**What was produced.** `.planning/CONTEXT-PRODUCT-LADDER-AND-ESTATE.md` (~460 lines)
— the durable copy of the analysis that died with the cleared session on the 28th.
It carries: the vault's **21 CB/CIB Context Product specs in five-tier
simplest-first order**; the five-store estate topology (Postgres `ccf_v2`, Fluree
`fibo-v2`, MongoDB `fibo_v2`, departmental SQLite, optional Neo4j — all on
`192.168.4.76`); a **live census** of every store; each product's §C store
assignment; and which products are empirically probed versus merely asserted.
Two memory files plus a third on the check-scoping lesson.

**THE HEADLINE, and the reason not to start building blind:**
`counterparty-reference-snapshot` — the rung the vault says to start on — carries
**THREE VERIFIED GAPS**, all confirmed by direct query, not read off a report:
1. **Addresses**: §B requires headquarters AND legal; only ONE address triple exists
   and **nothing records which of the two it is**. Fetchable from the GLEIF Level 1
   file already in use — not a source limitation.
2. **No-LEI entities: ZERO** of 156. This is the spec's own §D counterfactual
   realised — *"an LEI-only anchor silently excludes privately-held middle-market
   borrowers, and every downstream product inherits the exclusion."* The predecessor
   manifest marked it `COVERED` against crosswalk floors **every one of which is
   keyed on LEI**, so they were structurally incapable of seeing the absence.
3. **Entitlement scope by jurisdiction**: `principal` has 4 rows and **no
   jurisdiction column at all**, so the T1 Policy Operator has nothing to filter on
   — in the product every other product inherits its contract machinery from.

**`ccf_dataprep` repaired both defects this survey found** (`96b88ae`
family-tree population + a second miscount defect; `cf03d28` counterparty manifest
re-derived, ten mappings to four). **Dave owns that repo — read from it, never write
to it.** The full `spec_coverage.py` run now completes: **129 of 280 catalog rows
accounted for**, 151 unchecked, all inside the 12 products that have no manifest.
`rc=1` is the designed state while a `GAP` stands.

**CIK SURVIVED the vault's §C collapse** — folded into the crosswalk probe, which
now requires `lei` + `internal_client_id` + `cik` on one row (53 rows do). The
outstanding ruling shrank to **SIC code, internal obligor risk grade, coverage RM
assignment**, which the estate holds and no spec now asserts.

**ONE CORRECTION ON THE RECORD, mine.** This document first claimed all three T1
specs were *"fully backed."* That was reached by checking the named COLUMNS exist —
a weaker test than element satisfaction, which cannot see a required element with
zero rows, a missing distinction between two values sharing one column, or a missing
column on a different table. Corrected in place with the reason stated. Same class
as the family-tree probe defect: **a check whose population is not its question.**

## Next — Dave's call before anything is built

1. **RULE ON THE FIRST RUNG.** Close counterparty's three gaps (two are
   `ccf_dataprep` generation tasks, one is a fetch) and build it, **or** start on a
   different rung. `facility-terms-snapshot` and `obligor-financial-spread` are the
   alternatives and are **UNPROBED** — nobody has looked, so "clean" is not
   available as a claim about either.
2. **Rule on SIC / risk grade / RM assignment** — waive, keep as extra, or ask the
   vault custodian whether the collapse was deliberate. A draft question to the
   custodian was offered and not sent; `~/.agent-exchange/` is the channel and
   nothing goes without Dave seeing it.
3. **Then** discuss-phase for the chosen product. `D-GATE-19` binds criteria to the
   discuss sitting — none are written in advance.

**Dave's standing instruction for that build: PAUSE AFTER IT IS BUILT so he can
evaluate.** Do not close a phase around it.

Resume: read `.planning/CONTEXT-PRODUCT-LADDER-AND-ESTATE.md` §6.1.1 and §7 first.

---

**2026-08-28 save-state (19:06) — RESUME HERE.**

**THE BUILD ORDER IS RULED AND IS NOT REOPENABLE ON READINESS GROUNDS**
(`D-IMPL-219`, Dave, 2026-08-28). Context Products are built in the vault's
**complexity order**, simplest-first across the five-tier ladder. **The next
product is `counterparty-reference-snapshot`** — rung 1. The executing model
proposed `obligor-financial-spread` instead because its data was richer; Dave
refused, and the refusal is the point: *which* product is next is fixed by
complexity, *when* it can be built is a data question answered by loading data,
never by promoting a better-supplied product over a simpler one.

**BLOCKED ON DATAPREP, BY DESIGN.** Rung 1 has three verified gaps (all confirmed
by direct query 2026-08-28, all in §6.1.1 of
`.planning/CONTEXT-PRODUCT-LADDER-AND-ESTATE.md`):
1. **Jurisdiction entitlement — THE ONE THAT MATTERS.** `ccf_v2.principal` has 4
   rows and **no jurisdiction column at all**. §B defines T1's whole policy
   binding as *jurisdiction visibility per calling principal*, so today the Policy
   Operator would be a **no-op** — in the product every other product inherits its
   contract machinery from. Building around this would reproduce the exact
   "aggregate, not assemble" criticism that commissioned Phase 15.5.
2. **No-LEI entities: ZERO of 156.** The spec's own §D counterfactual realised.
3. **Second address.** §B requires headquarters AND legal; one triple exists and
   nothing records which it is. Fetchable from the GLEIF Level 1 file in use.

**Dave confirmed 19:06 that `ccf_dataprep` is addressing all three now.**

## On resume, in this order

1. **Verify the gaps are actually closed — do not take the word for it.** Re-run
   `cd /home/parkave/ccf_dataprep && .venv/bin/python validators/spec_coverage.py
   --product counterparty-reference-snapshot`. It must show **4 PASS, 0 GAP**;
   today it shows 1 PASS, 3 GAP. Then re-derive independently rather than trusting
   that output: `principal` carries a jurisdiction column with **differing** values
   across principals (a column of one repeated value satisfies the count and not
   the condition), `legal_entity` holds rows with a NULL lei, and the two addresses
   are **distinguishable** rather than merely two columns.
2. **Then build rung 1.** `D-GATE-19` binds success criteria to the discuss
   sitting, so criteria are written there and never in advance.
3. **PAUSE WHEN IT IS BUILT.** Dave's standing instruction, 2026-08-28: *"We will
   pause after it's built so I can evaluate."* No close panel, no `D-GATE`, no
   completion mark in `ROADMAP.md` or `STATE.md` until he has evaluated it.

**Still unruled, and smaller than it was:** SIC code, internal obligor risk grade
and coverage RM assignment are held by the estate and asserted by no spec after the
vault's §C collapse. **CIK survived** — dataprep deliberately kept it inside the
crosswalk probe (`lei` + `internal_client_id` + `cik` on one row, 53 rows do)
because `LEI → CIK → ticker` is a join six other specs depend on. A question to the
vault custodian about whether the collapse was deliberate was **drafted and NOT
sent**; `~/.agent-exchange/` is the channel and nothing goes without Dave seeing it.

**Two vault log entries exist for this session**, the second correcting the first:
the original claimed all three T1 specs were "fully backed" and called the
`spec_coverage` crash a reworded row. Both were wrong and both are corrected on the
record (`output/_inbox/2026-08-29T02-01-08-ccf-sdk-a84c0986.md`).

**`ccf_dataprep` IS DAVE'S — read from it, never write to it.**

Resume: verify the three gaps, then `/gsd:discuss-phase` for rung 1.

---

**2026-08-28 save-state (20:45) — RESUME HERE. RUNG 1 IS NOW BUILD-READY.**

**All three of `counterparty-reference-snapshot`'s gaps are CLOSED and were
verified here against the live store, not read off `ccf_dataprep`'s report.**
`validators/spec_coverage.py --product counterparty-reference-snapshot` now
reports **4 of 4 catalog rows accounted for, zero `GAP`** (it read 1 PASS / 3 GAP
at the start of this sitting). Full evidence in
`.planning/CONTEXT-PRODUCT-LADDER-AND-ESTATE.md` **§6.1.2**.

- **Addresses** — `465ba4d`. `legal_address_{country,city,region}` **and**
  `hq_address_{country,city,region}`; 153 of 156 loaded from GLEIF L1 at
  city/region; **69 differ** (65 under case normalization — see below). The three
  without an HQ are **proven by set equality in both directions** to be exactly
  the ABS trusts `SYN-SDART-2022-6`, `SYN-SDART-2024-1`, `SYN-TAOT-2022-B`.
- **Entitlement** — `principal_jurisdiction`, 17 rows. **All six principal pairs
  discriminate**, tested as visible-set inequality with a negative control, not as
  column presence. RES 102 / COV 74 / KYC 21 / TRD 21 visible of 156. The Policy
  Operator is **not** a no-op.
- **No-LEI identity** — `internal_client`, 30 rows, `synthetic — internal` per
  **`D-IMPL-220`**; `crosswalk.lei` nullable with 30 null rows, zero orphans; KYC
  ceiling fields present so §G's freshness-asymmetry criterion is testable.

**ONE FINDING OWED TO `ccf_dataprep`, not yet passed on.** Of the 69 differing
addresses, **four differ only by letter case** — `AMPHENOL CORP /DE/`,
`HNA ACQUISITION ULC`, `MURPHY OIL COMPANY LTD.`, `VML US FINANCE LLC`
(`WILMINGTON`/`Wilmington`, `EDMONTON`/`Edmonton`, `CALGARY`/`Calgary`). Under
`lower(btrim(…))` it is **65 of 153**. The conclusion is untouched at 42%, but the
distinguishability assertion their remaining validator will carry must normalize,
or it scores one address typed twice as two addresses.

**A CORRECTION ON MY RECORD, in §6.1.2.** I argued the on-disk HQ data could not
close the address gap, on a 9-of-140 (6%) measurement taken from
**`registry_company` at country granularity** — a different table from the one
dataprep had loaded, which is GLEIF L1 at city/region where the figure is 69 of
153. A claim about the estate built from the wrong table. I also "corrected" 50
fetchable anchors to 53 by arithmetic without checking what the three were; they
are the ABS trusts, and 50 was right. Same class as §6.1.1 and §6.2 — **a check
whose population is not its question.**

## Next

1. **Build rung 1** — `counterparty-reference-snapshot`. `D-GATE-19` binds success
   criteria to the discuss sitting, so criteria are written there and **never in
   advance**. Resume: `/gsd:discuss-phase` for rung 1.
2. **PAUSE WHEN IT IS BUILT.** Dave's standing instruction, 2026-08-28: *"We will
   pause after it's built so I can evaluate."* No close panel, no `D-GATE`, no
   completion mark in `ROADMAP.md` or `STATE.md` until he has evaluated it.
3. Pass the case-normalization finding to `ccf_dataprep`.

**Still unruled:** SIC code, internal obligor risk grade and coverage RM assignment
are held by the estate and asserted by no spec after the vault's §C collapse. A
question to the vault custodian was **drafted and NOT sent**; `~/.agent-exchange/`
is the channel and nothing goes without Dave seeing it. `EXAM-06` still has exactly
**two** open clauses (reproduce-or-link; whether the *"which file is the SDK's?"*
reveal is every example's or `cp-00`'s alone) — the snapshot clause is RULED at
`D-IMPL-218`, not open.

**`ccf_dataprep` IS DAVE'S — read from it, never write to it.** Held all session;
every figure above came from a read-only query.

Resume: `/gsd:discuss-phase` for rung 1 (`counterparty-reference-snapshot`).

---

**2026-08-29 save-state (09:12) — RESUME HERE. cp-01 IS DONE; THREE ITEMS ARE OPEN.**

**Phase 24.2 / `cp-01-counterparty-reference-snapshot` is BUILT, TESTED,
DOCUMENTED, PUBLISHED AND PUSHED.** `origin/main` = `467e62f`, tree clean.

- **13 tests** in `tests/examples/test_cp_01_output.py`, all passing against a
  seeded container.
- **8 product gates, each observed FAILING once.** `CPR-G01`–`G07` and `CPR-G09`
  were deliberately sabotaged and watched go red, then restored.
- **Documentation page** at artifact `6edeeba9-5266-44b0-a76e-b6119a64799d`
  ("Counterparty Reference Snapshot · cp-01"). cp-00's is
  `66047673-7537-4d21-addf-51f67b33f132` — note a **duplicate-titled decoy** sits
  at `c0f12122-aafb-441f-91f5-efc62184889f`.
- **Page generators committed and proven byte-identical** to the published pages,
  with the placeholders proven LIVE by planting a sentinel. Rendered HTML is
  gitignored; `python examples/cp-NN-*/page/build_page.py` reproduces it.

## THREE THINGS OPEN — to be tackled on return

1. **`EXAM-06`'s ledger row still reads "Not built for any example but `cp-00`"**,
   in BOTH channels — `.planning/REQUIREMENTS.md` line 74 (checkbox) and line 323
   (traceability table). cp-01's page now exists and the row is stale.
   **Held deliberately**: Dave wanted to read the page before the row claims it.
2. **`cp-01` is not wired into `make ci`.** Its 13 tests run nowhere
   automatically, so nothing catches a regression in the example. Related:
   `CPR-G08` has **no instance in the data** — every principal sees at least 21
   entities, so the empty-served-set refusal cannot fire. Registered at spec
   §F.2 row 20, owned by `ccf_dataprep`, and it is a one-row fixture rather than
   a data programme.
3. **`.planning/STATE.md` LOST 835 LINES (against 23 inserted) TO SOMETHING NOT
   DELIBERATELY RUN**, at ~09:05 on 2026-08-29. No `state.*` writer, no GSD
   command, no hand edit. Caught only because the diff was read before staging an
   unrelated commit; restored with `git checkout --` and kept out of that commit.
   **CAUSE UNKNOWN.** Candidates not ruled out: a SessionStart or other hook, the
   `remember` skill run minutes earlier, or a background GSD process.
   **Why it is worse than the known hazard:** the standing mitigation assumed a
   writer had been INVOKED. This instance had no invocation, so "do not call
   `state.*` writers" is insufficient. **Run
   `git diff --stat .planning/STATE.md` before EVERY `git add`**, not only after a
   GSD command. A 2,268-line file dropping to ~1,400 is the tell.

Resume: read the three items above; item 1 is a two-line ledger edit once Dave has
read the page, item 2 is a CI wiring change, item 3 is an investigation.

---

## Session resume — 2026-08-29 (cp-01 evaluated, process captured)

**HAND-EDITED APPEND. Verified below as insertions-only before staging** — this
file lost 835 lines earlier the same day to something nobody invoked, and the
mitigation is to diff before every `git add`, not to trust that no writer ran.

**`origin/main` = `6ef9815`.** Seven commits this session, all pushed and each
verified against GitHub with `git ls-remote`, never against the local ref.

### DAVE EVALUATED cp-01 AND IT PASSED, ON HIS OWN MACHINE

His stated criterion: *"the success criteria is for me to validate the examples
run and produce the expected output."* He ran four variations himself and each
matched the published run **byte-for-byte**, content address `ab2e1a62…` on the
baseline. **Phase 24.2's product is validated.** What that does NOT settle: the
phase has no `.planning/phases/24.2-*` directory and no `24.2-CONTEXT.md`, so it
has **no Success Criteria**, and `D-GATE-19` forbids writing them retroactively.
How 24.2 gets recorded is unruled and is Dave's.

### HE COULD NOT RUN IT AT FIRST, AND EVERY REASON WAS A REAL DEFECT

Not one was user error, and the fixes are now the process:

1. **Cursor was open on `/home/parkave/ccf` — a DIFFERENT repository**
   (`drcastillo/ccf`, the whitepaper repo, branch `master`, no `examples/`).
   Two repos one suffix apart.
2. **The README said bare `python`.** There is no `python` on `PATH` here.
3. **`make venv` DID NOT EXIST.** `PYTHON := .venv/bin/python` is a path and
   nothing in the repository ever created it.
4. **`make example-cp-01` did not exist.** cp-00 had a target; cp-01 did not.
5. **A pasted command carried a NON-BREAKING SPACE**, so bash reported
   `' export'` not found.

**A HANDOFF CLAIM WAS WRONG AND WAS CORRECTED BY MEASUREMENT:** cp-01's 13 tests
were recorded as running "nowhere automatically." They ran in CI the whole time —
`leg-postgres` selects `pytest.mark.postgres` **by marker** over the whole `tests`
tree, and `ci.yml:224` runs it always-on.

### SHIPPED THIS SESSION

- **`make venv`** and **`make example-cp-01`**, `.PHONY`-declared, in `make help`
- **cp-01 README rewritten** — venv first, make target, `-s`, and the two
  variations that exit non-zero *on purpose*
- **`summary_explanations.md`** (511 lines) — **Dave presents from this to
  BANKERS.** Glossary, seven runs, a *"what you'd have missed"* per run
- **US English** as a `CLAUDE.md` Working Principle, with identifiers, quoted
  source and **verbatim program output exempt**
- **`public/reference/specifications/example_delivery.md`** (403 lines, in nav) —
  the delivery recipe for every future Context Product
- **`spec_generation.md`**: §7.2 diagram unstaled, §8 retitled, **ownership seam
  marked — it stays the VAULT's**, §7 the named exception

### FINDINGS RAISED, NOT RESOLVED

- **`make docs-strict` IS RED ON `main`** — 17 findings, ALL the authoring
  standard's page tripping `pub01-whitepaper-shingle`. Arrived with `2709a39`.
  **Attributed by reverting to a clean HEAD and re-running**, where it fails
  identically. `docs-strict` is in `make ci`. **Unowned.**
- **`cp-01`'s spec writes `Failure behaviour`** where the Standard and `cp-00`
  both write `Failure behavior`. **My build diverged**, and the spec was Gate-1
  approved, so the fix is Dave's to authorize.
- **`CPR-G08` still has no instance in the data** — needs one principal granted
  nothing; that row is `ccf_dataprep`'s.
- **`EXAM-06`'s ledger row is stale in BOTH channels** (L74, L323) and its "two
  clauses stay OPEN" sentence is now false: cp-01 answered both by DEFAULT —
  reproduced the README, omitted the reveal. Unruled.
- **cp-01's published page is STALE** — it reproduces the pre-rewrite README and
  does not know `summary_explanations.md` exists.
- **`.planning/STATE.md`'s 835-line deletion is still unexplained.**

### THE VAULT HAS TWO MESSAGES WAITING

`~/.agent-exchange/ccf-sdk/outbox/` — the ownership proposal with the diff
attached, and **a correction to it**: the first message claimed to have removed
four lines of §7.2 and had removed two, with its own attached diff disagreeing
with its prose. Corrected by a second message rather than by editing a published
one.

### NEXT

**Rung 2 — `facility-terms-snapshot`.** *"How does a product anchor on something
other than a legal entity? Demonstrates the `from_entity_freshness` TTL anchor."*
**That anchor is exactly what cp-01 shipped a documented defect in** — `CPR-G09`,
a 24-hour TTL over a months-old `kyc_last_refresh`, 30 of 30 no-LEI counterparties
refusing, and the test **goes RED when the defect is fixed**.

Read `example_delivery.md` before building it. That is what it is for.

Resume: nothing is half-done. The tree is clean, everything is pushed, and the
next action is Dave's choice between ruling on the open items above and starting
rung 2.
