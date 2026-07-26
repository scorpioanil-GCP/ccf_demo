---
phase: 05-phase-i-2-agent-specialization-framework
verified: 2026-07-26T09:30:00Z
status: gaps_found
score: 3/4 must-haves verified
overrides_applied: 0
gaps:
  - truth: "Skill catalog supports registration, discovery, and runtime grant/revoke; the policy-compatibility check refuses a grant exceeding the agent's policy regime or context contract; every grant/revocation and the skill-set in force land in the replay record (ROADMAP SC3)"
    status: partial
    reason: "Registration, discovery, grant/revoke, tier-1 refusal, and replay capture all exist and pass tests — but the in-force skill-set identity recorded in replay dimension 4 is ledger-wide, not per-agent (REVIEW CR-01). With more than one agent sharing a GrantLedger (the normal Control Plane topology), every decision's grant_set_hash includes other agents' grants, and a grant to agent B changes the recorded skill-set of agent A's decisions. This is incorrect replay data written by construction — a direct violation of CLAUDE.md §6.2 ('a decision replays against the skills the agent actually had'). Additionally, the capture is caller-discipline rather than by-construction: Agent.perspective_conditioning defaults grant_set_hash to the positive NO_GRANTS claim (WR-01), and AgentFactory.construct(bound_skills=...) accepts arbitrary unvalidated mappings, bypassing the two-tier governance at the supported construction path (WR-03)."
    artifacts:
      - path: "src/ccf/skills/grants.py"
        issue: "effective_hashes() (line ~585) and grant_set_hash() (line ~593) ignore agent_definition_hash; contrast _effective_entries() which correctly filters per-agent. Also: request() wedges grants in 'requested' on missing catalog entry (WR-04); same-skill-name grant collision silently drops one (WR-05); no tenant-coherence check on the grant path (WR-02)"
      - path: "src/ccf/agents/agent.py"
        issue: "perspective_conditioning(grant_set_hash: str = NO_GRANTS_SET_HASH) — a skilled agent's caller who omits the argument records a false positive 'zero grants' claim in the audit record (WR-01)"
      - path: "src/ccf/agents/factory.py"
        issue: "construct(bound_skills: Mapping[str, object]) passes any objects through unchecked — ungoverned capability injection at the legitimate front door (WR-03)"
      - path: "tests/integration/test_agent_slice.py"
        issue: "Line 369 passes ledger.grant_set_hash() (ledger-wide) into dimension 4; all tests use one agent per ledger so the defect is invisible to the suite"
    missing:
      - "Scope effective_hashes()/grant_set_hash() by agent_definition_hash; update slice-test call site; add a two-agent test asserting agent A's hash is unaffected by a grant to agent B (CR-01 fix)"
      - "Make grant_set_hash a required argument of perspective_conditioning, or refuse the NO_GRANTS default when bound_skills is non-empty (WR-01)"
      - "Type/narrow bound_skills so its only producer is GrantLedger.bound_view (WR-03)"
      - "Resolve catalog entry before mutating grant state, or roll back + audit on lookup failure (WR-04); refuse or define ordering for same-skill-name grant collisions (WR-05); add tenant-coherence check on the grant path (WR-02)"
human_verification: []
---

# Phase 5: Phase I.2 — Agent Specialization Framework Verification Report

