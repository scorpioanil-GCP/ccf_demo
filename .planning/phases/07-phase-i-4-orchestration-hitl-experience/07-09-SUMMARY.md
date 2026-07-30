---
phase: 07-phase-i-4-orchestration-hitl-experience
plan: 09
subsystem: mcp
tags: [mcp, experience, hitl, front-door, EXPR-01, D-IMPL-20]
requires:
  - 07-03 (render_tool_surface — the D-IMPL-56 shared derivation)
  - 07-04 (HITLTransportProtocol, HumanPrincipalBinding)
  - 07-07 (ApprovalGate, hitl_actions_block dim-2 discipline)
  - 06 wave (egress.py structure, auth.py D-26 posture, crossproc fixture)
provides:
  - Experience-surface MCP edge (runtime/ccf_runtime/mcp/experience.py)
  - HITL MCP transport (runtime/ccf_runtime/mcp/hitl_server.py)
affects: [phase-07 verification, examples 04/05, D-GATE-I.4]
tech-stack:
  added: []
  patterns:
    - egress.py whole-file server structure (stateless_http=True, built never started, resolver-injection Protocols, canonical bytes, tenant as per-call URI segment)
    - D-26 required verifier+settings auth pair on both new servers
    - new MCP role = new module + new scheme + new role-separation rows, never a merged server
key-files:
  created:
    - runtime/ccf_runtime/mcp/experience.py
    - runtime/ccf_runtime/mcp/hitl_server.py
    - tests/crossproc/servers/mcp_experience_child.py
    - tests/crossproc/servers/mcp_hitl_child.py
    - tests/crossproc/test_experience_edge.py
    - tests/crossproc/test_hitl_mcp.py
  modified:
    - tests/invariants/test_mcp_role_separation.py
decisions:
  - "Experience edge owns its own URI scheme (ccf-experience-product://): a replay record must never confuse a front-door address with an egress (live) or artifact (immutable) address — the T-06-16 split extended to the third and fourth roles (ccf-hitl-queue:// likewise)"
  - "Both new servers are authenticated with the required D-26 verifier+settings pair (threat register T-07-19: auth posture on both servers)"
  - "procedure skills are omitted from the experience agent listing, never surfaced as tools (D-IMPL-56/T-07-05 — no seam-2 surface exists to render)"
  - "submit_hitl_action's input schema is the D-IMPL-21 field set flattened into required tool parameters; naive action_time refused typed (NaiveActionTimeRefused, D-IMPL-38)"
metrics:
  duration: "~50 min"
  completed: 2026-07-30
---

# Phase 07 Plan 09: Experience MCP Edge + HITL MCP Transport Summary

Front door 1 of 3 delivered (EXPR-01, discharging the D-GATE-I.3 named deferral): products AND agents on a role-separated Experience MCP edge, and the D-IMPL-20 primary authority channel exposing HITL queues as Resources and binding-complete actions as Tools.

## What Was Built

### Task 1 — Experience-surface MCP edge (`experience.py`)

- `ccf-experience-product://{tenant}/{product_class}/{version}` Resources over an injected `ExperienceProductResolverProtocol` (same keyword-only signature as the egress resolver, so one deployment resolver serves both roles structurally — modules stay separate).
- Agents as MCP Tools: `list_agents` returns a typed `AgentToolCatalog` whose per-agent listing composes artifact-carried values only and renders every bound skill through `ccf.skills.toolsurface.render_tool_surface` (CINV-01; D-IMPL-56); `invoke_agent` passes through an injected `AgentInvokerProtocol` — the deployment's factory path — verbatim.
- Zero privileged paths (T-07-20): the module imports no factory, no Control Plane, no agents package, no graph package; the crossproc test greps the source for all of them.
- Crossproc proof: a real subprocess assembles the banking product through L1→L6, factory-constructs the fixture `auto` agent through `AgentFactory` + `ControlPlaneRegistry` with a governed `metrics_local` grant, dispatches the bound skill over the wire, and lands the decision in a `DecisionReplayRecord` written through `ReplayWriter` over a `FileArtifactStore` — the parent independently recomputes the agent definition hash and verifies dimension 4 plus the content-derived replay address.

### Task 2 — HITL MCP transport (`hitl_server.py`)

- `ccf-hitl-queue://{tenant}` Resources over an injected `HitlQueueViewProtocol`; reads never consume; tenant partitioning proved cross-tenant on the wire.
- `submit_hitl_action` Tool requires every `HumanPrincipalBinding` field as a required parameter — the input schema *is* the D-IMPL-21 field set, so a call missing any field is a typed tool-level refusal before a submission can exist, and the pending event survives the refused call (asserted).
- Dim-2 landing proved verbatim: the parent recomputes the exact `HitlActionRecord` canonical block the gate serializes and asserts byte equality against `policy_bindings.hitl_actions` in the returned replay record.
- Module docstring states the D-IMPL-20 notification/authority separation (webhooks notify-only; authority only through this surface) and the D-22 scoping of which claim is structural vs. demonstrated.

### Role separation rows

`tests/invariants/test_mcp_role_separation.py` gained six new tests (additions only — `git diff` shows zero removed lines): module/import separation, scheme ownership, and no-graph-import scans for both new roles, cross-checked against egress, artifact, and each other. Existing rows untouched.

## Verification

- `tests/crossproc/test_experience_edge.py` + `tests/crossproc/test_hitl_mcp.py` + `tests/invariants/test_mcp_role_separation.py`: all green.
- `tools.lints --all`: exit 0.
- Full suite: **1161 passed, 0 failed, 0 skipped** (baseline 1141).
- Acceptance greps: `stateless_http=True` present in both modules, no server-start call; `grep -c sleep tests/crossproc/test_experience_edge.py` == 0.

## Task Commits

| Task | Phase | Commit | Description |
| ---- | ----- | ------ | ----------- |
| 1 | RED | 622297e | failing crossproc + invariant tests for the experience edge |
| 1 | GREEN | c30fecc | `experience.py` — products + agents front door |
| 2 | RED | f6165e1 | failing crossproc + invariant tests for the HITL transport |
| 2 | GREEN | a6f38c2 | `hitl_server.py` — D-IMPL-20 authority channel |

## Deviations from Plan

None - plan executed exactly as written. (The parent tests read authenticated resources via `run_with_session` + a local helper rather than `McpResourceClient`, because that client takes no `http_client_factory`; this is test plumbing, not a plan change.)

## Known Stubs

None.

## Threat Flags

None — all four surfaces introduced (two Resources, two Tool sets) are in the plan's threat model (T-07-19..22), each with its mitigation implemented and tested.

## Self-Check: PASSED

All created files exist on disk; all four task commits present in git log; no file deletions across the plan's commits; working tree clean before the SUMMARY commit.

## TDD Gate Compliance

Both tasks followed RED→GREEN with a `test(...)` commit demonstrating failure (ModuleNotFoundError on the not-yet-existing server modules plus the behavioral assertions) before each `feat(...)` commit. No refactor commits were needed.
