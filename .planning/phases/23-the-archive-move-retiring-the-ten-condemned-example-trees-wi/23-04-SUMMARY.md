---
phase: 23-the-archive-move-retiring-the-ten-condemned-example-trees-wi
plan: 04
subsystem: the move — ten condemned example trees relocated to archive/examples/ as a pure rename set
tags: [DOCS-17, criterion-1, criterion-2, criterion-16, D-03, D-IMPL-193, VAC-01, red-before-green]
status: complete
requires:
  - phase: 23-03
    provides: seven scan roots and one glob-set already reaching `archive/`, each proven a no-op while `archive/` did not exist
provides:
  - 265 tracked files at `archive/examples/`, in ten trees, at commit `ef336f3`
  - criterion 1 discharged by a STRONGER proof than the plan specified — 265 R100 and a 0-insertion/0-deletion shortstat
  - criterion 2 discharged under a stated reading, with the rejected alternative recorded and its 265-vs-266 reason measured
  - the wreckage inventory, taken once over a tree whose only change is the move
  - a measured correction: the plan's R/D/M proof PASSES on a moved-and-edited file
affects:
  - 23-05 (the 216 `$schema` headers, `PY_BEARING_NON_EXAMPLES`; and the RED it must turn green)
  - 23-06 (the four `D-07` citation edits — and the finding that no gate can see them)
  - 23-07 (the five `CLNT-30` tests, `test_ext00_fixture_schemas`, `test_schema_export`, `perf_smoke`)
  - 23-08 (the 102 includes + 111 prose paths, both RED and both at their pinned figures)
  - 23-12 (criterion 1's re-verification should use the R100/shortstat form, not R/D/M)
tech-stack:
  added: []
  patterns: [pure-rename-set, VAC-01-tracked-file-floor, every-figure-carries-its-command, sabotage-the-proof-machinery-not-the-subject, stated-reading-over-implied-one]
key-files:
  created:
    - archive/examples/  # 265 files across ten trees
    - .planning/phases/23-the-archive-move-retiring-the-ten-condemned-example-trees-wi/23-04-SUMMARY.md
  modified:
    - .gitignore  # Rule 3: the archived `.store/` re-point
    - .planning/phases/23-the-archive-move-retiring-the-ten-condemned-example-trees-wi/deferred-items.md
    - docs/surface/examples/RETIREMENT-COUPLINGS.md  # generated; regenerated LAST, in the venv
decisions:
  - "Criterion 1's second clause is proven by `265 R100` + `0 insertions(+), 0 deletions(-)`, NOT by the plan's `--diff-filter=M` = 0. Sabotage D shows R/D/M passes on a moved-and-edited file."
  - "Criterion 2's reading is the plan's, used verbatim and not re-derived: an example tree is a directory directly under `examples/` holding at least one tracked file other than its own README.md."
  - "`examples/external/README.md` stays. Moving it would make `archive/` 266 and contradict criterion 1's 265."
  - "The plan predicted `tools.lints --all` non-zero after the move. It exited 0, and the 0 is CORRECT — a move that changes no bytes cannot create a CINV finding. The widening's proof is that the walk reaches 24 archived modules, not that it goes red."
requirements-completed: []
metrics:
  duration: ~1h45m
  completed: 2026-08-24
  tasks: 3
  commits: 3
---

# Phase 23 Plan 04: The move — Summary

**265 files moved from `examples/` to `archive/examples/` in one commit that
changed zero bytes.** `git show -M --shortstat` on `ef336f3` reads *265 files
changed, 0 insertions(+), 0 deletions(-)*, and every one of the 265 entries is
`R100`. Criterion 1 is discharged — and discharged by a stronger proof than the
plan specified, because **sabotage showed the plan's proof was insufficient**.

**Tests added by this wave: NONE.** Criterion 7's per-wave roster for `23-04`
is empty (`D-IMPL-196`). Measured against **this wave's own commit**, not against
`PHASE_BASE` — see the roster section for why that distinction bit once already:

```bash
git show ef336f3 -- tests/ | grep -c '^+def test_'              # 0
git show ef336f3 -- tests/ | grep -c '^-def test_'              # 0
git show --name-only --format= ef336f3 -- tests/ | grep -c .    # 0  (no path under tests/ touched)
```

---

## Task 1 — the move, and the rename-set proof

### The commands, exactly as run

```bash
mkdir -p archive/examples/external
for t in 00-quickstart 01-agent-basics 02-skilling 03-harness-portability \
         04-cross-process 05-workflow-hitl 06-decision-replay \
         07-artifact-store-mcp 08-e2e-demo; do
  git mv "examples/$t" "archive/examples/$t"
done
git mv examples/external/00-hello-context archive/examples/external/00-hello-context
```

All ten succeeded silently. Commit: **`ef336f3`**.

### The proof, taken on the STAGED move, before committing

```bash
git diff --cached -M --diff-filter=R --name-only | wc -l   # 265
git diff --cached -M --diff-filter=D --name-only | wc -l   # 0
git diff --cached -M --diff-filter=M --name-only | wc -l   # 0
git diff --cached -M --diff-filter=A --name-only | wc -l   # 0
git diff --cached -M --diff-filter=C --name-only | wc -l   # 0
git diff --cached -M --diff-filter=T --name-only | wc -l   # 0
git diff --cached -M --name-only | wc -l                   # 265  (nothing outside the six filters)
```

And re-taken on the commit:

```bash
git show -M --name-status --format= HEAD | awk 'NF{print $1}' | sort | uniq -c
#   265 R100
git show -M --shortstat --format= HEAD
#   265 files changed, 0 insertions(+), 0 deletions(-)
git show -M --name-only --format= HEAD | grep -v '^archive/examples/' | wc -l
#   0        — nothing in the commit lies outside archive/examples/
```

### CORRECTION 1 — the plan's three-command proof is INSUFFICIENT, and sabotage says so

The plan asserts `R`=265, `D`=0 and **`M`=0**, with `M`=0 carrying the weight of
criterion 1's *"no file content changed in the move"*. It does not carry it.

Four sabotages, run in a **throwaway repo in the scratchpad, never in this
tree** (`git init` in `$SCRATCH/proofrepo`), because the subject under test here
is the proof machinery, not the tree:

| # | Mutation | Prediction | Observed | Held? |
|---|---|---|---|---|
| **S-P1** (control) | a pure 3-file rename set | `R=3 D=0 M=0`, shortstat `0 insertions, 0 deletions` | exactly that | — |
| **S-P2** | one of three DELETED instead of moved | `D` must rise | `R=2 D=1 M=0`; `D` names `a/f3.txt` | **YES** |
| **S-P3** | all three moved, one small file EDITED in flight | *"`M` rises"* | **`R=2 D=1 M=0`** — it surfaced as `D`+`A`, never as `M` | **CORRECTION** |
| **S-P4** | a **large** file moved AND lightly edited (similarity stays high) | — | **`R=3 D=0 M=0` — the plan's proof PASSES.** `name-status` shows `R099`, shortstat shows `1 insertion(+)` | **PROOF DEFEATED** |

**S-P4 is the finding.** A file that is moved *and* edited, where the edit is
small relative to the file, is still detected as a rename, so `R` counts it,
`D` stays 0, and `M` stays 0 — because `M` can only ever fire on a path that did
*not* move. On a 265-file rename set, `--diff-filter=M = 0` is very nearly
vacuous: it tests a population that is empty by construction.

What actually proves the second clause, and what holds on `ef336f3`:

- **every entry is `R100`** — exact similarity, zero entries at `R099` or below
  (`git show -M --name-status --format= HEAD | awk 'NF && $1!="R100"' | wc -l` → `0`);
- **`shortstat` is `0 insertions(+), 0 deletions(-)`**.

Both were measured. `M`=0 is retained as a *different* and still-useful check —
it catches an unrelated file sneaking into the commit — but it is recorded here
as not being the check the plan's prose says it is. **`23-12` should re-verify
criterion 1 in the `R100` + shortstat form.**

### CORRECTION 2 — the worktree/index trap, demonstrated rather than asserted

`T-23-12` says a proof run without `--cached` while the move is staged proves
nothing. Sabotage **S-P5**, on the pure-rename control:

```
WITHOUT --cached: R=0  D=0     <- reads as a perfectly clean tree
WITH    --cached: R=3  D=0
```

A reader handed only `R=0 D=0` would call that a clean result. Every figure in
this summary was taken with `--cached` while staged, or with `git show -M` after
the commit.

### The `VAC-01` guard (S-15) — the floors beside the diff

```bash
git ls-files archive/ | wc -l        # 265
```

Per tree, so a single tree left behind cannot hide inside the total:

| tree | tracked |
|---|---:|
| `00-quickstart` | 18 |
| `01-agent-basics` | 24 |
| `02-skilling` | 23 |
| `03-harness-portability` | 27 |
| `04-cross-process` | 33 |
| `05-workflow-hitl` | 21 |
| `06-decision-replay` | 32 |
| `07-artifact-store-mcp` | 19 |
| `08-e2e-demo` | 29 |
| `external/00-hello-context` | 39 |
| **sum** | **265** |

Every count `> 0`; the ten sum to 265; the per-tree counts are **byte-identical
to the same ten counts taken under `examples/` before the move**, which were
recorded first for exactly this comparison.

### No `s1` tree moved, and no `hw1` tree either (criterion 13's second clause, `D-01`)

```bash
git ls-files examples/s1-00-companies-over-revenue examples/s1-01-hello-context-product | wc -l   # 37
git diff --cached --name-only -- examples/s1-00-companies-over-revenue examples/s1-01-hello-context-product
#   (EMPTY)
git ls-files examples/hw1-companies-over-revenue examples/hw1-harness-clients | wc -l             # 19
git diff --cached --name-only -- examples/hw1-companies-over-revenue examples/hw1-harness-clients
#   (EMPTY)
```

Both empty diffs are `VAC-01`-guarded: the same pathspecs name **37** and **19**
tracked files, so the emptiness is a clean result and not a misspelling.

`examples/external/README.md` and `examples/.gitkeep` are both still tracked and
both absent from the commit.

### The `D-07` fence

```bash
git diff --stat b87fe58..HEAD -- src/ runtime/ pyproject.toml   # (EMPTY)
git ls-files src/ runtime/ pyproject.toml | wc -l               # 214   <- VAC-01 floor
```

The four permitted citation edits belong to `23-06`. None was made here.

---

## Task 2 — criterion 2, under a stated reading

### The reading, verbatim from the plan and NOT re-derived

> An **example tree** is a directory directly under `examples/` that holds at
> least one tracked file other than that directory's own `README.md`.
> `examples/.gitkeep` is a tracked file at the top level of `examples/`, not a
> directory, so it is not a tree. `examples/external/` after the move holds
> only its family-charter `README.md`, so it is a family CONTAINER, not a tree.

### The reading implemented as a command, not as prose

```bash
git ls-files examples/ | awk -F/ 'NF>2 {print $2}' | sort -u
# external  hw1-companies-over-revenue  hw1-harness-clients
# s1-00-companies-over-revenue  s1-01-hello-context-product
```

Per candidate, tracked files whose basename is not that directory's own README:

| candidate | tracked | non-own-README | verdict |
|---|---:|---:|---|
| `external` | 1 | **0** | container (README only) |
| `hw1-companies-over-revenue` | 10 | 9 | **TREE** |
| `hw1-harness-clients` | 9 | 8 | **TREE** |
| `s1-00-companies-over-revenue` | 11 | 10 | **TREE** |
| `s1-01-hello-context-product` | 26 | 25 | **TREE** |

**Four trees**, and they are the four the criterion names.

### Second clause — nothing condemned remains under `examples/`

```bash
git ls-files examples/00-quickstart … examples/external/00-hello-context   # (EMPTY), count 0
# VAC-01 guard on that emptiness — the same ten pathspecs rooted at archive/:
git ls-files archive/examples/00-quickstart … archive/examples/external/00-hello-context | wc -l   # 265
```

### The rejected alternative, recorded because it is reversible

Moving `examples/external/README.md` into the archive would make `examples/`
yield exactly four top-level directories under the plainest possible reading.
Measured cost:

```bash
echo $(( $(git ls-files archive/ | wc -l) + $(git ls-files examples/external/README.md | wc -l) ))   # 266
```

**266, against criterion 1's locked 265.** A stated reading is preferred over a
number that contradicts a locked criterion. If Dave prefers the other at the
close it is a two-command change.

### Recorded for `23-09`, and edited by nobody here

`examples/external/README.md` now describes a family whose only member has left:

```bash
grep -n "00-hello-context\|03-harness-portability" examples/external/README.md
# 50:| `00-hello-context` | Hello world — minimal financial-services scenario: …
# 61:(structural analog: `examples/03-harness-portability`):
```

Both confirmed at the lines the plan named. Untouched here.

---

## Task 3 — the wreckage, measured once

Every command below was run in the **FOREGROUND**. Longest single run: 4m17s.

### The three legs that stayed GREEN — and why each green is legitimate

| Leg | Command | Exit |
|---|---|---:|
| lint | `make lint` (`tools.lints --all`) | **0** |
| typecheck | `make typecheck` — *Success: no issues found in 211 source files* | **0** |
| chunks B and C of the test leg | see below | **0** |

#### CORRECTION 3 — `tools.lints --all` exiting 0 was predicted WRONG, and the 0 is right

The plan says: *"plan 23-03 widened it, so a non-zero exit here is the widening
WORKING and a zero exit is a claim that needs checking, not a relief."*

It exited **0 with zero lines of output**. Checked rather than accepted:

```python
from tools.lints.__main__ import LINTED_TREES, iter_python_files
# src 141 · runtime 70 · examples 18 · tests 289 · archive 24   TOTAL 542
```

**The walk reaches 24 archived Python modules** — exactly the 24 `.py` files
wave 3 measured in the ten trees. The lint is not looking at nothing; it is
looking at all of them and finding nothing. **A move that changes zero bytes
cannot create a CINV finding**, because every CINV rule is a property of file
content. The widening's evidence is the non-empty walk, not a red exit. The
plan's prediction was written as if the archive move could produce a hardcoding
or import violation; it cannot.

#### Chunk B green is the four count floors HOLDING, which is what 23-03 bought

Every floor is unchanged and every one is now met with the archive contributing:

| Gate | floor | count | partition |
|---|---:|---:|---|
| `MINIMUM_IMPLEMENTATIONS` (`test_required_operators_guard`) | 9 | **14** | `src 2 · examples 3 · archive 9` |
| `MINIMUM_GATE_CALL_SITES` (`test_gate_two_call_shape`) | 12 | **12** | `src 1 · examples 2 · archive 9` |
| `MINIMUM_PROJECTING_BODIES` | 14 | **14** | `examples 3 · archive 11` |
| `MINIMUM_RESOLVED_BINDER_SITES` | 12 | **12** | (12 sites, path not exposed on the record) |
| `MINIMUM_SCANNED_CITATION_HOSTS` | 953 | **1111** | — |
| `MINIMUM_CITATIONS_READ` | 797 | **1762** | — |

Pre-move (wave 3) the partitions read `examples 12`, `examples 11`, `examples
14`. Every unit crossed from `examples` to `archive` and **no total moved.**
`23-RESEARCH.md` §7.2 predicted all five of these RED on a bare move; wave 3's
widenings are why they are not.

### 1. Collection — the drop is **8**, not the 69 the research measured on a bare move

```bash
PYTHONPATH=src:runtime CCF_REQUIRE_HARNESSES=1 .venv/bin/python -m pytest --collect-only -q
# pre-move  (HEAD~1): 4231 tests collected     EXIT=0
# post-move (HEAD)  : 4223 tests collected     EXIT=0
```

Node-id set arithmetic rather than a headline number:

- **73 lost**, **65 gained**, net **−8**.
- Of the 73 lost, **61 are recovered at an `archive/…` re-path** — the same test,
  the same parametrization, a new path in the id.

| module | lost | gained | recovered by re-path | net |
|---|---:|---:|---:|---:|
| `tests/products/test_gate_two_call_shape.py` | 42 | 42 | 42 | 0 |
| `tests/products/test_required_operators_guard.py` | 9 | 9 | 9 | 0 |
| `tests/examples/test_artifact_schema_headers.py` | 10 | 10 | 10 | 0 |
| `tests/examples/test_ext00_fixture_schemas.py` | **12** | **4** | **0** | **−8** |

**The entire net loss is one module**, and it is `23-RESEARCH.md`'s S-9 shape
again — the one wave 3 hit at `S-F1`. `test_ext00_fixture_schemas.py` walks
`EXAMPLE_DIR = REPO_ROOT/"examples"/"external"/"00-hello-context"`, which wave 3
did not widen (`23-06` and `23-07` own it). The walk finds nothing, and its four
parametrized tests collapse from 12 real cases to four `[NOTSET]` cases:

```
tests/examples/test_ext00_fixture_schemas.py::test_anthropic_request_fixture_shape[NOTSET]
tests/examples/test_ext00_fixture_schemas.py::test_anthropic_response_fixture_validates[NOTSET]
tests/examples/test_ext00_fixture_schemas.py::test_gemini_request_fixture_shape[NOTSET]
tests/examples/test_ext00_fixture_schemas.py::test_gemini_response_fixture_validates[NOTSET]
```

Each reports `SKIPPED … got empty parameter set for (path)`. **A skip is not a
red.** The twelve node ids below are the ones a naive "did anything fail?" read
would never see, and they are `23-06`/`23-07`'s obligation:

```
::test_anthropic_request_fixture_shape[anthropic-00-request.json]  [anthropic-01-request.json]
::test_anthropic_response_fixture_validates[anthropic-00.json]     [anthropic-01.json]
::test_gemini_request_fixture_shape[gemini-00-request.json] [gemini-01-request.json] [gemini-02-request.json] [gemini-03-request.json]
::test_gemini_response_fixture_validates[gemini-00.json] [gemini-01.json] [gemini-02.json] [gemini-03.json]
```

The research's prediction of **4223 → 4154** was measured on a bare move with
the gates not widened. Waves 2 and 3 recovered 61 of the 69. The residual 8 is
one un-widened walk.

### 2. The test leg — three foreground chunks

The chunk plan from `23-02` was re-proven against the post-move collection
before it was trusted:

```bash
comm -12 ids-A ids-B | wc -l   # 0
comm -12 ids-A ids-C | wc -l   # 0
comm -12 ids-B ids-C | wc -l   # 0
diff -q ids-union ids-full     # SET-EQUAL
# A 1405 + B 1410 + C 1408 = 4223
```

```bash
PYTHONPATH=src:runtime CCF_REQUIRE_HARNESSES=1 .venv/bin/python -m pytest -q $CHUNK_A
#  53 failed, 1090 passed, 65 skipped, 197 errors in 257.81s   EXIT=1
PYTHONPATH=src:runtime CCF_REQUIRE_HARNESSES=1 .venv/bin/python -m pytest -q $CHUNK_B
#  1410 passed in 229.42s                                      EXIT=0
PYTHONPATH=src:runtime CCF_REQUIRE_HARNESSES=1 .venv/bin/python -m pytest -q $CHUNK_C
#  1349 passed, 59 skipped in 101.41s                          EXIT=0
```

**Summed: 3849 passed / 53 failed / 197 errors / 124 skipped.**
`3849 + 53 + 197 + 124 = 4223`, reconciling with the collection.
Base for comparison, `23-03`'s measured **4113 passed / 118 skipped / 0 failed**.

*Method note:* chunk A was first run with `-p no:randomly`. `pytest-randomly` is
not installed in this venv, so the flag was inert; chunk A was re-run under the
exact `23-02` command and produced the identical `53 failed, 1090 passed, 65
skipped, 197 errors`. Only that command's figures are reported above.

#### The 250 failing/erroring node ids in chunk A, by module

| module | kind | count |
|---|---|---:|
| `tests/examples/test_workflow_hitl_output.py` | errors | 37 |
| `tests/examples/test_decision_replay_output.py` | errors | 34 |
| `tests/examples/test_ext00_hardening.py` | failures | 27 |
| `tests/examples/test_e2e_demo_output.py` | errors | 19 |
| `tests/examples/test_cross_process_output.py` | errors | 19 |
| `tests/examples/test_skilling_output.py` | errors | 18 |
| `tests/examples/test_agent_basics_output.py` | errors | 17 |
| `tests/examples/test_ext00_serve_output.py` | errors | 15 |
| `tests/examples/test_harness_portability_output.py` | errors | 13 |
| `tests/examples/test_artifact_schema_headers.py` | failures | 12 |
| `tests/examples/test_artifact_store_output.py` | errors | 10 |
| `tests/examples/test_quickstart_output.py` | errors | 9 |
| `tests/examples/test_hw1_harness_clients_retirement.py` | failures | 5 |
| `tests/examples/test_demo_generator.py` | errors | 4 |
| `tests/examples/test_ext00_fixture_schemas.py` | failures | 3 |
| `tests/examples/test_harness_portability_output.py` | failures | 2 |
| `tests/examples/test_artifact_store_output.py` | failures | 2 |
| `tests/examples/test_gate_two_divergence.py` | errors | 2 |
| `tests/perf_smoke/test_smoke.py` | failures | 1 |
| `tests/cli/test_schema_export.py` | failures | 1 |
| **total** | | **250** |

**Exactly two failures fall outside `tests/examples/`**, and both are already
owned by `23-07`:

- `tests/cli/test_schema_export.py::test_every_quickstart_artifact_is_annotated_or_deferred`
- `tests/perf_smoke/test_smoke.py::test_suite_runs_untimed[crossproc]` — `23-RESEARCH.md`
  §7.5's *"one live path construction, in the always-on suite"*

#### The skip delta — +6, and only 4 of them are the ones you would expect

`118 → 124`. Four are the `[NOTSET]` empty-parametrization skips above. **The
other two are a silent PASS→SKIP degradation and matter more:**

```
SKIPPED tests/examples/test_artifact_schema_headers.py:489:
  examples/external/00-hello-context/fixtures: retired with the external example at wave 11 (plan 16-18)
SKIPPED tests/examples/test_artifact_schema_headers.py:489:
  examples/03-harness-portability/legs: retired with example 03 at wave 8 (plan 16-17)
```

`test_the_predicate_excludes_the_py_bearing_non_examples` is parametrized over
`PY_BEARING_NON_EXAMPLES`, whose keys are literal `examples/…` strings. Its
docstring says the control *"degrades to a named skip rather than turning red"*
once the wave that **retires** each has run. It was written for a wave that
**deletes**; this wave **moved**. So:

- the two node ids did not change, so they appear in neither the lost nor the
  gained set — **the collection arithmetic cannot see this at all**;
- the skip message now asserts something false on the tree: the directories were
  not retired by plan `16-18`/`16-17` (both retired phases), they exist, at
  `archive/examples/…`;
- **the control has stopped controlling, and nothing is red to say so.**

`23-05` already owns `PY_BEARING_NON_EXAMPLES`. This is recorded so `23-05` does
not wait for a red that will not arrive.

### 3. `make gate-tools` — EXIT 2, **13 failed / 316 passed**

`tools/lints/tests` (Makefile:189) passed clean: **415 passed in 7.23s**. The
failure is the second command, Makefile:190.

```
FAILED tools/docs_tests/test_mkdocstrings_gate.py::test_an_unresolvable_identifier_fails_the_strict_build
FAILED tools/docs_tests/test_mkdocstrings_gate.py::test_a_renamed_identifier_fails_the_strict_build
FAILED tools/docs_tests/test_mkdocstrings_gate.py::test_the_unmodified_tree_builds_clean
FAILED tools/docs_tests/test_no_stale_example_paths.py::test_every_prose_path_reference_resolves_on_disk
FAILED tools/docs_tests/test_no_stale_example_paths.py::test_every_snippet_include_resolves_on_disk
FAILED tools/docs_tests/test_no_stale_example_paths.py::test_the_unmodified_copy_passes
FAILED tools/docs_tests/test_no_stale_example_paths.py::test_a_tests_examples_path_is_not_mis_reported_as_a_bare_examples_path
FAILED tools/docs_tests/test_requirement_ledger.py::test_every_cited_path_in_a_status_cell_resolves_as_written
FAILED tools/docs_tests/test_resolver_seam_obligations.py::test_the_seam_cites_a_shipped_example_that_exists[ccf_runtime.mcp.egress.ProductResolverProtocol]
FAILED tools/docs_tests/test_resolver_seam_obligations.py::test_the_seam_cites_a_shipped_example_that_exists[ccf_runtime.mcp.experience.ExperienceProductResolverProtocol]
FAILED tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current
FAILED tools/docs_tests/test_snippet_gate.py::test_a_deleted_section_marker_fails_the_strict_build
FAILED tools/docs_tests/test_snippet_gate.py::test_the_unmodified_source_builds_clean
```

**Module for module, this is exactly `23-RESEARCH.md` §7.3's trial table.** The
research measured 313 passed / 13 failed; the count is now 316 passed because
waves 2 and 3 added tests, and the thirteen are the same thirteen.

### 4. `make docs-strict` — EXIT 2, failing at step 3 of 4

```bash
tools/publish_scan.py --pre-build      # PASSED
tools/publish_scan.py docs/schemas     # PASSED
python -m mkdocs build --strict        # FAILED  (Makefile:520)
```

```
ERROR   -  Error reading page 'how-to/bind-a-harness-adapter.md':
           Snippet at path 'examples/03-harness-portability/artifacts/agents/agent-definition.yaml'
           could not be found
pymdownx.snippets.SnippetMissingError: Snippet at path
  'examples/03-harness-portability/artifacts/agents/agent-definition.yaml' could not be found
```

A `SnippetMissingError` naming a path, as the plan predicted. `mkdocs --strict`
aborts on the first, so the build reports **one** of 102; the independent witness
below reports all of them at once, which is the point of criterion 5 having two.

### 5. The two independent witnesses for criterion 5 — RED, at the pinned figures

```python
from tools.docs_tests import test_no_stale_example_paths as M
pages = sorted(pathlib.Path("public").rglob("*.md"))       # 44 pages scanned
len(M.include_offenders(pages))      # 102   across 15 pages
len(M.prose_path_offenders(pages))   # 111   across 15 pages
```

**102 and 111 across 15 pages — `D-08`'s pinned figures, reproduced exactly, on
a tree where the only change is the move.** The 9 that criterion 6 counts is
`111 − 102`. The offender lists name every page and every line; they are in the
`gate-tools` log and are `23-08`'s work list.

The two witnesses are visibly independent here: the strict build died after one
offender, the walk enumerated all 111.

### 6. The citation walk — and an unexpected identity that turned out to be a finding

```
scanned_citation_hosts = 1111   floor MINIMUM_SCANNED_CITATION_HOSTS = 953
citations_read         = 1762   floor MINIMUM_CITATIONS_READ         = 797
```

Both above their floors, so `test_the_citation_walk_is_not_vacuous` is green.
But these differ from wave 3's `1109 / 1742`, which on a pure rename should be
impossible. Rather than assume, the pre-move tree was materialised read-only and
measured with the same checker:

```bash
git archive HEAD~1 | tar -x -C $SCRATCH/premove-tree      # 1986 files == git ls-tree HEAD~1
python -m tools.lints --citations --report --base $SCRATCH/premove-tree
python -m tools.lints --citations --report --base .
```

**All eight output lines are byte-identical** — 1762 matched in 1111 files, 1300
checked and passing, 0 findings, 39 path-unresolvable. So the `+2/+20` against
wave 3 is wave 3's own added test files, not the move. The `--base` flag was
proven live first (empty tree → `0 matched in 0 files`; `src`-only tree → `353
matched in 141 files, 317 unresolvable`), so the identity is a result and not an
ignored argument.

**And the identity is itself the finding.** `tools/lints/citations.py::resolve_cited`
falls back to suffix matching, so `examples/04-cross-process/producer_child.py`
resolves — via the single candidate `archive/examples/04-cross-process/producer_child.py`
— and is reported *checked and passing* while naming a path that no longer
exists. This is a second, stronger hole than the one `D-07`/`D-IMPL-192` records:
that one leaves a citation **unchecked**; this one leaves it **green and false**.
Logged to `deferred-items.md` item 4, not fixed. **`23-06` must not read a green
`make lint` as evidence that it made the four permitted edits.**

### 7. The coupling report — regenerated LAST, and its delta is a perfect mirror

```bash
PYTHONPATH=.:src:runtime .venv/bin/python tools/retirement_sweep.py --report
# wrote docs/surface/examples/RETIREMENT-COUPLINGS.md
# 394 coupling rows across 116 files (273 rows outside the three swept trees); 1948 files scanned
```

| figure | before | after | delta |
|---|---:|---:|---:|
| coupling rows | 285 | **394** | **+109** |
| files carrying a row | 82 | 116 | +34 |
| rows outside the three swept trees | 164 | 273 | +109 |
| refs *dropped* because their source is itself inside a retiring path | 235 | **126** | **−109** |

`285 + 109 = 394` and `235 − 109 = 126`. **The two deltas are the same 109 rows,
moving from one column to the other**, and the mechanism is exactly the one
`D-05` describes: `tools/retirement_sweep.py:131-167` still hardcodes the twelve
trees at their `examples/…` paths, so a reference *from* `archive/examples/…`
is no longer recognised as coming from inside a retiring path, stops being
dropped, and becomes a counted coupling. 110 rows in the new report name an
`archive/examples/` path.

This is `D-05`'s *"archived paths STILL count as couplings"* arriving by
accident before `23-10` re-points the table deliberately. It is **not** a repair
and must not be read as one — the rows are counted with the wrong owner
(`16-15`/`16-17`/`16-18`/`17-08`, all retired or blocked) until `23-10` runs.

`tools/docs_tests/test_retirement_sweep.py` is **47 passed** after the
regeneration, including `test_the_committed_report_is_current`, which was RED
before it.

**Final regeneration**, run after this summary was written (writing any
`.planning/` file stales the report — the standing Rule-3 deviation waves 1–3
also recorded):

```
395 coupling rows across 117 files (274 rows outside the three swept trees); 1931 files scanned
```

`394 → 395` and `116 → 117` is this summary itself becoming a coupling source.
`1948 → 1931` files scanned is exactly the **17** `.store/` files the `.gitignore`
deviation above took out of the walk — the two numbers reconcile.

---

## The wreckage mapped onto the criteria it is evidence FOR

| Criterion | RED evidence taken here | Turned green by |
|---|---|---|
| **5** (`S-1`, `S-2`) | `SnippetMissingError` from `mkdocs --strict` **and**, independently, `include_offenders` = **102** / `prose_path_offenders` = **111** over 15 pages | `23-08` |
| **8** (`S-6`, `S-7`) | `tests/examples/test_cross_process_output.py` — **19 errors**; `tests/examples/test_ext00_hardening.py` — **27 failures**. Both execute rather than read; both die on the `parents[N]` REPO_ROOT computations (`23-RESEARCH.md` §8.2) | `23-05` / `23-07` |
| **10** (`S-10`) | `tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current` — FAILED, the staleness half. Green again only after the report was regenerated LAST; the sweep's own `Retirement` table is still un-re-pointed | `23-10` |
| **1** | discharged here: `265 R100`, `0 insertions(+), 0 deletions(-)` | — |
| **2** | discharged here under a stated reading: four trees, zero condemned paths remaining | — |
| **16** (moved-file half) | discharged here: `git ls-files archive/` = 265, ten per-tree floors all `> 0` | — |

### `D-IMPL-193`'s five — RE-POINT, never remove

`tests/examples/test_hw1_harness_clients_retirement.py`, all five RED:

```
::test_the_historical_example_keeps_all_three_of_its_clients
::test_nothing_is_untracked_under_the_historical_example
::test_no_tracked_file_under_the_historical_example_is_dirty
::test_two_of_these_names_under_examples_is_the_mandated_state[client_adk.py]
::test_two_of_these_names_under_examples_is_the_mandated_state[client_anthropic.py]
```

`23-07` turns these GREEN **by re-pointing**. `D-09`/`D-IMPL-193` is explicit:
satisfying this by removing or weakening a test is a scope breach.

---

## Predictions, including the wrong ones

| Prediction | Source | Outcome |
|---|---|---|
| 265 renames, 0 deletions | plan task 1 | **HELD** |
| `--diff-filter=M` = 0 proves no content changed | plan task 1 | **FALSIFIED** — S-P4 passes R/D/M on a moved-and-edited file. Replaced by `R100`-for-all + zero shortstat, both measured |
| `--diff-filter=M` rises on a moved-and-edited file | S-P3 | **FALSIFIED** — it surfaces as `D`+`A` |
| the collection drop should be smaller than 69 | plan task 3 item 1 | **HELD** — it is 8 |
| a non-zero `tools.lints --all` exit is the widening working | plan task 3 item 5 | **FALSIFIED** — exit 0 is correct; the widening's evidence is a 24-module walk, not a red |
| `docs-strict` fails with a `SnippetMissingError` naming a path | plan task 3 item 4 | **HELD**, verbatim |
| `gate-tools` reproduces §7.3's 13 | plan / research | **HELD**, module for module |
| the four count floors break | `23-RESEARCH.md` §7.2 | **FALSIFIED by wave 3, as designed** — all four hold, with `archive` supplying the units `examples` used to |

**An unexpected GREEN was treated as a finding in every case**: chunk B, chunk C,
`make lint` and `make typecheck` were each opened up rather than accepted, and
each has a stated reason above.

---

## Deviations from Plan

### `[Rule 3 - Blocking]` `.gitignore` stopped matching the archived `.store/`, leaving 17 generated files untracked

**Found during:** task 3, at the post-run `git status` check.
**Issue:** `.gitignore:20` reads `examples/external/*/.store/`. After the move it
no longer matches, and the ext00 example — which stays RUNNABLE by `D-04` and is
executed by `tests/examples/test_ext00_hardening.py` — wrote **17** files to
`archive/examples/external/00-hello-context/.store/` during this wave's own test
runs. They showed as untracked, one `git add -A` away from being committed as
repository content.
**Not owned by any plan:** neither `.gitignore` nor `.store` appears in
`23-RESEARCH.md` or in any of `23-01`…`23-13`.
**Fix:** one added line, the identity re-point of the existing one under the same
prefix substitution the whole phase uses:

```
examples/external/*/.store/
archive/examples/external/*/.store/
```

**Proven not inert and not too broad**, rather than eyeballed:

```bash
git check-ignore -v archive/examples/external/00-hello-context/.store/x
#   .gitignore:26:archive/examples/external/*/.store/   <- matches
git check-ignore -v archive/examples/external/00-hello-context/serve.py   # exit 1 — NOT ignored
git check-ignore -v archive/examples/00-quickstart/run.py                 # exit 1 — NOT ignored
git ls-files archive/ | wc -l                                             # 265 — nothing newly ignored
```

**Files modified:** `.gitignore`. **Commit:** see the commit table.
**Why fixed rather than deferred:** the alternative is leaving generated runtime
output visibly untracked across five more waves, where a single `git add -A` by
any later executor commits it. That is a hazard the phase created and a
one-line, path-string-only repair; deferring it would be deferring a trap.

### The rest — none affecting scope

Three Rule-3-adjacent measurement additions, all
non-mutating and all inside the plan's own discipline:

1. **The proof-machinery sabotages (S-P1…S-P5)** were not in the plan. They were
   run because the plan asked for a proof and the standing discipline is that a
   guard is proven by sabotage. They found the plan's proof insufficient, which
   is the reason the discipline exists. Run in a throwaway `git init` repo in the
   scratchpad; **this tree was never mutated by them**.
2. **`git archive HEAD~1` into the scratchpad** to compare the citation scan
   pre- and post-move. Read-only extraction; no checkout, no stash, no reset in
   this tree.
3. **`docs/surface/examples/RETIREMENT-COUPLINGS.md`** was absent from the plan's
   `files_modified` (as it was for waves 1–3). Added to this summary's
   frontmatter and regenerated LAST.

**No `git clean`, no `git stash`, no `git checkout --`, no `git reset` was run in
this repository at any point.**

`CLNT-17` receives no verdict, limb or disposition here, and appears in no commit
message. `.planning/STATE.md` and `.planning/ROADMAP.md` are untouched (`D-10`,
`D-15`). No Success Criterion was authored, renumbered or edited.

---

## Tests added by this wave — criterion 7's roster

**NONE.** `23-04` adds zero test functions and removes zero.

```bash
git show ef336f3 -- tests/ | grep -c '^+def test_'              # 0
git show ef336f3 -- tests/ | grep -c '^-def test_'              # 0
git show --name-only --format= ef336f3 -- tests/ | grep -c .    # 0
```

### CORRECTION 4 — this summary first measured the roster against the wrong base, and its own control caught it

The first draft of this section ran `git diff PHASE_BASE..HEAD -- tests/` and
claimed the result was `0`. **It is `8`** — `PHASE_BASE..HEAD` spans the *whole
phase*, and waves 2 and 3 added the eight functions `D-IMPL-196` was written
about. A per-wave roster measured against the phase base is not a per-wave
roster; it silently attributes every earlier wave's additions to whichever wave
runs the command.

It was caught because the claim was checked with a non-vacuity control rather
than accepted — the same command shape run over wave 3's commits, which **must**
be non-zero:

```bash
for c in 0e87330 36f5011 c03cd70 34df27a 3055ed8 287ce14; do
  echo "$c $(git show $c -- tests/ | grep -c '^+def test_')"
done
# 0e87330 0 · 36f5011 2 · c03cd70 4 · 34df27a 0 · 3055ed8 2 · 287ce14 0    -> 8
```

Recorded rather than quietly fixed, because it is the exact defect class this
project keeps finding in its own verification code, and because `23-12` will
reconcile the roster phase-wide and needs to know which base means what:

```bash
# phase-wide, for 23-12 — waves 2 and 3 own all eight; wave 4 owns none
git diff b87fe58..HEAD -- tests/ | grep -c '^+def test_'   # 8
git diff b87fe58..HEAD -- tests/ | grep -c '^-def test_'   # 0
```

The 12 `test_ext00_fixture_schemas` node ids in the lost set are **not** removed
tests — the functions are all still present and collected; their parametrization
went empty. They return at `23-06`/`23-07`. `23-12` must reconcile them as
re-pointed, not as lost.

---

## Commits

| Commit | What |
|---|---|
| `ef336f3` | `refactor(23-04)`: the 265-file pure rename set. Nothing else. |
| `fc9b906` | `chore(23-04)`: `.gitignore` re-point for the archived `.store/` (Rule 3) |
| `689b58a` | `docs(23-04)`: summary, deferred item 4, regenerated coupling report |

---

## Self-Check: PASSED

Files claimed, all found: `archive/examples/00-quickstart/run.py`,
`archive/examples/external/00-hello-context/serve.py`,
`examples/external/README.md`, `examples/.gitkeep`, this summary,
`deferred-items.md`. Commit `ef336f3` found in `git log --oneline --all`.

The plan's own `<automated>` verify clauses, re-run:

```
PASS  git ls-files archive/ == 265
PASS  git show -M --diff-filter=D HEAD == 0 deletions
PASS  git ls-files examples/s1-* > 0
PASS  four trees under the stated reading
PASS  no 00–08 or external/00-hello-context path tracked under examples/
```
