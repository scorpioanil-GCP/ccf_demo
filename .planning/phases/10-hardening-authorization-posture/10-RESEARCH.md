# Phase 10: Hardening — Authorization & Posture - Research

**Researched:** 2026-08-01
**Domain:** In-repo hardening — per-tenant authorization at the HITL doors, HitlPolicy verification on primitive resolve surfaces, insecure-default warning
**Confidence:** HIGH (all findings verified by direct codebase reading; no external dependencies)

## Summary

This phase is pure in-repo mechanism work implementing three fully-ruled decisions (D-IMPL-68/69/73) against code surfaces that already exist and follow established patterns. There are no new external packages, no new frameworks, and no ecosystem research required — every load-bearing pattern (auth-hook binding, typed-refusal constants, Control Plane artifact classes with semver lanes, per-request policy re-resolution, dual-door error rendering) has a working precedent in the codebase, verified in this session by direct file reads.

The three work streams: (1) a new `ScopeMappingArtifact` (Control Plane policy artifact, D-03) plus a `TenantAuthorizerProtocol` and shared reference interpreter in `runtime/ccf_runtime/authz/`, enforced at the HTTP door (`create_app` dependency chain) and the MCP HITL door (`build_hitl_server` tool/resource handlers), deny-by-default with a typed 403 through a shared refusal-constants module, with every allow/deny decision audited; (2) HitlPolicy signed-binding verification replicated onto the four HITL primitives' resolution surfaces (`ApprovalGate.resolve`, `OverrideBoundary.resolve`, `ReviewQueue.release`, `ExceptionEscalation.resolve`), reusing the transport's `_signed_binding_required`/`_enforce_signed_binding` pattern and the existing refusal exception types; (3) `CcfInsecureDefaultWarning` + first-request logging WARNING in `create_app`, suppressed only by an explicit acknowledgment kwarg, with examples 05/06 extended in place and the Phase-9 hash manifest deliberately re-baselined for those two examples.

**Primary recommendation:** Plan this as three largely independent task groups (authz door enforcement, primitive-resolve verification, warning + examples), each mirroring an identified in-repo precedent file exactly, with the cross-door × cross-action test matrix as the phase gate for HARD-04.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Scope-mapping artifact schema (HARD-04, sub-ruling D-IMPL-68 delegated to this phase)
- **D-01:** Tenant-pattern grammar is **exact match + trailing wildcard only**
  (`tenant-a`, `tenant-*` prefix glob). No regex, no mid-string globs.
  Deterministic and greppable; misconfiguration surface minimized.
- **D-02:** Action vocabulary comes from **door-declared action IDs** — each
  HTTP route / MCP tool declares its action identifier; the artifact's
  action-sets are matched against those strings. The SDK ships matching
  mechanism only and invents no scope vocabulary (HARD-04).
- **D-03:** The artifact is a **new dedicated typed class** (e.g.
  `ScopeMappingArtifact`), Pydantic `extra=forbid`, following the existing
  D-IMPL-28 definition-artifact pattern, registered and versioned like other
  Control Plane policy bundles. Not folded into HitlPolicy.
- **D-04:** Versioning uses the **same semver-lane pattern** as other Control
  Plane bundles; the audit record captures the exact artifact version string
  in force at decision time (allow or deny), per the D-IMPL-68 ruling text.

#### Authorizer seam & placement (HARD-04)
- **D-05:** `TenantAuthorizerProtocol` and the shared reference interpreter
  both live in **runtime** (e.g. `runtime/ccf_runtime/authz/`), imported by
  both doors. `/src` core untouched — mirrors the D-IMPL-67 auth-hook seam.
- **D-06:** Doors take an **optional authorizer binding** with the same shape
  as the D-IMPL-67 auth hook. Auth bound + authorizer bound → enforce;
  authorizer unbound → the T-07-24 unauthenticated posture is unchanged
  (D-IMPL-68: "governs behavior only when auth is bound").
- **D-07:** The helper **re-resolves the scope-mapping artifact from the
  Control Plane per request** (no cache/TTL) — version changes take effect
  immediately and the exact version lands in the audit record. Matches the
  transport's per-submission HitlPolicy re-resolution posture.
- **D-08:** Refusals share **one refusal-constants module** consumed by both
  doors: the HTTP door renders the typed 403 JSON (errors.py constants
  pattern), the MCP door renders its protocol-native error carrying the same
  code/detail. One vocabulary, two renderings.

#### Audit record shape (HARD-04)
- **D-09:** The authorization decision record carries the **full decision
  tuple**: principal/subject, tenant, action, decision (allow/deny), matched
  scope pattern (or none), artifact version, timestamp.
- **D-10:** **Both allows and denials are audited** — refusals are
  security-relevant events (audit-by-construction, CLAUDE.md §8.2).
