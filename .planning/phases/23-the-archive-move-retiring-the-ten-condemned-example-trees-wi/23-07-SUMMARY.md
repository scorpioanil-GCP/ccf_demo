---
phase: 23-the-archive-move-retiring-the-ten-condemned-example-trees-wi
plan: 07
subsystem: the paired tests and the perf suites, re-pointed at the archive
tags: [DOCS-17, criterion-7, criterion-8, criterion-12, D-02, D-IMPL-190, D-IMPL-193, D-IMPL-196, red-before-green]
status: complete
requires:
  - phase: 23-04
    provides: the ten trees at `archive/examples/`, 265 files, commit `ef336f3`
  - phase: 23-05
    provides: four relocated children that resolve the repo root, so the archive is runnable
  - phase: 23-06
    provides: the four permitted `src/`/`runtime/` citation edits
provides:
  - "zero node ids LOST against PHASE_BASE — 63 lost ids all recovered at their archive re-path"
  - "collection 4223 -> 4231, the 8 additions all wave 3's and all named"
  - "the four count floors at 9/12/14/12 with every floor constant byte-identical to PHASE_BASE"
  - "the five CLNT-30 / H-14 tests GREEN by re-pointing; none removed, skipped or xfailed"
  - "criterion 8's three-legged control, including the S-9 demonstration that the total is blind"
  - "a BLOCKING finding introduced by plan 23-06 and unreported there"
  - "criterion 12's naming figures MEASURED — 19 of 31, not the carried 25 of 31"
affects:
  - "23-09 (the CLNT-30 README prose obligation, handed on explicitly)"
  - "23-11 (the DOCS-17 cell's naming figures — measured here, and they differ from the criterion's)"
  - "23-12 (criterion 7's accounted delta; criterion 8's discharge; the 23-06 fence finding needs a ruling first)"
tech-stack:
  added: []
  patterns:
    - "prove a re-point by the node-id LOST SET, not by the collected total"
    - "a bounded prefix substitution with three bound checks, because a naive `examples/` walk corrupts `tests/examples`"
    - "for an executing test, assert on a run ARTEFACT and on the SKIP COUNT — a pass total can see neither"
    - "widen a census's SUBJECT rather than lower its COUNT"
key-files:
  created:
    - .planning/phases/23-the-archive-move-retiring-the-ten-condemned-example-trees-wi/23-07-SUMMARY.md
  modified:
    - perf/suites/common.py
    - perf/suites/crossproc/conftest.py
    - perf/synth/artifacts/controlplane.yaml
    - tests/cli/test_schema_export.py
    - tests/conformance/test_a3_discharge.py
    - tests/conformance/test_harness_portability.py
    - tests/deployment/test_operator_builder.py
    - tests/integration/test_proto_quickstart.py
    - tests/products/test_gate_two_call_shape.py
    - tests/products/test_required_operators_guard.py
    - tests/examples/test_agent_basics_output.py
    - tests/examples/test_artifact_schema_headers.py
    - tests/examples/test_artifact_store_output.py
    - tests/examples/test_client_example_purity.py
    - tests/examples/test_cross_process_output.py
    - tests/examples/test_decision_replay_output.py
    - tests/examples/test_demo_generator.py
    - tests/examples/test_e2e_demo_output.py
    - tests/examples/test_ext00_fixture_schemas.py
    - tests/examples/test_ext00_hardening.py
    - tests/examples/test_ext00_serve_output.py
    - tests/examples/test_gate_two_divergence.py
    - tests/examples/test_harness_portability_output.py
    - tests/examples/test_hw1_harness_clients_no_model.py
    - tests/examples/test_hw1_harness_clients_retirement.py
    - tests/examples/test_quickstart_output.py
    - tests/examples/test_skilling_output.py
    - tests/examples/test_spine_separation.py
    - tests/examples/test_workflow_hitl_output.py
    - .planning/phases/23-the-archive-move-retiring-the-ten-condemned-example-trees-wi/deferred-items.md
    - docs/surface/examples/RETIREMENT-COUPLINGS.md  # generated; regenerated LAST, in the venv
decisions:
  - "The plan's `git grep 'examples/<tree>'` inventory is INCOMPLETE by construction — it cannot see `_REPO_ROOT / \"examples\" / \"04-cross-process\"`. Two of the LIVE files (`tests/cli/test_schema_export.py`, `tests/examples/test_gate_two_divergence.py`) are findable only by the quoted-segment grep."
  - "The CLNT-30 module gets a SECOND root (`ARCHIVE_EXAMPLES_ROOT`) rather than a re-pointed one. `H-13`'s census is about the LIVE tree; collapsing the two would let a claim about one be satisfied by the other."
  - "The 'two of these names' census WIDENED ITS SUBJECT to both roots and kept its count at two. Scoped to `examples/` alone it could only have gone green by lowering the count to one — the deletion-shaped outcome the test exists to refuse, reached by arithmetic instead of by `rm`."
  - "The documentary set was re-pointed, per the plan. `tests/invariants/test_citation_coverage.py:45` and `tests/lints/test_examples_scope.py:41,55` were checked and LEFT, each for a stated reason."
  - "Plan 23-06's fence failure is REPORTED, not fixed: the test's own docstring forbids narrowing it, and `D-IMPL-192` authorised the edit that trips it. The reconciliation is a ruling."
requirements-completed: []
metrics:
  duration: ~2h30m
  completed: 2026-08-24
  tasks: 3
  commits: 3
---

# Phase 23 Plan 07: The paired tests reach the archive — Summary

**61 path references in 29 files re-pointed; ZERO node ids lost against
`PHASE_BASE`; the five `CLNT-30`/`H-14` tests green by re-pointing and nothing
else.** Collection went `4223 → 4231`, and every one of the eight additions is
wave 3's, named in `23-03`'s roster, not this wave's.

