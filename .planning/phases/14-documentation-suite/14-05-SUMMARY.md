---
phase: 14-documentation-suite
plan: 05
subsystem: documentation
tags: [docs, concepts, pillars, invariants, replay, diagrams]
requires: ["14-01", "14-04"]
provides:
  - "public/concepts/** — the eight-page Concepts section"
  - "tools/docs_tests/test_diagram_coverage.py — diagram bijection assertion"
affects:
  - "mkdocs nav Concepts subtree (no config change)"
tech-stack:
  added: []
  patterns:
    - "mermaid fence whose only content is a pymdownx.snippets include of the .mmd — single artifact, no Node toolchain in CI"
    - "Markdown reference-style link definitions for cross-tree links"
key-files:
  created:
    - tools/docs_tests/test_diagram_coverage.py
  modified:
    - public/concepts/pillars/data-context.md
    - public/concepts/pillars/orchestration.md
    - public/concepts/pillars/agent-types.md
    - public/concepts/pillars/hitl.md
    - public/concepts/pillars/experience.md
    - public/concepts/invariants.md
    - public/concepts/replay-anatomy.md
    - public/concepts/whitepaper-index.md
decisions:
  - "Cross-tree links written as Markdown reference-style definitions rather than inline `](../../...)`, so both of the plan's mutually-tense link criteria hold literally"
  - "Long whitepaper section titles given in short form in the D-18 index; the publish scan fires on full titles, and the scan is the arbiter"
metrics:
  duration: ~45m
  completed: 2026-08-03
requirements: [DOCS-04]
---

# Phase 14 Plan 05: Concepts section Summary

Eight Concepts pages written — five pillar pages, invariants, replay anatomy,
and the D-18 whitepaper cross-reference index — with all eleven Phase D
diagrams embedded exactly once from their `.mmd` sources, and a standing test
that keeps the bijection true.

## Tasks

| Task | Name | Commit |
| --- | --- | --- |
| 1 | The five pillar pages | `a96ee23` |
| 2 | Invariants, replay anatomy, whitepaper index | `9c9aafb` |
| 3 | The diagram-coverage test | `100c572` |

## What was built

**The five pillar pages** each follow the same three-part shape: prose stating
the pillar's purpose and SDK realization written out from CLAUDE.md §4 (not
transcluded), a narrated diagram embedded via a snippet include inside a
`mermaid` fence, and a "Where this lives" section linking down to the Reference
surfaces that realize the pillar. The two seam diagrams landed on the pages
whose seam they show — `seam-artifact-store` on data-context,
`seam-harness-adapter` on agent-types.

**`invariants.md`** has one section per named invariant from CLAUDE.md §11,
each stating the promise, why the architecture forces it, and the concrete
enforcement — the specific `tools.lints` rule invocation for the three
lint-enforced ones, boot-time DI and the reader/writer protocol split for
single-writer, the gate runner's construction monopoly for the three validation
gates, and the ordering of the replay write ahead of the state transition for
audit-by-construction. Admission through assembly is broken out as its own
section so `seq-a2a-admission` sits where it belongs.

**`replay-anatomy.md`** names the five dimensions with their real field names
as they appear in `src/ccf/replay/record.py` — `ContextFabricSnapshot`,
`PolicyBindingsSnapshot`, `ModelVersionRecord`, `PerspectiveConditioning`,
`ContentGenerationPath`, and the SDK extensions `hitl_actions`,
`workflow_step_sequence`, `agent_definition_hash`, `archetype_composition` and
`grant_set_hash`.

**`whitepaper-index.md`** is a 30-row table of SDK surface, section number and
section title, opening with a statement that the whitepaper is not published.

**`tools/docs_tests/test_diagram_coverage.py`** globs `public/diagrams/*.mmd`,
scans `public/concepts/**/*.md` for snippet includes, and asserts a bijection —
plus a populated-fixtures precondition so the suite cannot pass vacuously if
either tree is renamed.

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 1 - Bug] The index scan-clean acceptance command passes a `str`
where a `Path` is required**
- **Found during:** Task 2
- **Issue:** The criterion's inline command calls
  `scan_text(text, 'x', shingles)`; `scan_text` forwards its second argument to
  `scan_path`, which calls `.parts` on it, so the command raises
  `AttributeError` regardless of page content and can never report a verdict.
