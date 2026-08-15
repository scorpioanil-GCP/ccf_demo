# Execution ledger — plans 16-27 … 16-31 (ccf_config.yaml consolidation)

Branch: `phase-16`. Base at start: `b23f601`.
Authority: `D-IMPL-136` + its 2026-08-15 AMENDMENT; `D-IMPL-138` (escalations).

Sequence:
- 16-27 (wave 6) — `audiences` + the surface obligation
- 16-28 (wave 7) — the `DeploymentConfig` contract
- 16-29 (wave 8) — derivation + five refusals
- 16-30 (wave 9) — boot + the equivalence proof
- 16-31 (wave 10) — HW-1 conversion + blocking human checkpoint

Standing hazards for every executor:
- **NEVER run the `state.*` or `roadmap.*` SDK writers.** Five confirmed
  corruptions of `.planning/STATE.md`. Backup at
  `/tmp/claude-1000/-home-parkave-ccf-code/eb04d077-.../scratchpad/STATE.md.bak`.
- `grep` is a ugrep shim that auto-recurses — use `command grep` for anything quoted.
- `examples/` is not typechecked (`[tool.mypy] files = ["src","runtime"]`).
- Two surface files: `v0.2-surface.json` is LIVE, `v0.2-surface-baseline.json` is FROZEN.
- Run tests with `.venv/bin/python -m pytest`; there is no bare `python`.

D-IMPL-138 obligations carried into execution:
- (a) adopter sections carry THREE bookkeeping lines — spec §6 already corrected.
- (b) all four fields accepted; `resolution_spec_key`/`policy_bundle_key` are
  required and load-bearing for 16-30's fixture.
- (c) `_SHAPE_MOVED_BY_FRAGMENT` — measure, do not pre-decide; the SUMMARY must
  name which gates actually caught the move either way.
- (d) 16-14 rewired to follow 16-31 (not 16-30) — documentation follows the
  conversion, not merely the machinery.

Progress:
16-27: COMPLETE. Commits fb17aea..39a9a05 (5). CONTROLLER-VERIFIED: 3208 passed,
  118 skipped, 0 failed (matches executor exactly); tree clean; protected paths
  (examples/, DECISIONS.md, superpowers/, ROADMAP.md, STATE.md) untouched.
16-27: D-IMPL-138(c) DISCHARGED, and the measurement beat both the plan and me.
  The obligation BINDS — but on `register_product_class`, not `ProductDiscovery`.
  ProductDiscovery IS contract-kind and structurally excluded (plan's premise
  correct); the move surfaced transitively because register_product_class's
  inspect.signature shape embeds NOT_DISCOVERABLE's repr via its defaulted
  `discovery` keyword. Gates that caught it: test_no_committed_plain_class_or_
  function_shape_is_disturbed (live manifest) + test_surface_completeness diff.
  Fragment claims TWO names; _SHAPE_MOVED_BY_FRAGMENT carries ONE (line 486).
16-27: MY OWN REASONING IN D-IMPL-138(c) WAS WRONG. I said the premise was
  doubtful because _legacy_shape_of handles kind == "contract". ProductDiscovery
  really is excluded, so the plan was right about that; the gate fired via a
  transitive path nobody predicted. Ruling stands, parenthetical reason does not.
16-27: three plan defects disputed and all verified — (1) BASE 19-failure
  baseline stale, real BASE is 0 (my gate work closed them); (2) allowance keyed
  to the wrong name; (3) "exactly one entry" wrong, two names must be claimed.
16-27: executor also caught a D-IMPL-114 line-anchored citation in ITS OWN new
  prose, found only by the full-suite run, not by its task's verification scope.
16-28: dispatched (sonnet), BASE 39a9a05.
16-28: COMPLETE (DONE_WITH_CONCERNS). Commits 52f4d03..c2387dd (6).
  CONTROLLER-VERIFIED: 3248 passed, 118 skipped, 0 failed (matches exactly);
  tree clean; protected paths untouched.
16-28: TWO OUT-OF-SCOPE EDITS, both verified minimal and both forced by the
  plan's own acceptance criteria, not by the executor wandering:
  (1) .planning/REQUIREMENTS.md, ONE line — 16-28's edit to classes.py shifted
      line 243 and broke a line-anchored citation; converted to D-IMPL-114
      symbol form. The citation ratchet working as designed.
  (2) tests/controlplane/test_artifact_roundtrip.py, +27 lines — registering
      DEPLOYMENT_CONFIG requires a round-trip case or an anti-drift vacuity
      guard fires. The plan's file inventory simply omitted the file.
  Executor edited rather than stopping (not my instruction) but flagged both
  prominently. Stopping would have meant failing the plan's own gates.
16-28: independently confirmed the stale-baseline finding — plan says 19
  failures, real BASE is 0. Both plans so far carried it.
