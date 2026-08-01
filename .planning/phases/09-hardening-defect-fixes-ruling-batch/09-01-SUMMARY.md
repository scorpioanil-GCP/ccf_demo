---
phase: 09-hardening-defect-fixes-ruling-batch
plan: 01
subsystem: governance
tags: [ruling-batch, mini-cycle, decisions, hash-manifest, D-14]
requires: []
provides:
  - "D-IMPL-68..73 rulings (all six batch items RESOLVED by Dave, zero deferrals)"
  - "D-14 pre-phase sha256 hash manifest of all eight examples' run.py + artifacts trees"
  - "docs/09-ruling-batch-minicycle.md (consolidated mini-cycle document, statuses RESOLVED)"
affects: [phase-10, phase-11, phase-14]
tech-stack:
  added: []
  patterns: ["Phase D mini-cycle inside an execution phase (rulings-first, D-02)"]
key-files:
  created:
    - .planning/phases/09-hardening-defect-fixes-ruling-batch/09-examples-hash-manifest.txt
    - docs/09-ruling-batch-minicycle.md
  modified:
    - docs/DECISIONS.md
decisions:
  - "D-IMPL-68: WR-01 scope mapping as versioned Control Plane policy artifact, door-side enforcement, deny-by-default (Option C)"
  - "D-IMPL-69: HITL primitives verify HitlPolicy signed bindings on resolve paths, typed refusals reused (Option A)"
  - "D-IMPL-70: perf governance — Dave-gated re-baseline, reviewed thresholds.toml, opt-in perf.yml per D-11 (Option A)"
  - "D-IMPL-71: docs are CI-artifact-only; no public publishing (Option A; GitHub Pages private-visibility constraint verified, not assumed)"
  - "D-IMPL-72: Phase-8 D-10 make ci composition amended — docs --strict joins always-on CI, effective at the Phase 14 plan creating the docs target (Option A)"
  - "D-IMPL-73: create_app insecure-default warning — dedicated warning category + log record, suppression only via explicit acknowledgment kwarg, no env var (Option C)"
metrics:
  duration: "~35 min (incl. checkpoint wait)"
  tasks: 3
  files: 3
  completed: 2026-08-01
---

# Phase 9 Plan 01: Ruling Batch & D-14 Baseline Summary

Six-item D-IMPL ruling batch run as one Phase D mini-cycle and fully ruled by
Dave (D-IMPL-68..73, zero deferrals, all per recommendation), with the D-14
pre-phase byte-identity hash manifest committed before any Phase 9 code change.

## Per-Item Ruling Outcomes (for the D-GATE-9 presentation)

| Item | D-IMPL | Outcome | Consumer |
|------|--------|---------|----------|
| WR-01 per-tenant authz mapping shape | 68 | RESOLVED — Option C: versioned Control Plane scope-mapping artifact, enforced door-side via one shared helper, deny-by-default, typed 403, policy-artifact version in the audit record | Phase 10 (HARD-04) |
| ApprovalGate.resolve × D-16 composition | 69 | RESOLVED — Option A: all four primitives verify the HitlPolicy on their resolution surfaces, reusing the transport's typed refusals; JWS verification stays outside any transport lock | Phase 10 (HARD-04) |
| Perf governance | 70 | RESOLVED — Option A: re-baselining is Dave-approved and logged; thresholds.toml changes reviewed as ruled artifacts; perf gating stays workflow_dispatch opt-in (D-11 pattern); always-on promotion is a future D-IMPL | Phase 11 |
| Docs toolchain/publishing | 71 | RESOLVED — Option A: CI-artifact-only, nothing hosted; hosting stays an explicitly open future D-IMPL | Phase 14 |
| Phase-8 D-10 `make ci` amendment | 72 | RESOLVED — Option A: `make ci` grows `docs-strict` (and ci.yml the job) effective at the Phase 14 plan that creates the docs target; new number per new-number-not-amend, Phase-8 D-10 text stands | Phase 14 |
| create_app insecure-default warning | 73 | RESOLVED — Option C: dedicated `UserWarning`-subclass category at construction + log WARNING at first request; single suppression surface is an explicit acknowledgment kwarg (no env var) | Phase 10 (HARD-05) |

