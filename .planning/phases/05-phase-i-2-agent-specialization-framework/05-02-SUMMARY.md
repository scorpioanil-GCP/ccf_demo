---
phase: 05-phase-i-2-agent-specialization-framework
plan: 02
subsystem: agents
tags: [agents, archetypes, factory, d-impl-11, d-impl-19, d-impl-28, d-12, replay-dimension-4, tdd]
requires: [05-01]
provides:
  - ArchetypeComponent Protocol + analytics_insights bundle (CCFContract obligations/defaults)
  - concrete final Agent (identity block, three fabric seams, no loop, no token)
  - AgentFactory.construct — the sole Agent construction path via Control Plane resolution
  - D-03 test-double harness in /tests + end-to-end banking slice with D-06 dimension-4 capture
affects: [05-03, 05-04, 05-05, 05-06, 05-07]
tech-stack:
  added: []
  patterns:
    - ControlPlaneProtocol-style runtime_checkable Protocol for the factory's injected resolution surface
    - composition behind a single _compose seam so 05-03 swaps composition.py in without signature change
    - agent_conditioning optional seam on build_replay_record (None keeps I.1 behavior byte for byte)
key-files:
  created:
    - src/ccf/agents/archetypes.py
    - src/ccf/agents/agent.py
    - src/ccf/agents/factory.py
    - tests/agents/test_archetypes.py
    - tests/agents/test_agent.py
    - tests/agents/test_factory.py
    - tests/agents/harness_double.py
    - tests/integration/test_agent_slice.py
  modified:
    - src/ccf/agents/__init__.py
    - src/ccf/agents/errors.py
    - src/ccf/replay/record.py
    - tests/fixtures/banking/agents/covenant_analytics.yaml
decisions:
  - "Factory resolves ccf-artifact:// refs by mapping the naming triple onto Control Plane key {tenant}/{class}/{name} and matching the URI version against each registered version's declared artifact_version/semver (content hashes also accepted as URI versions)"
  - "ConsumptionRefused/SkillNotBound/AgentConstructionError are exceptions, not returned refusals: an out-of-contract product, an unbound capability, or incoherent constructor inputs are broken wiring, not expected artifact outcomes (I.1 refusal-vs-exception line)"
  - "analytics_insights contributes zero configuration defaults — a calibration the SDK chose would be a D-IMPL-38 silent default; the default mechanism exists for the D-IMPL-19 declaration-order rule"
metrics:
  duration: ~10 min
  completed: 2026-07-26
  tasks: 3
  tests: 442 passed, 3 skipped
---

# Phase 5 Plan 02: The D-01 Vertical Slice — Archetype, Agent, Factory, Slice Summary

One YAML banking definition → `AgentFactory.construct` → concrete final `Agent` running its three fabric seams against the real I.1 fabric via the D-03 test double, with replay dimension 4 carrying content hash, versioned-URI annotation, archetype list, and the NO_GRANTS sentinel.

## Tasks

| Task | Name | Commits (RED/GREEN) |
| ---- | ---- | ------------------- |
| 1 | ArchetypeComponent + analytics_insights + concrete Agent | b2d3017 / 80e759e |
| 2 | AgentFactory construction path | ef9ab42 / f0d4e4b |
| 3 | D-03 harness double + end-to-end slice | 809c34a / fffb2a0 |

## What was built

- **`src/ccf/agents/archetypes.py`** — `@runtime_checkable ArchetypeComponent` Protocol (`fabric_interaction_pattern()`, `replay_obligations()`, `configuration_defaults()`); `ReplayObligation`/`ConfigurationDefault` as `CCFContract` values so D-IMPL-19 identity is decidable via canonical bytes; the `analytics_insights` bundle; `ARCHETYPES` registry keyed by definition-artifact identifiers (deliberate subset of `ARCHETYPE_IDS` until 05-03 ships the other five).
- **`src/ccf/agents/agent.py`** — concrete final `Agent` (D-IMPL-11: composition, never subclassing; D-12: no token — constructor validates identity-hash/composition/component coherence and stays a normal public class). Three seams: `consume` (context-contract + tenant + TTL refusal per INV-CH6-05), `invoke_skill` (typed `SkillNotBound` while ungranted), `emit_effect` (returned `EmittedEffect` value — no write handle, single-writer holds). `perspective_conditioning(principal_id)` serializes the D-06 dimension-4 field set from construction-time identity. No run/loop/step/plan surface (asserted by test).
- **`src/ccf/agents/factory.py`** — `AgentFactory` with injected `ControlPlaneResolution` Protocol (registry conforms via isinstance test); pinned-version-only reference resolution; six-axis validation; composition behind the `_compose` seam with `warnings.warn` on default conflicts; D-13 instruction-binding validation; the codebase's single `Agent(...)` call site (CINV-01c green with zero allowlist entries).
- **Slice** — `tests/agents/harness_double.py` (linear script, AST-asserted loop-free, no harness imports) drives the fixture agent, constructed via the factory from `covenant_analytics.yaml`, against the booted I.1 banking fabric; the gated real product is consumed; dimension 4 asserted exactly.

