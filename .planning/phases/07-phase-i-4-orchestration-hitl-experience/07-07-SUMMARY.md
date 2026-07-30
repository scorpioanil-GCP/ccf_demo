---
phase: 07-phase-i-4-orchestration-hitl-experience
plan: 07
subsystem: hitl-primitives
tags: [hitl, approval-gate, approval-sink, cinv-04, d-impl-20, d-impl-21, d-23, d-25, toctou, vertical-slice]
requires: [07-02, 07-04, 07-05, 07-06]
provides:
  - "ApprovalGate (src/ccf/hitl/approval_gate.py): the real suspending workflow-face HITL primitive — transport-surfaced pending decisions, HumanPrincipalBinding required by type, audited approve/reject, pre-serialized dim-2 HITL-action block yielded alongside the typed outcome"
  - "ApprovalSinkAdapter: thin sync grant face wrapping an already-completed bound GateResolution; decide never blocks and raises UnboundDecisionError when unbound"
  - "TOCTOU guard (T-07-39): suspend-time product_content_hash bound on the pending event; mismatch is a returned GateResolutionRefused audited resolved=False with the event left pending"
  - "D-01 vertical slice (tests/workflow/test_slice.py): factory-built two-step banking workflow suspends on the real gate, resumes on a bound approval, dims 2/5 byte-equal to the gate/engine serialized blocks"
  - "CINV-04 fully active: hitl-action-capture and workflow-trace-capture flipped with owning tests proven red under severed capture; suite skip count 0"
  - "hitl_action AuditAction member; payment-release banking fixtures; two-approver hitl.yaml fixture (D-23)"
affects: [07-08, 07-09, 07-12]
tech-stack:
  added: []
  patterns:
    - "Dual-face composition, never conflation: the async gate owns transport/suspend/binding; a thin adapter wraps a completed decision for the sync ApprovalSink seam and raises typed on an unbound decide"
    - "Pre-serialized verbatim replay blocks (07-05 keyword discipline) extended to dim 2: the gate serializes HitlActionRecord once; build_replay_record records it verbatim"
    - "D-22-scoped claims in docstrings: type-unrepresentable paths (unbound submission) named separately from lint/CI-covered paths (capture completeness via CINV-04 owning tests)"
key-files:
  created:
    - src/ccf/hitl/approval_gate.py
    - tests/hitl/test_approval_gate.py
    - tests/workflow/test_slice.py
    - tests/fixtures/banking/hitl.yaml
    - tests/fixtures/banking/tasks/payment_release_task.yaml
    - tests/fixtures/banking/workflows/payment_release_workflow.yaml
  modified:
    - src/ccf/hitl/__init__.py
    - src/ccf/controlplane/audit.py
    - tests/conformance/test_approval_sink.py
    - tests/invariants/test_replay_by_construction.py
decisions:
  - "ApprovalSink dual face resolved by composition as fixed in-plan (Cursor HIGH): ApprovalGate owns the async workflow face; ApprovalSinkAdapter satisfies the sync grant-scoped face by wrapping a completed bound decision — decide never blocks on a pending human and never fabricates a verdict"
  - "grants.py:24 'joins with zero state-machine change' honored as property-preserving: the GrantLedger state machine is byte-untouched and still owns every transition and audit record; what joins the conformance parametrization is the adapter, not the gate object itself"
  - "A TOCTOU refusal does NOT consume the pending event: the human can re-review the current product version and act on its hash; no action reaches the authority path on the refused attempt"
  - "hitl_action audit member carries rejections and TOCTOU refusals as resolved=False on the one shared log (the workflow_resumed refusal precedent)"
  - "The CINV-04 deferral machinery is removed rather than emptied: an empty parametrize over DEFERRED would itself emit a skip, breaking the 0-skip requirement — the discharged registry is active-only with an adversarial-case table per activated family"
metrics:
  duration: "~35 minutes"
  completed: "2026-07-30"
  tasks: 3
  commits: 5
