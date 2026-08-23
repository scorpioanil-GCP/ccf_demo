---
phase: 22-the-adoption-argument-what-rag-hand-rolled-assembly-and-a-se
plan: 01
subsystem: published documentation surface
tags: [DOCS-15, concepts-page, snippet-include, s1-01, retirement-couplings]
status: work-complete-blocked-on-ruling
requires:
  - examples/s1-01-hello-context-product (unmodified; cited only)
  - tests/examples/test_s1_01_output.py (unmodified; cited only)
provides:
  - public/concepts/answers-no-document-contains.md (question + demonstration halves)
  - mkdocs.yml nav entry under Concepts
affects:
  - docs/surface/examples/RETIREMENT-COUPLINGS.md (13 new 17-08-owned rows)
  - .planning/phases/22-*/22-02-PLAN.md (contrast half builds on these sections)
tech-stack:
  added: []
  patterns: [prose-names-the-test-then-include, whole-file-artifact-include]
key-files:
  created:
    - public/concepts/answers-no-document-contains.md
    - .planning/phases/22-.../22-01-SUMMARY.md
  modified:
    - mkdocs.yml
    - docs/surface/examples/RETIREMENT-COUPLINGS.md
decisions:
  - "Nav wiring pulled forward from task 3 into task 1 (Rule 3 deviation) so no commit lands on main with a red strict build"
  - "spine.py:gate excluded on two measured grounds: 149 body lines and 15 pub01-whitepaper-shingle findings"
  - "expected.yaml included whole-file because no artifact under s1-01 carries a snippet marker and examples/ is fenced"
metrics:
  duration: ~55 min
  completed: 2026-08-23
  tasks: 3
  commits: 3 (+1 report follow-up)
---

# Phase 22 Plan 01: The question and the demonstration — Summary

A published Concepts page, `public/concepts/answers-no-document-contains.md`,
that states the UBO question as checkable facts about `s1-01`'s own artifacts
and shows what a governed answer has to do through five literal `--8<--`
includes from a CI-gated source — with zero changes under `examples/`.

**One blocking finding stands in the way of closing this plan, and it is not
this plan's work.** See *The blocker* below. Everything the plan asked for was
built and measured; one acceptance criterion of task 3 —
`pytest tools/publish_scan_tests tools/docs_tests -q` exit 0 with no deselect —
cannot be met because a **Phase 21** gate freezes `public/` against all future
commits. That needs Dave's ruling.

---

## What shipped

| Task | Name | Commit | Files |
| --- | --- | --- | --- |
| 1 | Create the page and write the question | `b71308b` | `public/concepts/answers-no-document-contains.md`, `mkdocs.yml` |
| 2 | What a governed answer has to do — three spine includes | `0b3b20d` | `public/concepts/answers-no-document-contains.md` |
| 3 | Prove the strict build, sabotage, regenerate the report | (see below) | `docs/surface/examples/RETIREMENT-COUPLINGS.md` |

The page is 173 lines. First line is exactly `# Answers no document contains`.
No YAML frontmatter.

## The five include directives, verbatim

```
public/concepts/answers-no-document-contains.md:69   --8<-- "examples/s1-01-hello-context-product/artifacts/ubo-question.yaml"
public/concepts/answers-no-document-contains.md:95   --8<-- "examples/s1-01-hello-context-product/artifacts/expected.yaml"
public/concepts/answers-no-document-contains.md:125  --8<-- "examples/s1-01-hello-context-product/spine.py:operators"
public/concepts/answers-no-document-contains.md:152  --8<-- "examples/s1-01-hello-context-product/spine.py:project"
public/concepts/answers-no-document-contains.md:172  --8<-- "examples/s1-01-hello-context-product/spine.py:serve"
```

`grep -c -- '--8<--'` returns `5`.

All five were confirmed **rendered**, not merely accepted — one distinctive
symbol per include, counted in the built site after `mkdocs build --strict`:

| Include | Probe symbol | Occurrences in `site/concepts/answers-no-document-contains/index.html` |
| --- | --- | --- |
| `ubo-question.yaml` | `natural_person_class` | 1 |
| `expected.yaml` | `obligation_third_question` | 1 |
| `spine.py:operators` | `build_operator_registry` | 1 |
| `spine.py:project` | `refuse_operator_set_divergence` | 1 |
| `spine.py:serve` | `QueryPinWriter` | 1 |

