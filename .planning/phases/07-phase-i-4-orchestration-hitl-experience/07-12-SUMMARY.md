---
phase: 07-phase-i-4-orchestration-hitl-experience
plan: 12
subsystem: orchestration-layer
tags: [orch-02, d-impl-17, d-impl-60, orchestration-protocol, langgraph, d-06-split, conformance]
requires: [07-06, 07-11]
provides:
  - "OrchestrationProtocol in /src with the driver-implements doctrine sentence written verbatim"
  - "in-SDK reference adapter (WorkflowEngineOrchestrationAdapter) over WorkflowEngine — the conformance reference leg"
  - "D-06 module-tree split: ccf_runtime.orchestration carve-out + bidirectional orchestration/adapters import-ban lint"
  - "factory-parametrized OrchestrationLeg conformance suite (ADK + Claude legs join in 07-13 without body changes)"
  - "LangGraph driver leg: StateGraph + interrupt/Command(resume=...) over the engine's public surface"
affects: [src/ccf/orchestration/, runtime/ccf_runtime/orchestration/, tools/lints/, tests/conformance/]
tech-stack:
  added: []
  patterns:
    - "driver-side outcome store: engine's typed outcomes never enter graph state channels, so nothing CCF-typed reaches the orchestrator's checkpointer (T-07-30)"
    - "per-leg NamedTuple (factory + optional PositionProbe) so shared bodies never name an SDK type"
key-files:
  created:
    - src/ccf/orchestration/{__init__,protocol}.py
    - runtime/ccf_runtime/orchestration/{__init__,reference}.py
    - runtime/ccf_runtime/orchestration/langgraph/{__init__,driver}.py
    - tools/lints/orchestration_imports.py
    - tests/lints/test_orchestration_imports.py
    - tests/conformance/test_orchestration.py
  modified:
    - tools/lints/harness_imports.py (ORCHESTRATION_MODULES carve-out entry)
    - tools/lints/__main__.py (orchestration-imports checker wired into --all)
decisions:
  - "Protocol verbs are start_execution/resume_execution — deliberately not the engine's execute/resume names, so the bare engine structurally fails the runtime_checkable isinstance check (the doctrine made structural, not just written)"
  - "outcome return types are CCFContract at the /src boundary: the concrete suspend/terminal contracts live beside the machine in /runtime (record-next-to-the-machine), and /src imports neither /runtime nor any orchestrator SDK"
  - "the in-SDK reference adapter lives in runtime/ccf_runtime/orchestration/reference.py (plan's sanctioned /runtime placement); only the Protocol is /src"
  - "replay equivalence is exact canonical-bytes equality (no modulo): fresh worlds with identical injected clocks consume identical ticks, so the leg's step-sequence block, delegation chain, and trace content address equal the reference leg's byte-for-byte"
metrics:
  duration: "~35 min"
  completed: 2026-07-30
  tests: "1257 passed / 0 skipped under CCF_REQUIRE_HARNESSES=1 (baseline 1232 + 25 new); mypy --strict clean (147 files); tools.lints --all exit 0"
---

# Phase 7 Plan 12: OrchestrationProtocol + D-06 Split + LangGraph Driver Leg Summary

One-liner: opened the D-IMPL-60 orchestrator wave — `OrchestrationProtocol` in /src with the driver-implements doctrine, the lint-enforced orchestration/adapters module split with D-24 negative tests in both directions, a factory-parametrized conformance suite, and the LangGraph driver leg proving byte-identical replay obligations against the in-SDK reference adapter.

## What was built

**Task 1 — OrchestrationProtocol + in-SDK reference adapter** (commits `a11cabd` RED, `a6e6897` GREEN)

- `src/ccf/orchestration/protocol.py`: `runtime_checkable`, keyword-only `start_execution` / `resume_execution` taking WorkflowFactory-built `Workflow` handles and returning the engine's typed outcomes at the `CCFContract` boundary. The doctrine sentence is verbatim in the module docstring ("…not a third peer harness"). Identical-replay-obligations claim stated D-22-scoped (type-system-enforced surface; obligations proven by the conformance suite). Zero harness imports; `__ccf_mode__ = "algorithmic"`.
- `runtime/ccf_runtime/orchestration/reference.py`: `WorkflowEngineOrchestrationAdapter`, a thin delegating class — the isinstance target is the adapter, never the engine, and `test_the_bare_engine_is_not_the_isinstance_target` makes that structural (the Protocol's verb names differ from the engine's, so the engine fails the structural check by construction).