---

# Phase 07 Plan 07: D-01 Vertical Slice — Real ApprovalGate + CINV-04 Activation Summary

Real ApprovalGate via honest dual-face composition (async transport/binding gate + sync ApprovalSinkAdapter), a factory-built two-step banking workflow suspending and resuming through it end to end with dims 2/5 byte-verbatim, and both CINV-04 deferrals discharged with observed red counterfactuals — suite at 0 skips.

## Task Commits

| Task | Name | Commit(s) | Files |
| ---- | ---- | --------- | ----- |
| 1 | ApprovalGate + ApprovalSinkAdapter + conformance slot join | `3c5f55d` (test), `00b4f1e` (feat) | src/ccf/hitl/approval_gate.py, src/ccf/hitl/__init__.py, src/ccf/controlplane/audit.py, tests/hitl/test_approval_gate.py, tests/conformance/test_approval_sink.py, tests/fixtures/banking/hitl.yaml |
| 2 | D-01 vertical slice test + banking fixtures | `fd0ae8d` (test), `54a311c` (feat) | tests/workflow/test_slice.py, tests/fixtures/banking/tasks/payment_release_task.yaml, tests/fixtures/banking/workflows/payment_release_workflow.yaml |
| 3 | Flip both CINV-04 checks; skip count to zero | `187ece9` | tests/invariants/test_replay_by_construction.py |

## What Was Built

- **`ApprovalGate`** — constructor-injected transport, audit log, clock. `resolve()` requires a `HumanPrincipalBinding` by signature; approval and rejection are both returned typed `GateResolution` values (rejection audited `resolved=False`, never an exception); the gate serializes the `HitlActionRecord` (event + submission + verdict) once into `hitl_actions_block`, the verbatim dim-2 payload. Approval-policy content stays in the WorkflowDefinition's `gate_policies` binding, carried as the pending event's pinned `policy_ref` (CINV-01 — no approval rule in code).
- **`ApprovalSinkAdapter`** — conforms structurally to `ApprovalSink`; wraps a completed `GateResolution`; `decide()` with nothing bound raises `UnboundDecisionError`. Joins `test_approval_sink.py` as the `approval-gate-adapter` param; `git diff main` on that file touches only imports and the fixture — zero test-body changes.
- **D-01 slice** — `verify-payment` (skill) → `treasury-approval` (hitl-gate) → `released`/`rejected`, all content in fixture artifacts; suspend-time hash binding, TOCTOU mutate-between test, two-approver distinguishability (D-23), rejection as a recorded transition, dims 2/5 byte-equality, and the two adversarial skip-the-landing cases.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Added `hitl_action` AuditAction member**
- **Found during:** Task 1
- **Issue:** The gate's audited outcomes (a plan behavior) had no expressible action — the `AuditAction` Literal had `workflow_*` and `grant_*` members only, and recording a human verdict under either would make the log say something untrue.
- **Fix:** Added the `hitl_action` member with doc-comment rationale; rejections/TOCTOU refusals travel in it as `resolved=False`.
- **Files modified:** src/ccf/controlplane/audit.py
- **Commit:** `00b4f1e`

**2. [Rule 3 - Blocking] Removed the CINV-04 deferral machinery entirely instead of emptying it**
- **Found during:** Task 3
- **Issue:** The acceptance criteria require both `grep -c "not-yet-applicable" == 0` and 0 skips; the phrase lived in the `CheckStatus` Literal, `DEFERRAL_PHRASE`, and the skip-emitting test, and pytest emits a skip for an empty parametrize set — flipping statuses alone could not satisfy either criterion.
- **Fix:** Rewrote the registry as active-only (every `Check` carries an owning test), added the adversarial-case table, kept the local structural assertions byte-identical.
- **Files modified:** tests/invariants/test_replay_by_construction.py
- **Commit:** `187ece9`