- **D-11:** Authz decisions **extend the existing HITL audit path**
  (Decision Replay dimensions 2/4 extensions) — the authz record attaches to
  the HITL action it gated. No new replay dimension, no separate log surface.

#### Gate verification surfaces (HARD-05, D-IMPL-69)
- **D-12:** Verification lands on **all human-action surfaces**:
  `ApprovalGate.resolve`, OverrideBoundary's override entry, ReviewQueue's
  release/decision path, ExceptionEscalation's human handoff. Close the
  class, not just the audited instance.
- **D-13:** **Both layers verify, idempotently** — transport `submit` and
  primitive resolve each verify independently (defense in depth; read-only
  check). No verified-marker plumbing between layers (a forgeable marker is
  a bypass vector).
- **D-14:** Primitives **reuse the existing refusal types**
  (`SignedBindingRequiredRefused` / `SignedBindingInvalidRefused`) per the
  D-IMPL-69 ruling text — no new subclasses.

#### create_app warning + examples (HARD-05)
- **D-15:** D-IMPL-73 is fully ruled — implement exactly:
  `CcfInsecureDefaultWarning` (warnings.warn) + logging WARNING record, with
  an explicit acknowledgment kwarg as the single suppression surface. No
  environment variable.
- **D-16:** **Examples 05 and 06 are extended in place** with scope-mapping
  artifacts + authorizer binding, demonstrating one authorized and one
  refused path; READMEs updated. The D-14 (Phase 9) byte-identity manifest is
  deliberately re-baselined for these two examples only — a conscious,
  documented regeneration, not drift.

### Claude's Discretion
- Exact module/file names inside `runtime/ccf_runtime/authz/`, the artifact
  class name, and the kwarg name for the D-IMPL-73 acknowledgment — follow
  house naming conventions.
- Cross-door × cross-action test-matrix mechanics (parametrization shape),
  provided the matrix covers both doors × all door actions × allow/deny.
- TokenGrant scope-string format interpretation, consistent with D-IMPL-68's
  "tenant × action grammar never hardcoded" constraint.

### Deferred Ideas (OUT OF SCOPE)
- Free-threaded-Python variant of the concurrency hammer (Phase 9 review
  carry-forward — advisory tech-debt, not Phase 10 scope).
- Typed-error compatibility note and Protocol thread-safety obligation for
  adopter docs — Phase 14 (from Phase 9 cross-AI review consensus).
- Per-call executor overhead in `run_coroutine_sync` — revisit with Phase 11
  measured data.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HARD-04 | HITL doors enforce per-tenant authorization per D-IMPL-68 — deny-by-default, typed 403, authz decision in the audit record, cross-door × cross-action test matrix | §"Door enforcement points" — exact locations where identity is verified today at both doors; §"Control Plane artifact pattern" — how `ScopeMappingArtifact` registers/versions/resolves; §"Audit path" — `AuditLog`/`AuditEvent` shape and the extension question; §"Refusal constants" — the errors.py pattern and the MCP dual rendering precedent |
| HARD-05 | ApprovalGate.resolve × signed_binding_required composed per D-IMPL-69; create_app insecure-default warning per D-IMPL-73 | §"Primitive resolution surfaces" — the four resolve entry points and their exact signatures; §"Transport verification pattern to replicate" — `_signed_binding_required`/`_enforce_signed_binding` verbatim mechanics; §"create_app anatomy" — where the warning and kwarg land; §"Examples 05/06" — auth wiring and hash-manifest re-baseline mechanics |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **No-Hardcoding Rule (§6.4):** no inline prompts, no policy values in code. Note: D-IMPL-73 ruling explicitly states the warning text is *mechanism*, so inline warning prose is legitimate. The scope-mapping *content* (which scopes map to which tenants/actions) is deployment data in artifacts; the SDK ships only the grammar interpreter (D-01/D-02).
- **Harness neutrality:** zero harness imports in `/src`; this phase touches no harness surface.
- **Typed contracts:** Pydantic `extra=forbid` at every boundary (`CCFContract` base).
- **Mechanism, not values (§11 / CINV-01):** no scope vocabulary, tenant names, or token values in SDK code; examples carry values in YAML artifacts.
- **Audit-by-construction (§8.2):** no path through the HITL surface producing an unrecorded human action — extends here to authz decisions (D-10).
- **Every module carries `__ccf_mode__ = "algorithmic"`** and cites its ruling/section in the docstring — every file read in this session follows this; new modules in `runtime/ccf_runtime/authz/` must too.
- **Whitepaper fidelity:** all Phase-10 surfaces are SDK-defined extensions (§8.2/§8.3); docstrings must cite CLAUDE.md sections and D-IMPL numbers, not the whitepaper.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Scope-mapping artifact class + registration | `/src` Control Plane (`ccf.controlplane` pattern) or runtime — see Open Q1 | Control Plane registry | Typed artifact classes live beside `HitlPolicy`; but D-05 says `/src` core untouched — the class likely lives in `runtime/ccf_runtime/authz/` |
| Authorization interpretation (grammar matching) | `runtime/ccf_runtime/authz/` | — | D-05 locked: Protocol + reference interpreter in runtime, mirroring the D-IMPL-67 auth-hook seam |
| Enforcement | HTTP door (`http_api/app.py` + routes) and MCP HITL door (`mcp/hitl_server.py`) | — | D-IMPL-68: doors are where identity is verified (D-IMPL-67); transport stays a pure queue |
| Authz audit record | Existing HITL audit path (`ccf.controlplane.audit.AuditLog`) | — | D-11: no new log surface; extends dimensions 2/4 |
| Signed-binding verification on resolve | `/src/ccf/hitl/` primitives | Control Plane (policy read) | D-IMPL-69: verification at the authority-bearing call; primitives gain optional CP read dependency |
| Insecure-default warning | `runtime/ccf_runtime/http_api/app.py` | — | D-IMPL-73 target is `create_app`; log record at first request |
| Demonstration | `examples/05-workflow-hitl`, `examples/06-decision-replay` | — | D-16: extended in place, manifest re-baselined |

