---
phase: 07-phase-i-4-orchestration-hitl-experience
plan: 20
subsystem: hitl-identity
tags: [hitl, identity, auth, http, mcp, d-impl-67, gap-closure]
requires:
  - 07-15 (HITL MCP transport, submit_hitl_action tool)
  - 07-16 (principal_from_token_grant, create_app auth hook, token_grant stash)
provides:
  - Auth-composed HTTP HITL action door (D-IMPL-67 item 1)
  - Verified-identity-bound submit_hitl_action MCP tool (D-IMPL-67 item 2)
  - End-to-end hardened-path proof into replay dimension 2 (D-IMPL-67 item 3)
affects:
  - runtime/ccf_runtime/http_api/routes/hitl.py
  - runtime/ccf_runtime/mcp/hitl_server.py
tech-stack:
  added: []
  patterns:
    - "one derivation mechanism (principal_from_token_grant) serves both doors"
    - "subject_id as a claim-that-must-match preserves the D-IMPL-21 input schema"
key-files:
  created:
    - tests/http_api/test_hitl_door_identity.py
  modified:
    - runtime/ccf_runtime/http_api/routes/hitl.py
    - runtime/ccf_runtime/mcp/hitl_server.py
    - tests/crossproc/test_hitl_mcp.py
    - tests/crossproc/servers/mcp_hitl_child.py
decisions:
  - "MCP tool keeps subject_id as a required parameter (claim that must match) so the D-IMPL-21 field-set input schema is preserved"
  - "Child test server's token client_id set to the fixture credit officer's subject_id so the existing replay-dim-2 test doubles as the bound-subject assertion"
metrics:
  duration: "~15 minutes"
  completed: "2026-07-30"
  tests: "1315 passed / 0 skipped (baseline 1307 + 8 new)"
---

# Phase 7 Plan 20: Wire Identity into the HITL Doors (D-IMPL-67) Summary

Both HITL doors now bind the audited subject to the deployment-verified identity through the shared `principal_from_token_grant` derivation, with typed refusals on conflicting caller claims and an end-to-end proof into replay dimension 2.

## What Was Built

**HTTP door (item 1).** `POST /hitl/actions` now takes `Request`; when `create_app` bound an auth hook, the verified `TokenGrant` on `request.state.token_grant` governs the submission: a body principal whose `subject_id` conflicts with `grant.client_id` is a 403 (`HTTPException` detail names the identity conflict, cites D-IMPL-67/D-IMPL-21, never echoes the token) before anything touches the transport; a matching submission has its principal *rebuilt* through `principal_from_token_grant` (no caller subject parameter exists on that mechanism) with every other principal field carried verbatim. With no hook bound, the path is byte-identical to the T-07-24 posture.

**MCP door (item 2).** `submit_hitl_action` reads the server-verified `AccessToken` via a module-level `get_access_token` import (the monkeypatch seam). `None` → `UnverifiedCallerRefused`; a `subject_id` conflicting with `token.client_id` → `SubjectIdentityConflictRefused` (both in `__all__`, neither echoes token values). The binding that reaches the injected authority route is derived through `principal_from_token_grant` over a `TokenGrant` built from the verified token — the inline `HumanPrincipalBinding` construction and its `ccf.hitl.principal` imports were removed. The tool signature is unchanged: `subject_id` remains required, now as a claim that must match. T-07-22's role-separation grep suite stays green — the server still holds only the two injected Protocol callables.

**Hardened-path proof (item 3).** `test_hardened_path_verified_subject_reaches_replay_dim2` composes: enqueue → authed POST (Bearer, matching subject) → recorded submission off the transport → `ApprovalGate.resolve` → `build_replay_record(..., hitl_actions=resolution.hitl_actions_block)`. The verified subject `auditor-1` is asserted in the recorded submission, in `GateResolution.hitl_actions_block`, and in the built record's `policy_bindings.hitl_actions` (verbatim block equality included).

## Task Commits

| Task | Commits | Description |
| ---- | ------- | ----------- |
| 1 | 91f9e7c (RED), 6589e91 (GREEN) | HTTP door derivation + typed 403 conflict refusal |
| 2 | 1aa5fea (RED), 6df14cb (GREEN) | MCP tool subject binding + typed refusals |
| 3 | 56e9e4c | End-to-end hardened-path proof + full regression |

## Verification

- Full matrix under `CCF_REQUIRE_HARNESSES=1`: **1315 passed / 0 failed / 0 skipped** (baseline 1307 + 8 new tests).
- `mypy --strict src runtime tools`: clean, 167 files.
- `tools.lints --all`: exit 0.
- `tests/http_api/test_auth.py` and `tests/http_api/test_openapi.py` byte-unmodified vs baseline 360bc0b (`git diff --name-only` empty); `AUTH_POSTURE_SENTENCE` byte-identity test passes unmodified.
- Acceptance greps: `principal_from_token_grant` ×3 in routes/hitl.py, ×4 in hitl_server.py; `get_access_token` ×2 in hitl_server.py; `403` present in routes/hitl.py.

## Deviations from Plan

**1. [Minor] Task 3's composed test passed on first run (no RED).** Item 3 is a proof of the mechanism wired in Tasks 1–2, not new behavior — a failing-first state is not constructible once both doors are wired. Committed as a single `test(...)` commit.

**2. [Minor] Task 2's RED commit includes the child-server `CLIENT_ID` change** (to `credit-officer-11`, the fixture approver's subject). The plan authorizes this edit "as needed for the test asserting the bound subject"; it belongs with the RED tests because the cross-process conflict test depends on it.

Otherwise the plan executed exactly as written.

## Threat Register Outcomes

| Threat | Disposition | Outcome |
| ------ | ----------- | ------- |
| T-07.2-01 (HTTP spoofing) | mitigate | 403 before transport touch; derivation via mechanism — Test A/B |
| T-07.2-02 (MCP spoofing) | mitigate | typed refusals on conflict/absence — unit + crossproc tests |
| T-07.2-03 (repudiation) | mitigate | verified subject asserted in dim-2 block and built record |
| T-07.2-04 (info disclosure) | mitigate | refusal texts asserted token-free (HTTP Test A; MCP unit test) |
| T-07.2-05 (unbound door) | accept | T-07-24 posture unchanged, Test C |

## Self-Check: PASSED

- tests/http_api/test_hitl_door_identity.py — FOUND
- runtime/ccf_runtime/http_api/routes/hitl.py contains `token_grant` — FOUND
- runtime/ccf_runtime/mcp/hitl_server.py contains `get_access_token` — FOUND
- Commits 91f9e7c, 6589e91, 1aa5fea, 6df14cb, 56e9e4c — FOUND in log
