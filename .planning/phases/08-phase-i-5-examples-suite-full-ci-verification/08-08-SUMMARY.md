---
phase: 08-phase-i-5-examples-suite-full-ci-verification
plan: 08
subsystem: examples
tags: [examples, exam-06, exam-07, hitl, workflow, replay, d-14, d-16, auth]
requires: [08-02, 08-03, 08-05]
provides:
  - "examples/05-workflow-hitl runnable via make example-05 (EXAM-06): auth-bound workflow + ApprovalGate + ExceptionEscalation, D-14 live leg"
  - "examples/06-decision-replay runnable via make example-06 (EXAM-07): byte-equal reproduction with an auth-bound approval in the record, D-14 replay leg"
  - "D-14 examples-bind-auth obligation discharged across BOTH examples; D-16 signed-binding composition visibly exercised at the door and in replay"
affects: [08-12 CI examples job, top-level README example listing]
tech-stack:
  added: []
  patterns:
    - "Door-is-authority composition: under a signed-binding-required policy the D-16-verified HTTP submission IS the authority-path landing (D-IMPL-62); the driver as owning composition builds the HitlActionRecord from the pending event + the recorded submission"
    - "Token lifecycle as artifact data: an in-driver TokenSourceProtocol reads a YAML token table whose expired entry drives the 401 path"
    - "record()/replay_decision() helper split inside the example dir (review concern 4 mitigation)"
key-files:
  created:
    - examples/05-workflow-hitl/run.py
    - examples/05-workflow-hitl/README.md
    - examples/05-workflow-hitl/artifacts/ (task, workflow, agent, prompt, hitl, tokens)
    - examples/06-decision-replay/run.py
    - examples/06-decision-replay/README.md
    - examples/06-decision-replay/artifacts/ (ontology, events, controlplane, agent, prompt, skills, task, workflow, hitl, tokens)
  modified: []
decisions:
  - "ApprovalGate.resolve constructs an UNSIGNED submission, so it cannot land on a signed-binding-required transport; per D-IMPL-62 (door is submit-only, owning primitive resolves) the examples treat the D-16-verified door submission as the authority landing and the driver builds the dimension-2 HitlActionRecord from the pending event + the door-recorded submission — which is also what puts the SignedPrincipalBinding INTO the replay block, something a gate-built submission could never carry"
  - "Example 06 avoids any lowercase moving-target literal by importing LATEST_VERSION_TOKEN and building the refused ref with artifact_uri() — stronger than the acceptance criterion's single-marked-occurrence allowance"
  - "Replay-phase exact-version resolution: agent definition at its recorded dim-4 content hash; prompt + skill grant content-addressed out of the store and checked against the versions the record (and the definition it pins) declares; grant_set_hash recomputed from the resolved grant"
  - "Example 05's replay record uses the test_slice fixture-shaped execution/product with every value from artifacts/hitl.yaml replay block — the example's subject is the workflow/HITL dimensions, not the L1-L6 pipeline (which examples 00/01/06 own)"
metrics:
  duration: "~40 min"
  completed: "2026-07-31"
---

# Phase 08 Plan 08: examples 05 (workflow-HITL) + 06 (decision-replay) Summary

EXAM-06 and EXAM-07 shipped as runnable, asserted examples: a banking
loan-disbursement workflow approved through the hardened auth-bound HITL
door (live leg), and an energy/grid-ops load-shed decision recorded with
an auth-bound approval then reproduced byte-equal from the ArtifactStore
at exact versions (replay leg) — the D-14 absorption discharged in both.

## What was built

- **Task 1 (ee8b1ec):** `examples/05-workflow-hitl` — fresh
  `sterling-mutual` loan-disbursement closure (task with skill/agent/gate
  steps, workflow wrapper with exception ref + gate policy, agent +
  prompt artifacts, D-16 `HitlPolicy` with `signed_binding_required:
  true`, token table with an expired entry). run.py: factory-built
  workflow suspends at the gate with persisted state; approval travels
  `POST /hitl/actions` on `create_app(auth=BearerTokenAuth(...))` with a
  `sign_principal_binding`-produced binding; the audited principal is
  grant-derived. Negative refusals asserted against imported constants:
  `ERROR_UNAUTHENTICATED` (no token AND the artifact's expired token),
  `ERROR_SIGNED_BINDING_REQUIRED` (unsigned), `ERROR_SIGNED_BINDING_INVALID`
  (tampered) — nothing lands on the transport for any refusal. Dimension 2
  is byte-equal and contains the derived approver, the signed binding's
  signature, and the suspend-time product hash; dimension 5 is the
  engine's block verbatim. The escalation branch routes the failing step
  to its declared handler as a traced, audited `workflow_exception`.
- **Task 2 (14ed92e):** `examples/06-decision-replay` — fresh
  `boreal-grid` domain (substations/feeders/load-readings). `record()`:
  full L1→L6 pipeline, an `AnalyticsInsightsAgent` with an effective
  telemetry skill grant (dim 4 carries agent version AND grant-set hash),
  a load-shed workflow suspending at the gate, the same auth-bound door
  pattern for the approval, `serve()` through `ReplayWriter`, and the
  agent/prompt/grant artifacts landed in the same `FileArtifactStore`.
  `replay_decision()`: the replay engine reproduces the product
  **byte-equal** (canonical serializer); the agent definition resolves at
  its recorded content hash and matches the recorded URI version; the
  prompt and grant resolve content-addressed and check against pinned
  versions; `grant_set_hash` recomputes; the signed binding verifies from
  the record alone and reproduces the approver principal exactly.
  Negatives: `MovingTargetRefused` on a `LATEST_VERSION_TOKEN` ref, and a
  policy-version-mutated COPY of the record refuses with
  `ReplayUnresolvable`.

## Deviations from Plan

**1. [Rule 3 - Blocking] Door-submission-as-authority instead of gate resolution**
- **Found during:** Task 1 design
- **Issue:** The plan's flow implies the ApprovalGate resolves after the
  door submission, but `ApprovalGate.resolve` constructs an unsigned
  submission, which a `signed_binding_required` transport refuses — the
  two 08-03 features cannot compose that way.
- **Fix:** Per D-IMPL-62 the door submission (already D-16-verified at
  the transport authority path) is the authority landing; the driver, as
  the owning composition, builds the `HitlActionRecord` from the pending
  event + the door-recorded submission and consumes the event. This also
  makes the SignedPrincipalBinding part of the dimension-2 block, which
  the plan's assertions require and a gate-built submission could not
  provide.
- **Files modified:** examples/05-workflow-hitl/run.py, examples/06-decision-replay/run.py
- **Commit:** ee8b1ec, 14ed92e

Otherwise: none — both tasks landed as planned, first run green.

## Verification

- `make example-05` exit 0; `make example-06` exit 0 (byte-equality
  reproduction assertion inside)
- `grep -q BearerTokenAuth` and `grep -q sign_principal_binding` succeed
  in both run.py files
- `grep -rn "latest" examples/06-decision-replay/artifacts/ .../run.py`
  → no matches at all (token imported as a constant)
- `make lint` exit 0; `make typecheck` → clean (156 files)
- `make example-05 && make example-06` re-run green after both commits

## Known Stubs

None — every artifact value is consumed by a driver assertion; no
placeholder data, no unwired components.

## Threat Flags

None — all surface introduced was in the plan's threat model (T-08-17..19
mitigated as planned; T-08-20 accepted, READMEs state the tokens are
synthetic/illustrative).

## Self-Check: PASSED