## Standard Stack

No new dependencies. Everything needed is already in the tree and already imported by the files this phase touches [VERIFIED: codebase read, this session]:

| Library | Purpose in this phase | Already used by |
|---------|----------------------|-----------------|
| Pydantic (`CCFContract`, `extra=forbid`) | `ScopeMappingArtifact`, decision-tuple contract | every contract in `src/ccf/contracts/` |
| FastAPI (`Depends`, `HTTPException`, `Request`) | HTTP-door authorizer dependency, 403 rendering | `http_api/app.py`, `routes/hitl.py` |
| `mcp.server.fastmcp` / `get_access_token` | MCP-door grant access inside tool/resource handlers | `mcp/hitl_server.py` |
| stdlib `warnings` + `logging` | D-IMPL-73 dual emission | — (new usage, stdlib) |
| pytest (`pytest.warns`, `pytest.mark.parametrize`) | warning tests, cross-door × cross-action matrix | entire `tests/` tree |

### Alternatives Considered
None applicable — the rulings pin the approach; researching alternatives to locked decisions is out of scope per CONTEXT.md.

## Package Legitimacy Audit

**No external packages are installed by this phase.** All work uses stdlib and dependencies already in the lockfile (Pydantic, FastAPI, MCP SDK, pytest). Audit table empty by construction; slopcheck not required.

## Architecture Patterns

### System Architecture (data flow for an authorized HITL action)

```
Caller (HTTP client or MCP client)
   │ bearer token
   ▼
Door identity verification (existing, D-IMPL-67)
   HTTP: create_app _require_grant → request.state.token_grant : TokenGrant
   MCP:  FastMCP auth middleware → get_access_token() → AccessToken
   │ TokenGrant(client_id, scopes)
   ▼
NEW: Tenant authorization (D-IMPL-68, this phase)
   TenantAuthorizerProtocol.authorize(grant, tenant, action_id)
     → resolves ScopeMappingArtifact from Control Plane PER REQUEST (D-07)
     → matches grant.scopes → (tenant-pattern × action-set) per D-01/D-02 grammar
     → AuthzDecision tuple (D-09) appended to audit log — allow AND deny (D-10)
   ├─ no match → deny-by-default: typed 403 (HTTP) / protocol error (MCP),
   │             shared error-code constant (D-08) ── STOP
   ▼ allow
Existing door logic (subject conflict check, principal derivation)
   │ HitlActionSubmission
   ▼
Transport submit ── HitlPolicy signed-binding verification (existing D-16)
   │
   ▼
Primitive resolve (ApprovalGate / Override / ReviewQueue / Escalation)
   NEW: HitlPolicy signed-binding verification AGAIN, idempotently
        (D-IMPL-69, D-13) — same refusal types (D-14)
   │
   ▼
Audit record + replay dimension 2 (existing)
```

### Pattern 1: The auth-hook seam to mirror (D-05/D-06)

`runtime/ccf_runtime/http_api/auth.py` [VERIFIED: file read] defines `HttpAuthProtocol` (a `@runtime_checkable` Protocol with one keyword-only method returning `TokenGrant | None`) plus a reference implementation (`BearerTokenAuth`). `create_app` takes it as an optional keyword (`auth: HttpAuthProtocol | None = None`); unbound = posture unchanged. The authorizer binding must be the same shape: `TenantAuthorizerProtocol` + reference interpreter in `runtime/ccf_runtime/authz/`, an optional `authorizer=` kwarg on `create_app` and a parameter on `build_hitl_server`.