## Deviations from Plan

### Auto-fixed / plan-adjacent changes

**1. [Rule 2 - Missing critical] `build_replay_record` gained an optional `agent_conditioning` parameter (`src/ccf/replay/record.py`, not in the plan's file list)**
- **Found during:** Task 3 (RED failed on the missing seam)
- **Issue:** the fixed 05-01 builder had no path for agent-serialized dimension-4 conditioning; without it the slice could not record agent identity through the construction path (only by hand-assembling records around the builder).
- **Fix:** additive optional parameter recorded verbatim when supplied; `None` preserves I.1 behavior byte for byte. No contract change — `PerspectiveConditioning` untouched.
- **Commit:** fffb2a0

**2. [Rule 3 - Blocking] `src/ccf/agents/errors.py` extended (not in the plan's file list)**
- **Issue:** the new typed failures (`AgentConstructionError`, `SkillNotBound`, `ConsumptionRefused`) belong in the taxonomy module per PATTERNS, which Task 1's file list did not include.
- **Commit:** 80e759e

**3. [Acceptance-criterion divergence] factory contains no `load_artifact`/`safe_load` call**
- The Task 2 criterion `grep -c "safe_load\|load_artifact" factory.py ≥ 1` assumed the factory loads YAML. The factory instead resolves already-registered *typed* artifacts through Control Plane resolution only (DESIGN.md §3.5 "never raw storage") — strictly stronger than the criterion's intent (no raw `yaml.load` re-implementation; zero YAML handling exists in the module). Loading stays with registrars (`load_artifact`/`parse_artifact` in tests and, later, the CLI).

**4. [Fixture adjustment, plan-anticipated] `covenant_analytics.yaml` context contract re-pointed and bumped**
- `context_contract.consumes` now names the real served I.1 product class (`acme-bank.credit-exposure-summary@1.0.0`); `artifact_version` bumped `1.0.0 → 1.2.0` (skipping `1.1.0`, which the hash-verified-bump suite uses for its mutants). Added `referenced_artifacts` and `slice` sections so every registration/drive value lives in YAML, none in test code.

## Verification

- `.venv/bin/pytest tests/ -q` → 442 passed, 3 skipped
- `.venv/bin/mypy --strict src` → clean (58 files)
- `.venv/bin/python -m tools.lints` → exit 0; no new `cinv01c` allowlist entries (allowlist diff clean)
- `grep -rn "Agent(" src/ccf | grep -v factory.py | grep -v "class Agent"` → nothing
- `grep -c runtime_checkable src/ccf/agents/archetypes.py` → 2; no `_GATE_TOKEN`/token mechanism in `agent.py`
- `grep -c "while \|for .* in range" tests/agents/harness_double.py` → 0; no harness imports

## Known Stubs

- `Agent.invoke_skill` returns the bound object without dispatch semantics, and `bound_skills` is always empty (`{}` passed by the factory) — deliberate: grants, governance, and dispatch land in 05-05/05-06 per D-08/D-09; the seam exists now so the adapter surface stays stable.
- `_compose` implements only trivial single-archetype composition plus the default-conflict warning; the full D-IMPL-19 rules swap in via `composition.py` in 05-03 behind the same call.
- `grant_set_hash` is always the `NO_GRANTS_SET_HASH` positive claim until 05-05 computes the D-07 grant-set hash.

## Threat Flags

None — all new surface (untrusted YAML → factory, agent → fabric with no write handle, @latest refusal, /tests-only double) was in the plan's threat model (T-05-05..08) and each mitigation is implemented as specified.

## Self-Check: PASSED

All created files exist; commits b2d3017, 80e759e, ef9ab42, f0d4e4b, 809c34a, fffb2a0 present on `phase-i2`.

## TDD Gate Compliance

Each task has a `test(...)` RED commit (verified failing before implementation) followed by a `feat(...)` GREEN commit. No refactor commits needed.
