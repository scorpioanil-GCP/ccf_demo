---
phase: 05-phase-i-2-agent-specialization-framework
plan: 10
subsystem: agents
tags: [gap-closure, lints, controlplane, skilling, gate-package]
requires: ["05-09"]
provides:
  - CINV-01c catches import aliases; factory exemption is an explicit path allowlist (WR-06 closed)
  - AmbiguousPinnedVersionError refusal when one declared semver names two contents; unaudited peek probes (WR-08 closed)
  - SkillCatalog.discover derived from registry state via keys_of_class (IN-03 closed)
  - TaskFactory refuses agent steps resolving to non-AgentDefinition classes (IN-08 closed)
  - PHASE_I2_GATE.md rows 6-7 corrected; gap-closure note + IN-07 advisory; green re-verification sweep (IN-01 closed)
affects: [D-GATE-I.2 gate package, mechanism-of-record integrity, 05-VERIFICATION SC3]
tech-stack:
  added: []
  patterns: [explicit path allowlist over naming convention, unaudited introspection probe vs audited resolution, registry-derived membership]
key-files:
  created: []
  modified:
    - tools/lints/no_hardcoding.py
    - src/ccf/controlplane/registry.py
    - src/ccf/agents/factory.py
    - src/ccf/skills/grants.py
    - src/ccf/skills/catalog.py
    - docs/PHASE_I2_GATE.md
    - tests/lints/test_cinv01c_behavioral.py
    - tests/controlplane/test_registry.py
    - tests/agents/test_factory.py
    - tests/skills/test_catalog.py
key-decisions:
  - "AmbiguousPinnedVersionError lives in ccf.controlplane.registry (the errors' home alongside ControlPlaneMissing) and is raised from both declared-version matching loops"
  - "ControlPlaneRegistry.peek is a deliberately unaudited introspection surface: declared-version probes are not resolutions, so auditing them would record reads that never happened (WR-08 side effect)"
  - "ControlPlaneResolution protocol extended with peek and artifact_class_of; the registry conforms unchanged — no test double exists that needed updating"
  - "keys_of_class returns first-registration order; catalog's _keys index deleted outright rather than demoted to a cache"
  - "Factory allowlist entries are the exact repo-relative path (suffix-anchored at a path-segment boundary) plus the dotted module name — naming a file my_factory_helpers.py earns nothing"
requirements-completed: [AGNT-03]
duration: 22 min
completed: 2026-07-26
---

# Phase 5 Plan 10: Mechanism-of-Record Hardening + Gate Re-alignment Summary

Closed the WR-06/WR-08/IN-01/IN-03/IN-08 review findings: CINV-01c now tracks import
aliases and exempts only an explicit factory-path allowlist; pinned resolution refuses
declared-semver ambiguity with a typed error and audits only what it returns; catalog
discovery is registry-derived; TaskFactory class-checks agent steps; and the gate package
describes the fixed mechanisms with a recorded green sweep.

## Execution

- **Started:** 2026-07-26 (wave 10, parallel worktree)
- **Tasks:** 3/3
- **Files modified:** 10

## Task Commits

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 | Close CINV-01c static holes (WR-06) | b17cde2 |
| 2 | Ambiguity refusal, step class check, registry-derived discovery (WR-08, IN-08, IN-03) | 0a80fe1 |
| 3 | Gate package re-alignment + acceptance sweep (IN-01) | ebd70b9 |

## What Was Done

**Task 1 (WR-06).** `tools/lints/no_hardcoding.py` now walks `ast.Import`/`ast.ImportFrom`
and places any alias of `Agent`/`Task` (`from ccf.agents.agent import Agent as A`) into
`checked_names`; the `"factory" in path` substring exemption is replaced by
`FACTORY_MODULE_ALLOWLIST = {"src/ccf/agents/factory.py", "ccf.agents.factory"}` matched
exactly / suffix-anchored at a path-segment boundary. Behavioral fixtures prove the alias
bypass fires, that `my_factory_helpers.py` and `task_factory.py` are no longer exempt, and
that the real factory (synthetic allowlisted path + the shipped file) remains exempt.

