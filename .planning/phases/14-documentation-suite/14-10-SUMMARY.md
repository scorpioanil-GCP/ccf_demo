---
phase: 14-documentation-suite
plan: 10
subsystem: docs-gate-ci
tags: [docs, ci, publish-safety, D-IMPL-72, D-IMPL-71, D-02]
requires: ["14-02", "14-03", "14-05", "14-06", "14-07", "14-08", "14-09"]
provides:
  - "make docs-strict — the whole docs gate as one blocking target"
  - "make ci = ci-core + examples + docs-strict (D-IMPL-72)"
  - "always-on CI docs job with gate tests and ccf-docs-site artifact upload"
affects: [Makefile, .github/workflows/ci.yml, public/charter.md, public/index.md]
tech-stack:
  added: []
  patterns:
    - "gate checkers tested in CI before the gate they implement (lint-job precedent)"
    - "one make target per CI job step — CI and local run the identical command string"
key-files:
  created:
    - .planning/phases/14-documentation-suite/14-10-SUMMARY.md
  modified:
    - Makefile
    - .github/workflows/ci.yml
    - public/charter.md
    - public/index.md
decisions:
  - "D-IMPL-72 performed: docs-strict joins `ci` now that the gate is complete, never as a half-armed target"
  - "ENV_DOCS adds the repo root to PYTHONPATH because the publish scan is invoked script-form, not -m"
metrics:
  tasks: 3
  commits: 3
  duration: ~35m
  completed: 2026-08-03
---

# Phase 14 Plan 10: Close the Docs Gate Summary

The documentation gate is now one blocking command, part of `make ci`, and part of always-on CI on
every push and pull request — with its own checker tests running before it and the rendered site
uploaded as the `ccf-docs-site` artifact.

## What was built

**`make docs-strict` (Makefile).** Three ordered commands in one recipe: the pre-build structural
scan over `public/`, then `mkdocs build --strict`, then the post-build content scan over `site/`.
Pre-build runs first so a symlink or an escaping include is reported before the build can copy it.
No `|| true`, no `-` prefix, no report-only flag — verified by assertion against the recipe.

**`ci: ci-core examples docs-strict`.** The Phase-8 D-10 comment block above `ci:` is retained
verbatim and gains a D-IMPL-72 paragraph recording that the amendment was pre-authorized and
performed here, once the gate was real.

**The always-on CI `docs` job.** Mirrors the examples job (checkout@v4, setup-python@v5 with
`cache: pip`, dev-extras install, `.venv` provisioning with the verbatim rationale comment),
`timeout-minutes: 15`, no `if:` guard, no `secrets:`, no `env:`, no `continue-on-error` anywhere.
Its comment block names D-IMPL-71, D-IMPL-72, D-02 and states the deliberate absence of
`continue-on-error` against the I.1 D-07 precedent. The gate-checker unit tests run at a lower step
index than `make docs-strict`; the `upload-artifact@v4` step follows the gate, so a nonzero exit
fails the job and nothing ships.

**The two boundary documents.** `public/charter.md` now names `make docs-strict` and lists its three
checks in order, and states that the CI docs job runs the identical command and uploads the result;
the never-publish rule, Mermaid CDN caveat and decision-log note are unchanged. `public/index.md`
gives a first-time reader one recommended path (adopter's guide → their pillar → the Reference
surface that realizes it) and routes into all four Diátaxis sections as they actually exist.

## The CI wiring gap this plan closed

The orchestrator flagged that pytest `testpaths = ["tests"]` does not reach `tools/`, so the
publish-scan and docs-gate tests were not running in CI at all. Demonstrated post-change:

| Gate | Runs in CI via | Evidence |
|------|----------------|----------|
| strict docs build + publish scan | `docs` job → `make docs-strict` | job step asserted by YAML parse; `make docs-strict` exit 0 locally |
| `tools/publish_scan_tests` (17) | `docs` job → `pytest tools/publish_scan_tests tools/docs_tests -q` | step index asserted lower than the gate step; 30 combined tests pass |
| `tools/docs_tests` (13) | same step | same |
| `tests/perf_gate` (21) | `test` job → `pytest tests -q -m "not postgres and not chroma"` | verified by running that exact marker filter against `tests/perf_gate`: 21 passed |

