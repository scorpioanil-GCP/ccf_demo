---
phase: 20-client-access-from-three-harnesses-adk-anthropic-agent-sdk-a
plan: 06
subsystem: testing
tags: [ast-gate, purity, budget, command-identity, criterion-5, sabotage-controls]

requires:
  - phase: 20-05
    provides: "The three shipped `client_*.py` programs and `runner/drive.py`, whose imports, line counts and leg names this plan's gates read"
provides:
  - "A per-root permitted-import policy: one mapping, two roots, opposite verdicts on `ccf.client`, with `CLIENT_EXAMPLE_ROOTS` derived from it"
  - "A by-name refusal of `ccf` for the harness root, in a branch checked before the permitted-set test, so it survives that set being widened"
  - "A measured line budget (300, against a largest client of 288) declared once in the new README and enforced per module"
  - "Three documented commands paired character-identically with three one-line make recipes, asserted to differ at exactly one token"
  - "Thirteen sabotage mutations, every one observed red — C-20-1..C-20-9 plus four beyond the plan's roster"
affects: [20-07, 20-08]

tech-stack:
  added: []
  patterns:
    - "Policy as a per-root parameter, not a module-level constant: the union is the regression and one named control is what catches it"
    - "A control that asserts the REASON, not just the count, when two branches of a checker fire on the same subject"

key-files:
  created:
    - examples/hw1-harness-clients/README.md
  modified:
    - tests/examples/test_client_example_purity.py
    - tests/examples/test_client_example_budget.py
    - Makefile
    - docs/surface/examples/RETIREMENT-COUPLINGS.md

key-decisions:
  - "H-12's stated mechanics were contradicted by measurement and the plan's correction was applied: the permitted set is a per-root parameter, not a line of glue. H-12's intent — extend the module, weaken no rule, keep the runner structurally outside — is honoured in full"
  - "The declared budget is 300, derived from measurement (186/288/235), not from the plan's stale '~150 target' which described none of the three clients"
  - "Two mutations came back GREEN on the first sabotage sweep. Both were answered with new controls rather than reported as acceptable, because both were real holes in this plan's own control set"
  - "No second prompt checker was added. Prompt enforcement stays with tools/lints/no_hardcoding.py's destination arm from plan 20-02"

patterns-established:
  - "When a checker has two branches that both fire on one control subject, the control asserts which branch spoke — otherwise deleting either leaves it green"
  - "A gate armed automatically by importing another module's root tuple owes that root its own control; the pre-existing ones all build from CLIENT_EXAMPLE_ROOTS[0]"

requirements-completed: [CLNT-25]

metrics:
  tasks: 3
  commits: 3
  duration: "~2h"
  tests_before: 4032
  tests_after: 4066
  gate_module_tests_before: 31
  gate_module_tests_after: 65
---

# Phase 20 Plan 06: Client purity, budget and command identity for the harness root — Summary

The AST purity gate now covers `examples/hw1-harness-clients` as well as
`examples/hw1-companies-over-revenue`, with a **per-root** permitted-import
policy, a `ccf` refusal that names `ccf` rather than merely omitting it, a
measured 300-line budget the three clients fit, three documented commands
paired character-identically with three make recipes — and thirteen sabotage
mutations, every one observed red.

## What was measured before anything was written

The plan carried three numbers that measurement contradicted. All three were
corrected against the tree rather than followed.

| The plan said | The tree said | What was done |
| --- | --- | --- |
| `H-12`: adding the root "gates the three clients untouched" | `_permitted` admits only stdlib + `ccf.client`; the shipped parametrized assertion goes red on `import google.adk` | The permitted set became a per-root parameter — the plan's own `<measured_correction>`, applied |
| "the realistic range is **120-150**" lines | 186 / 288 / 235 physical lines | Declared **300**, twelve lines over the largest |
| `run.py`, `artifacts/` as gate traps | The runner is `runner/drive.py`; there is no `run.py` and no `artifacts/` | The probe was run against the real names; no file was created to satisfy a snippet |

