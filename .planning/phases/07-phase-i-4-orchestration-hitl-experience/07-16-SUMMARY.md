---
phase: 07-phase-i-4-orchestration-hitl-experience
plan: 16
subsystem: http_api
tags: [http, auth, hitl, identity, d-impl-21, d-impl-66, gap-closure]
requires:
  - runtime/ccf_runtime/mcp/auth.py (D-26 TokenSourceProtocol / TokenGrant / FileTokenSource)
  - src/ccf/hitl/principal.py (ApproverIdentity, AuthenticationContext, HumanPrincipalBinding)
provides:
  - "principal_from_token_grant — auth-context-derived HumanPrincipalBinding (D-IMPL-21 reference impl #1)"
  - "HttpAuthProtocol + BearerTokenAuth — optional bearer-auth hook at create_app (D-IMPL-66(a))"
affects:
  - Phase 8 examples (hardened HTTP surface demonstrable)
tech-stack:
  added: []
  patterns:
    - "Optional auth as a create_app keyword, never an ApiDependencies field — the frozen bundle is untouched"
    - "Per-router FastAPI dependencies list; /health exempt (liveness carries no authority)"
key-files:
  created:
    - runtime/ccf_runtime/identity_binding.py
    - runtime/ccf_runtime/http_api/auth.py
    - tests/http_api/test_auth.py
  modified:
    - runtime/ccf_runtime/http_api/app.py
decisions:
  - "AUTH_POSTURE_SENTENCE constant left byte-identical (its test passes unmodified); a separate _AUTH_HOOK_LINE sentence is appended after it in the OpenAPI description"
  - "Verified TokenGrant stashed on request.state.token_grant so route compositions and future principal derivation reach the auth context"
metrics:
  duration: "~20 min"
  completed: "2026-07-30"
---

# Phase 7 Plan 16: HTTP Auth Hook + Auth-Derived Principal (D-IMPL-21 ref impl #1) Summary

Optional Protocol-based bearer-auth hook on the HTTP front door reusing the D-26 constant-time TokenSourceProtocol machinery, plus principal_from_token_grant binding the approver's subject_id to the verified TokenGrant.client_id — no caller-typed subject exists — with the unbound default preserving the recorded T-07-24 posture exactly.

## Tasks

| Task | Name | Commit(s) | Files |
| ---- | ---- | --------- | ----- |
| 1 | Auth-context-derived principal (TDD) | b12aba0 (RED), bb7388e (GREEN) | runtime/ccf_runtime/identity_binding.py, tests/http_api/test_auth.py |
| 2 | Minimal HTTP auth hook, optional at create_app (TDD) | 4504864 (RED), e81b234 (GREEN) | runtime/ccf_runtime/http_api/auth.py, runtime/ccf_runtime/http_api/app.py, tests/http_api/test_auth.py |
| 3 | Full-suite regression sweep | 823ab06 (mypy annotation fix only) | runtime/ccf_runtime/http_api/app.py |

## What Was Built

- `principal_from_token_grant(*, grant, identity_provider_ref, method, assurance_level, session_ref, action_time, product_content_hash)` — constructs `ApproverIdentity(subject_id=grant.client_id, ...)`; the function has no `subject_id` parameter (asserted by an `inspect.signature` test and grep gate: `subject_id=grant.client_id` appears exactly once). No defaults for any deployment vocabulary (CINV-01). Contract validators surface unlaundered.
- `HttpAuthProtocol` (runtime_checkable Protocol: `grant_for_request(*, authorization_header) -> TokenGrant | None`) and `BearerTokenAuth` — parses `Authorization: Bearer <token>` (scheme case-insensitive per RFC 9110; missing header/other scheme/empty credential -> None) and delegates to the deployment's `TokenSourceProtocol.grant_for` — D-26 constant-time path reused, no new comparison code.
- `create_app(deps, *, auth=None)` — when `auth` is bound, all eight routers (`/agent /skill /workflow /hitl /replay /artifact /product /config`) carry a dependency raising `HTTPException(401)` on unrecognised credentials and stashing the grant on `request.state.token_grant`; `/health` exempt. When `auth is None`, nothing is registered — posture unchanged, `AUTH_POSTURE_SENTENCE` byte-identical and its test unmodified.

## Verification

- `pytest tests/http_api -q` — 44 passed (10 new in test_auth.py).
- Full suite: **1307 passed, 0 failed, 0 skipped** (baseline 1297 + 10 new).
- `mypy --strict src runtime tools` — Success: no issues found in 167 source files.
- `tools.lints --all` — exit 0.
- Grep gates: `class BearerTokenAuth` = 1; `from ccf_runtime.mcp.auth import` in http_api/auth.py = 1; no literal bearer token values in modified files (gate returned 0).

## Deviations from Plan

**1. [Rule 1 - Bug] Naive-datetime test catches `CanonicalizationError`, not `ValueError`**
- **Found during:** Task 1
- **Issue:** `ccf.contracts.canonical.CanonicalizationError` subclasses `TypeError`; the test's `(ValidationError, ValueError)` tuple missed it.
- **Fix:** Test catches `(ValidationError, CanonicalizationError)` — the module's own exception, still unlaundered by the derivation function.
- **Files modified:** tests/http_api/test_auth.py
- **Commit:** bb7388e

**2. [Rule 3 - Blocking] mypy --strict rejects `list[Depends]` annotation**
- **Found during:** Task 3
- **Issue:** `fastapi.Depends` is a function, not a type; `list[Depends]` fails valid-type under --strict.
- **Fix:** Annotate as `list[params.Depends]` (the class the function returns).
- **Files modified:** runtime/ccf_runtime/http_api/app.py
- **Commit:** 823ab06

## Threat Model Dispositions

| Threat | Disposition | Evidence |
|--------|-------------|----------|
| T-07.1-04 Spoofing (HTTP authority routes) | mitigated | 401 tests for missing/unrecognised/non-Bearer credentials; posture-preserved test for unbound default |
| T-07.1-05 Spoofing (principal subject_id) | mitigated | subject_id bound to verified client_id; signature test proves no caller parameter |
| T-07.1-06 Info disclosure (token comparison) | mitigated | delegation to D-26 `FileTokenSource.grant_for` (hmac.compare_digest); grep gate confirms single import, no new comparison |
| T-07.1-07 Elevation (/health under auth) | accepted | /health exempt by design; test E asserts reachability without a token |

## TDD Gate Compliance

Both implementation tasks followed RED → GREEN with committed failing tests (b12aba0, 4504864) preceding implementations (bb7388e, e81b234).

## Self-Check: PASSED

- runtime/ccf_runtime/identity_binding.py — FOUND
- runtime/ccf_runtime/http_api/auth.py — FOUND
- tests/http_api/test_auth.py — FOUND
- Commits b12aba0, bb7388e, 4504864, e81b234, 823ab06 — FOUND in log
