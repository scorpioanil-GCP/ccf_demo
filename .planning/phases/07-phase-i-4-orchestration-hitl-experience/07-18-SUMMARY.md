---
phase: 07-phase-i-4-orchestration-hitl-experience
plan: 18
subsystem: hitl
tags: [hitl, replay, tests, gap-closure]
requires: []
provides:
  - "End-to-end build_replay_record drives for ExceptionEscalation, OverrideBoundary, ReviewQueue (release + reject)"
affects: []
tech-stack:
  added: []
  patterns: ["full-path replay drive (primitive action → resolution → build_replay_record → dimension-2 byte assertion)"]
key-files:
  created:
    - tests/hitl/test_replay_e2e.py
  modified: []
decisions: []
metrics:
  duration: "~10 minutes"
  completed: "2026-07-30"
---

# Phase 07 Plan 18: HITL Replay End-to-End Drives Summary

Full-path `build_replay_record` proof for the three compositionally-covered HITL primitives — each resolution's `hitl_actions_block` now asserted byte-equal on dimension 2 of a real `DecisionReplayRecord`, matching the ApprovalGate slice's strength (D-IMPL-66 item c; gate row 7 closed).

## What Was Built

`tests/hitl/test_replay_e2e.py` — five tests:

- **E2E-1 (ExceptionEscalation):** escalate with `ExplicitEscalation` → resolve with bound `HumanPrincipalBinding` → `build_replay_record(hitl_actions=resolution.hitl_actions_block)` → `replay.policy_bindings.hitl_actions == resolution.hitl_actions_block` (byte equality), plus round-trip to `EscalationActionRecord` asserting the approver's `subject_id` and `accepted=True`.
- **E2E-2 (OverrideBoundary):** propose → resolve with a substitute → byte-equal landing, plus deserialized record carries **both** original and override values (`overridden=True`) — CLAUDE.md §8.2 override doctrine (T-07.1-11).
- **E2E-3a/3b (ReviewQueue):** submit_for_review → `release` and, separately, `reject` → byte-equal landing each; rejection round-trips with `released=False` — a recorded action, never an absence.
- **Negative guard:** with a resolution in hand, `hitl_actions=None` leaves the positive `NO_HITL_ACTIONS` sentinel (`"no-hitl-actions"`) on dimension 2, never the block — documenting that landing the block is the caller's replay obligation (honest boundary, not enforcement).

All values (approvers, events, override determinations, review lineage) come from `tests/fixtures/banking/hitl.yaml`; the module carries mechanism-shaped drives only (No-Hardcoding Rule §6.4). The record-builder fixture mirrors the 07-07 slice's `_replay_record` construction.

## Verification

- `tests/hitl/test_replay_e2e.py`: 5 passed; `grep -c hitl_actions_block` = 10 (≥ 4 required).
- Full sweep: **1285 passed / 0 failed / 0 skipped** (baseline 1280 + 5 new).
- `mypy --strict src runtime tools`: clean (164 files).
- `tools.lints --all`: exit 0.
- `git diff --stat src/ runtime/`: empty — tests-only plan, no wiring defect surfaced.

## Deviations from Plan

None - plan executed exactly as written. (The plan's illustrative placeholder hash for the escalation drive was replaced with a real `content_hash(trigger)` value because `HumanPrincipalBinding` validates the sha256 shape — a test-fixture construction detail, not a mechanism change.)

## Known Stubs

None.

## Threat Flags

None — no new security surface; the plan adds test coverage for existing trust-boundary crossings (T-07.1-10, T-07.1-11 both mitigated by the drives above).

## Commits

- `01e9969` test(07-18): end-to-end build_replay_record drives for escalation, override, review queue

## Self-Check: PASSED

- tests/hitl/test_replay_e2e.py exists — FOUND
- commit 01e9969 in log — FOUND
