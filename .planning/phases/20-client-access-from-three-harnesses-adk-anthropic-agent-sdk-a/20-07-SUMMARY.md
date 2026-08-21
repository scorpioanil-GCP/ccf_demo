---
phase: 20-client-access-from-three-harnesses-adk-anthropic-agent-sdk-a
plan: 07
subsystem: examples — retiring the prior-vintage duplicates in-phase
tags: [retirement, git-mv, h-13, h-14, sabotage-controls, append-only-record]
requires:
  - "20-04: examples/hw1-harness-clients/runner/model_stub.py::offline_cli_environment — the extracted offline `claude` recipe, verified present with ten variables BEFORE the spike was deleted"
  - "20-06: the purity and budget gates over examples/hw1-harness-clients/, which the leg-3 docstring edit had to stay inside"
  - "docs/surface/examples/ERGO-03-FROZEN.md — this repository's precedent for a retired-material record under docs/"
provides:
  - "docs/retired/16-external-consumers/ — the Phase 16 orphans, moved with history and a written record"
  - "docs/retired/16-external-consumers/README.md — the retirement record naming Phase 16, D-IMPL-152 and examples/hw1-harness-clients/"
  - "tests/examples/test_hw1_harness_clients_retirement.py — the tree assertion, the LangGraph-only census, the positive H-14 assertion, and six numbered controls"
  - "tests/examples/test_hw1_harness_clients_retirement.py::untracked_paths_violations — the carried-forward ext-00 guard, narrowed to untracked files"
  - "examples/external/00-hello-context/README.md — the H-14 historical marking, prose under an existing heading"
  - "docs/DECISIONS.md D-IMPL-164, D-IMPL-165"
affects:
  - "20-08: examples/s2-01-external-consumers/ no longer exists; criterion 8's prior-vintage duplicates are discharged. The retirement inventory is current AS OF this plan's task-3 commit and is re-staled by this SUMMARY — 20-08 regenerates it"
  - "any later phase: D-IMPL-164 is ONE destination for ONE directory and may NOT be cited as a quarantine convention"
tech-stack:
  added: []
  patterns:
    - "a census scoped to exactly the claim its ruling makes, with the narrowing written into the function's own docstring so it does not read as an oversight"
    - "a retirement gate that asserts the historical example STAYS, so the gate cannot be satisfied by deleting things"
    - "a carried-forward assertion narrowed to the damage mode it actually guarded, rather than transplanted verbatim into a host that makes it fragile"
    - "every pointer into a quarantined tree confined to docs/, so no build path reaches unmaintained code"
key-files:
  created:
    - docs/retired/16-external-consumers/README.md
    - tests/examples/test_hw1_harness_clients_retirement.py
  modified:
    - docs/retired/16-external-consumers/client_langgraph.py (moved)
    - docs/retired/16-external-consumers/client_claude_agent.py (moved)
    - docs/surface/examples/SECTION-2-TRANSPORT.md
    - docs/surface/examples/RETIREMENT-COUPLINGS.md
    - docs/DECISIONS.md
    - examples/external/00-hello-context/README.md
    - examples/hw1-harness-clients/client_langgraph.py
    - tests/examples/test_artifact_schema_headers.py
  deleted:
    - tests/examples/test_s2_client_transport_spike.py
key-decisions:
  - "The reference sweep had SEVEN sites, not six. examples/hw1-harness-clients/client_langgraph.py:19 cited the moved path and was created by plan 20-03, after 20-07 was written. The row is added below"
  - "Every pointer into the retired tree is confined to docs/. This is what makes the task-1 criterion literally satisfiable: the destination name contains `external-consumers`, so any .py outside docs/ citing the new location would match the very grep that criterion runs"
  - "The carried-forward ext-00 assertion is NARROWED from `git status --porcelain` to untracked-files-only. The verbatim form would be red right now — this plan's own H-14 marking leaves ` M README.md` in git status for the length of a task"
  - "No control is written for `two ADK clients under examples/`, because two is the mandated state. A parametrized test records that positively instead"
  - "A row in the coupling inventory owned by a retired plan is a MEASUREMENT with a stale owner, not a work item"
