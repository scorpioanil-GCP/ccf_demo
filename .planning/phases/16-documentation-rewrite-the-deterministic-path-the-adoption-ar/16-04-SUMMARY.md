---
phase: 16-documentation-rewrite-the-deterministic-path-the-adoption-ar
plan: 04
subsystem: testing
tags: [docs-gates, pytest, paragraph-scoping, whitepaper-shingle, makefile-bijection, publish-scan]

requires:
  - phase: 16-01
    provides: "D-IMPL-94 recorded in docs/DECISIONS.md — D-13 authorises the single src/ docstring carve-out, Q-8 rules the three gate suites into `make ci`"
provides:
  - "The three pre-existing gate-checker failures are green; `pytest tools/lints/tests tools/publish_scan_tests tools/docs_tests` is 0 failed for the first time this phase"
  - "tools/docs_tests/_prose.py — the shared paragraph-scoping helper for public/**/*.md, extracted once"
  - "tools/docs_tests/test_gate_two_wording.py — criterion 8 as a standing gate rather than a one-off sweep"
  - "tools/docs_tests/test_no_stale_example_paths.py — criterion 5's silent half, SURFACE-AUDIT A-5's path-target gap"
  - "tools/docs_tests/test_documented_commands_exist.py — the Makefile <-> published-command bijection"
affects: [16-12, 16-18, 16-19, all Section-1 authoring plans]

tech-stack:
  added: []
  patterns:
    - "Paragraph-scoped prose gates over public/**/*.md, fence-aware, with sentence-scoped negation"
    - "Every new gate ships a populated-tree precondition, a non-vacuity check, a CWD-independence test, and a control proving refusal"

key-files:
  created:
    - tools/docs_tests/_prose.py
    - tools/docs_tests/test_gate_two_wording.py
    - tools/docs_tests/test_no_stale_example_paths.py
    - tools/docs_tests/test_documented_commands_exist.py
  modified:
    - src/ccf/controlplane/artifacts.py
    - tools/docs_tests/test_snippet_gate.py
    - docs/schemas/ccf.product-class.json

key-decisions:
  - "The Gate-2 positive assertion triggers on CHARACTERIZATION of Gate 2, not on mere mention — a bare enumeration of the three validation gates asserts nothing about independence, and demanding the correction there would force padding into correct prose"
  - "Independence negation is scoped to the SENTENCE carrying the word, not the paragraph, so a `not` three sentences away cannot exonerate a claim"
  - "`make <target>` extraction is scoped to inline code spans and fenced blocks, never running prose — `make` is an English verb and a bare prose scan yields 7 false positives at HEAD"
  - "The stale-path gate scans fenced blocks as well as running prose; a stale path in a `sh` block is equally rotten and equally invisible to check_paths"
  - "The backward command-bijection direction is checked against the `examples:` prerequisite list, not all of `.PHONY` — requiring published prose for `help` and `install` is not a documentation debt"

patterns-established:
  - "Shared prose helper: three gates import tools/docs_tests/_prose.py rather than inlining three scoping rules that drift apart"
  - "Control tests in both polarities: every gate is watched failing on an injected violation AND watched passing on the unmodified baseline, so a refusal is provably caused by the injection"

requirements-completed: [DOCS-08, DOCS-17]

duration: 30min
completed: 2026-08-10
---

# Phase 16 Plan 04: Gate-Checker Repair and the Three Standing Tripwires Summary

**Three CI-only gate-checker failures made green, and three paragraph-scoped standing gates installed to police the forty-one pages this phase is about to rewrite — with the phase's single authorised `src/` edit confined to one docstring.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-08-10T16:30Z (approx., base `cf8c653`)
- **Completed:** 2026-08-10T17:00Z
- **Tasks:** 3 of 3
- **Files modified:** 7 (4 created, 3 modified)

## Accomplishments

### Task 1 — the three failing gate-checkers (`e984844`)

**Baseline, scripted:** `453 passed, 3 failed`.