**Plan drift, reported rather than worked around:** the plan's task-1 acceptance
probe asserts `'run.py' not in mods and 'model_stub.py' not in mods` for
`examples/hw1-harness-clients`. Neither file exists at that root — `run.py` does
not exist in this example at all, and `model_stub.py` lives in `runner/`. The
probe passes vacuously as written, so the shipped assertion
(`test_the_runner_is_structurally_outside_the_gate`) states the positive
instead: the reader-visible set is exactly the three `client_*.py`, and
`runner/drive.py` exists where `H-11` puts it. This is the third wave in a row
to meet a plan snippet naming a non-existent `run` module.

## Task 1 — per-root permitted sets and the by-name `ccf` refusal

`165cb2a` · `tests/examples/test_client_example_purity.py`

The two gated roots say opposite things about the same package, and both are
right:

| root | `ccf.client` | harness + `mcp` |
| --- | --- | --- |
| `hw1-companies-over-revenue` | permitted — it is `consume.py`'s whole subject | forbidden |
| `hw1-harness-clients` | **refused by name** | permitted |

Four properties, all of them required by the orchestrator's brief and all of
them shipped:

1. **`_permitted` keeps PREFIX matching.** Factored into
   `test_client_example_purity.py::_covers`, which both the permitted test and
   the refusal test call so they cannot drift into two notions of "under". The
   entries in `PERMITTED_IMPORTS` are package **prefixes**, and a comment beside
   the mapping says so in capitals because the `frozenset` container type says
   the opposite. Exact membership would refuse
   `ccf.client.adapters.mcp_stdio`, `google.adk.tools.mcp_tool`,
   `mcp.client.stdio`, `langgraph.graph` and `langchain_core.tools` — every real
   import in both roots — while reading like a tightened gate. `_covers` also
   stops at a package boundary, so `ccf.clientele` and `mcpx` are not covered.
2. **`ccf` is refused BY NAME.** `REFUSED_IMPORTS` is a second per-root mapping
   and `_refused_by_name` runs *before* the permitted-set test, so widening the
   harness root's permitted set cannot admit `ccf`. The violation text names the
   package and says the client learns nothing about CCF.
3. **`consume.py`'s root behaviour is preserved exactly.** `HW1_ROOT` keeps
   `frozenset({"ccf.client"})` permitted and `frozenset()` refused. Every
   pre-existing control now routes through `_hw1_purity`, which passes that
   root's policy — the assertions are unchanged in what they check.
4. **No second prompt checker.** This gate's subject is imports. `git diff` for
   `tools/lints/no_hardcoding.py` and `tools/lints/allowlist.yaml` across this
   plan is empty.

`CLIENT_EXAMPLE_ROOTS = tuple(PERMITTED_IMPORTS)` — derived, so a root cannot be
added to one mapping and gated by half the module. A precondition test asserts
both mappings name the same roots and that no permitted set is empty.

**No rule was weakened.** `grep -c rglob` returns `0`; `reader_visible_modules`
still uses `glob("*.py")`; the empty-root and missing-root violations are
intact; the relative-import refusal is intact. `grep -ci 'skip|exempt|allowlist'`
returns **3**, and all three are prose stating that no skip exists (lines 59,
63 and the docstring of
`test_client_example_purity.py::test_the_runner_is_structurally_outside_the_gate`).

## Task 2 — the measured budget, three commands, three targets, C-20-9

`59aa51f` · `examples/hw1-harness-clients/README.md`, `Makefile`,
`tests/examples/test_client_example_budget.py`

Measured, then declared:

| client | physical lines |
| --- | --- |
| `client_adk.py` | 186 |
| `client_langgraph.py` | 235 |
| `client_anthropic.py` | **288** |
| **Declared budget** | **300** |
| **Headroom over the largest** | **12** |

Leg 2 is legitimately largest: it configures a CLI subprocess as well as a tool.
The budget is enforced **per module**, never on the sum — which mattered little
while the gate walked one root with one `consume.py` and is the whole rule now
that a root carries three programs.

Three documented commands, three targets:

```
.venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs adk
.venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs anthropic
.venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs langgraph
```

