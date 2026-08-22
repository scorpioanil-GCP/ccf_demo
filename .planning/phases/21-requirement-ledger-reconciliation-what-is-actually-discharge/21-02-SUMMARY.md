---
phase: 21-requirement-ledger-reconciliation-what-is-actually-discharge
plan: 02
subsystem: testing
tags: [ledger, audit, citations, client-seam, sabotage-controls, vacuity]

requires:
  - phase: 21-requirement-ledger-reconciliation-what-is-actually-discharge
    provides: the strict parser, the pinned diff base, `refuse_unresolvable`, and the zero-ROW vacuity floor
provides:
  - 22 reconciled `CLNT` rows — `CLNT-01`..`CLNT-22` — in both ledger channels
  - the zero-CITATION limb of `refuse_unresolvable`, relocated from wave 1 to the wave where it can be true
  - `test_the_scan_finds_citations_to_check` — the precondition that makes Check A non-vacuous
  - `test_control_5b_a_table_with_no_citations_raises`
  - the first named absence of the phase — `CLNT-17`, `Not built`, with four surviving artefacts named
affects: [21-03, 21-04, 21-05, 21-06, 21-07]

tech-stack:
  added: []
  patterns:
    - "A citation is `path.py::symbol` wherever the evidence is Python, which for this lane is every row that has evidence at all"
    - "A verdict names the test that goes red on regression, not only the shipped symbol (`D-04`)"
    - "A vacuity guard lands in the wave where its subject first exists, never earlier and never weakened"

key-files:
  created:
    - .planning/phases/21-requirement-ledger-reconciliation-what-is-actually-discharge/21-02-SUMMARY.md
  modified:
    - .planning/REQUIREMENTS.md
    - tools/docs_tests/test_requirement_ledger.py
    - docs/surface/examples/RETIREMENT-COUPLINGS.md

key-decisions:
  - "`.github/workflows/ci.yml:NN` is UNUSABLE as a status-cell citation — the lint's path group refuses a leading dot, so the token resolves to `github/workflows/ci.yml`, which is not in the tree. `CLNT-14` and `CLNT-16` cite the Python that enforces the gate instead"
  - "The plan's second sabotage is unsatisfiable as written once the zero-citation limb exists; it was run in both the plan's shape and the discriminating one, and both are recorded"
  - "Twenty-one of twenty-two rows read Complete. The one that does not is named to four specific surviving artefacts rather than asserted"

patterns-established:
  - "Sabotage the SHIPPED function, watch the numbered control go red, restore from backup — and when a plan's stated discrimination is no longer expressible, reproduce the PRIOR module shape to show what the new test catches that the old one could not"

requirements-completed: [RECON-01, RECON-02]

duration: 105min
completed: 2026-08-22
---

# Phase 21 Plan 02: Verdicts for the 22 `CLNT` Rows — Summary

**Twenty-two rows of the fifty-four now carry a verdict backed by a citation that resolves as written and by the name of the test that goes red if the property regresses — twenty-one `Complete`, one `Not built` whose absence is four named artefacts still sitting in the tree — and the vacuity guard that plan `21-01` deliberately withheld landed immediately after the first eight citations existed, was watched refusing, and was never weakened.**

## Performance

- **Duration:** ~105 min
- **Tasks:** 3 of 3
- **Commits:** 3 task commits + this one
- **Tests added:** 2 (module 33 → 35; `gate-tools` leg 2 187 → 189)

## Task Commits

1. **Task 1: `CLNT-01`..`CLNT-08` + the zero-citation guard, precondition and CONTROL 5b** — `1a7a8b6` (feat)
2. **Task 2: `CLNT-09`..`CLNT-14` and `CLNT-16`** — `e190f28` (feat)
3. **Task 3: `CLNT-15`, `CLNT-17`..`CLNT-22` + the regenerated coupling inventory** — `6fa56f4` (feat)
4. **This SUMMARY + the regenerated coupling inventory** — final commit (docs)

## The 22 rows

Every citation below is a full repo-relative path that exists as written and
that `refuse_unresolvable` admits and the citation lint resolves. Where a row
carries several, the one most load-bearing is given here and the rest are in
the ledger's checkbox channel.

