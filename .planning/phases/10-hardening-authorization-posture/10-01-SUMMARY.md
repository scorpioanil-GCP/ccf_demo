---
phase: 10-hardening-authorization-posture
plan: 01
subsystem: authz
tags: [hard-04, d-impl-68, control-plane, audit, mcp]
requires: []
provides:
  - "runtime/ccf_runtime/authz package: ScopeMappingArtifact + SCOPE_MAPPING, TenantAuthorizerProtocol, ControlPlaneTenantAuthorizer, AuthzDecision, door action-ID constants"
  - "authz_decision AuditAction + AuthzDecisionAuditEvent decision-tuple event"
  - "ERROR_TENANT_UNAUTHORIZED refusal constant"
  - "A1 verdict for plan 10-03 MCP queue-read wiring"
affects: [10-03]
tech-stack:
  added: []
  patterns:
    - "HitlPolicy-style typed Control Plane artifact in runtime (RESEARCH Open Q1 placement)"
    - "GrantLedger-style audit-through-control_plane.audit_log with injected clock"
key-files:
  created:
    - runtime/ccf_runtime/authz/__init__.py
    - runtime/ccf_runtime/authz/artifact.py
    - runtime/ccf_runtime/authz/protocol.py
    - runtime/ccf_runtime/authz/refusals.py
    - tests/authz/test_scope_mapping_artifact.py
    - tests/authz/test_tenant_authorizer.py
    - tests/authz/test_authz_audit.py
    - tests/crossproc/test_fastmcp_resource_token_spike.py
  modified:
    - src/ccf/controlplane/audit.py
    - runtime/ccf_runtime/http_api/errors.py
decisions:
  - "D-11 reading: authz decisions are standalone authz_decision events in the one Control Plane audit log; correlation by tenant/action/timestamp (recorded in audit.py docstring)"
  - "Decision tuple rides on AuthzDecisionAuditEvent (derived class), not base AuditEvent fields — preserves canonical bytes of all pre-existing events (A2)"
  - "ScopeMappingArtifact lives in runtime per RESEARCH Open Q1 (adopted); /src untouched except additive audit.py"
metrics:
  duration: "~35 minutes"
  completed: "2026-08-01"
  tasks: 3
  files: 10
---

# Phase 10 Plan 01: Authorization Foundation (HARD-04) Summary

Scope-mapping Control Plane artifact with D-01 grammar, deny-by-default
ControlPlaneTenantAuthorizer auditing every allow/deny with the exact
artifact version via a new authz_decision audit event, plus empirical
closure of assumptions A1 and A2.

## Assumption Resolutions (read by plan 10-03)

### A1 — FastMCP resource-handler token access: **RESOLVED YES**
`get_access_token()` (from `mcp.server.auth.middleware.auth_context`)
returns the **verified, non-None token inside resource handlers** on an
authenticated `build_hitl_server(...)` instance — same mechanism the
action tool already uses. Proven in
`tests/crossproc/test_fastmcp_resource_token_spike.py` by an in-process
MCP client over the server's own streamable-HTTP ASGI app (lifespan
entered explicitly; Host must be `127.0.0.1:<port>` for FastMCP's
DNS-rebinding defaults). **Plan 10-03 can guard the queue-read resource
with `get_access_token()` directly.**

### A2 — AuditEvent canonical-bytes stability: **RESOLVED, with a finding**
The canonical serializer walks *every declared model field* and renders
`None` as `null`. Therefore adding optional fields to the `AuditEvent`
base class **would have changed the canonical bytes of every existing
event** — the exact drift the plan forbids. The sha256 pin written before
the change (`tests/authz/test_authz_audit.py::A2_PINNED_SHA256`) passes
unchanged after the extension because of the deviation below;
`tests/replay` + `tests/invariants/test_replay_by_construction.py` pass
with zero pin edits in the diff.

## What was built

- **`src/ccf/controlplane/audit.py` (additive):** `AuditAction` member
  `"authz_decision"` with rationale comment; `AuthzDecisionAuditEvent`
  carrying `authz_action_id` / `authz_matched_pattern` (default `None`);
  `AuditLog.append` gains the two keyword-only optionals and constructs
  the derived event only when one is supplied. Docstring records the
  D-11 reading explicitly.
- **`runtime/ccf_runtime/authz/artifact.py`:** `ScopeMappingArtifact` /
  `ScopeEntry` (Pydantic `extra=forbid`, semver lane) with a
  field_validator refusing any tenant pattern whose `*` is not the sole
  trailing character; `tenant_pattern_matches` two-branch matcher (no
  `import re` in the package); `SCOPE_MAPPING` ArtifactClass
  (`ccf.scope-mapping`). Runtime placement rationale in the docstring.