**Key structural fact:** the HTTP door's auth check is a router-level `Depends(_require_grant)` applied to all routers; but authorization needs the **tenant and action of the specific request**, which are only known inside route handlers (`tenant` query param on `GET /hitl/queue`; `submission.tenant` in the POST body). So enforcement cannot be a blanket router dependency — it is per-route (either an in-handler call or per-route dependency that reads parsed inputs). The planner must decide the wiring; the tenant source per route is:

| Door | Action surface | Tenant source | Suggested door-declared action ID (D-02, Claude's discretion) |
|------|---------------|---------------|--------------------------------------------------|
| HTTP | `GET /hitl/queue` | `tenant` query param | e.g. `hitl.queue.read` |
| HTTP | `POST /hitl/actions` | `submission.tenant` (body) | e.g. `hitl.action.submit` |
| MCP | resource `ccf-hitl-queue://{tenant}` | URI segment | same read ID |
| MCP | tool `submit_hitl_action` | `tenant` param | same submit ID |

Sharing action IDs across doors is what makes the artifact door-agnostic and the cross-door matrix meaningful. Action-ID constants should live beside the refusal constants (one shared module, D-08) — declared by the doors, never by `/src`.

**Scope of enforcement:** D-IMPL-68's surfacing context is HITL specifically ("a verified caller for tenant A can act on tenant B's HITL events"), and CONTEXT.md's Integration Points name "HTTP door routes and MCP server tool handlers" as the sole enforcement points. The success criteria say "any HITL door … any action" — the HITL noun's two actions per door, not the other seven HTTP nouns. Planner should scope the matrix to the HITL surfaces (queue read + action submit, both doors) unless discuss-phase says otherwise — the non-HITL routers mostly have no tenant parameter to authorize against. Flagged as Open Q2.

### Pattern 2: Control Plane artifact pattern to follow (D-03/D-04)

`HitlPolicy` in `src/ccf/hitl/transport.py` [VERIFIED: file read] is the exact precedent:

```python
class HitlPolicy(CCFContract):
    semver: str                      # required, no default — semver lane
    signed_binding_required: bool = False

HITL_POLICY = ArtifactClass(class_id="ccf.hitl-policy", contract=HitlPolicy)
```

Registered via `ControlPlaneRegistry.register_typed`, resolved via `resolve_latest(key)` which returns `(version, artifact)` — the version string is exactly what D-04/D-09 need in the audit record. `ScopeMappingArtifact` follows this shape: `semver` + a mapping of scope-string → (tenant-patterns, action-sets). Grammar validation (D-01: exact or trailing-`*` only) belongs in a Pydantic field validator so a malformed pattern is refused at registration, matching the "registering the wrong thing is a detectable error" doctrine in `src/ccf/controlplane/artifacts.py` [VERIFIED: file read].

**Per-request re-resolution (D-07)** has a direct precedent: `InMemoryHitlTransport._signed_binding_required()` calls `control_plane.resolve_latest(key)` on every submit, with a `TypeError` if the registered artifact is the wrong class. The authorizer helper does the same per request.

### Pattern 3: Dual-door refusal rendering (D-08)

Already demonstrated for the signed-binding refusals [VERIFIED: file read]:
- HTTP (`routes/hitl.py`): `HTTPException(status_code=403, detail=refusal_detail(error_code=ERROR_..., message=...))`
- MCP (`mcp/hitl_server.py`): `raise ValueError(json.dumps(refusal_detail(error_code=ERROR_..., message=...)))` — "the MCP door carries the SAME shared error-code constants as the HTTP door … single source of truth (T-08-07b)".

Today the constants live in `runtime/ccf_runtime/http_api/errors.py` and the MCP module already imports them cross-package. D-08 wants "one refusal-constants module consumed by both doors" — the planner can either (a) add the new constant(s) (e.g. `ERROR_TENANT_UNAUTHORIZED`-shaped) to `errors.py` and keep the existing import direction, or (b) hoist a shared door-neutral module (e.g. under `runtime/ccf_runtime/authz/` or a new `runtime/ccf_runtime/doors/` common module) re-exported from `errors.py` for backward compatibility. Note `errors.py`'s docstring calls the constant values "stable API surface" — do not rename existing values.

### Pattern 4: Transport verification pattern to replicate on primitives (D-12/D-13/D-14)

`InMemoryHitlTransport` [VERIFIED: file read] takes four optional-together constructor kwargs: `control_plane`, `hitl_policy_key`, `identity_provider`, `trusted_keys`. `submit` calls `_signed_binding_required()` (per-call CP resolve; unbound → `False` → pre-composition behavior) then `_enforce_signed_binding(submission)` (raises `SignedBindingRequiredRefused` / `SignedBindingInvalidRefused` / `RuntimeError` on broken wiring; verifies via `verify_principal_binding` and requires verified principal == submission principal).

The four primitives currently have **no** Control Plane dependency [VERIFIED: grep — no `control_plane`/`HitlPolicy` reference in `approval_gate.py`, `override.py`, `review_queue.py`, `escalation.py`]. Each gains the same four optional-together constructor kwargs and calls the same verification before submitting/consuming, on:

| Primitive | Resolution surface (exact) |
|-----------|---------------------------|
| `ApprovalGate` | `resolve()` (`approval_gate.py:212`) |
| `OverrideBoundary` | `resolve()` (`override.py:190`) |
| `ReviewQueue` | `release()` (`review_queue.py:234`) |
| `ExceptionEscalation` | `resolve()` (`escalation.py:305`) |

**Refactor opportunity (planner's call):** the verification pair is currently private to `InMemoryHitlTransport`. Four primitives + one transport needing identical logic argues for extracting a shared module-level helper in `src/ccf/hitl/transport.py` (or a small `src/ccf/hitl/policy_verification.py`) that both consume — avoiding five copies. D-13 forbids only *verified-marker plumbing between layers*, not shared verification code. Ordering inside each resolve: the ruling says verification happens at the authority-bearing call; verify **before** any queue consumption or audit-side effect (a refused resolution must leave the event pending, mirroring "a refused submission never touches the queues").

**Signed binding availability:** `HitlActionSubmission.signed_binding` exists; but primitive `resolve()` signatures take `principal: HumanPrincipalBinding` and build the submission internally — they have no `signed_binding` parameter today [VERIFIED: `approval_gate.py` resolve builds `HitlActionSubmission(...)` without `signed_binding`]. To verify a signed binding at resolve, the resolve signatures need an optional `signed_binding: SignedPrincipalBinding | None = None` parameter passed through to the submission. This is a required (additive, default-None) signature change on all four surfaces — the planner must include it.

### Pattern 5: create_app warning anatomy (D-15)

`create_app` [VERIFIED: file read] currently branches on `auth is not None`. D-IMPL-73 implementation points:
- Export `CcfInsecureDefaultWarning(UserWarning)` from the SDK (natural home: `http_api/app.py` or a small `http_api/warnings.py`; it must be importable for `-W error::…` and `pytest.warns`).
- `warnings.warn(CcfInsecureDefaultWarning(...))` at construction when `auth is None` and acknowledgment kwarg is `False`. Use `stacklevel=2` so the warning points at the caller.
- Logging WARNING **at first request** — implement via FastAPI middleware or a lightweight once-flag dependency; two emission points must stay message-consistent (ruling's accepted consequence). A `logging.getLogger("ccf_runtime.http_api")`-shaped logger; emit once, not per request.
- Acknowledgment kwarg `allow_unauthenticated: bool = False`-shaped (name is Claude's discretion), the **single** suppression surface — no env var.
- Interaction with the authorizer (D-06): authorizer without auth is inert (grant never exists). The warning fires on `auth is None` regardless of authorizer. Keep `AUTH_POSTURE_SENTENCE` byte-identical — it is test-asserted [VERIFIED: app.py docstring].
- MCP door is *not* in D-IMPL-73 scope — `build_hitl_server` already requires verifier+settings (authenticated by construction).

### Pattern 6: Audit record for authz decisions (D-09/D-10/D-11)

The existing audit surface is `ccf.controlplane.audit.AuditLog.append(action, key, version, resolved, occurred_at, actor, artifact_class)` with `AuditAction` a closed Literal list ending in `"hitl_action"` [VERIFIED: file read]. `ApprovalGate` audits via an injected `AuditLog` with `action="hitl_action"`.

**Fit analysis for the D-09 tuple:** `actor`=principal subject, `resolved`=allow/deny, `version`=scope-artifact version, `occurred_at`=timestamp, `key`=could carry tenant or event key — but **`action` (the door-declared action ID) and `matched scope pattern` have no field**. Options for the planner:
1. Add a new `AuditAction` value (e.g. `"authz_decision"`) and additional optional fields on `AuditEvent` (additive, defaulted `None` — non-breaking for a `CCFContract`? Note `CCFContract` is frozen/closed-world; adding optional fields is a schema change to a serialized contract — check replay-record byte-stability tests).
2. Define a dedicated `AuthzDecisionRecord(CCFContract)` (the full D-09 tuple) and log it through the HITL audit path by attaching it to the HITL action's audit/replay block (D-11: "the authz record attaches to the HITL action it gated"), serializing the tuple into an existing free-text-capable slot or as a companion record.

D-11's wording ("extend the existing HITL audit path … no new replay dimension, no separate log surface") permits either; the queue-read action has no HITL action to attach to, so denials on reads still need somewhere to land — this favors option 1 or a hybrid. **This is the single most consequential open design point in the phase** — see Open Q3. Also note: the doors do not currently hold an `AuditLog` handle; `ApiDependencies` has none, but `ControlPlaneRegistry` owns one (`audit_events()` / injected `audit_log`) — the authorizer helper can audit through the Control Plane's log since it already holds the CP handle for artifact resolution, honoring "the Control Plane is the audit plane, singular (WR-07)" [VERIFIED: registry.py docstring].

### Pattern 7: Examples 05/06 and the hash manifest (D-16)

- `examples/05-workflow-hitl/run.py` already binds `create_app(auth=BearerTokenAuth(...))` with a tokens.yaml-driven token source (`scopes: [hitl]` already present in the artifact) and demonstrates a 401 refusal from an expired token [VERIFIED: grep + tokens.yaml read]. Extension: add a scope-mapping artifact YAML, bind the authorizer, demonstrate one allowed and one refused (wrong-tenant or missing-scope) path; possibly add acknowledgment/auth so the D-IMPL-73 warning never fires in `make examples` (ruling: "examples bind `auth=` … so `make examples` stays warning-clean").
- Example 06 has `tokens.yaml` and `hitl.yaml` too; same extension pattern.
- The Phase-9 manifest is `.planning/phases/09-hardening-defect-fixes-ruling-batch/09-examples-hash-manifest.txt` — `sha256sum` lines over each example's `run.py` + artifacts [VERIFIED: file read]. Re-baseline = regenerate the sha256 lines for examples 05/06 files only, in a Phase-10 manifest (or documented update), with an explicit commit note that this is a conscious re-baseline per D-16. No test in `tests/` references the manifest [VERIFIED: grep found no consumer] — it is a documentation-of-record artifact; the re-baseline is a documented regeneration, not a test change.

### Anti-Patterns to Avoid
- **Authorization below the door trust boundary** — the transport stays a pure queue; no scope check in `InMemoryHitlTransport` (D-IMPL-68 ruling text; minicycle Option B rejected).
- **Caching the scope artifact** — D-07 forbids it; per-request resolve like the HitlPolicy precedent.
- **New refusal exception subclasses for signed-binding at resolve** — D-14 forbids; reuse the two existing types.
- **Verified-marker plumbing between transport and primitives** — D-13 forbids (forgeable marker = bypass vector).
- **JWS verification inside any lock** — D-IMPL-69 accepted consequence; the transport already documents this (WR-02); primitives hold no lock today, keep it that way on the verification path.
- **Renaming existing error-code constants** — stable API surface per errors.py docstring.
- **Scope vocabulary in SDK code** — the grammar interpreter ships; scope strings, tenant names, and mappings are artifact data (CINV-01).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Artifact validation/versioning | custom registry | `ControlPlaneRegistry.register_typed` + `ArtifactClass` | semver-lane collision detection (WR-08), audit, typed refusal all exist |
| Refusal body shape | new dict shape | `refusal_detail()` | one shape, both doors, test-asserted |
| Signed-binding verification | new verifier | transport's `verify_principal_binding` path | constant-time / JWS mechanics already ruled and tested (D-16, T-08-06) |
| Warning testability | print/log only | `warnings.warn` with exported category | `pytest.warns` + `-W error::` are the ruled CI hooks |
| Pattern grammar | regex engine | `str.startswith` on `pattern[:-1]` for trailing-`*`, `==` otherwise | D-01 rules out regex; two-branch match is the whole grammar |

## Common Pitfalls

### Pitfall 1: Blanket router dependency can't see tenant/action
Router-level `Depends` (the existing auth pattern) runs before body parsing per-router; the authz decision needs the parsed tenant. Enforce inside the two HITL handlers (or per-route dependencies with access to parsed params). **Warning sign:** an authorizer check that never reads `submission.tenant`.

### Pitfall 2: Auditing denials without an audit handle at the door
Doors currently hold no `AuditLog`. Route authz auditing through the Control Plane handle the authorizer already needs for artifact resolution (WR-07: one audit plane). **Warning sign:** a second, standalone log object constructed in `runtime/`.

### Pitfall 3: Frozen-contract schema drift
`AuditEvent`/replay records are canonically serialized; adding fields can change bytes replay tests pin. Run `tests/replay/` and `tests/invariants/test_replay_by_construction.py` early after any contract touch. **Warning sign:** canonical-bytes test failures in unrelated suites.

### Pitfall 4: Primitive resolve verification ordered after consumption
If verification runs after `_consume`, a refused resolution destroys the pending event. Verify before touching the queue; refused = event stays pending (matches TOCTOU-refusal behavior already in `ApprovalGate.resolve`). **Warning sign:** a refusal path that calls `_consume` or `submit` first.

### Pitfall 5: Double-submission verification breaking transport-fed flows
Primitives submit through the transport, which verifies again (D-13, intentional). The primitive-built submission must carry the `signed_binding` through, or the transport's check will refuse what the primitive accepted. Signature change (optional `signed_binding` param on resolve surfaces) is required — see Pattern 4.

### Pitfall 6: Warning fires in the example/test suite
`make examples` must stay warning-clean; every `create_app` call in examples and tests that omits `auth=` will now warn. Tests that construct bare apps need `pytest.warns` handling or the acknowledgment kwarg. **Warning sign:** `-W error::CcfInsecureDefaultWarning` CI leg failing on existing tests (`tests/http_api/test_routes.py` etc. construct unauth'd apps).

### Pitfall 7: MCP resource handlers and grant access
In the MCP door, the tool handler gets the verified identity via `get_access_token()`; the **resource** handler (`hitl_queue`) currently does no identity work at all [VERIFIED: file read]. Authorizing the queue read there requires the same `get_access_token()` call inside the resource function — verify FastMCP exposes the auth context to resource reads the same way it does for tools (it uses the same middleware contextvar; confirm with a test, not an assumption). [ASSUMED — A1]

## Code Examples

### The whole D-01 grammar (mechanism the SDK ships)
```python
# Source: D-01 locked decision; two-branch match, no regex
def tenant_pattern_matches(pattern: str, tenant: str) -> bool:
    if pattern.endswith("*"):
        return tenant.startswith(pattern[:-1])
    return tenant == pattern
```

### Per-request artifact resolve (mirrors transport._signed_binding_required)
```python
# Source: src/ccf/hitl/transport.py:362-382 pattern [VERIFIED]
version, artifact = control_plane.resolve_latest(scope_mapping_key)
if not isinstance(artifact, ScopeMappingArtifact):
    raise TypeError(...)  # wrong-class registration is broken wiring
# `version` is the exact string D-04/D-09 put in the audit record
```

### Dual-door refusal rendering (existing, to extend)
```python
# HTTP — runtime/ccf_runtime/http_api/routes/hitl.py [VERIFIED]
raise HTTPException(status_code=403,
    detail=refusal_detail(error_code=ERROR_..., message=...))
# MCP — runtime/ccf_runtime/mcp/hitl_server.py [VERIFIED]
raise ValueError(json.dumps(refusal_detail(error_code=ERROR_..., message=...)))
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (repo-standard) |
| Config | repo root (Makefile `test` target) |
| Quick run command | `python -m pytest tests/http_api tests/hitl -q` |
| Full suite command | `make ci-core` (lint + typecheck + `CCF_REQUIRE_HARNESSES=1 pytest -q`); full gate `make ci` (adds examples) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HARD-04 | Cross-door × cross-action allow/deny matrix (HTTP queue/actions × MCP resource/tool × allow/deny) | integration | `pytest tests/http_api/test_tenant_authz.py tests/hitl/... -q` (new files) | ❌ Wave 0 |
| HARD-04 | Deny-by-default when no mapping matches; typed 403 constant asserted | unit | same new files | ❌ Wave 0 |
| HARD-04 | Authz decision tuple (allow AND deny) in audit record with artifact version | unit | new file | ❌ Wave 0 |
| HARD-04 | Authorizer unbound → T-07-24 posture unchanged | regression | `pytest tests/http_api/test_auth.py tests/http_api/test_routes.py -q` | ✅ existing must stay green |
| HARD-05 | Each of four primitives refuses unsigned/invalid binding under `signed_binding_required: true` with existing refusal types; event stays pending | unit | `pytest tests/hitl/test_approval_gate.py tests/hitl/test_override.py tests/hitl/test_review_queue.py tests/hitl/test_escalation.py -q` (extended) | ✅ files exist; cases new |
| HARD-05 | Composed transport+primitive double-verification is idempotent | unit | `pytest tests/hitl/test_signed_binding_authority.py -q` (extend) | ✅ exists |
| HARD-05 | `CcfInsecureDefaultWarning` fires unauth'd, suppressed by kwarg, absent when auth bound; log record at first request | unit | `pytest tests/http_api/ -q` with `pytest.warns` (new file) | ❌ Wave 0 |
| HARD-04/05 | Examples 05/06 run clean end-to-end with authz demonstrated | e2e | `make example-05 example-06` | ✅ targets exist |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/http_api tests/hitl -q`
- **Per wave merge:** `make ci-core`
- **Phase gate:** `make ci` green (includes all eight examples)

### Wave 0 Gaps
- [ ] `tests/http_api/test_tenant_authz.py` (or similar) — HTTP-door matrix legs + audit assertions
- [ ] MCP-door matrix legs (extend `tests/crossproc/` or a new in-process FastMCP test beside the D-16 door tests)
- [ ] `tests/http_api/test_insecure_default_warning.py` — D-IMPL-73
- [ ] Existing bare `create_app(...)` call sites in tests/examples audited for new-warning fallout (Pitfall 6)

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control (this phase) |
|---------------|---------|------------------------------|
| V4 Access Control | yes | Deny-by-default tenant×action authorization at trust boundary; decision audited (this phase's core deliverable) |
| V2 Authentication | yes (existing) | D-IMPL-67 bearer hook / D-26 token verifier — unchanged, precondition for authz |
| V5 Input Validation | yes | Pydantic `extra=forbid` on artifact + submission contracts (existing pattern) |
| V6 Cryptography | yes (existing) | JWS binding verification reused, never re-implemented (D-14) |
| V7 Error/Logging | yes | Typed error codes, no token echo in refusal prose (existing discipline); both allow and deny audited |

### Known Threat Patterns
| Pattern | STRIDE | Mitigation in this phase |
|---------|--------|--------------------------|
| Cross-tenant action (WR-01) | Elevation of privilege | Deny-by-default scope match at both doors |
| Unsigned resolve bypass (audit finding) | Repudiation/Tampering | D-IMPL-69 verification at every resolution surface |
| Forged verification marker | Elevation | Ruled out by D-13 (no marker; both layers verify) |
| Silent insecure deployment | Info disclosure risk | D-IMPL-73 loud, greppable acknowledgment |
| TOCTOU on policy version | Tampering | Per-request re-resolution; exact version audited (D-07) |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | FastMCP's auth contextvar (`get_access_token`) is available inside **resource** handlers, not only tools | Pitfall 7 | MCP queue-read authorization needs a different grant-access mechanism; verify with a spike test in Wave 0 |
| A2 | Adding optional fields to `AuditEvent` (if that path is chosen) does not break canonical-bytes replay pins | Pattern 6 / Pitfall 3 | Choose the companion-record path (Open Q3 option 2) instead |

## Open Questions

1. **Where does `ScopeMappingArtifact` live — `/src` or `runtime`?**
   - What we know: D-05 says `/src` core untouched and the interpreter lives in runtime; D-03 says it follows the D-IMPL-28 artifact pattern (whose classes live in `/src/ccf/controlplane/` and `/src/ccf/hitl/`). `HitlPolicy` lives in `/src` because the transport (in `/src`) reads it; nothing in `/src` will read the scope mapping.
   - Recommendation: put the artifact class in `runtime/ccf_runtime/authz/` beside the interpreter — Control Plane `register_typed` accepts any `ArtifactClass` regardless of module, and D-05's "/src untouched" then holds literally for HARD-04 (HARD-05 does touch `/src/ccf/hitl/` by ruling). Planner should state this placement explicitly.

2. **Matrix scope — HITL surfaces only, or all eight HTTP nouns?**
   - What we know: ruling context and CONTEXT.md integration points name the HITL doors; most other routes carry no tenant parameter.
   - Recommendation: scope enforcement and matrix to the four HITL action surfaces (2 doors × 2 actions × allow/deny minimum); note the generalization path in docstrings.

3. **Audit-record mechanics for the D-09 tuple** (most consequential design point).
   - What we know: `AuditEvent` lacks fields for action-ID and matched-pattern; `AuditAction` is a closed Literal; D-11 forbids a new log surface; queue-read denials have no HITL action to attach to.
   - Options: (a) new `AuditAction "authz_decision"` + additive optional `AuditEvent` fields; (b) a typed `AuthzDecisionRecord` serialized into the existing shape (e.g. tuple canonicalized into `key`/`version`/`artifact_class` semantics is too lossy — likely needs (a)); Recommendation: (a), with replay-pin tests checked first (Assumption A2). If bytes break, escalate — this could be a small D-IMPL if the planner judges the audit contract change to exceed delegated discretion, though D-09–D-11 read as delegating the shape to this phase.

## Sources

### Primary (HIGH confidence — direct file reads this session)
- `runtime/ccf_runtime/http_api/{app,auth,errors,dependencies}.py`, `routes/hitl.py`
- `runtime/ccf_runtime/mcp/{auth,hitl_server}.py`
- `src/ccf/hitl/{transport,approval_gate}.py`; grep of `override.py`, `review_queue.py`, `escalation.py`
- `src/ccf/controlplane/{audit,artifacts,registry}.py` (headers + key sections)
- `docs/DECISIONS.md` D-IMPL-68/69/70/73; `docs/09-ruling-batch-minicycle.md` items 1, 2, 6
- `examples/05-workflow-hitl/` (run.py grep, tokens.yaml), `examples/06-decision-replay/artifacts` listing
- `.planning/phases/09-hardening-defect-fixes-ruling-batch/09-examples-hash-manifest.txt`; `Makefile` test/ci/examples targets

### Secondary / Tertiary
None — no external research was needed; all rulings pin the approach in-repo.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all imports verified in-tree
- Architecture: HIGH — every pattern has a working, read-and-cited precedent file
- Pitfalls: HIGH for 1–6 (verified against code); MEDIUM for 7 (A1 assumption)
- Audit-record extension mechanics: MEDIUM — Open Q3 is a real design fork the planner must resolve

**Research date:** 2026-08-01
**Valid until:** stable — valid until any Phase-10-adjacent code merges