**One blocking finding, and it is not this wave's:** plan `23-06`'s permitted
`src/ccf/products/bind.py` edit trips an unbounded Phase-20 fence
(`tests/examples/test_hw1_harness_clients_readme.py::test_criterion_seven_no_sdk_mechanism_ships_at_all`).
Bisected to `2256526` exactly. `23-06-SUMMARY.md` does not mention it. **Not
fixed here** — see "The finding this wave did not fix".

---

## Tests added by this wave — criterion 7's roster

**NONE.** `23-07` adds zero test functions and removes zero.

```bash
for c in 7fa18e8 fb85640; do echo "$c +$(git show $c -- tests/ | grep -c '^+def test_') -$(git show $c -- tests/ | grep -c '^-def test_')"; done
# 7fa18e8 +0 -0
# fb85640 +0 -0
```

Non-vacuity control on that zero — the same command shape over wave 3's
commits, which **must** be non-zero:

```bash
for c in 36f5011 c03cd70 3055ed8; do echo "$c $(git show $c -- tests/ | grep -c '^+def test_')"; done
# 36f5011 2 · c03cd70 4 · 3055ed8 2   -> 8
```

---

## Criterion 7 — the accounted delta, by node id

**The target is NOT 4223.** `D-IMPL-196` replaced the absolute pin with an
accounted delta: *zero node ids lost against `PHASE_BASE`, every addition
named, the total re-measured at the close*. `PHASE_BASE` collected 4223 and
wave 3 added eight guards, so a correct tree after this wave collects **4231**.

### How the `PHASE_BASE` set was measured

```bash
git archive b87fe58 | tar -x -C $S/base-tree        # 1981 files == git ls-tree -r b87fe58 | wc -l
env -C $S/base-tree PYTHONPATH=$S/base-tree/src:$S/base-tree/runtime CCF_REQUIRE_HARNESSES=1 \
  .venv/bin/python -m pytest --collect-only -q      # 4223 tests collected
```

**CORRECTION 1 — the first run of this measurement was taken with the wrong
cwd and produced a wrong answer that looked right.** Run from the repo root
with `--rootdir` pointed at the extracted tree, `tests/examples/test_artifact_schema_headers.py`
errored at collection with

```
ValueError: '/home/parkave/ccf_code/archive/examples/00-quickstart/artifacts'
            is not in the subpath of '.../base-tree'
```

— the extracted module was resolving `tools/` from the **real** repo via cwd,
so the "PHASE_BASE" collection was reading the post-move tree through a
half-open window. `env -C` fixed it. A measurement of a historical tree that
silently reads the current one is the same defect class as a green-and-false
citation, and it is recorded rather than smoothed.

**CORRECTION 2 — node ids embed absolute paths, so the raw sets differ for a
reason that is not a delta.** Six `tests/crossproc/test_mcp_acquisition.py`
ids are parametrized on `.../tests/crossproc/servers/mcp_content_child.py` as
an absolute path; extracted at a different root they read as 6 lost and 6
gained. Normalised with a root substitution before any arithmetic.

**CORRECTION 3 — my own accounting script committed the exact naive-`examples/`
walk this plan's bound check exists to catch.** The first classifier used
`re.sub(r'(?<!archive/)\bexamples/', 'archive/examples/', node_id)`, which
rewrote the `tests/examples/` **module path** inside every node id and reported
24 lost ids as unrecovered when only 12 were. Fixed with a second lookbehind
`(?<!tests/)`. The plan warned about this shape for the *source* edit; it
turned up in the *measuring* code instead, which is where this project's
defects keep landing.

### The delta, before and after

| | LOST | of which recovered at an `archive/` re-path | GAINED | GAINED not a re-path |
|---|---:|---:|---:|---:|
| at `HEAD` before this wave (4223) | 75 | 63 | 75 | 12 |
| at `HEAD` after this wave (**4231**) | 63 | **63** | 71 | **8** |

**LOST-UNRECOVERED after this wave: ZERO.** The twelve that were outstanding
are back, by node id:

```
tests/examples/test_ext00_fixture_schemas.py::test_anthropic_request_fixture_shape[anthropic-00-request.json]
tests/examples/test_ext00_fixture_schemas.py::test_anthropic_request_fixture_shape[anthropic-01-request.json]
tests/examples/test_ext00_fixture_schemas.py::test_anthropic_response_fixture_validates[anthropic-00.json]
tests/examples/test_ext00_fixture_schemas.py::test_anthropic_response_fixture_validates[anthropic-01.json]
tests/examples/test_ext00_fixture_schemas.py::test_gemini_request_fixture_shape[gemini-00-request.json]
tests/examples/test_ext00_fixture_schemas.py::test_gemini_request_fixture_shape[gemini-01-request.json]
tests/examples/test_ext00_fixture_schemas.py::test_gemini_request_fixture_shape[gemini-02-request.json]
tests/examples/test_ext00_fixture_schemas.py::test_gemini_request_fixture_shape[gemini-03-request.json]
tests/examples/test_ext00_fixture_schemas.py::test_gemini_response_fixture_validates[gemini-00.json]
tests/examples/test_ext00_fixture_schemas.py::test_gemini_response_fixture_validates[gemini-01.json]
tests/examples/test_ext00_fixture_schemas.py::test_gemini_response_fixture_validates[gemini-02.json]
tests/examples/test_ext00_fixture_schemas.py::test_gemini_response_fixture_validates[gemini-03.json]
```

and the four degenerate `[NOTSET]` ids that stood in for them are gone:

```
tests/examples/test_ext00_fixture_schemas.py::test_anthropic_request_fixture_shape[NOTSET]
tests/examples/test_ext00_fixture_schemas.py::test_anthropic_response_fixture_validates[NOTSET]
tests/examples/test_ext00_fixture_schemas.py::test_gemini_request_fixture_shape[NOTSET]
tests/examples/test_ext00_fixture_schemas.py::test_gemini_response_fixture_validates[NOTSET]
```

`4223 + 12 − 4 = 4231`, which is the number measured.

