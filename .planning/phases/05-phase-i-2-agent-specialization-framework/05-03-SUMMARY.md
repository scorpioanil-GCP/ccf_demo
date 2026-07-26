---
phase: 05-phase-i-2-agent-specialization-framework
plan: 03
subsystem: agents
tags: [agents, archetypes, composition, d-impl-19, consumption-discipline, tdd]
requires: [05-02]
provides:
  - all six archetype bundles as ArchetypeComponent mechanism (AGNT-01)
  - D-IMPL-19 composition rules as pure functions (dedupe / order-wins / contradiction)
  - factory warning semantics for order-resolved default conflicts
  - consumption-discipline negative test (no path from Agent to L1-L5)
  - deal_monitor_assembler multi-archetype banking fixture
affects: [05-04, 05-05, 05-06, 05-07]
tech-stack:
  added: []
  patterns:
    - canonical_bytes as the D-IMPL-19 identity/contradiction decidability substrate
    - conflicts returned as typed facts from pure composition; warnings.warn only in the factory
    - AST import-allowlist negative testing for boundary invariants
key-files:
  created:
    - src/ccf/agents/composition.py
    - tests/agents/test_composition.py
    - tests/agents/test_consumption_discipline.py
    - tests/fixtures/banking/agents/deal_monitor_assembler.yaml
  modified:
    - src/ccf/agents/archetypes.py
    - src/ccf/agents/factory.py
    - src/ccf/agents/__init__.py
    - tests/agents/test_archetypes.py
    - tests/agents/test_factory.py
decisions:
  - "Contradiction predicate: same ReplayObligation.name contributed with different canonical bytes — an obligation is a replay requirement, and two incompatible requirements under one key cannot both hold; default conflicts (preferences) resolve by declaration order instead"
  - "Bundle id→instance lookup stays in the factory; composition.py takes an ordered sequence of already-resolved ArchetypeComponent bundles, so it stays pure and harness/registry-free"
  - "All five new bundles contribute zero configuration defaults — any calibration the SDK chose would be a D-IMPL-38 silent default; the conflict machinery is exercised via structural test bundles"
metrics:
  duration: ~12 min
  completed: 2026-07-26
  tasks: 3
  tests: 483 passed, 3 skipped
---

# Phase 5 Plan 03: Six Archetypes + D-IMPL-19 Composition Summary

All six archetypes ship as mechanism-only ArchetypeComponent bundles, the D-IMPL-19 ordered-composition rules land as pure canonical-bytes functions wired into the factory with warning semantics, and the AGNT-01 consumption-discipline negative test proves no path from Agent to L1–L5.

## Tasks

| Task | Name | Commits (RED/GREEN) |
| ---- | ---- | ------------------- |
| 1 | The remaining five archetype bundles | 586af5b / 5782154 |
| 2 | D-IMPL-19 composition rules + factory integration | aa33c7b / ba8fbe7 |
| 3 | Consumption-discipline negative test | 865a76b (test-only task) |

## What was built