patterns-established:
  - "A gate that names what it condemns will match a grep for the condemned name; the honest criterion is that no test CONSTRUCTS the path as a live subject"
requirements-completed: [CLNT-29, CLNT-30]
duration: ~2h
completed: 2026-08-21
---

# Phase 20 Plan 07: Retiring the Prior-Vintage Duplicates — Summary

**`examples/s2-01-external-consumers/` is out of `examples/` with its history
intact and a written record beside it; `examples/` now holds exactly one
LangGraph client; and `examples/external/00-hello-context/` is marked
historical by a sentence rather than a move — seven headings intact,
`make example-ext-00` still green.**

## The measurement that matters

```
find examples -name 'client_langgraph.py' | wc -l   ->  1     (H-13's claim, discharged)
find examples -name 'client_anthropic.py' | wc -l   ->  2     (H-14's mandated state, NOT a violation)
find examples -name 'client_adk.py'       | wc -l   ->  2     (same)
grep -c '^## ' examples/external/00-hello-context/README.md  ->  7
git diff <README> | grep -c '^[-+]## '                        ->  0
```

`make ci` exits **0**: `4064 passed, 118 skipped` in 10m29s, plus `406 passed`
in `tools/lints/tests` and `154 passed` in
`tools/publish_scan_tests tools/docs_tests`. The arithmetic is exact — the
tree carried 4066 before this plan, the deleted spike held 15 tests and the
new retirement module holds 13.

`make example-ext-00` prints its eight PASS lines in 19.3s.
`examples/hw1-harness-clients` still prints one address across three legs with
**no refusal line**:

```
reference address   5d7bfa49f5b3f65add25ea61220a191a91982f5ae97901e010b26c5ca8dc37f5
leg adk             5d7bfa49…  MATCH  names: Kestrelmark Industries, Volanti Logistics, Brightpath Materials
leg anthropic       5d7bfa49…  MATCH  names: …
leg langgraph       5d7bfa49…  MATCH  names: …
legs compared       3
```

## The sequencing precondition, run before anything was deleted

```
.venv/bin/python -c "… m.offline_cli_environment(…) …"
recipe extracted 10
```

`examples/hw1-harness-clients/runner/model_stub.py::offline_cli_environment`
exists and answers **ten** variables against the nine the precondition
required. The spike was the only worked offline `claude` recipe in the tree;
it was extracted by plan `20-04` before this plan deleted it, and `20-04`
improved it in passing — the spike shipped `DISABLE_NON_ESSENTIAL_MODEL_CALLS`,
which the bundled binary never reads.

## Task-by-task

| Task | Commit | What landed |
|---|---|---|
| 1 — the move, the record, the prose references | `e4e8e1d` | `git mv` to `docs/retired/16-external-consumers/`; `README.md`; `SECTION-2-TRANSPORT.md` repointed; the stale `test_artifact_schema_headers.py` docstring corrected; the seventh reference site handled |
| 2 — the spike retired, the tree asserted | `6d8afa0` | `test_s2_client_transport_spike.py` deleted; `test_hw1_harness_clients_retirement.py` created — 13 tests, six controls |
| 3 — the marking, the inventory, the record | `8783a38` | The `H-14` blockquote; `RETIREMENT-COUPLINGS.md` regenerated; `D-IMPL-164` and `D-IMPL-165` appended |

## THE REFERENCE SWEEP HAD SEVEN SITES, NOT SIX

The plan's `<reference_sweep>` table claims repo-wide completeness, and its own
text says a missing row falsifies the whole table. Measured repo-wide
(excluding `.git`, `.venv`, `.planning/`) at the start of execution, there were
**seven**. The seventh did not exist when the plan was written — plan `20-03`
created it three waves earlier in the same phase.