```bash
PYTHONPATH=src:runtime CCF_REQUIRE_HARNESSES=1 .venv/bin/python -m pytest --collect-only -q | tail -1
# 4231 tests collected in 6.29s
PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/examples/test_ext00_fixture_schemas.py -q
# 15 passed in 1.12s     <- 12 recovered parametrizations + 3 module-level tests, ZERO skipped
```

### The GAINED set, all eight, none of them this wave's

```
tests/examples/test_artifact_schema_headers.py::test_the_discovery_finds_an_archived_artifact_directory
tests/examples/test_artifact_schema_headers.py::test_the_discovery_globs_reach_the_live_tree_and_the_archive
tests/examples/test_artifact_schema_headers.py::test_the_discovery_ignores_an_artifact_directory_outside_both_roots
tests/examples/test_artifact_schema_headers.py::test_the_gated_roots_are_the_live_tree_and_the_archive
tests/lints/test_examples_scope.py::test_cinv01_scope_includes_the_archive_tree
tests/lints/test_examples_scope.py::test_cinv02_does_not_flag_harness_imports_under_the_archive
tests/products/test_gate_two_call_shape.py::test_the_scan_root_membership_is_exactly_the_expected_sets
tests/products/test_required_operators_guard.py::test_the_scan_root_membership_is_exactly_the_expected_set
```

All eight are plan `23-03`'s, and `D-IMPL-196` was minted about them.

---

## Task 1 — the inventory, built by grep, and the 61 re-points

### The inventory BEFORE editing, per file

Built by `git grep`, never from `docs/surface/examples/RETIREMENT-COUPLINGS.md`
(`D-IMPL-194`: the eleven `test_*_output.py` modules source **zero** rows).

```bash
git grep -lnE 'examples/(00-quickstart|01-agent-basics|02-skilling|03-harness-portability|04-cross-process|05-workflow-hitl|06-decision-replay|07-artifact-store-mcp|08-e2e-demo|external/00-hello-context)' -- tests/ perf/
# 29 files
```

Counting only occurrences NOT already under `archive/` (`23-03`/`23-05` had
already re-pointed 3 in `test_artifact_schema_headers.py` and 3 in
`test_examples_scope.py`): **57 literal occurrences across 29 files.**

| n | file | n | file |
|--:|---|--:|---|
| 1 | `perf/suites/common.py` | 1 | `tests/examples/test_decision_replay_output.py` |
| 1 | `perf/suites/crossproc/conftest.py` | 1 | `tests/examples/test_demo_generator.py` |
| 1 | `perf/synth/artifacts/controlplane.yaml` | 1 | `tests/examples/test_e2e_demo_output.py` |
| 1 | `tests/conformance/test_a3_discharge.py` | 1 | `tests/examples/test_ext00_fixture_schemas.py` |
| 2 | `tests/conformance/test_harness_portability.py` | 1 | `tests/examples/test_ext00_hardening.py` |
| 1 | `tests/deployment/test_operator_builder.py` | 1 | `tests/examples/test_ext00_serve_output.py` |
| 1 | `tests/examples/test_agent_basics_output.py` | 1 | `tests/examples/test_harness_portability_output.py` |
| 6 | `tests/examples/test_artifact_schema_headers.py` | 1 | `tests/examples/test_hw1_harness_clients_no_model.py` |
| 1 | `tests/examples/test_artifact_store_output.py` | 9 | `tests/examples/test_hw1_harness_clients_retirement.py` |
| 1 | `tests/examples/test_client_example_purity.py` | 1 | `tests/examples/test_quickstart_output.py` |
| 2 | `tests/examples/test_cross_process_output.py` | 1 | `tests/examples/test_skilling_output.py` |
| 1 | `tests/integration/test_proto_quickstart.py` | 1 | `tests/examples/test_spine_separation.py` |
| 1 | `tests/invariants/test_citation_coverage.py` | 3 | `tests/examples/test_workflow_hitl_output.py` |
| 2 | `tests/lints/test_examples_scope.py` | 11 | `tests/products/test_gate_two_call_shape.py` |
| 1 | `tests/products/test_required_operators_guard.py` | | **TOTAL 57** |

### CORRECTION 4 — the plan's grep CANNOT SEE the LIVE path constructions, and that is most of what this wave had to fix

Every one of those 57 is a **prose** occurrence. The LIVE constructions are
segment-quoted and the plan's regex does not match them:

```python
_EXAMPLE_04 = _REPO_ROOT / "examples" / "04-cross-process"       # perf/suites/crossproc/conftest.py:52
EXAMPLE_DIR = REPO_ROOT / "examples" / "external" / "00-hello-context"
```

A second grep — `git grep -n '"examples"' -- tests/ perf/` — found **16** of
these. Two of the files carrying them appear in **neither** the plan's literal
grep nor the plan's LIVE table:

* `tests/cli/test_schema_export.py:60` (the plan names the file but not how to
  find it — its only reference is segment-quoted)
* **`tests/examples/test_gate_two_divergence.py:96`** — not named anywhere in
  the plan. It errored twice in wave 4's chunk A.

Had the inventory been built from the plan's command alone, `test_gate_two_divergence.py`
would have been missed and the phase would have carried two silent errors
forward. **The plan's grep is a prose inventory, not a coupling inventory.**

### The substitution and its bound

61 substitutions across 28 files (the 29th, the `CLNT-30` module, is task 2):
**45 literal** `examples/<tree>` → `archive/examples/<tree>` and **16
quoted-segment** `"examples" / "<tree>"` → `"archive" / "examples" / "<tree>"`.
Both patterns carry a `(?<!archive/)` lookbehind so a second run is a no-op,
and the literal one carries `(?<!tests/)` so the string `tests/examples` cannot
be walked.

### The three bound checks — all held, each with a non-vacuity floor

