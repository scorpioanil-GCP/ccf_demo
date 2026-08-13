# Phase 15.6 — deferred items

Out-of-scope discoveries logged rather than fixed, per the executor scope
boundary (only issues *directly caused by* a task's own changes are auto-fixed).

---

## DI-15.6-01 — three `tools/docs_tests` gates are red, and were red before this phase touched them

- **Found during:** plan `15.6-09`, task 3, running
  `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests -q`
  as that task's own verification step.
- **Established as pre-existing by measurement, not by assumption.** A
  throwaway detached worktree was created at this plan's base commit
  `4b407e0`, the same command was run there, and it produced **the identical
  three failures** — `3 failed, 83 passed`. At this plan's HEAD the same three
  fail and `98` pass, the difference being the 15 cases plan `15.6-09` added.
  The worktree was removed afterwards.
- **The three:**

  | Failing test | What it reports |
  |---|---|
  | `tools/docs_tests/test_documented_commands_exist.py::test_every_composed_example_target_is_documented` | `example-s1-01` runs in CI but no published page under `public/` names it — *"maintained, tested, and unfindable"* |
  | `tools/docs_tests/test_documented_commands_exist.py::test_the_gate_refuses_an_undocumented_composed_example` | the same gate's own control, failing for the same reason |
  | `tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current` | `docs/surface/examples/RETIREMENT-COUPLINGS.md` is stale — committed at **163 rows across 47 files**, the sweep now measures **181 across 52** |

- **Why it went unnoticed.** `pyproject.toml` sets `testpaths = ["tests"]`, so
  `tools/docs_tests` does **not** run under `make ci-core`. It runs in CI as
  its own step. A plan that verifies with `make ci-core` alone will report
  green over a red package, which is one of the two process findings already
  carried from the 15.1 close and is the reason plan `15.6-09` ran it
  explicitly and separately.
- **Why it is deferred rather than fixed.** Both are outside plan `15.6-09`'s
  file scope and neither is caused by its changes. The first wants a published
  page to name `example-s1-01`, which is `public/` authoring. The second wants
  `python tools/retirement_sweep.py --report` re-run and the regenerated
  report committed — an 18-row, 5-file drift that predates this phase and
  belongs to whoever owns the sweep's cadence. Neither is an executor
  auto-fix under Rules 1 to 3: they are not caused by this task and fixing
  them would silently regenerate a committed artifact.
- **Owner:** unassigned. Wants a ruling at the Phase 15.6 gate on whether the
  retirement report is regenerated in-phase or carried, and on whether
  `example-s1-01` gets a published page.

---

## `DI-15.6-02` — the citation ratchet's two floors are outside `COUNT_COUPLING_TREES`

- **Raised by:** plan `15.6-11` (the citation sweep and its ratchet), 2026-08-12.
- **What.** `tests/invariants/test_citation_coverage.py` carries two
  `MINIMUM_*` floors — `MINIMUM_SCANNED_CITATION_HOSTS` (954) and
  `MINIMUM_CITATIONS_READ` (797). Both are shaped so
  `tools/retirement_sweep.py::_floors` recognises them, and **it does**: run
  against the module it reports both, each paired with the scan function
  feeding it, and `count_coupling_rows(roots=[tests/invariants])` emits **four
  live rows** owned by `16-18`. What the sweep's *default* walk does not reach
  is the tree: `tools/retirement_sweep.py::COUNT_COUPLING_TREES` is
  `("tests/products",)`.
- **The coupling those four rows report, which is real and is why this is
  recorded rather than dropped.** Both scans walk `examples/`, so
  `MINIMUM_SCANNED_CITATION_HOSTS` has **headroom 0** and **first breaks at
  wave 8**, when `16-15` retires `examples/03-harness-portability` (27 hosts).
  `MINIMUM_CITATIONS_READ` has headroom 6 against
  `tests/examples/test_ext00_serve_output.py`.
- **Why plan `15.6-11` did not widen it.** Widening is one line of data — the
  sweep's own docstring invites exactly that (*"Data, so a later plan widens
  the search without editing the detector"*) — but it changes
  `docs/surface/examples/RETIREMENT-COUPLINGS.md`, which
  `tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current`
  already reports **stale at this phase's base** under `DI-15.6-01`.
  Regenerating it inside this plan would silently discharge a deferred item
  owned elsewhere and fold an 18-row pre-existing drift into a citation-sweep
  commit.
- **What closing it costs.** Add `"tests/invariants"` to `COUNT_COUPLING_TREES`,
  re-run `python tools/retirement_sweep.py --report`, commit the regenerated
  report. Measured: **4 new rows, all owned by `16-18` from the schedule**, so
  `test_the_committed_report_carries_no_unowned_row` stays green.
- **Owner:** whoever closes `DI-15.6-01`, since both want the same report
  regenerated in the same commit.
