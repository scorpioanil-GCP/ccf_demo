---
phase: 16-documentation-rewrite-the-deterministic-path-the-adoption-ar
plan: 06
subsystem: docs
tags: [mkdocs, mkdocstrings, graph-registry, deployment-manifest, surface-record, advisory-discharge]

# Dependency graph
requires:
  - phase: 15.2-15.4
    provides: the graph adapter registry seam, GraphQuery, backend_secrets, ccf backends list / GET /backends
  - phase: 16-01
    provides: D-IMPL-94 and its Q-6 / Q-7 dispositions
  - phase: 16-04
    provides: tools/docs_tests/_prose.py, the documented-command gate, the stale-path gate
provides:
  - "public/reference/artifacts/deployment-manifest.md — A-1 day-1 import convention and A-8 both halves"
  - "public/reference/surface-toolchain.md — A-2 maintainer page for the surface record"
  - "three stale pages rewritten against the surface at HEAD (A-3)"
  - "tools/docs_tests/test_advisory_discharge.py — the standing per-advisory evidence gate"
  - "the first mkdocs.yml nav edit of the phase (40 -> 42 entries)"
affects: [16-07, 16-08, 16-09, 16-10, 16-11, 16-12, 16-13, 16-14, 16-16, 16-17, 16-18]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "per-advisory gate modules that name the advisory in the failure message"
    - "nav membership parsed from mkdocs.yml by slicing the nav block (yaml.safe_load refuses the !!python/name: tag)"
    - "signature drift asserted against inspect.signature() at run time, never against a transcription"

key-files:
  created:
    - public/reference/artifacts/deployment-manifest.md
    - public/reference/surface-toolchain.md
    - tools/docs_tests/test_advisory_discharge.py
  modified:
    - public/how-to/write-a-graph-backend-adapter.md
    - public/how-to/security-and-deployment.md
    - public/reference/protocols/storage-and-graph.md
    - mkdocs.yml
    - examples/06-decision-replay/run.py

key-decisions:
  - "Task order reversed: new pages + nav shipped before the three rewrites, because mkdocs nav is an explicit enumeration and neither the plan's Task 1 nor its Task 2 could produce a green build in the order written"
  - "The DI-15.4-05 private-surface-gap section was REMOVED from the published adapter how-to rather than reworded — Q-7 forbids teaching an unruled surface, and a hedge is still a description"
  - "The 'no line changing in the SDK' zero-cost claim was dropped from the how-to's opening rather than restated, per the Codex finding that it is partly true by construction of the measurement (DI-15.4-06)"
  - "No worked-example include on the new manifest page: the plan's named source (examples/s1-01-hello-context-product) is built by the parallel plan 16-05 and does not exist in this worktree, and every current example is retired by D-07"
  - "A-1's counter-example is stated as a bare dotted name, never as an import line, because the plan's own acceptance criterion greps public/ for that line and would have been failed by the page teaching it"

patterns-established:
  - "Advisory gates report by advisory id: a failure says 'A-8 is undischarged', not 'assertion failed'"
  - "Every advisory assertion is paired with a control that mutates a copy of the real page and asserts refusal — non-vacuity proven by watching the gate fail, not by a corpus floor"
  - "Unruled decisions go to docs/DECISIONS.md and the phase record; public/ describes only the settled surface"

requirements-completed: [DOCS-16]

# Metrics
duration: 62min
completed: 2026-08-10
---

# Phase 16 Plan 06: Discharge the four carried advisories Summary

**A-1, A-2, A-3 and A-8 discharged on published pages with a standing per-advisory gate: two new reference pages (deployment manifest, surface-record toolchain), three stale pages rewritten against the registry seam / query seam / secret surface at HEAD, and 18 tests that fail if any page is reverted.**

## Performance

- **Duration:** ~62 min
- **Started:** 2026-08-10T17:52Z
- **Completed:** 2026-08-10T18:54Z
- **Tasks:** 3
- **Files modified:** 8 (3 created, 5 modified)

## Accomplishments

- **A-3 discharged where it bit hardest.** The published tree now names the
  registry seam, the six shipped adapters, `ccf backends list` / `GET /backends`,
  `GraphQuery`, the per-round-trip content-hash replay pin, and `backend_secrets`
  — all of which were measured at **zero** occurrences across `public/` when the
  audit was written.
- **A-1 stated with its real scope.** `from ccf.deployment import …` is the day-1
  spelling and submodule paths are implementation detail — and the page says
  explicitly that this is a spelling rule for one package, not an instruction to
  collapse the API, which is the over-reading the raw advisory invites.