```bash
# 1. no `s1` path touched  (D-01, criterion 13's second clause)
diff <(git grep -h 's1-0' -- tests/ perf/ | sort) <(git grep -h 's1-0' HEAD -- tests/ perf/ | sort)
#   IDENTICAL      floor: 13 files carry an s1 token, so the emptiness is a result
# and against PHASE_BASE, per-file counts are identical too:
#   tests/products/test_gate_two_call_shape.py:11  … 13 files, byte-for-byte

# 2. no `hw1` line touched — the surviving client examples are not condemned
diff <(git grep -h 'hw1-' -- tests/ perf/ | sort) <(git grep -h 'hw1-' HEAD -- tests/ perf/ | sort)
#   IDENTICAL      floor: 91 lines

# 3. `tests/examples` uncorrupted
git grep -n 'archive/tests\|tests/archive' -- tests/ perf/     # (EMPTY)
diff <(git grep -c 'tests/examples' -- tests/ perf/ | sort) <(git grep -c 'tests/examples' HEAD -- tests/ perf/ | sed 's#^HEAD:##' | sort)
#   IDENTICAL      floor: 20 files carry the token
```

The `hw1` and `s1` diffs against `PHASE_BASE` show **line-number** drift only
(waves 2/3/5 inserted lines above them); the diffs against the pre-edit `HEAD`
are byte-identical, which is what this wave is answerable for.

### The DOCUMENTARY set — re-pointed, as a decision

Thirteen prose sentences in live code (`test_a3_discharge` 1,
`test_harness_portability` 2, `test_proto_quickstart` 1, `test_operator_builder` 1,
`test_gate_two_call_shape` 11 — the research's 5 plus 6 `#:` constant comments
the research did not enumerate — `test_required_operators_guard` 1,
`perf/suites/common.py` 1, `perf/synth/artifacts/controlplane.yaml` 1) were
re-pointed even though none went red and no gate resolves them.

**The rule applied, stated so it can be argued with:** re-point a path in
**live code**; leave one in a **dated record**. Every occurrence here is in
live code. The one uncomfortable consequence is recorded rather than hidden —
`tests/examples/test_artifact_schema_headers.py:3` now reads *"Plan 15-12 added
`$schema` headers to `archive/examples/00-quickstart/artifacts/` only"*, which
is anachronistic, because 15-12 wrote them where the tree then was. The
alternative is a path that resolves nowhere, and `D-27`'s complaint is about
exactly that half-repaired state.

### Checked and LEFT, each with its reason

| File | Occurrences | Why left |
|---|---:|---|
| `tools/publish_scan_tests/test_publish_scan.py` | 2 | `tmp_path` synthetic tokens; outlive their subject by construction (research §7.6). Green throughout. |
| `tests/lints/test_examples_scope.py:41,55` | 2 | Same shape — `_write(tmp_path, "examples/00-quickstart/run.py", …)` builds a **synthetic** tree. Wave 3 already added the archive twins beside them. |
| `tests/invariants/test_citation_coverage.py:45` | 1 | *"the first breaks at wave 8 when `examples/03-harness-portability` retires"* narrates `RETIREMENT_SCHEDULE`, which still spells the path `examples/…` until plan `23-10` re-points it. Re-pointing here would desynchronise the sentence from the data it describes. Not in this plan's `files_modified`. |

### The four count floors — 9 / 12 / 14 / 12, no constant edited

Every constant compared byte-for-byte against `PHASE_BASE`:

```bash
for c in MINIMUM_IMPLEMENTATIONS MINIMUM_GATE_CALL_SITES MINIMUM_PROJECTING_BODIES \
         MINIMUM_RESOLVED_BINDER_SITES MINIMUM_SCANNED_CITATION_HOSTS MINIMUM_CITATIONS_READ; do
  diff <(git grep -h "^$c" -- tests/ tools/ src/ runtime/) \
       <(git grep -h "^$c" b87fe58 -- tests/ tools/ src/ runtime/)
done      # all six IDENTICAL
```

Values re-measured by partitioning each module's own scan output by path:

| Gate | floor | value | partition |
|---|---:|---:|---|
| `MINIMUM_IMPLEMENTATIONS` | **9** | 14 | `src/runtime 2 · examples 3 · archive 9` |
| `MINIMUM_GATE_CALL_SITES` | **12** | 12 | `src/runtime 1 · examples 2 · archive 9` |
| `MINIMUM_PROJECTING_BODIES` | **14** | 14 | `examples 3 · archive 11` |
| `MINIMUM_RESOLVED_BINDER_SITES` | **12** | 12 | `examples 1 · archive 11` |

`SCANNED_TREES = ('src','runtime','examples','archive')` and
`BINDER_SCANNED_TREES = ('examples','archive')` — both still carry the LIVE
tree, which is the `S-16` swap the research warned a floor cannot see, and
which wave 3's two membership tests now assert directly.

### Task 1's automated verify

```bash
PYTHONPATH=src:runtime CCF_REQUIRE_HARNESSES=1 .venv/bin/python -m pytest \
  tests/products/test_gate_two_call_shape.py tests/products/test_required_operators_guard.py \
  tests/cli/test_schema_export.py -q -rs
# 156 passed, 4 warnings in 7.43s        (0 skipped, 0 xfailed)
```

And the perf leg that wave 4 left red:

```bash
PYTHONPATH=src:runtime CCF_REQUIRE_HARNESSES=1 .venv/bin/python -m pytest tests/perf_smoke -q
# 4 passed in 207.88s      <- includes test_suite_runs_untimed[crossproc], RED after the move
```

---

## Task 2 — the five `CLNT-30` / `H-14` tests, GREEN by re-pointing

### Before

```bash
PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/examples/test_hw1_harness_clients_retirement.py -q
# 5 failed, 11 passed in 0.22s
```

| # | Node id | before | after |
|---|---|---|---|
| 1 | `::test_the_historical_example_keeps_all_three_of_its_clients` | FAILED | **PASSED** |
| 2 | `::test_nothing_is_untracked_under_the_historical_example` | FAILED | **PASSED** |
| 3 | `::test_no_tracked_file_under_the_historical_example_is_dirty` | FAILED | **PASSED** |
| 4 | `::test_two_of_these_names_under_examples_is_the_mandated_state[client_adk.py]` | FAILED | **PASSED** |
| 5 | `::test_two_of_these_names_under_examples_is_the_mandated_state[client_anthropic.py]` | FAILED | **PASSED** |