- **Fix:** Ran the corrected form with `pathlib.Path` for the second argument.
  Exit 0. No source change — the defect is in the acceptance command, not in
  `tools/publish_scan.py`.

**2. [Rule 3 - Blocking] Two acceptance criteria on the pillar pages are in
tension**
- **Found during:** Task 1
- **Issue:** The plan requires at least two `reference/` links per pillar page
  AND `! grep -rqE '\]\(\.\./\.\./|\]\(docs/' public/concepts/`. Pillar pages
  are two directories deep, so every inline link to a Reference page is
  necessarily `](../../reference/...)` and trips the second criterion. Absolute
  links are not an escape — `validation.absolute_links: warn` plus
  `strict: true` makes them fatal — and `mkdocs.yml` is out of this plan's
  scope.
- **Fix:** Wrote the cross-tree links as Markdown reference-style
  (`[text][key]` with `[key]: ../../reference/...` definitions at the foot of
  the page). MkDocs resolves and validates them identically, the intent of the
  guard is preserved (nothing links outside the published tree), and both
  criteria hold literally.
- **Files modified:** all five pillar pages.

**3. [Rule 1 - Bug] Three whitepaper section titles tripped the publish scan**
- **Found during:** Task 2
- **Issue:** D-18 permits section numbers and titles, but three verbatim
  headings are long enough to form ten-word shingles against the whitepaper —
  the 5.2 heading, the 8.6 heading, and the 8.7.1 heading — and the same held
  for one sentence of `replay-anatomy.md` prose that had drifted close to the
  source wording. `tools/publish_scan.py` takes no allowlist and is the arbiter.
- **Fix:** Gave the three long titles in short form (with a note in the page
  intro that the section number is the authoritative key) and rewrote the
  replay-anatomy opening in different words. Scan exits 0.
- **Files modified:** `public/concepts/whitepaper-index.md`,
  `public/concepts/replay-anatomy.md`.

## Verification

| Check | Result |
| --- | --- |
| `make docs` (strict, full validation block) | exit 0 |
| `tools/publish_scan.py site` | exit 0 |
| `pytest tools/docs_tests -q` | 10 passed |
| Each pillar page embeds its own diagram exactly once | 5/5 |
| `seam-artifact-store` / `seam-harness-adapter` on the right pages | yes |
| `reference/` links per pillar page | 2, 2, 2, 6, 7 |
| `class="mermaid"` files under `site/concepts/pillars/` | 5 |
| `## ` sections in `invariants.md` | 9 (≥7) |
| `tools.lints` mentions in `invariants.md` | 3 |
| Table rows in `whitepaper-index.md` | 32 (≥22) |
| Sequence diagrams across Concepts, total / distinct | 4 / 4 |
| `SPEC_INVENTORY` / `DESIGN.md` / `DECISIONS.md` under `public/concepts/` | absent |
| Orphan negative control (`orphan.mmd`) | test fails, names the file |
| Duplicate negative control (`pillar-hitl.mmd` twice) | test fails, names both pages |

Both negative controls were reverted; `git status` clean apart from the tracked
commits.

## Known Stubs

None. All eight Concepts pages carry substantive content; no placeholder text
remains under `public/concepts/`.

## Threat Flags

None. No new network endpoint, auth path, file-access pattern or schema change
was introduced — this plan writes documentation and one test module.

The three mitigations the plan's threat register assigned to this plan were
applied: T-14-23 (index constrained to number plus title, scan run against the
page and against the built tree), T-14-24 (pages written from CLAUDE.md §4 and
from the code; post-build scan green), T-14-25 (internal deliverable names
asserted absent), T-14-26 (bijection test).

## Self-Check: PASSED

All eight modified pages and the new test module exist on disk; all three
commit hashes resolve in `git log`.