- **A-8 stated in one paragraph, both halves.** A `role: load` artifact is
  reachable on `BootedFabric.artifacts` **and** absent from `pins`, absent from
  the Control Plane registry, and absent from replay dimension 2. The gate refuses
  the two halves split across paragraphs, because a reader can meet the first
  alone and that is the whole of the mislead.
- **A-2 shipped as a maintainer page** covering the generated manifest, the
  three generator modes, baseline immutability (with the reasoning: a manifest
  regenerated whenever it disagrees with the tree asserts nothing), the always-on
  drift assertion and its two stated limits, the curated half's seven-field
  refusal, and the three adjacent generators.
- **Q-7 honoured.** The `## The private-surface gap, stated plainly` section —
  which named the six private helpers `DI-15.4-05` is about — is gone from the
  published tree, and nothing replaced it. `grep -rc "DI-15.4-05\|substrate_vocabulary" public/` is 0.

## Task Commits

1. **Task 2 (shipped first): the two new reference pages + nav** — `1e32a80` (docs)
2. **Task 1: rewrite the three stalest pages against HEAD** — `5bf819b` (docs)
3. **Task 3: the advisory-discharge gate + the A-1 example fix** — `2ff2b4e` (test)

**Plan metadata:** this summary's own commit.

## Files Created/Modified

- `public/reference/artifacts/deployment-manifest.md` **(created)** — the day-1
  import convention with its reason and its scope; both halves of `role`;
  `registration: typed | versioned` in the **corrected** D-IMPL-84/85 wording (a
  manifest *may* name all six author-versioned classes as `versioned`; what is
  refused is `typed` for such a class); the `ccf.` prefix reservation; `backend`
  as a shape rule with membership checked at load; `backend_secrets` as
  field/env-var pairs. Renders `load_and_boot`, `BootedFabric`,
  `DeploymentManifest`, `ManifestEntry` and `SecretReference`, none of which was
  rendered anywhere before — no duplicate-identifier risk.
- `public/reference/surface-toolchain.md` **(created)** — A-2. Passes
  `pub02-internal-path` by wording; links nothing under the curated-log tree per
  Q-6, and the hyphenated token appears nowhere in `public/`.
- `public/how-to/write-a-graph-backend-adapter.md` — rewritten. New: the five
  `BackendRegistration` fields as a table; why `config_model` must derive from
  `CCFContract`; the two discovery sources with the disk-read-not-import
  distinction; `declared_names()` fail-closed on all three refusals and
  `resolve()` importing exactly one adapter; a `What query() must answer`
  section pointing at `docs/GRAPH_QUERY_SEMANTICS.md`; the honest pushdown
  posture (`GQ-34` — byte-identity is a correctness bar, not a translation
  measure; `translated_answers` / `fallback_answers` are). Removed: the
  private-surface gap section, and the zero-cost claim in the opening.
- `public/how-to/security-and-deployment.md` — new §1.3 covering the adapter
  credential path end to end, including that `canonical_bytes` **refuses
  `SecretStr` outright** (mechanism, not discipline) and the deployment rule that
  a connection string belongs in the caller-supplied `connection=` mapping.
- `public/reference/protocols/storage-and-graph.md` — the query seam and the
  adapter registry, in the protocol-page form; the six shipped adapters with
  their config models, config fields and credential fields.
- `mkdocs.yml` — two nav entries, count comment 40 → 42 (43 markdown files, one
  `not_in_nav`). Verified by parsing.
- `tools/docs_tests/test_advisory_discharge.py` **(created)** — 18 tests.
- `examples/06-decision-replay/run.py` — one import folded (see deviations).

## Decisions Made

- **The plan's Task 1/Task 2 order cannot produce a green build and was
  reversed.** `mkdocs.yml`'s nav is an explicit enumeration and
  `validation.nav.omitted_files` under `--strict` fails **both** a page absent
  from nav and a nav entry with no file. Task 2 creates two pages whose nav
  entries the plan assigns to Task 3, so Task 2's own `make docs-strict` verify
  could never pass as written; and Task 1's rewritten pages want to link forward
  to Task 2's pages. Shipping the new pages *with* their nav entries first makes
  every commit independently green and lets the rewrites link forward honestly.
- **The private-surface gap was deleted, not hedged.** The section was correct
  when 15.4-11 wrote it and is now an unruled position. A softened version would
  still teach a reader a surface that is about to be re-decided, which is exactly
  what Q-7 forbids.