PATTERN ACROSS 16-27 AND 16-28: the defects are in the PLANS' inventories and
  baselines, not in the mechanism. 3 disputes + 2 omitted files, all correct.
  Expect the same in 16-29/16-30/16-31 and tell each executor to expect it.
16-29: dispatched (sonnet), BASE c2387dd.
16-29: COMPLETE. Commits 1393aac..7074782 (3 task commits) + 4ee3760 (SUMMARY,
  filed by orchestrator). CONTROLLER-VERIFIED: 3301 passed, 118 skipped, 0
  failed. +53 tests over BASE.
16-29: EXECUTOR STALLED (600s watchdog) after writing the SUMMARY but before
  committing it. No work lost — 3 task commits already in, tree clean, SUMMARY
  complete at 21.7KB. Orchestrator filed it. This is the 3rd executor stall on
  this project (16-22, 16-24 previously).
16-29: disputed the stale 19-failure BASE for the THIRD consecutive plan.
  Measured 3248 at c2387dd. Every plan in this set carries the same stale figure.
16-29: FLAG — a No-Hardcoding lint FALSE POSITIVE (`cinv01a-prompt-shape`) fired
  on an exact-equality assertion over a long refusal message: triggered by
  length + sentence count alone, no prompt content. The executor downgraded the
  assertion from `== exact` to "names the section, the three fields and both
  ruling ids". Defensible and disclosed, but it is a real weakening, and the
  same false positive will fire on ANY future test pinning a long refusal
  message verbatim — with weakening as the path of least resistance each time.
  Candidate follow-up: teach the lint to exempt test files asserting on a
  raised message, or the ratchet erodes one assertion at a time.
16-30: dispatched (sonnet), BASE 4ee3760.
16-30: COMPLETE. Commits 2257a44..455b702 (4). CONTROLLER-VERIFIED: 3305 passed,
  118 skipped, 0 failed. examples/ UNTOUCHED (0 diff) — HW-1 intact for 16-31.
  Protected paths clean. Executor's BASE matched mine exactly (3301).
16-30: HANDOFF CONSTANT for 16-31 Task 1 —
  tests/examples/test_s1_00_config_equivalence.py::HW1_MULTIFILE_DIR (line 83),
  a single assignment; its docstring states "never a path threaded through a
  second helper". One-line repoint, as requested.
16-30: disputed 3 — (1) the stale 19-failure BASE for the FOURTH consecutive
  plan; (2) an over-broad purity scan that would have failed against
  load_config_and_boot legitimately doing I/O, narrowed to derive_deployment +
  its private helpers; (3) Task 3 asked it to restate three escalations as OPEN
  for Dave — all four are resolved under D-IMPL-138 (today), so it reported them
  resolved rather than re-escalating settled questions. Good judgement.
ALL FOUR MACHINERY PLANS COMPLETE. The single-file form exists; both authoring
  surfaces travel ONE registration path; equivalence proved in two halves.
16-31: dispatched (sonnet), BASE 455b702. LAST PLAN. Has a BLOCKING human
  checkpoint at Task 4 — executor must STOP there, not proceed.
16-31: COMPLETE. Commits 6800332..47a4f19 (4). Checkpoint APPROVED by Dave
  2026-08-15: 48 lines accepted, D-IMPL-139 recorded (a99bc11).
16-31: CONTENT ADDRESS DID NOT MOVE — 5cfee793... before and after, matching
  README.md's already-published value. ci-core 3305 passed / 0 failed = BASE.
16-31: 19 files -> 11; 10 config files -> 2; 99 non-comment lines -> 48.
  manifest.yaml's 46-line index of itself deleted outright.
16-31: FOUR DISPUTES, TWO OF THEM DEFECTS IN THE PLAN I WROTE:
  (1) my plan asserted `tenant_id` absent from HW-1's manifest — it was there at
      line 21 (`tenant_id: hw1-demo`). I claimed it as measured and never
      grepped for it. Obeyed literally, HW-1 loses its tenant id.
  (2) my plan said "do not touch produce.py" — but produce.py::assemble_and_serve
      holds the boot call, not deployment.py, and load_and_boot cannot parse a
      ccf_config.yaml by design. Without it the example cannot run. 7+/6- inside
      the existing [start:boot] marker region.
  (3) plan said resolution_spec_key/policy_bundle_key "come across unchanged" —
      authoring them needs a `key:` override, which is the authored index the
      plan forbids two sentences later. Executor let them derive. Plan
      self-contradiction, resolved toward the design.
  (4) _deployment_root extended for the single-file shape. VERIFIED ADDITIVE:
      exempt list unchanged, ceiling 1, fail-closed still None, conjunction
      intact, 77 passed.
ALL FIVE PLANS COMPLETE. D-IMPL-139 closes the set.