All six items ruled interactively; zero rulings invented by the executor; zero
deferrals, so no downstream phase is gated by an open batch item (D-04
partial-proceed never invoked).

## What Was Done

1. **D-14 baseline manifest (Task 1, commit 118e070).** Deterministic sorted
   sha256 manifest of every `run.py` and `artifacts/` file across all eight
   example directories (57 files) at
   `.planning/phases/09-hardening-defect-fixes-ruling-batch/09-examples-hash-manifest.txt`,
   captured before any Phase 9 code change (Wave-1, rulings-first per D-02).
   `make examples` confirmed green at baseline (all eight examples exit 0).
2. **Mini-cycle document (Task 2, commit 018b73c).**
   `docs/09-ruling-batch-minicycle.md` (361 lines): six items, each with
   surfacing context, 2–3 options with consequences, and a recommendation;
   candidate numbers D-IMPL-68..73 verified against the actual DECISIONS.md
   tail (last entry D-IMPL-67); Phase-8 D-10 vs Phase-9 CONTEXT D-10
   namespaces explicitly disambiguated in item 5; D-04 partial-proceed stated
   in the preamble.
3. **Rulings logged (Task 3 checkpoint, commit 663f08a).** Dave ruled all six
   items in the interactive walkthrough (2026-08-01); each ruling appended to
   `docs/DECISIONS.md` in house format (`**D-IMPL-NN — title.** RESOLVED —
   option, 2026-08-01, Approver: Dave.` with surfacing context, question,
   consequences, Originates line); mini-cycle status table updated to match.

## Verified Fact Worth Preserving

RESEARCH assumption A2 was verified against GitHub's official documentation
(not assumed) before drafting item 4, with a sharpening: private GitHub Pages
visibility ("access control") requires GitHub Enterprise Cloud **and** an
organization-owned repository — `drcastillo/ccf_code` is a personal-account
private repo, so any Pages site from it would be publicly readable. Recorded
inside D-IMPL-71.

## Deviations from Plan

None material. One environment note: the worktree lacked `.venv`, so `make
examples` was run via a temporary symlink to the main checkout's venv
(removed before commit; nothing committed). The plan's WebSearch instruction
for A2 was satisfied via direct fetch of GitHub's official docs pages (no
WebSearch tool in this environment) — same verification outcome, primary
source.

## Notes for the D-GATE-9 Presentation

- **Branching strategy:** `.planning/config.json` has
  `branching_strategy: "none"`, but CLAUDE.md §2.2 mandates phase branches
  with merge-to-main at D-GATE. Phase 9 executed on worktree agent branches
  merged by the orchestrator, not a `phase-9` branch. This divergence needs
  Dave's explicit disposition at D-GATE-9 (per RESEARCH Open Question 3 —
  surfaced, not defaulted).
- **Mixed model mandate:** this plan (Phase-D-shaped mini-cycle) ran under
  Fable 5 high effort per CLAUDE.md §3 (Phase D); plans 09-02/09-03
  (Phase-I-shaped code fixes) run under Opus per CLAUDE.md §3 (Phase I). The
  split is deliberate (RESEARCH model-mandate flag) — record it at D-GATE-9.
- **Post-phase D-14 check:** at phase close, re-run the manifest command and
  diff against `09-examples-hash-manifest.txt`; any drift is a blocking
  event per D-14.

## Known Stubs

None.

## Threat Flags

None — no new security surface introduced; T-09-01/02/03 mitigations all
executed as planned (rulings only after Dave's answers; Pages visibility
verified before presenting; manifest committed before any code change).

## Commits

- 118e070 — chore(09-01): capture D-14 pre-phase examples hash manifest
- 018b73c — docs(09-01): draft consolidated six-item ruling-batch mini-cycle document
- 663f08a — docs(09-01): log D-IMPL-68..73 — six ruling-batch outcomes

## Self-Check: PASSED

- Manifest, mini-cycle doc, and DECISIONS.md entries verified on disk
- Commits 118e070, 018b73c, 663f08a present in git log
- grep count of D-IMPL-6[89]/7[0-3] entries in DECISIONS.md: 6
