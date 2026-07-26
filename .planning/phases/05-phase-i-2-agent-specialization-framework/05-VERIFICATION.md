---
phase: 05-phase-i-2-agent-specialization-framework
verified: 2026-07-26T18:00:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 3/4
  gaps_closed:
    - "SC3: Skill catalog registration/discovery/grant/revoke with per-agent, by-construction replay capture of the skill-set in force (CR-01 + WR-01..WR-08 + IN-01/02/03/08 closed by plans 05-08..05-10)"
  gaps_remaining: []
  regressions: []
human_verification: []
---

# Phase 5: Phase I.2 — Agent Specialization Framework Verification Report

**Phase Goal:** Agents are declared, versioned Control Plane artifacts produced exclusively by the Agent & Task Factory from the six shipped archetypes, specialized through the two governed channels
**Verified:** 2026-07-26T18:00:00Z
**Status:** passed
**Re-verification:** Yes — after gap-closure plans 05-08, 05-09, 05-10

## Goal Achievement

### Observable Truths (ROADMAP Phase 5 Success Criteria)

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Unified Agent base + six archetypes in `/src`, no agent instances/prompts/domain values in library code; composition per D-IMPL-11/19 | ✓ VERIFIED | Regression check: all six archetype IDs (`workflow_task`, `document_intelligence`, `analytics_insights`, `monitoring_surveillance`, `content_generation`, `context_assembly`) confirmed in `src/ccf/agents/archetypes.py`; composition module intact; No-Hardcoding lint suite exit 0 |
| 2 | Agent & Task Factory constructs only from definition artifacts (D-IMPL-28); no supported bypass path; lint rejects bypass and prompt literals | ✓ VERIFIED | Sole `Agent(...)` call site confirmed at `src/ccf/agents/factory.py:304`; WR-06 closed — CINV-01c now tracks `ast.Import`/`ast.ImportFrom` aliases (`no_hardcoding.py:394`) and the `"factory"` substring exemption is gone (grep count 0), replaced by exact `FACTORY_MODULE_ALLOWLIST` (`no_hardcoding.py:90`); alias-bypass behavioral fixtures present in `tests/lints/test_cinv01c_behavioral.py:92-108`; WR-03 side door closed (see SC3) |
| 3 | Skill catalog registration/discovery/grant/revoke; tier-1 refusal; every grant/revocation and the skill-set in force land in replay | ✓ VERIFIED | **Previously FAILED — now closed, verified directly in code.** CR-01: `GrantLedger.grant_set_hash(agent_definition_hash: str)` is a required per-agent argument (`grants.py:715`), `effective_hashes` filters by agent (`grants.py:694-711`); two-agent regression `test_grant_set_hash_is_per_agent_across_two_agents` (`tests/skills/test_grants.py:477`) passes; slice test passes `content_hash(definition)` at both dimension-4 call sites (`test_agent_slice.py:370,375`). WR-01: `perspective_conditioning(*, principal_id, grant_set_hash)` has no default and raises `FalseGrantClaimError` on a zero-grants claim with non-empty bound skills (`agent.py:317-341`). WR-03: `bound_skills: BoundSkillView | None` (`factory.py:244`), `BoundSkillView` produced only by `GrantLedger.bound_view` (`grants.py:752`). WR-02: `TenantMismatch` tier-1 refusal (`grants.py:261`). WR-04/WR-05: resolve-before-mutate request + `GrantCollisionError` (`grants.py:124`); targeted tests (tenant/collision/wedged/missing) pass. WR-07: `ControlPlaneRegistry(audit_log: AuditLog | None)` injection (`registry.py:216`) with shared-log regression `test_registry_and_grant_lifecycle_share_one_audit_sequence` (`tests/skills/test_grants.py:385`) passing. IN-03: `SkillCatalog.discover` derives from `keys_of_class` (`catalog.py:266`), volatile `_keys` index gone. WR-08: `AmbiguousPinnedVersionError` (`registry.py:125`) raised at both declared-semver loops (`factory.py:147`, `grants.py:456`) |
| 4 | All six specialization axes expressible in the definition artifact and versioned; axis change ⇒ new agent version visible in replay | ✓ VERIFIED | Regression check: all six axes present on `AgentDefinition` (`definitions.py:212-217`); WR-08 ambiguity refusal removes the pinned-resolution caveat; version-matrix and hash-verified-bump tests in the passing suite; IN-08 closed — TaskFactory class-checks agent-step refs via `artifact_class_of` against `AGENT_DEFINITION.class_id` (`factory.py:457-465`) |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `src/ccf/agents/definitions.py` | Six-axis AgentDefinition + Task/Prompt schemas | ✓ VERIFIED | Regression check passed; all six axes at lines 212-217 |
| `src/ccf/agents/archetypes.py` | Six ArchetypeComponent bundles | ✓ VERIFIED | All six IDs confirmed |
| `src/ccf/agents/composition.py` | D-IMPL-19 composition | ✓ VERIFIED | Regression: suite green |
| `src/ccf/agents/factory.py` | Sole construction path; governed bound_skills seam | ✓ VERIFIED | Sole `Agent(...)` site line 304; `BoundSkillView | None` seam; `AmbiguousPinnedVersionError`; agent-step class check |
| `src/ccf/agents/agent.py` | No loop; replay conditioning with no false-claim path | ✓ VERIFIED | Required `grant_set_hash` kwarg; `FalseGrantClaimError` refusal |
| `src/ccf/agents/errors.py` | Typed errors incl. FalseGrantClaimError | ✓ VERIFIED | `class FalseGrantClaimError` at line 84 |
| `src/ccf/skills/catalog.py` | 4-type entry schema, registry-derived discovery | ✓ VERIFIED | IN-03 closed: `keys_of_class`-derived discovery |
| `src/ccf/skills/grants.py` | Per-agent state machine, tier-1 refusals, D-07 hash | ✓ VERIFIED | Previously DEFECTIVE; CR-01/WR-02/WR-04/WR-05 all confirmed fixed in code |
| `src/ccf/skills/dispatch.py` | local/tool dispatch | ✓ VERIFIED | Regression: suite green |
| `src/ccf/controlplane/registry.py` | Injected shared AuditLog; peek; keys_of_class | ✓ VERIFIED | `audit_log` injection line 216, read-only property line 226; unaudited `peek` line 468; `keys_of_class` line 457 |
| `tools/lints/no_hardcoding.py` | CINV-01c with alias tracking + explicit allowlist | ✓ VERIFIED | WR-06 closed; behavioral fixtures exercise both holes |
| `docs/PHASE_I2_GATE.md` | Accurate gate rows 6-7 + gap-closure note | ✓ VERIFIED | Rows 6-7 describe the actual fixed mechanisms; gap-closure note maps 05-08..05-10 to CR-01/WR-01..WR-08/IN-01/02/03/08 |