| # | Reference | Shape | Liveness | Disposition |
|---|---|---|---|---|
| 1 | `tests/examples/test_s2_client_transport_spike.py` `LEG_DIR` | constructs the path | **LIVE — build goes red** | Module deleted (task 2) |
| 2 | `docs/surface/examples/SECTION-2-TRANSPORT.md:24` | prose naming `client_langgraph.py` | documentary | Repointed at the retired path with a note naming the move and the replacement |
| 3 | `docs/surface/examples/RETIREMENT-COUPLINGS.md` | inventory rows | documentary | **Regenerated** by the tool |
| 4 | `tests/examples/test_artifact_schema_headers.py:445` | docstring naming a `fixtures/` dir plan 16-09 never shipped | documentary | Sentence corrected; the justification it carried is unchanged and no longer depends on a directory that never existed |
| 5 | `docs/DECISIONS.md` `D-IMPL-125` | prose, historical record | documentary | **NOT rewritten.** Verified byte-identical to HEAD |
| 6 | `docs/DECISIONS.md` `D-IMPL-136` | prose, the no-bulk-migration list | documentary | **NOT rewritten.** Verified byte-identical to HEAD |
| **7** | **`examples/hw1-harness-clients/client_langgraph.py:19`** | **docstring citing the moved file as the source of its no-bridge-package rationale** | **documentary, and inside a gated example** | **ADDED BY EXECUTION.** Repointed at `docs/surface/examples/SECTION-2-TRANSPORT.md`, the spike record that actually holds the measurement |

Both `D-IMPL-125` and `D-IMPL-136` were verified programmatically against
`git show HEAD:docs/DECISIONS.md` rather than by eye: the entry lines are
byte-identical, and the whole `docs/DECISIONS.md` diff is `4 insertions, 0
deletions`.

**Not found anywhere, re-verified:** `Makefile`, `.github/workflows/*.yml`,
`mkdocs.yml`, `public/`, `pyproject.toml`. No `make` target and no CI job
named `s2-01`. Nothing broke by moving it.

## Deviations from Plan

### 1. [Rule 3 — Blocking] Task 2's zero-occurrence criterion cannot coexist with task 2's own gate

- **Found during:** Task 2, running the acceptance criteria.
- **Issue:** The criterion is `grep -rn 's2-01\|s2_01' tests/ | wc -l` returns
  `0`. The same task requires *"a tree assertion holds
  `examples/s2-01-external-consumers/` gone"*. An assertion that a directory is
  absent has to name the directory. The two cannot both hold.
- **Resolution:** The criterion is read as what it means — *"nothing in the
  test tree still **constructs** the moved path"* — and measured that way. The
  single remaining occurrence is
  `test_hw1_harness_clients_retirement.py::CONDEMNED_DIRECTORY_NAME`, the
  constant the gate compares against. Measured:
  `grep -rn 's2-01\|s2_01' tests/ | grep -cv test_hw1_harness_clients_retirement.py` → `0`.
  No live path construction survives.

### 2. [Rule 3 — Blocking] The destination name collides with task 1's own grep

- **Found during:** Task 1.
- **Issue:** The plan mandates the destination `docs/retired/16-external-consumers/`
  **and** a criterion that
  `grep -rn 's2-01\|s2_01\|external-consumers' --include='*.py' … --exclude-dir=docs`
  returns nothing. The destination name contains `external-consumers`, so any
  `.py` outside `docs/` citing the new location trips the criterion the plan
  itself set.
- **Resolution:** Satisfied literally, by confining **every** pointer into the
  quarantined tree to `docs/`. `examples/hw1-harness-clients/client_langgraph.py`
  now cites `docs/surface/examples/SECTION-2-TRANSPORT.md` — the spike record
  that holds the measurement — instead of the retired file, and
  `tests/examples/test_artifact_schema_headers.py`'s corrected docstring names
  no path at all. This is the better outcome, not a workaround: no build path,
  test or example now reaches into unmaintained code, which is what `CLNT-17`'s
  no-partial-state is for. Measured: the grep returns nothing.

### 3. [Rule 2 — Missing critical functionality] The carried-forward assertion was narrowed, not transplanted

- **Found during:** Task 2, accounting for
  `test_the_shipped_external_example_is_untouched`.
- **Issue:** `tests/examples/test_ext00_hardening.py` does **not** carry it, so
  it had to be carried forward. But its shipped form —
  `git status --porcelain -- examples/external/00-hello-context/` must be
  empty — is a *side-effect* check belonging to a module that spawned that
  server and read its artifacts. Transplanted verbatim into a general module it
  goes red for any legitimate uncommitted edit. **This plan proves it:** during
  task 3, `git status --short examples/external/00-hello-context/` printed
  ` M examples/external/00-hello-context/README.md` — the `H-14` marking. The
  verbatim assertion would have been red for the length of the task.
