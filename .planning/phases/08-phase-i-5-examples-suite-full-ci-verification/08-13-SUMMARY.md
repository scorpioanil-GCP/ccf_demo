---
phase: 08-phase-i-5-examples-suite-full-ci-verification
plan: 13
subsystem: docs
tags: [v0, gate, d-gate-i, packaging, readme, review, exam-09]
requires: [08-12]
provides:
  - "Top-level README.md: install, quickstart pointer, eight-example table, no-PyPI posture (D-17)"
  - "pyproject version 0.1.0 (bumped from 0.1.0.dev0), make ci green after the bump"
  - "docs/PHASE_I5_GATE.md: §3.1 Phase I per-invariant checklist, six-class whitepaper-fidelity spot check, obligations status, review appendix"
  - "D-GATE-I logged (Dave, 2026-07-31); phase-i5 merged to main --no-ff; v0.1.0 tagged on the merge commit"
affects: [main, origin, v0.1.0]
tech-stack:
  added: []
  patterns:
    - "Gate document mirrors the I.4 D-17/D-25 row format: mechanism + what-would-fail, D-22 scoping"
    - "Cross-AI review with Codex inline fallback when its bwrap sandbox cannot read the tree"
key-files:
  created: [README.md, docs/PHASE_I5_GATE.md]
  modified: [pyproject.toml, docs/DECISIONS.md]
decisions:
  - "C-4 (README 'any agent harness' wording) rejected with rationale: the sentence tracks CLAUDE.md §1's own mission claim; the gate states what is demonstrated (three harnesses)"
  - "X-1 blocking fix: composition-coverage gate row narrowed to the shipped_operators() test registry (four operators today; extension is a maintainer step)"
metrics:
  duration: "~50 min + gate checkpoint"
  completed: "2026-07-31"
---

# Phase 08 Plan 13: v0 packaging + the Phase I gate Summary

Phase I is gated and v0 is declared: README + version 0.1.0 + gate document
authored, the §3.1 cross-AI review triaged with its one blocking finding
fixed in-phase, Dave approved on 2026-07-31, D-GATE-I logged, `phase-i5`
merged to `main --no-ff`, and `v0.1.0` tagged on the merge commit — in
exactly that order (RESEARCH Pitfall 6).

## What was built

- **Task 1 (a955969):** Top-level `README.md` (what CCF is in one
  five-pillar paragraph, `pip install -e ".[dev]"`, `make example-00`
  quickstart pointer, the eight-example table with commands, docs pointers,
  private-repo/no-PyPI posture per D-17); `pyproject.toml` bumped to
  `0.1.0`; `docs/PHASE_I5_GATE.md` mirroring the I.4 gate format — the
  seven §3.1 Phase I rows (No-Hardcoding, harness-import, `@algorithmic`,
  composition-preservation, replay-by-construction, full §9 suite, example
  03 portability) each with mechanism + failure mode, a six-class
  whitepaper-fidelity spot check (CCFContract §6.3, graph protocols §7.3,
  operators §7.4, ProjectionEngine §7.5, replay record §7.10.1, λ_c decay
  §7.7 — no fidelity defect; extensions correctly labeled), Phase 8
  obligation statuses (D-14..D-17, D-15, D-16, A3, R1, R2/N5 — all
  discharged or staged), the success-criteria evidence map, and the
  push-authorization flag. `make ci` green after the bump.
- **Task 2 (26a71b5):** §3.1 cross-AI review. Cursor ran full-tree; Codex's
  sandboxed run failed (`bwrap: loopback: Failed RTM_NEWADDR`, the same
  environment defect as at I.4) and was re-run with the deliverables
  supplied inline (sandbox-bypass flags are blocked in this environment).
  One blocking finding (X-1: gate row 4 overclaimed composition coverage as
  "grows automatically"; verified against `tests/properties/strategies.py`)
  fixed in-phase; advisories fixed (X-2 D-22 row scoping, X-3 `make ci` vs
  Actions precision in gate §1 and README) or dispositioned (C-4 rejected
  with rationale, X-4 carried). §7 appendix populated with the full
  disposition table. `make ci` re-run green (docs-only fixes).
- **Task 3 (checkpoint):** Presented to Dave. **Approved 2026-07-31**, with
  push authorization granted in a follow-up ruling.
- **Task 4 (d3252c1, 358ba0d, v0.1.0):** `D-GATE-I` appended to
  `docs/DECISIONS.md` (chronological tail position); gate document status
  header updated append-only; `phase-i5` merged to `main --no-ff` with the
  merge commit referencing D-GATE-I (`358ba0d`); annotated tag `v0.1.0` on
  the merge commit on `main`; branches and tag pushed to origin per the
  authorization.

## Verification

- `make ci` exit 0 (twice: post-bump, post-review-fixes): lints 0, mypy
  clean (156 files), **1339 passed / 0 skipped / 0 failed** under
  `CCF_REQUIRE_HARNESSES=1`, all eight examples exit 0.
- `git tag -l v0.1.0` → present; `git log main -1 --merges` references
  D-GATE-I; `v0.1.0^{commit} == main` (tag on the merge commit, never
  pre-approval state).

## Deviations from Plan

- **[Rule 3 - Blocking] Codex sandbox fallback:** Codex's read-only sandbox
  cannot execute any command in this environment and sandbox-bypass flags
  are permission-blocked; the review was completed by supplying the
  deliverables inline (document-scoped leg), with Cursor as the full-tree
  leg. Recorded honestly in the gate §7 per the I.3/I.4 "a review that
  could not see the tree is not a passing review" discipline.
- **[Minor] D-GATE-I placement:** first inserted before D-GATE-I.4.1, then
  moved to the chronological tail of DECISIONS.md before committing.
- **[Rule 2 - Missing critical] Gate-doc status addendum:** a short
  post-approval STATUS header was added to PHASE_I5_GATE.md in the D-GATE
  commit (append-only, I.4 §8 pattern) so the document does not claim to be
  awaiting approval after approval.

## Known Stubs

None.

## Threat Flags

None new. T-08-30 held (reviewer keys sourced at runtime from the homecams
.env, never committed); T-08-31 held (§3.1 ordering enforced: D-GATE-I
recorded before merge and tag).

## Self-Check: PASSED
