---
phase: 14-documentation-suite
plan: 01
subsystem: docs-toolchain
tags: [mkdocs, docs, build, publish-boundary]
requires: []
provides:
  - "mkdocs.yml at the repo root with strict validation and check_paths closed"
  - "public/ docroot with the D-06 charter, index, and 36 stub pages"
  - "`docs` dependency extra composed into `dev`"
  - "`make docs` / `make docs-serve` targets"
  - "tools/docs_tests/ package marker"
affects:
  - "pyproject.toml [project.optional-dependencies]"
  - "Makefile .PHONY and target list"
  - ".gitignore"
tech-stack:
  added:
    - mkdocs==1.6.1
    - mkdocs-material==9.7.7
    - mkdocstrings[python]==1.0.6
    - mkdocstrings-python==2.0.5
    - pymdown-extensions==11.0.1
    - griffe-pydantic==1.3.1
  patterns:
    - "Exact == pins with a comment naming the ruling that added the group"
    - "Self-referential `ccf[docs]` composition into `dev`"
    - "Every mkdocs.yml tuning knob carries a D-NN / Pitfall citation"
key-files:
  created:
    - mkdocs.yml
    - public/README.md
    - public/index.md
    - "public/**/*.md (36 stubs)"
    - tools/docs_tests/__init__.py
  modified:
    - pyproject.toml
    - .gitignore
    - Makefile
decisions:
  - "MkDocs aliases README.md to index.md; `not_in_nav` cannot silence the resulting conflict warning, so the charter is `exclude_docs`'d — research assumption A5 falsified"
metrics:
  duration: ~35 min
  completed: 2026-08-03
---

# Phase 14 Plan 01: Docs Toolchain and Strict Build Summary

A strict-by-default MkDocs build now exists at the repo root, reads only
`public/`, and demonstrably fails on a missing snippet section and on a dead
internal link — the single gate every later plan in this phase hangs on.

## What Was Built

**Task 1 — dependency extra, gitignore, make targets** (`2e0c0aa`)

- `pyproject.toml`: a `docs` optional-dependency group with six exact `==`
  pins and a comment naming D-IMPL-71 and the MkDocs-2.0 rationale (2.0 is an
  announced backward-incompatible rewrite with no migration path and all
  plugins removed, so `>=` would break the gate the day it lands). `"ccf[docs]"`
  joins `dev`, so no existing CI job's install step changes.
- `.gitignore`: `site/` with the local one-line cited-comment style.
- `Makefile`: `docs` and `docs-serve` targets plus the `.PHONY` group. The
  `ci:` line is untouched — `docs-strict` and the D-IMPL-72 composition belong
  to plans 14-02 and 14-10.

**Task 2 — the `public/` docroot** (`9b9774c`)

38 Markdown files: the D-06 never-publish charter, a purpose-written landing
page naming the five pillars and linking the four Diátaxis sections, and 36
stubs — one behind every nav entry Task 3 declares. Zero symlinks. No page
outside the charter references the internal deliverable tree. Also
`tools/docs_tests/__init__.py`, following the `tools/lints/tests/` precedent of
a real package outside `testpaths`.

**Task 3 — `mkdocs.yml`** (`dd9bdf9`)

Both silently-permissive defaults are explicitly closed, each with its
citation: `pymdownx.snippets.check_paths: true` (D-08 in its entirety) and the
full `validation:` block at `warn` (the levels default to `info`, which
`--strict` cannot promote). `show_source: false` is annotated as a
publish-safety control, not aesthetics. The nav enumerates all 37 page paths
explicitly, no globs, and the nav count is asserted against the file count so
the two cannot drift apart silently.

### Empirical verification (temporary, reverted probes)

| Probe | Result |
|---|---|
| `--8<-- "examples/00-quickstart/run.py:does-not-exist"` | exit 2, `Snippet section 'does-not-exist' could not be located` |
| `[dead](nope.md)` | exit 2, `the target is not found among documentation files` |
| `::: ccf.products.contract.ContextProductContract` | exit 0, two built pages carry a `Show JSON schema` block (research A2 confirmed on a real repo model) |