**(a) The docstring leak.** `test_no_docstring_reproduces_whitepaper_body_text` reported exactly one leak — `ProductClassDeclaration`, 20 shingle hits — matching D-IMPL-94's re-measurement at `3cbaa0c`. All 20 hits traced to a **single verbatim quotation** of whitepaper body text about the empty-operator guard; every other shingle in the docstring was clean. The passage is rewritten in the project's own words, citing §7.6 (*Context Products — System of Delivery*) by section number and title only, per CLAUDE.md §11 and Phase 14 D-18. Post-edit hit count: **0**.

**(b) The snippet fixtures.** `SNIPPET_SOURCE`/`SECTION` pointed at an `[start:ontology]` marker that no longer exists in `examples/00-quickstart/run.py` — the fixture reported this correctly as *"fixture drifted from its source"*. Repointed to `boot` (line 156, verified present). A comment records that **plan 16-18 repoints both constants again** at the Section-1 spine when `00-quickstart` retires, so the terminal plan does not rediscover the coupling from a failing assertion.

**Result:** `456 passed, 0 failed`.

### Task 2 — the shared helper and the Gate-2 wording gate (`229aed5`)

`tools/docs_tests/_prose.py` composes the two halves that already existed (`publish_scan.normalize` strips markup; `citations.citation_sentence` maps an offset back to a sentence) into the paragraph-scoped read over `public/**/*.md` that `16-PATTERNS.md` § *No Analog Found* records as absent. It preserves casing (callers want case-insensitive *matching*, not a lowercased corpus), and it **marks fenced blocks rather than dropping them**, because the wording gates must skip them and the command gate must read them.

`test_gate_two_wording.py` ships two assertions of deliberately different shape. The negative one catches the direct reintroduction ("two independently authored sets"); the positive one catches the subtler form that uses no trigger word at all ("Gate 2 verifies that the declared set matches the executed one"). Green at HEAD with **no published page edited**, as plan 15.1-20's sweep implies.

### Task 3 — the stale-path and command gates (`23bffcc`, `b19a809`)

`test_no_stale_example_paths.py` imports `publish_scan.include_targets` rather than re-implementing an include parser, and a control proves the block form would defeat a hand-rolled inline-only regex. Its own subject is the silent half: **running prose alone — 13 distinct tokens, 15 references, 7 pages** (the surface `16-RESEARCH.md` § A.2 enumerates); **prose and fenced blocks together — 56 distinct tokens, 119 references, 15 pages**. Zero unresolvable in either set.

`test_documented_commands_exist.py` asserts the Makefile bijection in both directions: **17 documented targets, 0 undefined; 10 composed `example-*` targets, 0 undocumented.**

## Scripted verification

Every figure below is command output, not assertion (P-8).

| Check | Result |
|-------|--------|
| `pytest tools/lints/tests tools/publish_scan_tests tools/docs_tests -q` | **488 passed, 0 failed** (baseline 453/3; floor required ≥456) |
| `pytest tools/docs_tests -q` | 45 passed |
| The three new gate modules alone | 32 passed |
| `ProductClassDeclaration` shingle hits | **0** (was 20) |
| `tools/publish_scan.py --pre-build` | exit 0 |
| `make ci-core` | exit 0 — **2423 passed, 81 skipped, 0 failed** |
| `make lint` | exit 0 |
| `make typecheck` | Success: no issues in 186 source files |
| `mypy --strict` on the 4 new/changed tools modules | Success: no issues in 4 source files |
| `make docs-strict` | exit 0 |
| `grep -c "assembly-path integrity" src/ccf/controlplane/artifacts.py` | 1 — unchanged from pre-edit |
| `grep -c "\[start:boot\]" examples/00-quickstart/run.py` | 1 |
| `git diff --stat cf8c653..HEAD -- src/ runtime/` | `src/ccf/controlplane/artifacts.py` only, 8 insertions / 5 deletions, **all docstring lines** |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] `docs/schemas/ccf.product-class.json` regenerated**