### Property-preserving note on grants.py:24

The letter of "I.4's real ApprovalGate joins with zero state-machine change" is honored as *property-preserving composition*: the `GrantLedger` state machine and its audit obligations are byte-untouched and still own every transition; what joins the reserved conformance parametrization is the `ApprovalSinkAdapter` carrying the gate's completed decision, because one object honestly doing both the async suspend face and the sync `decide` face would have to lie when no human has acted. This is the resolution fixed in the plan's review-response note, recorded here as required.

## CINV-04 D-25 Counterfactuals (verbatim red outputs)

**hitl-action-capture** — capture severed in `build_replay_record` (dim-2 pass-through replaced with the sentinel), owning test red:

```
_____________ test_the_human_action_lands_on_dimension_2_verbatim ______________
        block = replay.policy_bindings.hitl_actions
>       assert block == resolution.hitl_actions_block
E       assert 'no-hitl-actions' == '{"approved":..."acme-bank"}}'
E         - {"approved":true,"event":{"event_class":"approval-gate","event_key":"acme-bank/exec-1/treasury-approval",...,"product_content_hash":"547ebaff5ca906456d72083e19e5b39a8d8a3c05cdd3c83b11e11bc1ee8c57f5",...},"submission":{"action":"approve",...,"principal":{...,"approver":{"identity_provider_ref":"acme-bank/idp/okta","subject_id":"credit-officer-11"},...
FAILED tests/workflow/test_slice.py::test_the_human_action_lands_on_dimension_2_verbatim
1 failed in 0.15s
```

**workflow-trace-capture** — dim-5 pass-through severed, owning test red:

```
_____________ test_the_step_sequence_lands_on_dimension_5_verbatim _____________
>       assert (
            replay.content_generation_path.workflow_step_sequence
            == outcome.step_sequence_block
        )
E         - [{"kind":"transition",...,"source":"verify-payment","target":"treasury-approval"},{"kind":"suspend",...},{"kind":"resume",...,"target":"released"}]
E         + no-workflow-trace
FAILED tests/workflow/test_slice.py::test_the_step_sequence_lands_on_dimension_5_verbatim
1 failed in 0.14s
```

Both severs were restored immediately; `src/ccf/replay/record.py` is byte-identical to its pre-task state (verified by `git status` clean on that file).

## Verification

- `pytest tests/conformance/test_approval_sink.py tests/hitl tests/workflow/test_slice.py` — green, both sink params.
- `CCF_REQUIRE_HARNESSES=1 pytest -q` — **1120 passed, 0 skipped, 0 failed**.
- `mypy --strict` over `src` + `runtime` — clean (111 files).
- `tests/lints` — 28 passed (No-Hardcoding, CINV-01c, isolation lints).
- `grep -c "not-yet-applicable" tests/invariants/test_replay_by_construction.py` — 0.
- `git diff main -- tests/conformance/test_approval_sink.py` — no `def test_` lines touched.
- Gate/adapter docstrings carry the D-22 scope statement (grep "type-unrepresentable" — present in module, resolve(), and adapter docstrings).

## Known Stubs

None — no placeholder values, empty-data wirings, or TODO markers in the files created/modified by this plan.

## Threat Flags

None beyond the plan's own threat model: T-07-14 (binding required by type — conformance + gate tests), T-07-15 (CINV-04 active with red-proven owning test + adversarial case), T-07-39 (TOCTOU mutate-between test) are all mitigated as planned. No new network endpoints, auth paths, or trust-boundary schema changes were introduced.

## Self-Check: PASSED

- src/ccf/hitl/approval_gate.py — FOUND
- tests/workflow/test_slice.py — FOUND
- tests/fixtures/banking/{hitl.yaml, tasks/payment_release_task.yaml, workflows/payment_release_workflow.yaml} — FOUND
- Commits 3c5f55d, 00b4f1e, fd0ae8d, 54a311c, 187ece9 — FOUND in log