| Id | Verdict | Citation | Guarding test |
|---|---|---|---|
| `CLNT-01` | Complete | `tests/client/test_surface.py::assert_public_surface` | same — set equality on `__all__`, plus four controls that watch it refuse a fifth name |
| `CLNT-02` | Complete | `src/ccf/client/result.py::GUARDED_FIELDS` | `tests/client/test_result_guard.py::test_a_refused_result_refuses_every_post_assembly_field`, parametrized once per field |
| `CLNT-03` | Complete | `src/ccf/client/errors.py::BindingError` | `tests/client/test_result_guard.py::test_binding_error_is_a_transport_error` + `tests/client/test_codec.py::test_a_malformed_wire_raises_and_never_returns_a_refusal` |
| `CLNT-04` | Complete | `src/ccf/client/binding.py::resolve_binding` | `tests/client/test_binding.py::test_an_explicit_kwarg_beats_a_set_env_var` (asserts which adapter RAN) |
| `CLNT-05` | Complete as ruled | `src/ccf/client/wire.py::TransportAdapter` | `tests/client/test_surface.py::test_no_adapter_constructs_the_outcome` |
| `CLNT-06` | Complete | `tests/client/test_surface.py::count_result_construction_sites` | `::test_result_is_constructed_in_exactly_one_place` + `::test_the_construction_scan_reads_the_whole_shipped_tree` |
| `CLNT-07` | Complete | `src/ccf/products/refusal.py::RefusalEnvelope` | `tests/products/test_refusal_envelope.py::test_the_refusal_vocabulary_is_closed_by_set_equality` |
| `CLNT-08` | Complete | `tests/client/test_codec.py::test_a_served_outcome_survives_the_round_trip_whole` | same, plus `tests/client/test_inprocess_adapter.py::test_the_wire_carries_exactly_the_canonical_bytes_of_the_vessel` |
| `CLNT-09` | Complete | `src/ccf/products/resolver.py::GovernedResolver` | `tests/invariants/test_src_does_not_import_runtime.py::test_no_module_under_src_imports_the_runtime_package` |
| `CLNT-10` | Complete | `tests/client/test_no_provisioning.py::scan_for_provisioning` | `tests/client/test_inprocess_adapter.py::test_a_second_ask_on_one_client_does_not_reboot` + `tests/client/test_no_provisioning.py::test_the_client_tree_is_actually_scanned` |
| `CLNT-11` | Complete | `tests/client/conformance/suite.py::assert_served_parity` | the same suite, driven from both `test_inprocess_conformance.py` and `test_mcp_conformance.py` |
| `CLNT-12` | Complete | `tests/examples/test_hw1_harness_clients_runner_gates.py::test_control_1_a_marker_chrome_can_satisfy_is_refused` | same — `D-IMPL-170` requires a STANDING control, so evidence and guard are one thing here |
| `CLNT-13` | Complete | `examples/hw1-companies-over-revenue/consume.py::main` | `tests/examples/test_client_example_purity.py::test_the_make_target_runs_the_readmes_documented_command` |
| `CLNT-14` | Complete | `tests/examples/test_client_example_purity.py::check_example_purity` | same + `tests/examples/test_client_example_budget.py::test_the_readmes_number_is_what_the_gate_enforces` |
| `CLNT-15` | Complete | `src/ccf/client/adapters/mcp_stdio.py::McpStdioAdapter` | `tests/client/conformance/test_mcp_conformance.py::test_refusal_parity` |
| `CLNT-16` | Complete | `tools/retirement_sweep.py::render` | `tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current` |
| `CLNT-17` | **Not built** | — (see the absence below) | none — there is nothing to guard |
| `CLNT-18` | Complete | `tests/examples/test_hw1_two_transports.py::NOT_COPIED` | `tests/examples/test_hw1_two_transports.py::example`, which refuses a subject carrying a graph |
| `CLNT-19` | Complete | `tests/invariants/test_mcp_role_separation.py::test_the_client_tree_holds_exactly_the_named_unentitled_door` | same, gated by `::test_the_detector_sees_the_in_process_adapter` |
| `CLNT-20` | Complete | `src/ccf/products/debt_scorer.py::AssemblyDebtScorer` | `tests/products/test_reference_debt_scorer.py::test_control_empty_assembly_fires` and its four sibling controls |
| `CLNT-21` | Complete | `src/ccf/client/adapters/binding_document.py::BindingDocument` | `tests/client/test_binding_document.py::test_the_document_carries_exactly_one_reference` |
| `CLNT-22` | Complete | `tests/products/test_resolver_defaults.py::test_the_default_is_selected_when_no_scorer_is_passed` | same + `tests/client/test_data_only_deployment.py::test_the_debt_on_the_wire_was_measured_by_the_sdk_reference_scorer` |

