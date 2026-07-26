---
phase: 05-phase-i-2-agent-specialization-framework
plan: 08
subsystem: skills
tags: [grants, replay, tenant-isolation, gap-closure]
requires: ["05-07"]
provides:
  - per-agent GrantLedger.effective_hashes/grant_set_hash (CR-01 closed)
  - TenantMismatch tier-1 refusal on cross-tenant grants (WR-02 closed)
  - resolve-before-mutate GrantLedger.request, audited missing-entry failure (WR-04 closed)
  - GrantCollisionError on same-skill_name double-effective state (WR-05 closed)
affects: [replay dimension 4, skilling governance, 05-VERIFICATION SC3]
tech-stack:
  added: []
  patterns: [typed governance refusals as returned values, resolve-before-mutate state machine]
key-files:
  created: []
  modified:
    - src/ccf/skills/grants.py
    - src/ccf/skills/__init__.py
    - tests/skills/test_grants.py
    - tests/integration/test_agent_slice.py
    - tests/fixtures/banking/skills/grants.yaml
key-decisions:
  - "Tenant mismatch is a returned TenantMismatch tier-1 refusal (audited, resolved=False), not a GrantTransitionError — the artifact is well-formed; crossing a tenant boundary is a governance outcome the caller inspects"
  - "Missing-catalog-entry failure is audited (grant_refused, resolved=False) before SkillNotInCatalog propagates, with zero ledger mutation — the grant content hash stays re-requestable"
  - "Same-name double-effective grants raise GrantCollisionError (governance-state defect) rather than last-granted-wins shadowing"
requirements-completed: [AGNT-03]
duration: 18 min
completed: 2026-07-26
---

# Phase 05 Plan 08: Grants Correctness Cluster (CR-01, WR-02, WR-04, WR-05) Summary

Per-agent D-07 grant-set identity plus tenant-coherence, resolve-before-mutate, and
same-name-collision enforcement in `GrantLedger` — replay dimension 4 now records the
skills the agent actually had, per CLAUDE.md §6.2.

- **Duration:** ~18 min (2026-07-26)
- **Tasks:** 2/2 complete
- **Files changed:** 5

## What Was Done

### Task 1 — Per-agent grant-set identity (CR-01) — commit `1c264a5`
- `GrantLedger.effective_hashes(agent_definition_hash: str | None = None)` filters
  effective grants by agent; `None` keeps the ledger-wide operator-inspection view,
  documented as never a replay identity input.
- `GrantLedger.grant_set_hash(agent_definition_hash: str)` — required argument, no
  default — hashes the per-agent set via the module-level D-07 helper; returns
  `NO_GRANTS_SET_HASH` when the per-agent set is empty.
- Slice test (`tests/integration/test_agent_slice.py`) passes
  `content_hash(definition)` at both dimension-4 call sites; no argument-less
  `ledger.grant_set_hash()` call remains anywhere.
- Two-agent regression `test_grant_set_hash_is_per_agent_across_two_agents`: two
  definitions against one ledger; a grant to B leaves A at `NO_GRANTS_SET_HASH`, and a
  grant to A leaves B's hash unmoved.

### Task 2 — Grant-path governance seams (WR-02/04/05) — commit `a76df23`
- **WR-04:** `request` resolves the catalog entry before registering the artifact or
  mutating `_states`/`_grants`. A `SkillNotInCatalog` failure is audited
  (`grant_refused`, `resolved=False`) and raised with the ledger untouched; the same
  grant content hash succeeds once the entry exists (regression test proves the round
  trip). The already-seen `GrantTransitionError` message now distinguishes
  "already seen (state ...)" from "already decided".
- **WR-02:** after catalog resolution and registration, `request` refuses with a typed
  `TenantMismatch` (tier-1 refusal shape, audited `resolved=False`) when
  `grant.tenant != definition.tenant` or `entry.tenant != definition.tenant`.
  Exported from `ccf.skills`.
- **WR-05:** `_effective_entries` raises `GrantCollisionError` (naming the skill and
  both grant hashes) when two effective grants bind one `skill_name` for one agent;
  revoking one grant restores the bound view. Exported from `ccf.skills`.
- Fixture material (`grants.yaml`): `other-bank` cross-tenant entry+grant, a
  `covenant-metrics@1.1.0` upgrade entry+grant, and a `late_skills` latecomer
  entry+grant registered mid-test.

## Verification Results

- `pytest -q -m "not postgres"` — 560 passed, 2 skipped (baseline 556 + new tests)
- `pytest -q tests/skills/ tests/integration/test_agent_slice.py tests/conformance/test_approval_sink.py tests/invariants/test_replay_by_construction.py` — 68 passed
- `python -m tools.lints` — exit 0
- `mypy --strict src tools` — no issues in 74 source files
- All plan acceptance-criteria greps pass (single-line `grant_set_hash`/
  `effective_hashes` signatures; `catalog.resolve` at line 560 precedes first
  `self._states[` assignment at line 572; exactly one `class GrantCollisionError`)

## Deviations from Plan

**1. [Rule 2 - Missing critical] Missing-entry failure audited before raise**
- **Found during:** Task 2 (WR-04)
- **Issue:** Pure resolve-before-mutate would leave the failure unauditable, violating the must_have "the failure is auditable"
- **Fix:** `request` appends a `grant_refused` (`resolved=False`) audit event before re-raising `SkillNotInCatalog`
- **Files modified:** src/ccf/skills/grants.py
- **Commit:** a76df23

**Total deviations:** 1 auto-fixed (Rule 2). **Impact:** none beyond closing the audit gap the plan's truths required.

## Known Stubs

None.

## Threat Flags

None — changes tighten existing trust boundaries (tenant isolation on the skilling channel); no new surface introduced.

## Next Phase Readiness

CR-01/WR-02/WR-04/WR-05 closed; SC3/AGNT-03 unblocked pending 05-09/05-10 sibling gap-closure plans and re-verification.

## Self-Check: PASSED

- Modified files exist on disk: verified
- Commits `1c264a5`, `a76df23` present on branch: verified
- All task acceptance criteria re-run: PASS
- Plan-level verification (pytest, lints, mypy): PASS
