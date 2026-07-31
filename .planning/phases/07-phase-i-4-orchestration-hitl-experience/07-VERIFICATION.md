---
phase: 07-phase-i-4-orchestration-hitl-experience
verified: 2026-07-30T00:00:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
---

# Phase 7: Phase I.4 — Orchestration, HITL, Experience Verification Report

**Phase Goal:** Multi-agent workflows with human gates execute, suspend, and resume with every human action and trace replay-recorded, reachable through the three v0 front doors
**Verified:** 2026-07-30 (on `main` post-merge, per D-26)
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Workflow primitive executes state-machine workflows with skill/agent/HITL-gate nodes; definitions are Control Plane artifacts via the Task Factory; suspended state persists at Control Plane boundary (D-IMPL-18) and resumes; traces land in replay dims 4/5 | ✓ VERIFIED | `runtime/ccf_runtime/workflow/engine.py` (784 lines) accepts only `WorkflowFactory`-built handles (typed rejection at line 658), writes via `AuditedStateWriter` (line 291), calls `build_replay_record`; `src/ccf/workflow/definitions.py` + `factory.py` implement the wrapper contract; `tests/workflow/test_slice.py` D-01 end-to-end slice passes; `tests/workflow/test_engine_stateful.py` hypothesis.stateful suspend/resume coverage |
| 2 | All four HITL primitives write to Decision Replay by construction; CI verifies no unrecorded human action | ✓ VERIFIED | `src/ccf/hitl/{approval_gate,escalation,override,review_queue}.py` all exist, substantive (317–433 lines), all require `HumanPrincipalBinding`; override records both original and override value; escalation uses real `assess_debt`/`DebtProfile`; review_queue makes lineage-free items unconstructible; both CINV-04 checks active in `tests/invariants/test_replay_by_construction.py`; suite skip count 0 |
| 3 | OrchestrationProtocol allows external orchestrator to drive workflows without touching SDK internals | ✓ VERIFIED | `src/ccf/orchestration/protocol.py` (`class OrchestrationProtocol(Protocol)`, line 67); three real driver legs (`langgraph`, `adk`, `claude_agent` under `runtime/ccf_runtime/orchestration/`) plus in-SDK reference, all four passing the factory-parametrized `tests/conformance/test_orchestration.py` (`ORCHESTRATION_PARAMS = ("in-sdk", "langgraph", "adk", "claude-agent")`) with unchanged shared bodies; `tools/lints/orchestration_imports.py` enforces D-06 bidirectional split (lints exit 0) |
| 4 | All three front doors work: MCP edge (products + agents), `ccf` CLI (D-IMPL-22 noun set), HTTP API with valid OpenAPI (D-IMPL-23) | ✓ VERIFIED | `runtime/ccf_runtime/mcp/{experience,hitl_server}.py` on distinct modules from egress/artifact roles (`tests/invariants/test_mcp_role_separation.py` new rows); CLI commands cover all eight nouns (`agent, artifact, config, hitl, product, replay, skill, workflow` + `skill import`), thin httpx client with `--local` sharing `ApiDependencies` by type; `tests/http_api/test_openapi.py` asserts `openapi == "3.1.0"` from the emitted document; `tests/http_api/test_routes.py` asserts noun set-equality against the D-IMPL-22 ruling text |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `docs/DECISIONS.md` D-IMPL-60/61, D-GATE-I.4 | Rulings + gate entry | ✓ VERIFIED | All present, dated 2026-07-29/30, approver Dave; D-IMPL-62..65 also ruled |
| `src/ccf/controlplane/state.py` | Token-gated put + audited write surface | ✓ VERIFIED | `_STATE_WRITE_TOKEN` identity check (line 113–114); `tests/invariants/test_state_seam_closure.py` exists |
| `src/ccf/skills/toolsurface.py` | Shared tool-surface derivation | ✓ VERIFIED | All three adapters import `from ccf.skills.toolsurface import` (grep -l confirms all three) |
| `src/ccf/workflow/{definitions,factory}.py` | WorkflowDefinition wrapper + WorkflowFactory | ✓ VERIFIED | 290/284 lines, `ccf.workflow-definition` class |
| `src/ccf/hitl/*` (7 modules incl. webhook) | Four primitives + principal + transport + D-IMPL-64 webhook | ✓ VERIFIED | All substantive; webhook.py shipped in-phase per D-IMPL-64 rejection of deferral |
| `src/ccf/replay/correlation.py` | D-IMPL-45 TraceCorrelationHook delivery | ✓ VERIFIED | 128 lines, hooks into existing dim-3 `harness_trace` slot |
| `runtime/ccf_runtime/workflow/{engine,state}.py` | Async-first state machine + WorkflowStateRecord | ✓ VERIFIED | 784/141 lines |
| `runtime/ccf_runtime/orchestration/{langgraph,adk,claude_agent}/driver.py` + `reference.py` | Three D-IMPL-60 legs + reference | ✓ VERIFIED | 181/272/419 lines; all name OrchestrationProtocol and drive WorkflowEngine |
| `runtime/ccf_runtime/mcp/{experience,hitl_server}.py` | EXPR-01 front door | ✓ VERIFIED | 377/264 lines; hitl_server requires complete HumanPrincipalBinding, no reduced variant |
| `runtime/ccf_runtime/http_api/` (app, dependencies, routes) | EXPR-03 front door | ✓ VERIFIED | FastAPI app factory, `ApiDependencies` bundle |
| `runtime/ccf_runtime/cli/` (main + 9 command modules) | EXPR-02 front door | ✓ VERIFIED | noun-verb dispatcher, httpx + `--local` over `ApiDependencies` |
| `tests/spikes/test_claude_driver_probe.py` | Claude leg feasibility probe | ✓ VERIFIED | Exists; leg proceeded (GO outcome, per gate) |
| `docs/PHASE_I4_GATE.md` | Gate package | ✓ VERIFIED | Present with D-22-scoped criterion-2 rows, sweep evidence, cross-AI triage §7 |

