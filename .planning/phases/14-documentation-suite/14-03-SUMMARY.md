---
phase: 14-documentation-suite
plan: 03
subsystem: docs-http-contract
tags: [openapi, drift-check, d-12, http-api]
requires:
  - "runtime/ccf_runtime/http_api/app.py::create_app"
  - "runtime/ccf_runtime/http_api/dependencies.py::ApiDependencies"
provides:
  - "openapi.json — the committed HTTP contract baseline (D-12)"
  - "make openapi — one-command deterministic regeneration"
  - "tools.dump_openapi.serialize — the single serialization recipe"
affects:
  - "plan 14-06 (public/reference/http-api.md whole-file-includes openapi.json)"
  - "plan 14-10 (CI step already runs tools/docs_tests)"
tech-stack:
  added: []
  patterns:
    - "Committed derivative + always-on byte-equality drift assertion"
    - "Standing negative control outside testpaths (tools/lints/tests precedent)"
key-files:
  created:
    - tools/dump_openapi.py
    - openapi.json
    - tools/docs_tests/test_openapi_drift_control.py
  modified:
    - Makefile
    - tests/http_api/test_openapi.py
decisions:
  - "D-12's committed spec is asserted on bytes, not parsed dicts — the file is reviewed as a diff, so whitespace and key order are part of the contract"
  - "The serialization recipe is stated once in tools/dump_openapi.py and imported by both the drift test and the negative control"
metrics:
  duration: ~25 min
  completed: 2026-08-03
---

# Phase 14 Plan 03: OpenAPI Drift Baseline Summary

The HTTP contract is now a committed, byte-stable `openapi.json` regenerated
by `make openapi` and asserted equal to `create_app()`'s output by a test in
the already-always-on `test` job, with a standing negative control proving the
comparison still discriminates.

## What Was Built

**Task 1 — `tools/dump_openapi.py` + `make openapi`** (commit `0054cdb`)

The tool constructs the app and writes
`json.dumps(document, indent=2, sort_keys=True) + "\n"` to `openapi.json` at
the repo root. It exposes `serialize()` as the single statement of the
recipe, `OPENAPI_PATH` as the single statement of the location, and a
`--check` flag that writes nothing and returns 1 on a mismatch, so the tool is
usable as both regenerator and standalone check.

The module docstring names D-12, states why the committed spec is the
reviewable baseline (D-11's generate-at-build posture with one deliberate
exception), states the determinism levers (`sort_keys=True` plus the exact
`fastapi`/`pydantic` pins), and states the corollary explicitly: a dependency
bump *will* move the spec, and that diff is desirable rather than a bug.

`ApiDependencies` is constructed with `None` handles rather than duplicating
the fixture's fabric wiring, because `create_app` mounts routers
unconditionally and nothing reads the bundle at construction time. This was
verified empirically, not assumed — the drift test runs against the
conftest fixture's *fully-wired* app and passes against the null-deps dump,
so the two constructions are demonstrably schema-identical. A future
divergence would fail the check rather than hide in it.

The `openapi` target joined the `.PHONY` docs group. The `ci:` line was left
untouched, per the plan: the drift assertion rides the existing `test` job.

Emitted spec: OpenAPI 3.1.0, 21 paths, 2095 lines.

**Task 2 — the always-on drift assertion + standing control** (commit `4aacb28`)

`tests/http_api/test_openapi.py` gained three tests beside the existing ones,
using the same `(app: Any)` fixture signature:

- byte-equality of the committed file against `serialize(app.openapi())`,
  failing with `_DRIFT_MESSAGE`;
- an edge-case test asserting that message names `make openapi` literally;
- a test that the committed artifact parses and advertises a non-empty
  `paths`.

The repo root is resolved from `pathlib.Path(__file__).resolve().parents[2]`,
never `Path.cwd()`. The recipe is imported from `tools.dump_openapi` rather
than restated, with the determinism rationale in the loud-comment style the
file already uses for pins.

