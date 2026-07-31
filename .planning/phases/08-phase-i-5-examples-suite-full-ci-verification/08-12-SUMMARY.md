---
phase: 08-phase-i-5-examples-suite-full-ci-verification
plan: 12
subsystem: infra
tags: [ci, github-actions, examples, live-legs, d-10, d-11, exam-09]
requires: [08-05, 08-06, 08-07, 08-08, 08-09, 08-11]
provides:
  - "ci.yml always-on examples job: make examples with CCF_REQUIRE_HARNESSES=1, timeout-minutes 20, never continue-on-error (D-10)"
  - "live-legs.yml: workflow_dispatch examples-live-ollama (installs Ollama, pulls parameterized small model) + secret-gated examples-live-anthropic (D-11)"
  - "make ci finalized as ci-core + examples — the phase gate command, command-identical to the always-on pipeline"
  - "Full local verification sweep green: EXAM-09's CI-equivalence evidence pending push authorization"
affects: [phase-08 gate review, EXAM-09]
tech-stack:
  added: []
  patterns:
    - "CI examples job provisions .venv so the identical Makefile command strings run in Actions and locally (D-10)"
    - "Anthropic live job fails fast with a clear ::error before any setup when the secret is absent"
key-files:
  created: [.github/workflows/live-legs.yml]
  modified: [.github/workflows/ci.yml, Makefile]
decisions:
  - "Ollama live-leg model is a workflow_dispatch input defaulting to qwen3:0.6b (CPU-feasible on ubuntu-latest); local runs remain the primary way to exercise the leg per the CONTEXT discretion note"
  - "make ci semantics finalized: ci = ci-core (lint + typecheck + full test) + examples; live legs deliberately excluded (D-11)"
metrics:
  duration: "~12 min"
  completed: "2026-07-31"
---

# Phase 08 Plan 12: CI wiring + full verification sweep Summary

EXAM-09 closed at the wiring level: the examples suite is an always-on CI job
(`make examples`, never continue-on-error), the two live legs are opt-in
workflow_dispatch jobs per D-11, and the full local sweep is green as the
interim CI evidence — pushing `phase-i5` awaits Dave's authorization.

## What was built

- **Task 1 (f145f1e):** `ci.yml` gained an always-on `examples` job mirroring
  the existing setup block (checkout@v4, setup-python@v5 3.12 + pip cache,
  `pip install -e ".[dev]"`), plus a `.venv` provisioning step so the
  Makefile's `.venv/bin/python` command strings execute identically in CI and
  locally (D-10). Runs `make examples` (00–07 incl. 03's deterministic leg)
  with `CCF_REQUIRE_HARNESSES: "1"` (a skipped harness leg is a failure) and
  `timeout-minutes: 20` (subprocess examples cannot hang the runner). No
  `continue-on-error` anywhere in either workflow (grep confirms: only
  comments stating the prohibition). New `live-legs.yml`, both jobs
  `workflow_dispatch`: `examples-live-ollama` installs Ollama via the official
  script, starts the server with a readiness poll, pulls a parameterized
  small model (input `ollama_model`, default `qwen3:0.6b`), exports
  `CCF_OLLAMA_*`, runs `make example-03-live-ollama` under
  `timeout-minutes: 15`; `examples-live-anthropic` fails fast with a clear
  `::error` when the `ANTHROPIC_API_KEY` secret is absent, otherwise runs
  `make example-03-live-anthropic` (secret reaches only this job, never
  echoed — T-08-28). Makefile `ci` comment finalized: `ci = ci-core +
  examples` is the phase gate command from here on.
- **Task 2 (evidence-only, no code change):** full local verification sweep
  as the CI-equivalence record (RESEARCH A5). No Makefile↔ci.yml command
  drift found (T-08-29).

## Sweep record (make ci, 2026-07-31, exit 0)

| Step | Result |
|------|--------|
| `python -m tools.lints --all` | exit 0 |
| `python -m mypy` | Success: no issues in 156 source files |
| `CCF_REQUIRE_HARNESSES=1 python -m pytest -q` | **1339 passed, 0 failed, 0 skipped** (91s) — ≥ the 1315 baseline |
| `make examples` | all eight exit 0: 00 quickstart, 01 agent-basics, 02 skilling, 03 harness-portability (deterministic: product bytes identical ×3, 7 governed fields equal ×3, 3 distinct traces), 04 cross-process, 05 workflow-hitl, 06 decision-replay (byte-equal reproduction), 07 artifact-store-mcp |

README/artifacts contract check (D-09): all 8 `examples/NN-*/` PASS —
non-empty `artifacts/`, README with `make example-` command, whitepaper
citation, CLAUDE.md citation, and domain-rationale line.

`timeout-minutes` present on the CI examples job (20) and both live-legs
jobs (15 each).

## FLAG FOR DAVE — push authorization

`phase-i5` (and `main`) are ahead of origin; pushing is not authorized
(RESEARCH Open Question 1). The Actions runs for the new `examples` job and
`live-legs.yml` cannot be observed until a push happens. The local sweep
above is command-identical to the always-on pipeline and stands in as
EXAM-09 evidence until then.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None new — T-08-28 held (secret confined to the gated job, deterministic
pipeline keyless), T-08-29 held (identical command strings verified in the
sweep).

## Self-Check: PASSED