`example-hw1-harness-clients-adk`, `-anthropic`, `-langgraph`. One recipe line
each, `.venv/bin/python` spelled literally, `.PHONY` declared, and deliberately
**not** prerequisites of `examples:` — that list runs the all-legs target, which
uses `$(ENV) $(PYTHON)` because CI has no `.venv`. The same two-target shape
`example-hw1` / `example-hw1-mcp` already have.

`make -n` on each exits 0;
`grep -A1 -E '^example-hw1-harness-clients-(adk|anthropic|langgraph):' Makefile | grep -c '\$(PYTHON)'`
returns `0`.

## Task 3 — the command-identity machinery, generalized

`251066b` · `tests/examples/test_client_example_purity.py`,
`docs/surface/examples/RETIREMENT-COUPLINGS.md`

The shipped machinery was pinned to `CLIENT_EXAMPLE_ROOTS[0]` and to a
`MAKE_TARGETS` constant, so adding a root armed the *import* assertions against
the new README and pointed none of the *command* assertions at it. Good half —
no accidental red. Bad half — no coverage. The bad half is the silent one.

- `COMMAND_SPECS` is per-root, mirroring `PERMITTED_IMPORTS`.
  `HARNESS_README_COMMAND` anchors on the invocation, because these commands
  carry no environment assignment and `README_COMMAND` would have matched
  nothing — a `findall` over the wrong pattern returns `[]`, not an error.
- `documented_commands(root, pattern, targets)` and
  `make_recipe(target, makefile_path)` take their subject as parameters.
  `make_recipe`'s missing-target lookup now asserts instead of raising
  `StopIteration`.
- `test_client_example_purity.py::test_every_documented_command_names_a_distinct_binding_scheme`
  was **not** parametrized over the new root. It is about `CCF_BINDING` schemes,
  which these commands do not carry. Confirmed: `-k binding_scheme` collects one
  test.
- The new root's analogous claim ships as
  `single_token_difference_violations` — the three commands differ at exactly
  one token position, and that token's values are exactly the legs the example
  ships a `client_*.py` for. Vacuity guards: fewer than three commands, unequal
  token counts, a repeated value at the differing position.

**Retirement inventory regenerated** as the final step: 238 → 239 rows across
78 → 79 files. The Makefile edit shifted the report's line-numbered `Makefile`
rows as predicted, and one new `documentary` row appeared from the `C-20-3`
docstring's reference to
`examples/external/00-hello-context/run.py::_assert_zero_ccf_imports` (cited to
say that grep is *not* the precedent, per `H-12`). A second run left the file
byte-identical.

## Sabotage controls — thirteen mutations, thirteen red

Every mutation was applied to the **shipped** function, the named test was run
against it, and the file was restored from a pristine copy. `diff -q` confirmed
restoration after every sweep.

| Control | Mutation to the shipped code | Observed |
| --- | --- | --- |
| **C-20-1** | `_imports` ignores `ast.Import` | `AssertionError: a `ccf` import in a harness client passed the gate` |
| **C-20-2** | `_imports` ignores `ast.ImportFrom` | `` `from ccf.client import ...` passed the gate `` |
| **C-20-3** | `_imports` scans `tree.body` instead of `ast.walk` — *the grep equivalent* | `a deferred `ccf` import passed the gate` |
| **C-20-4** | `_imports` reports every `ImportFrom` as absolute | violation present but says `runner`, not `relativ` |
| **C-20-5** | permitted set becomes a module-level **union** and the by-name refusal is removed | `a `ccf.client` submodule passed the harness root's gate` |
| **C-20-6** | an empty root returns `[]` instead of the vacuity violation | `a harness root with no client program passed the gate` |
| **C-20-7** | a missing root returns `[]` | `a non-existent harness root passed the purity gate` |
| **C-20-8a** | `command_identity_violations` stops comparing the two strings | `a bare interpreter` |
| **C-20-8b** | the `$(PYTHON)` refusal is removed | `the refusal … did not say why: expected 'not a string a reader can type'` |
| **C-20-8c** | the `.venv/bin/python` requirement is removed | `an identical pair that nobody can type was accepted` |
| **C-20-9** | `check_example_budget` checks `modules[:1]` only (the one-module assumption) | `client_langgraph.py over the declared budget passed the gate` |
| **T-20-40** | `_covers` becomes exact membership | `AssertionError: ccf.client.adapters.mcp_stdio` |
| **precondition** | a root added to `PERMITTED_IMPORTS` only | `the permitted and refused mappings name different roots` |

