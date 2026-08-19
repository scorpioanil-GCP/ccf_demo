# Deferred items — Phase 18.1

## A SECOND pre-existing `make ci-core` red, in files this executor may not edit

**Discovered:** 18.1-01 Task 1, running `make ci-core` after the D-19 report regeneration.

`18.1-VALIDATION.md` § *Pre-existing Red* declares **one** red at `7f048a6`
(`test_the_committed_report_is_current`). That one is fixed by Task 1 and is green.
There is a **second**, which the validation strategy did not measure:

```
FAILED tests/invariants/test_citation_coverage.py::test_the_unanchored_python_citation_population_cannot_regrow
1 failed, 3870 passed, 118 skipped in 581.54 s
```

Five unanchored `path.py:LINE` citations sit in the planning tree, ceiling is 0:

| Site | Cites | Introduced by |
|---|---|---|
| `.planning/ROADMAP.md:1530` | `src/ccf/client/adapters/mcp_stdio.py:322` | `aef864e` (2026-08-18 06:41) |
| `.planning/STATE.md:23` | `tests/examples/test_hw1_two_transports.py:261` | `6023320` (2026-08-18 18:40) |
| `.planning/STATE.md:24` | `src/ccf/client/binding.py:160` | `6023320` |
| `.planning/STATE.md:374` | `door.py:139-141` | `1c5c04f` (2026-08-18 05:55) |
| `.planning/STATE.md:375` | `mcp_stdio.py:397,404` | `1c5c04f` |

`git blame` puts **every one of the five before this plan's first commit** (`c8bfadc`),
and all five were written by phase-18.1 *planning*, not by execution.

**Why it is not fixed here.** The only two files carrying the citations are
`.planning/STATE.md` and `.planning/ROADMAP.md`. This executor was launched under an
explicit, critical-priority prohibition on modifying either — the orchestrator is their
single writer, because this project's `state.*`/`roadmap.*` handlers have corrupted
`STATE.md` twice while reporting success. The remedy is therefore **not this plan's to
apply**, and raising `MAXIMUM_UNANCHORED_PY_CITATIONS` was rejected: the gate's own
failure text says a deliberate addition and an accidental regression need the identical
edit to that constant, so raising it for documents this plan did not author would spend
a ratchet on someone else's drift.

**Remedy, for whoever owns the tracking files.** Convert all five to the
`path.py::Symbol` form `D-IMPL-114` ruled. Roughly five one-line edits; no code moves.

**Consequence for the rest of Phase 18.1.** `make ci-core` reads
`1 failed, 3870 passed` and the failure is this one. That is the phase's true baseline
after Task 1. Any *other* failure is a real regression. Every `make ci-core` acceptance
criterion in plans `18.1-01` … `18.1-05` should be read as "green but for
`test_the_unanchored_python_citation_population_cannot_regrow`" until this is cleared.