## Per-source `pub01-whitepaper-shingle` counts — measured, not assumed

Run in the venv against `tools.publish_scan.scan_text` with
`whitepaper_shingles()`, extracting each spine region between its own
`[start:]`/`[end:]` markers:

```
ubo-question.yaml:   0 pub01-whitepaper-shingle findings   (total findings 0)
expected.yaml:       0 pub01-whitepaper-shingle findings   (total findings 0)
spine.py:operators:  0 pub01-whitepaper-shingle findings   (total findings 0)
spine.py:project:    0 pub01-whitepaper-shingle findings   (total findings 0)
spine.py:serve:      0 pub01-whitepaper-shingle findings   (total findings 0)
spine.py:gate:      15 pub01-whitepaper-shingle findings   (total findings 15)
```

Both grounds for excluding `spine.py:gate` therefore hold, and both were
measured rather than inherited from the plan:

1. **Length** — the region spans lines 399–549 of `spine.py`, 149 body lines.
2. **It would fail `make docs-strict`** — 15 shingle findings, against 0 for
   each of the five sources this page ships. `make docs-strict`'s post-build
   scan reads the rendered site with HTML stripped, so a `<pre><code>` block is
   scanned as running words. No allowlist, no `--exit-zero` (the no-allowlist
   posture is the publish-scan ruling **D-20**, cited in `tools/publish_scan.py`
   and on `public/charter.md` — it is **not** a `22-CONTEXT.md` decision, which
   carries `D-01` through `D-15` only).

`events.yaml` (502 lines) and `source-estate.yaml` (576 lines) were not
included. `grep -c 'spine.py:gate\|events.yaml\|source-estate.yaml'` on the page
returns `0`.

## Why `expected.yaml` ships whole-file

`grep -rn -- "--8<--" examples/s1-01-hello-context-product/artifacts/` returns
nothing (exit 1) — **no artifact under `s1-01` carries a single snippet marker**.
A named-region include is therefore unavailable, and adding one would mean
editing `examples/`, which this plan's scope fence and ROADMAP criterion 7 both
forbid. Criterion 3 requires the claim be carried by a literal include rather
than by prose, so the choice was whole-file or nothing.

Whole-file is also the right trade independently: this artifact is the page's
answer key, and five of its declarations — `debt_signal_first_question: "ok"`,
`debt_signal_third_question: "forced_llm"`, `debt_weak_factor: freshness`,
`obligation_first_question` and `obligation_third_question` — are the entirety
of what carries ROADMAP criterion 11's evidence once plan 02 drops the
`debt-profile.yaml` include. **Do not trim this include to a slice.** A later
reader who slices it silently removes criterion 11's evidence path.

## Test node ids cited, and the command that proved each collects

Command, once per name:

```
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest "tests/examples/test_s1_01_output.py::<name>" --collect-only -q
```

| Node id | Precedes | Collect exit |
| --- | --- | --- |
| `test_the_product_answers_the_question_the_caller_asked` | `ubo-question.yaml` include | 0 |
| `test_the_aggregate_ownership_answer_matches_the_declared_expectation` | `expected.yaml` include | 0 |
| `test_the_answer_is_a_sum_over_paths_not_a_single_hop` | `expected.yaml` include | 0 |
| `test_every_declared_absence_really_is_absent` | `spine.py:operators` include | 0 |
| `test_a_different_company_gets_a_different_answer` | `spine.py:project` include | 0 |
| `test_the_same_company_at_a_later_instant_gets_a_different_answer` | `spine.py:project` include | 0 |
| `test_the_obligation_in_force_is_pinned_into_the_replay_record` | `spine.py:serve` include | 0 |

Every one is a `path::symbol` node id. The page carries **no** `file.py:NNN`
line citation — `grep -nE "[A-Za-z0-9_]+\.py:[0-9]+"` exits 1.

## Published-tree prohibitions, each measured

