# Phase 10: Hardening — Authorization & Posture - Pattern Map

**Mapped:** 2026-08-01
**Files analyzed:** 13 new/modified files
**Analogs found:** 12 / 13 (the D-IMPL-73 warning has no in-repo analog; stdlib pattern given)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `runtime/ccf_runtime/authz/protocol.py` (new — `TenantAuthorizerProtocol` + reference interpreter; names Claude's discretion) | middleware/service | request-response | `runtime/ccf_runtime/http_api/auth.py` | exact (D-05/D-06 mandate mirroring it) |
| `runtime/ccf_runtime/authz/artifact.py` (new — `ScopeMappingArtifact`) | model (Control Plane artifact) | CRUD (register/resolve) | `HitlPolicy` in `src/ccf/hitl/transport.py:161-193` | exact |
| `runtime/ccf_runtime/authz/refusals.py` (new — shared refusal + action-ID constants, D-08) | config/constants | — | `runtime/ccf_runtime/http_api/errors.py` | exact |
| `runtime/ccf_runtime/http_api/app.py` (modified — authorizer kwarg + D-IMPL-73 warning) | config/factory | request-response | itself (`create_app` auth branch) | exact |
| `runtime/ccf_runtime/http_api/routes/hitl.py` (modified — per-route authz enforcement) | controller | request-response | itself (`act` handler's grant/refusal flow) | exact |
| `runtime/ccf_runtime/mcp/hitl_server.py` (modified — authz in resource + tool) | controller (MCP) | request-response | itself (`submit_hitl_action` refusal flow) | exact |
| `src/ccf/hitl/approval_gate.py` (modified — resolve verification) | service (primitive) | request-response | `InMemoryHitlTransport._signed_binding_required`/`_enforce_signed_binding` (`transport.py:362-426`) | exact |
| `src/ccf/hitl/override.py` (modified — same) | service | request-response | same transport pair | exact |
| `src/ccf/hitl/review_queue.py` (modified — same, on `release()`) | service | request-response | same transport pair | exact |
| `src/ccf/hitl/escalation.py` (modified — same) | service | request-response | same transport pair | exact |
| `tests/http_api/test_tenant_authz.py` (new) + MCP-door matrix tests | test | — | `tests/http_api/test_signed_binding_door.py`, `tests/http_api/test_hitl_door_identity.py` | exact |
| `tests/http_api/test_insecure_default_warning.py` (new) | test | — | `tests/http_api/test_auth.py` (app-construction fixtures) + `pytest.warns` | role-match |
| `examples/05-workflow-hitl/`, `examples/06-decision-replay/` (extended) | config/example | — | example 05's existing `create_app(auth=BearerTokenAuth(...))` wiring (`run.py:405-426`) + `artifacts/tokens.yaml` | exact |

Audit extension (D-09/D-10/D-11) modifies `src/ccf/controlplane/audit.py` — analog is itself; see Shared Patterns.

## Pattern Assignments

### `runtime/ccf_runtime/authz/*` — Protocol + reference interpreter (D-05/D-06)

**Analog:** `runtime/ccf_runtime/http_api/auth.py` (entire file, 74 lines)

**Module header pattern** (lines 1-28) — every new module must reproduce this shape: docstring citing CLAUDE.md section + D-IMPL numbers, "SDK-defined" marker, "Algorithmic module (CINV-03)", then:
```python
from __future__ import annotations
from typing import Protocol, runtime_checkable
__ccf_mode__ = "algorithmic"
__all__ = ["BearerTokenAuth", "HttpAuthProtocol"]
```

**Protocol shape** (lines 31-44) — the authorizer Protocol mirrors this exactly (keyword-only method, `runtime_checkable`, docstring explaining Protocol-over-base-class per CLAUDE.md §11):
```python
@runtime_checkable
class HttpAuthProtocol(Protocol):
    def grant_for_request(
        self, *, authorization_header: str | None
    ) -> TokenGrant | None:
        """Return the request's grant, or ``None`` if it must be refused."""
        ...
```
Authorizer analog signature: `authorize(self, *, grant: TokenGrant, tenant: str, action_id: str) -> AuthzDecision`-shaped.

**Reference impl shape** (lines 47-73): plain class, keyword-only `__init__` taking injected dependencies, "No default: … deployment value (CINV-01)" docstring discipline.

---

### `ScopeMappingArtifact` (D-03/D-04)

**Analog:** `HitlPolicy` + `HITL_POLICY` in `src/ccf/hitl/transport.py` lines 161-193:
```python
class HitlPolicy(CCFContract):
    semver: str
    signed_binding_required: bool = False

    @field_validator("semver")
    @classmethod
    def _semver_is_well_formed(cls, value: str) -> str:
        return validate_semver(value)

HITL_POLICY = ArtifactClass(class_id="ccf.hitl-policy", contract=HitlPolicy)
```
Imports to copy: `from ccf.contracts.base import CCFContract`; `from ccf.controlplane.artifacts import ArtifactClass, validate_semver`; `from pydantic import field_validator`.

Add a `field_validator` on the tenant-pattern fields enforcing D-01 grammar at registration (exact or single trailing `*`; refuse regex/mid-string globs) — mirrors `PendingHitlEvent._event_class_is_a_known_primitive` (transport.py:110-119) for the "malformed refused at the boundary" style. Grammar match itself (from RESEARCH):
```python
def tenant_pattern_matches(pattern: str, tenant: str) -> bool:
    if pattern.endswith("*"):
        return tenant.startswith(pattern[:-1])
    return tenant == pattern
```

**Per-request resolve** (D-07) — copy `InMemoryHitlTransport._signed_binding_required`, transport.py lines 362-382, verbatim mechanics:
```python
if self._control_plane is None or self._hitl_policy_key is None:
    return False
_, artifact = self._control_plane.resolve_latest(self._hitl_policy_key)
if not isinstance(artifact, HitlPolicy):
    raise TypeError(
        f"artifact under {self._hitl_policy_key!r} is not a HitlPolicy"
        " (got {type(artifact).__name__}); ..."
    )
```
For the authorizer, keep the `(version, artifact)` tuple — `version` is exactly what D-04/D-09 put in the audit record.

---

### Refusal-constants module (D-08)

**Analog:** `runtime/ccf_runtime/http_api/errors.py` (entire file, 61 lines):
```python
from typing import Final
#: The request carried no credential the bound auth hook recognises (401).
ERROR_UNAUTHENTICATED: Final[str] = "unauthenticated"

def refusal_detail(*, error_code: str, message: str) -> dict[str, str]:
    return {"error_code": error_code, "message": message}
```
New constant follows the kebab-case value + one-line `#:` comment pattern (e.g. `ERROR_TENANT_UNAUTHORIZED: Final[str] = "tenant-unauthorized"`). **Do not rename existing values** — errors.py docstring declares them "stable API surface." Reuse `refusal_detail()`, never a new dict shape. Door-declared action-ID constants live beside these (D-02/D-08).

---

### `runtime/ccf_runtime/http_api/app.py` — authorizer kwarg + warning (D-06, D-15)

**Analog:** `create_app`'s existing auth branch, `app.py` lines 84-132:
```python
def create_app(
    deps: ApiDependencies, *, auth: HttpAuthProtocol | None = None
) -> FastAPI:
    ...
    guarded: list[params.Depends] = []
    if auth is not None:
        hook = auth
        def _require_grant(request: Request) -> None:
            grant = hook.grant_for_request(
                authorization_header=request.headers.get("Authorization")
            )
            if grant is None:
                raise HTTPException(status_code=401, detail=refusal_detail(
                    error_code=ERROR_UNAUTHENTICATED, message=...))
            request.state.token_grant = grant
        guarded = [Depends(_require_grant)]
```
The authorizer arrives the same way: `authorizer: TenantAuthorizerProtocol | None = None`. **Do not enforce authz as a blanket router dependency** — tenant/action are only known inside the two HITL handlers (RESEARCH Pitfall 1); thread the authorizer into `hitl.build_router(deps, authorizer=...)` or equivalent.

**D-IMPL-73 warning (no analog — stdlib pattern):**
```python
class CcfInsecureDefaultWarning(UserWarning): ...

# in create_app, when auth is None and ack kwarg is False:
warnings.warn(CcfInsecureDefaultWarning(...), stacklevel=2)
```
Plus a once-only `logging.getLogger("ccf_runtime.http_api")` WARNING at first request (middleware or once-flag dependency). Keep `AUTH_POSTURE_SENTENCE` (app.py:59-64) byte-identical — test-asserted. Add a sibling constant-line the way `_AUTH_HOOK_LINE` (app.py:77-81) was added beside, not into, the asserted sentence.

---

### `routes/hitl.py` — HTTP-door enforcement point

**Analog:** the `act` handler's grant-access + typed-refusal flow, `routes/hitl.py` lines 77-146. Copy: grant retrieved via `getattr(request.state, "token_grant", None)`; fail-closed `isinstance(grant, TokenGrant)` check (lines 81-95); typed 403 rendering:
```python
raise HTTPException(
    status_code=403,
    detail=refusal_detail(error_code=ERROR_SUBJECT_CONFLICT, message=...),
)
```
Authz check runs when `grant` is a `TokenGrant` and the authorizer is bound, before the transport submit (a refused request never touches the transport — same discipline as the subject-conflict refusal). Tenant sources: `tenant` query param on `GET /queue` (line 69), `submission.tenant` on `POST /actions`.

---

### `mcp/hitl_server.py` — MCP-door enforcement point

**Analog:** `submit_hitl_action`'s identity + dual-rendering flow, `hitl_server.py` lines 296-369. Grant access (lines 296-309):
```python
token = get_access_token()
if token is None:
    raise UnverifiedCallerRefused(...)
```
Refusal rendering with the SAME shared constants (lines 348-360):
```python
raise ValueError(
    json.dumps(refusal_detail(error_code=ERROR_SIGNED_BINDING_REQUIRED,
                              message=str(error)))
) from error
```
`TokenGrant` reconstruction from the token for the authorizer call (lines 311-312): `TokenGrant(client_id=token.client_id, scopes=tuple(token.scopes))`.

**Caution (RESEARCH A1):** the resource handler `hitl_queue` (lines 243-247) currently does no identity work; verify with a Wave-0 spike test that `get_access_token()` works inside resource handlers before wiring queue-read authz there.

---

### Four HITL primitives — resolve-surface verification (D-12/D-13/D-14)

**Analog:** `InMemoryHitlTransport` D-16 machinery, `src/ccf/hitl/transport.py`:

Constructor pattern — four optional-together kwargs (lines 346-360), to be added to each primitive's existing constructor-injection block (see `ApprovalGate.__init__`, `approval_gate.py:201-210`):
```python
control_plane: ControlPlaneProtocol | None = None,
hitl_policy_key: str | None = None,
identity_provider: IdentityProvider | None = None,
trusted_keys: Mapping[str, JsonWebKey] | None = None,
```

Verification pair to reuse (planner may extract a shared module-level helper — D-13 forbids only marker plumbing, not shared code): `_signed_binding_required` (lines 362-382, quoted above) and `_enforce_signed_binding` (lines 384-426):
```python
if submission.signed_binding is None:
    raise SignedBindingRequiredRefused(
        "the HITL policy in force requires a signed principal binding"
        " and this submission carries none (D-16; D-IMPL-21; CLAUDE.md §8.2)")
if self._identity_provider is None or self._trusted_keys is None:
    raise RuntimeError("... broken composition-root wiring")
try:
    verified = verify_principal_binding(
        submission.signed_binding,
        provider=self._identity_provider,
        public_keys=self._trusted_keys,
    )
except PrincipalBindingInvalid as error:
    raise SignedBindingInvalidRefused(...) from error
if verified != submission.principal:
    raise SignedBindingInvalidRefused(...)
```
Reuse `SignedBindingRequiredRefused` / `SignedBindingInvalidRefused` (transport.py:133-158) — D-14 forbids new subclasses.

**Ordering:** verify before any queue consumption — mirror `ApprovalGate.resolve`'s TOCTOU-before-consume ordering (`approval_gate.py:241-278`: guard runs, refusal returned, event stays pending, refusal audited `resolved=False`). Surfaces gaining verification: `ApprovalGate.resolve` (approval_gate.py:212), `OverrideBoundary.resolve` (override.py:190), `ReviewQueue.release` (review_queue.py:234), `ExceptionEscalation.resolve` (escalation.py:305).

**Required signature change:** resolve surfaces need an additive `signed_binding: SignedPrincipalBinding | None = None` parameter passed through to the internally-built `HitlActionSubmission` (which already has the field, transport.py:217) — otherwise the transport's own check (D-13 double verification) refuses what the primitive accepted (RESEARCH Pitfall 5).

---

### Tests

**Analog:** `tests/http_api/test_signed_binding_door.py` (dual-door refusal + error-code assertions), `tests/http_api/test_hitl_door_identity.py` (grant/identity fixtures), `tests/http_api/test_auth.py` (auth-bound vs unbound app construction), `tests/hitl/test_signed_binding_authority.py` (transport verification cases — extend for idempotent double-verification), and the four `tests/hitl/test_{approval_gate,override,review_queue,escalation}.py` (per-primitive extension). Matrix: `pytest.mark.parametrize` over doors × action IDs × allow/deny (mechanics Claude's discretion per CONTEXT).

**Pitfall 6 sweep:** every bare `create_app(...)` in `tests/http_api/test_routes.py` etc. will now warn — audit call sites for `pytest.warns` handling or the acknowledgment kwarg.

---

### Examples 05/06 (D-16 of CONTEXT)

**Analog:** `examples/05-workflow-hitl/run.py` lines 405-426:
```python
app = create_app(
    ...,
    auth=BearerTokenAuth(
        token_source=ArtifactTokenSource(path=ARTIFACTS / "tokens.yaml")
    ),
)
```
Extend in place: add a scope-mapping YAML under `artifacts/` (values in artifacts, never code — CINV-01), bind `authorizer=`, demonstrate one allowed + one refused path. `tokens.yaml` already carries `scopes:` entries (run.py:168). Re-baseline `sha256sum` lines for these two examples only, against the Phase-9 manifest pattern at `.planning/phases/09-hardening-defect-fixes-ruling-batch/09-examples-hash-manifest.txt` (no test consumes it — documentation-of-record).

## Shared Patterns

### Module header discipline
**Source:** every file read (e.g. `auth.py:1-28`). **Apply to:** all new modules. Docstring: CLAUDE.md §-citation + D-IMPL numbers + "SDK-defined" + "Algorithmic module (CINV-03)"; then `__ccf_mode__ = "algorithmic"` and sorted `__all__`.

### Audit path (D-09/D-10/D-11) — the phase's open design fork
**Source:** `src/ccf/controlplane/audit.py` (entire file). `AuditAction` is a closed `Literal` (lines 95-116) grown additively with a rationale `#:` comment per member — the precedent for adding `"authz_decision"`-shaped member. `AuditEvent` (lines 119-148) has `actor`/`key`/`version`/`resolved`/`occurred_at` but no fields for action-ID or matched-pattern; `AuditEvent` fields are additive-optional (`actor: str | None = None` precedent). **Check replay canonical-bytes pins (`tests/replay/`, `tests/invariants/test_replay_by_construction.py`) immediately after any `AuditEvent` touch** (RESEARCH Pitfall 3 / A2). Doors hold no `AuditLog`; audit through the Control Plane handle the authorizer already holds (WR-07: one audit plane). Both allows and denies recorded — `resolved=True/False` on one member, per the `workflow_resumed`-carries-refusals precedent (audit.py:80-94).

### Dual-door refusal rendering
**Source:** `routes/hitl.py:129-146` (HTTP `HTTPException` 403) + `hitl_server.py:346-369` (MCP `ValueError(json.dumps(...))`). **Apply to:** the new tenant-authz refusal at both doors. One constant, one `refusal_detail` shape, two renderings.

### Optional-together binding kwargs
**Source:** `create_app(auth=None)` branch + `InMemoryHitlTransport.__init__`. **Apply to:** authorizer binding on both doors and CP kwargs on primitives — unbound means byte-identical prior posture (T-07-24 / pre-composition behavior).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `CcfInsecureDefaultWarning` + first-request log record | warning/config | — | No `warnings.warn` usage anywhere in the tree; stdlib pattern given in the app.py assignment above (D-IMPL-73 ruling text is the spec) |

## Metadata

**Analog search scope:** `runtime/ccf_runtime/http_api/`, `runtime/ccf_runtime/mcp/`, `src/ccf/hitl/`, `src/ccf/controlplane/`, `tests/http_api/`, `tests/hitl/`, `examples/05-workflow-hitl/`
**Files scanned:** 9 read in full or targeted section; test/example directories listed
**Pattern extraction date:** 2026-08-01
