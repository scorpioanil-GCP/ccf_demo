---
phase: 08-phase-i-5-examples-suite-full-ci-verification
plan: 01
subsystem: infra
tags: [makefile, ci, lints, cinv-01, cinv-02, examples]
requires: []
provides:
  - "Branch phase-i5 off main"
  - "Repo-root Makefile: help, install, lint, typecheck, test, ci-core, ci, examples, example-00..07, example-03-live-{ollama,anthropic}"
  - "RULE_TREE_SCOPE per-rule lint scoping in tools/lints/__main__.py"
  - "tests/lints/test_examples_scope.py posture suite"
affects: [all later 08-* plans — every plan verifies via make targets]
tech-stack:
  added: []
  patterns:
    - "Per-rule tree scoping as linter config (RULE_TREE_SCOPE), not allowlist or test-only assertion"
    - "Makefile help via ## -annotated targets + grep/awk"
key-files:
  created: [Makefile, tests/lints/test_examples_scope.py]
  modified: [tools/lints/__main__.py, tools/lints/tests/test_runner.py]
decisions:
  - "Lint posture over /examples: CINV-01 (no-hardcoding) covers examples; CINV-02/CINV-03/orchestration-imports scoped to src+runtime — enforced in RULE_TREE_SCOPE config, tested in tests/lints/test_examples_scope.py"
  - "ci-core (lint+typecheck+test) is the mid-phase sweep; ci = ci-core+examples becomes meaningful at 08-12"
metrics:
  duration: "~10 min"
  completed: "2026-07-30"
---

# Phase 08 Plan 01: Wave-0 Scaffold (branch, Makefile, lint posture) Summary

Branch `phase-i5`, D-10 Makefile command surface mirroring ci.yml, and the
lint posture over `/examples` config-enforced via `RULE_TREE_SCOPE` (CINV-01
in, CINV-02 out) with a three-test posture suite.

## What was built

- **Task 1 (204b7ab):** Branch `phase-i5` created off `main`; editable
  install refreshed (`pip install -e ".[dev]"`, Pitfall 7 — `.venv/bin/ccf
  --help` exits 0). Repo-root `Makefile` with `.DEFAULT_GOAL := help`, all
  targets `.PHONY` and `## `-annotated: `install`, `lint`, `typecheck`,
  `test` (with `CCF_REQUIRE_HARNESSES=1`), `ci-core`, `ci` (with the "use
  ci-core until 08-12" comment), `example-00`..`example-07` (final directory
  names; example-03 passes `--mode deterministic`), `examples`,
  `example-03-live-ollama`, `example-03-live-anthropic`. All Python via
  `.venv/bin/python` with `PYTHONPATH=src:runtime`.
- **Task 2 (RED 4af0552, GREEN 4725813):** TDD posture suite
  `tests/lints/test_examples_scope.py` — (1) CINV-01 scope includes
  `examples` and a prompt-shaped literal in a tmp examples tree is rejected;
  (2) harness imports (`langgraph`, `claude_agent_sdk`, `google.adk`) under
  `examples/` produce zero CINV-02 findings; (3) a harness import in a
  synthetic `src/` module still fails (regression guard). GREEN change:
  `RULE_TREE_SCOPE` mapping in `tools/lints/__main__.py` with a module
  comment citing CLAUDE.md §6.4/§7.3 and RESEARCH Open Question 3; `run()`
  skips rules outside their tree scope. Checker behavior over src/runtime is
  unchanged (`harness_imports.py` untouched).

## Deviations from Plan

**1. [Rule 3 - Blocking] Updated `tools/lints/tests/test_runner.py::test_examples_and_runtime_trees_are_linted`**
- **Found during:** Task 2 GREEN
- **Issue:** The pre-existing runner test asserted the superseded posture
  (harness-imports lint firing on an examples-tree file → expected 2
  findings), directly contradicting the plan's ruled posture.
- **Fix:** Assertion updated to 1 finding (runtime still flagged, examples
  exempt) with a docstring citing the plan-08-01 posture.
- **Files modified:** tools/lints/tests/test_runner.py
- **Commit:** 4725813

## Verification

- `git branch --show-current` → `phase-i5`
- `make ci-core` green: lint exit 0, `mypy` clean (155 files), pytest
  1318 passed / 0 failed
- `pytest tests/lints -q` → 41 passed; `pytest tools/lints/tests` → green
  (part of the 90-passed lints run)
- `make help` lists all targets; `grep -c "example-0" Makefile` → 13;
  `CCF_REQUIRE_HARNESSES=1` present; `.venv/bin/ccf --help` exits 0
- Exemption is greppable in linter config: `RULE_TREE_SCOPE` in
  `tools/lints/__main__.py`

## Known Stubs

`example-NN` Makefile targets reference `examples/NN-*/run.py` files that do
not exist yet — expected and stated in the plan; each lands in its own plan
(08-05..08-11), and `examples` is wired into CI only at 08-12.

## TDD Gate Compliance

RED commit 4af0552 (`test(...)`) precedes GREEN commit 4725813 (`feat(...)`).

## Self-Check: PASSED