| Check | Result |
| --- | --- |
| `grep -nE "examples/0[0-8]\|examples/external/00-hello-context"` | exit 1 (nothing) |
| `grep -nE "[A-Za-z0-9_]+\.py:[0-9]+"` | exit 1 (nothing) |
| `grep -nE "DECISIONS\.md\|SPEC_INVENTORY\.md\|DESIGN\.md\|FEASIBILITY\.md\|ROADMAP\.md\|CCF_Whitepaper"` | exit 1 (nothing) |
| `grep -niE "RAG\|vector store\|vector database\|semantic layer\|prompt template\|hand-rolled\|hand rolled\|chunked"` | exit 1 (nothing) |
| `git status --porcelain examples/ src/ runtime/` | prints nothing |

Every figure on the page was checked against the artifact rather than against
memory. Occurrence counts across `expected.yaml` + `ubo-question.yaml`:
`30.000` × 6, `12.0` × 1, `60.0` × 3, `25.0` × 2, `30.0` × 8.

Note on the fourth grep: `RAG` case-insensitively is a substring of `storage`,
`paragraph`, `coverage`, `leverage` and `average`, so the page's prose avoids
those words too. Worth knowing before plan 02 edits it.

## Nav and the enumeration comment — measured numbers

- `grep -n "concepts/answers-no-document-contains.md" mkdocs.yml` → exactly one
  line, `mkdocs.yml:131`, inside `- Concepts:` and above `- Pillars:`.
- `find public -name '*.md' | wc -l` → **44**
- `grep -cE "^\s+- [^:]+: [a-z]" mkdocs.yml` → **44** (43 nav entries plus the
  one `not_in_nav` `charter.md` line)
- The comment above `nav:` was corrected from "42 pages … 43 markdown files" to
  "43 pages … 44 markdown files". Both new numbers match the measurements above.

## The three sabotage runs — watched failing, reverted, re-confirmed

Every run in the foreground, in the venv, with
`PYTHONPATH=.:src:runtime .venv/bin/python -m mkdocs build --strict`.

**1. Renamed marker** — `spine.py:operators` → `spine.py:operatorsX`.
Exit **1**:

```
ERROR   -  Error reading page 'concepts/answers-no-document-contains.md': Snippet section 'operatorsX' could not be located
  File ".../pymdownx/snippets.py", line 155, in extract_section
    raise SnippetMissingError(f"Snippet section '{section}' could not be located")
```

Reverted; `git diff --quiet` clean against HEAD; re-built exit **0**.

**2. Missing snippet FILE** — `artifacts/ubo-question.yaml` →
`artifacts/ubo-questionX.yaml`. Exit **1**:

```
ERROR   -  Error reading page 'concepts/answers-no-document-contains.md': Snippet at path 'examples/s1-01-hello-context-product/artifacts/ubo-questionX.yaml' could not be found
pymdownx.snippets.SnippetMissingError: Snippet at path '...ubo-questionX.yaml' could not be found
```

Reverted; clean; re-built exit **0**. This is the second of the two guards
`pymdownx.snippets` implements at separate call sites — the plan required both
be watched on *this page* rather than one standing for the pair, and both were.

**3. Deleted `nav:` entry.** Exit **1**:

```
WARNING -  The following pages exist in the docs directory, but are not included in the "nav" configuration:
  - concepts/answers-no-document-contains.md
```

(`validation.nav.omitted_files: warn` plus `strict: true` promotes it to a
build failure.) Restored from a backup copy; `git diff --quiet mkdocs.yml`
clean; re-built exit **0**.

## `make docs-strict`

Exit **0** on all four steps, in order: pre-build structural scan over
`public/`, the `docs/schemas` scan, `mkdocs build --strict`, and the post-build
content scan over `site/`.

## The coupling report

Regenerated **in the venv**, with exactly:

```
PYTHONPATH=.:src:runtime .venv/bin/python tools/retirement_sweep.py --report
```

`.venv/bin/python -c "import joserfc"` exits **0** — the interpreter that ran
the sweep has the dependency whose absence causes the silent six-row drop.

Sweep output: `257 coupling rows across 81 files (146 rows outside the three
swept trees); 1890 files scanned`.