- **`runtime/ccf_runtime/authz/protocol.py`:** `AuthzDecision` frozen
  contract; `@runtime_checkable TenantAuthorizerProtocol` (single
  keyword-only `authorize`); `ControlPlaneTenantAuthorizer` taking
  keyword-only `control_plane` / `scope_mapping_key` / `clock` (no
  defaults). Per-call `resolve_latest` (D-07: a v2 registered between
  two calls is observed without reconstructing the authorizer, test-
  proven); `TypeError` on a wrong-class artifact; unregistered mapping =
  audited deny with `artifact_version=""`; both outcomes audited through
  `control_plane.audit_log` (WR-07).
- **`runtime/ccf_runtime/authz/refusals.py`:** `ACTION_HITL_QUEUE_READ`
  (`hitl.queue.read`) and `ACTION_HITL_ACTION_SUBMIT`
  (`hitl.action.submit`) — D-02 door-declared IDs shared by both doors.
- **`runtime/ccf_runtime/http_api/errors.py`:** `ERROR_TENANT_UNAUTHORIZED
  = "tenant-unauthorized"` added; nothing renamed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] D-09 tuple fields on a derived event class, not on `AuditEvent` itself**
- **Found during:** Task 2
- **Issue:** The plan's literal instruction ("AuditEvent gains additive
  optional fields") is mutually unsatisfiable with its own must-have
  truth (A2 byte-stability): `ccf.contracts.canonical._normalize`
  serializes every declared field of a model, `None` included, so fields
  on the base class change the bytes of *every* event and break the A2
  pin — the STOP condition.
- **Fix:** `AuthzDecisionAuditEvent(AuditEvent)` carries the two fields;
  `AuditLog.append` constructs it only when an authz kwarg is supplied.
  All plan must-haves hold: one member, one log, one append, full D-09
  tuple, A2 pin byte-identical, replay suites green with zero pin edits.
  This stays inside Open Q3 option (a)'s shape (additive member +
  optional event fields); the STOP-and-surface trigger ("pinned bytes
  change") never fired because the pin never broke.
- **Files modified:** src/ccf/controlplane/audit.py
- **Commit:** 930920e

**2. [Rule 3 - Blocking] A1 spike transport mechanics**
- **Found during:** Task 1
- **Issue:** `httpx.ASGITransport` does not drive the ASGI lifespan
  (FastMCP starts its session manager there) and FastMCP's DNS-rebinding
  protection refuses Host headers outside `127.0.0.1:*`/`localhost:*`.
- **Fix:** the spike enters `app.router.lifespan_context` explicitly and
  uses a loopback-with-port base URL; both quirks documented in the test
  for 10-03's benefit.
- **Files modified:** tests/crossproc/test_fastmcp_resource_token_spike.py
- **Commit:** 386403a

## Verification

- `pytest tests/authz tests/replay tests/invariants/test_replay_by_construction.py tests/crossproc/test_fastmcp_resource_token_spike.py tests/controlplane tests/hitl tests/http_api tests/lints -q` — 336 passed
- `python -m tools.lints --all` — exit 0
- `mypy --strict` (full `src` + `runtime`) — clean, 161 files
- `grep -v '^#' runtime/ccf_runtime/authz/*.py | grep -c "import re"` — 0

## Commits

| Task | Commit | Description |
| ---- | ------ | ----------- |
| 1 | 386403a | test(10-01): close assumption spikes A1 and A2 |
| 2 (RED) | b34f6a6 | test(10-01): failing decision-tuple cases |
| 2 (GREEN) | 930920e | feat(10-01): audit extension |
| 3 (RED) | 9252e94 | test(10-01): failing artifact + authorizer tests |
| 3 (GREEN) | 74c6c66 | feat(10-01): authz package + errors constant |

## Known Stubs

None — no placeholder values or unwired surfaces; the doors themselves
are wired in plan 10-03 by design.

## Threat Flags

None beyond the plan's threat model: no new network endpoint, auth path,
or schema surface outside the declared T-10-01..05 mitigations, all of
which are implemented and test-asserted here (T-10-01 deny matrix,
T-10-02 per-call resolve, T-10-03 dual-outcome audit, T-10-05 A2 pin).

## Self-Check: PASSED

All created files exist on disk; all five task commits present in git
log; no file deletions across the plan's diff range.
