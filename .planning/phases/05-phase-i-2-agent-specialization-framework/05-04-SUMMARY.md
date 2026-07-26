---
phase: 05-phase-i-2-agent-specialization-framework
plan: 04
subsystem: agents
tags: [agents, task-factory, cinv01c, json-schema, d-05, d-11, d-12, tdd]
requires: [05-03]
provides:
  - TaskDefinition schema + TASK_DEFINITION artifact class (D-11, construction only)
  - Task + TaskFactory mirroring the AgentFactory flow, no execution surface
  - behavioral proof the CINV-01c factory-bypass lint fires (D-12, no longer vacuous)
  - cinv01c module-level alias detection (A = Agent; A(...) is caught)
  - JSON Schema export assertions for every I.2 artifact contract (D-IMPL-28)
  - six-axis axis-change => new-version matrix (success criterion 4)
affects: [05-05, 05-06, 05-07]
tech-stack:
  added: []
  patterns:
    - shared _resolve_pinned/_validated_instruction_artifacts helpers between both factories
    - ARTIFACT_CONTRACTS module-level registry so 05-05 extends the tuple, not the tests
    - synthetic-module-on-disk lint testing via check() + the shipped runner over the real tree
key-files:
  created:
    - tests/fixtures/banking/tasks/covenant_review_task.yaml
    - tests/lints/test_cinv01c_behavioral.py
    - tests/lints/conftest.py
    - tests/agents/test_schema_export.py
  modified:
    - src/ccf/agents/definitions.py
    - src/ccf/agents/factory.py
    - src/ccf/agents/__init__.py
    - tools/lints/no_hardcoding.py
    - tests/agents/test_factory.py
decisions:
  - "Task and TaskIdentity live in factory.py itself so the single Task(...) call site sits under the lint's factory path marker with zero structural exceptions"
  - "hitl-gate steps must carry NO ref in I.2 — binding an approval policy before anything can execute would be a claim the artifact cannot honor; gate semantics are I.4 (D-11)"
  - "cinv01c alias extension is minimal by design: module-level Name = Agent|Task assignments only; the accepted D-12 residual stays exactly dynamic construction, no wider and no narrower"
  - "Six-axis mutants are structural transformations of fixture-loaded data (ref-version bumps, tuple reorder/extension, fixture-value reuse) — never new prompt or domain content"
metrics:
  duration: ~8 min
  completed: 2026-07-26
  tasks: 3
  tests: 512 passed, 3 skipped
---

# Phase 5 Plan 04: Factory Hardening Summary

TaskDefinition + TaskFactory ship as schema and construction/validation only (no execution engine, D-11), the CINV-01c no-bypass lint is behaviorally proven firing on synthetic Agent/Task bypasses including module-level aliases (D-12), JSON Schemas export closed-world for every I.2 artifact contract, and all six specialization axes are proven to produce distinct content hashes with unbumped changes refused (D-05) — completing AGNT-02.

## Tasks

| Task | Name | Commits (RED/GREEN) |
| ---- | ---- | ------------------- |
| 1 | TaskDefinition schema + TaskFactory (construction only, D-11) | 49c4a59 / 8ff131c |
| 2 | CINV-01c behavioral lint fixture + alias extension | 79af0c3 / bfef36a |
| 3 | JSON Schema export + axis-change versioning tests | fbc62ab (test-only task) |

## What was built