**Phase Goal:** Agents are declared, versioned Control Plane artifacts produced exclusively by the Agent & Task Factory from the six shipped archetypes, specialized through the two governed channels
**Verified:** 2026-07-26
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Phase 5 Success Criteria)

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Unified Agent base + six archetypes in `/src`, no agent instances/prompts/domain values in library code; composition per D-IMPL-11/19 | ✓ VERIFIED | All six archetype IDs (`workflow_task`, `document_intelligence`, `analytics_insights`, `monitoring_surveillance`, `content_generation`, `context_assembly`) implemented in `src/ccf/agents/archetypes.py`; D-IMPL-19 composition (dedupe / declaration-order-wins / typed contradiction error) in `src/ccf/agents/composition.py` with `tests/agents/test_composition.py` passing; No-Hardcoding lint suite exits 0 — all domain values confirmed in `tests/fixtures/banking/` (REVIEW concurs) |
| 2 | Agent & Task Factory constructs only from definition artifacts (D-IMPL-28); no supported bypass path; No-Hardcoding lint rejects bypass and prompt literals | ✓ VERIFIED | `AgentFactory`/`TaskFactory` in `src/ccf/agents/factory.py` resolve through Control Plane; sole `Agent(...)` call site in factory; CINV-01c behavioral fixture (`tests/lints/test_cinv01c_behavioral.py`) proves the lint fires; `python -m tools.lints` exit 0. Caveats carried as warnings: lint has static bypass holes — `import ... as` alias and `"factory"` path-substring exemption (WR-06); `bound_skills` parameter is an ungoverned side door counted under SC3 (WR-03) |
| 3 | Skill catalog registration/discovery/grant/revoke; tier-1 refusal; every grant/revocation and the skill-set in force land in replay | ✗ FAILED | Mechanism exists and 556 tests pass, but `GrantLedger.grant_set_hash()` is **ledger-wide, not per-agent** (`src/ccf/skills/grants.py` `effective_hashes`/`grant_set_hash` take no `agent_definition_hash`, verified directly in code) — dimension 4 records the wrong in-force skill-set whenever >1 agent shares a ledger. "By construction" claim is actually caller discipline (WR-01 default sentinel; WR-03 unchecked `bound_skills`). The skill-set-in-force replay commitment (CLAUDE.md §6.2, CINV-04) is not correctly met |
| 4 | All six specialization axes expressible in the definition artifact and versioned; axis change ⇒ new agent version visible in replay | ✓ VERIFIED | `AgentDefinition` in `src/ccf/agents/definitions.py` carries `archetypes`, `context_contract`, `perspective`, `policy_regime`, `halflife_debt_profile`, `instruction_bindings` (frozen, extra=forbid); six-axis version matrix in `tests/agents/test_factory.py`; D-05 hash-verified bump refusal in `tests/controlplane/test_hash_verified_bump.py`; dimension-4 definition hash + versioned URI asserted in `tests/integration/test_agent_slice.py`. Caveat (warning): `register_typed`-path pinned resolution is ambiguous — same declared semver can name two contents, oldest silently wins (WR-08) |

**Score:** 3/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `src/ccf/agents/definitions.py` | Six-axis AgentDefinition + TaskDefinition + PromptArtifact schemas | ✓ VERIFIED | All axes present; ArtifactClass constants; JSON Schema export tested |
| `src/ccf/agents/archetypes.py` | Six ArchetypeComponent bundles | ✓ VERIFIED | All six IDs registered; no domain values |
| `src/ccf/agents/composition.py` | D-IMPL-19 composition | ✓ VERIFIED | Dedupe/order-wins/error, canonical-bytes identity |
| `src/ccf/agents/factory.py` | Sole construction path via Control Plane | ⚠️ VERIFIED with warning | Works; `bound_skills: Mapping[str, object]` unvalidated (WR-03); TaskFactory step refs not class-checked (IN-08) |
| `src/ccf/agents/agent.py` | Concrete Agent, no loop, replay conditioning | ⚠️ VERIFIED with warning | No loop, tenant-isolated consume; WR-01 default sentinel |
| `src/ccf/agents/prompts.py` | Jinja2 parse-only validation (D-13) | ✓ VERIFIED | `find_undeclared_variables`; no `render()` in /src |
| `src/ccf/skills/catalog.py` | 4-type entry schema, registration/discovery | ⚠️ VERIFIED with warning | Works; discovery uses volatile per-instance index (IN-03) |
| `src/ccf/skills/grants.py` | State machine, tier-1, ApprovalSink, grant-set hash | ✗ DEFECTIVE | CR-01 (ledger-wide hash), WR-02, WR-04, WR-05 |
| `src/ccf/skills/dispatch.py` | local/tool dispatch, NotYetBound for mcp/a2a | ✓ VERIFIED | `tests/skills/test_dispatch.py` passing |
| `tools/lints/no_hardcoding.py` | CINV-01c factory-bypass lint | ⚠️ VERIFIED with warning | Fires on behavioral fixture; static holes per WR-06 |
| `docs/PHASE_I2_GATE.md` | Gate checklist + evidence map + I.3 handoff | ⚠️ VERIFIED with warning | Exists with success-criteria evidence map (§3); rows 6–7 overstate mechanism (IN-01: "by construction" is caller discipline; "one AuditLog" is two logs, WR-07) |

### Key Link Verification