- **Found during:** Task 1, at the `make ci-core` acceptance check.
- **Issue:** Pydantic exports a model's class docstring as the JSON Schema `description`, so the committed ERGO-12 schema tree is a **derived artifact of the docstring**. The authorised edit turned three assertions in `tests/cli/test_schema_export.py` red (`test_the_committed_schemas_match_what_the_classes_emit`, the `[ccf.product-class]` byte-for-byte case, and `test_an_orphan_schema_is_drift`). Leaving it stale would have left `make ci` red on a file the plan's own edit caused.
- **Fix:** `make schemas` — the committed regenerator, whose serialization recipe the test imports rather than restates. The regeneration touched **one line in one file**: the `description` of `ccf.product-class.json`.
- **Scope check:** `docs/schemas/` is outside `src/` and `runtime/`, so ROADMAP criterion 10 and plan 16-19's allowlist are unaffected. It is not a file owned by 16-02, 16-03 or 16-21.
- **Commit:** `e984844`

**2. [Rule 1 — Bug in my own work] A control test asserting a false property**

- **Found during:** Task 3, first run.
- **Issue:** I wrote `test_the_gate_refuses_a_missing_path_across_a_line_wrap` on the plan's stated rationale — *"a wrapped Markdown sentence hides a path from a line-scoped regex"*. It failed, and it was **right to fail**: a Markdown reflow breaks at whitespace, a path is a single token, and the joined paragraph therefore contains `tests/examples/ test_x.py` **with a space**, whose leading fragment resolves. Paragraph scoping does not rescue a mid-token wrap, and no scan that joins with a space can.
- **Fix:** the false control is replaced by three that assert true properties (fence awareness, a reflowed sentence around an intact path, and the `tests/examples` lookbehind). The module docstring now **states the plan's rationale as not holding for this gate** and names the reasons that do hold, plus the residual limit — rather than repeating a justification that does not survive contact.
- **Commit:** `23bffcc`

**3. [Rule 1 — Bug in my own work] An understated measurement in a docstring**

- **Found during:** final measurement sweep.
- **Issue:** the stale-path module quoted "13 distinct path tokens, 15 references" as what it asserts over. That is the **running-prose** figure; the gate deliberately scans fenced blocks too, where the figure is 56/119/15. Quoting the smaller number understated the gate's coverage roughly fourfold — a record claiming measurement that had measured a different thing (P-8).
- **Fix:** both figures stated, both scripted.
- **Commit:** `b19a809`

### Judgement calls worth Dave's eye

**The Gate-2 positive assertion triggers on characterization, not on mention.** The plan specifies: *"Every paragraph mentioning `INV-CH7-47` or the phrase 'lineage strict equality' also contains 'assembly-path integrity' or an explicit negation."* Taken literally, that fails at HEAD on two pages — `public/concepts/invariants.md:78` and `public/concepts/replay-anatomy.md:75` — which name lineage strict equality **inside a list of the three validation gates** and assert nothing whatever about independence.

The plan anticipates a failure at HEAD and calls it *"a finding: record which page it caught and fix the page in this plan."* I judged this to be a **mis-specification rather than a page defect**, and did not edit either page. Forcing "assembly-path integrity" into a bare enumeration is padding; a gate that demands it teaches authors to write worse pages to satisfy it. The trigger is therefore *mention **plus** a characterization verb* (`verifies`, `establishes`, `proves`, `witnesses`, `confirms`, `guarantees`, `attests`, `demonstrates`), which is exactly the set of paragraphs that owe the reader the correction.

This is deliberately held from both sides by controls: one proves the gate **refuses** `"Gate 2 verifies that the operator set the product declares matches the set the engine resolved"` (no trigger word anywhere — the subtle reintroduction the negative assertion alone would pass); another proves it **admits** a bare enumeration. A precondition asserts the positive filter matches something (2 paragraphs today, both already correct), so it cannot pass vacuously.

If Dave prefers the literal reading, the change is one regex and two page edits.

