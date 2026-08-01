---
phase: 10-hardening-authorization-posture
plan: 02
subsystem: hitl
tags: [hitl, authorization, signed-binding, d-impl-69, hardening]
requires:
  - "Phase 8 D-16 transport verification machinery (transport.py private pair)"
  - "ccf.hitl.identity_binding (D-IMPL-21 reference impl #2)"
provides:
  - "Module-level signed_binding_required / enforce_signed_binding helpers in ccf.hitl.transport"
  - "Signed-binding verification on all four HITL primitive resolution surfaces (D-IMPL-69)"
  - "Additive signed_binding parameter threading through to HitlActionSubmission (Pitfall 5)"
affects:
  - "10-01/10-03 (HARD-04 door plans): doors can now thread signed bindings to primitives"
tech-stack:
  added: []
  patterns:
    - "Shared module-level verification helpers, delegated by the transport's private pair (D-13: shared code allowed, trust markers forbidden)"
    - "Optional-together verification kwargs (control_plane, hitl_policy_key, identity_provider, trusted_keys) — unbound is byte-identical prior posture"
key-files:
  created: []
  modified:
    - src/ccf/hitl/transport.py
    - src/ccf/hitl/approval_gate.py
    - src/ccf/hitl/override.py
    - src/ccf/hitl/review_queue.py
    - src/ccf/hitl/escalation.py
    - tests/hitl/test_signed_binding_authority.py
    - tests/hitl/test_approval_gate.py
    - tests/hitl/test_override.py
    - tests/hitl/test_review_queue.py
    - tests/hitl/test_escalation.py
decisions:
  - "Verification runs after the internally-built HitlActionSubmission is constructed and before transport.submit/_consume — refusal raises with the pending event untouched (Pitfall 4)"
  - "ReviewQueue.reject also verifies (shared _resolve path) — D-12 says close the class on every authority-bearing surface, and reject is one"
  - "Primitive-layer refusals raise (transport refusal semantics), unlike TOCTOU refusals which return typed values — matches the D-14 reuse of the exception classes"
metrics:
  duration: "~25 minutes"
  completed: "2026-08-01"
---

# Phase 10 Plan 02: HITL Primitive Signed-Binding Verification Summary

**One-liner:** D-IMPL-69 implemented — shared signed-binding verification helpers extracted from the transport and applied at all four HITL primitive resolution surfaces (ApprovalGate.resolve, OverrideBoundary.resolve, ReviewQueue.release/reject, ExceptionEscalation.resolve) with idempotent double verification at the transport (D-13) and refusal-leaves-pending semantics (Pitfall 4).

## Tasks Completed

| Task | Name | Commits | Files |
| ---- | ---- | ------- | ----- |
| 1 | Extract shared verification helpers in transport.py | c5011f8 (test), c03c5ea (feat) | transport.py, test_signed_binding_authority.py |
| 2 | Verification on ApprovalGate.resolve and OverrideBoundary.resolve | 1aae58c (test), e1f927e (feat) | approval_gate.py, override.py, test_approval_gate.py, test_override.py |
| 3 | Verification on ReviewQueue.release and ExceptionEscalation.resolve + composed idempotency | 5b30afa (test), 906af16 (feat) | review_queue.py, escalation.py, test_review_queue.py, test_escalation.py, test_signed_binding_authority.py |

## What Was Built

- **`signed_binding_required(*, control_plane, hitl_policy_key) -> bool`** and
  **`enforce_signed_binding(submission, *, identity_provider, trusted_keys) -> None`** —
  module-level in `ccf.hitl.transport`, added to `__all__`. Exact semantics of the
  former private pair (unbound => False; per-call `resolve_latest`; TypeError on
  non-HitlPolicy; `SignedBindingRequiredRefused` / `SignedBindingInvalidRefused` /
  RuntimeError-on-broken-wiring). `InMemoryHitlTransport`'s private methods now
  delegate — zero external caller change, all pre-existing transport tests pass
  unmodified. Docstrings note D-13 forbids marker plumbing, not shared code.
- **Four hardened primitives.** Each constructor gained the four keyword-only
  optional-together verification kwargs; each resolution surface gained an
  additive keyword-only `signed_binding: SignedPrincipalBinding | None = None`
  threaded into the internally-built `HitlActionSubmission`, so the transport's
  intentional second verification accepts what the primitive accepted (Pitfall 5).
  Verification runs before `transport.submit` and `_consume`: a refusal raises
  and the pending event survives — a subsequent valid resolve of the same event
  succeeds (test-asserted per primitive).
- **Composed idempotency tests** (ApprovalGate + ReviewQueue in
  `test_signed_binding_authority.py`): both layers bound, one valid signed
  submission traverses primitive AND transport verification end-to-end; an
  unsigned submission is refused at the primitive layer before the transport is
  touched.

## Verification

- `pytest tests/hitl -q`: 104 passed
- Full regression `pytest tests -q`: 1377 passed, 2 skipped
- `mypy --strict src/ccf/hitl/`: clean (9 files)
- `python -m tools.lints --all`: exit 0
- No new exception classes (D-14): `grep -c "class SignedBinding"` in transport.py == 2
- `enforce_signed_binding` call sites present in all four primitive files

## Deviations from Plan

None - plan executed exactly as written. (One discretionary extension consistent
with D-12: `ReviewQueue.reject` shares `_resolve` with `release`, so it verifies
too — the plan named `release`; leaving `reject` unverified would have left an
authority-bearing surface open.)

## Requirements

HARD-05 is **half complete** per this plan ("gate-verification half"); the
create_app-warning half lands in the sibling plan. REQUIREMENTS.md was NOT
updated — the orchestrator should mark HARD-05 only when both halves merge.

## Known Stubs

None.

## Threat Flags

None — no new surface beyond the plan's threat model (T-10-06/07/08/09 all
mitigated as planned).

## Self-Check: PASSED

- All five src files contain verification call sites: FOUND
- Commits c5011f8, c03c5ea, 1aae58c, e1f927e, 5b30afa, 906af16: FOUND in git log
- SUMMARY.md: this file
