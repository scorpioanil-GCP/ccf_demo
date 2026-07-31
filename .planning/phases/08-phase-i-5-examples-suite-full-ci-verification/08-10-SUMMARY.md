---
phase: 08-phase-i-5-examples-suite-full-ci-verification
plan: 10
subsystem: examples
tags: [examples, harness-portability, exam-04, a3-discharge, e-commerce, d-impl-24]
requires: [08-04, 08-05]
provides:
  - "examples/03-harness-portability deterministic base leg green via make example-03 (EXAM-04, D-01/D-02)"
  - "Advisory A3 discharged: tests/conformance/test_a3_discharge.py drives a real SDK-produced ResultMessage through the Claude adapter's seam-4 path"
  - "Fresh atlas-commerce e-commerce artifacts incl. ONE shared agent definition and per-harness deployment values"
affects: [08-11 live legs, 08-12 CI examples job, phase gate A3 status]
tech-stack:
  added: []
  patterns:
    - "Real harness loop machinery over scripted transports: ClaudeSDKClient + custom Transport, ADK Runner + InMemorySessionService, compiled LangGraph graph — all under a process-global socket guard"
    - "Per-leg record built from that leg's own recovered product bytes, so dimension-5 product_content_address has teeth"
key-files:
  created:
    - examples/03-harness-portability/run.py
    - examples/03-harness-portability/README.md
    - examples/03-harness-portability/legs/__init__.py
    - examples/03-harness-portability/legs/deterministic.py
    - examples/03-harness-portability/artifacts/ontology.yaml
    - examples/03-harness-portability/artifacts/events.yaml
    - examples/03-harness-portability/artifacts/controlplane.yaml
    - examples/03-harness-portability/artifacts/prompt.yaml
    - examples/03-harness-portability/artifacts/harnesses.yaml
    - examples/03-harness-portability/artifacts/agents/order_insights.yaml
    - tests/conformance/test_a3_discharge.py
  modified: []
decisions:
  - "The Claude leg's session runs over the adapter's OWN seam-1 carrier (the ClaudeAgentOptions inject_context built), so the SDK-constructed ResultMessage came out of the same configuration the harness would live under — stronger than a bare default-options session"
  - "A3 required zero adapter change: the RED test passed immediately because the advisory named missing evidence, not missing behavior; the test + example leg are the evidence, and the isinstance gate is regression-pinned"
  - "legs/deterministic.py imports all three harness SDKs unconditionally — a missing harness is an ImportError failure, mirroring CCF_REQUIRE_HARNESSES with no skip path"
metrics:
  duration: "~18 min"
  completed: "2026-07-31"
---

# Phase 08 Plan 10: Example 03 deterministic legs + A3 discharge Summary

One atlas-commerce agent definition executed unmodified under real
ClaudeSDKClient/ADK-Runner/LangGraph loop machinery with byte-level
equivalence asserted across the three legs, and advisory A3 closed with a
genuinely SDK-produced `ResultMessage` through the Claude adapter's seam 4.

## What was built

- **Task 1 (3bcba71):** `examples/03-harness-portability/` — fresh
  e-commerce artifacts (tenant `atlas-commerce`: customer/order/catalog_item
  ontology, four-envelope stream with dual-source lineage accumulation, a
  similarity-ranked-out routine order, a restricted age-gated catalog item
  the policy operator substitutes out; per-harness deployment values in
  `harnesses.yaml`; exactly ONE agent definition in `artifacts/agents/`).
  `legs/deterministic.py` builds all three D-IMPL-24 adapters and drives
  the four seams per leg with the seam-4 execution produced by **real loop
  machinery**: (a) a real `ClaudeSDKClient` session over a scripted
  in-process `Transport` whose result frame the SDK's own parser turns into
  a `ResultMessage`; (b) a real ADK `Runner` over an
  `InMemorySessionService` driving the adapter's execution vehicle; (c) the
  adapter's real compiled LangGraph graph with reported values on
  LangChain's own tracing keys. A process-global socket guard is installed
  and probe-asserted before any leg runs. `run.py` (`--mode
  deterministic|live --provider ollama|anthropic`; live exits 2 pointing at
  plan 08-11) boots the full L1→L6 fabric from artifacts, factory-constructs
  the one agent, serves and consumes a gated product, renders the pinned
  instruction once, then asserts: product bytes recovered from each carrier
  identical across legs and equal to the fabric's admitted bytes; governed
  replay fields (D-18 set) exactly equal field by field; one governed
  emission; three distinct harness traces each carrying its own harness's
  reported model/trace id/token counts; five typed dimensions per record.
  README with the invariant/what-would-fail table and change-first guidance.