**No test was written in this plan under `tests/`, and none was written anywhere
to manufacture a name for `D-04`.** Every guarding test named above already
existed. The only `tools/` write is the relocated vacuity guard.

## The one `Not built` row, and what closing it would mean

**`CLNT-17` — the condemned Section-1 example trees are not dispositioned.**

The absence is four things still in the tree, each checked at execution time
rather than inferred from a SUMMARY:

- `examples/s1-00-companies-over-revenue/` and
  `examples/s1-01-hello-context-product/` are both tracked directories.
- `tests/examples/test_spine_separation.py` (14 test functions, scoped on
  `s1-*`) and `tests/examples/test_section_one_is_agent_free.py` both still
  ship, so the example-shape rulings `D-26` and `D-25` suspended are still
  enforced by gates that were supposed to be retired with their subjects.
- The `example-s1-00` and `example-s1-01` Makefile targets both still exist.
- `docs/surface/examples/RETIREMENT-COUPLINGS.md` still files **58** coupling
  rows against plan `17-08` as their owner.

**Why it stopped is on the record, and it is not neglect.**
`17-08-SUMMARY.md` carries `status: blocked-at-task-3`: the removal was
**disputed on a measurement**, not skipped. Deleting
`examples/s1-01-hello-context-product` removes the last shipped `examples/`
call site of `ccf.products.request::refuse_request`, which a standing
seam-obligation gate asserts exists; and the plan's task 4 returned the
`00`–`08` half of `D-27` to Dave as an undecided blocking checkpoint.

**For plan `21-05`'s work list, lifted so it need not be re-derived:**

> Closing `CLNT-17` means removing both `s1-*` trees together with every gate,
> make target, CI job, floor constant and published snippet that names them —
> in one change, because `D-27` forbids a partial state — retiring
> `test_spine_separation.py` and `test_section_one_is_agent_free.py` rather
> than leaving them blind, re-counting `MINIMUM_GATE_CALL_SITES`,
> `MINIMUM_PROJECTING_BODIES` and `MINIMUM_RESOLVED_BINDER_SITES` from the
> post-removal tree, and first supplying a replacement worked example for
> `ccf.products.request::refuse_request` so the seam-obligation gate keeps a
> live call site. **It also needs Dave's ruling on the `00`–`08` half of
> `D-27`, which plan `17-08` returned undecided.** Nothing in this list was
> started here: `D-11` and the ROADMAP's out-of-scope paragraph forbid an
> executor closing a gap the audit discovers.

## The zero-citation guard: relocated from wave 1, not weakened

**The measurement that forced the relocation.** At this phase's pinned base
`c51406b`, `citations_in_status_cells(ledger_text())` returned **zero** tokens
— scanned across all 133 status cells with the citation lint's own `NODE_ID`
and `CITATION` patterns plus the module's wider `LOOSE_NODE_ID`. A guard
raising on zero citations, and a precondition asserting the real ledger yields
a non-empty citation list, would therefore both have **failed on landing** and
reddened `ci-core` for five waves — in a phase whose own `Makefile` contract is
that `ci-core` stays green from wave one onward.

So plan `21-01` landed the zero-**ROW** limb only, which was false the day it
shipped and therefore honest the day it shipped, and said in its own docstring
that the zero-**CITATION** limb was owed here. This plan landed it in task 1,
**after** writing the first eight rows' citations and in the same commit, so it
has never existed in a state where it could not be true. Three things landed
together:

- the zero-citation limb inside `refuse_unresolvable`, raising rather than
  returning `[]`;
- `test_the_scan_finds_citations_to_check`, the precondition — which per `D-21`
  carries **no count**, because a floor of fifteen would have to be re-edited by
  every later wave and could be silently satisfied by a citation nobody meant
  to write;
- `test_control_5b_a_table_with_no_citations_raises`.

Fifteen citation-shaped tokens existed in status cells at the moment the guard
landed; **the guard reads none of that number.** It reads non-emptiness.

### Every mutation, and what it made red

All three were applied to the **shipped** function, observed, and restored from
a backup copy taken before the first one.

