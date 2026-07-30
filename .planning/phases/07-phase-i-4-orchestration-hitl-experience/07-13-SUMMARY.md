---
phase: 07-phase-i-4-orchestration-hitl-experience
plan: 13
subsystem: orchestration
tags: [d-impl-60, orchestration-protocol, adk, claude-agent-sdk, conformance, probe]
requirements: [ORCH-02]
dependency-graph:
  requires:
    - "07-12: OrchestrationProtocol, in-SDK reference adapter, LangGraph leg, factory-parametrized conformance suite, d06-orchestration-split lint"
  provides:
    - "AdkWorkflowDriver (D-IMPL-60 leg 2) — SequentialAgent composition driving the CCF engine"
    - "ClaudeAgentWorkflowDriver (D-IMPL-60 leg 3) — ClaudeSDKClient session over the SDK's public custom-Transport seam"
    - "Claude feasibility probe (tests/spikes) — the phase's largest external risk, answered GO early"
    - "Conformance suite at four legs (in-sdk, langgraph, adk, claude-agent), shared bodies unchanged"
  affects:
    - "07-14+ (gate wave): D-IMPL-60 evidence now complete — three real legs plus reference"
tech-stack:
  added: []
  patterns:
    - "Scripted in-process Transport: play the wire's role only; run the real SDK session machinery (control protocol, hooks, SDK-MCP routing) with no model/network/CLI (D-09)"
    - "Orchestrator holds position only: ADK session state / Claude session transcript carry scalars; typed CCF outcomes stay driver-side (T-07-33)"
key-files:
  created:
    - tests/spikes/__init__.py
    - tests/spikes/test_claude_driver_probe.py
    - runtime/ccf_runtime/orchestration/adk/__init__.py
    - runtime/ccf_runtime/orchestration/adk/driver.py
    - runtime/ccf_runtime/orchestration/claude_agent/__init__.py
    - runtime/ccf_runtime/orchestration/claude_agent/driver.py
  modified:
    - tests/conformance/test_orchestration.py  # leg params + build branches ONLY; no shared-body edits
decisions:
  - "Probe verdict GO (recorded before Task 3 began): all three load-bearing Claude surfaces expressible — no escalation to Dave needed"
  - "Claude leg runs the real ClaudeSDKClient machinery over the SDK's exported custom Transport seam; the scripted transport plays only the CLI/wire role, because D-09 forbids a model call and a workflow drive must be deterministic for replay equivalence"
  - "ADK suspension surfaces as control returning to CCF between Runner runs (ADK has no interrupt primitive); resume is a second run over the resume segment"
metrics:
  duration: "9 minutes"
  completed: 2026-07-30
  tasks: 3
  tests: "1268 passed / 0 skipped / 0 failed under CCF_REQUIRE_HARNESSES=1 (baseline 1257 + 11 new)"
---

# Phase 07 Plan 13: ADK + Claude Agent SDK Driver Legs Summary

