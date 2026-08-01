---
phase: 10-hardening-authorization-posture
plan: 03
subsystem: authz
tags: [hard-04, d-impl-68, http-door, mcp-door, deny-by-default]
requires: [10-01]
provides:
  - "HTTP door: create_app(authorizer=...) with in-handler tenant authz on GET /hitl/queue and POST /hitl/actions"
  - "MCP door: build_hitl_server(authorizer=...) with authz in the queue resource and the action tool"
  - "HARD-04 cross-door x cross-action matrix (2 doors x 2 actions x allow/deny) with the shared ERROR_TENANT_UNAUTHORIZED constant on every deny leg"
affects: []
tech-stack:
  added: []
  patterns:
    - "in-handler authorize() with door-declared action IDs (Pitfall 1 — never a blanket router Depends)"
    - "one refusal constant, two protocol-native renderings (D-08)"
key-files:
  created:
    - tests/http_api/test_tenant_authz.py
    - tests/crossproc/test_mcp_tenant_authz.py
  modified:
    - runtime/ccf_runtime/http_api/app.py
    - runtime/ccf_runtime/http_api/routes/hitl.py
    - runtime/ccf_runtime/mcp/hitl_server.py
decisions:
  - "HTTP door: shared _grant_from/_enforce_tenant_authz helpers inside build_router keep the fail-closed TokenGrant check and the authz call identical for both handlers"
  - "MCP tool: authz enforced after identity verification (subject-conflict check), before principal derivation and the action route — a refused submit never touches the seam"
  - "Cross-door consistency test drives the real HTTP handlers (minimal FastAPI over build_router) and the real MCP handlers against one registry/authorizer/grant"
metrics:
  duration: "~25 minutes"
  completed: "2026-08-01"
  tasks: 2
  files: 5
---

# Phase 10 Plan 03: Door Enforcement (HARD-04) Summary

Deny-by-default per-tenant authorization at both Experience-Layer HITL
doors (D-IMPL-68): optional authorizer binding on `create_app` and
`build_hitl_server` (D-06), enforcement inside the handlers where the
parsed tenant and the door-declared action ID are known, typed 403 /
protocol-native refusal carrying the one shared
`ERROR_TENANT_UNAUTHORIZED` constant (D-08), and the full HARD-04
cross-door x cross-action matrix green — ROADMAP criteria 1 and 2 are now
observable.

## What was built

- **`runtime/ccf_runtime/http_api/app.py`:** `create_app` gains
  keyword-only `authorizer: TenantAuthorizerProtocol | None = None`,
  threaded to the HITL router only. `authorizer=None` leaves the routes
  byte-identical to the prior posture; `AUTH_POSTURE_SENTENCE` untouched.
- **`runtime/ccf_runtime/http_api/routes/hitl.py`:** both handlers call
  `authorize()` before any transport interaction — `GET /hitl/queue` with
  the `tenant` query param under `hitl.queue.read`, `POST /hitl/actions`
  with `submission.tenant` under `hitl.action.submit` (the RESEARCH
  tenant-source table, honored exactly). Enforcement is in-handler
  (Pitfall 1), reuses the existing fail-closed `isinstance(TokenGrant)`
  check (now shared by both routes via `_grant_from`), and is inert when
  no grant exists (auth unbound — D-06, T-07-24 posture preserved). Deny
  is `HTTPException(403, refusal_detail(ERROR_TENANT_UNAUTHORIZED, ...))`.
- **`runtime/ccf_runtime/mcp/hitl_server.py`:** `build_hitl_server` gains
  the same keyword-only `authorizer`. The queue resource guards
  `hitl.queue.read` with the URI tenant segment via `get_access_token()`
  — exactly the A1-verified mechanism from 10-01. The action tool guards
  `hitl.action.submit` after the existing identity verification, before
  principal derivation and the action route. Deny is
  `ValueError(json.dumps(refusal_detail(...)))` — same constant,
  protocol-native rendering (D-08).
- **Matrix tests:** 23 tests across the two files. HTTP legs: exact and
  prefix-pattern allows, deny-by-default (wrong tenant, unmapped scope,
  action mismatch, empty artifact), transport-untouched on deny, audit
  events for allow AND deny with the exact artifact version, and both
  posture regressions (authorizer unbound; authorizer bound but auth
  unbound). MCP legs: resource and tool x allow/deny (direct handlers
  with the signed-binding-door monkeypatch precedent), two over-the-wire
  legs on the A1 spike harness (real middleware, no monkeypatching), and
  the cross-door consistency leg asserting identical outcomes per
  (grant, tenant, action_id) across six tuples at both doors (D-02).

## Deviations from Plan

None affecting behavior — plan executed as written. Two test-harness
notes (not code deviations):

- The cross-door consistency leg's FastAPI `Depends` stash function needed
  its `Request` import at module level: with postponed annotations,
  FastAPI resolves handler annotations in module globals, and a
  function-local import made `request` a query parameter (422).
- The over-the-wire deny assertion walks the rendered exception chain:
  `ccf.mcp.client.run_with_session` wraps the task-group failure in
  `McpServerUnreachable`, so the `McpError` carrying the payload sits in
  the `__cause__` chain rather than surfacing directly.

## Verification

- `pytest tests/http_api tests/crossproc tests/authz tests/hitl tests/lints -q` — 314 passed
- `python -m tools.lints --all` — exit 0
- `mypy` (configured `--strict` over src + runtime) — clean, 161 files
- `grep -v '^#' runtime/ccf_runtime/http_api/routes/hitl.py | grep -c "authorize"` — 8 (>= 2)
- `grep -v '^#' runtime/ccf_runtime/mcp/hitl_server.py | grep -c "authorize"` — 10 (>= 2)
- Matrix coverage: 2 doors x 2 actions x allow/deny = well past the
  8-leg minimum (23 tests across the two files)

## Commits

| Task | Commit | Description |
| ---- | ------ | ----------- |
| 1 (RED) | 23ac180 | test(10-03): failing HTTP-door matrix tests |
| 1 (GREEN) | 3a9d40e | feat(10-03): HTTP HITL door enforcement |
| 2 (RED) | fcc7b04 | test(10-03): failing MCP-door matrix tests |
| 2 (GREEN) | 9c063cf | feat(10-03): MCP HITL door enforcement |

## Known Stubs

None — no placeholder values or unwired surfaces.

## Threat Flags

None beyond the plan's threat model: T-10-10 (deny-by-default before
transport, matrix-tested on all 4 surfaces), T-10-11 (tenant matched
against grant scopes, never trusted), T-10-12 (both outcomes audited via
the authorizer's Control Plane path), T-10-13 (in-handler enforcement,
grep-asserted), and T-10-14 (refusal bodies carry code + prose only — no
scope or token echo) are all implemented and test-asserted.

## Self-Check: PASSED

Both created test files and all three modified runtime files exist on
disk; all four task commits present in git log; no file deletions in the
plan's diff range.
