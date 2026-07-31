---
phase: 07-phase-i-4-orchestration-hitl-experience
plan: 10
subsystem: experience-layer
tags: [http-api, fastapi, openapi, expr-03, d-impl-22, d-impl-23]
requires: [07-04, 07-06, 07-07, 07-08]
provides:
  - "FastAPI app factory mirroring the full D-IMPL-22/23 ruled noun set"
  - "ApiDependencies named provider bundle (shared with 07-11 CLI --local)"
  - "OpenAPI 3.1.0 document generated from the existing extra=forbid contracts"
affects: [07-11, 07-14]
tech-stack:
  added: []
  patterns:
    - "closure-based build_router(deps) per noun — no module-level singletons"
    - "refusal-vs-exception line over HTTP: typed 4xx bodies vs opaque 5xx"
key-files:
  created:
    - runtime/ccf_runtime/http_api/__init__.py
    - runtime/ccf_runtime/http_api/app.py
    - runtime/ccf_runtime/http_api/dependencies.py
    - runtime/ccf_runtime/http_api/routes/__init__.py
    - runtime/ccf_runtime/http_api/routes/{product,agent,skill,workflow,hitl,replay,artifact,config}.py
    - tests/http_api/{__init__,conftest,test_routes,test_openapi}.py
  modified: []
decisions:
  - "Route walk asserted via app.openapi() paths: FastAPI 0.140 keeps included routers lazy (_IncludedRouter) so app.routes never materializes noun routes"
  - "Emitted OpenAPI version is 3.1.0 (asserted from the document, per research A1)"
  - "AUTH_POSTURE_SENTENCE is a module constant carried verbatim in info.description and string-equality-asserted by test (D-22 honesty; Ollama S4)"
metrics:
  duration: "~50 min"
  completed: "2026-07-30"
---

# Phase 7 Plan 10: HTTP API Skeleton (EXPR-03) Summary

FastAPI 0.140.0 skeleton mirroring the D-IMPL-22/23 ruled noun set verbatim over the SDK's existing extra=forbid contracts, with a frozen `ApiDependencies` provider bundle the CLI's `--local` mode (07-11) constructs identically.

## What was built

- **`ApiDependencies`** (`runtime/ccf_runtime/http_api/dependencies.py`) — frozen, keyword-only bundle of eight injected handles (Control Plane, artifact store, egress product resolver, WorkflowFactory, WorkflowEngine, HITL transport, skill catalog, grant ledger). The named abstraction both front doors share; holds no graph handle, no bind address, no tenant, no default (CINV-01).
- **`create_app(deps)`** (`app.py`) — built, never hosted. Mounts one APIRouter per ruled noun: `agent` (declare/list/show/versions via the D-05 versioned Control Plane path), `skill` (catalog discovery + grants through the two-tier GrantLedger), `workflow` (invoke/resume through the WorkflowFactory handle path only — ORCH-01 at the HTTP boundary — plus status from the state seam), `hitl` (typed queue view + action submission over `HITLTransportProtocol`), `replay` (decisions/resolve via `ccf.replay.engine`; `@latest` → 409), `artifact` (get/put on `ArtifactStoreProtocol`), `product` (GET-only over the egress `ProductResolverProtocol` seam), `config` (registry keys/versions/resolution), plus `/health`.
- **Contracts on the wire**: request/response models are the SDK's own contracts (`AgentDefinition`, `SkillGrant`, `HitlActionSubmission`, `WorkflowStateRecord`, `PendingHitlEvent`, `ArtifactRef`, engine outcome types); thin extra=forbid wrappers only where a route genuinely needs one (declaration/grant/invocation requests). Extra fields die with 422; typed refusals (grant refusals, workflow resume refusals, registration refusals) return as 4xx typed bodies; wiring errors surface as FastAPI's opaque 500 (T-07-26).
- **OpenAPI**: `app.openapi()` emits **3.1.0** (asserted from the document); every contract-bearing route lands a components schema; extra=forbid surfaces as `additionalProperties: false` (spot-checked); `info.description` carries the exact `AUTH_POSTURE_SENTENCE` constant, string-equality-asserted.

## Verification

- `tests/http_api` — 32 tests green (noun-set set-equality parsed from the D-IMPL-22 ruling text in `docs/DECISIONS.md`; no ingest/L1/write path; product read-only; contract round-trips on every noun; OpenAPI validity).
- Full suite: **1173 passed, 0 skipped, 0 failed** (baseline 1141 + 32 new).
- `tools.lints --all` exit 0; `mypy` (strict, src+runtime per pyproject) clean: 126 files, no issues.

## Commits

| Task | Commit | What |
| ---- | ------ | ---- |
| 1 RED | a20f8c3 | failing route tests (noun set, no write door, contracts, refusals) |
| 1 GREEN | 7354126 | app factory + ApiDependencies + 8 noun routers + health |
| 2 | 6457606 | OpenAPI validity + exact auth-posture tests |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Route walk via `app.openapi()` paths instead of `app.routes`**
- **Found during:** Task 1 (GREEN)
- **Issue:** FastAPI 0.140 registers included routers lazily as `_IncludedRouter` entries on `app.routes`; the planned `app.routes` walk sees only `/health` and can never enumerate noun routes.
- **Fix:** The noun-set, forbidden-path, and read-only assertions walk `app.openapi()["paths"]` — the materialized surface, which is also EXPR-03's own claim (the document IS the contract).
- **Files modified:** tests/http_api/test_routes.py
- **Commit:** 7354126

### TDD Gate Compliance

Task 1 followed RED (a20f8c3) → GREEN (7354126) cleanly. Task 2's tests passed on first run: the `AUTH_POSTURE_SENTENCE` constant and OpenAPI metadata were installed structurally with the app factory in Task 1 (the module docstring's posture paragraph references the constant), so Task 2's RED phase was pre-satisfied by Task 1's implementation rather than by accident — investigated per the fail-fast rule and confirmed the tests assert exactly that implementation. The commit is a `test(...)` commit documenting the assertions.

## Residual risk (for the 07-14 gate document)

**T-07-24 (accepted): the v0 surface is unauthenticated.** The exact posture sentence is served in the OpenAPI `info.description` and test-asserted. HITL actions and workflow invocation are authority-bearing surfaces; the acceptance depends entirely on the in-trust-boundary deployment assumption. **Recorded as residual deployment risk** per the plan's threat register (Codex finding).

## Known Stubs

None — every route delegates to a real injected handle; no hardcoded empty values or placeholder responses.

## Threat Flags

None — the delivered surface matches the plan's threat model exactly (no new endpoints beyond the ruled noun set; T-07-23/25/26 mitigations are test-enforced).

## Self-Check: PASSED

All created files present; commits a20f8c3, 7354126, 6457606 verified in log; no unexpected deletions; no stray untracked files.