| | Coupling rows | Files |
| --- | --- | --- |
| Committed at `951eb4a` | **244** | 80 |
| Committed at plan start (`ad50402`) | **244** | 80 |
| After regeneration | **257** | 81 |

The count **rose** by 13. It did not fall, so the silent-drop trap did not fire.
Rows owned by `17-08` went 58 → 71; `prose` 44 → 52; `snippet-include` 53 → 58.

**The thirteen new rows, verbatim.** Every one names the page and every one is
owned by `17-08` — ROADMAP criterion 10's mechanical half, observed here for the
first time so that plan 04 is confirming a measurement rather than discovering
one. The plan anticipated two rows; the measured landing is thirteen (five
snippet-include, eight prose):

```
| `public/concepts/answers-no-document-contains.md` | 33 | `examples/s1-01-hello-context-product` | `prose` | documentary | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 63 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 69 | `examples/s1-01-hello-context-product` | `snippet-include` | live | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 77 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 80 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 95 | `examples/s1-01-hello-context-product` | `snippet-include` | live | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 121 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 125 | `examples/s1-01-hello-context-product` | `snippet-include` | live | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 141 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 145 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 152 | `examples/s1-01-hello-context-product` | `snippet-include` | live | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 167 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 172 | `examples/s1-01-hello-context-product` | `snippet-include` | live | - | - | 17-08 |  |
```

`tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current`
is **green** after the regeneration, with no deselect.

The report was regenerated a **second** time after this SUMMARY was written,
because `tools/retirement_sweep.py` is an `os.walk` from the repo root and
`.planning/phases/22-*` files are already sweep subjects.

## The deselect flag, recorded verbatim

Tasks 1 and 2 ran their verification with exactly one deselect:

```
--deselect tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current
```

The reason: creating a page under `public/` — a swept tree — makes the
committed coupling report stale the moment task 1 writes it, and the report is
not regenerated until task 3. The deselect was **lifted** in task 3 after the
regeneration, and the test is green with no deselect in force.

---

## The blocker — a Phase 21 gate freezes `public/` forever

**This is the one thing standing between this plan and a clean close, and it is
a pre-existing defect in a closed phase's verification machinery, not a defect
in this plan's work.**

`tools/docs_tests/test_requirement_ledger.py::test_the_scope_fence_holds`
asserts:

```
git diff --stat <21-BASE-COMMIT>..HEAD -- src/ runtime/ examples/ public/ pyproject.toml
```

is **empty**. The base is pinned in
`.planning/phases/21-requirement-ledger-reconciliation-what-is-actually-discharge/21-BASE-COMMIT.txt`
at `c51406be1170259336e8799f5d4c69b2e39d4c8a`. The upper bound is `HEAD` — it is
**not** bounded to Phase 21's close commit.

Phase 21 closed at `D-GATE-21.1` / `951eb4a`. The assertion did not stop with
it. As written it now forbids **any** future commit anywhere under `src/`,
`runtime/`, `examples/`, `public/` or `pyproject.toml`, for the rest of the
repository's life. Phase 22's entire deliverable is one file under `public/`, so
the very first commit of this phase turned it red:

```
AssertionError: this phase wrote inside the `D-11` scope fence...
   public/concepts/answers-no-document-contains.md | 96 +++++++++++++++++++++++++
   1 file changed, 96 insertions(+)
```

**Scope of the damage, measured.** Of the four untouched-tree assertions built
on that base, exactly one is red:

| Assertion pathspec | `git diff --stat <base>..HEAD` | Status |
| --- | --- | --- |
| `src/ runtime/` | empty | green |
| `src/ runtime/ examples/ public/ pyproject.toml` (`FENCE`) | the new page, 96 insertions | **RED** |
| the eleven `*-VERIFICATION.md` records | empty | green |
| `tools/lints/citations.py` | empty | green |