- **`src/ccf/agents/definitions.py`** — `TaskStep` (kinds `{skill, agent, hitl-gate}` per CLAUDE.md §8.1; skill/agent steps require a pinned `ccf-artifact://` ref, hitl-gate steps refuse one — structural validation only in I.2), `TaskDefinition(_TwoLaneVersioned)` with ordered nonempty steps and optional instruction bindings, and `TASK_DEFINITION = ArtifactClass("ccf.task-definition", ...)`.
- **`src/ccf/agents/factory.py`** — reference resolution and D-13 instruction-binding validation extracted into shared module-level helpers (`_resolve_pinned`, `_validated_instruction_artifacts`) used by both factories; `TaskIdentity` (content hash + versioned URI), concrete data-holding `Task` (no `execute`/`run`/`step`/`loop`/`plan`, asserted by absence tests; no replay capture — nothing executes, nothing records), and `TaskFactory.construct` mirroring resolve→validate→instantiate minus archetype composition. The single `Task(...)` call site is factory.py.
- **`tools/lints/no_hardcoding.py`** — cinv01c now tracks module-level `Name = Agent|Task` aliases and checks calls through them, reporting the canonical name; the D-12 accepted residual (dynamic construction) is documented in the rule docstring.
- **`tests/lints/test_cinv01c_behavioral.py`** — synthetic bypassing modules written to real tmp files: `Agent(...)`/`Task(...)` outside factory paths fire `RULE_FACTORY_BYPASS` (positive assertions on rule id and message), in-factory construction and unrelated aliases do not, aliased bypass fires, and the real tree is *observed* (via the shipped runner) at zero cinv01c findings.
- **`tests/agents/test_schema_export.py`** — `model_json_schema()` asserted for `AgentDefinition`, `TaskDefinition`, `PromptArtifact` via the extensible `ARTIFACT_CONTRACTS` tuple: closed-world at root and every `$defs` object level, all six axes present and required on AgentDefinition, pydantic pinned at 2.13.4 with an explicit-reason skip guard (Pitfall 7).
- **`tests/agents/test_factory.py`** — the six-axis matrix: one structural mutant per axis, each producing a distinct content hash, each refused as `RefuseUnbumpedChange` under the unchanged `artifact_version` (registry left untouched), and a bumped axis-6 variant registering, constructing through the factory, and landing its new `agent_definition_hash` in dimension 4.
- **`tests/fixtures/banking/tasks/covenant_review_task.yaml`** — covenant-review task: a skill step, an agent step referencing covenant_analytics, a hitl-gate step; all values in YAML (No-Hardcoding §6.4).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `tools` package not importable from `tests/`**
- **Found during:** Task 2 (RED collection failed with ModuleNotFoundError)
- **Issue:** `tools` is a repo-local package, not an installed distribution like `ccf`; `tests/lints/` could not import the lint under test (existing lint tests live under `tools/lints/tests/` where the package root resolves for free).
- **Fix:** `tests/lints/conftest.py` inserts the repo root into `sys.path`, scoped to that directory.
- **Files modified:** tests/lints/conftest.py (created)
- **Commit:** 79af0c3

## Verification

- `.venv/bin/pytest tests/ -q` → 512 passed, 3 skipped
- `.venv/bin/pytest tools/lints/tests -q` → all pass with the alias extension
- `.venv/bin/mypy --strict src` → clean (59 files)
- `.venv/bin/python -m tools.lints` → exit 0 against the real tree
- `grep -rn "Task(" src/ccf | grep -v factory.py | grep -v "class Task"` → empty
- `git diff tools/lints/allowlist.yaml` → empty (zero new allowlist entries)
- Six-axis matrix: all axes distinct hashes, all refused unbumped, bumped variant visible in dimension 4

## Known Stubs

- Carried from 05-02/05-03, unchanged: `bound_skills` empty and `grant_set_hash` = NO_GRANTS sentinel until 05-05; context-assembly emission pattern-declared only until I.3.
- Task execution semantics deliberately absent (D-11) — the I.4 Workflow primitive consumes the now-stable Task artifact format; documented in every relevant docstring, not a gap.

## Threat Flags

None — all three new surfaces were in the plan's threat model and mitigated as specified: CINV-01c behavioral fixture + alias extension (T-05-12, residual = dynamic construction per Dave's D-12 ruling), Task has no execute surface asserted by absence (T-05-13), six-axis D-05 refusal matrix (T-05-14).

## Self-Check: PASSED

All created files exist (covenant_review_task.yaml, test_cinv01c_behavioral.py, conftest.py, test_schema_export.py); commits 49c4a59, 8ff131c, 79af0c3, bfef36a, fbc62ab present on `phase-i2`.

## TDD Gate Compliance

Tasks 1 and 2 each have a `test(...)` RED commit (verified failing before implementation) followed by a `feat(...)` GREEN commit. Task 3 is a test-only task proving already-shipped mechanism (schema export from 05-01 contracts, D-05 refusals from the 05-01 registry) — no feat commit applies. No refactor commits needed.
