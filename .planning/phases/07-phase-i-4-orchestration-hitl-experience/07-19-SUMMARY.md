---
phase: 07-phase-i-4-orchestration-hitl-experience
plan: 19
subsystem: cli-hitl, gate-docs
tags: [hitl, cli, d-impl-62, d-impl-66, gate]
requires: []
provides:
  - "ccf hitl submit as primary verb; decide deprecated alias (D-IMPL-66(d))"
  - "PHASE_I4_GATE.md post-merge status addendum (D-IMPL-66(e))"
affects: []
tech-stack:
  added: []
  patterns: ["one shared RequestSpec builder for aliased verbs", "append-only gate addendum"]
key-files:
  created: []
  modified:
    - runtime/ccf_runtime/cli/commands/hitl.py
    - tests/cli/test_cli.py
    - docs/PHASE_I4_GATE.md
decisions:
  - "decide's deprecation notice goes to stderr at build time, preserving machine-readable stdout (main.py exit-code/output discipline)"
metrics:
  duration: "~15 min"
  completed: "2026-07-30"
---

# Phase 7 Plan 19: hitl submit alias + gate post-merge addendum Summary

`ccf hitl submit` added as the primary D-IMPL-62-honest verb (decide deprecated, one shared builder) and the Phase I.4 gate document gains its post-merge status addendum recording D-GATE-I.4 and the 1280/0/0 main sweep.

## Tasks

| Task | Name | Commits |
|------|------|---------|
| 1 | submit verb + decide deprecated alias (TDD) | 173f8ac (RED), 3221c56 (GREEN) |
| 2 | Post-merge status addendum to docs/PHASE_I4_GATE.md | fdd6f91 |
| 3 | Full-suite regression sweep | (verification only) |

## What was built

- **Task 1:** `_submit` is the single RequestSpec builder for `POST /hitl/actions`; `submit` registered with help stating the D-IMPL-62 truth ("submission only; resolution is the owning primitive's act"); `decide` kept, help prefixed "(deprecated — use 'submit')", its build wrapper printing one deprecation line to stderr and delegating to `_submit`. Three new tests: spec equality, stderr notice (and submit notice-free), help-text semantics; `("hitl","submit","--file","f")` added to the inventory parametrize. Acceptance greps: `path="/hitl/actions"` count = 1; "deprecated" present.
- **Task 2:** Appended `## 8. Post-merge status addendum (Phase 7.1, D-IMPL-66(e))` — D-GATE-I.4 approved 2026-07-30 by Dave, merge commit `60f5192` named verbatim (verified via `git log --merges`), post-merge main sweep 1280/0/0, mypy 152 files, lints exit 0, and the supersession of §7.4's closing sentence. Top-of-document STATUS line added. `git diff --numstat`: 24 additions, 0 deletions.

## Verification

- `tests/cli`: 43 passed (40 pre-existing + 3 new).
- Full sweep: **1283 passed / 0 skipped / 0 failed** under `CCF_REQUIRE_HARNESSES=1` (baseline 1280 + this plan's 3 tests); `mypy --strict` clean, 164 source files (src+runtime+tools invocation; the gate's 152 figure is the `[tool.mypy]` src+runtime set); `tools.lints --all` exit 0.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — no new security-relevant surface; T-07.1-12 mitigated (single builder, honest verb), T-07.1-13 mitigated (append-only, 0 deletions asserted).

## Self-Check: PASSED

- runtime/ccf_runtime/cli/commands/hitl.py: FOUND
- docs/PHASE_I4_GATE.md addendum greps: FOUND
- Commits 173f8ac, 3221c56, fdd6f91: FOUND