| Sabotage | Applied to | Observed |
|---|---|---|
| the zero-citation limb `return []`s instead of raising | `refuse_unresolvable` | **CONTROL 5b RED**, and nothing else — 1 failed, 34 passed |
| `citations_in_status_cells` returns `[]`, guard intact | the shipped extractor | **8 failed**, including the precondition and every Check-A control — the guard catches it too |
| `citations_in_status_cells` returns `[]` **and** the zero-citation limb removed (the wave-1 module shape) | both | **the precondition RED while `test_every_cited_path_in_a_status_cell_resolves_as_written` stayed GREEN over nothing** — the discrimination the precondition exists for |

The third row is the one worth keeping. It reproduces the exact state plan
`21-01` shipped in and shows what the new test catches that the old module
could not: a Check-A assertion reporting green over an empty set.

## Deviations from Plan

### 1. [Rule 3 — the citation form the plan asked for is unusable in this file]

- **Found during:** Task 2 preparation, before any edit.
- **Issue:** The plan's task 2 says to cite `CLNT-14`'s and `CLNT-16`'s
  gate-reachability claims as anchored line citations naming *"the `Makefile`
  target and the `.github/workflows/ci.yml` step"*. **Neither is expressible.**
  A `Makefile` has no suffix, so it matches neither citation pattern and is
  invisible to the lint by construction — which is already on the record in
  this phase's `deferred-items.md`. And `.github/workflows/ci.yml:35` is worse
  than invisible: the lint's `CITATION` path group is
  `[A-Za-z0-9_][A-Za-z0-9_./+-]*\.(…)` and **refuses a leading dot**, so the
  token that actually matches is `github/workflows/ci.yml`, which is not a file
  in this tree. Measured: `CITATION.search('.github/workflows/ci.yml:35')`
  returns the path `github/workflows/ci.yml`. Writing it into a status cell
  would have been REFUSED by this phase's own `refuse_unresolvable` — correctly,
  as a citation to a path that does not exist as written.
- **Fix:** Both rows cite the **Python that enforces the property** and state
  the reachability fact in prose. `CLNT-14` cites `check_example_purity` and
  `check_example_budget` and records that `[tool.pytest] testpaths = ["tests"]`
  is what puts them in the always-on pipeline; `CLNT-16` cites
  `test_the_committed_report_is_current` and records that `make gate-tools` is a
  leg of `ci-core` and `ci`. No plain-word anchor was used anywhere, so the
  plan's *"a plain-word anchor is silently unchecked"* hazard cannot arise.
- **Commit:** `e190f28`

### 2. [Rule 2 — a plan-specified sabotage became unsatisfiable once the guard landed]

- **Found during:** Task 1(b), running the acceptance criteria.
- **Issue:** The plan's second observed sabotage says: make
  `citations_in_status_cells` return `[]`; the precondition FAILS *"while
  `test_every_cited_path_in_a_status_cell_resolves_as_written` still passes —
  which is precisely why the precondition exists."* Once the zero-citation limb
  is inside `refuse_unresolvable`, that is **no longer true**: the shipped
  assertion goes red too, because the guard catches the same blindness.
  The two mechanisms overlap, which is a strengthening, but it makes the stated
  discrimination inexpressible against the module as shipped.
- **Fix:** Both were run and both are recorded above. The plan's shape was run
  against the shipped module (8 red, including the shipped assertion), and then
  the **wave-1 module shape** was reconstructed — extractor blinded *and* the
  zero-citation limb removed — which produces exactly the plan's stated
  observation. That is the honest version of the claim: the precondition is what
  would have caught the vacuity in the wave where the guard did not yet exist.
- **Commit:** `1a7a8b6`

### 3. `CLNT-13` carries a clause the row did not anticipate

- **Found during:** Task 2.
- **Issue:** `CLNT-13` reads *"`consume.py` beside an opaque `deployment/`
  directory and a README"*. The tree also holds
  `examples/hw1-companies-over-revenue/server/`, added by Phase 18.1 when it
  separated the MCP server from the client.
- **Resolution:** The verdict stays `Complete` and the qualifying clause **says
  so** rather than eliding it. `deployment/` is still opaque to the client and
  `consume.py` still reaches it through `CCF_BINDING` alone, so no clause of the
  row is weakened; but a later reader comparing the row to the tree will find a
  third directory, and the cell tells them why.
- **Commit:** `e190f28`

### 4. Two `.md` files in `docs/` are untracked and were left alone