Five further failures are **the controls working correctly, not separate
defects**: `CONTROL 18` (parameterised over `FENCE`'s five members) and
`CONTROL 35` both refuse to grade a mutation when the intact case is already
red — "a control that is red anyway is red under any mutation, so nothing below
about it would mean anything."

Full run:
`PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/publish_scan_tests tools/docs_tests -q`
→ **6 failed, 260 passed**. With the fence and its dependent controls
deselected, `tools/docs_tests` is **202 passed, 21 deselected, exit 0** — nothing
else in the docs gate is broken.

**Why this was not auto-fixed (deviation Rule 4).** Three independent reasons:

1. `tools/docs_tests/test_requirement_ledger.py` is a **Phase 21 deliverable
   approved at `D-GATE-21.1`**. Re-scoping a shipped gate is a governance
   ruling, not a bug fix.
2. **Phase 22's own plan 04 explicitly forbids it**: *"Do not edit
   `tools/docs_tests/test_requirement_ledger.py`."* Plan 04 also runs that
   module as its verification command, so plan 04 is blocked by the same thing.
3. `21-BASE-COMMIT.txt` says plan `21-06` *"re-asserts at the phase close"* —
   the unbounded upper bound may have been deliberate. Changing it silently is
   exactly the move this project treats as a defect
   (`CLAUDE.md` §15: surface gaps, do not paper over).

**This blocks every remaining plan in Phase 22**, all six of which write under
`public/`.

**The options, for Dave.**

| # | Option | Consequence |
| --- | --- | --- |
| 1 | Bound the four assertions to Phase 21's close commit (`951eb4a`) instead of `HEAD` | Preserves each assertion's stated meaning exactly — *"Phase 21 touched nothing"* — and unfreezes the tree. Requires a one-line change plus its controls in a closed phase's module, and a `D-IMPL-NN`. |
| 2 | Retire the four untouched-tree assertions now that Phase 21 is closed | Simplest. Loses the historical record that Phase 21 stayed inside its fence. |
| 3 | Move `public/` (and `examples/`) out of `FENCE` | Narrowest edit, but weakens what the fence meant during Phase 21 retroactively. |
| 4 | Revert this plan's two commits and stop | Discards correct work and only defers the same collision to the next attempt. |

Option 1 is the recommendation: it is the only one that leaves the Phase 21
assertion saying what it was written to say.

## Deviations from Plan

### Auto-fixed

**1. [Rule 3 — Blocking] Nav wiring pulled forward from task 3 into task 1**

- **Found during:** Task 1 verification.
- **Issue:** The plan's task 1 acceptance criterion requires
  `pytest tools/docs_tests -q` with only the retirement-sweep deselect to exit
  0. It does not.
  `tools/docs_tests/test_mkdocstrings_gate.py::test_the_unmodified_tree_builds_clean`
  builds the **real** tree, and a page under `public/` with no `nav:` entry
  trips `validation.nav.omitted_files` under `strict: true`. Following the plan
  literally would have put two commits on `main` with a red build.
- **Fix:** Made the `mkdocs.yml` edits (nav entry, placement comment,
  enumeration-comment correction) part of task 1 instead of task 3. Task 3 kept
  everything else it owns: the strict build, all three sabotage runs, and the
  report regeneration. No acceptance criterion was dropped — only re-ordered.
- **Files modified:** `mkdocs.yml`
- **Commit:** `b71308b`

### Not fixed — escalated

**2. [Rule 4 — Governance] Phase 21's `D-11` scope fence freezes `public/`**

See *The blocker* above. Escalated rather than fixed. Dave's ruling required.

## Threat Flags

None. This plan ships no runtime surface, no network-reachable code, no request
handler, no persistence and no authentication path. `T-22-01` and `T-22-02`
(information disclosure through includes and prose citations) were mitigated as
planned: every included artifact and spine region was read in full before
inclusion, the sources are synthetic FIBO data with `example.org` URIs, and
`make docs-strict`'s post-build site scan — no allowlist — is exit 0.
`T-22-03` (tampering with the strict settings) was mitigated by watching all
three failure modes fail and reverting rather than trusting them.

## Known Stubs

None. Every section this plan wrote is complete and every include resolves and
renders.

## Tracking deferred to the orchestrator

Per `docs/DECISIONS.md` **D-15**, no `state.*` or `roadmap.*` SDK writer was
invoked and neither `.planning/STATE.md` nor `.planning/ROADMAP.md` was
modified. Both are hand-edited by the orchestrator after the phase.