The bare `pytest tools/publish_scan_tests tools/docs_tests -q` form was verified to work without a
`PYTHONPATH` prefix: `tools/` is a package, so pytest's rootdir insertion puts the repo root on
`sys.path` — the same mechanism the lint job's existing `pytest tools/lints/tests -q` relies on.

## Verification

- `make docs-strict` exits 0, echoing pre-build scan → strict build → post-build scan in order.
- Negative test: a temporary symlink under `public/` made the target exit nonzero **at the
  pre-build step, before `mkdocs build` ran** (`pub03-symlink`); removed afterwards.
- `make ci` exits 0 end to end (lint, typecheck, full suite, ten examples, docs gate).
- `make help | grep docs-strict` names D-IMPL-72.
- `.github/workflows/ci.yml` parses; `jobs.docs` asserts clean on every criterion.
- `git diff --stat` on `perf.yml` and `live-legs.yml` is empty — both stay opt-in.
- `git status --porcelain` shows no `site/` — build output stayed ignored.
- Nav coverage re-derived rather than restated: **39 nav entries vs 40 `public/**/*.md` files**,
  the difference being `public/charter.md`, the single deliberate `not_in_nav` page. Every one of
  the 39 nav targets has a rendered `index.html` under `site/`. (Recorded as an observation.)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `tools/publish_scan.py` could not import `tools.lints` under the target's env**

- **Found during:** Task 1
- **Issue:** The Makefile's shared `ENV` is `PYTHONPATH=src:runtime`. The `lint` target works
  because `-m tools.lints` puts the cwd on `sys.path`; a *script* run (`python tools/publish_scan.py`)
  puts the script's own directory there instead, so `from tools.lints import format_finding` raised
  `ModuleNotFoundError` and the target died at step one.
- **Fix:** Added a dedicated `ENV_DOCS := PYTHONPATH=.:src:runtime` with a comment explaining the
  script-vs-`-m` distinction, and used it for the three `docs-strict` commands. `ENV` is unchanged,
  so no other target is affected.
- **Files modified:** `Makefile`
- **Commit:** 3bdbd1a

### Notes on declared intent

The plan's `files_modified` list was honoured exactly — `Makefile`, `.github/workflows/ci.yml`,
`public/index.md`, `public/charter.md`. The prompt raised the option of loosening
`PYTHON := .venv/bin/python` to `?=` for worktree robustness; that was **not** done. The worktree
was made workable by symlinking the primary `.venv` (an untracked, gitignored path), which required
no change to tracked files, so the Makefile edit would have been an unforced widening of scope on
the phase's final plan.

## Known Stubs

None.

## Threat Flags

None. No new network endpoint, auth path, file-access pattern or schema change at a trust boundary
was introduced; the changes tighten an existing boundary (built `site/` → uploaded artifact) rather
than opening one.

## Threat Model Dispositions

| Threat ID | Disposition | How it is realized |
|-----------|-------------|--------------------|
| T-14-49 | mitigated | No softening construct in the target recipe or the job, asserted programmatically; the job's comment block records the deliberate absence of `continue-on-error` |
| T-14-50 | mitigated | Build and both scans are one target with no independent invocation path; the CI job runs that one target |
| T-14-51 | mitigated | `upload-artifact` follows the gate step; a nonzero exit fails the job before the upload |
| T-14-52 | mitigated | The job has neither a `secrets:` key nor an `env:` block |
| T-14-53 | mitigated | `perf.yml` and `live-legs.yml` diffs empty; the docs job has no `if:` and no dispatch-only trigger |
| T-14-54 | mitigated | The gate's own tests run as their own CI step at a lower index than the gate |

## Self-Check: PASSED

- `Makefile` — FOUND, contains `ci: ci-core examples docs-strict` exactly once
- `.github/workflows/ci.yml` — FOUND, `jobs.docs` parses with 7 steps
- `public/charter.md` — FOUND, names `make docs-strict`
- `public/index.md` — FOUND, links all four sections
- `.planning/phases/14-documentation-suite/14-10-SUMMARY.md` — FOUND
- Commits 3bdbd1a, 6747cd8, dd55881 — all FOUND in `git log`
