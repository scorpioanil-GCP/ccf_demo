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
