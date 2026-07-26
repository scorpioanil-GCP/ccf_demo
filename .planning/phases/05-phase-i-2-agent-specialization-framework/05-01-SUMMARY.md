---
phase: 05-phase-i-2-agent-specialization-framework
plan: 01
subsystem: agents
tags: [agents, d-impl-28, jinja2, control-plane, replay, tdd]
requires: []
provides:
  - AgentDefinition + PromptArtifact six-axis schemas (D-IMPL-28)
  - Jinja2 parse-only prompt validation (D-13)
  - register_versioned D-05 hash-verified bump with typed refusals
  - Complete D-06 dimension-4 replay extension with sentinels
affects: [05-02, 05-03, 05-04, 05-05, 05-06]
tech-stack:
  added: [jinja2==3.1.6]
  patterns:
    - ArtifactClass + load_artifact reuse for agent artifacts
    - GateRefusal-style returned refusal values for registration
    - positive-claim sentinel constants (NO_GRANTS_SET_HASH, NO_AGENT_DEFINITION)
key-files:
  created:
    - src/ccf/agents/__init__.py
    - src/ccf/agents/definitions.py
    - src/ccf/agents/prompts.py
    - src/ccf/agents/errors.py
    - tests/agents/test_definitions.py
    - tests/agents/test_prompts.py
    - tests/controlplane/test_hash_verified_bump.py
    - tests/fixtures/banking/agents/covenant_analytics.yaml
    - tests/fixtures/banking/prompts/covenant_summary.yaml
  modified:
    - pyproject.toml
    - src/ccf/controlplane/registry.py
    - src/ccf/controlplane/artifacts.py
    - src/ccf/controlplane/audit.py
    - src/ccf/replay/record.py
    - tests/replay/test_serve_writes_replay.py
    - tests/integration/test_proto_quickstart.py
decisions:
  - "D-05 content comparison uses a version-normalized fingerprint (artifact_version blanked before hashing) so a bump alone never reads as a content change; the stored registry version remains the full content hash"
  - "delegation_chain field default is the single-element NO_AGENT_DEFINITION chain; build_replay_record passes the single-element originating-principal chain (I.2 shape per RESEARCH Open Question 3 — RESOLVED)"
  - "validate_semver factored out of controlplane/artifacts.py as a public function rather than importing the private regex (PATTERNS no-second-copy rule)"
metrics:
  duration: ~35 min
  completed: 2026-07-26
  tasks: 3
  tests: 411 passed, 3 skipped
---

# Phase 5 Plan 01: Foundations — Schemas, Prompt Validation, Bump Check, Dimension 4 Summary

Six-axis D-IMPL-28 agent/prompt artifact schemas with Jinja2 parse-only validation (D-13), the D-05 hash-verified version bump in the Control Plane, and the complete D-06 dimension-4 replay extension done in one contract change.

## Tasks

| Task | Name | Commits (RED/GREEN) |
| ---- | ---- | ------------------- |
| 1 | Branch, jinja2 pin, six-axis schemas | 3e0bdfa / e5c45e3 |
| 2 | Jinja2 parse-only prompt validation (D-13) | 69d7805 / 32ca3bb |
| 3 | D-05 hash-verified bump + D-06 dimension-4 extension | d65a75b / c626030 |

## What was built

- **`src/ccf/agents/definitions.py`** — `AgentDefinition` (two-field versioning, all six required axes: archetypes, context_contract, perspective, policy_regime, halflife_debt_profile, instruction_bindings) and `PromptArtifact`; sub-axis structures are all `CCFContract` subclasses; `AGENT_DEFINITION`/`PROMPT_ARTIFACT` `ArtifactClass` constants; refs validated through `parse_artifact_uri` so `@latest` is refused at schema level; unknown archetypes refused against the six shipped identifiers.
- **`src/ccf/agents/prompts.py`** — `validate_prompt_artifact` (exact-match rule both directions, `Environment().parse` + `find_undeclared_variables`, syntax errors chained) and `validate_instruction_binding`. No `.render(` anywhere in `/src`.
- **`src/ccf/controlplane/registry.py`** — `register_versioned` implementing the D-05 four-outcome table with `RefuseUnbumpedChange`/`RefuseEmptyBump` returned as CCFContract values; all outcomes audited (refusals `resolved=False`); `register_typed` byte-compatible.
- **`src/ccf/replay/record.py`** — `PerspectiveConditioning` extended once with `agent_definition_hash`, `agent_definition_uri`, `archetype_composition`, `grant_set_hash`, never-empty `delegation_chain`; sentinels `NO_GRANTS_SET_HASH="no-grants"`, `NO_AGENT_DEFINITION="no-agent"`.
- **Fixtures** — banking agent definition (analytics_insights, D-02 slice agent) and covenant-summary prompt; all axis values and template text in YAML, none in code.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] D-05 content identity normalizes artifact_version**
- **Found during:** Task 3 (empty-bump test failed)
- **Issue:** `content_hash(artifact)` includes `artifact_version`, so a bump alone always read as a content change and `RefuseEmptyBump` could never fire.
- **Fix:** the bump check compares a fingerprint computed with `artifact_version` blanked; the registry version remains the full content hash.
- **Commit:** c626030

**2. [Rule 2 - Missing critical] `src/ccf/controlplane/audit.py` extended**
- **Issue:** `AuditAction` Literal lacked a value for the new registration path; auditing refusals under `register_typed` would misattribute the action.
- **Fix:** added `"register_versioned"` to the Literal. File was not in the plan's `files_modified` list.
- **Commit:** c626030

**3. [Rule 3 - Blocking] `src/ccf/controlplane/artifacts.py` touched**
- **Issue:** plan/PATTERNS required reusing the semver validation without duplicating the regex; the regex was module-private.
- **Fix:** factored public `validate_semver`; `_VersionedArtifact` now delegates to it.
- **Commit:** e5c45e3

**4. [Minor sequencing] Prompt fixture created in Task 1**
- The `covenant_summary.yaml` fixture (listed under Task 2) was created in Task 1's RED commit because the `PromptArtifact` schema test loads it.

## Verification

- `git branch --show-current` → `phase-i2`
- `pytest tests/ -q` → 411 passed, 3 skipped
- `mypy --strict src` → clean (55 files)
- `python -m tools.lints` → exit 0
- `grep -rn "\.render(" src/ccf/agents/` → no matches
- `grep -c "jinja2==3.1.6" pyproject.toml` → 1; venv asserts jinja2 3.1.6 / pydantic 2.13.4

## Known Stubs

None. Sentinel defaults (`NO_GRANTS_SET_HASH`, `NO_AGENT_DEFINITION`) are deliberate positive-claim values per D-06/D-07, replaced by real values in plans 05-02 (agent identity) and 05-05 (skilling), with no further contract change.

## Threat Flags

None — all new surface (artifact registration, YAML loading, Jinja2 templates) was in the plan's threat model; T-05-03 (SSTI) remains accepted for I.2 (parse-only, no render surface exists).

## Self-Check: PASSED

All created files exist; all six task commits present on `phase-i2`.

## TDD Gate Compliance

Each task has a `test(...)` RED commit (verified failing before implementation) followed by a `feat(...)` GREEN commit. No refactor commits needed.
