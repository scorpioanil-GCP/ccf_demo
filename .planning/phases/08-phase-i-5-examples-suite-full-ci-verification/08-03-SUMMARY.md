---
phase: 08-phase-i-5-examples-suite-full-ci-verification
plan: 03
subsystem: hitl/http_api/mcp
tags: [d-16, signed-binding, non-repudiation, error-codes, r1, was-called]
requires: [08-01, 08-02]
provides:
  - "HitlPolicy Control Plane artifact (ccf.hitl-policy) with schema-validated signed_binding_required (default false on absence)"
  - "D-16 enforcement at the transport authority path: SignedBindingRequiredRefused / SignedBindingInvalidRefused before anything lands"
  - "Door mapping: both refusals carry ERROR_SIGNED_BINDING_* constants at HTTP and MCP (shared source of truth)"
  - "R1 closed: was-called derivation assertions on both door seams"
affects: [08-08 example 05 refusal assertions, 08-09 example 06 replay of signed bindings]
tech-stack:
  added: []
  patterns:
    - "Policy re-resolved from the Control Plane per submission — flip the registered value, behavior flips, zero code change"
    - "Wrap-and-count monkeypatch spy (wrap, don't replace) for was-called regression guards"
key-files:
  created:
    [
      tests/hitl/test_signed_binding_authority.py,
      tests/http_api/test_signed_binding_door.py,
      tests/hitl/test_was_called_derivation.py,
    ]
  modified:
    [
      src/ccf/hitl/transport.py,
      runtime/ccf_runtime/http_api/routes/hitl.py,
      runtime/ccf_runtime/mcp/hitl_server.py,
    ]
decisions:
  - "HitlPolicy contract lives in ccf.hitl.transport (the authority seam it governs), class_id ccf.hitl-policy; the documented example surface is the signed_binding_required field of the deployment's HITL policy YAML"
  - "Both D-16 refusals map to HTTP 403 (authority-shaped refusals, matching 08-02's subject-conflict precedent)"
  - "MCP door carries the codes as canonical-JSON refusal_detail payloads inside the tool error (same constants imported from http_api.errors — no duplicated strings)"
  - "MCP tool gains optional signed_binding_signature/key_id, presented together-or-not-at-all, wrapping the derived binding"
metrics:
  duration: "~15 min"
  completed: "2026-07-31"
---

# Phase 08 Plan 03: Hardening B — D-16 signed-binding requiredness, door mapping, R1 Summary

Signed-binding requiredness is now a Control Plane value enforced at the
HITL transport authority path with two distinct typed refusals, mapped to
08-02's `ERROR_SIGNED_BINDING_*` constants at both the HTTP and MCP doors,
plus R1 was-called derivation assertions — all TDD, within D-IMPL-21/63/67.

## What was built

- **Task 1 (RED b80249a, GREEN 86ee2e3):** `HitlPolicy` artifact contract
  (`ccf.hitl-policy`) with schema-validated `signed_binding_required: bool
  = False` — absent key is well-defined false, never a KeyError (Ollama
  C3). `HitlActionSubmission` gained optional `signed_binding:
  SignedPrincipalBinding | None`. `InMemoryHitlTransport` optionally binds
  `control_plane` / `hitl_policy_key` / `identity_provider` /
  `trusted_keys`; `submit()` re-resolves the policy per call and, when
  required, verifies via `verify_principal_binding` (joserfc JWS, never
  hand-rolled — T-08-05) and enforces principal match (T-08-06) before
  recording. Two distinct refusals: `SignedBindingRequiredRefused` (absent)
  and `SignedBindingInvalidRefused` (invalid/mismatch). Five-case matrix
  green including flip-the-Control-Plane-value-only and the grep guard that
  no `signed_binding_required = True` exists in /src (T-08-07).
- **Task 2 (RED 6e04967, GREEN 05eefce):** `routes/hitl.py` catches the
  two transport refusals and returns 403 `refusal_detail` bodies carrying
  `ERROR_SIGNED_BINDING_REQUIRED` / `ERROR_SIGNED_BINDING_INVALID`;
  `mcp/hitl_server.py` mirrors the mapping in its tool error payloads,
  importing the same constants (T-08-07b). The MCP tool accepts optional
  `signed_binding_signature`/`signed_binding_key_id` (together or not at
  all) wrapping the derived principal. Signed bindings round-trip through
  the HTTP body into `HitlActionSubmission` with no serializer change
  (Pydantic field). No route redesign; no workflow-engine ripple — the
  bounded-scope guard never fired.
- **Task 3 (317a871):** `tests/hitl/test_was_called_derivation.py`
  — wrap-and-count spies prove `principal_from_token_grant` is actually
  invoked (call_count == 1, verified grant argument) on both auth-bound
  doors and that the recorded principal **is** the derivation's return
  value (object identity, not equality); the unauthenticated posture never
  derives. R1 (Cursor LOW, 07-REVIEWS) closed.

## Deviations from Plan

**Scope note (not a deviation):** the plan's Task 2 RED expected all four
door tests to fail; the positive HTTP round-trip (Test 3) passed at RED
because Task 1's GREEN already shipped the `signed_binding` contract field
and transport admission — the door's happy path needed no new code. The
two refusal-mapping tests and the MCP parity test were genuinely red and
drove the GREEN change.

Otherwise: none — plan executed as written. The Codex HIGH bounded-scope
stop condition (ripple beyond the named files) did not trigger.

## Verification

- `pytest tests/hitl -q` → 74 passed (Task 1); `pytest tests/http_api
  tests/hitl -q` → 134 passed (final)
- `grep -n "ERROR_SIGNED_BINDING" routes/hitl.py mcp/hitl_server.py` →
  both doors import and emit the shared constants
- Every new refusal payload is `refusal_detail(...)` — code + prose,
  never prose-only
- `make ci-core` green; final `make test` → **1337 passed / 0 failed**
  (`CCF_REQUIRE_HARNESSES=1`); mypy clean (156 files); `tools.lints
  --all` exit 0

## TDD Gate Compliance

- Task 1: RED b80249a (`test(...)`) → GREEN 86ee2e3 (`feat(...)`)
- Task 2: RED 6e04967 (`test(...)`) → GREEN 05eefce (`feat(...)`)
- Task 3: 317a871 — tests-only per plan ("no production change expected") — the
  was-called regression guards are green against as-built code by design.

## Known Stubs

None.

## Threat Flags

None — all surface introduced was in the plan's threat model
(T-08-05..07, T-08-07b, all mitigated as planned).

## Self-Check: PASSED
