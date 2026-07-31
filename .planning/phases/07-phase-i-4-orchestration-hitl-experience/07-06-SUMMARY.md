---
phase: 07-phase-i-4-orchestration-hitl-experience
plan: 06
subsystem: orchestration-engine
tags: [workflow, engine, orch-01, d-impl-17, d-impl-18, d-impl-27, d-impl-61, d-14, d-23, hypothesis-stateful]
requires: [07-02, 07-04, 07-05]
provides:
  - "WorkflowEngine: async-first state-machine execution of WorkflowFactory-built handles (/runtime, D-14)"
  - "WorkflowStateRecord + WORKFLOW_STATE record class on the Control Plane state seam, defined next to the machine"
  - "Suspend/resume lifecycle: hitl-gate suspension via typed handle + InMemoryHitlTransport stub; audited (tenant, execution_id)-keyed state"
  - "Trace write-through to the ArtifactStore at suspend and terminal (D-IMPL-18); live suspended state native (D-IMPL-27)"
  - "Replay handoff: verbatim pre-serialized dim-5 step-sequence block + dim-4 workflow delegation chain (07-05 keywords)"
  - "workflow_* AuditAction members (transition/suspended/resumed/exception/completed)"
  - "hypothesis.stateful interleaving coverage across two tenants and two workflow definitions"
affects: [07-07, 07-08, 07-09, 07-12]
tech-stack:
  added: []
  patterns:
    - "GrantLedger discipline ported to /runtime: keyword-only constructor injection, SplitAuditPlaneError on a foreign audit log, opaque typed record with isinstance foreign-record error, one private audited-write helper"
    - "Harness-neutral node bindings: SkillNodeBinding/AgentNodeBinding Protocols the composition root binds onto skill dispatch and a harness-adapter-run agent — the engine names neither"
    - "Refusal doctrine at the engine: expected outcomes (suspension, exception routing, resume refusals) are typed returned CCFContract values audited resolved=False; broken wiring raises"
key-files:
  created:
    - runtime/ccf_runtime/workflow/__init__.py
    - runtime/ccf_runtime/workflow/state.py
    - runtime/ccf_runtime/workflow/engine.py
    - tests/workflow/test_engine.py
    - tests/workflow/test_engine_stateful.py
    - tests/fixtures/banking/tasks/certificate_refresh_task.yaml
    - tests/fixtures/banking/workflows/certificate_refresh_workflow.yaml
  modified:
    - src/ccf/controlplane/audit.py
decisions:
  - "Open Question 2 resolved in writing (module docstrings): workflow contracts are sync /src (07-04); the engine and its state record are /runtime per D-14 and the record-next-to-the-machine doctrine"
  - "Node execution travels two injected Protocols (SkillNodeBinding, AgentNodeBinding) rather than importing dispatch_skill or a harness adapter directly: the plan's 'existing skill dispatch' expects a full catalog/grant wiring the engine must not own, and direct wiring would put a dispatch target's transport inside the engine — the composition root binds both seams, the engine holds only the Protocol"
  - "Resume decisions name a declared transition target from the suspended gate (CINV-01: routing is the artifact's statement; no decision→state mapping constant exists in code); an undeclared decision is a typed refusal audited resolved=False"
  - "Exception with a bound ref suspends as status exception-routed (resumable retry) with the routed transition's target recorded as the pinned handler ref; absent ref transitions to the reserved failed terminal (D-IMPL-61 option-a) as a first-class audited event"
  - "Audit-event policy: state-changing events (suspend/exception-routed/terminal) ride the AuditedStateWriter write as the domain event — one event per write (INV-CH7-71); non-persisting transitions append workflow_transition directly to the one log; resume refusals reuse workflow_resumed with resolved=False (the failed-resolve precedent)"
  - "Terminal-state delegation chain is derived deterministically from the persisted trace + the handle (agent-step refs of visited nodes), so it reproduces across resume boundaries without in-memory carryover"
metrics:
  duration: "~50 min"
  completed: 2026-07-30
---

# Phase 07 Plan 06: Workflow Engine (ORCH-01 execution half) Summary

Async-first workflow state machine in /runtime executing WorkflowFactory-built handles only, with audited suspend/resume on the Control Plane seam, D-IMPL-18/27 trace persistence, and verbatim replay dims 4/5 handoff.

## What was built