`tools/docs_tests/test_openapi_drift_control.py` is the standing negative
control (3 tests): one clean case asserting an unmutated copy compares equal,
one renaming the first *sorted* path key on an in-memory copy, one appending
a sentence to `info.description`. It imports the shared `serialize`, never
writes to any file, and hard-codes no endpoint name — route churn cannot turn
it into a no-op. It lives outside `testpaths` per the `tools/lints/tests/`
precedent and joins plan 14-10's existing
`pytest tools/publish_scan_tests tools/docs_tests -q` step with no wiring.

**Assumption A4 held.** The bytes were stable across runs; the documented
parsed-dict fallback was not needed.

## Verification

| Check | Result |
|---|---|
| `make openapi` twice → `git status --porcelain openapi.json` empty second time | pass (byte-stable) |
| `tools/dump_openapi.py --check` on the committed file | exit 0 |
| Same after a one-character edit to `openapi.json` | exit 1, message names `make openapi` (reverted) |
| Single trailing newline | pass |
| `make help \| grep openapi` names D-12 | pass |
| `pytest tests/http_api/test_openapi.py -q` | 8 passed |
| Mutated `openapi.json` → drift test fails, output contains `make openapi` | pass (reverted) |
| `/health` renamed to `/healthz` in `app.py` → drift test fails with `make openapi` | pass (reverted) |
| `pytest tools/docs_tests/test_openapi_drift_control.py -q` | 3 passed |
| `git status --porcelain openapi.json` after control run | empty |
| `make lint` | pass |
| `make typecheck` | Success, 161 files |
| `make test` | 1536 passed, 2 skipped (283s) |

## Threat Mitigations Applied

- **T-14-15 / T-14-18** — byte-equality against `create_app()` in the always-on
  `test` job; a hand edit or a stale spec fails on the same commit.
- **T-14-17** — `sort_keys=True` plus exact pins; stability proven by running
  the dump twice.
- **T-14-18b** — the standing control exercises the failing polarity on every
  run, including a subtle prose-only mutation, so a refactor of `serialize`
  that stopped discriminating would fail here.

## Deviations from Plan

**1. [Rule 3 — Blocking] Symlinked the primary `.venv` into the worktree**

- **Found during:** Task 1
- **Issue:** The Makefile hard-codes `PYTHON := .venv/bin/python`, relative to
  cwd; the parallel-execution worktree has no `.venv`, so `make openapi`,
  `make lint`, `make typecheck` and `make test` were all unrunnable.
- **Fix:** `ln -s /home/parkave/ccf_code/.venv .venv` inside the worktree.
  `.venv` is gitignored (line 15), so nothing was committed and no Makefile
  change was needed. `PYTHONPATH=src:runtime` stays relative, so imports
  resolved against this worktree's sources (confirmed: the drift test imported
  the `tools/dump_openapi.py` written here).
- **Files modified:** none tracked.
- **Commit:** n/a.

No other deviations — the plan executed as written.

## Known Stubs

None.

## Threat Flags

None. No new network endpoint, auth path, or trust-boundary schema was
introduced; `openapi.json` describes the pre-existing route surface and is
reviewed as a diff precisely so T-14-16 (internal detail in a description)
surfaces at review time.

## TDD Gate Compliance

Task 2 carried `tdd="true"`, but its deliverable is *itself* test code
asserting an artifact committed in Task 1, so the RED/GREEN split degenerates:
there is no production behavior for a failing test to drive out. The failing
polarity was proven two ways instead — by the two reverted acceptance probes
(mutated `openapi.json`; `/health` renamed to `/healthz`, both producing a
failure whose output contains `make openapi`) and, permanently, by the
committed standing negative control, which is exactly the artifact the plan
specifies for this reason. Commits: `feat(14-03)` then `test(14-03)`.

## Self-Check: PASSED

- `tools/dump_openapi.py` — FOUND
- `openapi.json` — FOUND
- `tools/docs_tests/test_openapi_drift_control.py` — FOUND
- commit `0054cdb` — FOUND
- commit `4aacb28` — FOUND