- **No worked-example include on the manifest page.** The plan names
  `examples/s1-01-hello-context-product/artifacts/manifest.yaml`, which plan
  16-05 is building in a sibling worktree and which does not exist here; every
  other example is retired by D-07. The mkdocstrings render of the contracts
  (with `griffe_pydantic` schemas) carries the shape instead. A later plan owning
  the Section-1 example can add the include.
- **A-1's counter-example is written as a bare dotted name.** The plan's action
  text asks the page to say "never `from ccf.deployment.manifest import
  load_and_boot`", but its own acceptance criterion requires
  `grep -c "from ccf\.deployment\.[a-z_]* import" public/` to return 0. The rule
  is stated without spelling an importable line, satisfying both.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Folded a submodule import in `examples/06-decision-replay/run.py`**
- **Found during:** Task 3 (the A-1 gate)
- **Issue:** The plan's A-1 gate requires `from ccf.deployment.<sub> import` to
  appear nowhere in `public/` **or** `examples/`. One site violated it:
  `examples/06-decision-replay/run.py:82` imported `ResolvedPins` from
  `ccf.deployment.pins`. The gate could not be written as specified and pass.
- **Fix:** Folded `ResolvedPins` into the existing top-level
  `from ccf.deployment import (...)` block. `ResolvedPins` is in
  `ccf.deployment.__all__`, so this is the same object by the preferred spelling;
  member ordering matches the tree's convention (classes before functions).
- **Files modified:** `examples/06-decision-replay/run.py`
- **Verification:** `pytest tests/examples/test_decision_replay_output.py -q` →
  34 passed. The import block is not inside any `--8<--` snippet region, so no
  published page changed. The example is retired by D-07 later this phase, which
  makes the change cheap either way.
- **Committed in:** `2ff2b4e`
- **Note:** this file is outside the plan's declared `files_modified`.

**2. [Rule 1 - Bug] Two plan `read_first` claims are false against the tree**
- **Found during:** Task 1
- **Issue:** The plan states `write-a-graph-backend-adapter.md` "predates the
  registry seam entirely and is the page most likely to be materially wrong
  post-15.4". It does not: `c7e3f88` / `3db28f9` (plan 15.4-11) wrote it *for*
  the registry seam, and it already named entry points, `secret_fields`,
  `ResolvedSecret` and the conformance suites. The plan also cites
  `src/ccf/deployment/__init__.py` lines 72-79 as "the canonical Gate-2
  paragraph"; those lines are the lineage-strict-equality statement, and Gate 2
  is not mentioned on either new page.
- **Fix:** Rewrote against what the page actually said rather than against the
  plan's description of it. The real defects were the two Q-7/DI-15.4-06 claims
  and four missing subjects (`BackendRegistration`'s field list, the two
  discovery sources, `docs/GRAPH_QUERY_SEMANTICS.md`, the `GQ-34` posture).
- **Files modified:** `public/how-to/write-a-graph-backend-adapter.md`
- **Verification:** every Task-1 acceptance grep passes; `make docs-strict` 0.
- **Committed in:** `5bf819b`

**3. [Rule 3 - Blocking] Task ordering reversed (see Decisions Made)**
- **Found during:** Task 1
- **Issue:** Neither Task 1 nor Task 2 could satisfy its own `make docs-strict`
  verify in the order written, because nav registration was assigned to Task 3.
- **Fix:** Shipped the new pages together with their nav entries as the first
  commit; the three rewrites second; the gate third.
- **Files modified:** `mkdocs.yml` (committed with Task 2's pages rather than
  with Task 3)
- **Verification:** `make docs-strict` exits 0 at each of the three commits.
- **Committed in:** `1e32a80`, `5bf819b`, `2ff2b4e`

---

**Total deviations:** 3 auto-fixed (1 blocking import fold, 1 plan-text
correction, 1 task reorder)
**Impact on plan:** No scope creep. One file outside `files_modified`
(`examples/06-decision-replay/run.py`, one import line), forced by the gate the
plan itself specifies. No change under `src/` or `runtime/` —
`git diff --stat -- src/ runtime/` is empty.

## Q-7: the open question, recorded here rather than published

`D-IMPL-94`'s Q-7 disposition leaves two questions unruled, and this plan wrote
them here instead of onto a page:

- **`DI-15.4-05` — the public-versus-private adapter surface.** Six names an
  out-of-tree adapter author must reach for are absent from their modules'
  `__all__`: `materialize_view`, `_ordered_view`, `_entity_records`,
  `_relationship_records` and `_LineageRowsFor` from the graph reader module, and
  `_GraphTxn` from the writer's private module. `BaseGraphReader` is public but
  SQL-shaped, so a non-relational store cannot use it. Until this is ruled, the
  published how-to describes only the settled seam — `BackendRegistration`
  declared as `REGISTRATION` in a `*_write.py` module, discovered by disk read or
  through the `ccf.graph_backends` entry-point group.
- **`DI-15.4-06` — `substrate_vocabulary` derives from in-tree adapters only**,
  so `cinv04-substrate-name` enforces "no *built-in* substrate name in core". The
  consequence Codex named at the 15.4 close-time panel is that the third-party
  zero-cost claim is "partly true by construction of the measurement". That claim
  is therefore not restated on any published page; the how-to's opening now
  states the mechanism (entry-point declaration, resolution by name, the same
  conformance suites) instead of the property.

Both belong to a Phase D mini-cycle, not to this documentation phase.

## Issues Encountered

- **`yaml.safe_load` cannot read `mkdocs.yml`** — it carries a
  `!!python/name:pymdownx.superfences.fence_code_format` tag the safe loader
  refuses. The nav-membership assertions parse the nav block by slicing instead,
  with a precondition asserting the parse is non-empty and contains `index.md` so
  a regex that stopped matching cannot pass silently.
- **The A-3 signature half has no corpus at HEAD.** Zero published pages carry a
  `boot(` invocation with arguments — the pre-15.4 `boot(database_path=…)` form
  was already gone. Rather than demand a page write a call it has no reason to
  write, non-vacuity is proven by a control that injects the stale spelling and
  asserts refusal, plus a second control that injects a *correct* call and
  asserts silence (so the first cannot pass by reporting everything), plus a
  third asserting `load_and_boot(` is not read as `boot(`.

## Verification

| Check | Result |
| --- | --- |
| `tools/publish_scan.py --pre-build` | exit 0 |
| `make docs-strict` (pre-build scan + strict build + site scan) | exit 0 |
| `pytest tools/docs_tests tools/publish_scan_tests -q` | 111 passed (86 + 25), incl. 18 new |
| `python -m tools.lints --all` | exit 0 |
| `pytest tests/examples/test_decision_replay_output.py -q` | 34 passed |
| `git diff --stat -- src/ runtime/` | empty |
| `grep -rc "DI-15.4-05\|substrate_vocabulary" public/` | 0 |
| `grep -rEc "[a-z_]+\.py:[0-9]+" public/` | 0 |
| `grep -rc "SURFACE-CHANGES\|surface-changes" public/` | 0 |
| `grep -rEc "from ccf\.deployment\.[a-z_]* import" public/` | 0 |
| `grep -rc "boot(database_path" public/` | 0 |
| `grep -rc "cannot name an author-versioned" public/` | 0 |
| nav entries vs. markdown files | 42 nav + 1 `not_in_nav` = 43 files ✓ |
| diagram bijection (`test_diagram_coverage.py`) | intact — neither new page embeds a `.mmd` |

## User Setup Required

None.

## Next Phase Readiness

- **The nav is now 42 entries.** Waves 6–11 each add their own entries; the count
  comment in `mkdocs.yml` is authoritative and must move with them.
- **`tools/docs_tests/test_advisory_discharge.py` is standing.** Later plans that
  rewrite `public/reference/artifacts/deployment-manifest.md` or
  `public/reference/surface-toolchain.md` must keep A-1's preferred spelling, the
  A-2 token list, and A-8's two halves *in one paragraph*. The module's page
  constants are at the top for exactly that reason.
- **The A-1 gate now covers `examples/`.** Plans writing new example code must
  import from `ccf.deployment`, never from its submodules, or the gate goes red.
- **A worked-example include is owed** on the deployment-manifest page once a
  Section-1 example exists that this phase does not retire.
- **Not blocked on anything.** Q-7's two open questions are recorded above and
  are a Phase D mini-cycle's business, not a blocker for the remaining Phase 16
  waves.

## Self-Check: PASSED

All three created files present on disk; all three task commits present in
`git log` (`1e32a80`, `5bf819b`, `2ff2b4e`). No modification to `STATE.md` or
`ROADMAP.md` — the orchestrator owns those writes.

---
*Phase: 16-documentation-rewrite-the-deterministic-path-the-adoption-ar*
*Completed: 2026-08-10*
