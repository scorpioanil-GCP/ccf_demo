---
phase: 14
slug: documentation-suite
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-03
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Populated by the planner from `14-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (`testpaths = ["tests"]`) + `mkdocs build --strict` as an executable gate + `tools/publish_scan.py` as a blocking content gate |
| **Config file** | `pyproject.toml` (pytest, mypy, extras); `mkdocs.yml` (plan 14-01 creates); `perf/pytest.ini` (perf battery only) |
| **Quick run command** | `make docs && PYTHONPATH=. .venv/bin/python tools/publish_scan.py site` |
| **Full suite command** | `make ci` (after plan 14-10: `ci-core examples docs-strict`) |
| **Gate-test command** | `PYTHONPATH=src:runtime:. .venv/bin/python -m pytest tools/publish_scan_tests tools/docs_tests -q` — outside `testpaths`, run before the gate they implement (`src:runtime` on the path because `test_openapi_drift_control.py` imports the app's serialization helper) |
| **Estimated runtime** | `make docs` ~5 s; publish scan ~1 s (107,712 shingles built in 0.04 s); gate tests ~30 s (three subprocess builds plus two in-memory controls); `make ci` ~12 min |

> **Assertion-shape rule for every command in this document and in the plans.** An assertion's
> verdict is its **exit status**. `grep -c` and `grep -vc` exit 1 when the count is zero, so
> "`grep -c X` returns 0" and any pipeline ending `| grep -vc Y` are red exactly when the work is
> correct. Negative assertions are written `! grep -q ...` or `test -z "$(...)"`; count assertions
> wrap the count in `test ... -eq/-ge N`. A count that is only stated in prose (`... | wc -l` ≥ 8)
> is not an assertion at all and is rewritten into `test ... -ge N` form.
>
> **Three further shapes are banned by the same reasoning.** (1) A tail that exits 0 regardless of
> the condition — a chain ending in a bare `git status --porcelain` asserts nothing, because that
> command exits 0 dirty or clean; residue is asserted with `test -z "$(...)"`, or, where a parallel
> plan in the same wave may legitimately leave the tree dirty, by comparing a snapshot captured
> before the run against one captured after. (2) Non-POSIX constructs and external tools — no bash
> brace expansion inside `for ... in` (it degrades to a literal path under `sh` and the loop then
> silently passes), and no `bc` (not guaranteed present; its absence yields an empty string and a
> `test: integer expression expected`). (3) Variables defined only in prose — every variable a
> criterion references is captured by a command stated in that task's own action step.
>
> **A criterion may only assert over what its own task controls.** A task does not gate on a file
> another task owns, on a historical record it must not rewrite, or on an outcome a downstream
> checkpoint is entitled to decline. All ten plans were audited against every rule above, row by
> row, in the 2026-08-03 revision passes.

---

## Sampling Rate

- **After every task commit:** `make docs` + `tools/publish_scan.py site` (~6 s). Add `make lint`
  after any task touching `examples/`, `src/` or `runtime/`; add `pytest tests/http_api -q` when
  the OpenAPI check is touched.
- **After every plan wave:** `make ci-core` + `make docs-strict` (once 14-10 lands; before that,
  `make docs` plus both scan modes).
- **Before `/gsd:verify-work`:** `make ci` fully green, all four negative drift controls passing,
  and a manual read of the built site.
- **Max feedback latency:** ~6 s for the docs gate; ~12 min for the full sweep.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 14-01 T1 | 14-01 | 1 | DOCS-06 | T-14-03, T-14-05 | `site/` never committed; pinned deps only | unit | `.venv/bin/python -m mkdocs --version && grep -q '^site/$' .gitignore` | ❌ Wave 0 | ⬜ pending |
| 14-01 T2 | 14-01 | 1 | DOCS-02 | T-14-02 | zero symlinks under `public/`; no reference into `docs/` | unit | `test -z "$(find public -type l)"` | ❌ Wave 0 | ⬜ pending |
| 14-01 T3 | 14-01 | 1 | DOCS-02, DOCS-06 | T-14-01, T-14-04, T-14-06 | missing marker, dead link and dead identifier all fail the build | integration | `make docs` + three reverted probe edits | ❌ Wave 0 | ⬜ pending |
| 14-02 T1 | 14-02 | 1 | DOCS-02 | T-14-09, T-14-10, T-14-11, T-14-13 | no allowlist, no report-only mode; four rule tokens | unit | `PYTHONPATH=. python tools/publish_scan.py --pre-build` | ❌ Wave 0 | ⬜ pending |
| 14-02 T2 | 14-02 | 1 | DOCS-02 | T-14-12 | self-test fires on the whitepaper; controls both polarities | unit | `pytest tools/publish_scan_tests/test_publish_scan.py -q` | ❌ Wave 0 | ⬜ pending |
| 14-02 T3 | 14-02 | 1 | DOCS-02 | T-14-08, T-14-14 | zero quoting docstrings; every citation retained | unit | `pytest tools/publish_scan_tests/test_docstring_leaks.py -q && make lint && make typecheck` | ❌ Wave 0 | ⬜ pending |
| 14-03 T1 | 14-03 | 2 | DOCS-05 | T-14-17 | byte-stable deterministic dump | unit | `make openapi` twice, second leaves git clean | ✅ Makefile exists | ⬜ pending |
| 14-03 T2 | 14-03 | 2 | DOCS-05 | T-14-15, T-14-18, T-14-18b | route change fails always-on CI, message names the fix; the comparison still discriminates | unit + negative | `make test && PYTHONPATH=src:runtime:. pytest tools/docs_tests/test_openapi_drift_control.py -q` | ✅ `tests/http_api/test_openapi.py` | ⬜ pending |
| 14-04 T1 | 14-04 | 2 | DOCS-04, DOCS-05 | T-14-19, T-14-20, T-14-21, T-14-22 | only three named paths move; no dangling reference; includes unedited | integration | `make docs && tools/publish_scan.py --pre-build && tools/publish_scan.py site` | ❌ 14-01 | ⬜ pending |
| 14-04 T2 | 14-04 | 2 | DOCS-04 | — | CLAUDE.md edit is Dave-ruled, not silent | manual | checkpoint:decision | n/a | ⬜ pending |
| 14-05 T1 | 14-05 | 3 | DOCS-04 | T-14-24 | pillar prose from CLAUDE.md and code, not whitepaper text | integration | `make docs && tools/publish_scan.py site` | ❌ 14-01 | ⬜ pending |
| 14-05 T2 | 14-05 | 3 | DOCS-04 | T-14-23, T-14-25 | index is section numbers and titles only | unit + integration | `tools/publish_scan.py site` + `scan_text` on the index page | ❌ 14-02 | ⬜ pending |
| 14-05 T3 | 14-05 | 3 | DOCS-04 | T-14-26 | diagram bijection: none orphaned, none doubled | unit | `pytest tools/docs_tests/test_diagram_coverage.py -q` | ❌ Wave 0 | ⬜ pending |
| 14-06 T1 | 14-06 | 3 | DOCS-02 | T-14-27, T-14-28, T-14-29 | no hand-written signature; no excluded internal; no `show_source` override | integration | `make docs && tools/publish_scan.py site` | ❌ 14-01 | ⬜ pending |
| 14-06 T2 | 14-06 | 3 | DOCS-03, DOCS-05 | T-14-31, T-14-32 | every model renders a generated schema; spec included whole | integration | `make docs && test "$(grep -rl 'Show JSON schema' site/reference/artifacts \| wc -l)" -ge 8` | ❌ 14-01 | ⬜ pending |
| 14-06 T3 | 14-06 | 3 | DOCS-02 | T-14-30 | a renamed Protocol fails the build | negative | `pytest tools/docs_tests/test_mkdocstrings_gate.py -q` | ❌ Wave 0 | ⬜ pending |
| 14-07 T1 | 14-07 | 3 | DOCS-01 | T-14-36 | markers are comments only; examples still green | unit | `make lint && make examples && test -z "$(git diff -U0 -- examples \| grep '^[+-]' \| grep -v '^[+-][+-]' \| grep -v '8<--')"` | ✅ examples exist | ⬜ pending |
| 14-07 T2 | 14-07 | 3 | DOCS-01 | T-14-33, T-14-35, T-14-37 | zero pasted code; every include from `examples/` | integration | `make docs && tools/publish_scan.py site` | ❌ 14-01 | ⬜ pending |
| 14-07 T3 | 14-07 | 3 | DOCS-01 | T-14-34 | deleted marker AND missing file each fail the build; no repo-tree residue | negative | `pytest tools/docs_tests/test_snippet_gate.py -q && test "$(git status --porcelain public/ examples/ mkdocs.yml)" = "$SNIPPET_GATE_BEFORE"` | ❌ Wave 0 | ⬜ pending |
| 14-08 T1 | 14-08 | 3 | DOCS-04 | T-14-42 | markers are comments only | unit | `make lint && make examples && test -z "$(git diff -U0 -- examples \| grep '^[+-]' \| grep -v '^[+-][+-]' \| grep -v '8<--')"` | ✅ examples exist | ⬜ pending |
| 14-08 T2 | 14-08 | 3 | DOCS-04 | T-14-40, T-14-41 | every page narrates a green CI-run example | integration | `make docs && tools/publish_scan.py site` | ❌ 14-01 | ⬜ pending |
| 14-08 T3 | 14-08 | 3 | DOCS-05 | T-14-38, T-14-39 | no key-shaped literal; substance unrewritten (`$BEFORE` captured by a stated command in the action step) | integration | `make docs && tools/publish_scan.py site` + key-literal grep | ❌ 14-04 | ⬜ pending |
| 14-09 T1 | 14-09 | 3 | DOCS-06 | T-14-46, T-14-48 | gate has no write path to baselines; medians plausible | integration | `make perf CCF_PERF_RUNNER_CLASS=local && pytest tests/perf_gate -q` | ✅ perf suite exists | ⬜ pending |
| 14-09 T2 | 14-09 | 3 | DOCS-06 | T-14-43 | no baseline recorded without Dave's approval | manual | checkpoint:human-verify | n/a | ⬜ pending |
| 14-09 T3 | 14-09 | 3 | DOCS-06 | T-14-44, T-14-45 | numbers included from the committed file, never transcribed | integration | `make docs && git ls-files --error-unmatch perf/baselines/local.json` | ❌ 14-01 | ⬜ pending |
| 14-10 T1 | 14-10 | 4 | DOCS-06 | T-14-49, T-14-50 | one blocking target; pre-build scan runs first | integration | `make docs-strict && make ci` | ❌ 14-02 | ⬜ pending |
| 14-10 T2 | 14-10 | 4 | DOCS-06 | T-14-51, T-14-52, T-14-53, T-14-54 | always-on, no secrets, upload after the gate, gate tests first | unit | YAML-parse assertion on `jobs.docs` | ✅ `ci.yml` exists | ⬜ pending |
| 14-10 T3 | 14-10 | 4 | DOCS-06 | — | charter names the enforcement that exists; nav and file counts re-derived, never restated | integration | `make docs-strict && make ci` | ❌ 14-01 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Per research, Wave 0 must land before any drift gate can go green. Waves 1 and 2 of this plan set
constitute Wave 0:

- [ ] `mkdocs.yml` at repo root with `check_paths: true` (D-08 in its entirety) and raised
      `validation.links.*` levels — plan 14-01 Task 3
- [ ] `public/` tree with charter, index and every nav-backed stub — plan 14-01 Task 2
- [ ] `docs` dependency extra in `pyproject.toml`, composed into `dev` — plan 14-01 Task 1
- [ ] `site/` added to `.gitignore` — plan 14-01 Task 1
- [ ] `tools/publish_scan.py` — the DOCS-02 never-publish criterion — plan 14-02 Task 1
- [ ] `tools/publish_scan_tests/` — the gate's own controls and self-test — plan 14-02 Task 2
- [ ] Rework of the 13 whitepaper-quoting docstrings — **blocks the first green publish scan** —
      plan 14-02 Task 3
- [ ] `tools/dump_openapi.py` + `openapi.json` + `make openapi` — DOCS-05's stored baseline —
      plan 14-03
- [ ] `tools/docs_tests/` package marker — plan 14-01 Task 2; the five committed negative drift
      controls land in plans 14-03, 14-05, 14-06 and 14-07

---

## Negative Drift Controls (the phase's core assertion)

| Drift class | Violating case | Clean case | Owner |
|---|---|---|---|
| deleted snippet marker | source copy with `[start:x]` stripped → strict build nonzero | unmodified tree → exit 0 | 14-07 T3 |
| missing snippet file | include of a nonexistent path → nonzero | valid path → exit 0 | 14-07 T3 |
| renamed / removed Protocol | `::: ccf.does.not.Exist` and a near-miss rename → nonzero | every curated `:::` resolves | 14-06 T3 |
| changed OpenAPI endpoint | `tools/docs_tests/test_openapi_drift_control.py` mutates an in-memory copy of the spec and asserts the comparison helper reports a difference — standing, run every time | the unmutated copy compares equal; the committed file matches `create_app()` | 14-03 T2 |
| leaked whitepaper text | scanner fed the whitepaper fires (self-test) | fed the two moved pages → zero | 14-02 T2 |
| orphaned diagram | an unreferenced `.mmd` → test fails | bijection holds | 14-05 T3 |

Assert polarities, never the measured counts — counts move when the whitepaper is edited, the
polarities do not.

Every one of the six controls is a **committed executable test** exercising the failing polarity on
every run. None is a one-time reverted acceptance probe: a probe proves the gate worked once, and
nothing standing then proves it still discriminates after a later refactor. The OpenAPI row was the
last exception and was closed in the 2026-08-03 revision pass by
`tools/docs_tests/test_openapi_drift_control.py`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dave approves the measured baseline before PERFORMANCE.md cites it | DOCS-06 | D-IMPL-70 makes recording a baseline a Dave-gated act; no automation may substitute for the approval | Plan 14-09 Task 2: read `perf/baselines/local.json`, compare wall times against `perf/README.md`'s budget table, confirm the runner class, supply the approval reference |
| The CLAUDE.md skeleton edit for the D-03 move | DOCS-04 | CLAUDE.md is the canonical project document; D-03 authorizes the edit but `public/` is a new top-level tree the skeleton does not list | Plan 14-04 Task 2: review the four-hunk diff, choose apply-now, defer-to-gate, or revise |
| The docs job runs green on Actions and the artifact is downloadable and readable | DOCS-06 | First observed run on origin; cannot be asserted locally | After plan 14-10 merges, observe the `docs` job and download `ccf-docs-site`. Mermaid diagrams render only with network access (CDN-loaded at view time) — a blank diagram in an offline artifact is expected, not a defect |
| The site reads as an adoption path end to end | DOCS-01 | Narrative quality is not machine-checkable | Read `public/index.md` → adopter's guide → one pillar → its Reference surface, and confirm the path holds without needing any file in `docs/` |

---

## Validation Sign-Off

- [x] All tasks have an `<automated>` verify or are explicit blocking checkpoints (14-04 T2, 14-09 T2)
- [x] Every automated verify and acceptance criterion audited for inverted or non-deterministic exit
      status (`grep -c`, `grep -vc`, unwrapped `wc -l`, pipelines whose status comes from the wrong
      stage) — 2026-08-03 revision pass
- [x] Every row of the Per-Task Verification Map re-audited against the assertion-shape rule stated
      above, including the prose-only `≥ N` and boolean-`grep -c` shapes — 2026-08-03 revision pass 2
- [x] No criterion asserts over a file its task does not own, a historical approval record, or an
      outcome a checkpoint may decline — 2026-08-03 revision pass 2
- [x] No vacuous assertion tail (a command exiting 0 regardless of the condition), no bare page-count
      literal that a later plan invalidates, no `bc` or bash brace expansion inside `for`, and no
      prose-defined variable — 2026-08-03 revision pass 2
- [x] Sampling continuity: no 3 consecutive tasks without an automated verify
- [x] Wave 0 covers all MISSING references (plans 14-01, 14-02, 14-03)
- [x] No watch-mode flags (`mkdocs serve` is the only watch surface and is excluded from `ci` by design)
- [x] Feedback latency < 10 s for the per-task docs gate
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
