---
phase: 19-the-client-seam-integrity-checks-must-be-able-to-fail-insert
plan: 05
subsystem: client-seam / integrity gates
tags: [ast-gate, C-17, C-13, CLNT-06, CLNT-12, D-22, sabotage-control]
requires:
  - "ccf.products.door.DoorOutcome — the one outcome shape, landed by 19-01"
  - "ccf.client.wire.WireOutcome — the alias, landed by 19-01"
  - "src/ccf/client/adapters/ containing no construction — made true by 19-02"
provides:
  - "tests/client/test_surface.py::count_outcome_construction_sites — the C-17 scan"
  - "tests/client/test_surface.py::assert_no_adapter_constructs_the_outcome"
  - "tests/client/test_surface.py::ADAPTER_ROOTS — the one scoped directory"
affects:
  - "19-04 (named in the gate's blind-spot paragraph as what covers re-labelling)"
  - "19-07 (prose; the gate's docstring states what it cannot reach)"
  - "19-08 (the D-IMPL entry ratifying C-17)"
tech-stack:
  added: []
  patterns:
    - "mirror a gate's pattern rather than importing it, so one cannot silently change the other"
    - "hold a rule's NECESSITY with a deliberately weakened reference walk, not just its presence"
    - "measure the population before writing the docstring sentence that describes it"
key-files:
  created: []
  modified:
    - "tests/client/test_surface.py"
decisions:
  - "Two extra controls beyond the plan's nine: a weakened name-only walk and a weakened module-scope-only walk, each asserting the weak walk counts 0 where the shipped walk counts 1 — so the two rules' necessity is CI-held rather than SUMMARY-claimed"
  - "The coverage leg names all four adapter modules as a subset floor rather than pinning an exact set, matching the existing scan's floor style"
metrics:
  duration: "~1h15m"
  tasks: 2
  commits: 3
  collected_delta: "3935 -> 3949 (+14)"
  completed: 2026-08-20
---

# Phase 19 Plan 05: The Gate That Says No Adapter Constructs The Outcome — Summary

Turned *"no adapter constructs the outcome"* from a convention a reviewer holds
into a red check over `src/ccf/client/adapters/`, counting both shapes its
analog counts, and shipped it with a sabotage control that was **observed
failing** in two independent ways before this was written down.

## What Was Built

**One scan over one directory.** `count_outcome_construction_sites(roots)` in
`tests/client/test_surface.py`, mirroring `count_result_construction_sites`
and deliberately **not** importing it — the two scans are independent, so a
change to one cannot silently change the other. `ADAPTER_ROOTS` is a single
directory, because `ccf.products.door.door_answer` is the one legitimate
construction site and a wider scope would count it and force an exemption
list, which is how a narrow gate becomes the framework `C-13` rejected.

**Two counted shapes, because the analog counts two.** A call to a local name
bound by an import (resolved against both `ccf.client.wire` and
`ccf.products.door`, both spellings, honouring `as` aliases), **and** any
attribute call spelled `….WireOutcome(...)` / `….DoorOutcome(...)` whatever it
is an attribute of. The second is deliberately broad on the analog's own
argument — over-counting fails the build and puts a human in front of the
question; under-counting is the silent direction.

**The walk is `ast.walk` over the whole module**, not module scope, because an
adapter constructs inside `ask`, not at import time.

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | The C-17 assertion, red against a function that does not exist | `20905fe` | `tests/client/test_surface.py` |
| 1 (GREEN) | `count_outcome_construction_sites` and the shipped assertion | `a5e8bc5` | `tests/client/test_surface.py` |
| 2 | The named sabotage control over a `tmp_path` tree | `5c4a2d4` | `tests/client/test_surface.py` |

## The Full Mapping Over The Adapters Directory

Printed from the **shipped** function, not from a re-implementation:

```
roots: ['<worktree>/src/ccf/client/adapters']
  src/ccf/client/adapters/__init__.py: 0
  src/ccf/client/adapters/binding_document.py: 0
  src/ccf/client/adapters/inprocess.py: 0
  src/ccf/client/adapters/mcp_stdio.py: 0
modules read: 4
constructing: []
```

Every module gets an entry including the zeros, which is what lets *no adapter
constructs one* be distinguished from *nothing was read*.

## The Measurement Behind The Broad Attribute Rule

Run as a one-off AST script **before the rule was written**, per the analog's
own discipline. Counting `ast.Call` nodes whose `func` is an `ast.Attribute`
with `attr in {"WireOutcome", "DoorOutcome"}`:

