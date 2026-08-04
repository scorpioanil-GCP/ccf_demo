---
phase: 14-documentation-suite
plan: 04
subsystem: docs
tags: [docs-site, publish-boundary, d-03, mkdocs]
requires:
  - "14-01: public/ tree, mkdocs.yml, tools/publish_scan.py"
provides:
  - "public/tutorial/demo-walkthrough.md — DEMO-03 narrated walkthrough as the Tutorial page"
  - "public/how-to/security-and-deployment.md — DOCS-05 security/deployment notes as a How-to page"
  - "public/diagrams/ — the eleven Phase D architecture diagrams at their published home"
affects:
  - "docs/ now holds only never-publish content plus the whitepaper figure PNGs"
  - "CLAUDE.md §3 and §14 name public/diagrams and list /public in the skeleton"
tech-stack:
  added: []
  patterns:
    - "git mv for every relocation so --follow history survives the publish-boundary move"
    - "repo-root-relative snippet includes survive relocation unchanged under base_path: ['.']"
key-files:
  created: []
  modified:
    - public/tutorial/demo-walkthrough.md
    - public/how-to/security-and-deployment.md
    - public/diagrams/*.mmd
    - mkdocs.yml
    - README.md
    - docs/DESIGN.md
    - examples/08-e2e-demo/README.md
    - tools/publish_scan_tests/test_publish_scan.py
    - CLAUDE.md
decisions:
  - "D-03 executed: one home per file — the walkthrough, the security notes and all eleven diagrams move out of docs/ into public/, with no duplication and no sync question"
  - "Dave, 2026-08-03: apply-as-proposed — the CLAUDE.md skeleton/reference edit lands inside this plan rather than deferring to the Phase 14 gate"
metrics:
  duration: ~25m
  tasks: 2
  completed: 2026-08-03
requirements: [DOCS-04, DOCS-05]
---

# Phase 14 Plan 04: Execute the D-03 Move Summary

The two publishable documents and the whole eleven-file diagram tree moved out of `docs/` into
`public/` with `git mv` so history follows, every inbound reference outside `.planning/` was
repointed, and the two nav entries plan 14-01 deliberately withheld are now in `mkdocs.yml`.

## What Was Built

**Task 1 — the move and the repoint** (commit `1aad0b6`)

Three relocations, all via `git mv`:

| From | To |
| --- | --- |
| `docs/demo-walkthrough.md` | `public/tutorial/demo-walkthrough.md` |
| `docs/security-notes.md` | `public/how-to/security-and-deployment.md` |
| `docs/diagrams/` (11 `.mmd`) | `public/diagrams/` |

`docs/figures/` — the 27 whitepaper figure PNGs — did not move, as required.

The walkthrough's ten `--8<--` snippet include paths were **not touched**. They are
repo-root-relative, and with `mkdocs.yml` at the repo root under `base_path: ["."]` all ten resolve
unchanged across the move — exactly what the page's Phase 12 header comment anticipated. That stale
header comment (which prescribed a `base_path: [".."]` that is now wrong) was replaced with a
one-line pointer to `mkdocs.yml`, keeping its closing sentence that nothing on the page pastes code
and the doc always shows the exact files CI runs — the DOCS-01 non-goal restated.

The security page took a level-1 heading matching its new How-to role
(`# Manage keys and secrets when deploying (v0)`, was `# Security Notes — Key Management (v0)`).
Its substance is unchanged: Phases 9 and 10 authored it and it is factual to shipped mechanism.

Inbound references repointed: `README.md` line 85; `docs/DESIGN.md` (31 occurrences across the
eight pillar/seam mapping rows, the prose references, and the invariant table);
`examples/08-e2e-demo/README.md` trailing link. Everything under `.planning/` and the `D-GATE-D`
entry at `docs/DECISIONS.md:227` were left alone — those are historical approval records and
rewriting them would falsify an approval.

Two nav entries added: the walkthrough under `Tutorial` after the adopter's guide, and the security
page as the first `How-to` entry (D-17 placement). The nav header comment's page count was updated
from 37/38 to 39/40 to stay accurate.

**Task 2 — the CLAUDE.md ruling** (commit `3bbc163`)

The exact proposed diff was rendered verbatim — all four hunks, as three diff blocks — and the
question was asked before any edit was applied. `CLAUDE.md` was left unmodified during the pause.

**Dave's ruling, 2026-08-03: `apply-as-proposed`.** The diff was applied exactly as presented, with
no wording changes:

1. §3 Phase D deliverable line (~162): `docs/diagrams/` → `public/diagrams/`
2. §14 directory skeleton (~1227): `/docs/diagrams` replaced by a `/public` entry describing D-01
   (the published surface, default-deny by existence, the only tree mkdocs reads) plus
   `/public/diagrams`
3. §14 one-diagram-per-pillar instruction (~1248): `docs/diagrams/` → `public/diagrams/`

`! git grep -q 'docs/diagrams' CLAUDE.md` holds.

## Verification

All Task 1 acceptance criteria pass:

- `! test -d docs/diagrams` and `test "$(ls public/diagrams/*.mmd | wc -l)" -eq 11` — pass
- `! test -f docs/demo-walkthrough.md`, `! test -f docs/security-notes.md` — pass
- `test -d docs/figures` — pass, the whitepaper figures did not move
- `git log --follow --oneline public/tutorial/demo-walkthrough.md | wc -l` = 2 (`-gt 1`) — history followed
- `! git grep -qE 'docs/diagrams|docs/demo-walkthrough|docs/security-notes'` under the plan's
  pathspec — pass, no dangling reference
- `grep -q 'public/diagrams' README.md`; `grep -c 'public/diagrams' docs/DESIGN.md` = 31 (`-ge 8`) — pass
- `grep -q 'public/tutorial/demo-walkthrough.md' examples/08-e2e-demo/README.md` — pass
- `grep -c -- '--8<--' public/tutorial/demo-walkthrough.md` = 10 — every include survived untouched
- mkdocs build exits 0; `site/tutorial/demo-walkthrough/index.html` (420 KB) and
  `site/how-to/security-and-deployment/index.html` both exist non-empty
- `publish_scan.py --pre-build` exits 0 — no include in `public/` reaches `docs/` or `.planning/`,
  no symlink created
- `publish_scan.py site` exits 0 — both moved pages scan-clean in the built tree, matching the
  measured negative controls
- `pytest tools/publish_scan_tests` — 17 passed

Task 2 acceptance criteria pass: the diff was displayed verbatim before the question; the ruling was
`apply-as-proposed`; `! git grep -q 'docs/diagrams' CLAUDE.md` holds; the ruling, its date, and the
selected option are recorded above.

All verification was re-run after the CLAUDE.md edit landed and remains green.

Note on tooling: `make docs` invokes `.venv/bin/python`, which does not exist in this worktree. The
equivalent was run with the primary interpreter at `/home/parkave/ccf_code/.venv/bin/python` with
`PYTHONPATH` set explicitly from the worktree root, so the build and both scans tested this
worktree's tree. No change was made to the Makefile.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Repointed the publish-scan negative-control paths**

- **Found during:** Task 1
- **Issue:** `tools/publish_scan_tests/test_publish_scan.py:104`
  (`test_the_two_moved_public_docs_are_shingle_clean`) read the two documents at their old `docs/`
  paths as the measured shingle-clean negative control. The move would have left the test reading
  files that no longer exist, breaking a test the plan's own threat register (T-14-21) depends on
  for its mitigation.
- **Fix:** repointed the tuple to `public/how-to/security-and-deployment.md` and
  `public/tutorial/demo-walkthrough.md`. The assertion itself is unchanged and still passes.
- **Files modified:** `tools/publish_scan_tests/test_publish_scan.py`
- **Commit:** `1aad0b6`

This file is not in the plan's `files_modified` list, but it is squarely in Task 1's scope: it is an
inbound reference to a moved path, and Task 1's own acceptance criterion
(`! git grep -qE 'docs/demo-walkthrough|docs/security-notes' -- .` with a pathspec that does not
exclude `tools/`) could not have passed without it.

**2. [Rule 1 - Bug] Removed a literal include token from the new header comment**

- **Found during:** Task 1
- **Issue:** the first replacement header comment used the literal `--8<--` token in its prose (as
  the original comment had), which pushed
  `grep -c -- '--8<--' public/tutorial/demo-walkthrough.md` to 11 and failed the exactly-10
  acceptance criterion. The count is the plan's proxy for "no include was edited during the move"
  (threat T-14-20), so an inflated count defeats the check.
- **Fix:** reworded to "every literal include below" — no token, count back to exactly 10.
- **Files modified:** `public/tutorial/demo-walkthrough.md`
- **Commit:** `1aad0b6`

### Nav header comment count

`mkdocs.yml`'s nav comment asserted "37 pages ... for the 38 files under `public/`". With two pages
added it now reads 39/40, with a clarifying note that the eleven `.mmd` diagram sources under
`public/diagrams/` are embedded by the Concepts pages rather than being nav entries. Verified:
`find public -name '*.md' | wc -l` = 40.

## Known Stubs

None.

## Threat Flags

None. The move relocates existing content across an already-established publish boundary; both
post-move scan modes exit 0 and no new network, auth, file-access, or schema surface was introduced.

## Commits

| Commit | Description |
| --- | --- |
| `1aad0b6` | Move publishable docs and diagrams into `public/` (D-03); repoint all inbound references; add two nav entries |
| `3bbc163` | Repoint CLAUDE.md at `public/diagrams` and add `/public` to the §14 skeleton (Dave, 2026-08-03, apply-as-proposed) |

## Self-Check: PASSED

- `public/tutorial/demo-walkthrough.md` — FOUND
- `public/how-to/security-and-deployment.md` — FOUND
- `public/diagrams/` — FOUND, 11 `.mmd` files
- `docs/figures/` — FOUND (correctly unmoved)
- commit `1aad0b6` — FOUND
- commit `3bbc163` — FOUND