Four further mutations beyond the plan's roster, also red:
`single_token_difference_violations`' minimum-three guard dropped; its
`len(differing) != 1` rule loosened to `< 1`; its repeated-value check dropped;
its equal-length check dropped. Plus three end-to-end mutations against the
*artifacts* rather than the code: the `adk` recipe "fixed" back to
`$(ENV) $(PYTHON)` (identity assertion red), the anthropic README block losing
`--legs` (one-token assertion red), a documented leg the example does not ship
(`crewai`, leg-coverage assertion red), and one fenced block deleted
(command-count assertion red).

**Controls that could not be made to fail: none.** Two came back green on the
first sweep and were fixed rather than reported as acceptable:

1. **The `$(PYTHON)` and `.venv/bin/python` branches of
   `command_identity_violations` were unreachable through a divergent pair.**
   Every mutation in the C-20-8 set makes the two strings differ, and
   `documented != recipe` gets there first — so deleting either branch left the
   control green. Answered by adding
   `test_c20_8_the_identity_check_refuses_an_identical_but_untypeable_pair`: a
   README and a recipe that **agree perfectly** and are still not a command
   anybody can type. It asserts the *reason* in the violation text, because both
   branches fire on the `$(PYTHON)` subject and a count-only assertion would
   stay green with one deleted.
2. **The `len(differing) != 1` rule had no case that isolated it.** Loosened to
   `< 1`, every existing case was still caught by the length check, the
   distinctness check or the minimum. Answered by adding *"two tokens differ and
   both carry distinct values"* — three commands that change the subject
   alongside the harness, which is the `18.1-CLOSE-REVIEWS` finding shape one
   root over.

Both are recorded in the shipped docstrings, not just here.

## Verification

| Check | Result |
| --- | --- |
| `.venv/bin/python -m pytest tests/examples/test_client_example_purity.py -q` | 54 passed (22 before this plan) |
| `.venv/bin/python -m pytest tests/examples/test_client_example_budget.py -q` | 11 passed (9 before) |
| `.venv/bin/python -m pytest tests/examples -q` | 439 passed, 37 skipped |
| `.venv/bin/python -m pytest tools/docs_tests/…::test_the_committed_report_is_current -q` | passed |
| `.venv/bin/python -m pytest tests/invariants/test_citation_coverage.py -q` | 5 passed |
| `make ci-core` | **exit 0** — 4066 passed, 118 skipped (4032 before) |
| `make ci` | **exit 0** |
| `make example-hw1-harness-clients` (inside `make ci`) | three legs `MATCH` on `5d7bfa49…` with declared company names, **no refusal line** |
| `git diff --stat 2f4a2f5 -- src/` | empty |
| `git diff 2f4a2f5 -- tools/lints/allowlist.yaml` | empty |
| `git diff 2f4a2f5 -- tools/lints/no_hardcoding.py` | empty |
| `grep -c rglob tests/examples/test_client_example_purity.py` | `0` |
| `grep -ci 'declared budget' examples/hw1-harness-clients/README.md` | `1` |
| `tests/examples/test_s2_client_transport_spike.py` | untouched — `20-07` owns its retirement |

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 2 — missing critical functionality] Two sabotage controls could not
be made to fail, and the gap was closed rather than reported**

- **Found during:** Task 3's first sabotage sweep.
- **Issue:** Mutating away the `$(PYTHON)` branch of
  `command_identity_violations`, and loosening
  `single_token_difference_violations`' `len(differing) != 1` to `< 1`, both
  left the corresponding controls green.