```bash
PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/examples/test_hw1_harness_clients_retirement.py -q -rs
# 16 passed in 0.23s      (0 skipped, 0 xfailed)
```

### Nothing removed, skipped or weakened — proven three ways

```bash
# 1. the node-id set is IDENTICAL to PHASE_BASE, not merely the same size
diff <(grep 'test_hw1_harness_clients_retirement.py::' $S/ids-base-norm.txt | sort) \
     <(pytest … --collect-only -q | grep '::' | sort)          # IDENTICAL (16)
# 2. the function count is unchanged
git show b87fe58:tests/examples/test_hw1_harness_clients_retirement.py | grep -c '^def test_'   # 15
grep -c '^def test_' tests/examples/test_hw1_harness_clients_retirement.py                       # 15
# 3. no skip/xfail marker exists — the only `skip`/`xfail` strings in the file are in the
#    docstring sentence that says none was added
```

### What changed, and the one design call

* **`ARCHIVE_EXAMPLES_ROOT` is a SECOND root, not a re-pointed one.**
  `EXAMPLES_ROOT` stays `examples/` because `H-13`'s claims — the condemned
  `s2-01-external-consumers` directory being gone, and the LangGraph census —
  are about what a listing of the **live** tree shows. Collapsing the two roots
  would let a claim about one be satisfied by the other. Verified the census is
  unaffected: `client_langgraph.py` exists once, under
  `examples/hw1-harness-clients/`, and **zero** times under `archive/`.
* `historical_example_violations` is now called with `ARCHIVE_EXAMPLES_ROOT`;
  `GUARDED_EXAMPLE` is `archive/examples/external/00-hello-context`.
* **`test_two_of_these_names_under_examples_is_the_mandated_state` widened its
  SUBJECT and kept its COUNT.** The census now walks both roots and still
  expects **two**. Measured:

  ```
  archive/examples/external/00-hello-context/client_adk.py        examples/hw1-harness-clients/client_adk.py
  archive/examples/external/00-hello-context/client_anthropic.py  examples/hw1-harness-clients/client_anthropic.py
  archive/examples/external/00-hello-context/client_bare.py
  ```

  Left scoped to `examples/` it would have found one of each and could have
  been made green **only by lowering the expected count to one** — the
  deletion-shaped outcome the test exists to refuse, arrived at by arithmetic
  instead of by `rm`. That is the weakening `D-IMPL-193` calls a scope breach,
  and it was available and refused.
* The module docstring now records `D-IMPL-193` in its own words: that
  *"CI-green" means ITS TESTS KEEP PASSING*, that the tree moved intact and
  runnable at `23-04`, that the ruling *"does not authorize dropping or
  weakening the tests that still execute it"*, and — explicitly — that the
  **README prose half of the marking obligation is `CLNT-30`'s and lands in
  plan `23-09`**, so the module does not read as claiming to discharge it.

### `CLNT-30`'s README prose obligation is NOT discharged here

*"Marked historical in prose under an existing README heading, stating that its
clients target the pre-Phase-17 surface over HTTP with bearer auth and that
Phase 20's trio is canonical going forward"* stands, untouched, and lands in
**plan `23-09`** with the other README work. Said here so the obligation is
visibly handed on rather than silently split. `deferred-items.md` item 2 also
carries the orphaned `examples/external/README.md` index row for the same plan.

### Sabotage ledger for task 2 — applied AFTER the fix was committed (`fb85640`)

| # | Mutation | Prediction | Observed | Held? |
|---|---|---|---|---|
| **S-H14a** | move `client_bare.py` out of the archived tree | `test_the_historical_example_keeps_all_three_of_its_clients` fails naming it | `2 failed, 14 passed`; the clients test fails and names `client_bare.py` **twice** — *and the dirty-tracked arm fires too*, an extra witness the prediction did not name | **YES, plus one** |
| **S-H14b** | `ARCHIVE_EXAMPLES_ROOT` re-pointed at `archive/no-such-examples` | *the plan predicts all five fail.* **I predicted THREE** — the clients test and both parametrizations — because `GUARDED_EXAMPLE` is anchored on its own literal, not on the constant | `3 failed, 13 passed`, exactly those three | **MY PREDICTION HELD; THE PLAN'S DID NOT** |
| **S-H14b2** | both anchors re-pointed at a path that does not exist | all five fail, with the module's own message quoting the ruling | `5 failed, 11 passed` — **the identical five that were red before the fix** — and the message reads *"`H-14` rules that this example STAYS, running and CI-green, marked historical in its README…"* verbatim | **YES** |
| **S-H14c** | the whole archived tree moved aside — the scope-breach direction | the five fail; the module RESISTS being satisfied by deletion | `5 failed, 11 passed` | **YES** |

**S-H14b is a correction to the plan, and the useful kind.** The module has
**two independent path anchors**, and mutating one leaves the other's two tests
green. A control written to the plan's prediction ("all five fail") would have
been recorded as failing when it was in fact reporting a true fact about the
module's shape. The two-anchor split is deliberate — one arm asks the
filesystem, the other asks `git` — and S-H14b2 shows both re-points landed.

Restores were byte-identical, checked positively rather than by `git diff
--quiet` alone:

```bash
git status --porcelain -- archive/     # EMPTY after each
git ls-files archive/examples/external/00-hello-context | wc -l     # 39, before and after S-H14c
grep -n '^ARCHIVE_EXAMPLES_ROOT = REPO_ROOT / "archive" / "examples"$' …   # line 92
grep -n '^GUARDED_EXAMPLE = pathlib.PurePosixPath("archive/examples") / …' # line 397
grep -c "def build_covenant_slice_product" archive/…/producer_child.py     # 1
```

---

## Task 3 — criterion 8: the two EXECUTING tests really execute

### Leg 1 — the skip count

