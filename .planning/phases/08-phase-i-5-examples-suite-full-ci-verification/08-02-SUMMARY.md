---
phase: 08-phase-i-5-examples-suite-full-ci-verification
plan: 02
subsystem: http_api/cli
tags: [hitl, auth, hardening, d-15, error-codes, fail-closed]
requires: [08-01]
provides:
  - "ccf hitl decide removed; submit is the one verb (D-15, logged in DECISIONS.md)"
  - "runtime/ccf_runtime/http_api/errors.py — typed refusal error-code constants incl. reserved signed-binding codes for 08-03"
  - "Fail-closed isinstance(grant, TokenGrant) branch at the HITL HTTP door"
affects: [08-03 door mapping, examples 05/06 hardened HITL surface]
tech-stack:
  added: []
  patterns:
    - "refusal_detail(error_code, message) as the one refusal-body shape"
    - "Absence test enforcing a removed CLI verb"
key-files:
  created: [runtime/ccf_runtime/http_api/errors.py, tests/http_api/test_auth_hardening.py]
  modified: [runtime/ccf_runtime/cli/commands/hitl.py, runtime/ccf_runtime/http_api/app.py, runtime/ccf_runtime/http_api/routes/hitl.py, tests/cli/test_cli.py, tests/http_api/test_hitl_door_identity.py, docs/DECISIONS.md]
decisions:
  - "Non-TokenGrant grant object at the door refuses with 403 ERROR_INVALID_GRANT (auth-shaped fail-closed refusal, per the plan's 403-or-500 latitude)"
  - "Error-code constants scoped to auth-composition refusals (401/403 door branches); generic 404/409 fabric refusals keep their typed SDK exception bodies"
metrics:
  duration: "~12 min"
  completed: "2026-07-31"
---

# Phase 08 Plan 02: Hardening A — D-15 verb removal, fail-closed grant branch, typed error codes Summary

`ccf hitl decide` deleted tree-wide with an absence test (D-15), plus the
Codex fail-closed `isinstance(TokenGrant)` branch and Ollama typed refusal
`error_code` constants in a new `http_api/errors.py` — all TDD.

## What was built

- **Task 1 (RED 8d77d04, GREEN b7d233a):** The 07-19 deprecation test
  flipped to an absence test — `ccf hitl decide` is an argparse
  invalid-choice with nonzero exit, and `hitl --help` names no `decide`
  and no deprecation. `_decide`, its stderr notice, and its subparser
  registration deleted from `cli/commands/hitl.py`; module docstring
  records the removal. Tree-wide `grep` sweep: only historical gate/review
  documents still mention the verb. `docs/DECISIONS.md` gained the D-15
  entry (2026-07-30, Dave): v0 ships one verb, `submit`.
- **Task 2 (RED bf05655, GREEN e866e08):** New
  `runtime/ccf_runtime/http_api/errors.py` exporting `Final[str]`
  constants — `ERROR_UNAUTHENTICATED`, `ERROR_SUBJECT_CONFLICT`,
  `ERROR_INVALID_GRANT`, plus `ERROR_SIGNED_BINDING_REQUIRED` /
  `ERROR_SIGNED_BINDING_INVALID` reserved for 08-03's door mapping — each
  with a one-line stable-surface docstring, and `refusal_detail()` as the
  single refusal-body shape. `routes/hitl.py` gained the fail-closed
  branch: a stashed grant that is not a `TokenGrant` instance is a typed
  403 `ERROR_INVALID_GRANT` refusal before principal derivation — the
  caller-supplied principal is never used, and the test asserts nothing
  landed on the transport (impostor is a duck-typed compatible object,
  proven `not isinstance`). The 401 in `app.py` and the subject-conflict
  403 now carry `error_code`; the one prose-parsing assertion
  (`test_hitl_door_identity.py` "identity" in text) migrated to the
  constant.

## Deviations from Plan

**1. [Rule 1 - Bug] Wrap-tolerant help assertion in the rewritten CLI test**
- **Found during:** Task 1 GREEN
- **Issue:** With `decide` gone, argparse re-wraps the shorter help text,
  splitting "resolution is the owning primitive's act" across lines; the
  carried-over exact-substring assertion failed.
- **Fix:** Assertion normalizes whitespace before matching.
- **Files modified:** tests/cli/test_cli.py
- **Commit:** b7d233a

**Scope note (not a deviation):** error-code constants cover the auth
composition's refusal branches (401 unauthenticated, 403 subject-conflict,
403 invalid-grant, reserved signed-binding pair). The generic 404/409/422
fabric refusals across the other nouns wrap typed SDK exception bodies and
were not the reviews' finding; no test parses their prose either.

## Verification

- `pytest tests/cli -q` → 43 passed (absence test green)
- `grep -rn "hitl decide" runtime src` → no matches
- `pytest tests/http_api tests/hitl tests/cli -q` → 163 passed
- `python -c "from ccf_runtime.http_api.errors import ERROR_INVALID_GRANT, ERROR_SIGNED_BINDING_REQUIRED, ERROR_SIGNED_BINDING_INVALID"` → ok
- `make lint` exit 0; `make typecheck` → clean, 156 files
- `make test` → **1323 passed / 0 failed** (`CCF_REQUIRE_HARNESSES=1`)

## TDD Gate Compliance

Task 1: RED 8d77d04 (`test(...)`) → GREEN b7d233a (`feat(...)`).
Task 2: RED bf05655 (`test(...)`) → GREEN e866e08 (`feat(...)`).

## Known Stubs

None. The reserved `ERROR_SIGNED_BINDING_*` constants are deliberate
forward exports per the plan (emitting branches land in 08-03).

## Self-Check: PASSED