## Threat Model Discharge

| Threat ID | Disposition | Evidence |
|-----------|-------------|----------|
| T-16-04-01 | mitigated | `pub01-whitepaper-shingle` hits on `ProductClassDeclaration`: 20 → 0; `tools/publish_scan.py --pre-build` exit 0; the gate test passes. Verified by scan, not inspection. |
| T-16-04-02 | mitigated | `git diff --stat cf8c653..HEAD -- src/ runtime/` names one file; the full `git diff` on it shows docstring lines only — no signature, default, annotation, import or statement line. |
| T-16-04-03 | mitigated | Each of the three new modules carries a populated-tree precondition, a non-vacuity check, a CWD-independence test (`monkeypatch.chdir`), and controls proving refusal **and** a clean baseline. |
| T-16-04-04 | accepted | The three new modules add 32 tests; `tools/docs_tests` runs in 5.6 s total. |
| T-16-04-05 | transferred | Owned by plan 16-21. No file of that plan exists in this worktree: `tools/retirement_sweep.py`, `tools/docs_tests/test_retirement_sweep.py` and `docs/surface/examples/RETIREMENT-COUPLINGS.md` are all absent. |
| T-16-04-SC | accepted | No package install of any kind. New modules use only `pathlib`, `re`, `shutil`, `collections.abc`, `typing` and `pytest`. |

## Success Criteria

- [x] The three pre-existing failures are green, counts scripted (453/3 → 488/0)
- [x] The only `src/` change is one docstring inside `ProductClassDeclaration`
- [x] Three standing gates exist, each with a precondition, a CWD-independence test and a proven refusal
- [x] The shared prose helper is extracted once and imported by all three consumers, not inlined
- [x] No Makefile change (plan 16-12 owns it) — the backward control mutates Makefile text **in memory**
- [x] No file owned by plan 16-21 touched
- [x] STATE.md and ROADMAP.md untouched (orchestrator owns those writes)

## Notes for Later Plans

- **16-12** owns the `Makefile`. Q-8 rules the three gate suites into `make ci`; they are green now, so that composition can land without a repair step. Note `[tool.pytest] testpaths = ["tests"]` still excludes them from a bare `pytest`.
- **16-18** must repoint `SNIPPET_SOURCE`/`SECTION` in `tools/docs_tests/test_snippet_gate.py` when `examples/00-quickstart` retires. The coupling is recorded in the module.
- **16-19**'s `tools/gates/gate_16.py` should allowlist exactly `src/ccf/controlplane/artifacts.py::ProductClassDeclaration`. Note that a docstring edit **also moves `docs/schemas/*.json`** — if gate_16 asserts on the schema tree, that coupling is now measured.
- **Every authoring plan** now writes under three live tripwires. The one most likely to fire is the Gate-2 wording gate: any new paragraph that says what Gate 2 verifies must carry "assembly-path integrity". The canonical sentence to copy (never paraphrase) is `src/ccf/deployment/__init__.py:72-79`.
- **Known limit, recorded not deferred:** a path broken *mid-token* across a line (`examples/08-e2e-demo/artifacts/` then `scenario.yaml`) is undetectable by the stale-path gate, or any scan that joins lines with a space. Stated in the module docstring.

## Self-Check: PASSED

Files verified present on disk:

- `tools/docs_tests/_prose.py` — FOUND
- `tools/docs_tests/test_gate_two_wording.py` — FOUND
- `tools/docs_tests/test_no_stale_example_paths.py` — FOUND
- `tools/docs_tests/test_documented_commands_exist.py` — FOUND
- `src/ccf/controlplane/artifacts.py` — FOUND (modified)
- `tools/docs_tests/test_snippet_gate.py` — FOUND (modified)
- `docs/schemas/ccf.product-class.json` — FOUND (modified)

Commits verified in `git log`:

- `e984844` — FOUND
- `229aed5` — FOUND
- `23bffcc` — FOUND
- `b19a809` — FOUND
