---
phase: 07-phase-i-4-orchestration-hitl-experience
plan: 15
subsystem: hitl
tags: [hitl, identity, jws, d-impl-21, d-impl-66, gap-closure]
requires:
  - src/ccf/hitl/principal.py (HumanPrincipalBinding)
  - src/ccf/peering/identity.py (D-IMPL-15 signing machinery)
provides:
  - "SignedPrincipalBinding contract + sign/verify functions (D-IMPL-21 reference impl #2)"
affects:
  - 07-16 (auth-context-derived reference impl #1, runtime leg)
tech-stack:
  added: []
  patterns:
    - "Detached compact JWS (protected..signature) carried beside the clear binding; payload recomputed from the binding at verify time"
key-files:
  created:
    - src/ccf/hitl/identity_binding.py
    - tests/hitl/test_identity_binding.py
  modified:
    - src/ccf/hitl/__init__.py
decisions:
  - "verify_principal_binding takes an explicit public_keys mapping (mirroring IdentityProvider.verify) — trust resolution stays outside the seam, and the unknown-key test requires the caller-supplied key set"
  - "signature field carries the RFC 7515 Appendix F detached compact form ({protected}..{signature}) so SignedPrincipalBinding stays three fields as planned while preserving the provider's detached envelope exactly"
metrics:
  duration: "~15 min"
  completed: "2026-07-30"
---

# Phase 7 Plan 15: JWS-Signed Principal Binding (D-IMPL-21 ref impl #2) Summary

JWS-signed HumanPrincipalBinding via ccf.peering.identity (D-IMPL-15 reuse): detached ES256 JWS over canonical_bytes(binding), typed PrincipalBindingInvalid on tamper/unknown-key, giving HITL approver identity cryptographic non-repudiation per D-IMPL-66(a).

## Tasks

| Task | Name | Commit(s) | Files |
| ---- | ---- | --------- | ----- |
| 1 | SignedPrincipalBinding (TDD) | d328197 (RED), 0579f4c (GREEN) | src/ccf/hitl/identity_binding.py, src/ccf/hitl/__init__.py, tests/hitl/test_identity_binding.py |
| 2 | Full-suite regression sweep | (verification only, no changes) | — |

## What Was Built

- `SignedPrincipalBinding(CCFContract)`: `binding: HumanPrincipalBinding`, `signature: str` (detached compact JWS `{protected}..{signature}` exactly as the D-IMPL-15 provider emits its detached members), `key_id: str`. `extra=forbid` proven by test.
- `sign_principal_binding(binding, *, provider, key_id)` — delegates to `IdentityProvider.sign(product=binding, ...)`; payload is `canonical_bytes(binding)` (single serialization, D-IMPL-38/26; naive datetimes already refused by the canonical serializer).
- `verify_principal_binding(signed, *, provider, public_keys)` — rebuilds the provider's `SignedContextProduct` envelope from the binding's recomputed canonical bytes, cross-checks the declared `kid` against `signed.key_id`, and wraps every peering-identity failure in `PrincipalBindingInvalid` with the cause chained (`raise ... from`).
- No new key machinery, no JWS registry, no algorithm constant in this module — machinery reuse verified by grep gates (1 import of `ccf.peering.identity`, 0 `JWSRegistry`, 0 `ccf_runtime`), `__ccf_mode__ = "algorithmic"`.

## Tamper-Test Red Output (verbatim, per plan counterfactual discipline)

RED phase (tests committed at d328197 before the module existed):

```
ERROR collecting tests/hitl/test_identity_binding.py
ImportError while importing test module '.../tests/hitl/test_identity_binding.py'.
tests/hitl/test_identity_binding.py:24: in <module>
    from ccf.hitl.identity_binding import (
E   ModuleNotFoundError: No module named 'ccf.hitl.identity_binding'
1 error in 0.18s
```

The tamper counterfactual assertion now passing GREEN: `test_a_binding_with_a_substituted_approver_fails_verification` re-binds the original signature to a binding whose approver `subject_id` is `"attacker-substituted-approver"` and asserts `pytest.raises(PrincipalBindingInvalid)` with `caught.value.__cause__` an instance of `SignatureInvalid` — a forged approver identity is detected, not admitted.

## Verification

- `pytest tests/hitl/test_identity_binding.py -q` — 4 passed (round-trip, tamper, unknown-key, extra=forbid).
- Full suite: **1284 passed, 0 failed, 0 skipped** (baseline 1280 + 4 new).
- `mypy --strict src runtime tools` — Success: no issues found in 165 source files.
- `tools.lints --all` — exit 0.

## Deviations from Plan

**1. [Rule 3 - Blocking] `verify_principal_binding` takes a required `public_keys` kwarg**
- **Found during:** Task 1
- **Issue:** The plan's sketch `verify_principal_binding(signed, *, provider)` is uncallable against the actual `IdentityProvider.verify(*, signed, public_keys)` surface, which deliberately takes candidate public keys from the caller (trust stays outside the seam — module doctrine of `ccf.peering.identity`). The plan itself instructs "match the exact signatures as they exist … do not assume."
- **Fix:** Added `public_keys: Mapping[str, JsonWebKey]` as a required keyword, mirroring the provider. This is also what makes the plan's Test 3 (unknown key) expressible.
- **Files modified:** src/ccf/hitl/identity_binding.py
- **Commit:** 0579f4c

## Threat Model Dispositions

| Threat | Disposition | Evidence |
|--------|-------------|----------|
| T-07.1-01 Spoofing (binding fields) | mitigated | forged-approver test raises `PrincipalBindingInvalid` (cause `SignatureInvalid`) |
| T-07.1-02 Repudiation | mitigated | detached JWS over canonical bytes via D-IMPL-15 provider |
| T-07.1-03 Tampering (payload bytes) | mitigated | payload recomputed from the delivered binding; any mutation invalidates the signature |

## Self-Check: PASSED

- src/ccf/hitl/identity_binding.py — FOUND
- tests/hitl/test_identity_binding.py — FOUND
- Commits d328197, 0579f4c — FOUND in log