| Tree | Modules | Attribute-call constructions |
|------|---------|------------------------------|
| `src/ccf/client/adapters/` (the gate's scope) | 4 | **0** |
| `src/` (informational) | 100 | 0 |
| `runtime/` (informational) | 36 | 0 |

The docstring's sentence claims **only** the first row — four modules, zero
hits — because that is the population the gate covers. The other two rows are
recorded here and deliberately **not** in the docstring: a gate that makes a
claim about a tree it does not scan is the defect this phase is named after.

`tests/` was not scanned. It contains forging fixtures by design (this plan
writes five of them), so a number over it would be meaningless, not merely
noisy. It is also where wave-3 siblings `19-04` and `19-06` are working.

## Both Rules Are Necessary — Measured, Not Assumed

Before writing the shipped walk, three variants were run over the same seven
sources: **V1** names-only + module-scope-only, **V2** names-only + full walk,
**V3** the shipped rule.

| Case | V1 | V2 | V3 |
|------|----|----|----|
| 1 plain `WireOutcome` import | 1 | 1 | 1 |
| 2 `DoorOutcome` from `ccf.products.door` | 1 | 1 | 1 |
| 3 `as`-aliased import | 1 | 1 | 1 |
| **4 nested in a function body** | **0** | 1 | 1 |
| **5 attribute call, no local name** | **0** | **0** | 1 |
| V-a annotation only | 0 | 0 | 0 |
| V-b neither imports nor constructs | 0 | 0 | 0 |

**Case 5 was written first and observed to count 0** against a walk resolving
only import aliases — it binds no local name, so alias resolution has nothing
to find. It is the case that discharges the blocker.

**Case 4 was written first and observed to count 0** against a module-scope-only
walk. Task 1's implementation does walk the full tree; that was **confirmed
rather than assumed** by this table and then pinned permanently — see below.

**This is not left as a SUMMARY claim.** Two controls
(`test_control_the_attribute_rule_is_the_only_thing_that_catches_case_five`,
`test_control_the_full_walk_is_the_only_thing_that_catches_case_four`) carry
deliberately weakened reference walks (`_names_only_sites`,
`_module_scope_only_sites`) and assert the weak walk counts `0` where the
shipped walk counts `1`. A future "simplification" of the walk goes red and
explains what it costs. This is two tests beyond the plan's nine, and it is the
reason for the count below.

## The Gate Was OBSERVED Failing — Twice, Two Different Ways

`CLNT-12` / `D-22`. Neither observation edited a tracked file; both ran from
scratch scripts, and `git status --porcelain src/` was clean throughout.

### Sabotage 1 — the shipped assertion against a forging *real* adapter

The real `src/ccf/client/adapters/` was copied **out of the tree** and one
construction added to the real `inprocess.py`:

```
BASELINE  : real adapters directory passes the gate
SABOTAGED : counts = {'__init__.py': 0, 'binding_document.py': 0,
                      'inprocess.py': 1, 'mcp_stdio.py': 0}
SABOTAGE OK: the gate went RED ->
    no adapter may construct the outcome shape (C-17), and 1 module(s) do:
    .../inprocess.py (1 site(s)). An adapter that builds the answer can fill
    `request` from the argument it was handed, and the cli...
RESTORED  : real adapters directory still passes the gate
```

### Sabotage 2 — weaken the gate, watch its own controls go red

A control that cannot fail proves nothing either. `test_surface.py` was copied
to an untracked probe file **at the same depth** and two weakenings applied,
then the probe was deleted in a `finally`:

| Weakening | Result | Which controls went red |
|-----------|--------|-------------------------|
| A: attribute branch removed | **2 failed, 31 passed** | the attribute-necessity control, and the parametrized forgery's `attribute-qualified-call` case |
| B: module scope only | **7 failed, 26 passed** | both necessity controls, and **all five** parametrized forgery cases |

The discrimination is exact and is itself evidence the controls are not
blunt: weakening A leaves the nested-body control **green** (it does not touch
nesting), while weakening B reds all five forgeries because every one of them
constructs inside `ask` — which is the point case 4 exists to make.

**A first attempt at sabotage 2 was contaminated and is recorded rather than
hidden.** Running the probe from `/tmp` made
`_REPO_ROOT = Path(__file__).resolve().parents[2]` resolve to `/`, which
changed the mapping's key format and failed 16 tests for a reason unrelated to
the weakening. The run above is the corrected one, at the original's depth. An
uncorrected reading of that first run would have over-claimed the controls'
reach.

## Collected-Count Arithmetic

`tests/client/test_surface.py`: **19 → 33 (N = +14)**, and the full suite moves
by exactly the same 14, so nothing else in the tree changed behaviour.

| | Before | After | Δ |
|---|---|---|---|
| `tests/client/test_surface.py` | 19 | 33 | **+14** |
| `tests/client` | 376 | 390 | +14 |
| full suite (`make ci-core`) | 3935 | **3949** | +14 |

Each increment, named against `C-17`:

| # | Test | What it holds |
|---|------|---------------|
| 1 | `test_no_adapter_constructs_the_outcome` | the shipped assertion — `C-17` itself |
| 2 | `test_the_outcome_scan_reads_every_adapter_module` | the walk is not vacuous; all four modules present, all `0` |
| 3 | `..._counts_a_forging_adapter[imported-from-ccf.client.wire]` | CONTROL 13 — the plain import |
| 4 | `..._counts_a_forging_adapter[imported-from-ccf.products.door]` | CONTROL 14 — the same class via its defining module |
| 5 | `..._counts_a_forging_adapter[imported-under-an-as-alias]` | CONTROL 15 — the shape a `grep` misses |
| 6 | `..._counts_a_forging_adapter[nested-in-a-function-body]` | CONTROL 16 — deferred into a function, where an adapter puts it |
| 7 | `..._counts_a_forging_adapter[attribute-qualified-call]` | CONTROL 17 — binds no local name at all |
| 8 | `..._the_attribute_rule_is_the_only_thing_that_catches_case_five` | CONTROL 18 — the attribute rule's **necessity** |
| 9 | `..._the_full_walk_is_the_only_thing_that_catches_case_four` | CONTROL 19 — the full walk's **necessity** |
| 10 | `..._does_not_count_a_mere_annotation` | CONTROL 20 — vacuity: importing is not constructing |
| 11 | `..._does_not_count_an_unrelated_module` | CONTROL 21 — vacuity: the zeros are present |
| 12 | `..._refuses_a_root_it_cannot_resolve` | CONTROL 22 — raises, never skips |
| 13 | `..._refuses_a_file_it_cannot_parse` | CONTROL 23 — raises, never skips |
| 14 | `..._refuses_a_walk_that_read_nothing` | CONTROL 24 — the vacuous walk |

Both vacuity cases assert `== 0` on the **written module's own entry**, not on
the mapping being empty — an empty mapping means nothing was read, which is a
different and worse condition.

## Verification

| Step | Result |
|------|--------|
| `pytest tests/client/test_surface.py -q` | **33 passed, 0 failed** |
| `pytest tests/client -q` | **390 passed, 0 failed** |
| `make lint` | **exit 0** |
| `make ci-core` | **exit 0** — 3949 passed, 118 skipped, 0 failed; 400 lint-tool; 154 publish/docs |
| `git status --porcelain src/` | **clean** (checked after both sabotages) |
| the full mapping over the adapters directory | pasted above; 4 entries, all `0` |

**Source assertions:**

| Assertion | Required | Measured |
|-----------|----------|----------|
| `grep -c "def count_outcome_construction_sites"` | 1 | 1 |
| `grep -c "ast.Attribute"` | increases by ≥ 1 | 1 → **2** |
| the new branch tests `attr in` a **two-name set** | yes | `function.attr in _OUTCOME_NAMES`, a two-name `frozenset` |
| `grep -c "getattr"` | increases by ≥ 1 | 2 → **3** |
| `grep -c "model_copy"` | ≥ 1 | **1** |
| `grep -c "match="` | increases by ≥ 2 | 7 → **11** (+4) |
| the gate does not import or call `count_result_construction_sites` | yes | the two scans share no code; separate `_outcome_aliases` / `_outcome_construction_sites` helpers |
| existing `CLNT-06` assertion still green, count unchanged | yes | all 19 pre-existing tests still pass |

## The must-have truths, each verified

1. **No module under `src/ccf/client/adapters/` constructs the outcome by
   either counted shape** — proven by a red check over the tree, not by
   convention and not by a type annotation `mypy` only sees inside
   `src`/`runtime`. Mapping pasted above; both shapes controlled.
2. **The gate names what it cannot reach, in its own docstring** — `getattr`
   dispatch, and decode/`model_copy`/re-encode **re-labelling**, which is not a
   construction at all and is invisible to any construction counter. The
   docstring states plainly that this is not hypothetical because this phase's
   own `19-03`/`19-04` controls use that idiom, and names `19-04`'s conformance
   obligation as what covers it.
3. **It mirrors `CLNT-06`'s pattern exactly** — roots as a parameter, an entry
   for every module read including zeros, and `AssertionError` rather than a
   skip for an unresolvable root or an unparseable file.
4. **It carries its own named sabotage control, in this same plan** — twelve
   controls, plus two out-of-tree observations of the gate actually going red.
5. **One assertion over one directory** — `ADAPTER_ROOTS` is a single path and
   is not `SCANNED_ROOTS`; no exemption list exists because none is needed.
6. **The shipped assertion refuses a walk that read nothing** — checked first
   and separately, with CONTROL 24 holding it.

## Deviations from Plan

### Where the plan was measurably wrong

**1. `grep -c "roots: Sequence[pathlib.Path]"` was already 2 at baseline, not
1.** The criterion said it should *"return 2 (the existing scan and the new
one)"*, which assumed one pre-existing occurrence. There were already two —
`count_result_construction_sites` and `assert_one_result_construction_site`
both take the parameter. After this plan it is **4**, for the same reason: the
new scan and its new assertion both take it. The criterion's intent (the new
function takes its roots as a parameter, so a control can point it at a tree it
actually reads) is satisfied and was verified directly.