- **Fix:** Added `test_c20_8_the_identity_check_refuses_an_identical_but_untypeable_pair`
  (with a `because` column asserting which branch spoke) and a
  *"two tokens differ and both carry distinct values"* case. Both mutations then
  observed red.
- **Files modified:** `tests/examples/test_client_example_purity.py`
- **Commit:** `251066b`

**2. [Rule 2] `make_recipe` raised `StopIteration` on an undeclared target**

- **Found during:** Task 3, while parameterizing `makefile_path`.
- **Issue:** `next(...)` with no default. A documented target the Makefile does
  not carry is exactly the divergence this machinery exists to find, and
  `StopIteration` reports it as a lookup miss a caller could read as "nothing to
  compare".
- **Fix:** An assertion naming the target and the Makefile, plus
  `test_the_recipe_reader_refuses_a_target_that_is_not_declared` — observed red
  under a mutation that returns `""` instead.
- **Commit:** `251066b`

### Deliberate departures from the plan text

**3. The declared budget is 300, not the plan's "realistic range 120-150"**

Measurement: 186 / 288 / 235. The plan's range describes none of the three
clients. 300 satisfies the plan's own acceptance criterion
(`0 <= budget - max <= 30`) with 12 lines of headroom.

**4. C-20-9 pads the LAST client program, not the first**

The plan says "pad one `client_*.py`". Padding `modules[-1]` rather than
`modules[0]` makes the control catch the *one regression this root uniquely
invites*: every other root the budget gate walks holds exactly one
reader-visible program, so "check `modules[0]`" is a passing implementation
everywhere else in the tree and a hole exactly here. That mutation is what the
control was observed red against.

**5. `documented_commands`' pattern and targets default to a per-root lookup
rather than to hw1's constants**

The plan specifies `documented_commands(root, pattern, targets)`.
`tests/examples/test_hw1_two_transports.py` imports this function and calls it
with one argument, and that file is not in this plan's `files_modified`. Making
the parameters required would have broken it; giving them hw1-shaped defaults
would have made one root's rule the implicit one. `COMMAND_SPECS` resolves both:
a single-argument call gets *that root's* rule, and a control can still pass its
own explicitly.

**6. No `PERMITTED_PACKAGE` removal**

The plan permits keeping the name "if anything still reads it". It is retained
as the value inside `PERMITTED_IMPORTS[HW1_ROOT]` and documented as the hw1
root's one permitted package; the gate's decision comes from the per-root set.

## Known stubs

None. Every assertion added reads a shipped artifact or the shipped tree.

## Threat flags

None. This plan added no network surface, no auth path, no file access pattern
and no schema at a trust boundary. It added test-tree and example-tree material
only; `src/` is untouched.

## Notes for `20-07` and `20-08`

- **The full teaching README is still owed.** `examples/hw1-harness-clients/README.md`
  exists early because two of its parts — the budget line and the three fenced
  commands — are gated from now on. Its closing section says so explicitly. A
  `20-08` rewrite must keep exactly one `declared budget` line and exactly three
  line-initial `.venv/bin/python examples/hw1-harness-clients/…` strings, or
  `documented_commands`' count assertion fires.
- **The retirement inventory is current at this plan's close** and will be
  re-staled by this SUMMARY. The next plan regenerates it.
- **A new documentary coupling row** now points at
  `examples/external/00-hello-context` from
  `tests/examples/test_client_example_purity.py` (the `C-20-3` docstring). If
  `20-07` retires that example, that row is one of the references it must
  account for — the citation is load-bearing prose (`H-12`'s "the grep is not
  the precedent"), not an incidental mention.

## Self-Check: PASSED

- `examples/hw1-harness-clients/README.md` — FOUND
- `tests/examples/test_client_example_purity.py` — FOUND
- `tests/examples/test_client_example_budget.py` — FOUND
- `Makefile` — FOUND
- `docs/surface/examples/RETIREMENT-COUPLINGS.md` — FOUND
- commit `165cb2a` — FOUND
- commit `59aa51f` — FOUND
- commit `251066b` — FOUND