```bash
PYTHONPATH=src:runtime CCF_REQUIRE_HARNESSES=1 .venv/bin/python -m pytest \
  tests/examples/test_cross_process_output.py tests/examples/test_ext00_hardening.py -q -rs
# 46 passed, 1 warning in 6.89s      EXIT=0
# `-rs` skip-reason lines: 0        xfailed: 0        errors: 0
```

**46 = 19 + 27**, which are wave 4's exact error and failure counts for the two
modules on the un-re-pointed tree.

### Leg 2 — the run artefact, with observed values

Not "the test passed". The archived source was **executed** and what it
produced was read.

**`test_cross_process_output.py` — the module's own `_load` and `run()`:**

```
T1.EXAMPLE_DIR                  = /home/parkave/ccf_code/archive/examples/04-cross-process
loaded producer_child.__file__  = /home/parkave/ccf_code/archive/examples/04-cross-process/producer_child.py
loaded run.py       __file__    = /home/parkave/ccf_code/archive/examples/04-cross-process/run.py

# the assembly leg, in-process:
producer.sqlite3 written        = True, 69632 bytes

# the two-process leg, run exactly as the `consumer` fixture runs it:
tenant_id                       = harborline-syndications
admission_record_address        = f69c55f65ca9679a9d5f899fc9b62f0a13e5f2ef3717ab56ee8eea2279d34610
digest_before_ingest            = 4991cac897692aeb17c3ab419759bb8ab990bb02414129e59bfbee1b5670…
digest_after_ingest             = 5892088845c435e011e238ea45b242a0b145a5624761aee4aadd4170fdfd…
consumer_policy_version         = 4bb2d7ee9a02d60cd8cf28b3843adb3f81d01fbe81292d93fb567ea38acd0783
files written under the run root:
  admission-records/.artifact-names.json
  admission-records/f69c55f65ca9679a9d5f899fc9b62f0a13e5f2ef3717ab56ee8eea2279d34610
  consumer.sqlite3
  keys/harborline-lead-arranger-key-1.jwk
  producer-child.stderr            <- 891 bytes, written by a REAL CHILD PROCESS
producer-child.stderr head       = "INFO StreamableHTTP streamable_http_manager.py:131 session manager started"
```

`admission_record_address` is content-addressed and reproduced **identically
across two independent probe runs** — a deterministic artefact of the archived
producer, not an exit code.

**`test_ext00_hardening.py` — the module's own `subprocess.run(["run.py",
"--legs", ""], cwd=EXAMPLE_DIR)`:**

```
cwd        = /home/parkave/ccf_code/archive/examples/external/00-hello-context
returncode = 0        stdout = 557 bytes
  PASS 1: client legs exit 0 ()
  PASS 2: revoked token refused with 401 (D-12)
  PASS 3: zero CCF imports in client_*.py (D-06)
  PASS 4: README headings match the seven Phase-13 template names in order (D-17/D-08)
  PASS 5: lineage + replay record retrieved over MCP (D-15)
  PASS 6: resource path and get_context serve identical bytes (D-07)
  PASS 7: advertised tools equal the artifact allowlist (D-05)
  PASS 8: fabric-side byte-equal reproduction (D-16)