**2. The plan's `<read_first>` line citations are stale, as waves 1 and 2 both
warned.** `test_surface.py:256-265` for the two-shape counter is actually
`_construction_sites`; `:269-360` for `count_result_construction_sites` is
roughly `:269-317`. Every symbol name was correct and was used to find the
code. `D-IMPL-114` rules that prose cites `path.py::Symbol` for exactly this
reason.

**3. Nine new tests were specified; fourteen shipped.** Two are the shipped
assertions (Task 1). The other twelve are Task 2's, which is three more than
the nine required: the extra three are the two **necessity** controls described
above, plus a `read-nothing` vacuous-walk control. The necessity controls exist
because the plan required case 4 and case 5 to be *"confirmed rather than
assumed"* — and a confirmation that lives only in a SUMMARY decays the moment
someone edits the walk, which is this repo's recorded failure mode.

### Rule 2 — auto-added, for correctness

The two necessity controls (CONTROL 18, 19) are an addition under Rule 2. The
plan asked that the two hard cases be *observed* discriminating; observation
recorded only in prose is not a property of the tree. Pinning it costs two
small tests and converts the plan's own acceptance criterion into something CI
re-checks on every run.

### Not done, and deliberately

- **No production code was touched.** `git status --porcelain src/` clean; the
  whole plan is one test file.
