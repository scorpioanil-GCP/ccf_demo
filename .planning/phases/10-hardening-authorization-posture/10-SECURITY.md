---
phase: 10
slug: hardening-authorization-posture
status: verified
threats_open: 0
asvs_level: 1
created: 2026-08-01
---

# Phase 10 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| HTTP/MCP caller → door | Untrusted bearer-token holder requesting tenant-scoped HITL actions | Bearer token, tenant claim, HITL submissions |
| Deployment config → Control Plane | Scope-mapping artifact content validated at registration | ScopeMappingArtifact (deployment vocabulary) |
| Caller → primitive resolve surface | Authority-bearing human action; principal cryptographically bound when policy requires | SignedPrincipalBinding, approver identity |
| Primitive → transport | Intentionally re-verified (defense in depth); no trust marker crosses | Submissions, pending events |
| Operator → create_app configuration | Insecure deployment posture must be loud, never silent | auth=None default, acknowledgment kwarg |
| Example artifacts → Control Plane | Deployment values enter via validated YAML artifacts only | Scope mappings, HITL policies |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-10-01 | Elevation | ControlPlaneTenantAuthorizer.authorize | mitigate | Deny-by-default: `matched` starts `None`, `ControlPlaneMissing` → deny, near-miss artifact audited-then-raised, `allowed=matched is not None` — `runtime/ccf_runtime/authz/protocol.py:137-188`; matrix tests `tests/authz/test_tenant_authorizer.py` | closed |
| T-10-02 | Tampering (TOCTOU) | scope-mapping resolution | mitigate | Per-call `self._control_plane.resolve_latest(...)` inside `authorize()`; exact `version` carried into audit event — `protocol.py:141-143,160,197` | closed |
| T-10-03 | Repudiation | authz decisions | mitigate | Allow AND deny both append `action="authz_decision"` to Control Plane `audit_log` (`protocol.py:157-167` deny-on-near-miss, `:194-204` every decision); `src/ccf/controlplane/audit.py:147` registers the action | closed |
| T-10-04 | Info disclosure | refusal bodies | mitigate | `refusal_detail` emits `{"error_code", "message"}` only — `runtime/ccf_runtime/http_api/errors.py:64`; `ERROR_TENANT_UNAUTHORIZED:61`; refusal prose names action/tenant, never scope strings or tokens (`routes/hitl.py:127-128`) | closed |
| T-10-05 | Tampering (replay drift) | AuditEvent contract | mitigate | A2 sha256 byte-pin written before the change — `tests/authz/test_authz_audit.py:35` (`A2_PINNED_SHA256`), asserted at `:57-58` | closed |
| T-10-06 | Spoofing/Repudiation | four HITL resolve surfaces | mitigate | `signed_binding_required(...)` + `enforce_signed_binding(...)` at all four: `approval_gate.py:329-339`, `review_queue.py:397-403`, `override.py:331-337`, `escalation.py:450-456` | closed |
| T-10-07 | Elevation (forged marker) | primitive/transport seam | mitigate | No trust marker exists — `transport.py:208` documents refusal of "verified-marker plumbing"; both layers verify independently; idempotency asserted `tests/hitl/test_signed_binding_authority.py:441` | closed |
| T-10-08 | Tampering (event destruction on refusal) | queue consumption ordering | mitigate | `enforce_signed_binding` raises BEFORE `transport.remove(...)` claim (`approval_gate.py:329-340` vs `:341`); failed submit re-enqueues claimed event (`:353-360`, Pitfall 4) | closed |
| T-10-09 | DoS (JWS under lock) | verification path | mitigate | JWS verification lives in primitives outside the transport `threading.Lock`; `transport.py:433-441` discharges D-IMPL-69's "verification stays outside any transport lock"; `tests/hitl/test_transport_concurrency.py` | closed |
| T-10-10 | Elevation (cross-tenant) | both door handlers | mitigate | `_enforce_tenant_authz` → `authorizer.authorize(...)` before transport on all 4 surfaces: HTTP `routes/hitl.py:140,156`; MCP `hitl_server.py:312,379` | closed |
| T-10-11 | Spoofing (tenant claim) | tenant parsing | mitigate | Tenant taken from parsed route/body surface (`routes/hitl.py:139-142` query, `:156-158` submission.tenant) and matched against grant scope patterns (`protocol.py:176-186`); never trusted as authorization | closed |
| T-10-12 | Repudiation | door decisions | mitigate | Doors delegate to authorizer, which audits both outcomes itself (`protocol.py:194-204`; `hitl_server.py:275` "authorizer audits both outcomes") | closed |
| T-10-13 | Tampering (blanket-Depends bypass) | router wiring | mitigate | Enforcement is in-handler with parsed tenant, not a blanket router `Depends` — `routes/hitl.py:105-145`; call sites grep-asserted in both handlers | closed |
| T-10-14 | Info disclosure | refusal bodies | mitigate | Same `refusal_detail` code+message discipline as T-10-04; MCP door renders same `ERROR_TENANT_UNAUTHORIZED` constant (`authz/refusals.py` docstring; `errors.py:61`) | closed |
| T-10-15 | Info disclosure (silent insecure deploy) | create_app | mitigate | `CcfInsecureDefaultWarning` class (`app.py:68`), emitted when `auth is None and not acknowledge_insecure_default` (`app.py:210-214`); kwarg-only acknowledgment (`app.py:155`), no env var | closed |
| T-10-16 | Repudiation (suppressed warning) | test config | mitigate | No `filterwarnings` anywhere in pyproject/pytest config/tests (grep-verified empty); `-W error::CcfInsecureDefaultWarning` sweep recorded green (10-04-SUMMARY:87); `tests/http_api/test_insecure_default_warning.py` present | closed |
| T-10-17 | Tampering (manifest drift) | hash manifest | mitigate | `10-examples-hash-manifest.txt` header cites D-16, states only 05/06 lines regenerated, other lines copied verbatim from Phase 9 manifest | closed |
| T-10-18 | Elevation (insecure example) | examples 05/06 | mitigate | Both examples bind `auth=BearerTokenAuth(...)` and `authorizer=ControlPlaneTenantAuthorizer(...)` (`05/run.py:436,442`; `06/run.py:791,797`); live 403 refusal asserted (`05/run.py:465,531`) | closed |
| T-10-SC | Tampering (supply chain) | package installs | accept | No packages installed this phase; audit table empty by construction | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| R-10-01 | T-10-SC (x4, one per plan 10-01..10-04) | No package installations occurred in Phase 10; supply-chain surface unchanged by construction (per each plan's RESEARCH) | Plan-time disposition (register authored at plan time) | 2026-08-01 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-01 | 19 | 19 | 0 | gsd-security-auditor |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-01