```

Eight PASS lines printed by a program running out of `archive/`. And the
`.store/` it writes stays ignored — `git status --porcelain` after every run in
this wave is clean apart from three `references/*.md` files that were untracked
before the wave began. Wave 4's `.gitignore` repair holds.

### Leg 3 — sabotage

| # | Mutation | Prediction | Observed | Held? |
|---|---|---|---|---|
| **S-6** | `archive/examples/04-cross-process/producer_child.py` moved aside | research says *"19 ERRORS at collection"*. **I predicted 19 FIXTURE errors, not collection errors**, because `_load` runs inside the fixtures | `19 errors in 2.94s`, traceback through `archive/examples/04-cross-process/run.py:343` — the archived source executing and failing | **YES, with my refinement** |
| **S-7** | `archive/examples/external/00-hello-context/serve.py` moved aside | research says `test_ext00_hardening.py` **27 FAILED** + `test_ext00_serve_output.py` **15 ERRORS** | `test_ext00_hardening.py` **7 failed, 20 passed**; `test_ext00_serve_output.py` **15 errors** | **HALF — see below** |
| **S-9** | a wholesale env-guard skip on `test_ext00_hardening.py` | (a) the collected node-id set is byte-identical; (b) the total stays 4231; (c) the summary reports 27 skipped | (a) `diff` of the two id files: **IDENTICAL**; (b) **4231**; (c) `19 passed, 27 skipped` | **YES** |

**S-7's correction.** The research's *27 FAILED* was measured on the **bare
move**, where the whole `EXAMPLE_DIR` was unreachable. Removing only `serve.py`
reds **7** of the 27; the other 20 read `run.py`, `replay_server.py` and
`artifacts/experience.yaml`, which are still there. The research conflated
"delete `serve.py`" with "the tree is gone". Seven is still decisive, and the
15 errors in `test_ext00_serve_output.py` held exactly. Restored: `42 passed`.

### S-9's observation IS the deliverable

The three things the sabotage established, in order of how badly they are
needed:

1. **Criterion 7's entire subject is blind to it.** Under `D-IMPL-196` the gate
   is the collected **node-id set**. With the skip guard installed that set is
   `diff`-identical and the total is the same 4231. A wholesale skip of an
   executing test is **structurally invisible** to the check that is supposed to
   prove the phase changed no behaviour.
2. **The pass total is blind too.** `46 passed` becomes `19 passed, 27 skipped`;
   nothing in this repository gates on an exact passed count since `D-IMPL-196`
   replaced the `4105 passed / 118 skipped` pin.
3. **Only the skip-count leg saw it**, which is why criterion 8 asks for it.

**A refinement worth carrying:** `grep -c '^SKIPPED'` on `-rs` output returned
**26** while the summary reported **27 skipped**, because pytest collapses
identical reasons into `SKIPPED [2] …`. Asserting on the count of `-rs` lines
would under-report. **Zero lines still means zero skips**, so leg 1's assertion
as written is sound — but a future control that asserts a *non-zero* skip
budget must read the summary line, not count `-rs` entries.

### The class this wave CANNOT guard — inherited from wave 5, not re-derived

`ccf` and `ccf_runtime` are **editable-installed**, so a meta-path finder
resolves them regardless of `sys.path`; a broken `parents[N]` in an archived
child does **not** fail here. Worse for this plan specifically:
`test_cross_process_output.py`'s `assembled` fixture imports `producer_child`
**in-process**, after `ccf` is already in `sys.modules`. **Re-pointing its path
does not make it a witness for the depth**, and no standing gate in this
repository can witness that defect class. The only proof on record is wave 5's
scrubbed-`sys.meta_path` probe. **Stated as an ungated surface, not implied to
be covered.**

The citation lint is likewise **green and false** on stale paths (wave 4's
`resolve_cited` suffix-fallback finding). `python -m tools.lints --all` exits 0
here; that is not evidence of anything in this wave, and the four newly
introduced `path::symbol` node ids were checked by resolving them on disk
instead:

```
OK archive/examples/external/00-hello-context/run.py
OK archive/examples/03-harness-portability/legs/deterministic.py
OK archive/examples/03-harness-portability/run.py
OK archive/examples/06-decision-replay/run.py
OK archive/examples/external/00-hello-context/serve.py
OK archive/examples/04-cross-process/producer_child.py
OK archive/examples/00-quickstart/artifacts
```

`D-IMPL-123`'s line-anchored ceiling is untouched — the diff introduces **zero**
`*.py:<line>` citations (`git diff -U0 -- tests/ perf/ | grep -E '^\+[^+]' |
grep -cE '\.py:[0-9]+'` → `0`), and that check was run as its own step, its
output read, before either commit.

---

## Criterion 12's naming figures — MEASURED, and two of them differ

Criterion 12 requires the `DOCS-17` cell to state what still exercises the
archive. `23-RESEARCH.md` §14.5 flagged *"25 of 31"* as **unverified**. It is
now verified, and it does not hold.

| Figure | criterion / research says | **measured** | command |
|---|---|---|---|
| files under `tests/examples` | 31 | **31** ✓ | `git ls-files tests/examples \| wc -l` |
| …that NAME the condemned set | **25** | **19** ✗ | `git grep -lE 'archive/examples/(…)\|"archive" / "examples"' -- tests/examples/ \| wc -l` |
| …that EXECUTE it | 2 | **2** ✓ (under the *spawns-a-process* reading — see below) | |
| tests `tests/examples` collects | 515 | **519** ✗ | `pytest tests/examples --collect-only -q` |

**Both deltas are explained, not hand-waved.**

* **19, not 25.** The same predicate run against `PHASE_BASE` with the pre-move
  spelling also returns **19**, so this is not something the move changed — the
  25 was never on the tree. The research measured a *different* thing (14 files
  by literal path, plus 7 from the coupling report, overlapping) and said so.
* **519, not 515.** `PHASE_BASE` collected **515** under `tests/examples`
  (`grep -c '^tests/examples/' ids-base-norm.txt`), and wave 3 added four
  discovery guards to `test_artifact_schema_headers.py`. `515 + 4 = 519`. The
  515 limb of `D-IMPL-196` is a `PHASE_BASE` figure, and the cell must either
  say so or state 519.

**"2 EXECUTE" is true only under a narrow reading, and the cell should say
which.** Measured taxonomy over the 19:

| tier | count | what it means |
|---|---:|---|
| spawns a real OS process running the archived source | **2** | `test_ext00_hardening.py` (`subprocess.run(["run.py","--legs",""], cwd=EXAMPLE_DIR)`) and `test_cross_process_output.py` (its `run()` spawns `producer_child.py` — the `producer-child.stderr` artefact above is the proof) |
| `exec_module`s archived source in-process | **14** | every `test_*_output.py`, `test_gate_two_divergence.py`, `test_ext00_serve_output.py`, `test_demo_generator.py`, `test_hw1_harness_clients_no_model.py` — these RUN module bodies, they do not merely read text |
| reads the archived tree without loading it | **3** | `test_artifact_schema_headers.py`, `test_client_example_purity.py`, `test_spine_separation.py`, `test_hw1_harness_clients_retirement.py` (via `git status`) |

A cell reading *"25 of 31 read it and 2 execute it"* would state one figure that
is wrong and one that is right for a reason it does not give. **Both are plan
`23-11`'s to write and both must be re-measured there** — `RECON-09` is exactly
the failure of stating a figure nobody measured.

---

## The finding this wave did NOT fix

**`tests/examples/test_hw1_harness_clients_readme.py::test_criterion_seven_no_sdk_mechanism_ships_at_all`
is RED, was made red by plan `23-06`, and `23-06-SUMMARY.md` does not mention
it.**

```bash
B=$(head -1 .planning/phases/20-…/20-BASE-COMMIT.txt)   # 9e4bd0e
git diff --stat $B..2256526^ -- src/     # EMPTY
git diff --stat $B..2256526  -- src/     #  src/ccf/products/bind.py | 2 +-
git diff --stat $B..HEAD     -- src/     #  src/ccf/products/bind.py | 2 +-
```

The bisect is exact. The assertion is `git diff --stat <phase-20-base>..HEAD --
src/` = `""`, and `D-IMPL-192` explicitly authorised the one-line edit that
makes it non-empty. `D-11`'s *"the scope fence is SAFE"* in `23-CONTEXT.md`
covers `test_requirement_ledger.py`, which `D-IMPL-188` **bounded** to
`base..951eb4a`; this assertion is a different one and is still unbounded at
`..HEAD`.

**Not fixed here, for three reasons that agree.** The test's own docstring says
*"A non-empty result here is a blocking finding to report, never a reason to
narrow this assertion back to the client surface."* The brief forbids relaxing
an assertion to go green. And two Dave-level documents now contradict each
other, which is a ruling (bound the window as `D-IMPL-188` did, or record the
permitted edit as an allowance), not an executor's edit. Logged as
`deferred-items.md` item 5 and **owed before the phase closes.**

It is the only failure in `tests/examples` + `tests/perf_smoke` after this wave:

```bash
PYTHONPATH=src:runtime CCF_REQUIRE_HARNESSES=1 .venv/bin/python -m pytest tests/examples tests/perf_smoke -q -rs
# 1 failed, 485 passed, 37 skipped in 302.28s
```

All 37 skips are pre-existing `CCF_TEST_{NEO4J,MONGO,FLUREE}_*` container
skips in `test_s1_01_output.py` — none introduced by this wave, and the four
`[NOTSET]` skips wave 4 found are gone.

---

## Deviations from Plan

### `[Rule 3 - Blocking]` The plan's inventory command cannot see the LIVE constructions

Documented as CORRECTION 4 above. A second grep (`git grep -n '"examples"'`)
was added to the inventory and found 16 segment-quoted path constructions, two
of them in files the plan's own LIVE table would not have led me to
(`test_gate_two_divergence.py` in particular). **No scope change** — every file
is inside `files_modified` (`tests/examples/`, `tests/cli/test_schema_export.py`).

### `[Rule 3 - Blocking]` `docs/surface/examples/RETIREMENT-COUPLINGS.md` regenerated

Absent from this plan's `files_modified`, as for waves 1–6. Generated, walks
`.planning/`, and every write here stales it. Regenerated **LAST**, in the venv,
and added to this summary's frontmatter — the standing Rule-3 deviation.

### Nothing else

* `.planning/STATE.md` and `.planning/ROADMAP.md` untouched (`D-10`, `D-15`).
* No Success Criterion authored, renumbered or edited.
* `CLNT-17` receives no verdict, limb or disposition here, and appears in no
  commit message.
* No `src/`, `runtime/` or `pyproject.toml` edit — the diff against
  `PHASE_BASE` is still exactly wave 6's four lines
  (`grep -cE '^\+[^+]'` → **4**).
* No `git clean`, no `git stash`, no `git reset` anywhere. The two
  `git checkout --` restores were taken **after** the corresponding fix was
  committed, and each was confirmed by a positive sanity grep, not by
  `git diff --quiet` alone.

---

## Predictions, including the wrong ones

| Prediction | Source | Outcome |
|---|---|---|
| the collected total returns to `PHASE_BASE`'s 4223 | plan `must_haves` | **FALSIFIED, and correctly so.** `D-IMPL-196` superseded the absolute pin; the right answer is 4231 and the right gate is the empty lost-set. The brief said as much; the plan's `must_haves` line still carries the old form |
| the four floors read 9/12/14/12 | plan task 1 | **HELD**, constants byte-identical |
| `S-H14b` fails all five | plan task 2 | **FALSIFIED** — it fails three; the module has two independent path anchors. My own prediction of three was recorded before the run and held |
| `S-6` errors at COLLECTION | research §15 | **REFINED** — 19 errors, but at fixture setup, with the traceback running through the archived `run.py` |
| `S-7` reds 27 in `test_ext00_hardening.py` | research §15 | **FALSIFIED** — 7 of 27. The 27 was measured with the whole tree missing, not with `serve.py` missing |
| `S-9` is invisible to the total | research §15 | **HELD, and stronger than stated** — it is invisible to the node-id SET, which is criterion 7's whole subject |
| criterion 12's `25 of 31` | criterion 12 | **FALSIFIED** — 19 of 31, at `PHASE_BASE` and at `HEAD` |
| `tests/examples` collects 515 | `D-IMPL-196` | **PHASE_BASE-true, HEAD-false** — 519 now, `515 + 4` wave-3 additions |

---

## Commits

| Commit | What |
|---|---|
| `7fa18e8` | `test(23-07)`: 61 paths in 28 files re-pointed at the archive; zero node ids lost |
| `fb85640` | `test(23-07)`: the five `H-14` assertions re-pointed, none weakened |
| *(this one)* | `docs(23-07)`: summary, `deferred-items.md` items 5–6, regenerated coupling report |

---

## Self-Check
: PASSED

Files claimed, all found: `tests/examples/test_hw1_harness_clients_retirement.py`,
`tests/examples/test_cross_process_output.py`, `tests/examples/test_ext00_hardening.py`,
`perf/suites/crossproc/conftest.py`, this summary, `deferred-items.md`.

The plan's four `artifacts.contains` clauses, each grepped rather than assumed:

```
OK  tests/examples/test_cross_process_output.py           contains archive/examples/04-cross-process
OK  tests/examples/test_ext00_hardening.py                contains archive/examples/external/00-hello-context
OK  tests/examples/test_hw1_harness_clients_retirement.py contains archive/examples/external/00-hello-context
OK  perf/suites/crossproc/conftest.py                     contains archive
```

Commits `7fa18e8` and `fb85640` both found in `git log --oneline --all`.

The plan's `<verification>` block, re-run:

```
PASS  pytest --collect-only -q                       -> 4231; ZERO node ids lost vs PHASE_BASE
PASS  four floors 9/12/14/12, every constant byte-identical to PHASE_BASE
PASS  test_hw1_harness_clients_retirement.py         -> 16 collected (== PHASE_BASE), 16 passed
PASS  the two executing modules                      -> 46 passed, 0 skipped, 0 xfailed
PASS  git diff PHASE_BASE..HEAD -- src/ runtime/ pyproject.toml -> exactly 23-06's four lines
PASS  git grep -c 's1-0' -- tests/ perf/             -> unchanged
```

Expected-still-RED at the end of this plan, as the plan predicts: `docs-strict`
(23-08), `test_documented_commands_exist` (23-09),
`test_the_committed_report_is_current` (23-11 — green transiently after the
regeneration below, and stale again on the next `.planning/` write). The `test`
leg is now green **except** the one blocking finding above, which is `23-06`'s
and needs a ruling.