- **`.planning/STATE.md` and `.planning/ROADMAP.md` were NOT written**, per the
  orchestrator's standing instruction. (`19-02`'s recorded `make ci-core`
  blocker on `STATE.md`'s two citations is already resolved in this plan's base
  commit `8020d67`; `make lint` exits 0 here.)
- **No surface fragment was filed.** This plan adds no public SDK name — the
  new functions are test-module-local. The surface gates were green in the
  `make ci-core` run above, confirming rather than assuming this.
- **`tests/` was not scanned for a whole-tree attribute number.** Reasons in
  the measurement section.

## Known Stubs

None. Every constant added is read by the walk or by a control; every control
asserts on a subject the shipped function actually reads.

## Threat Flags

None beyond the plan's own `<threat_model>`. `T-19-15` is mitigated and the
mitigation was observed failing under sabotage; `T-19-16` is mitigated with
three unresolvable-case controls; `T-19-17` remains **transferred** and is
stated in the docstring rather than implied — an out-of-tree adapter is
reachable by no in-tree gate. `T-19-SC` holds: no package was installed and no
dependency added.

## Note For The Orchestrator — a sibling agent's run was visible on the host

`pgrep` during verification showed a second `make ci-core` running from a
different working directory (no `PYTHON` override, invoking a relative
`.venv/bin/python`), i.e. a wave-3 sibling. Reported, not acted on: this
worktree's `git status` showed only this plan's own file throughout, so no
foreign state entered the tree. It is noted only because it roughly doubled
`make ci-core`'s wall time (636s for the pytest leg).

One environment note the next executor will hit: **this worktree has no
`.venv`** (it is gitignored and not copied into worktrees), so
`.venv/bin/python` does not resolve here. Every command was run as
`PYTHONPATH=src:runtime /home/parkave/ccf_code/.venv/bin/python …`, and `make`
targets as `make PYTHON=/home/parkave/ccf_code/.venv/bin/python …`. Imports
were verified to resolve **inside the worktree** before any measurement was
taken.

## Self-Check: PASSED

Modified files:
- FOUND: `tests/client/test_surface.py`

Commits (all present in `git log`):
- FOUND: `20905fe` `test(19-05): the C-17 assertion over the adapters directory, red`
- FOUND: `a5e8bc5` `test(19-05): count_outcome_construction_sites, the C-17 gate over the adapters directory`
- FOUND: `5c4a2d4` `test(19-05): the C-17 gate's named sabotage control, over a tmp_path tree`

Key links (matched):
- `tests/client/test_surface.py` → `def count_outcome_construction_sites` — 1 match
- `tests/client/test_surface.py` → `ADAPTER_ROOTS` bound to `src/ccf/client/adapters` — 1 match