- **Resolution:** Carried forward as
  `test_hw1_harness_clients_retirement.py::untracked_paths_violations`,
  narrowed to `git ls-files --others --exclude-standard`. Untracked files are
  the damage mode the original guarded — a test writing *into* a shipped
  example tree — and a reviewed edit to a tracked file is not. CONTROL 6 watches
  it fail. The narrowing and its measured reason are written into the module
  docstring and into `D-IMPL-165`.

## Controls: six written, all seven mutations observed red

Each mutation was applied to the property function in place, the single control
run, and the module restored and verified byte-identical afterwards.

| Control | Subject | Mutation applied | Observed |
|---|---|---|---|
| CONTROL 1 | synthetic `examples/` still holding `s2-01-external-consumers/client_langgraph.py` | the `condemned.exists()` branch of `retirement_violations` removed | **RED**, exit 1 |
| CONTROL 2 | synthetic retired destination with no `README.md` | the `not record.is_file()` branch removed | **RED**, exit 1 |
| CONTROL 3a | a non-existent `examples_root` | `retirement_violations` answers a missing root with `[]` | **RED**, exit 1 |
| CONTROL 3b | a non-existent `examples_root` | `langgraph_census_violations` answers a missing root with `[]` | **RED**, exit 1 |
| CONTROL 4 | synthetic tree with two `client_langgraph.py` | the over-count branch of `langgraph_census_violations` removed | **RED**, exit 1 |
| CONTROL 5 | synthetic `external/00-hello-context/` missing `client_adk.py` | `historical_example_violations` stops reporting missing clients | **RED**, exit 1 |
| CONTROL 6 | a real `git init` repo with an untracked `graph.sqlite3` under the guarded tree | `untracked_paths_violations` drops git's answer | **RED**, exit 1 |

**Controls that could not be made to fail: none.**

**The control deliberately NOT written, and why.** There is no control for
*"two ADK clients under `examples/` is a violation"* — because **two is the
mandated state.** `H-14` keeps `examples/external/00-hello-context/` with its
own `client_adk.py` and `client_anthropic.py`; `H-10` puts Phase 20's trio at
`examples/hw1-harness-clients/`. A per-harness census refusing any count above
one would go red against the tree this phase was ruled to produce. The absence
is recorded three times so it is not later scored as a gap: in
`langgraph_client_count`'s docstring, in
`test_two_of_these_names_under_examples_is_the_mandated_state` (a parametrized
test asserting the count **is** 2, which fails if a later change resolves the
duplication by deletion instead of by the marking), and in `D-IMPL-165`.

**`H-13`'s claim is the only count asserted.** `must_haves`, the task-1
acceptance criteria, the task-1 `<verify>` block and
`langgraph_census_violations` all say the same thing: LangGraph, 2→1. Nothing
in this module counts ADK or Anthropic clients as a violation.

## What a coupling row owned by a retired plan means now — the judgement the plan asked for

The regenerated inventory carries 242 rows in five ownership buckets: `16-02`
(10), `16-15` (24), `16-17` (41), `16-18` (109), `17-08` (58). Four of those
five owners are plans withdrawn under `D-IMPL-152`; the fifth belongs to a
closed phase. Not one of them can act on a row.

**The judgement: an ownership column naming a withdrawn plan does not
invalidate the row — it relocates the obligation.** A coupling row is a
*measurement* (this file, at this line, names that retiring path, in this
shape, with this liveness). The measurement is true regardless of who was
supposed to act on it. What the stale owner tells you is that **nobody is
scheduled to**, which is exactly the signal `D-IMPL-152` says must not be lost:
*"retiring the phase retires the APPROACH, never the NEED."*

Two consequences, stated rather than implied:

1. **The inventory is a hazard map, not a work queue.** Its value is that a
   phase about to move an example tree can see, before it moves, what will
   break. This plan used it that way. It is not a backlog and nothing should be
   executed from it — the same posture `D-IMPL-152` sets for `abandoned/`.
