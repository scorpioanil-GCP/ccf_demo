---
phase: 07-phase-i-4-orchestration-hitl-experience
plan: 04
subsystem: orchestration-hitl-contracts
tags: [workflow, hitl, factory, d-impl-61, d-impl-21, d-impl-20, orch-01, cinv-01c]
requires: [07-01]
provides:
  - "WorkflowDefinition contract + ccf.workflow-definition ArtifactClass (syntactic validation)"
  - "WorkflowFactory: registry-backed semantic validation + factory-built Workflow handle"
  - "HumanPrincipalBinding (D-IMPL-21) discharging the audit actor-doctrine hook"
  - "HITLTransportProtocol + InMemoryHitlTransport (D-IMPL-20)"
affects: [07-06, 07-07, 07-08]
tech-stack:
  added: []
  patterns:
    - "syntactic/semantic validation split: Pydantic contract checks local shape; factory checks against resolved artifacts"
    - "CINV-01c FACTORY_ONLY_NAMES extended to Workflow with explicit allowlist entry"
key-files:
  created:
    - src/ccf/workflow/__init__.py
    - src/ccf/workflow/definitions.py
    - src/ccf/workflow/factory.py
    - src/ccf/hitl/__init__.py
    - src/ccf/hitl/principal.py
    - src/ccf/hitl/transport.py
    - tests/workflow/test_definitions.py
    - tests/workflow/test_factory.py
    - tests/hitl/test_principal.py
    - tests/hitl/test_transport.py
    - tests/fixtures/banking/workflows/covenant_review_workflow.yaml
  modified:
    - tools/lints/no_hardcoding.py
    - tests/lints/test_cinv01c_behavioral.py
decisions:
  - "WORKFLOW_FAILED_STATE ('failed') is a reserved schema-declared terminal: D-IMPL-61 option-a needs a defined destination, so every workflow's effective_terminal_states includes it and it can never be a source or the start"
  - "Terminal reachability is computed over the declared transitions only — the implicit D-IMPL-61 exception transition is an exception path and does not rescue a nominal dead-end"
  - "Workflow handle is a plain frozen class (Task precedent), identity-agreement-checked in __init__, guarded by the CINV-01c lint rather than a construction token (D-12 precedent)"
  - "Gate-policy refs are resolved at factory time alongside exception refs — same pinned-resolvability rule, one discipline"
metrics:
  duration: "~35 min"
  completed: "2026-07-30"
---

# Phase 7 Plan 04: Workflow + HITL Contract Layer Summary

WorkflowDefinition wrapper with a syntactic/semantic validation split, WorkflowFactory making ORCH-01's factory path literal, and the HITL contract layer (HumanPrincipalBinding + HITLTransportProtocol) — all interface-first for 07-06/07/08.

## What Was Built

- **`src/ccf/workflow/definitions.py`** — `WorkflowDefinition` wraps a pinned TaskDefinition ref and adds ONLY transitions, terminal states, per-node exception refs (D-13), and per-gate approval-policy bindings (D-12). Local validators: URI pinning (`@latest` refused), transition-graph internal consistency, terminal declaration, reachability + terminal-reachability + no-unreachable-node over the declared graph, binding keys within declared names. D-IMPL-61 option-a implemented exactly: absent exception ref validates; the reserved terminal `failed` state is schema-declared (`WORKFLOW_FAILED_STATE`, `effective_terminal_states`), a valid transition target, and never a source. Module docstring names the factory-deferred semantic checks.
- **`src/ccf/workflow/factory.py`** — `WorkflowFactory.construct` resolves the wrapper and its wrapped TaskDefinition through Control Plane resolution only (shared `resolve_pinned`, IN-01), refuses a task ref bound to a non-`ccf.task-definition` class, enforces D-12 step-name agreement against the *resolved* task, gate-policy→hitl-gate kind agreement, and D-13 exception-ref/gate-ref resolvability. Returns a frozen `Workflow` handle with dual provenance (`WorkflowIdentity`: wrapper hash+URI and task hash+URI); no execution surface.
- **`src/ccf/hitl/principal.py`** — `HumanPrincipalBinding` with all four D-IMPL-21 fields required: `ApproverIdentity` (subject id + identity-provider ref into the D-IMPL-15 IdentityProvider family — no new mechanism), `AuthenticationContext`, injected `action_time`, sha256-shape-validated `product_content_hash` (D-IMPL-26). Discharges the `audit.py` actor-doctrine hook by name.
- **`src/ccf/hitl/transport.py`** — `HITLTransportProtocol` (runtime_checkable, keyword-only, state.py shape) over typed `PendingHitlEvent`/`HitlActionSubmission` contracts; `HitlActionSubmission.principal` is required by type. `InMemoryHitlTransport` reference impl with per-tenant FIFO queues (D-23). Docstring records the D-IMPL-20 authority/notify separation, names 07-08 as the webhook leg's single owning plan, and D-22-scopes the recording obligation to the primitives.
- **CINV-01c extension** — `Workflow` joined `FACTORY_ONLY_NAMES`; `ccf.workflow.factory` allowlisted; four new behavioral lint tests (bypass fires, alias bypass fires, allowlisted path exempt, real module exempt).

## Verification

- `tests/workflow` (28) + `tests/hitl` (22) green; full suite **1081 passed / 2 skipped**
- `git diff main -- src/ccf/agents/definitions.py` empty (D-12 byte-identical)
- `mypy --strict` clean (107 files); `tools.lints --all` exit 0
- TDD gate sequence per task: test(RED) commit → feat(GREEN) commit (7ba09e4→e712fee, f738a34→b1b4aa6, e0e34dc→2ac7d61, f9e18e9→ebf3b22)

## Deviations from Plan

None - plan executed exactly as written. (Two in-flight test corrections during Task 1 GREEN — `ArtifactClass.validate` takes an instance, and the cycle mutant needed its orphaned gate node removed — were test-authoring fixes inside the TDD loop, not plan deviations.)

## Known Stubs

None. `gate_policies`/`exception_refs` reference deployment-declared artifact classes by design (approval-policy semantics are 07-07's scope); nothing here renders empty or placeholder data.

## Threat Flags

None — all surfaces built match the plan's threat model (T-07-06/07/08/37 mitigations implemented: binding required by type, authority/notify separation encoded, extra=forbid + pinned refs + dual-layer validation, CINV-01c extended to workflows).

## Commits

| Task | RED | GREEN |
| ---- | --- | ----- |
| 1 WorkflowDefinition | 7ba09e4 | e712fee |
| 2 HumanPrincipalBinding | f738a34 | b1b4aa6 |
| 3 HITLTransportProtocol | e0e34dc | 2ac7d61 |
| 4 WorkflowFactory | f9e18e9 | ebf3b22 |

## Self-Check: PASSED

All created files exist on disk; all eight commit hashes present in `git log`.
