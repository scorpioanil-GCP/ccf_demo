---
phase: 04-phase-i-1-fabric-core
plan: 01
subsystem: scaffold
tags: [packaging, ci, governance]
requires: []
provides:
  - ccf + ccf_runtime installable packages (editable, .venv)
  - pytest/mypy configuration with markers postgres/chroma/conformance
  - GitHub Actions CI (blocking lint job + postgres-service test matrix)
  - D-IMPL-52 ruling logged; CLAUDE.md §9 and ROADMAP criterion 4 amended
affects:
  - every subsequent Phase 4 plan installs, tests, and lints against this scaffold
  - plan 04-02 must land `tools/lints` (CI lint job is red until it does — by design, D-07)
tech-stack:
  added:
    - pydantic==2.13.4
    - pyyaml==6.0.3
    - sqlite-vec==0.1.9
    - "psycopg[binary]==3.3.4"
    - chromadb==1.5.9 (optional extra `chroma` only)
    - pytest==9.1.1, hypothesis==6.161.5, testcontainers==4.15.0, mypy==2.3.0, pytest-cov==7.1.0 (dev extra)
  patterns:
    - single v0 distribution shipping two packages via `packages.find where = ["src", "runtime"]`
key-files:
  created:
    - pyproject.toml
    - .github/workflows/ci.yml
    - src/ccf/__init__.py
    - runtime/ccf_runtime/__init__.py
    - tests/conftest.py
    - tests/test_smoke.py
  modified:
    - .gitignore
    - CLAUDE.md
    - docs/DECISIONS.md
    - .planning/ROADMAP.md
decisions:
  - "D-IMPL-52 (Dave, 2026-07-25): v0 examples suite is a horizontal mix of domains; example 00 and the I.1 slice fixtures are banking — replaces CLAUDE.md §9's single-neutral-domain rule"
  - "D-12 scope amendment recorded on ROADMAP Phase 4 criterion 4: I.1 ships ArtifactStore Protocol + file-backed dev impl only; MCP-backed reference impl moves to Phase 6 (I.3)"
  - "Single distribution (not two) for the ccf/ccf_runtime split — D-05 left this to Claude's discretion; one pyproject is simpler and both packages import cleanly"
  - "Assumption A1 resolved empirically: mypy 2.3.0 `--strict` flag surface is unchanged from the 1.x expectation"
metrics:
  duration: ~12 min
  completed: 2026-07-25
  tasks: 3
  commits: 3
---

# Phase 4 Plan 01: Phase I.1 Scaffold Summary

Bootstrapped Phase I.1 on branch `phase-i1`: an editable-installable `ccf` +
`ccf_runtime` distribution with strict-typed, marker-aware test configuration,
a GitHub Actions workflow whose lint step blocks from the first fabric commit,
and the three governance-doc amendments Dave's D-03/D-12 rulings owed.

## What Was Built

**Task 1 — packaging and test scaffold** (`c87eb11`). Branched `phase-i1` from
`main` per CLAUDE.md §2.2. `pyproject.toml` declares one v0 distribution
shipping both packages (`packages.find` over `where = ["src", "runtime"]`),
with every runtime pin taken verbatim from the 04-RESEARCH.md Standard Stack
and `chromadb` confined to the `chroma` extra so its transitive tree
(onnxruntime, opentelemetry, kubernetes) never enters a core install. pytest
gets `testpaths` plus the three markers (`postgres`, `chroma`, `conformance`);
mypy is strict over `src`. Package roots carry docstrings citing CLAUDE.md
§10/§7.3 and hold no logic. A `.venv` was created (host pip is PEP-668
externally managed) and the package installed editable with dev extras.

**Task 2 — CI workflow** (`52d7f65`). Two jobs. `lint` runs
`python -m tools.lints --all` and `mypy --strict src`; the lints runner lands
in plan 04-02, so this job is red on the branch until then — intentional,
since D-07 forbids making the step non-blocking to hide the gap. `test` runs a
`postgres:16` service container with a `pg_isready` health check, exports
`CCF_TEST_POSTGRES_DSN` for the D-16 conformance suite, and splits the quick
leg (marker-excluded) from the postgres leg (vacuously passing today). Coverage
is reported informationally with no `--cov-fail-under`, per D-17.

**Task 3 — governance amendments** (`61fdca0`). CLAUDE.md §9's "one coherent
neutral domain" bullet is replaced by the horizontal-mix policy naming banking
for example 00 and the I.1 slice fixtures, while preserving the constraints
that survive (no domain packs; domain values in artifacts, never example code).
`docs/DECISIONS.md` gains D-IMPL-52 in the established entry format. ROADMAP
Phase 4 criterion 4 now carries a visible scope-amendment callout rather than a
silent edit, so the gate review verifies the amended criterion.

## Key Implementation Details

- Two packages ship from one distribution rather than two. D-05 left this to
  discretion; a second `runtime/pyproject.toml` would have bought nothing at v0
  and doubled the install story for every downstream plan.
- The CI lint job is knowingly red until 04-02. Recording this in the workflow
  comment keeps a later reader from "fixing" it by making the step advisory,
  which would silently void D-07.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `readme = "README.md"` referenced a nonexistent file**
- **Found during:** Task 1
- **Issue:** The repo has no `README.md`; the editable install would fail on the
  missing readme target.
- **Fix:** Dropped the `readme` field from `[project]`. Creating a README was
  out of the plan's file scope and belongs to a docs plan, not the scaffold.
- **Files modified:** `pyproject.toml`
- **Commit:** `c87eb11`

**2. [Rule 2 - Missing critical functionality] Deferred MCP ArtifactStore had no receiving deliverable**
- **Found during:** Task 3
- **Issue:** The plan directed amending Phase 4 criterion 4 to defer the
  MCP-backed ArtifactStore to Phase 6, but the ROADMAP's Phase 6 section named
  no ArtifactStore deliverable at all. Deferring work into a phase that does not
  claim it loses the work — and Phase 8 example 07 (file-backed → MCP-backed
  swap) depends on it existing.
- **Fix:** Added Phase 6 success criterion 5 requiring the MCP-backed reference
  impl to pass the same shared conformance suite, annotated as inherited from
  the Phase 4 D-12 amendment.
- **Files modified:** `.planning/ROADMAP.md`
- **Commit:** `61fdca0`

## Verification

| Check | Result |
|---|---|
| `git branch --show-current` | `phase-i1` |
| `.venv/bin/python -c "import ccf, ccf_runtime"` | exit 0, both resolve to the source tree |
| `.venv/bin/pytest tests -q` | 2 passed, 0 failures |
| `.venv/bin/mypy --strict src` | Success: no issues found |
| `ci.yml` YAML parse, jobs `lint`+`test`, postgres present | ok |
| `grep -c "tools.lints" ci.yml` | 2 (≥1 required) |
| coverage gate present | none (D-17 satisfied) |
| Task 3 doc-edit grep chain | VERIFY OK |

## Known Stubs

None. Both package roots are intentionally empty packaging roots (declared as
such in their docstrings), not stubbed functionality; `tests/conftest.py` is a
declared placeholder whose real fixtures land with their subsystem plans.

## Self-Check: PASSED

All six created files exist on disk; all three commit hashes (`c87eb11`,
`52d7f65`, `61fdca0`) are present in `git log` on `phase-i1`.
