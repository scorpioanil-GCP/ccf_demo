---
phase: 07-phase-i-4-orchestration-hitl-experience
plan: 05
subsystem: replay
tags: [decision-replay, hitl, workflow, trace-correlation, d-impl-45, d-impl-55]
requires: []
provides:
  - "PolicyBindingsSnapshot.hitl_actions (dim 2) with NO_HITL_ACTIONS sentinel"
  - "ContentGenerationPath.workflow_step_sequence (dim 5) with NO_WORKFLOW_TRACE sentinel"
  - "dim-4 delegation_chain workflow-chain commitment proven and marked delivered"
  - "ccf.replay.correlation: ExternalTraceProviderProtocol, TraceCorrelation, NoOpTraceProvider, TraceCorrelationHook"
affects: [07-06 workflow engine, 07-07/07-08 HITL primitives]
tech-stack:
  added: []
  patterns: ["D-IMPL-55 three-edit extension pattern (doctrine line + positive sentinel + verbatim keyword)", "Protocol + reference-impl-in-one-module (state.py shape)"]
key-files:
  created:
    - src/ccf/replay/correlation.py
    - tests/replay/test_dimension_extensions.py
    - tests/replay/test_trace_correlation.py
  modified:
    - src/ccf/replay/record.py
    - tests/replay/test_harness_trace.py
decisions:
  - "HITL/workflow blocks are pre-serialized str fields (canonical bytes decoded), recorded verbatim — the builder never reconstructs, per T-07-09"
  - "TraceCorrelation payload is exactly {trace_provider, trace_id} — wider would be an ingestion, which D-IMPL-45 excludes"
  - "TraceCorrelationHook enriches HarnessTrace BEFORE build_replay_record; no new field/dimension/sentinel (T-07-10)"
metrics:
  duration: "~25 min"
  completed: "2026-07-30"
  tasks: 3
  tests: "49 replay tests passing; full suite 1002 passed, 2 skipped"
---

# Phase 7 Plan 05: Replay Dimension Extensions + D-IMPL-45 Delivery Summary

**One-liner:** Dimension 2/5 gained verbatim pre-serialized HITL/workflow slots with positive sentinels via the thrice-used D-IMPL-55 three-edit pattern, dimension 4's delegation_chain workflow commitment is proven delivered with no contract change, and the I.3 gate's TraceCorrelationHook handoff is discharged against the existing dim-3 harness_trace slot.

## What was built

- **Task 1 (TDD, commits 37c8f91 test / b21f8cf feat):** `PolicyBindingsSnapshot.hitl_actions: str = NO_HITL_ACTIONS` (dim 2) and `ContentGenerationPath.workflow_step_sequence: str = NO_WORKFLOW_TRACE` (dim 5); `build_replay_record` gains optional `hitl_actions` / `workflow_step_sequence` keywords, None → sentinel, recorded verbatim. Five-dimension structural assertion (INV-CH7-80), byte-equality, round-trip, and two-tenant (D-23/Ollama S5) tests all pass; existing-caller behavior unchanged.
- **Task 2 (commit 34559c6):** Verified `delegation_chain: tuple[str, ...]` already admits multi-element workflow chains — no type or signature change needed, exactly as the :258-266 commitment promised. Two-agent multi-element and two-tenant tests added; doctrine comment updated to delivered.
- **Task 3 (TDD, commits a5233d2 test / a32d583 feat):** `src/ccf/replay/correlation.py` — `ExternalTraceProviderProtocol` (runtime_checkable, keyword-only, single `correlate` obligation), `TraceCorrelation` contract, `NoOpTraceProvider` reference impl, and `TraceCorrelationHook` which composes a provider's payload into the existing `HarnessTrace.trace_provider`/`trace_id` fields before the block reaches `build_replay_record`. No-op byte-identity, in-slot landing with five-dimension assertion, and build-time-only capture all proven. record.py :184 reservation updated to delivered.

## Verification

- `pytest tests/replay` — 49 passed. Full suite — 1002 passed, 2 skipped.
- `mypy --strict src/ccf/replay/record.py src/ccf/replay/correlation.py` — clean.
- `tools.lints --all` — exit 0.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Extended the pre-existing byte-identity test's strip set**
- **Found during:** Task 1
- **Issue:** `tests/replay/test_harness_trace.py::test_every_pre_change_field_is_byte_for_byte_unchanged` compares against a pre-I.3 canonical literal after stripping only the I.3 `harness_trace` key; the new I.4 sentinel fields necessarily appear in the serialized record, failing the assertion. The plan's must_have explicitly allows "byte-identical except for the sentinel fields."
- **Fix:** The test now also strips `,"hitl_actions":"no-hitl-actions"` and `,"workflow_step_sequence":"no-workflow-trace"` before comparing — the assertion's meaning (only the named extension keys differ) is preserved and strengthened.
- **Files modified:** tests/replay/test_harness_trace.py
- **Commit:** b21f8cf

### Informational (no action, recorded per plan discipline)

- **D-IMPL-45 wording drift:** the DECISIONS.md D-IMPL-45 entry says the hook is "on replay dimension 5"; the later D-IMPL-55 ruling and PHASE_I3_GATE §5 both place the attachment at the dimension-3 `harness_trace` slot, and the plan follows them. Implemented against dim 3 per the plan and the gate handoff — no slot minted, no discrepancy requiring a stop.
- D-IMPL-45 also mentions "resolve at replay time" and a `{trace_url?, capture_time}` payload; the plan scopes v0 delivery to the single `correlate` obligation and the two fields the slot carries. Wider payloads/resolution are alternative-provider concerns behind the same Protocol.

## Known Stubs

None — `NoOpTraceProvider` is an honest reference implementation (no tracer configured → no correlation), not a placeholder.

## Threat Flags

None — no new network endpoints, auth paths, or trust-boundary schema beyond the plan's registered threat model (T-07-09/T-07-10, both mitigated by verbatim-block byte-equality tests and the five-dimension structural assertion).

## Self-Check: PASSED

- src/ccf/replay/correlation.py — FOUND
- tests/replay/test_dimension_extensions.py — FOUND
- tests/replay/test_trace_correlation.py — FOUND
- Commits 37c8f91, b21f8cf, 34559c6, a5233d2, a32d583 — FOUND
