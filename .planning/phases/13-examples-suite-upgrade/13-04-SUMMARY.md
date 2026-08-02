---
phase: 13-examples-suite-upgrade
plan: 04
subsystem: examples
tags: [hitl, review-queue, override-boundary, decision-replay, readme-template]
requires: [13-01]
provides:
  - "Example 05 exercises ApprovalGate + ExceptionEscalation + ReviewQueue with audit-by-construction assertions"
  - "Example 06 exercises OverrideBoundary in replay — original and override both byte-present in the record"
  - "Template-conformant seven-heading READMEs for examples 05 and 06"
affects: [13-05 (verifier), phase-14 docs mount]
tech-stack:
  added: []
  patterns:
    - "ReviewQueue driven from artifact values with signed release landing on replay dimension 2"
    - "OverrideBoundary parameterized by a deployment-typed contract whose values live in artifacts"
key-files:
  created: []
  modified:
    - examples/05-workflow-hitl/README.md
    - examples/05-workflow-hitl/artifacts/hitl.yaml
    - examples/05-workflow-hitl/artifacts/tokens.yaml
    - examples/05-workflow-hitl/run.py
    - examples/06-decision-replay/README.md
    - examples/06-decision-replay/artifacts/hitl.yaml
    - examples/06-decision-replay/run.py
decisions:
  - "Review is post-terminal async review of the generated briefing (not a workflow node) — matches ReviewQueue's §8.2 'before release' framing and keeps workflow routing untouched"
  - "05 gains a fourth ACTIVE reviewer token so the reviewer subject follows the same active-token client_id convention as the approver"
  - "06 serves the override decision's OWN five-dimension record (one HITL block per record, matching the SDK's test_replay_e2e pattern) rather than overloading the approval record's dimension 2"
metrics:
  duration: "~12 min"
  completed: "2026-08-02"
---

# Phase 13 Plan 04: Examples 05 + 06 HITL Upgrade Summary

ReviewQueue lands in example 05 and OverrideBoundary lands in example 06 — the two previously-unexercised HITL primitives — both replay-recorded by construction, with both READMEs rewritten to the seven-heading D-02 template.

## What was done

**Task 1 — example 05 (commit f851032).** `artifacts/hitl.yaml` gained a `review:` block (versioned-URI-pinned `output_ref`, passage-level lineage, reviewer identity + authentication, artifact-driven release/reject drive); `tokens.yaml` gained an ACTIVE `reviewer` entry whose `client_id` equals the reviewer subject. `run.py` gained interpreter-only code: it constructs a policy-bound `ReviewQueue` (signed bindings required, same D-16 policy), drives `submit_for_review` → `release` from artifact values (mirroring `tests/hitl/test_review_queue.py`), and asserts — not prints — that the release lands in the Control Plane audit log with the reviewer as actor AND byte-equal on a replay record's dimension 2 (`ReviewActionRecord` round-trip, output_ref present). All seven artifacts carry the verbatim `[ADAPT]`/`[MECHANISM]` markers. README rewritten: seven headings in template order, the old invariant table preserved and extended as "What would fail" with a ReviewQueue row, ApprovalGate/ExceptionEscalation/ReviewQueue all glossed per the Part-2 table, Phase-10 auth posture narrated as demonstrated security, regeneration warning naming `artifacts/hitl.yaml`.

**Task 2 — example 06 (commit 2242267).** `artifacts/hitl.yaml` gained an `override:` block declaring the agent's original shed determination AND the supervisor's substitution (quoted decimals), overrider identity bound to the active token, and an override/confirm drive. `run.py` gained a deployment-typed `ShedDetermination` contract (field values only from artifacts) plus interpreter code driving `OverrideBoundary.propose`/`resolve` with a signed binding; the override decision's own five-dimension record is served to the same ArtifactStore, and `replay_decision()` replays it: byte-equal product, `OverrideActionRecord[ShedDetermination]` round-trips from dimension 2, `canonical_bytes(original)` and `canonical_bytes(final)` both literally present in the block, overrider signature verifying from the record alone with the grant-derived subject. All eleven artifacts carry the markers. README rewritten to the template, glossing the five replay dimensions and narrating the flagship "both values in the record" claim.

## Expected-output deltas (D-09, reviewed)

- 05: one new stdout line `review released credit-review-officer-7 → …disbursement-briefing@1.0.0`. `expected_gate` and existing drive values unchanged (workflow routing untouched).
- 06: one new stdout line `override (dim 2) 12.5MW/30min → 9.0MW/45min (both values in the record)`. `controlplane.yaml`/`skills.yaml` expected blocks unchanged (fabric and skill legs untouched).

## Auth posture (unweakened)

`scope_mapping.yaml` untouched in both examples; all deny-by-default 403 legs, signed-binding refusals, and expired-token 401 legs still asserted. 05's tokens.yaml addition is an extra ACTIVE credential for the reviewer convention — nothing removed or loosened; all tokens remain obviously synthetic.

## Verification

- `make example-05` — exit 0 with review leg asserted
- `make example-06` — exit 0 with override leg asserted in replay
- `make lint` — green (No-Hardcoding/CINV lints; run.py diffs interpreter-and-assertion only)
- `grep -c '^## '` = 7 for both READMEs; `review`/`override` present in the respective hitl.yaml files
- Exactly one commit per example directory

## Deviations from Plan

None - plan executed exactly as written. (Environment note: the worktree lacked the gitignored `.venv`; a temporary symlink to the main checkout's venv was used for `make` runs and removed before the final commit — no tracked files affected.)

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or trust-boundary schema changes beyond the plan's threat model; T-13-01/02/04/05 mitigations applied as specified.

## Self-Check: PASSED

- examples/05-workflow-hitl/README.md — FOUND
- examples/06-decision-replay/README.md — FOUND
- commit f851032 — FOUND
- commit 2242267 — FOUND