**Task 2 (WR-08, IN-08, IN-03).** `AmbiguousPinnedVersionError` (registry module) is raised
by both declared-semver matching loops — `factory._resolve_pinned` and
`GrantLedger._resolve_policy_regime` — when a second distinct content matches one declared
semver, naming the key, semver, and all matching content hashes. Probing now goes through
the new unaudited `ControlPlaneRegistry.peek`; exactly one audited `resolve` records the
resolution actually returned. `TaskFactory.construct` checks `artifact_class_of` on every
`agent` step's URI-derived key against `AGENT_DEFINITION.class_id`, refusing with
`AgentDefinitionError` naming the step and the actual class. `SkillCatalog.discover`
derives membership from `keys_of_class(SKILL_CATALOG_ENTRY.class_id)`; the volatile
per-instance `_keys` list is deleted — a second catalog over the same registry discovers
identical entries.

**Task 3 (IN-01).** Gate rows 6–7 now describe the required-`grant_set_hash`-argument /
`FalseGrantClaimError` / per-agent-D-07-hash mechanism and the single-shared-`AuditLog`
mechanism. A gap-closure note maps plans 05-08..05-10 to the closed finding ids
(CR-01, WR-01..WR-08, IN-01/02/03/08); the IN-07 test-scoping deviation is recorded as an
advisory carry-forward for §3.1 triage. Re-verification sweep recorded in the doc.

## Verification

- `pytest -q -m "not postgres"` — **577 passed, 2 skipped** (exactly the two declared I.4
  CINV-04 deferral skips), exit 0
- `python -m tools.lints` — exit 0, zero findings
- `mypy --strict src tools` — no issues in 74 source files
- Acceptance greps: `ImportFrom` present in the lint; `'"factory" in'` count 0;
  `AmbiguousPinnedVersionError` at definition + two raise sites; gate doc references
  05-08/05-09/05-10 and CR-01

## Deviations from Plan

**1. [Rule 3 - Blocking] Plan's file/line map for WR-08 was slightly off**
- **Found during:** Task 2
- **Issue:** The plan located `_resolve_pinned` in `registry.py:229-277`; the declared-semver
  loops actually live in `src/ccf/agents/factory.py` (`_resolve_pinned`) and
  `src/ccf/skills/grants.py` (`_resolve_policy_regime`). The registry holds only exact-pin
  `resolve`.
- **Fix:** Applied the ambiguity refusal at both real loop sites; the typed error lives in
  the registry module as the plan directed.
- **Files modified:** src/ccf/agents/factory.py, src/ccf/skills/grants.py
- **Commit:** 0a80fe1

**2. [Rule 2 - Missing critical] Added `peek` and `keys_of_class` introspection to the registry and the factory's `ControlPlaneResolution` protocol**
- **Found during:** Task 2
- **Issue:** Closing the WR-08 audit side effect (probes recorded as resolutions) and IN-03
  (registry-derived discovery) required introspection surfaces the registry did not expose.
- **Fix:** `peek(key, version)` (deliberately unaudited, documented as such) and
  `keys_of_class(class_id)` (introspection-only, like `versions`/`artifact_class_of`);
  protocol extended accordingly. Tests pin the non-auditing property.
- **Files modified:** src/ccf/controlplane/registry.py, src/ccf/agents/factory.py
- **Commit:** 0a80fe1

**Total deviations:** 2 auto-fixed (1 blocking location correction, 1 missing mechanism).
**Impact:** None adverse — both serve the plan's stated must-have truths exactly.

## Self-Check: PASSED

- All 10 modified files exist on disk
- Commits b17cde2, 0a80fe1, ebd70b9 present on `worktree-agent-a5dc858c939f38ebb`
- All task acceptance criteria re-verified green (greps + full sweep above)

## Next

Phase I.2 gap-closure set (05-08..05-10) complete; SC3/AGNT-03 closeable and the
D-GATE-I.2 package is ready to present to Dave per CLAUDE.md §3.1.