- **Task 2 (1036271):** `tests/conformance/test_a3_discharge.py` — a real
  `ClaudeSDKClient` session over a scripted `Transport` (fixture values
  from `tests/fixtures/banking/harnesses.yaml`, wire field names the SDK's
  own — `modelUsage`) produces the SDK-constructed `ResultMessage`; driven
  through `ClaudeAgentAdapter.replay_trace`, the `HarnessTrace` carries the
  real session's `session_id`, `model_usage`-derived model, and token
  counts with every sentinel fallback explicitly excluded. Regression test
  pins the `isinstance` gate's `TypeError` for non-`ResultMessage` inputs.

**A3 status for the gate document: CLOSED.** Evidence =
`tests/conformance/test_a3_discharge.py` (both tests, run under
`CCF_REQUIRE_HARNESSES=1`) + example 03's Claude leg, whose replay hook
routes the same real-message path (`legs/deterministic.py::_claude_execution`
→ `drive_leg` seam 4). The hand-built `execution()` in
`test_harness_adapter.py` remains as the per-leg conformance driver; the
discharge supplies the real-session counterpart the advisory demanded.

## Deviations from Plan

**1. [Rule 2 - Missing critical piece] README.md authored in Task 1**
- **Found during:** Task 1
- **Issue:** The plan's `files_modified` lists
  `examples/03-harness-portability/README.md` but neither task's `<files>`
  names it; §9 mandates a README per example.
- **Fix:** README written as part of Task 1 (invariant table, citations,
  run commands, change-first guidance).
- **Files modified:** examples/03-harness-portability/README.md
- **Commit:** 3bcba71

## TDD Gate Compliance

Task 2's RED test **passed on first run** — investigated rather than
skipped past: the adapter's seam-4 mapping already handles a real
SDK-produced message correctly, exactly the "zero adapter change" outcome
the plan anticipated ("the point is evidence, not redesign"). No GREEN
commit exists because there is no implementation delta; the single
`test(...)` commit (1036271) is the discharge evidence itself, with the
regression half guarding the gate.

## Verification

- `make example-03` exit 0 — all three legs executed (`claude-agent-sdk`,
  `google-adk`, `langgraph`), product bytes identical ×3, 7 governed
  fields exactly equal ×3, 3 distinct harness traces
- `--mode live --provider ollama` exits 2 with the 08-11 pointer
- `ls examples/03-harness-portability/artifacts/agents/ | wc -l` → 1
- `CCF_REQUIRE_HARNESSES=1` `pytest tests/conformance -q` → **224 passed**
  (17 passed for a3-discharge + harness-portability alone)
- `make lint` exit 0 (CINV-02 quiet on the example's legitimate harness
  imports per the 08-01 RULE_TREE_SCOPE posture); `make typecheck` clean
  (156 files; examples outside mypy scope by design)

## Known Stubs

`run.py --mode live` exits 2 by design — the live legs and the
`--provider` wiring are plan 08-11's deliverable; the flag surface is
stable now so the Makefile live targets already dispatch correctly.

## Threat Flags

None — T-08-23 held (legs emit only through `capture_effect` →
`Agent.emit_effect`; no leg touches a write surface), T-08-24 discharged
(seam-4 trace from a real SDK message, gate retained), T-08-25 held
(socket guard installed and probe-asserted).

## Self-Check: PASSED