2. **The `owning plan` column should be re-derived, not re-assigned, when the
   sweep is next changed.** Re-assigning 242 rows to live plans would be a
   fabrication: no live plan has agreed to own them. That is a separate
   decision for a phase that scopes it, and this plan does not make it.

The sweep's own suite (`tools/docs_tests`, run by `make gate-tools`) is
**green** on the regenerated output — 154 passed. Nothing to surface there.

## The `H-14` marking

Added as a blockquote paragraph at the top of `## What this demonstrates`, so
a reader hits it before anything else in the section. **No `## ` heading was
added** — `examples/external/00-hello-context/run.py::_assert_seven_heading_readme`
requires exactly seven, by exact name and in order, and it is `PASS 4` of the
example's own run. Verified both ways: the count is `7`, and
`git diff | grep -c '^[-+]## '` is `0` — no heading line was added *or*
removed. `make example-ext-00` exits 0.

## The retirement inventory, regenerated as the final step

```
.venv/bin/python tools/retirement_sweep.py --report
wrote docs/surface/examples/RETIREMENT-COUPLINGS.md
242 coupling rows across 80 files (146 rows outside the three swept trees); 1822 files scanned
```

Run unprefixed, as `<retirement_currency>` specifies; the report's own
`## Re-running` header prints the `PYTHONPATH=.:src:runtime` form and neither
was edited to match the other. **Idempotent**: a second run left the file
byte-identical (`diff -q` exit 0). Never hand-edited. The currency test —
`tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current`
— passes, which is the acceptance criterion, not the fact that the file
changed.

**The report is current as of commit `8783a38` and is re-staled by this
SUMMARY**, which lands under `.planning/` and names retiring paths. That is the
per-plan cycle `<retirement_currency>` describes, and plan `20-08` regenerates
it for this one.

## Invariants held

| Invariant | Measured |
|---|---|
| Nothing under `src/` changed | `git diff --stat 9e4bd0e..HEAD -- src/ \| wc -l` → `0` |
| The wave-2 prompt arm not weakened | `git diff c1ddbb8..HEAD -- tools/lints/allowlist.yaml` and `-- tools/lints/no_hardcoding.py` both empty |
| `docs/DECISIONS.md` append-only | `4` insertions, `0` deletions; `D-IMPL-125` and `D-IMPL-136` byte-identical to HEAD |
| History followed the move | `git log --follow` on `docs/retired/16-external-consumers/client_langgraph.py` reaches `33c0626 feat(16-03)` |
| Citation ceiling (`MAXIMUM_UNANCHORED_PY_CITATIONS = 0`) | `.venv/bin/python -m tools.lints --citations` exit 0 at every step |
| No package installed | none |
| `H-14`'s example intact and green | three clients present; `make example-ext-00` exit 0 |
| Nothing written into the tracked hw1 tree | the drive seeds `/tmp/ccf-hw1-clients-*` copies only |

## Threat register disposition

| Threat ID | Disposition | How |
|---|---|---|
| T-20-27 (repudiation, the move) | mitigated | `git mv` with `--follow` verified; a record naming Phase 16, `D-IMPL-152` and the replacement; `D-IMPL-164` and `D-IMPL-165` appended |
| T-20-28 (DoS, `make ci`) | mitigated | marking is prose; heading count `7` and zero added/removed `## ` lines both asserted; `make example-ext-00` green |
| T-20-29 (tampering, the CLI recipe) | mitigated | the sequencing precondition was run mechanically and answered ten variables before the deletion |
| T-20-30 (repudiation, lost coverage) | mitigated | the ext-00 assertion is accounted for in writing — not duplicated in `test_ext00_hardening.py`, carried forward narrowed, with CONTROL 6 |
| T-20-31 (tampering, the inventory) | mitigated | regenerated by the tool, never hand-edited; idempotency asserted; `make gate-tools` green |
| T-20-32 (repudiation, historical record) | mitigated | `D-IMPL-125`/`D-IMPL-136` byte-identical, verified against `git show HEAD:` |
| T-20-SC (package installs) | mitigated | none installed |

## Known Stubs

None.

## Threat Flags

None. This plan adds no network endpoint, no auth path, no file-access pattern
and no schema at a trust boundary. It removes surface: two client programs
moved outside every lint and gate scope, and one live test path into them
deleted.