### Key Link Verification

| From | To | Via | Status |
| --- | --- | --- | --- |
| tests/integration/test_agent_slice.py | skills/grants.py | per-agent `grant_set_hash(content_hash(definition))` into dimension 4 | ✓ WIRED (previously HOLLOW) |
| agents/factory.py | skills/grants.py | `BoundSkillView` sole-producer seam | ✓ WIRED |
| skills/grants.py | controlplane/registry.py | single shared AuditLog at composition time | ✓ WIRED (previously PARTIAL) — one log, one sequence, regression test passing |
| factory.py / grants.py | registry.py | `AmbiguousPinnedVersionError` at both declared-semver loops | ✓ WIRED |
| tests/lints/test_cinv01c_behavioral.py | tools/lints/no_hardcoding.py | alias-bypass and allowlist fixtures | ✓ WIRED |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Full test suite | `.venv/bin/python -m pytest -q -m "not postgres"` | 577 passed, 2 skipped (the two declared CINV-04 deferral skips), 12 deselected | ✓ PASS |
| Lint suite | `.venv/bin/python -m tools.lints` | exit 0 | ✓ PASS |
| Strict typing | `.venv/bin/python -m mypy --strict src tools` | no issues in 74 files | ✓ PASS |
| Two-agent grant-hash regression | targeted pytest | 6 passed (TestGrantSetHash) | ✓ PASS |
| Tenant/collision/wedged/missing regressions | targeted pytest `-k` | 4 passed | ✓ PASS |
| Debt markers (TBD/FIXME/XXX) in phase-modified modules | grep over agents, skills, lints, registry | none | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plans | Status | Evidence |
| --- | --- | --- | --- |
| AGNT-01 (Agent base + six archetypes) | 05-02, 05-03, 05-07 | ✓ SATISFIED | SC1 verified (regression) |
| AGNT-02 (Agent & Task Factory + D-IMPL-28 + No-Hardcoding CI) | 05-01, 05-02, 05-04, 05-07, 05-10 | ✓ SATISFIED | SC2 + SC4 verified; WR-06 lint holes closed |
| AGNT-03 (Skill catalog: registration, discovery, governed grant/revoke with replay capture) | 05-05, 05-06, 05-07, 05-08, 05-09, 05-10 | ✓ SATISFIED | Previously BLOCKED on CR-01; per-agent D-07 hash + by-construction capture now verified in code with two-agent regression |

No orphaned requirements: REQUIREMENTS.md maps exactly AGNT-01/02/03 to Phase 5, all claimed by plans.

### Anti-Patterns Found

None blocking. The post-gap-closure code review (05-REVIEW.md) carries 5 warnings / 6 info as advisory findings for §3.1 triage (including the IN-07 test-scoping carry-forward recorded in the gate doc); no critical findings remain.

### Human Verification Required

None. All checks in this phase are programmatically verifiable; no plan carried deferred `<human-check>` blocks.

### Gaps Summary

No gaps remain. The prior verification's single FAILED truth (SC3) and its full finding cluster are closed and verified directly in the codebase, not from summary claims: `grant_set_hash` is per-agent with a required argument and a two-agent regression test; the false-zero-grants default is gone and refused with a typed error; the `bound_skills` seam admits only `GrantLedger.bound_view` output; registry and grant-ledger events share one injected AuditLog with one sequence; tenant-coherence, resolve-before-mutate, and same-name-collision refusals are in place; the CINV-01c lint's alias and substring-exemption holes are closed with behavioral fixtures; pinned-semver ambiguity is a typed refusal; catalog discovery is registry-derived; TaskFactory class-checks agent steps; and the gate document now describes the mechanisms as they actually are. Full sweep green: 577 passed / 2 declared skips, lints exit 0, mypy --strict clean. No regressions in the three previously-verified truths.

Phase goal achieved. The D-GATE-I.2 package is ready to present to Dave per CLAUDE.md §3.1 (approval authority remains Dave's alone).

---

_Verified: 2026-07-26T18:00:00Z_
_Verifier: Claude (gsd-verifier)_