- **`src/ccf/agents/archetypes.py`** — the five remaining bundles (`workflow_task` [id `workflow`], `document_intelligence`, `monitoring_surveillance`, `content_generation`, `context_assembly`) per DESIGN.md §3.2 contracts: context_assembly declares the emission obligation (`emitted-product-replay-envelope`, plus `policy-before-similarity`); monitoring_surveillance declares `trigger-activation-record` + `freshness-reevaluation`; content_generation declares `passage-anchored-claims` + `prompt-artifact-versions`. Registry now maps exactly `ARCHETYPE_IDS` (6 ids). Zero domain vocabulary, zero numeric literals — asserted by test over serialized bundle content.
- **`src/ccf/agents/composition.py`** — `compose(Sequence[ArchetypeComponent]) -> ComposedArchetype` implementing the three D-IMPL-19 rules: identical obligations dedupe via `canonical_bytes` equality; conflicting defaults resolve first-declared-wins with a typed `DefaultConflict` fact; same obligation name with different canonical bytes raises `CompositionContradiction`. Pure — no I/O, no clock, no warning emission (`grep -c "warnings.warn"` = 0).
- **`src/ccf/agents/factory.py`** — `_compose` keeps the id→bundle lookup (unrealized-bundle typed error) and delegates rules to `composition.compose`; each conflict fact becomes one `warnings.warn` naming the key and both archetypes; contradictions propagate as construction failures.
- **`tests/agents/test_consumption_discipline.py`** — AST import allowlist over `src/ccf/agents/*` (allowed: agents-internal, contracts, canonical, controlplane artifacts/registry, artifacts protocol, replay record, products contract); write-surface attribute denylist over the constructed fixture agent; signature assertion that the only fabric input across Agent methods is `ContextProductContract`. Allowlist verified by temporary mutation (graph-writer import injected → test fails → reverted).
- **`tests/fixtures/banking/agents/deal_monitor_assembler.yaml`** — the CLAUDE.md §6.3 composition example: a wholesale-deal monitoring agent that is also an assembler (`archetypes: [monitoring_surveillance, context_assembly]`), all six axes in YAML; constructs via the factory with `archetype_composition == ("monitoring_surveillance", "context_assembly")`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Stale factory test broken by Task 1**
- **Found during:** Task 2 (verify runs test_factory.py)
- **Issue:** `test_a_declared_archetype_without_a_shipped_bundle_is_refused` used `workflow` as its "declared but unrealized" archetype; Task 1 shipped the workflow bundle, so the premise no longer held and the test would fail.
- **Fix:** the test now narrows the factory's registry view via `monkeypatch.setattr("ccf.agents.factory.ARCHETYPES", ...)`, preserving the invariant (unrealized bundle → typed error, never silent no-op) with all six bundles shipped.
- **Files modified:** tests/agents/test_factory.py
- **Commit:** aa33c7b

**2. [Minor] composition.py docstring reworded**
- The module docstring initially named `warnings.warn` literally, tripping the purity acceptance criterion (`grep -c "warnings.warn" composition.py = 0`); reworded before the GREEN commit so the criterion measures code, not prose.

## Verification

- `.venv/bin/pytest tests/ -q` → 483 passed, 3 skipped
- `.venv/bin/mypy --strict src` → clean (59 files)
- `.venv/bin/python -m tools.lints` → exit 0
- `grep -cin "credit\|covenant\|kyc\|banking" src/ccf/agents/archetypes.py` → 0
- `grep -c "warnings.warn" src/ccf/agents/composition.py` → 0; `src/ccf/agents/factory.py` → 3 (docstrings + one call site)
- Import-allowlist mutation check: injected `from ccf.graph._writer import BaseGraphWriter` into agent.py → test failed; reverted → green
- deal_monitor_assembler constructs; dimension-4 tuple preserves declaration order

## Known Stubs

- Context-assembly emission remains pattern-declared only (obligation values); transports (in-process/MCP/A2A) bind in I.3 per D-08 — deliberate, stated in the bundle docstring.
- Carried from 05-02, unchanged: `bound_skills` always empty, `grant_set_hash` = NO_GRANTS sentinel until 05-05.

## Threat Flags

None — both new surfaces (obligation merge, agent→fabric boundary) were in the plan's threat model (T-05-09..11) and each mitigation is implemented as specified: canonical-bytes decidability + typed contradiction error (T-05-09), conflict facts + factory warning + declaration order in dimension 4 (T-05-10), import allowlist + attr denylist (T-05-11).

## Self-Check: PASSED

All created files exist (composition.py, test_composition.py, test_consumption_discipline.py, deal_monitor_assembler.yaml); commits 586af5b, 5782154, aa33c7b, ba8fbe7, 865a76b present on `phase-i2`.

## TDD Gate Compliance

Tasks 1 and 2 each have a `test(...)` RED commit (verified failing before implementation) followed by a `feat(...)` GREEN commit. Task 3 is a test-only task (negative test) — no feat commit applies. No refactor commits needed.
