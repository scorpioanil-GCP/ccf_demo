---
phase: 05-phase-i-2-agent-specialization-framework
plan: 06
subsystem: skills
tags: [skills, grants, governance, dispatch, d-impl-29, d-07, d-08, d-09, d-10, cinv-04, tdd]
requires: [05-05]
provides:
  - SkillGrant versioned Control Plane artifact + GrantLedger state machine (requested → pending-approval → effective/refused, plus revoked) behind the @runtime_checkable ApprovalSink Protocol (D-09)
  - tier-1 non-waivable policy-compatibility check — structural subset logic over opaque identifiers with typed returned GrantRefusals (D-IMPL-29)
  - D-07 grant_set_hash = content_hash(frozenset(active grant hashes)) + live bound_view for agent skill binding
  - local_callable/tool dispatch with typed results; mcp/a2a raise typed NotYetBound (D-08)
  - replay dimension 4 carries the captured grant-set hash; CINV-04 skill-set-capture ACTIVE (3 skips → 2, D-10)
  - ApprovalSink conformance suite (I.4's ApprovalGate joins unchanged)
affects: [05-07, phase-6, phase-7]
tech-stack:
  added: []
  patterns:
    - grant transitions audited as new grant_* AuditAction members through the existing AuditLog (no second log type)
    - skill_governance envelope (PolicyRegimeGovernance) read from the policy-regime declaration — mechanism schema; scope values and the tier-2 flag stay deployment statements in YAML
    - bound_skills held by reference — the ledger's live Mapping view resolves at invoke time so grants/revocations never touch agent identity
key-files:
  created:
    - src/ccf/skills/grants.py
    - src/ccf/skills/dispatch.py
    - tests/skills/test_grants.py
    - tests/skills/test_dispatch.py
    - tests/skills/sinks.py
    - tests/conformance/test_approval_sink.py
    - tests/fixtures/banking/skills/grants.yaml
    - tests/fixtures/banking/skills/callables.py
  modified:
    - src/ccf/skills/__init__.py
    - src/ccf/agents/errors.py
    - src/ccf/agents/agent.py
    - src/ccf/agents/factory.py
    - src/ccf/controlplane/audit.py
    - tests/invariants/test_replay_by_construction.py
    - tests/integration/test_agent_slice.py
    - tests/agents/test_consumption_discipline.py
    - tests/agents/test_factory.py
    - tests/fixtures/banking/skills/covenant_metrics_tool.yaml
    - tests/fixtures/banking/agents/covenant_analytics.yaml
    - tests/fixtures/banking/tasks/covenant_review_task.yaml
decisions:
  - "The tier-1 governance envelope is read from a `skill_governance` field inside the policy-regime declaration, validated into the typed PolicyRegimeGovernance contract — the field name is mechanism schema (like `requirements` on a catalog entry); permitted scopes and the tier-2 flag are deployment statements in YAML"
  - "Grant transitions audit as new grant_* members of the existing AuditAction Literal rather than a parallel log type — one audit plane, one event contract (RESEARCH Don't-Hand-Roll)"
  - "Tool dispatch returns a typed ToolInvocation value and executes nothing — the effect-as-value discipline; the SDK ships no command execution surface"
  - "NotYetBound is a typed RuntimeError (not a returned refusal): a granted, valid mcp/a2a entry whose transport this build lacks is a deployment-shape fact, not a bad artifact (RESEARCH Open Question 2 resolution, documented on the class)"
  - "ledger.grant_set_hash() returns the positive NO_GRANTS_SET_HASH sentinel when zero grants are effective; the pure module function stays exactly content_hash(frozenset(...)) per D-07"
metrics:
  duration: ~12 min
  completed: 2026-07-26
  tasks: 2
  tests: 568 passed, 2 skipped
---

# Phase 5 Plan 06: Two-Tier Grants, Dispatch, and Active Skill-Set Capture Summary

D-IMPL-29 two-tier skilling governance ships end to end: a non-waivable structural tier-1 check plus the full grant state machine behind the ApprovalSink Protocol, local/tool dispatch with typed NotYetBound for mcp/a2a, and the D-07 grant-set hash captured in replay dimension 4 — with the CINV-04 skill-set-capture invariant flipped active (suite now shows exactly 2 skips per D-10). AGNT-03 complete.

## Tasks

| Task | Name | Commits (RED/GREEN) |
| ---- | ---- | ------------------- |
| 1 | Grants — tier-1 check, state machine, ApprovalSink, audit, grant-set hash | 65b3f70 / 397fa37 |
| 2 | Dispatch + replay capture + CINV-04 activation | a174c71 / f1ae62c |

## What was built

- **`src/ccf/skills/grants.py`** (`__ccf_mode__ = "algorithmic"`) — `SkillGrant(CCFContract)` (agent by content hash, catalog entry by pinned version; two-lane D-IMPL-28 versioning; `ccf.skill-grant` artifact class registered via the D-05 path); `PolicyRegimeGovernance` envelope; typed `GrantRefusal` hierarchy in the GateRefusal style (`PolicyRegimeUnresolvable`, `GovernanceUndeclared`, `RequirementsExceedRegime` naming the excess identifiers, `ApprovalRejected`); `@runtime_checkable ApprovalSink` (one `decide` method — the state machine owns every transition and audit record, so a conforming sink cannot drop the audit obligation); `GrantLedger` with injected registry/catalog/AuditLog/sink/clock running tier 1 always before tier 2, tier-2 requirement read from the regime artifact; `grant_set_hash(frozenset)` exactly `content_hash(frozenset(active_grant_hashes))`; live `bound_view` Mapping.
- **`src/ccf/skills/dispatch.py`** — `dispatch_skill`: local_callable via importlib dotted-path resolution returning typed `SkillInvocation`; tool returning a `ToolInvocation` value; mcp/a2a raising `NotYetBound` (added to `ccf.agents.errors` with the refusal-vs-exception choice documented).
- **Agent/Factory wiring** — `Agent.invoke_skill(name, arguments=...)` dispatches the bound catalog entry; `bound_skills` held by reference (ledger live view); `AgentFactory.construct(bound_skills=...)` channel-2 seam; `Agent.perspective_conditioning(grant_set_hash=...)` records the captured D-07 value verbatim.
- **Slice + invariant** — the fixture agent gets a real governed grant of the covenant-metrics tool and dispatches it; dimension 4 carries the ledger's in-force hash, and a post-revocation record carries `NO_GRANTS` while the definition hash never moves. CINV-04 `skill-set-capture` is `status="active"` with `owning_test` pointing at the behavioral slice test; `pytest tests/invariants/test_replay_by_construction.py -rs` shows exactly 2 skips (both I.4).
- **Conformance** — `tests/conformance/test_approval_sink.py` parametrizes over sink factories (scripted double in `tests/skills/sinks.py`); I.4's ApprovalGate joins the param list with no test-body change.

## Deviations from Plan

### Auto-fixed / plan-adjacent changes

**1. [Rule 3 - Blocking] `src/ccf/controlplane/audit.py` extended with `grant_*` AuditAction members (not in the plan's file list)**
- **Found during:** Task 1 GREEN
- **Issue:** `AuditEvent.action` is a closed Literal; grant transitions cannot pass `AuditLog.append` without new members, and the plan's key_link requires every transition through the existing AuditLog.
- **Fix:** five `grant_*` members appended to the Literal with a docstring note; no existing member or behavior changed.
- **Commit:** 397fa37

**2. [Rule 3 - Blocking] downstream fixture/test re-pins after the agent-definition bump (files not in the plan's list)**
- The `wholesale-credit` policy bundle gained the `skill_governance` envelope (semver 1.0.0 → 1.1.0), cascading: agent definition `artifact_version` 1.2.0 → 1.3.0, `covenant_review_task.yaml` step ref re-pinned (+ its own bump 1.0.0 → 1.1.0), and `test_factory.py`'s bumped-mutant lane moved 1.3.0 → 1.4.0 to avoid colliding with the now-real 1.3.0.
- **Commit:** f1ae62c

**3. [Rule 3 - Blocking] `tests/agents/test_consumption_discipline.py` allowlist extended**
- The AGNT-01 import guard refused `ccf.skills.*` from `agent.py`. `ccf.skills.catalog` and `ccf.skills.dispatch` are Control Plane surface above L6 — binding them opens no path from Agent to L1–L5, which is what the guard protects. Added with a comment citing §6.2/D-08.
- **Commit:** f1ae62c

**4. [Fixture adjustment, plan-anticipated] `covenant-metrics-local` variant bumped to 1.1.0**
- `callable_ref` re-pointed at the importable fixture callable (`fixtures.banking.skills.callables.covenant_metrics`) so dispatch actually resolves it; a binding change is a content change (D-05).

## Verification

- `.venv/bin/pytest tests/ -q` → 568 passed, 2 skipped
- `.venv/bin/pytest tests/invariants/test_replay_by_construction.py -rs -x` → 7 passed, exactly 2 skipped (hitl-action-capture, workflow-trace-capture — both I.4)
- `.venv/bin/pytest tests/skills tests/conformance/test_approval_sink.py -q` → green
- `.venv/bin/mypy --strict src` → clean (63 files)
- `.venv/bin/python -m tools.lints` → exit 0 (no new allowlist entries)
- `grep -c "frozenset" src/ccf/skills/grants.py` → 10; no epoch counter or agent version bump exists anywhere in the grant path (asserted by test)

## Known Stubs

- mcp/a2a dispatch is deliberately `NotYetBound` until I.3 binds the MCP/A2A transports (D-08) — the entries validate, register, and grant; only dispatch is deferred, by ruling, with a typed exception naming the deferral.
- `ApprovalSink` decides synchronously in I.2; the suspending real ApprovalGate is I.4 scope (D-09) and joins both the state machine and the conformance suite unchanged. Approver identity is an id string only — binding is D-IMPL-21 (I.4; T-05-19 accepted).

## Threat Flags

None — all surface was in the plan's threat model: T-05-15 (tier-1 + sink gate), T-05-16 (every transition audited + CINV-04 active), T-05-17 (D-07 frozenset content hash, captured value recorded), T-05-18 (callables resolve only from registered catalog entries; refs live in fixtures/user artifacts), T-05-19 (accepted, documented on the sink).

## Self-Check: PASSED

All created files exist; commits 65b3f70, 397fa37, a174c71, f1ae62c present on `phase-i2`.

## TDD Gate Compliance

Both tasks have a `test(05-06)` RED commit (verified failing on collection before implementation) followed by a `feat(05-06)` GREEN commit. No refactor commits needed.
