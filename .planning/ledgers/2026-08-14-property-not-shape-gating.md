# SDD ledger — plan: docs/superpowers/plans/2026-08-14-property-not-shape-gating.md

Branch: `phase-16` (not main; phase work belongs here per CLAUDE.md §2.2)
Base at start: `8169b56`

Tasks:
1. Gate 1 — role discovery and the region properties (P1–P4)
2. Gate 1 — printing properties and the scope predicate (P5, P6)
3. Gate 2 — the premise detector
4. Gate 2 — conditioning the demand, and the ceiling
5. Gate 2 — the row-B and row-C controls
6. Record D-IMPL-137 and verify the phase

Progress:
Task 1: dispatched (sonnet), BASE dcb76d3 — brief task-1-brief.md, report task-1-report.md
Task 1: implementer DONE_WITH_CONCERNS, commit 208c0d9 (16 passed, 2 failed = the
  two parametrizations of the Task-2-owned printing test; correct end state)
Task 1: controller-confirmed gap — module docstring lines 1-28 still declare the
  two-filename contract ("spine.py holds every call ... deployment.py holds
  everything the adopter writes") which the code no longer enforces. Enters the
  fix loop with the reviewer's findings.
Task 1: task reviewer dispatched (sonnet) over dcb76d3..208c0d9
Task 1: review verdict — Spec OK, Task quality Approved. 1 Important (plan-mandated
  duplication of the missing/extra derivation), 2 Minor.
Task 1: RULING (Dave, 2026-08-14) — extract `region_report(spine)`; the extraction
  governs over the plan's literal Step 4/Step 5 code. Authorized plan deviation.
Task 1: minor (deferred): redundant parenthesis wrapping at ~line 236
Task 1: minor (deferred): `region_modules(...)[0]` indexed without a defensive
  check; P1 test asserts non-emptiness first, so cosmetic
Task 1: fix round 1/5 dispatched — (a) region_report extraction, (b) module
  docstring lines 1-28 still declare the two-filename contract
Task 1: fix round 1/5 implemented, commit 95ea18d (end state unchanged: 16 passed,
  2 failed = the Task-2-owned printing test). Implementer DISPUTES the reviewer's
  "wording drift" sub-claim — says messages were already consistent. Re-review
  dispatched (sonnet) over 208c0d9..95ea18d to adjudicate that specifically.
Task 1: fix round 1/5 (2 addressed, 0 open; commits 208c0d9..95ea18d)
Task 1: NOTE — the reviewer's "wording drift" sub-claim was FALSE. Re-review
  verified the two message families were already byte-identical apart from the
  P2 test's deliberate `{directory.name}/` prefix. Implementer's dispute upheld.
Task 1: complete (commits 208c0d9..95ea18d, review clean)
Task 2: dispatched (sonnet), BASE 95ea18d — brief task-2-brief.md, report task-2-report.md
Task 2: implementer DONE, commit 3249335. CONTROLLER-VERIFIED independently:
  `22 passed in 0.09s`, zero failures; `git status --short examples/` empty.
  GATE 1 IS GREEN — 16 of the phase's 18 failures closed, no example modified.
Task 2: task reviewer dispatched (sonnet) over 95ea18d..3249335
Task 2: review verdict — Spec OK, Task quality Approved, 0 Critical, 0 Important.
  Both flagged checks verified: all 4 control substrings match their predicate's
  actual message text; PRINT_RE.sub neutralises every print (no count arg).
Task 2: complete (commits 95ea18d..3249335, review clean)
Task 3: dispatched (sonnet), BASE 3249335 — brief task-3-brief.md, report task-3-report.md
Task 3: implementer DONE, commit f6bdb8c. 70 passed / 2 failed, the 2 unchanged
  (both s1-00/produce.py, Task 4 closes them). Detector reproduces the
  pre-confirmed measurement exactly: exempt = ['examples/s1-00-companies-over-revenue'],
  10 registering deployments.
Task 3: task reviewer dispatched (sonnet) over 3249335..f6bdb8c, with 4 named
  checks: _deployment_root boundary cases, the registration regex vs the $schema
  comment, row-C behaviour, and multi-plan aggregation in one body.
Task 3: review verdict — Spec OK but Task quality NEEDS FIXES. 1 Important
  (plan-mandated), 2 Minor. All four named checks passed on direct execution.
Task 3: CONTROLLER-VERIFIED DEFECT — `_one_document` returns True for a body with
  no artifact tree. Reproduced: deployment_root None -> registers False -> falls
  through to the AST checks -> True. `_registers_requirements(None)` being False
  means the guard never fires. This is a PLAN BUG: spec §4.4 and the brief's own
  prose both mandate fail-closed on a missing tree; only the code sample was
  wrong, so the plan contradicted itself and the prose governs. No human ruling
  needed — both readings agree the code is wrong. Plan file corrected too.
Task 3: second real defect — test_a_body_with_no_artifact_tree_is_subject_to_the
  _demand asserts only the two helpers in isolation, never calls _one_document.
  It does not test the composition it is named for, which is why the defect
  survived a green suite.
Task 3: REQUIREMENTS_CLASS_ID confirmed dead (defined line 400, zero references).
Task 3: minor (deferred): _deployment_root iterates its nearest candidate twice
  ((path.parent, *path.parents); parents[0] IS path.parent). Harmless.
Task 3: fix round 1/5 dispatched — (a) fail-closed on root is None, (b) make the
  test exercise _one_document with a body that would otherwise be exempt,
  (c) build the regex from the constant so the dead name goes live.
Task 3: fix round 1/5 implemented, commit c6e0e00. 70 passed / 2 failed unchanged;
  detector measurement unchanged. Implementer PROVED the rewritten test would have
  caught Finding 1 — reverted to the buggy guard and confirmed the new assertion
  fails. That is the right proof and I asked the re-review to verify it.
Task 3: plan text corrected and committed separately (fa76deb) — not part of the
  fix diff, so the re-review is not judging it.
Task 3: re-review dispatched (sonnet) over f6bdb8c..c6e0e00, with one named check:
  that the synthesized body in the rewritten test would genuinely have been exempt
  but for the missing artifact tree (else the test passes vacuously).
Task 3: fix round 1/5 (3 addressed, 0 open; commits f6bdb8c..c6e0e00)
Task 3: complete (commits 3249335..c6e0e00, review clean)
Task 4: dispatched (OPUS — highest-risk task: conditioning that could silence
  controls, plus judgment-heavy docstring surgery), BASE fa76deb.
Task 4: BRIEF CONFLICT RESOLVED BY CONTROLLER — task-4-brief.md still carries the
  pre-flight inline version of test_the_one_document_exemption_has_not_spread,
  while task-5-brief.md carries the corrected `_exemption_problems` predicate form
  and says Task 4 must expose it. The briefs were extracted after the pre-flight
  edit but that edit landed the new code in Task 5's section only. Dispatch tells
  Task 4 the predicate form governs.
Task 4: CONTROLLER-ADDED INSTRUCTION not in the brief — the 350-line module
  docstring states the demand as unconditional and becomes false with this change.
  Six specific points enumerated in the dispatch, incl. adding the conditioning to
  the limits list and NOT claiming R-3 is narrowed.
Task 4: implementer DONE_WITH_CONCERNS, commit 9b09910. CONTROLLER-VERIFIED:
  95 passed across BOTH gates, 0 failures. THE PHASE'S 18 FAILURES ARE CLOSED.
  This plan changed exactly 3 files: the plan doc + the two test modules.
  `git diff --stat 8169b56..HEAD -- src/ runtime/ examples/` is EMPTY.
Task 4: MINIMUM_PROJECTING_BODIES re-measured 11 -> 13 (11 construct-and-execute
  + 2 replay resolve_plan). Old comment "nine ... plus two" was two short.
Task 4: controls verified by MUTATION, not by passing — forcing demanded=False
  makes reject_a_binder_that_cannot_fail FAIL. Property (1) confirmed still firing
  inside the exempt deployment: absence of demand, not a licence.
Task 4: CORRECTION TO MY OWN EARLIER CLAIM — detects_a_projection_that_skips_it
  does NOT route through _one_document/_binder_collapses; it asserts
  _names_the_binder directly, so the conditioning cannot silence it. The control
  the fail-closed default actually protects is reject_a_binder_that_cannot_fail.
  Fail-closed remains load-bearing; I named the wrong beneficiary twice.
Task 4: PLAN DEFECT FOUND AND FIXED — the Verification section used
  `git diff --stat main...HEAD -- src/ runtime/`, which spans all of phase-16
  (HW-1, 16-22/23/24 legitimately changed src/ and examples/) and can never be
  empty. Rescoped to this plan's base 8169b56.
Task 4: DEFERRED FINDINGS raised by the implementer, pre-existing, NOT acted on —
  C1: MINIMUM_RESOLVED_BINDER_SITES 11 vs 12 actual; MINIMUM_GATE_CALL_SITES 9 vs
  11 actual. Both carry headroom the module's own no-headroom doctrine forbids.
  C2: two function docstrings state counts now false (11/11).
  C3: Task 3's prose says fixtures are synthesized under tmp_path; they use
  REPO_ROOT / "probe.py". Mechanism sound (parent is not under examples/, so
  _deployment_root still returns None), illustration wrong.
  => C1+C2 are a scoped follow-up for Dave to rule on; out of this plan's scope.
Task 4: task reviewer dispatched (OPUS) over fa76deb..9b09910, 5 named checks.
Task 4: review verdict — Spec OK, Task quality APPROVED. All 5 named checks passed
  on independent verification (not on the report's say-so): property (1) genuinely
  unconditional; (2)+(3) in two separate `if demanded:` blocks preserving the
  section markers; ceiling in predicate form and drivable by a synthetic list;
  constant 13 and its comment agree; the 3 re-broken messages concatenated by hand
  and confirmed byte-identical. Reviewer also checked an unnamed risk of its own —
  _one_document called 4-arg from _binder_collapses and 3-arg elsewhere — and
  confirmed the shared default makes the call sites unable to disagree.
Task 4: 1 Important — `_binder_collapses`'s OWN docstring (IN-03 paragraph, ~:2040)
  still says a body with no binder call is reported by property (3) AND the
  coverage assertion. For an EXEMPT body it is now reported by NEITHER. Same defect
  class as the module docstring, one level down; Correction 2 caught the parent and
  missed the child. Plus the coverage test's "what is still not asserted" list does
  not name the exemption — the largest thing it no longer asserts.
Task 4: minor (deferred): MINIMUM_RESOLVED_BINDER_SITES newly load-bearing — a 2nd
  exempt claimant takes readable sites 12->11 and leaves that floor green. Ceiling
  catches it with no headroom, so redundant defence w/ 1 unit of slack. Name it in
  the C1 follow-up commit.
Task 4: minor (deferred): no control exercises the coverage test's early return.
Task 4: minor (deferred): _one_document_deployments() re-parses the tree. Cost only.
Task 4: fix round 1/5 dispatched — two docstring qualifications, no behaviour change.
Task 4: fix round 1/5 (1 addressed, 0 open; commits 9b09910..4ef54e2). Re-review
  confirmed the original IN-03 reasoning preserved byte-unchanged with a six-word
  qualifier appended, the exempt case added as a NEW paragraph, R-3 untouched, and
  the exemption filed in the coverage docstring as a deliberate carve-out rather
  than an AST limit — the distinction that matters, since its neighbours in that
  list ARE AST limits.
Task 4: complete (commits fa76deb..4ef54e2, review clean)
Task 5: THIRD PLAN DEFECT, controller-found before dispatch. The brief's row-C
  control copied HW-1 to tmp_path and read the copy. Verified by execution:
  _deployment_root(tmp copy) is None -> fail-closed refuses the body whatever its
  AST says. The control would have passed on day one AND kept passing if row C
  were wholly broken. Row C is the one shape the exemption must never admit.
  Replaced with an in-memory mutation against the REAL path, plus two spine
  assertions: baseline-exempt (the mutation is what flips it) and root-is-not-None
  (the row-C reading is in play, not fail-closed).
Task 5: PATTERN WORTH KEEPING — all three plan defects were in the VERIFICATION,
  never the mechanism. The conditioning, the detector and the properties were
  right each time; what was wrong was the thing meant to prove them right.
Task 5: dispatched (sonnet), BASE 00f899c. Implementer DONE, commit abb96ca.
  CONTROLLER-VERIFIED: 98 passed across both gates, 0 failures; no `shutil`
  reference in the file (the defective control's only need for it).
Task 5: implementer watched the row-C control fail (no-op'd the mutation string,
  saw it fail at `assert mutated != text`). Review asked whether that is the RIGHT
  proof — it shows dependence on the mutation string, not that the control would
  fail if row-C DETECTION regressed.
Task 5: task reviewer dispatched (sonnet) over 00f899c..abb96ca, 4 named checks.
Task 5: review verdict — Spec OK, Task quality APPROVED. All 4 checks held under
  independent tracing. 1 Important, but about REPORT ACCURACY not shipped code:
  the implementer's vacuity proof (no-op the mutation string) demonstrates a
  guard against SOURCE drift, not against DETECTION drift, while the report
  claimed the stronger result and closed "Concerns: None".
Task 5: CONTROLLER PERFORMED THE MISSING PROOF. Sabotaged _one_document to return
  True unconditionally (row-C detection neutralised), ran the row-C control:
  FAILED at its TERMINAL assertion — `AssertionError: []` at :2513, i.e. problems
  was empty because property (3) never ran. That is the right failure, at the
  right line. File restored via git checkout; tree clean; 76 passed re-verified.
  => The control genuinely catches a row-C detection regression. Finding closed
  by evidence rather than by a fix; no fix round needed.
Task 5: minor (deferred): row-C docstring has no explicit "what this does not
  prove" clause (one shape, one deployment, not exhaustive over how required=
  could diverge) where the module's register elsewhere does.
Task 5: minor (deferred): row-B control overlaps test_the_premise_detector_reads
  _the_shipped_tree_correctly on the registration half — strengthening, not
  duplication (row B adds the AST half the older test lacks).
Task 5: complete (commits 00f899c..abb96ca, review clean)
Task 6: dispatched (sonnet), BASE abb96ca — brief task-6-brief.md, report task-6-report.md
Task 6: implementer DONE, commit e890453. D-IMPL-137 at line 416, between
  D-IMPL-136 (414) and D-GATE-15.6 (418) — correct placement, paragraph form.
Task 6: implementer CORRECTED MY BRIEF, rightly — the four DI-15.6-01(a) residuals
  cannot appear in ci-core at all: pyproject `testpaths = ["tests"]` excludes
  tools/. So "green except four known" was never the right baseline; green is.
Task 6: CONTROLLER-VERIFIED ci-core independently, exit 0:
  `3199 passed, 118 skipped, 105 warnings in 389.97s`. Zero failures.
  105 warnings are pre-existing a2a/starlette deprecations in unrelated suites.
Task 6: complete (commits abb96ca..e890453, review = the full-suite verification)
FINAL: whole-branch review dispatched (OPUS) over 8169b56..e890453, 12 commits,
  with the ledger handed over for deferred-finding triage and six questions the
  scoped reviews structurally could not answer.
FINAL: verdict APPROVE WITH FIXES. 0 Critical. 4 Important, all prose/control,
  none changing what either gate refuses. Thesis confirmed by the reviewer's own
  enumeration: 12 projecting bodies demanded, exactly 1 exempt, ceiling 1, and
  `git diff 8169b56..e890453 -- src/ runtime/ examples/` empty.
FINAL: one fix wave (7c8d488, a092bfb, 139481e) — 99 passed. I-4 control watched
  to fail under the fold, and it was the ONLY failure (1 failed / 98 passed),
  which is the finding restated as data.
FINAL: one scoped re-review — ALL FOUR ADDRESSED, merge readiness READY.
RESIDUAL (parked, needs Dave): the sentence "the second fail-closed guard is what
  holds them demanded" is imprecise. Verified: _deployment_root(probe.py) is None,
  so guard 1 short-circuits via the `or` BEFORE guard 2 is reached; both would
  catch, but guard 1 executes. True only counterfactually. Inherited from MY
  dispatch wording, not introduced by the fixer. This is the FIFTH iteration of
  this one claim and the THIRD distinct way it has been wrong. Reviewer: Minor,
  not a blocker; the following clause states the counterfactual correctly.
  No second fix wave per the skill — surfaced to Dave instead.
OPEN FOR DAVE: (1) the phrasing residual above; (2) C1 floors follow-up
  (MINIMUM_GATE_CALL_SITES 9 vs 11, MINIMUM_RESOLVED_BINDER_SITES 11 vs 12);
  (3) whether to push phase-16, which is currently pushed RED at 868aa4e.