### Key Link Verification

| From | To | Via | Status |
| --- | --- | --- | --- |
| adapters (all 3) | `ccf.skills.toolsurface` | shared derivation import | ✓ WIRED |
| workflow engine | `WorkflowFactory` handles | typed-only input, raw definition rejected | ✓ WIRED |
| workflow engine | `controlplane/state.py` | `AuditedStateWriter` only | ✓ WIRED |
| workflow engine / HITL primitives | `replay/record.py` | `build_replay_record` verbatim blocks | ✓ WIRED |
| `skills/grants.py` | audited state path | `_put_state` (lines 518/785/808) | ✓ WIRED |
| HITL primitives | `HumanPrincipalBinding` | required on every action | ✓ WIRED |
| orchestration drivers | `WorkflowEngine` | drive engine; adapters/orchestration split lint-enforced (`d06-orchestration-split`) | ✓ WIRED |
| CLI | HTTP API | httpx + `ApiDependencies` `--local` | ✓ WIRED |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Full suite green, 0 skips | `CCF_REQUIRE_HARNESSES=1 PYTHONPATH=src:runtime .venv/bin/python -m pytest -q` | 1280 passed, 0 skipped/failed, 89.2s | ✓ PASS |
| Strict typing | `mypy --strict src runtime tools` | Success: no issues in 164 source files | ✓ PASS |
| All CI lints (No-Hardcoding, harness imports, @algorithmic, d06-orchestration-split) | `python -m tools.lints --all` | exit 0 | ✓ PASS |

(Gate document claims 1280/0/0 and mypy clean — independently reproduced here; not taken on trust.)

### Requirements Coverage

| Requirement | Source Plans | Status | Evidence |
| --- | --- | --- | --- |
| ORCH-01 | 07-01..07 | ✓ SATISFIED | Truth 1 |
| ORCH-02 | 07-12, 07-13 | ✓ SATISFIED | Truth 3 |
| HITL-01 | 07-03..09 | ✓ SATISFIED | Truth 2 |
| EXPR-01 | 07-09 | ✓ SATISFIED | Truth 4 (MCP edge) |
| EXPR-02 | 07-11 | ✓ SATISFIED | Truth 4 (CLI) |
| EXPR-03 | 07-10 | ✓ SATISFIED | Truth 4 (HTTP/OpenAPI 3.1.0) |

No orphaned requirements: REQUIREMENTS.md maps exactly these six IDs to Phase 7, all marked Complete, and all six appear in plan frontmatter.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| — | — | none | — | Zero TBD/FIXME/XXX/TODO/HACK markers in phase-modified source trees; "placeholder" grep hits are docstrings stating "not a placeholder" |

### Human Verification Required

None. Every success criterion is exercised by the automated suite (end-to-end slice, four-leg conformance, OpenAPI validity, CLI dispatch tests); no visual/UX surface ships in this phase. The unauthenticated v0 HTTP surface (T-07-24) is a recorded residual deployment risk in the gate, not a verification gap.

### Gaps Summary

No gaps. Phase goal achieved with direct codebase evidence at all four levels (existence, substance, wiring, behavior). One bookkeeping note (informational, not a gap): the ROADMAP.md Phase 7 checklist still shows `07-14-PLAN.md` unchecked even though the gate completed, D-GATE-I.4 is logged, and phase-i4 is merged to main.

---

_Verified: 2026-07-30_
_Verifier: Claude (gsd-verifier)_