| From | To | Via | Status |
| --- | --- | --- | --- |
| definitions.py | contracts/base.py | CCFContract subclassing | ✓ WIRED |
| factory.py | controlplane/registry.py | Control Plane resolution | ✓ WIRED |
| factory.py | prompts.py | instruction-binding validation at construct | ✓ WIRED |
| factory.py | composition.py | compose during construct | ✓ WIRED |
| skills/catalog.py | controlplane/registry.py | D-05 versioned registration | ✓ WIRED |
| skills/grants.py | controlplane/audit.py | transitions → AuditLog | ⚠️ PARTIAL — wired, but ledger log is disjoint from registry's private log (WR-07); "Control Plane is the audit plane, singular" (§7.8.2) not held |
| slice test → replay/record.py | dimension-4 assertions | grant_set_hash / agent_definition_hash | ⚠️ HOLLOW for grants — asserts a ledger-wide value; per-agent correctness untested (all test worlds hold one agent) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Full test suite | `.venv/bin/python -m pytest -q -m "not postgres"` | 556 passed, 2 skipped (exactly the 2 declared invariant skips), 12 deselected | ✓ PASS |
| Lint suite (CINV-01a/b/c, harness imports, @algorithmic) | `.venv/bin/python -m tools.lints` | exit 0 | ✓ PASS |
| Strict typing | `.venv/bin/python -m mypy --strict src tools` | no issues in 74 files | ✓ PASS |
| Debt markers in phase files | grep TBD/FIXME/XXX over src/ccf/agents, src/ccf/skills, lints | none | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plans | Status | Evidence |
| --- | --- | --- | --- |
| AGNT-01 (Agent base + six archetypes) | 05-02, 05-03, 05-07 | ✓ SATISFIED | SC1 verified |
| AGNT-02 (Agent & Task Factory + D-IMPL-28 artifacts + No-Hardcoding CI) | 05-01, 05-02, 05-04, 05-07 | ✓ SATISFIED | SC2 + SC4 verified |
| AGNT-03 (Skill catalog: registration, discovery, governed grant/revoke with replay capture) | 05-05, 05-06, 05-07 | ✗ BLOCKED | SC3 failed on CR-01 — replay capture of skill-set in force is incorrect per-agent and not by-construction |

No orphaned requirements: REQUIREMENTS.md maps exactly AGNT-01/02/03 to Phase 5, all claimed by plans.

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
| --- | --- | --- | --- |
| src/ccf/skills/grants.py:585-603 | Ledger-wide identity used as per-agent replay fact | 🛑 Blocker | Wrong dimension-4 data by construction with >1 agent (CR-01) |
| src/ccf/agents/agent.py:291 | Positive false-claim default (`= NO_GRANTS_SET_HASH`) | ⚠️ Warning | Audit record integrity depends on caller discipline (WR-01) |
| src/ccf/agents/factory.py:212+ | Unvalidated `Mapping[str, object]` capability injection | ⚠️ Warning | Channel-2 governance bypass at supported path (WR-03) |
| src/ccf/skills/grants.py | Cross-tenant grants admissible; wedged `requested` state; silent same-name collision | ⚠️ Warning | WR-02/WR-04/WR-05 |
| tools/lints/no_hardcoding.py | Alias-import bypass; `"factory"` substring exemption | ⚠️ Warning | Mechanism of record narrower than ruling (WR-06) |
| controlplane registry vs grant ledger | Two disjoint audit logs | ⚠️ Warning | WR-07; gate doc row 7 overstates |
| tests/agents/harness_double.py:52 | Stale `pragma: no cover` comment | ℹ️ Info | IN-02 |

### Human Verification Required

None. All checks in this phase are programmatically verifiable; no plan carried deferred `<human-check>` blocks.

### Gaps Summary

The phase is close: archetype/agent separation is real, the factory is the sole construction path, the No-Hardcoding boundary genuinely holds, all six axes are expressible and versioned, and the entire suite/lint/mypy sweep is green. The gap is concentrated exactly where the phase's audit claims are strongest — the skilling channel. `grant_set_hash()` records a ledger-wide identity as an agent's in-force skill-set, so replay dimension 4 is wrong the moment two agents share the Control Plane grant machinery, and the surrounding seams (default no-grants sentinel, unchecked `bound_skills`, disjoint audit logs, wedged grant state, missing tenant check) mean "audit by construction" is presently "audit by well-behaved caller." Every test world holds one agent, one tenant, and disciplined callers, which is why the suite is green over the defect. SC3/AGNT-03 cannot be marked achieved until CR-01 is fixed with a two-agent regression test; the WR-level seams should be closed in the same pass since they share the grants.py locus.

Note per §3.1: the review's critical finding is a blocking finding — the phase does not complete around it, and `D-GATE-I.2` should not be logged until it is closed.

---

_Verified: 2026-07-26T09:30:00Z_
_Verifier: Claude (gsd-verifier)_