**Task 2 — D-06 split lint + guarded carve-out** (commit `0ff0bb2`)

- `ORCHESTRATION_MODULES = frozenset({"ccf_runtime.orchestration"})` — its own considered CINV-02 carve-out entry (distinct constant, dot-bounded), not a widened prefix.
- `tools/lints/orchestration_imports.py` (`d06-orchestration-split`): bans imports bidirectionally between `ccf_runtime.orchestration.*` and `ccf_runtime.adapters.*`; wired into `tools.lints --all` (D-07 blocking gate).
- All four plan-named negative tests pass: harness import in `ccf_runtime.peering` still fails, in `ccf_runtime.cdc` still fails, orchestration→adapters fails, adapters→orchestration fails; plus a `ccf_runtime.orchestration_evil` lookalike-sibling boundary test.

**Task 3 — conformance suite + LangGraph driver leg** (commits `a11cabd` RED, `9b68b2f` GREEN)

- `tests/conformance/test_orchestration.py`: `OrchestrationLeg` NamedTuple (leg_id, driver factory, optional `PositionProbe`), params `("in-sdk", "langgraph")` — 07-13 appends `"adk"` and `"claude-agent"` without touching bodies. Reuses `harness_unavailable` / `CCF_REQUIRE_HARNESSES=1` machinery; absent-SDK skip names the SDK and the extra.
- Shared bodies: structural conformance; end-to-end payment-release drive (skill step → real `ApprovalGate` suspension → approve → resume to `released` terminal); replay equivalence (canonical-bytes-equal step-sequence block, delegation chain, and trace content address vs the reference leg, D-23 two-tenant keying through the driver seam).
- `runtime/ccf_runtime/orchestration/langgraph/driver.py`: authors its own two-node `StateGraph` (`drive`, `gate`) against the engine's public surface — nothing read from the adapter tree (grep for adapter imports: zero hits; lint enforces it). Gate node parks on `interrupt({gate, event_key})`; `Command(resume=decision)` replays it and hands the decision to the engine's own `resume`. `InMemorySaver` holds graph position plus two scalar channels only; the engine's outcomes live in a driver-side dict, and `checkpointed_values()` is the introspection seam the T-07-30 assertion runs over (every persisted value asserted `str|bool|int`, never a `CCFContract`).

## Threat register dispositions

- **T-07-30 (orchestrator holding authoritative state)** — mitigated and tested: suspended `WorkflowStateRecord` on the Control Plane store; checkpointer values contain no CCF state.
- **T-07-31 (driver reaching adapter internals / loop absorption)** — mitigated: bidirectional lint + negative tests both directions.
- **T-07-32 (external drive escaping replay)** — mitigated: replay-equivalence body compares canonical bytes against the reference leg.

## Deviations from Plan

**1. [Rule 3 - Blocking] Worktree base drift corrected at startup** — worktree HEAD's merge-base with the expected base commit `8fc42be` was an ancestor; reset per the spawned branch-check protocol before any work.

**2. Minor placements within plan intent:** `runtime/ccf_runtime/orchestration/__init__.py` and `reference.py` were created in Task 1 (the reference adapter is Task 1's conformance target; the plan listed the `__init__` under Task 2's files). Task 1's behavior tests live in `tests/conformance/test_orchestration.py` (the plan's Task 3 file) rather than a new test module — the plan's `-k orchestr` verify command covers them and no extra file leaves the plan's file list.

No other deviations — no auth gates, no architectural changes.

## Verification

- `CCF_REQUIRE_HARNESSES=1 pytest`: **1257 passed, 0 skipped, 0 failed** (baseline 1232 + 15 conformance + 10 lint tests).
- `mypy --strict` (pyproject files=src,runtime): clean, 147 files.
- `python -m tools.lints --all`: exit 0.
- Acceptance greps: `class OrchestrationProtocol` + `runtime_checkable` present; "not a third peer harness" verbatim; zero `langgraph|google|claude` hits in `src/ccf/orchestration/`; zero adapter imports under `runtime/ccf_runtime/orchestration/`; `ccf_runtime.orchestration` distinct frozenset entry in the harness lint.

## Self-Check: PASSED

- All created files exist on disk (src/ccf/orchestration/protocol.py, runtime/ccf_runtime/orchestration/langgraph/driver.py, tools/lints/orchestration_imports.py, tests/conformance/test_orchestration.py, tests/lints/test_orchestration_imports.py).
- Commits a11cabd, a6e6897, 0ff0bb2, 9b68b2f present in `git log`.
