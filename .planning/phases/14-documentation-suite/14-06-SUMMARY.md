---
phase: 14-documentation-suite
plan: 06
subsystem: docs
tags: [reference, mkdocstrings, griffe-pydantic, openapi, drift-gate]
requires: ["14-01", "14-02", "14-03"]
provides:
  - "Twelve generated Protocol reference pages (public/reference/protocols/)"
  - "Eight generated definition-artifact schema pages (public/reference/artifacts/)"
  - "The HTTP contract page as a whole-file include of the committed openapi.json"
  - "tools/docs_tests/test_mkdocstrings_gate.py — the D-14 rename/removal negative control"
affects:
  - "public/reference/protocols/context-products.md cross-links product-registration.md"
tech-stack:
  added: []
  patterns:
    - "mkdocstrings ::: identifier directives, zero hand-written signatures (DOCS-02 non-goal)"
    - "griffe-pydantic schema: true renders every model's JSON Schema and extra=forbid config"
    - "pymdownx.snippets whole-file includes for artifacts and openapi.json (D-09, D-12)"
    - "Strict-mode collection failure AS the drift gate, proven by paired positive/negative controls"
key-files:
  created:
    - tools/docs_tests/test_mkdocstrings_gate.py
  modified:
    - public/reference/protocols/*.md (12 pages)
    - public/reference/artifacts/*.md (8 pages)
    - public/reference/http-api.md
decisions:
  - "RegisteredProductClass and MaxTTL are generated once, on the artifact page, not twice"
metrics:
  tasks: 3
  commits: 3
  pages: 21
  directives: 69
  completed: 2026-08-03
---

# Phase 14 Plan 06: Reference Section Summary

Twenty-one Reference pages whose every signature, docstring, field list and JSON Schema is
generated at build time — plus a paired control proving that renaming a documented Protocol
breaks the build rather than silently stranding a page.

## What was built

**Twelve curated Protocol pages** (`public/reference/protocols/`), carrying 69 `:::` identifier
directives drawn from the D-13 verified surface inventory. Each page opens with one or two
sentences of framing naming what the group of surfaces is for and which invariant it carries —
the single-writer asymmetry on the graph page, composition-preservation on the operator page,
audit-by-construction on the HITL page — and then contains nothing but directives. The four
deliberately excluded internals (`ccf.boot._Backend`, `ccf.graph._writer._Store`/`_Txn`,
`ccf.graph.reader.Row`) are absent, and no page overrides the global `show_source: false`
publish-safety setting.

**Eight definition-artifact schema pages** (`public/reference/artifacts/`), one per artifact
class, each rendering a generated JSON Schema block plus exactly one whole-file example include
of a real artifact from the examples suite. The prose on each page is commentary — what the
class is for, when an adopter authors one, which pillar it belongs to — and carries no
transcribed field, type or requiredness.

**The HTTP contract page**, a whole-file include of the committed `openapi.json` inside a
`json` fence, with a paragraph naming `make openapi` as the regeneration command and explaining
that the committed baseline is drift-checked against `create_app()` by an always-on test. The
published contract is the committed contract by construction; there is no transcription step in
which they could diverge.

**The D-14 negative control** (`tools/docs_tests/test_mkdocstrings_gate.py`), three tests
running the real site config against a copy of the real `public/` tree.

## Deviations from Plan

**1. [Rule 3 — Blocking] `RegisteredProductClass` and `MaxTTL` were allocated to two pages**

- **Found during:** Task 2, on the first build after the artifact pages landed.
- **Issue:** The plan assigns both models to the `context-products` Protocol page (Task 1) and
  to the `product-registration` artifact page (Task 2). Rendering one identifier on two pages
  gives it two primary URLs, which `mkdocs_autorefs` reports as a WARNING — fatal under
  `strict: true`. `make docs` aborted.
- **Fix:** The generated block lives on the artifact page, which is where the D-11 authoring
  surface belongs and which needs it for the "eight pages render a schema" criterion. The
  Protocol page now carries a short paragraph cross-linking to it and stating why the block is
  not repeated. This is a presentation-level resolution; no surface was dropped from the
  reference.
- **Files modified:** `public/reference/protocols/context-products.md`
- **Commit:** `b9d80bd`

**2. [Advisory] One acceptance criterion is not literally satisfiable as written**

Task 2 specifies `grep -q '"openapi"' site/reference/http-api/index.html`. The included JSON is
syntax-highlighted, so every double quote in the rendered page is HTML-escaped to `&quot;`. The
literal command exits 1 on a correct build. Verified the equivalent instead: `openapi&quot;`
is present, and the rendered page is 317 KB — the full 70 KB spec plus highlight markup, not a
truncated or empty include. Recording this rather than silently substituting.

**No docstring edits were required.** The orchestrator flagged that any docstring surfaced by
mkdocstrings becomes published text subject to the D-02/D-20 scan, and that a leak should be
fixed in the docstring. None leaked: `tools/publish_scan.py site` exits 0 over the whole built
site, including `site/reference/protocols/halflife-and-debt/index.html` scanned on its own,
which is the page plan 14-02's D-20 rework was written to serve. Its docstrings render as
paraphrase plus `§`-citation, which was the quality bar. No file under `src/` or `runtime/` was
touched by this plan.

## Assumption A2 resolved favourably

Research flagged that `griffe-pydantic` might render complex models awkwardly, naming the five
discriminated binding types in `SkillCatalogEntry` as the hardest case. Inspected the rendered
`skill-catalog` page: all five (`LocalCallableBinding`, `ToolBinding`, `McpBinding`,
`PeeringBinding`, `ProcedureBinding`) render cleanly with 11–12 occurrences each, each with its
own schema block. No compensating prose was needed beyond a sentence explaining that the union
is discriminated by the entry's skill type — which is domain-independent commentary, not a
transcribed schema. The inherited-field case is likewise clean: `_TwoLaneVersioned` stays
private and out of the reference, with its fields inlined into the subclasses.

## Verification

| Check | Result |
|---|---|
| `make docs` (strict) | exits 0 |
| Directives across the twelve Protocol pages | 69, every page non-empty (min 1, max 14) |
| Hand-written signatures in `public/reference/protocols/` | none (`def `/`class `/`(self` absent) |
| Excluded internals documented | none |
| Per-page `show_source` overrides | none |
| Artifact pages rendering a JSON Schema | 8 of 8 |
| `additionalProperties` in rendered agent-definitions | present (extra=forbid published) |
| Five binding types in rendered skill-catalog | all present |
| Includes per artifact page | exactly 1 each, all whole-file, no section suffix |
| `_TwoLaneVersioned` in `public/reference/` | absent |
| Transcribed schema fields (`type: string`, `required:`) | none |
| `tools/publish_scan.py site` | exits 0 |
| halflife-and-debt page scanned alone | exits 0 |
| `pytest tools/docs_tests -q` | 9 passed (3 new) |
| Gate test residue vs. baseline | identical |

`make test` was not re-run: this plan touches no file under `src/`, `runtime/`, `tests/` or
`examples/`, so the library suite cannot be affected by it.

## Commits

| Task | Commit | Description |
|---|---|---|
| 1 | `ba18a08` | Twelve curated Protocol reference pages |
| 2 | `b9d80bd` | Eight artifact schema pages and the HTTP contract page |
| 3 | `d1d4c17` | The D-14 rename-and-removal negative control |

## Threat Flags

None. The plan's six registered threats are each mitigated and asserted: T-14-27 by the
post-build scan over the whole site plus the halflife page individually, T-14-28 by the
no-overrides grep, T-14-29 by the excluded-internals grep, T-14-30 by the paired controls
including the near-miss rename case, T-14-31 by the whole-file include of the committed spec,
and T-14-32 because every include on these pages is a whole file under `examples/` or the
repo-root `openapi.json`. No new security-relevant surface was introduced — this plan adds
documentation pages and one test.

## Known Stubs

None. All twenty-one pages this plan owns are filled.

## Self-Check: PASSED

All 21 content pages and the new test file exist on disk; all three commit hashes resolve in
`git log`; the working tree is clean.