- **Found during:** every `git status` in this plan.
- **Issue:** `docs/CCF_SDK_DE_REQUIREMENTS.md` and
  `docs/Context_Product_Specification_Standard_v0-3.md` are untracked. They were
  untracked before this plan began.
- **Disposition:** **Pre-existing, reported, not touched.** They are outside
  this plan's `files_modified` and outside the audit's subject; committing or
  ignoring them would be a disposition this plan has no authority to make.

## Verification

| Check | Result |
|---|---|
| `pytest tools/docs_tests/test_requirement_ledger.py -q` | **exit 0** — 35 passed (was 33) |
| `pytest tools/docs_tests/test_retirement_sweep.py -q` | **exit 0** |
| `python -m tools.lints --citations` | **exit 0**, 0 findings |
| `make lint` | **exit 0** |
| `make typecheck` | **exit 0** — 211 source files |
| `make test` | **exit 0** — **4105 passed / 118 skipped**, 10m41s — identical to the wave-1 baseline |
| `make gate-tools` | **exit 0** — leg 1 406, leg 2 **189** (was 187) |
| `pytest tests/invariants/test_citation_coverage.py -q` | **exit 0** — 5 passed; the ceiling is unmoved because every citation written here is `::symbol`, not an unanchored line citation |
| `git diff --stat <base>..HEAD -- src/ runtime/ examples/ public/ pyproject.toml` | empty |
| `git diff --name-only <base>..HEAD -- tools/` | only `tools/docs_tests/test_requirement_ledger.py` |
| `git diff --stat <base>..HEAD -- tools/lints/citations.py` | empty |
| `git diff --stat -- tests/` per task commit | empty |
| `CLNT-01`..`CLNT-22` carrying a bolded vocabulary token | **22 of 22** |
| `CLNT-` rows in this lane still reading `Pending` | **0** |
| the ten `RECON-` rows | untouched, still `Pending` in both channels |
| `git status --porcelain` after the final commit | only the two pre-existing untracked `docs/` files |

`make ci-core` is `lint typecheck test gate-tools`. Each leg was run
individually rather than as one command, because a full pipeline cannot
complete inside this harness's foreground call budget.

## What plans `21-03`..`21-07` inherit

- **A calibrated citation form.** `path.py::symbol` wherever the evidence is
  Python. It is now proven in bulk: 22 rows, ~90 citations, `--citations` at
  zero findings and `refuse_unresolvable` at zero messages.
- **The knowledge that `.github/` paths cannot be cited** in a status cell, and
  neither can a `Makefile` line. The documentation lane (`21-03`, `21-04`) will
  hit this harder than this lane did, because far more of its evidence lives in
  files the lint's path grammar cannot name.
- **A non-vacuous Check A.** `test_every_cited_path_in_a_status_cell_resolves_as_written`
  now has a subject, and `test_the_scan_finds_citations_to_check` proves it.
- **One work-list entry already written**, `CLNT-17`, in the form plan `21-05`
  needs it.

## Threat Flags

None. This plan reads tracked repo files and writes markdown and one test
module. No credential, no network call, no external input, no package
installed — `T-21-SC` stays true by the `pyproject.toml` emptiness assertion
inside `FENCE`. `T-21-10` (closing a gap discovered mid-audit) was live in this
plan for the first time, at `CLNT-17`, and the fence assertion is what proves
it was not closed.

## Known Stubs

None.

## Self-Check: PASSED

All six files this plan created or modified exist on disk. All three task
commits `1a7a8b6`, `e190f28` and `6fa56f4` resolve in this repository.
Re-verified after the last edit: the ledger module is 35 passed, `--citations`
is exit 0, `make gate-tools` is exit 0 at 406 + 189, `make test` is exit 0 at
4105 passed / 118 skipped, and the pinned-base diff over `src/ runtime/
examples/ public/ pyproject.toml tools/lints/citations.py` is empty.

Two claims in this document were checked rather than asserted, because both are
the kind that read plausibly and can be wrong. `git ls-files
examples/hw1-companies-over-revenue/` returns nine paths and none is a store
file (`CLNT-18`). And `CITATION.search('.github/workflows/ci.yml:35')` was run
against the shipped pattern and returns the path `github/workflows/ci.yml`,
which `(REPO_ROOT / cited).is_file()` refuses — the measurement behind
deviation 1.
