# Phase 24.5.1 — deferred items (out-of-scope discoveries, not fixed here)

## 1. `tools/docs_tests/test_requirement_ledger.py::test_the_uat_roster_matches_the_records_on_disk` is RED, pre-existing (found by plan 24.5.1-04)

- **Found during:** plan `24.5.1-04` Task 3, running the plan's prescribed
  `pytest tools/docs_tests` (287 passed, 1 failed).
- **What:** `the frozen human_verification roster and the records on disk have
  diverged. on disk but not in the roster:
  ['.planning/phases/24.5-sdk-gap-catch-up-cp-00-through-cp-04/24.5-VERIFICATION.md']`.
- **Pre-existing, measured:** the record on disk last moved at `cae7297c`
  (Phase 24.5 close) and the frozen roster in the test at `14c28ea6` (Phase
  23.1); both predate every 24.5.1-04 commit (`8f98ec04`, `3f1b4d9b`,
  `cb4427c5`). The test reads `.planning/` records and the test module's own
  roster; it reads nothing plan 04 touched.
- **Not mine to fix:** plan 04's `files_modified` roster is the nine hw1/test
  files plus the Makefile; the roster in the test module is a frozen list a
  ruling owns.
- **Owner:** plan `24.5.1-07` (close prep — every instrument at close) or a
  dated ruling adding `24.5-VERIFICATION.md` to the roster.
