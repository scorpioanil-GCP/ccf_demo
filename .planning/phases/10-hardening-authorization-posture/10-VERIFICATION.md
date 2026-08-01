---
phase: 10-hardening-authorization-posture
verified: 2026-08-01T00:00:00Z
status: passed
score: 15/15 must-haves verified
overrides_applied: 0
---

# Phase 10: Hardening — Authorization & Posture — Verification Report

**Phase Goal:** Every HITL door refuses unauthorized tenants by default and every audited human action carries the authorization decision — implemented exactly per the Phase 9 rulings (HARD-04, HARD-05; D-IMPL-68/69/73)
**Verified:** 2026-08-01
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (merged roadmap SC + plan must_haves)

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Regex/mid-string-glob tenant pattern refused at registration (D-01) | VERIFIED | `runtime/ccf_runtime/authz/artifact.py` `tenant_pattern_matches` + `ScopeMappingArtifact`; `tests/authz/test_scope_mapping_artifact.py` parametrizes `*tenant`, `te*nt`, `t*n*`, `*a*` as refused — all pass |
| 2 | Reference authorizer denies by default; every allow AND deny audited with exact artifact version (D-09/D-10) | VERIFIED | `runtime/ccf_runtime/authz/protocol.py:94-185` — `ControlPlaneTenantAuthorizer` appends `authz_decision` on both outcomes; `tests/authz/test_authz_audit.py` + `test_tenant_authorizer.py` pass; example 06 asserts `denied[0].version == scope_mapping_version` at runtime |
| 3 | Scope-mapping artifact re-resolved from Control Plane per authorize() call (D-07) | VERIFIED | `protocol.py:138` `self._control_plane.resolve_latest(...)` inside `authorize()` |
| 4 | `authz_decision` AuditAction changes no existing replay canonical bytes (A2) | VERIFIED | Full suite (1439 passed, incl. replay canonical-bytes tests) green; `src/ccf/controlplane/audit.py:146` additive member |
| 5 | All four primitives refuse unsigned/invalid binding at resolution surface; pending event survives refusal (D-12/D-14) | VERIFIED | `enforce_signed_binding`/`signed_binding_required` wired in `approval_gate.py`, `override.py`, `review_queue.py`, `escalation.py` (verification before queue consumption); `tests/hitl/test_signed_binding_authority.py` (586 lines) passes |
| 6 | Idempotent double verification — transport and primitive both verify; valid binding passes both (D-13) | VERIFIED | Shared helpers in `src/ccf/hitl/transport.py` (`SignedBindingRequiredRefused`/`SignedBindingInvalidRefused`, lines 135-149, 255-278) consumed by both layers; idempotency tests in signed-binding suite pass |
| 7 | Primitives with no Control Plane bound behave byte-identically to pre-Phase-10 | VERIFIED | `signed_binding` kwargs default `None`; full `tests/hitl` suite green |
| 8 | Unauthorized principal at any HITL door (HTTP + MCP), any action → typed 403 deny-by-default (ROADMAP SC1) | VERIFIED | `routes/hitl.py:115-127` and `mcp/hitl_server.py:250-297` enforce via `TenantAuthorizerProtocol.authorize`; `tests/http_api/test_tenant_authz.py` + `tests/crossproc/test_mcp_tenant_authz.py` (16 matrix tests) pass |
| 9 | Cross-door × cross-action matrix passes asserting shared `ERROR_TENANT_UNAUTHORIZED` constant on every deny leg (ROADMAP SC1/SC2) | VERIFIED | Constant defined once (`http_api/errors.py:61`), rendered per-door; matrix suites green |
| 10 | Every door authz decision (allow and deny) lands in audit with artifact version | VERIFIED | Authorizer audits both outcomes itself (D-09/D-10); audit assertions in door test suites pass |
| 11 | Authorizer unbound → T-07-24 posture byte-identical; authz stays out of `/src` core behind Protocol (ROADMAP SC2) | VERIFIED | `app.py:80,115-117` inert when `authorizer is None`; `test_auth.py`/`test_routes.py` green; authz code lives in `runtime/ccf_runtime/authz/`, not `/src`; lints (`tools.lints --all`) exit 0 |
| 12 | ApprovalGate.resolve × signed_binding_required composed per Dave's ruling with pinning tests (ROADMAP SC3) | VERIFIED | `approval_gate.py:244-258` + `test_signed_binding_authority.py` pass |
| 13 | `create_app` auth=None without acknowledgment → `CcfInsecureDefaultWarning` at construction + once-only first-request log WARNING; single suppression kwarg; auth bound → no warning (D-15, ROADMAP SC4) | VERIFIED | `app.py:63-175` (`acknowledge_insecure_default` kwarg, per-app first-request flag); `tests/http_api/test_insecure_default_warning.py` passes |
| 14 | `make ci` green: bare create_app call sites swept; examples warning-clean | VERIFIED | Full pytest 1439 passed / 2 skipped; lints exit 0; examples 05/06 run end-to-end exit 0 |
| 15 | Examples 05/06 demonstrate one authorized and one refused tenant path via scope-mapping artifacts + authorizer binding; manifest re-baselined for 05/06 only with D-16 note (D-16, ROADMAP SC4) | VERIFIED | Both examples executed live: printed `authz allowed (200)` and `authz refused (403) ... tenant-unauthorized`; `10-examples-hash-manifest.txt` header names D-16, `sha256sum -c` OK for all 05/06 lines; scope values in `artifacts/scope_mapping.yaml` (CINV-01) |