- **`runtime/ccf_runtime/workflow/state.py`** — `WORKFLOW_STATE` record class, `TraceEntry`, and `WorkflowStateRecord` (frozen CCFContract: tenant, execution_id, current state, status, trace, pinned workflow-definition URI). Docstring states the Open Question 2 resolution and the D-IMPL-18/27 mutability split.
- **`runtime/ccf_runtime/workflow/engine.py`** — `WorkflowEngine` with `async execute` / `async resume`, accepting only the factory-built `Workflow` handle (`WorkflowExecutionTypeError` otherwise). Nodes dispatch by TaskStep kind: `skill`/`agent` through injected harness-neutral bindings (with a pinned-ref wiring check that raises `WorkflowWiringError` on an unresolvable ref), `hitl-gate` suspends — typed `WorkflowSuspended` handle, `PendingHitlEvent` enqueued on the injected `HITLTransportProtocol` (InMemoryHitlTransport stub only; the real ApprovalGate is 07-07's). Every transition audits to the one log; state persists exclusively through `AuditedStateWriter`; traces write through to the ArtifactStore at suspend and terminal as content-addressed canonical bytes; `WorkflowCompleted` carries the engine-serialized dim-5 block and dim-4 delegation chain.
- **`src/ccf/controlplane/audit.py`** — five `workflow_*` `AuditAction` members added as enum literals with a doctrinal comment.
- **Tests** — 14 behavior tests (`test_engine.py`, incl. byte-equality through `build_replay_record`'s 07-05 keywords) + a `RuleBasedStateMachine` suite (`test_engine_stateful.py`) over two tenants × two workflow shapes with four invariants; two new straight-line banking fixtures.

## Verification

- `tests/workflow` — 42 passed (engine 14, stateful 1 machine, prior contract/factory suites intact)
- Full suite: 1096 passed, 2 skipped
- `mypy --strict` (project config over src + runtime): clean
- `tools.lints --all`: exit 0 (no-hardcoding, harness-import, algorithmic, CINV-01c)
- Acceptance greps: 5 `async def` surfaces in engine.py; zero harness names under `runtime/ccf_runtime/workflow/`; the only `put(` is the ArtifactStore trace write — no raw token minting or state-store bypass

## Deviations from Plan

**1. [Task-structure] Milestone-2 engine surface landed with milestone 1's commit.**
- **Found during:** Task 2
- **Issue:** `resume`, trace write-through, and the replay handoff fields fell out naturally while implementing the milestone-1 state machine (suspension already required trace/persistence plumbing); the milestone-2 tests passed on first run.
- **Resolution:** Milestone commits stayed strict and in order; the milestone-2 commit pins the Task 2 behaviors (round-trip, D-IMPL-18/27 split, byte-equality on dims 4/5, audited refusals) and its message records the note. Investigated per the TDD fail-fast rule: the passing-RED cause is the known early landing, not a mis-aimed test.

**2. [Design resolution] Node bindings are injected Protocols, not direct imports of skill dispatch / a harness adapter.**
- **Found during:** Task 1
- **Issue:** `dispatch_skill` requires catalog entries, grant views, and registries the engine must not own, and a direct adapter import would name a harness in the engine tree.
- **Fix:** `SkillNodeBinding` / `AgentNodeBinding` Protocols; the composition root binds them onto the real dispatch and adapter surfaces. Harness-neutrality grep and CINV-02 lint stay clean by construction.

**3. [Rule 2 - scope] Added two straight-line banking fixture artifacts** (`certificate_refresh_task.yaml`, `certificate_refresh_workflow.yaml`) not listed in the plan's `files_modified`: a terminal-reaching skill-only workflow is untestable from the gated covenant fixture alone, and the No-Hardcoding Rule forbids inline definitions in tests.

## Known Stubs

- The hitl-gate interaction is deliberately the typed suspend handle + `InMemoryHitlTransport` only — 07-07 owns the real ApprovalGate semantics (explicit slice ownership per the plan's must-haves, not an accidental stub).

## Threat Flags

None — the plan's threat register is discharged: T-07-11 (isinstance-checked record, audited-write-only path, tenant keying), T-07-12 (audit-every-transition + stateful trace-completeness invariant), T-07-13 (no graph writer held; harness-import lint green), T-07-38 (factory-handle-only execute boundary). No new security surface beyond the register.

## Commits

- `04a3ff7` test(07-06): add failing tests for the workflow engine core
- `5f60ff2` feat(07-06): implement WorkflowStateRecord + async engine core (milestone 1)
- `09b71e1` test(07-06): pin resume, trace write-through, and replay landing (milestone 2)
- `a8e8e4f` test(07-06): hypothesis.stateful interleaving suite (milestone 3)

## Self-Check: PASSED

All 7 created files present on disk; all 4 task commits present in git log.
