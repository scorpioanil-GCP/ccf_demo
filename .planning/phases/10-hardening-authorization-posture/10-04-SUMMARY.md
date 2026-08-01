---
phase: 10-hardening-authorization-posture
plan: 04
subsystem: http-api, examples
tags: [hard-04, hard-05, d-impl-73, d-impl-68, insecure-default, examples]
requires: [10-01, 10-03]
provides:
  - "CcfInsecureDefaultWarning + acknowledge_insecure_default kwarg + once-only first-request log record on create_app (D-IMPL-73, exact)"
  - "Warning-clean tree under -W error::CcfInsecureDefaultWarning"
  - "Examples 05/06 tenant authorization demo (one 200, one 403 tenant-unauthorized) via scope-mapping artifacts + authorizer binding"
  - "Phase-10 examples hash manifest with documented 05/06 re-baseline"
affects: []
tech-stack:
  added: []
  patterns:
    - "per-app once-flag ASGI middleware for the first-request log emission"
    - "shared _INSECURE_DEFAULT_MESSAGE constant keeps the two ruled emission points consistent"
key-files:
  created:
    - tests/http_api/test_insecure_default_warning.py
    - examples/05-workflow-hitl/artifacts/scope_mapping.yaml
    - examples/06-decision-replay/artifacts/scope_mapping.yaml
    - .planning/phases/10-hardening-authorization-posture/10-examples-hash-manifest.txt
  modified:
    - runtime/ccf_runtime/http_api/app.py
    - runtime/ccf_runtime/cli/main.py
    - tests/http_api/conftest.py
    - tests/http_api/test_auth.py
    - tests/http_api/test_hitl_door_identity.py
    - tests/http_api/test_tenant_authz.py
    - tests/hitl/test_was_called_derivation.py
    - tests/cli/test_cli.py
    - examples/05-workflow-hitl/run.py
    - examples/05-workflow-hitl/artifacts/tokens.yaml
    - examples/05-workflow-hitl/README.md
    - examples/06-decision-replay/run.py
    - examples/06-decision-replay/artifacts/tokens.yaml
    - examples/06-decision-replay/README.md
decisions:
  - "Kwarg named acknowledge_insecure_default (Claude's discretion per CONTEXT, house verbosity)"
  - "CLI --local mode acknowledges the warning with an in-code rationale: the in-process ASGI transport is never network-bound, so the posture is the caller's existing in-process authority"
  - "Token entries gained a `label` field so examples can select the approver / expired / unauthorized entries without keying on status (two entries are now active)"
metrics:
  duration: "~35 minutes"
  completed: "2026-08-01"
  tasks: 3
  files: 18
---

# Phase 10 Plan 04: Insecure-Default Warning + Examples Authorization Summary

D-IMPL-73 implemented exactly (`CcfInsecureDefaultWarning` at
construction + once-only first-request logging WARNING, suppressed only
by the `acknowledge_insecure_default` kwarg — no env var), the whole tree
proven warning-clean under `-W error`, and examples 05/06 extended in
place with scope-mapping artifacts and authorizer bindings demonstrating
one authorized (200) and one refused (403 `tenant-unauthorized`) tenant
path, with the 05/06 hash-manifest lines consciously re-baselined per
D-16. ROADMAP criterion 4 is now observable end to end.

## What was built

- **`runtime/ccf_runtime/http_api/app.py`:** exported
  `CcfInsecureDefaultWarning(UserWarning)`; `create_app` gains
  keyword-only `acknowledge_insecure_default: bool = False`. When
  `auth is None` and unacknowledged: `warnings.warn(..., stacklevel=2)`
  at construction plus a per-app once-flag HTTP middleware emitting one
  `logging.getLogger("ccf_runtime.http_api")` WARNING at the first served
  request — both emissions share one `_INSECURE_DEFAULT_MESSAGE`
  constant (the ruling's consistency consequence). `auth` bound or kwarg
  `True` => neither emission; the authorizer never affects the warning.
  `AUTH_POSTURE_SENTENCE` byte-identical (test-pinned). No `os.environ`
  anywhere in the path.
- **`tests/http_api/test_insecure_default_warning.py`:** 7 tests —
  `pytest.warns` on bare construction, category is a `UserWarning`
  subclass, kwarg suppression under `simplefilter("error")`, auth-bound
  silence regardless of kwarg, caplog exactly-one-record across two
  requests / zero after acknowledgment, and the posture-sentence byte
  pin.
- **Call-site sweep (Pitfall 6):** the shared `app` fixture in
  `tests/http_api/conftest.py`, `test_hitl_door_identity`,
  `test_tenant_authz` (auth-unbound legs), `test_was_called_derivation`,
  and `test_cli`'s uvicorn leg acknowledge explicitly; the
  `test_auth.py` posture-preservation test wraps its bare construction
  in `pytest.warns` (the warning documents the posture the test
  asserts). No `filterwarnings` config entry added anywhere. Full suite
  passes with `-W error::ccf_runtime.http_api.app.CcfInsecureDefaultWarning`.
- **Examples 05/06 (D-16, extended in place):** each registers a
  `scope_mapping.yaml` Control Plane artifact (all scope strings, tenant
  patterns, and door action IDs live in YAML — CINV-01) and binds
  `authorizer=ControlPlaneTenantAuthorizer(...)` on `create_app`. A
  third, ACTIVE token with an unmapped scope (`reporting` / `metering`)
  is authenticated but refused deny-by-default: typed 403 carrying
  `ERROR_TENANT_UNAUTHORIZED`, asserted against the imported constant,
  with the deny audited in the one Control Plane log carrying the exact
  registered mapping version and the outsider's client_id as actor.
  stdout prints both legs (`authz allowed (200)` / `authz refused (403)
  … tenant-unauthorized`). READMEs updated with the demo description and
  the adapt-first pointer (edit `scope_mapping.yaml`).
- **`10-examples-hash-manifest.txt`:** Phase-9 manifest lines copied
  verbatim except examples 05/06, whose lines are freshly generated
  (including the two new `scope_mapping.yaml` files); header names the
  Phase 10 D-16 re-baseline as a conscious, documented regeneration.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] CLI `--local` mode fired the new warning**