`git status --porcelain public/` clean afterwards.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] No `.venv` in the parallel worktree**

- **Found during:** Task 1
- **Issue:** `.venv` is gitignored and therefore absent from the worktree, so
  `.venv/bin/pip install -e ".[dev]"` failed with exit 127.
- **Fix:** Created the venv (`python3 -m venv .venv`) and ran the plan's own
  install command into it. No package substitution occurred; all six docs pins
  resolved exactly as specified.
- **Commit:** n/a (untracked build environment)

**2. [Rule 1 - Bug] Research assumption A5 falsified — `not_in_nav` cannot publish `public/README.md`**

- **Found during:** Task 3
- **Issue:** MkDocs 1.6 treats `README.md` as an alias for `index.md`. With
  both present it emits `Excluding 'README.md' from the site because it
  conflicts with 'index.md'` — a WARNING, therefore fatal under `strict: true`.
  `not_in_nav` cannot silence it, because the file never becomes a page at all.
  The first `make docs` aborted on exactly this.
- **Fix:** Added `exclude_docs: | README.md`, which removes the file before the
  conflict is evaluated. The charter stays committed and readable where it
  actually governs — the source tree — exactly like its named precedent
  `examples/external/README.md`, which is likewise not a published page. This
  strictly shrinks the published surface, which D-01 prefers. The `not_in_nav`
  entry is retained, with a comment explaining both.
- **Impact on must_haves:** the truth "`public/README.md` is published but
  absent from the nav" is superseded — it is **committed** and absent from both
  nav and the built site. The `artifacts` check (`public/README.md` contains
  `never-publish`) is satisfied unchanged. Flagged for the phase reviewer since
  it is a stated must_have, not a silent reinterpretation.
- **Files modified:** `mkdocs.yml`
- **Commit:** `dd9bdf9`

### Plan assertion defects (work is correct; the assertion was not)

- `make help | grep -qE '^docs +'` — `make help` prefixes every line with two
  spaces (`printf "  %-28s %s\n"`), so an anchored `^docs` can never match.
  Verified with the equivalent `^ *docs +`; both `docs` and `docs-serve` appear
  with non-empty descriptions.
- `git grep -q 'ci: ci-core examples$' Makefile` — the real line carries a
  trailing `## ` help string, so `$` never matches. The intent (the `ci:` line
  untouched) was verified from `git diff -- Makefile`: exactly one line removed,
  the `.PHONY` continuation, and it is re-added with `docs docs-serve` appended.

## Verification

- `make docs` exits 0; `site/index.html` exists.
- `make lint` — green.
- `make typecheck` — `Success: no issues found in 161 source files`.
- `make test` — `1513 passed, 22 skipped in 265.31s`.
- All Task 1 / Task 2 / Task 3 acceptance criteria pass (with the two assertion
  defects above corrected in form, not in intent).

## Known Stubs

36 pages under `public/` are intentional stubs — a `# Title` plus a sentence
naming the plan that fills it. This is the plan's design: every later plan
fills a page that already has a nav entry, so no later plan contends on
`mkdocs.yml`. Fill-in ownership: 14-05 (concepts, 8), 14-06 (reference, 21),
14-07 (tutorial, 1), 14-08 (how-to, 5), 14-09 (performance, 1).

## Threat Flags

None. No new network endpoint, auth path, or schema was introduced; the six
new dependencies are build-time only and were slopcheck-audited in 14-RESEARCH
(7/7 `[OK]`).

## Self-Check: PASSED

- `mkdocs.yml`, `public/README.md`, `public/index.md`, `tools/docs_tests/__init__.py` — all present.
- Commits `2e0c0aa`, `9b9774c`, `dd9bdf9` — all present in `git log`.
