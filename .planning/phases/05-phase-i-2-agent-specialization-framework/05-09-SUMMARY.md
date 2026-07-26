---
phase: 05-phase-i-2-agent-specialization-framework
plan: 09
subsystem: agents
tags: [audit-by-construction, replay, skilling, gap-closure]
requires: ["05-08"]
provides:
  - required grant_set_hash with FalseGrantClaimError refusal on false zero-grants claims (WR-01 closed)
  - typed BoundSkillView bound_skills seam, sole producer GrantLedger.bound_view (WR-03 closed)
  - single shared AuditLog spanning registry and grant ledger (WR-07 closed)
  - stale harness-double pragma cleared with granted-path coverage (IN-02 closed)
affects: [replay dimension 4, skilling governance, 05-VERIFICATION SC3]
tech-stack:
  added: []
  patterns: [typed seam with module-private producer discipline, injected shared audit log at composition time]
key-files:
  created: []
  modified:
    - src/ccf/agents/agent.py
    - src/ccf/agents/factory.py
    - src/ccf/agents/errors.py
    - src/ccf/skills/grants.py
    - src/ccf/skills/__init__.py
    - src/ccf/controlplane/registry.py
    - tests/agents/test_agent.py
    - tests/agents/test_factory.py
    - tests/agents/test_consumption_discipline.py
    - tests/agents/harness_double.py
    - tests/integration/test_agent_slice.py
    - tests/skills/test_grants.py
key-decisions:
  - "FalseGrantClaimError is a raised exception, not a returned refusal — a false replay claim is broken wiring in the caller, not a governance outcome to inspect"
  - "BoundSkillView producer discipline is docstring-declared module-private plus a runtime isinstance refusal in Agent construction (AgentConstructionError), holding the line against dynamically-injected mappings that mypy alone cannot catch"
  - "grants.py's AgentDefinition import moved to TYPE_CHECKING to break the runtime cycle created by agent.py importing BoundSkillView"
  - "ControlPlaneRegistry keeps a fresh-log default so non-injecting callers are behavior-preserved; sharing is a composition-time statement"
requirements-completed: [AGNT-03]
duration: 25 min
completed: 2026-07-26
---

# Phase 05 Plan 09: Audit-by-Construction Seams (WR-01, WR-03, WR-07, IN-02) Summary

Converted three "audit by well-behaved caller" seams into audit by construction:
required-and-refused grant-set claims on dimension 4, a ledger-only typed
bound_skills seam, and one unified audit log across registry and grant ledger.

- **Duration:** ~25 min (2026-07-26)
- **Tasks:** 2/2 complete
- **Files changed:** 13

## What Was Done

### Task 1 — False-claim default removed, bound_skills seam typed (WR-01, WR-03, IN-02) — commit `3aede1e`
- `Agent.perspective_conditioning(grant_set_hash: str)` is now a required
  keyword argument (no `NO_GRANTS_SET_HASH` default), and passing the
  zero-grants claim while `bound_skills` is non-empty raises the new typed
  `FalseGrantClaimError` (src/ccf/agents/errors.py).
- `BoundSkillView` (renamed from module-private `_BoundSkills` in
  src/ccf/skills/grants.py, exported from `ccf.skills`) is the typed seam:
  `GrantLedger.bound_view` returns it, `AgentFactory.construct` accepts
  `BoundSkillView | None`, and `Agent` refuses anything else at construction
  via `_validated_bound_skills` (runtime `isinstance`, `object`-typed helper
  to satisfy `warn_unreachable`). `invoke_skill` return typing tightened to
  `SkillCatalogEntry | SkillInvocation | ToolInvocation`; the dead
  not-a-catalog-entry `TypeError` branch removed.
- `grants.py` now imports `AgentDefinition` under `TYPE_CHECKING` only,
  breaking the runtime cycle introduced by `agent.py`/`factory.py` importing
  `BoundSkillView`.
- IN-02: the `# pragma: no cover - unreachable until grants land` at
  tests/agents/harness_double.py cleared; a granted-path drive test
  (`test_the_double_drives_a_granted_skill_without_the_typed_error`) covers
  the `unbound is None` branch live.
- New tests: required-argument `TypeError`; `FalseGrantClaimError` on a
  skilled agent (slice); raw-dict refusal at both the `Agent` constructor
  and the factory front door.

### Task 2 — Unified audit plane (WR-07) — commit `2bb5f4c`
- `ControlPlaneRegistry.__init__` accepts `audit_log: AuditLog | None = None`
  (fresh-log default preserves existing behavior) and exposes a read-only
  `audit_log` property.
- Both grant-ledger composition sites (tests/skills/test_grants.py `_World`,
  tests/integration/test_agent_slice.py `_granted_agent`) now share one
  `AuditLog` between registry and ledger.
- Regression test `test_registry_and_grant_lifecycle_share_one_audit_sequence`:
  after one `request(...)`, the grant's `register_versioned` registration
  event and the `grant_requested`/`grant_effective` lifecycle events land in
  the SAME log with `sequence == range(len(events))` — one log, one
  sequence, one clock. `AuditLog` itself unchanged.

## Verification Results

- `pytest -q -m "not postgres"` — 566 passed, 2 skipped (baseline 560 + new tests)
- `python -m tools.lints` — exit 0
- `mypy --strict src tools` — no issues in 74 source files
- Acceptance greps: no `grant_set_hash: str = NO_GRANTS_SET_HASH` in agent.py;
  exactly one `class BoundSkillView` in grants.py; no
  `bound_skills: Mapping[str, object]` in factory.py; no
  "unreachable until grants land" in harness_double.py;
  `audit_log: AuditLog | None` present in registry.py

## Deviations from Plan

**1. [Rule 3 - Blocking] Agents consumption-discipline allowlist extended**
- **Found during:** Task 1
- **Issue:** tests/agents/test_consumption_discipline.py's import allowlist
  predates the WR-03 seam and rejected `ccf.skills.grants` from agent/factory
- **Fix:** added `ccf.skills.grants` to `ALLOWED_CCF_PREFIXES` with rationale —
  grants are Control Plane skilling mechanism above L6 (same class as
  catalog/dispatch); no path from Agent to L1–L5 is opened
- **Files modified:** tests/agents/test_consumption_discipline.py
- **Commit:** 3aede1e

**2. [Rule 3 - Blocking] Grant-only audit assertions filtered for the shared log**
- **Found during:** Task 2
- **Issue:** two TestAudit tests asserted exact whole-log event lists, which
  the unified log (now carrying registry events) breaks
- **Fix:** assertions filter to `grant_*` actions and check monotonic (not
  dense) sequences; the new WR-07 regression test owns the whole-log claim
- **Files modified:** tests/skills/test_grants.py
- **Commit:** 2bb5f4c

**Total deviations:** 2 auto-fixed (Rule 3). **Impact:** test-side only; both are direct consequences of the plan's intended seam changes.

## Known Stubs

None.

## Threat Flags

None — changes tighten existing trust boundaries (false-claim refusal,
governed-only capability injection, unified audit sequence); no new surface.

## Next Phase Readiness

WR-01/WR-03/WR-07/IN-02 closed; SC3's "by construction" claim is now
mechanically true. Remaining gap-closure: sibling plan 05-10, then phase
re-verification.

## Self-Check: PASSED

- Modified files exist on disk: verified
- Commits `3aede1e`, `2bb5f4c` present on branch: verified
- All task acceptance-criteria greps re-run: PASS
- Plan-level verification (pytest, tools.lints, mypy --strict): PASS