**One-liner:** D-IMPL-60 complete — Google ADK (SequentialAgent composition) and Claude Agent SDK (ClaudeSDKClient + hooks/tools over the SDK's public custom-Transport seam) driver legs join the conformance suite with every shared body unchanged, after an early feasibility probe answered GO on the Claude leg's expressibility.

## Probe Outcome (Task 1 — recorded before any full-leg work)

**Verdict: GO.** `tests/spikes/test_claude_driver_probe.py` passed green on its first run. Against the predefined escalation artifact's attempted-surfaces list:

1. **ClaudeSDKClient session with CCF-node-advancement exposed as tools** — WORKS. SDK-MCP `tools/call` routes through the SDK's own control protocol into in-process `@tool` handlers calling the `OrchestrationProtocol` reference adapter; both node advancements (start-to-gate, gate-to-terminal) travelled as tool invocations.
2. **Hook surface intercepting the hitl-gate** — WORKS. `CanUseTool` was consulted for every call and honoured; a `PostToolUse` `HookCallback` fired at the gate with the CCF suspend handle (`treasury-approval`, engine's own `event_key`) obtainable driver-side.
3. **Session resume/continuation after the bound decision** — WORKS. A second `client.query` on the live session (and, in the full driver, continuation via the same `session_id`) resumed the suspended execution through the engine's own `resume` to `terminal_state == "released"`. `ForkSessionResult` was not needed.
4. **Interrupt/streaming-control surfaces** — not needed; suspension maps onto the turn boundary (the result frame ends the turn, control returns to CCF).

**The one honest caveat, stated precisely:** the SDK's *default* transport spawns the `claude` CLI toward a live model, which the D-09 discipline (no model, no network — same guard as the harness conformance suite, asserted via socket monkeypatch) forbids. The probe and driver therefore run the real SDK session machinery — initialize handshake, hook registration/dispatch, permission callbacks, SDK-MCP JSONRPC routing, message parsing, session continuation — over a scripted in-process `Transport` (a **public, exported** SDK seam: `claude_agent_sdk.Transport`, documented for custom connections). The scripted side plays only the wire's role: it decides *when* tools are invoked, which for a deterministic workflow drive is not a model decision (replay equivalence would forbid one). This is the same species of choice the harness suite already made for all three SDKs ("real SDK objects on real code paths, no model") and is not a narrowed claim: every conformance body passes with bodies unchanged.

## What Was Built

### Task 2 — `AdkWorkflowDriver` (leg 2)
- `SequentialAgent` composition per drive: an engine-invoking segment (`BaseAgent` subclass with `_run_async_impl`, ADK's sanctioned no-model execution path, run by a real `Runner`) followed by a gate-park segment that records scalar position and ends the run — suspension surfaces as control returning to CCF between ADK invocations.
- ADK's `InMemorySessionService` holds scalar position only (`ccf_execution_id`, `ccf_suspended`, `ccf_segment` via `EventActions.state_delta`); typed outcomes stay driver-side. `persisted_state()` is the suite's T-07-33 introspection seam.
- Resume is a second ADK run over the resume segment with the externally-bound decision handed to the engine's own `resume`.

### Task 3 — `ClaudeAgentWorkflowDriver` (leg 3)
- Per-turn `ClaudeSDKClient` session: node advancement as SDK-MCP tool invocations (`advance_workflow` / `resume_workflow`) against the engine's public surface; `CanUseTool` gates every call; a `PostToolUse` hook yields the parked gate; resume continues the same `session_id`.
- `_ScriptedSessionTransport` plays the CLI side of the control protocol in-process (initialize acknowledgement + hook-id capture, `can_use_tool` / `mcp_message` / `hook_callback` requests, result frame per turn).
- `session_transcript()` exposes the scalar session position for the T-07-33 body.

### Conformance suite
- `ORCHESTRATION_PARAMS` now `("in-sdk", "langgraph", "adk", "claude-agent")`; the diff on `test_orchestration.py` is leg params + `build_orchestration_leg` branches only — **zero shared-body edits** (verified by diff at each RED commit).
- Absent-SDK skips name the module and the extra (`google.adk` / `adk`, `claude_agent_sdk` / `claude-agent`) via the shared `harness_unavailable` machinery; `CCF_REQUIRE_HARNESSES=1` turns skips into failures.

## Verification

- Orchestration conformance: **25/25 green** (5 bodies × 4 legs + 5 suite-mechanism tests), bodies unchanged from 07-12.
- Full suite: **1268 passed / 0 skipped / 0 failed** under `CCF_REQUIRE_HARNESSES=1` (baseline 1257 + 5 adk + 5 claude-agent + 1 probe).
- `mypy --strict` over `src` + `runtime`: clean (one targeted `type: ignore[no-untyped-call]` on ADK's unannotated `InMemorySessionService()` constructor, comment-justified).
- `python -m tools.lints --all`: clean (no-hardcoding, harness-imports incl. the orchestration carve-out, algorithmic, d06-orchestration-split).
- `grep -rn "ccf_runtime.adapters" runtime/ccf_runtime/orchestration/{adk,claude_agent}/`: zero hits.

## Deviations from Plan

### Auto-fixed / noted
**1. [Rule 3 - Blocking] Worktree base drift corrected at start** — the worktree HEAD was ahead of the plan's base commit; reset to `56f9573` per the spawn contract before any work.

**2. [Note] ADK `SequentialAgent` is deprecated at google-adk 2.5.0** (in favor of `Workflow`, which "cannot yet be used as an LlmAgent sub-agent"). The plan's verified-interface ruling names `SequentialAgent`, so it is used; the deprecation emits warnings only. Logged to `deferred-items.md` for a future pin-bump wave.

**3. [Minor] Package docstrings reworded** to keep the plan's literal acceptance grep (`ccf_runtime.adapters`) at zero hits — the langgraph leg's docstring convention mentioned the adapter tree by path, which the `.`-wildcard grep would match.

Otherwise executed as written: probe → ADK → Claude, with TDD RED/GREEN commits per driver task.

## TDD Gate Compliance

- Task 2: `test(07-13)` 53dba9b (RED, 5 adk errors) → `feat(07-13)` 009f819 (GREEN).
- Task 3: `test(07-13)` ea09844 (RED, 5 claude-agent errors) → `feat(07-13)` d00d6e8 (GREEN).
- No refactor commits needed.

## Commits

| Commit | Message |
| --- | --- |
| e219a63 | test(07-13): Claude Agent SDK feasibility probe — GO |
| 53dba9b | test(07-13): add failing adk leg param to orchestration conformance suite |
| 009f819 | feat(07-13): Google ADK OrchestrationProtocol driver leg (D-IMPL-60 leg 2) |
| ea09844 | test(07-13): add failing claude-agent leg param to orchestration suite |
| d00d6e8 | feat(07-13): Claude Agent SDK OrchestrationProtocol driver leg (D-IMPL-60 complete) |

## Known Stubs

None — both drivers run real SDK objects on real code paths; no placeholder data, no mocked leg.

## Threat Flags

None beyond the plan's register. T-07-33 (SDK state divergence) is asserted by the shared engine-authoritative body over both new legs' position seams; T-07-34 (replay escape) by the shared replay-equivalence body running unchanged on every leg.

## Self-Check: PASSED

All created files exist on disk; all five task commits present in git log; working tree clean of unintended changes; no STATE.md/ROADMAP.md modifications.