**Score:** 15/15 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `runtime/ccf_runtime/authz/artifact.py` | ScopeMappingArtifact + SCOPE_MAPPING + tenant_pattern_matches | VERIFIED | 118 lines, all three present |
| `runtime/ccf_runtime/authz/protocol.py` | Protocol + reference authorizer + AuthzDecision | VERIFIED | 185 lines, all present |
| `runtime/ccf_runtime/authz/refusals.py` | Shared action-ID constants | VERIFIED | 38 lines |
| `src/ccf/controlplane/audit.py` | `authz_decision` AuditAction + authz fields | VERIFIED | Present, additive |
| `src/ccf/hitl/transport.py` | Shared verification helpers | VERIFIED | Refusal classes + enforce/required helpers |
| `src/ccf/hitl/{approval_gate,override,review_queue,escalation}.py` | signed_binding parameter + resolution-surface verification | VERIFIED | All four wired |
| `runtime/ccf_runtime/http_api/app.py` | authorizer kwarg + CcfInsecureDefaultWarning | VERIFIED | Both present, threaded to HITL router (line 223) |
| `runtime/ccf_runtime/http_api/routes/hitl.py` | Per-route tenant authz | VERIFIED | Handler-level enforcement |
| `runtime/ccf_runtime/mcp/hitl_server.py` | Authz in resource + tool handlers, dual-rendered refusal | VERIFIED | Shared constant rendered per-door |
| Test suites (authz, signed-binding, HTTP/MCP matrix, warning) | Behavior pinned | VERIFIED | 203 targeted tests pass |
| `examples/05,06 run.py + scope_mapping.yaml + README` | Tenant authz demonstration | VERIFIED | Run end-to-end, exit 0 |
| `10-examples-hash-manifest.txt` | Documented 05/06 re-baseline | VERIFIED | D-16 named; hashes verify |

### Key Link Verification

| From | To | Via | Status |
| --- | --- | --- | --- |
| authz/protocol.py | ControlPlaneRegistry.resolve_latest | per-request resolution | WIRED (line 138) |
| authz/protocol.py | controlplane/audit.py | `action="authz_decision"` | WIRED (line 175) |
| hitl primitives | hitl/transport.py | shared refusal types + helpers | WIRED (all four) |
| routes/hitl.py | authz/protocol.py | `authorize` inside handlers | WIRED |
| mcp/hitl_server.py | http_api/errors.py | `ERROR_TENANT_UNAUTHORIZED` | WIRED |
| examples/05,06 run.py | authz/protocol.py | `authorizer=ControlPlaneTenantAuthorizer(...)` | WIRED + executed |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Phase test suites | pytest (authz, hitl, matrix, warning, regression) | 203 passed | PASS |
| Full suite regression | `python -m pytest -q` | 1439 passed, 2 skipped | PASS |
| CI lints (No-Hardcoding, harness-import, @algorithmic) | `python -m tools.lints --all` | exit 0 | PASS |
| Example 05 end-to-end | `python examples/05-workflow-hitl/run.py` | allowed 200 + refused 403 printed, exit 0 | PASS |
| Example 06 end-to-end | `python examples/06-decision-replay/run.py` | allowed 200 + refused 403, byte-equal reproduction, exit 0 | PASS |
| Manifest integrity | `sha256sum -c` (05/06 lines) | all OK | PASS |

### Requirements Coverage

| Requirement | Source Plans | Status | Evidence |
| --- | --- | --- | --- |
| HARD-04 | 10-01, 10-03, 10-04 | SATISFIED | Deny-by-default typed 403, audited decisions with artifact version, cross-door × cross-action matrix green |
| HARD-05 | 10-02, 10-04 | SATISFIED | Both halves: signed-binding composition on all four primitives (10-02, merged) AND create_app loud warning (10-04, merged) |

No orphaned requirements: REQUIREMENTS.md maps only HARD-04/HARD-05 to Phase 10; both are claimed by plans. REQUIREMENTS.md checkboxes/status column remain "Pending" — deliberately left untouched per orchestration note; informational only, an orchestrator-level bookkeeping update remains for milestone close.

### Anti-Patterns Found

None. No TBD/FIXME/XXX/TODO/HACK markers in phase-modified files (only benign "working implementation, not a placeholder" docstring phrases). Lints exit 0.

### Advisory Context (from 10-REVIEW.md, not re-verified)

The code review's 1 Critical + 6 Warnings (AuditLog.append thread-safety under threadpool, unsynchronized HITL side-band dicts, D-01 grammar accepting bare `*`, etc.) remain advisory findings for triage per §3.1 — none contradicts a phase must-have, and all must-have tests pass.

### Gaps Summary

None. All 15 merged must-haves (4 roadmap success criteria + plan-level truths) verified against the codebase with live test and example execution.

---

_Verified: 2026-08-01_
_Verifier: Claude (gsd-verifier)_