- **Found during:** Task 2 (`-W error` sweep)
- **Issue:** `runtime/ccf_runtime/cli/main.py` builds `create_app`
  in-process for `--local`/injected-dependency execution; 12 CLI tests
  failed under escalation, and every `ccf --local` invocation would have
  warned on a surface that is never network-bound.
- **Fix:** the CLI acknowledges with an in-code rationale comment (the
  ASGI transport is in-process only; the posture is the caller's own
  in-process authority, not a new exposure surface).
- **Files modified:** runtime/ccf_runtime/cli/main.py
- **Commit:** 091d9e7

**2. [Rule 1 - Bug] Audit-version assertion used the semver, not the registry version**
- **Found during:** Task 3 (example 05 first run)
- **Issue:** `register_typed` versions artifacts by content hash, not by
  the artifact's own `semver` field; the deny-audit assertion failed.
- **Fix:** capture the version string `register_typed` returns and
  assert the audited deny carries exactly that.
- **Files modified:** examples/05-workflow-hitl/run.py (and 06 written
  correctly from the start)
- **Commit:** 7779a74

**3. [Rule 1 - Bug] Variable shadowing in example 05's print path**
- **Found during:** Task 3
- **Issue:** the new authz-refusal response was stored in `refused`,
  which later legs reuse — the final print showed the wrong error code.
- **Fix:** renamed to `authz_refused` / captured `authz_refusal_code`
  at assertion time.
- **Files modified:** examples/05-workflow-hitl/run.py
- **Commit:** 7779a74

### Note on Task 3 TDD

Task 3 is marked `tdd="true"` but its behavior surface is two example
drivers (no test files in its file set); the RED/GREEN cycle was
realized as run-fail/fix/run-pass against `make example-05 example-06`
rather than as separate test commits. Task 1 followed the full
RED-commit/GREEN-commit cycle.

## Verification

- `make ci` — green end to end: lints exit 0, `mypy --strict` clean
  (161 files), 1439 passed / 2 skipped, all eight examples OK
- `pytest tests/ -W error::ccf_runtime.http_api.app.CcfInsecureDefaultWarning`
  — 1439 passed, zero unhandled emissions
- `grep -c "class CcfInsecureDefaultWarning" runtime/ccf_runtime/http_api/app.py` — 1
- `grep -v '^#' runtime/ccf_runtime/http_api/app.py | grep -c "os.environ"` — 0
- No `ignore::…CcfInsecureDefaultWarning` filter in any pytest config
- `grep -v '^#' examples/05…/run.py examples/06…/run.py | grep -c "tenant-a\|hitl.queue.read"` — 0
- `sha256sum -c` over the manifest's 05/06 lines — all OK
- Both example stdouts contain `tenant-unauthorized`

## Commits

| Task | Commit | Description |
| ---- | ------ | ----------- |
| 1 (RED) | a3d53e4 | test(10-04): failing D-IMPL-73 warning tests |
| 1 (GREEN) | 0d70977 | feat(10-04): CcfInsecureDefaultWarning in create_app |
| 2 | 091d9e7 | fix(10-04): bare create_app call-site sweep |
| 3 | 7779a74 | feat(10-04): examples 05/06 tenant authz + manifest re-baseline (D-16) |

## Known Stubs

None — no placeholder values or unwired surfaces.

## Threat Flags

None beyond the plan's threat model: T-10-15 (loud warning, single
greppable kwarg, no env var), T-10-16 (`-W error` sweep run; no blanket
filter), T-10-17 (only 05/06 manifest lines regenerated; header and
commit cite D-16), and T-10-18 (examples bind auth= and authorizer= and
demonstrate a live 403) are all implemented and verified.

## Self-Check: PASSED

All four created files exist on disk; commits a3d53e4, 0d70977, 091d9e7,
7779a74 present in git log; no file deletions in the plan's diff range.
