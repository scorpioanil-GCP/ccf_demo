---
phase: 10
slug: hardening-authorization-posture
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-01
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (repo-standard) |
| **Config file** | repo root (Makefile `test` target) |
| **Quick run command** | `python -m pytest tests/http_api tests/hitl -q` |
| **Full suite command** | `make ci-core` (lint + typecheck + `CCF_REQUIRE_HARNESSES=1 pytest -q`); full gate `make ci` (adds examples) |
| **Estimated runtime** | quick ~20s; ci-core ~2 min; full ci ~4 min |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/http_api tests/hitl -q`
- **After every plan wave:** Run `make ci-core`
- **Before `/gsd:verify-work`:** `make ci` must be green (includes all eight examples)
- **Max feedback latency:** ~120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (filled by planner) | — | — | HARD-04 | deny-by-default | Cross-door × cross-action allow/deny matrix (HTTP × MCP × allow/deny) | integration | `pytest tests/http_api/test_tenant_authz.py -q` + MCP legs | ❌ W0 | ⬜ pending |
| (filled by planner) | — | — | HARD-04 | typed 403 | No mapping match ⇒ typed 403 constant asserted | unit | same new files | ❌ W0 | ⬜ pending |
| (filled by planner) | — | — | HARD-04 | audit | Authz decision tuple (allow AND deny) in audit record with artifact version | unit | new file | ❌ W0 | ⬜ pending |
| (filled by planner) | — | — | HARD-04 | posture | Authorizer unbound → T-07-24 posture unchanged | regression | `pytest tests/http_api/test_auth.py tests/http_api/test_routes.py -q` | ✅ | ⬜ pending |
| (filled by planner) | — | — | HARD-05 | D-16 refusals | Four primitives refuse unsigned/invalid binding; event stays pending | unit | `pytest tests/hitl/test_approval_gate.py tests/hitl/test_override.py tests/hitl/test_review_queue.py tests/hitl/test_escalation.py -q` | ✅ (cases new) | ⬜ pending |
| (filled by planner) | — | — | HARD-05 | idempotency | Transport+primitive double-verification idempotent | unit | `pytest tests/hitl/test_signed_binding_authority.py -q` | ✅ | ⬜ pending |
| (filled by planner) | — | — | HARD-05 | warning | `CcfInsecureDefaultWarning` fires / kwarg-suppressed / absent when auth bound | unit | `pytest tests/http_api/test_insecure_default_warning.py -q` | ❌ W0 | ⬜ pending |
| (filled by planner) | — | — | HARD-04/05 | e2e | Examples 05/06 demonstrate authorized + refused paths | e2e | `make example-05 example-06` | ✅ targets | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/http_api/test_tenant_authz.py` — HTTP-door matrix legs + audit assertions
- [ ] MCP-door matrix legs — extend `tests/crossproc/` or new in-process FastMCP test beside the D-16 door tests
- [ ] `tests/http_api/test_insecure_default_warning.py` — D-IMPL-73 warning behavior
- [ ] Audit of existing bare `create_app(...)` call sites in tests/examples for new-warning fallout (RESEARCH Pitfall 6)

---

## Manual-Only Verifications

All phase behaviors have automated verification. (Examples 05/06 READMEs are reviewed at code-review, not manually executed beyond `make example-*`.)

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
